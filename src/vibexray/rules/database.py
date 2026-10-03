"""Database rules for Supabase and Postgres projects."""

from __future__ import annotations

import base64
import json
import re
from collections.abc import Iterable

from vibexray.model import Finding
from vibexray.rules.base import Rule
from vibexray.rules.util import (
    SQL,
    SRC,
    UI,
    custom_rule,
    is_client,
    is_noise,
    line_of,
    line_rule,
)
from vibexray.walker import SourceFile

_CREATE_TABLE = re.compile(
    r'create\s+table\s+(?:if\s+not\s+exists\s+)?(?:"?(?P<schema>\w+)"?\.)?"?(?P<name>\w+)"?', re.I
)
_OTHER_SCHEMAS = {
    "auth",
    "storage",
    "extensions",
    "cron",
    "graphql",
    "realtime",
    "vault",
    "pgsodium",
}


def _sql_files(files: list[SourceFile]) -> list[SourceFile]:
    """Postgres files that Supabase can expose. Prisma and drizzle folders can too, but only with grants."""
    return [
        f
        for f in files
        if f.suffix == ".sql" and not is_noise(f.path) and "seed" not in f.path.lower()
    ]


def _supabase_like(sqls: list[SourceFile]) -> bool:
    return any(
        "supabase/" in f.path.lower()
        or re.search(r"auth\.uid\(\)|\bto\s+(?:anon|authenticated)\b", f.text, re.I)
        for f in sqls
    )


