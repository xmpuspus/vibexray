"""Secret keys that anyone can read."""

from __future__ import annotations

import re
from collections.abc import Iterable

from vibexray.model import Finding
from vibexray.rules.base import Rule
from vibexray.rules.util import (
    ENVFILE,
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

_PUBLIC_OK = re.compile(
    r"PUBLISHABLE|ANON|ANALYTICS|MAPS|_PUBLIC_|PUBLIC_KEY|PUBLIC_TOKEN|SITE_KEY|DSN|MEASUREMENT",
    re.I,
)
_PROVIDERS = re.compile(
    r"OPENAI|ANTHROPIC|CLAUDE|GEMINI|GOOGLE_AI|GROQ|OPENROUTER|MISTRAL|COHERE|DEEPSEEK|XAI|REPLICATE"
    r"|TOGETHER|PERPLEXITY|ELEVENLABS|HUGGING",
    re.I,
)
_PREFIXES = r"(?:VITE_|NEXT_PUBLIC_|REACT_APP_|EXPO_PUBLIC_)"
ENV_SUFFIXES = SRC + ENVFILE


def _public_name(f: SourceFile, m: re.Match, t: str) -> dict | None:
    name = m.group(0)
    if _PUBLIC_OK.search(name) or _PROVIDERS.search(name):
        return None
    return {"snippet": name}


public_secret_name = line_rule(
    "public-prefix-secret-name",
    "secret_exposure",
    "high",
    "rewrite",
    "A setting that looks secret has a name that sends it to every visitor.",
    "Rename it without the public prefix and read it only on the server. Rotate the key if it shipped.",
    pattern=re.compile(
        rf"\b{_PREFIXES}\w*(?:SECRET|PRIVATE|SERVICE_ROLE|PASSWORD|TOKEN|API_?KEY|_SK|CREDENTIAL)\w*",
        re.I,
    ),
    suffixes=ENV_SUFFIXES,
    refine=_public_name,
    skip_scripts=False,
)

_KEY_VALUE = (
    r"sk-(?:proj-|ant-)?[A-Za-z0-9_\-]{20,}|sk_live_[A-Za-z0-9]{20,}|rk_live_[A-Za-z0-9]{20,}"
    r"|whsec_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,}"
    r"|xox[abprs]-[A-Za-z0-9\-]{10,}|SG\.[\w\-]{22}\.[\w\-]{43}|sb_secret_[A-Za-z0-9_\-]{20,}"
)


def _env_value(f: SourceFile, m: re.Match, t: str) -> dict | None:
    return {"snippet": f"{t.split('=', 1)[0].strip()}=[hidden]"}


public_secret_value = line_rule(
    "public-prefix-secret-value",
    "secret_exposure",
    "high",
    "rewrite",
    "The value of a public setting is a private key.",
    "Move the key to a server-only variable and rotate it. Public-prefixed values ship to every browser.",
    pattern=re.compile(rf"^\s*{_PREFIXES}\w+\s*=\s*['\"]?(?:{_KEY_VALUE})", re.M),
    suffixes=ENVFILE,
    refine=_env_value,
    skip_scripts=False,
)

_KEY_SRC = re.compile(
    r"\bsk-(?:proj-|ant-)?(?=[A-Za-z0-9_\-]*\d)[A-Za-z0-9_\-]{20,}|sk_live_[A-Za-z0-9]{20,}|rk_live_[A-Za-z0-9]{20,}"
    r"|whsec_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{50,}"
    r"|xox[abprs]-[A-Za-z0-9\-]{10,}|SG\.[\w\-]{22}\.[\w\-]{43}|sb_secret_[A-Za-z0-9_\-]{20,}"
    r"|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----|sk_test_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_\-]{35}"
)
_PLACEHOLDER = re.compile(
    r"your|xxx|example|placeholder|changeme|\.\.\.|<|dummy|fake|test_key", re.I
)


def _key_refine(f: SourceFile, m: re.Match, t: str) -> dict | None:
    if _PLACEHOLDER.search(t):
        return None
    return {"severity": "low"} if m.group(0).startswith(("sk_test_", "AIza")) else {}


key_in_source = line_rule(
    "key-pattern-in-source",
    "secret_exposure",
    "high",
    "rewrite",
    "A real key sits in a code file.",
    "Remove the key, rotate it, and read it from a server-side environment variable.",
    pattern=_KEY_SRC,
    suffixes=SRC + SQL + ENVFILE + (".json", ".toml", ".yaml", ".yml", ".html"),
    refine=_key_refine,
    skip_scripts=False,
    per_file=5,
)

_SECRET_ENV_NAME = re.compile(r"SECRET|KEY|TOKEN|PASSWORD|DATABASE_URL|SERVICE_ROLE|PRIVATE", re.I)
_PUBLIC_VAL_NAME = re.compile(r"PUBLISHABLE|ANON|PROJECT_ID|SUPABASE_URL|_URL$|PUBLIC", re.I)
_ENV_NAME = re.compile(r"\.env(?:\.[\w.]+)?")
_ENV_SKIP = re.compile(r"example|sample|template|dist")
_ENV_LINE = re.compile(r"\s*(?:export\s+)?([A-Z][A-Z0-9_]*)\s*=\s*['\"]?([^'\"\s#]{9,})")


def _env_committed(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in files:
        name = f.path.rsplit("/", 1)[-1]
        if not _ENV_NAME.fullmatch(name) or _ENV_SKIP.search(name):
            continue
        for i, line in enumerate(f.lines, 1):
            m = _ENV_LINE.match(line)
            if (
                not m
                or not _SECRET_ENV_NAME.search(m.group(1))
                or _PUBLIC_VAL_NAME.search(m.group(1))
            ):
                continue
            if _PLACEHOLDER.search(m.group(2)):
                continue
            yield rule.finding(f, i, f"{m.group(1)}=[hidden]")
            break


env_committed = custom_rule(
    "env-file-committed",
    "secret_exposure",
    "high",
    "check",
    "A file with secret settings sits in the project folder. It may be in the saved history.",
    "Run git ls-files for it. If tracked, rotate every key in it and remove it from history.",
    _env_committed,
    ENVFILE,
)

_VITE_SERVER_ENV = re.compile(
    r"import\.meta\.env\.(?!VITE_|MODE\b|DEV\b|PROD\b|BASE_URL\b|SSR\b)\w+"
)
_NEXT_SERVER_ENV = re.compile(r"process\.env\.(?!NEXT_PUBLIC_|NODE_ENV\b)\w+")
_USE_CLIENT = re.compile(r"""^\s*['"]use client['"]""", re.M)


def _server_env(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in files:
        if f.suffix not in UI or is_noise(f.path) or not is_client(f):
            continue
        patterns = [_VITE_SERVER_ENV]
        if _USE_CLIENT.search(f.text[:400]):
            patterns.append(_NEXT_SERVER_ENV)
        for pattern in patterns:
            for m in pattern.finditer(f.text):
                ln = line_of(f.text, m.start())
                if f.lines[ln - 1].strip().startswith("//"):
                    continue
                yield rule.finding(f, ln, f.lines[ln - 1])


server_env_client = custom_rule(
    "server-env-read-in-client",
    "secret_exposure",
    "medium",
    "rewrite",
    "A browser file reads a private setting. The browser gets nothing, so the feature fails.",
    "Read this variable in server code and pass the result to the page. Only public-prefixed names reach browsers.",
    _server_env,
    UI,
)

vite_define = line_rule(
    "vite-define-env-leak",
    "secret_exposure",
    "medium",
    "check",
    "The build config copies all settings into the page.",
    "Pass only the named public values through define. Never pass the whole process.env.",
    pattern=re.compile(
        r"define\s*:\s*\{[^}]*process\.env\s*[:}]|'process\.env'\s*:\s*(?:process\.env|JSON\.stringify\(env\))"
    ),
    suffixes=UI,
    allow_config=True,
)

secret_fallback = line_rule(
    "secret-default-fallback",
    "secret_exposure",
    "medium",
    "rewrite",
    "The code has a built-in backup secret, so a missing setting goes unnoticed.",
    "Remove the fallback and fail at startup when the secret is missing.",
    pattern=re.compile(
        r"(?:process\.env\.\w*(?:KEY|SECRET|TOKEN|PASSWORD|JWT)\w*|import\.meta\.env\.\w*(?:KEY|SECRET|TOKEN|PASSWORD|JWT)\w*)"
        r"\s*(?:\|\||\?\?)\s*['\"][^'\"]{12,}['\"]"
        r"|os\.(?:environ\.get|getenv)\(\s*['\"]\w*(?:KEY|SECRET|TOKEN|PASSWORD|JWT)\w*['\"]\s*,\s*['\"][^'\"]{12,}['\"]\s*\)"
    ),
    suffixes=SRC,
)

RULES: list[Rule] = [
    public_secret_name,
    public_secret_value,
    key_in_source,
    env_committed,
    server_env_client,
    vite_define,
    secret_fallback,
]
