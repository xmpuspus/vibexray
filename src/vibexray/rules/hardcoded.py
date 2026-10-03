"""Hardcoded values that belong in settings or a database."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable

from vibexray.model import Finding
from vibexray.rules.base import Rule
from vibexray.rules.util import (
    ENVFILE,
    SQL,
    SRC,
    code_only,
    custom_rule,
    is_client,
    line_of,
    line_rule,
    live,
)
from vibexray.walker import SourceFile

_DEV_LINE = re.compile(
    r"\bis_?dev\b|\bdev\s*\?|NODE_ENV|import\.meta\.env\.DEV|isLocal|listen|console\.|Logger",
    re.I,
)


def _localhost(f: SourceFile, m: re.Match, t: str) -> dict | None:
    if _DEV_LINE.search(t) or f.path.endswith((".example", ".sample")) or ".env." in f.path:
        return None
    sev = "medium"
    if re.search(r"fetch\(|axios", t) and is_client(f) and not re.search(r"\?\?|\|\|", t):
        sev = "high"
    return {"severity": sev}


localhost = line_rule(
    "localhost-url",
    "hardcoded_config",
    "medium",
    "rewrite",
    "The app calls an address that works only on the developer's computer.",
    "Read the base URL from an environment variable. Do not ship localhost in a deployed build.",
    pattern=re.compile(r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?::\d+)?"),
    suffixes=SRC + (".env", ".local"),
    refine=_localhost,
    per_file=3,
)

_MONEY = re.compile(
    r"\b(?:price|amount|cost|fee|tax|discount|credits|maxAmount|minAmount|refundLimit"
    r"|[A-Z][A-Z_]*(?:REFUND|AMOUNT|PRICE|FEE)[A-Z_]*)\s*[:=]\s*\d+(?:\.\d+)?\b"
)


def _money(f: SourceFile, m: re.Match, t: str) -> dict | None:
    if re.search(r"\bwidth|height|delay|timeout|offset|index", t, re.I):
        return None
    sev = (
        "high" if re.search(r"(^|/)(api|server|supabase/functions)/|route\.", f.path) else "medium"
    )
    return {"severity": sev}


price_or_limit = line_rule(
    "hardcoded-price-or-limit",
    "hardcoded_config",
    "medium",
    "check",
    "A price, fee, or limit is a typed-in number in code, not a setting.",
    "Move money values to config or the database so they change without a release.",
    pattern=_MONEY,
    suffixes=SRC,
    refine=_money,
    per_file=3,
)

stripe_id = line_rule(
    "stripe-id-literal",
    "hardcoded_config",
    "medium",
    "rewrite",
    "A payment product ID is typed into the code. It breaks when the account changes.",
    "Read Stripe IDs from environment settings. Test-mode and live-mode IDs differ.",
    pattern=re.compile(
        r"\b(?:price|prod|cus|sub|pi|plink)_(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{14,}\b"
    ),
    suffixes=SRC + SQL,
    per_file=3,
)

feature_flag = line_rule(
    "feature-flag-literal",
    "hardcoded_config",
    "low",
    "check",
    "A switch in code turns a feature on or off. Nobody can change it without a release.",
    "Move flags to config or a flag service. Remove dead branches such as if (false).",
    pattern=re.compile(
        r"\b(?:FEATURE_|ENABLE_|SHOW_|USE_|FLAG_)\w+\s*[:=]\s*(?:true|false)\b|\bif\s*\(\s*(?:true|false)\s*\)"
    ),
    suffixes=SRC,
    per_file=2,
)

_NAMED_NUMBER = re.compile(
    r"\b((?:max|min)\w*(?:amount|price|fee|credits|refund|discount)\w*|\w*refund\w*|\w*threshold\w*|\w*quota\w*)"
    r"\s*[:=]\s*(\d+(?:\.\d+)?)\b",
    re.I,
)


def _magic_conflict(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    seen: dict[str, list[tuple[SourceFile, int, str]]] = defaultdict(list)
    for f in live(files, SRC + SQL):
        code = code_only(f.text)
        for m in _NAMED_NUMBER.finditer(code):
            key = m.group(1).lower().replace("_", "")
            seen[key].append((f, line_of(f.text, m.start()), m.group(2)))
    for places in seen.values():
        if len({p[2] for p in places}) < 2 or len({p[0].path for p in places}) < 2:
            continue
        first = places[0]
        other = next((p for p in places if p[2] != first[2] and p[0].path != first[0].path), None)
        if other is None:
            continue
        (f, ln, _), (g, gl, _) = first, other
        yield rule.finding(
            f,
            ln,
            f.lines[ln - 1],
            related_file=g.path,
            related_line=gl,
            related_snippet=g.lines[gl - 1],
        )


magic_conflict = custom_rule(
    "magic-number-conflict",
    "hardcoded_config",
    "medium",
    "check",
    "The same rule has different numbers in different files.",
    "Pick one value, keep it in one place, and import it everywhere.",
    _magic_conflict,
    SRC + SQL,
)

preview_url = line_rule(
    "preview-or-tunnel-url",
    "hardcoded_config",
    "medium",
    "rewrite",
    "The app points at a temporary address from a build tool.",
    "Replace preview and tunnel hosts with the real production domain from config.",
    pattern=re.compile(
        r"https?://[\w.-]+\.(?:vercel\.app|netlify\.app|lovable\.app|lovableproject\.com|bolt\.host|stackblitz\.io"
        r"|replit\.(?:dev|app)|ngrok(?:-free)?\.(?:io|app|dev)|trycloudflare\.com|loca\.lt|github\.dev)"
    ),
    suffixes=SRC + SQL + ENVFILE,
    allow_config=True,
    per_file=3,
)


def _uuid_ok(f: SourceFile, m: re.Match, t: str) -> dict | None:
    return None if re.search(r"0{8}-0{4}", t) else {}


record_id = line_rule(
    "hardcoded-record-id",
    "hardcoded_config",
    "medium",
    "rewrite",
    "A query always uses one fixed user or record. Every visitor sees the same one.",
    "Use the signed-in user's ID from the session instead of a literal ID.",
    pattern=re.compile(
        r"\.eq\(\s*['\"](?:user_id|owner_id|account_id|org_id|customer_id|id)['\"]\s*,\s*['\"]"
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}['\"]"
    ),
    suffixes=SRC,
    refine=_uuid_ok,
)

RULES: list[Rule] = [
    localhost,
    price_or_limit,
    stripe_id,
    feature_flag,
    magic_conflict,
    preview_url,
    record_id,
]