def _rls_missing(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    sqls = _sql_files(files)
    if not _supabase_like(sqls):
        return
    blob = "\n".join(f.text for f in sqls)
    if re.search(r"loop[\s\S]{0,400}enable\s+row\s+level\s+security", blob, re.I):
        return
    for f in sqls:
        for m in _CREATE_TABLE.finditer(f.text):
            schema = (m.group("schema") or "public").lower()
            name = m.group("name")
            if schema in _OTHER_SCHEMAS or schema != "public":
                continue
            enabled = re.search(
                rf'alter\s+table\s+(?:only\s+)?(?:"?public"?\.)?"?{re.escape(name)}"?\s+enable\s+row\s+level\s+security',
                blob,
                re.I,
            )
            if not enabled:
                ln = line_of(f.text, m.start())
                yield rule.finding(f, ln, f.lines[ln - 1])


rls_missing = custom_rule(
    "rls-missing",
    "database_rules",
    "high",
    "rewrite",
    "Anyone with the public key from the page can read and change this table.",
    "Enable row level security on this table and add owner-scoped policies. The public key is visible in the browser.",
    _rls_missing,
    SQL,
)


def _rls_no_policy(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    sqls = _sql_files(files)
    blob = "\n".join(f.text for f in sqls)
    for f in sqls:
        for m in re.finditer(
            r"grant\s+(?:all|insert|update|delete)\b[^;\n]*\sto\s+(?:[\w\s,]*\b)?(?:anon|public)\b",
            f.text,
            re.I,
        ):
            ln = line_of(f.text, m.start())
            yield rule.finding(f, ln, f.lines[ln - 1])
        for m in re.finditer(
            r'alter\s+table\s+(?:only\s+)?(?:"?public"?\.)?"?(\w+)"?\s+enable\s+row\s+level\s+security',
            f.text,
            re.I,
        ):
            name = m.group(1)
            if not re.search(
                rf'create\s+policy[^;]*\son\s+(?:"?public"?\.)?"?{re.escape(name)}"?', blob, re.I
            ):
                ln = line_of(f.text, m.start())
                fnd = rule.finding(
                    f,
                    ln,
                    f.lines[ln - 1],
                    pm_text="Row security is on, but no rule lets anyone in. The app may fail here.",
                    engineer_text="Add policies for this table, or confirm that only the service role uses it.",
                )
                fnd.severity = "low"
                yield fnd


rls_no_policy = custom_rule(
    "rls-enabled-no-policy-or-grants",
    "database_rules",
    "medium",
    "check",
    "Row security is on, but broad grants to anonymous visitors can still leave the table open.",
    "Revoke broad grants from anon and authenticated, then add narrow policies. Adding policies does not remove old grants.",
    _rls_no_policy,
    SQL,
)

_POLICY_TRUE = re.compile(
    r"create\s+policy[^;]{0,400}?(?P<hit>(?:using|with\s+check)\s*\(\s*true\s*\))", re.I | re.S
)
_USER_COL = re.compile(
    r"\b(?:user_id|owner_id|email|created_by|author_id|profile_id|customer_id|member_id|phone)\b",
    re.I,
)
_TABLE_DEF = re.compile(
    r'create\s+table\s+(?:if\s+not\s+exists\s+)?(?:"?public"?\.)?"?(\w+)"?\s*\(', re.I
)
_POLICY_ON = re.compile(r'\son\s+(?:"?public"?\.)?"?(\w+)"?')
_WRITE_POLICY = re.compile(r"for\s+(?:all|insert|update|delete)")


def _user_tables(sqls: list[SourceFile]) -> set[str]:
    out: set[str] = set()
    for f in sqls:
        for m in _TABLE_DEF.finditer(f.text):
            end = f.text.find(");", m.end())
            if _USER_COL.search(f.text[m.end() : end if end != -1 else m.end() + 2000]):
                out.add(m.group(1).lower())
    return out


def _policy_true(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    sqls = _sql_files(files)
    user_tables = _user_tables(sqls)
    reported: set[str] = set()
    for f in sqls:
        for m in _POLICY_TRUE.finditer(f.text):
            stmt = m.group(0).lower()
            if "service_role" in stmt:
                continue
            table = _POLICY_ON.search(stmt)
            write = bool(_WRITE_POLICY.search(stmt)) or "with check" in stmt
            if not write and not (table and table.group(1) in user_tables):
                continue
            if table:
                # One finding per table keeps a repo with many policies readable.
                if table.group(1) in reported:
                    continue
                reported.add(table.group(1))
            ln = line_of(f.text, m.start("hit"))
            fnd = rule.finding(f, ln, f.lines[ln - 1])
            fnd.severity = "high" if write else "medium"
            yield fnd


policy_true = custom_rule(
    "policy-using-true",
    "database_rules",
    "high",
    "rewrite",
    "A database rule says everyone is allowed where a user check belongs.",
    "Replace true with an owner check such as auth.uid() = user_id. Keep true only for public read data.",
    _policy_true,
    SQL,
)

_SERVICE = re.compile(
    r"service_role|SERVICE_ROLE|sb_secret_[A-Za-z0-9_\-]{8,}|SUPABASE_SECRET_KEY|VITE_\w*SERVICE|NEXT_PUBLIC_\w*SERVICE"
)
service_role = line_rule(
    "service-role-in-client",
    "database_rules",
    "high",
    "rewrite",
    "The page ships a master key that skips every database rule.",
    "Move the service key to server code only. Use the publishable key in the browser.",
    pattern=_SERVICE,
    suffixes=UI,
    client=True,
)

_SENSITIVE = (
    "users|profiles|accounts|payments|orders|invoices|subscriptions|roles|user_roles|admin_users"
    "|permissions|credits|balances"
)
client_write = line_rule(
    "client-write-sensitive-table",
    "database_rules",
    "medium",
    "check",
    "The browser writes straight to a table that holds money, people, or roles.",
    "Check that row policies limit rows and columns for this table. Move role and money writes to the server.",
    pattern=re.compile(
        rf"\.from\(\s*['\"](?:{_SENSITIVE})['\"]\s*\)\s*\.(?:insert|update|upsert|delete)\("
    ),
    suffixes=UI,
    client=True,
)


def _rpc_open(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in _sql_files(files):
        text = f.text
        for m in re.finditer(r"create\s+(?:or\s+replace\s+)?function\b", text, re.I):
            start = text.find("$", m.end())
            header = text[m.start() : start if start != -1 else m.start() + 600]
            if not re.search(r"security\s+definer", header, re.I) or re.search(
                r'set\s+"?search_path"?', header, re.I
            ):
                continue
            tag = re.match(r"\$\w*\$", text[start:]) if start != -1 else None
            end = text.find(tag.group(0), start + len(tag.group(0))) if tag else start
            body = text[start:end] if tag and end != -1 else ""
            if "auth.uid()" in body:
                continue
            ln = line_of(text, m.start())
            yield rule.finding(f, ln, f.lines[ln - 1])
        for m in re.finditer(
            r"grant\s+execute\s+on\s+function[^;\n]*\sto\s+(?:anon|public)\b", text, re.I
        ):
            ln = line_of(text, m.start())
            yield rule.finding(f, ln, f.lines[ln - 1])


rpc_open = custom_rule(
    "rpc-or-function-open",
    "database_rules",
    "medium",
    "check",
    "Anyone can call a database function, and it can run with owner rights.",
    "Set search_path, check auth.uid() inside, and revoke execute from anon unless the function is public on purpose.",
    _rpc_open,
    SQL,
)

_JWT = re.compile(r"eyJ[\w-]{10,}\.(eyJ[\w-]{10,})\.[\w-]{10,}")


def _key_kind(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    """Anon and publishable keys are public by design, so only a service key is reported."""
    for f in files:
        if f.suffix not in SRC or is_noise(f.path) or not is_client(f):
            continue
        for m in re.finditer(
            r"createClient\([^)]*?(eyJ[\w-]{10,}\.eyJ[\w-]{10,}\.[\w-]{10,})", f.text, re.S
        ):
            payload = _JWT.match(m.group(1))
            if not payload:
                continue
            try:
                raw = payload.group(1) + "=" * (-len(payload.group(1)) % 4)
                role = json.loads(base64.urlsafe_b64decode(raw)).get("role")
            except ValueError:
                continue
            if role == "service_role":
                ln = line_of(f.text, m.start())
                yield rule.finding(f, ln, f.lines[ln - 1])


key_kind = custom_rule(
    "supabase-client-key-kind",
    "database_rules",
    "high",
    "rewrite",
    "A hardcoded database key in the page gives full access instead of public access.",
    "Replace the service key with the publishable key in client code. Rotate the exposed service key.",
    _key_kind,
    SRC,
)

RULES: list[Rule] = [
    rls_missing,
    rls_no_policy,
    policy_true,
    service_role,
    client_write,
    rpc_open,
    key_kind,
]
