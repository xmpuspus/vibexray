"""Shared helpers for the rule modules: path filters, client and server tests, rule factories."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from functools import lru_cache

from vibexray.model import Finding
from vibexray.rules.base import Rule
from vibexray.walker import SourceFile

UI = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte")
PY = (".py",)
SQL = (".sql",)
SRC = UI + PY
ENVFILE = (".env", ".example", ".local", ".sample")

# Segment-aware: a raw substring test would skip "latest.ts" or miss a root-level "tests/".
_TEST_DIRS = {
    "test",
    "tests",
    "__tests__",
    "__mocks__",
    "__fixtures__",
    "fixtures",
    "e2e",
    "spec",
    "specs",
    "stories",
    "cypress",
    "storybook",
    ".storybook",
    "docs",
    "node_modules",
}
_TEST_NAME = re.compile(
    r"[._-](test|spec|stories|story|e2e)\.[a-z]+$|^test_|_test\.py$|^conftest\.py$"
)
_CONFIG_NAME = re.compile(
    r"^(vite|vitest|next|tailwind|postcss|eslint|jest|playwright|capacitor|babel|webpack|rollup"
    r"|svelte|nuxt|astro|drizzle|prettier)\.config\.\w+$"
)
_LOCKS = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "uv.lock"}
_SEED_PATH = re.compile(r"(^|/)seeds?(/|\.|-|_)|(^|/)prisma/seed|supabase/seed|(^|/)seed-data")


def is_test(path: str) -> bool:
    parts = path.lower().split("/")
    return any(p in _TEST_DIRS for p in parts[:-1]) or bool(_TEST_NAME.search(parts[-1]))


def is_noise(path: str, allow_config: bool = False) -> bool:
    low = path.lower()
    parts = low.split("/")
    name = parts[-1]
    if is_test(path) or name.endswith(".d.ts") or name in _LOCKS:
        return True
    if any(a == "components" and b == "ui" for a, b in zip(parts, parts[1:], strict=False)):
        return True
    return not allow_config and bool(_CONFIG_NAME.match(name))


def is_script_or_seed(path: str) -> bool:
    low = path.lower()
    return "scripts/" in low or low.startswith("script/") or bool(_SEED_PATH.search(low))


_SERVER_PATH = re.compile(
    r"(^|/)(app/api|pages/api|server|backend|supabase/functions|functions|netlify/functions|workers?|cron|jobs)/"
    r"|(^|/)api/|(^|/)route\.(ts|js|mjs)$|(^|/)middleware\.(ts|js)$"
)
_CLIENT_DIR = re.compile(r"(^|/)(frontend|client|web)/|(^|/)public/")
_APP_SRC_DIR = re.compile(
    r"(^|/)src/(components|hooks|pages|lib|utils|services|contexts|context|store|stores|views)/"
)
_SERVER_TEXT = re.compile(
    r"process\.env\.(?!NEXT_PUBLIC_)|from ['\"](express|fastify|@nestjs/\w+|next/server|koa|hono|pg)['\"]"
    r"|require\(['\"]express|Deno\.|@prisma/client|drizzle-orm|createServer\("
)
_USE_CLIENT = re.compile(r"""^\s*['"]use client['"]""", re.M)
_BROWSER_API = re.compile(r"\b(localStorage|sessionStorage|document\.|window\.|navigator\.)")


def is_server(f: SourceFile) -> bool:
    if f.suffix == ".py" or _SERVER_PATH.search(f.path.lower()):
        return not _CLIENT_DIR.search(f.path.lower()) or "process.env." in f.text
    return bool(_SERVER_TEXT.search(f.text)) and not _USE_CLIENT.search(f.text[:400])


def is_client(f: SourceFile) -> bool:
    """Evidence inside the file or a clear client folder. Never a guess from 'src/' alone."""
    p = f.path.lower()
    head = f.text[:400]
    if _USE_CLIENT.search(head):
        return True
    if f.suffix in (".py", ".sql") or "'use server'" in head or '"use server"' in head:
        return False
    if "import.meta.env" in f.text:
        return True
    server_text = bool(_SERVER_TEXT.search(f.text))
    if _SERVER_PATH.search(p) and not (_CLIENT_DIR.search(p) and not server_text):
        return False
    if f.suffix in (".vue", ".svelte", ".jsx"):
        return not server_text
    if f.suffix == ".tsx":
        return not server_text and not re.search(r"(^|/)app/", p)
    if _CLIENT_DIR.search(p) and not server_text:
        return True
    if _BROWSER_API.search(f.text) and not server_text:
        return True
    return bool(_APP_SRC_DIR.search(p)) and not server_text and f.suffix in UI


_STRIP = re.compile(
    r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`",
    re.S,
)


def _blank(m: re.Match) -> str:
    s = m.group(0)
    if s[0] in "\"'`":
        inner = re.sub(r"[^\n]", " ", s[1:-1])
        return s[0] + inner + s[-1]
    return re.sub(r"[^\n]", " ", s)


@lru_cache(maxsize=512)
def code_only(text: str) -> str:
    """Same length and line breaks, with comments and string text blanked out."""
    return _STRIP.sub(_blank, text)


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def match_close(code: str, open_idx: int) -> int | None:
    """Index of the bracket that closes the one at open_idx, on blanked code."""
    pairs = {"{": "}", "[": "]", "(": ")"}
    o = code[open_idx]
    c = pairs[o]
    depth = 0
    for i in range(open_idx, len(code)):
        ch = code[i]
        if ch == o:
            depth += 1
        elif ch == c:
            depth -= 1
            if depth == 0:
                return i
    return None


_FUNC_DEF = re.compile(
    r"\b(?:const|let|var)\s+(?P<n1>\w+)\s*(?::[^=\n]+)?=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*"
    r"(?::\s*[^={\n]+)?=>\s*\{"
    r"|\b(?:async\s+)?function\s+(?P<n2>\w+)\s*\([^)]*\)\s*(?::\s*[^{\n]+)?\{"
)


def function_bodies(text: str) -> list[tuple[str, int, int]]:
    """(name, body start, body end) for named JS and TS functions."""
    code = code_only(text)
    out = []
    for m in _FUNC_DEF.finditer(code):
        end = match_close(code, m.end() - 1)
        if end is not None:
            out.append((m.group("n1") or m.group("n2"), m.end(), end))
    return out


def enclosing_function(text: str, pos: int) -> tuple[str, int, int] | None:
    best = None
    for name, a, b in function_bodies(text):
        if a <= pos <= b and (best is None or a > best[1]):
            best = (name, a, b)
    return best


NETWORK = re.compile(
    r"\bfetch\(|axios|\bky\b|\.post\(|\.put\(|\.patch\(|\.delete\(|\.insert\(|\.update\(|\.upsert\("
    r"|\.rpc\(|\.invoke\(|mutate|trpc|supabase|useSWR|sendBeacon|\.from\(|signIn|signUp|location\b"
    r"|navigate\(|router\.|window\.open|reload\(|submit\(|\bapi\.|\bapi\b\w*\("
)


def is_comment_line(line: str) -> bool:
    s = line.strip()
    return s.startswith(("//", "/*", "*", "#", "--", "<!--"))


def _eligible(
    r: Rule, f: SourceFile, allow_config: bool, skip_scripts: bool, skip_noise: bool
) -> bool:
    if not r.applies_to(f):
        return False
    if skip_noise and is_noise(f.path, allow_config):
        return False
    return not (skip_scripts and is_script_or_seed(f.path))


Refine = Callable[[SourceFile, re.Match, str], dict | None]
Custom = Callable[[Rule, list[SourceFile]], Iterable[Finding]]


def line_rule(
    rid: str,
    category: str,
    severity: str,
    label: str,
    pm: str,
    eng: str,
    *,
    pattern: re.Pattern,
    suffixes: tuple[str, ...] = SRC,
    refine: Refine | None = None,
    absent: re.Pattern | None = None,
    client: bool | None = None,
    server: bool | None = None,
    skip_scripts: bool = True,
    skip_noise: bool = True,
    allow_config: bool = False,
    per_file: int | None = None,
    skip_comments: bool = True,
) -> Rule:
    """A regex rule. The pattern runs on the whole file so it can span lines."""
    holder: list[Rule] = []

    def check(files: list[SourceFile]) -> list[Finding]:
        r = holder[0]
        out: list[Finding] = []
        for f in files:
            if not _eligible(r, f, allow_config, skip_scripts, skip_noise):
                continue
            if client is not None and is_client(f) != client:
                continue
            if server is not None and is_server(f) != server:
                continue
            if absent is not None and absent.search(f.text):
                continue
            lines = f.lines
            seen: set[int] = set()
            for m in pattern.finditer(f.text):
                pos = m.start()
                for g in ("hit", "hit2"):
                    if g in pattern.groupindex and m.group(g) is not None:
                        pos = m.start(g)
                        break
                ln = line_of(f.text, pos)
                if ln in seen or ln > len(lines):
                    continue
                text = lines[ln - 1]
                if skip_comments and is_comment_line(text):
                    continue
                extra: dict = {}
                if refine is not None:
                    got = refine(f, m, text)
                    if got is None:
                        continue
                    extra = dict(got)
                sev = extra.pop("severity", None)
                snippet = extra.pop("snippet", text)
                fnd = r.finding(f, extra.pop("line", ln), snippet, **extra)
                if sev:
                    fnd.severity = sev
                out.append(fnd)
                seen.add(ln)
                if per_file and len(seen) >= per_file:
                    break
        return out

    rule = Rule(
        id=rid,
        category=category,
        severity=severity,
        label=label,
        pm_text=pm,
        engineer_text=eng,
        suffixes=suffixes,
        check=check,
    )
    holder.append(rule)
    return rule


def custom_rule(
    rid: str,
    category: str,
    severity: str,
    label: str,
    pm: str,
    eng: str,
    fn: Custom,
    suffixes: tuple[str, ...] = SRC,
) -> Rule:
    """A cross-file rule. fn gets the rule and every file, and yields findings."""
    holder: list[Rule] = []

    def check(files: list[SourceFile]) -> Iterable[Finding]:
        return fn(holder[0], files)

    rule = Rule(
        id=rid,
        category=category,
        severity=severity,
        label=label,
        pm_text=pm,
        engineer_text=eng,
        suffixes=suffixes,
        check=check,
    )
    holder.append(rule)
    return rule


def live(files: list[SourceFile], suffixes: tuple[str, ...] = SRC) -> list[SourceFile]:
    """Files a cross-file rule may read: right suffix, not a test, story, or UI kit file."""
    return [f for f in files if f.suffix in suffixes and not is_noise(f.path, allow_config=True)]
