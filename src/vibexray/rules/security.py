"""Other security risks that a PM never sees but an attacker finds."""

from __future__ import annotations

import re
from collections.abc import Iterable

from vibexray.model import Finding
from vibexray.rules.ai import _LLM_CALL
from vibexray.rules.auth import _AUTH_WORDS
from vibexray.rules.base import Rule
from vibexray.rules.util import (
    ENVFILE,
    SQL,
    SRC,
    UI,
    code_only,
    custom_rule,
    is_server,
    line_of,
    line_rule,
    live,
    match_close,
)
from vibexray.walker import SourceFile

CAT = "security_other"


_UNTRUSTED = re.compile(
    r"message|content|text|html|markdown|reply|answer|response|comment|body|input|prompt|completion"
    r"|output|summary|description|query|review|post",
    re.I,
)
_SANITIZER = re.compile(r"escapeHtml|escape_html|escapeHTML|sanitize|DOMPurify|he\.encode")


def _untrusted_variable(f: SourceFile, start: int, end: int) -> bool:
    """A template placeholder or a name that looks like user or model text."""
    code = code_only(f.text)[start:end]
    names = re.sub(r"""['"`\\\s+()]""", "", code)
    if "${" in f.text[start:end]:
        names += f.text[start:end]
    return bool(_UNTRUSTED.search(names))


def _xss_refine(f: SourceFile, m: re.Match, t: str) -> dict | None:
    if _SANITIZER.search(f.text):
        return None
    if m.group("val") is not None:
        value = m.group("val")
        if "JSON.stringify" in value:
            return None
        return {} if _untrusted_variable(f, m.start("val"), m.end("val")) else None
    if m.group("val3") is not None:
        return {}
    code = code_only(f.text)
    start = m.start("val2")
    stop = code.find(";", start)
    stop = len(code) if stop == -1 else min(stop, start + 3000)
    return {} if _untrusted_variable(f, start, stop) else None


xss = line_rule(
    "xss-html-injection",
    CAT,
    "high",
    "rewrite",
    "Text from users or the AI is inserted into the page as HTML. A crafted message can run code.",
    "Render as text, or sanitize with DOMPurify before using innerHTML or dangerouslySetInnerHTML.",
    pattern=re.compile(
        r"(?P<hit>dangerouslySetInnerHTML)\s*=\s*\{\{\s*__html\s*:\s*(?P<val>[^}]*)"
        r"|(?P<hit2>\.innerHTML)\s*=\s*(?P<val2>[^\n]*)|v-html\s*=\s*(?P<val3>\"[^\"]*\")"
    ),
    suffixes=UI + (".vue", ".html"),
    refine=_xss_refine,
    skip_scripts=False,
    per_file=3,
)


def _code_rule(
    rid: str, severity: str, label: str, pm: str, eng: str, rx: re.Pattern, suffixes=SRC
) -> Rule:
    """A regex on code with strings and comments blanked, so words in text never match."""

    def fn(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
        for f in live(files, suffixes):
            for m in rx.finditer(code_only(f.text)):
                ln = line_of(f.text, m.start())
                yield rule.finding(f, ln, f.lines[ln - 1])

    return custom_rule(rid, CAT, severity, label, pm, eng, fn, suffixes)


eval_rule = _code_rule(
    "eval-or-new-function",
    "high",
    "rewrite",
    "The code runs text as a program. Anyone who controls that text controls the app.",
    "Remove eval and new Function. Parse data with JSON.parse or call a fixed function.",
    re.compile(r"(?<![\w.$])eval\s*\(|\bnew\s+Function\s*\("),
)

_WILDCARD = re.compile(
    r"""origin\s*:\s*['"]\*['"]|Access-Control-Allow-Origin['"]?\s*[:,]\s*['"]\*['"]""", re.I
)
_CREDS = re.compile(
    r"""credentials\s*:\s*true|Access-Control-Allow-Credentials['"]?\s*[:,]\s*['"]?true""", re.I
)


def _cors(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, SRC):
        if not _CREDS.search(f.text):
            continue
        for m in _WILDCARD.finditer(f.text):
            ln = line_of(f.text, m.start())
            yield rule.finding(f, ln, f.lines[ln - 1])


cors = custom_rule(
    "cors-wildcard-credentials",
    CAT,
    "high",
    "rewrite",
    "Any website can call this server with a visitor's login.",
    "List the exact allowed origins. Never combine a wildcard origin with credentials.",
    _cors,
)

sql_concat = line_rule(
    "sql-string-concat",
    CAT,
    "high",
    "rewrite",
    "A database query is built by joining text, so a crafted input can read or wipe data.",
    "Use parameterized queries or the ORM query builder. Never join user input into SQL text.",
    pattern=re.compile(
        r"(?:query|execute|raw|\$queryRawUnsafe|unsafe)\w*\(\s*(?:`[^`]*\b(?:select|insert|update|delete)\b[^`]*\$\{"
        r"|['\"][^'\"]*\b(?:select|insert|update|delete)\b[^'\"]*['\"]\s*\+|f['\"][^'\"]*\b(?:select|insert|update|delete)\b[^'\"]*\{)",
        re.I,
    ),
    suffixes=SRC,
)

_TOKEN_KEY = re.compile(r"token|jwt|api[_-]?key|(?<![a-z])auth(?![a-z])", re.I)
_TOKEN_VALUE = re.compile(r"token|jwt|api[_-]?key", re.I)

ls_token = line_rule(
    "token-in-localstorage",
    CAT,
    "medium",
    "check",
    "The login token is kept where any script on the page can read it.",
    "Use an httpOnly, secure cookie for session tokens. Browser storage is open to XSS.",
    pattern=re.compile(
        r"(?:local|session)Storage\.setItem\(\s*(?P<key>[^,)]+),\s*(?P<val>[^)\n]*)"
    ),
    suffixes=UI,
    refine=lambda f, m, t: (
        {} if _TOKEN_KEY.search(m.group("key")) or _TOKEN_VALUE.search(m.group("val")) else None
    ),
)

_PAY_URL = r"""['"`][^'"`]*(?:checkout|payment|charge|pay|stripe|order)[^'"`]*['"`]"""
trusted_amount = line_rule(
    "client-trusted-amount",
    CAT,
    "high",
    "rewrite",
    "The page sends the price to the payment step. A visitor can change it.",
    "Look up prices on the server from product IDs. Ignore any amount that the browser sends.",
    pattern=re.compile(
        rf"fetch\(\s*{_PAY_URL}[^;]{{0,300}}?body\s*:\s*JSON\.stringify\(\s*\{{[^}}]*?\b(?P<hit>amount|price|total|unit_amount)\b\s*[:,}}]"
        r"|invoke\(\s*['\"][^'\"]*(?:checkout|payment|charge|pay)[^'\"]*['\"][^;]{0,300}?\b(?P<hit2>amount|price|total)\b\s*[:,}]",
        re.S,
    ),
    suffixes=UI,
    client=True,
)

open_redirect = line_rule(
    "open-redirect",
    CAT,
    "medium",
    "rewrite",
    "A link can send visitors to any other site after login. Phishing pages use this.",
    "Allow only relative paths or a fixed list of hosts for redirect targets.",
    pattern=re.compile(
        r"(?:res\.redirect|NextResponse\.redirect|redirect|location\.(?:href|replace|assign)|window\.location(?:\.href)?)"
        r"\s*(?:\(|=)\s*(?:req\.(?:query|body)\.\w+|searchParams\.get\([^)]*\)|params\.\w+|query\.\w+)"
    ),
    suffixes=SRC,
    absent=re.compile(r"""startsWith\(['"]/['"]\)|allowlist|ALLOWED_|isSafeRedirect"""),
)

_DEBUG_PATH = re.compile(r"(^|/)(app|pages)/api/(debug|test|dev|seed|_debug)(/|\.)")
_DEBUG_ROUTE = re.compile(
    r"""(?:app|router)\.(?:get|post|all|use)\(\s*['"]/(?:debug|test|dev|__debug|_debug|seed|admin/seed)\b"""
    r"""|@(?:app|router)\.(?:get|post)\(\s*['"]/(?:debug|test|seed)\b"""
)


def _debug(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in files:
        if f.suffix not in SRC or re.search(r"\.(?:test|spec)\.", f.path):
            continue
        if _DEBUG_PATH.search(f.path):
            yield rule.finding(f, 1, f.lines[0] if f.lines else f.path)
            continue
        for m in _DEBUG_ROUTE.finditer(f.text):
            ln = line_of(f.text, m.start())
            yield rule.finding(f, ln, f.lines[ln - 1])


debug_route = custom_rule(
    "debug-route-left-on",
    CAT,
    "medium",
    "check",
    "A test or debug page is still reachable on the live site.",
    "Remove debug and seed routes, or guard them with an admin check and a development-only flag.",
    _debug,
)

_ROUTE = re.compile(
    r"(app/api|pages/api|supabase/functions|(^|/)routes?/|controllers?/|route\.(ts|js))|@Post\(|@Controller"
    r"|\b(?:app|router)\.(?:post|get)\(|\bserve\(|@(?:app|router)\.(?:post|get)\(",
)
_LIMITER = re.compile(
    r"ratelimit|rate-limit|rate_limit|slowapi|Limiter|throttle|quota|upstash", re.I
)
_LOGIN_PATH = re.compile(r"(login|signin|sign-in|password|auth/token)", re.I)


def _no_rate_limit(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, SRC):
        if not is_server(f) or _LIMITER.search(f.text) or not _ROUTE.search(f.path + "\n" + f.text):
            continue
        code = code_only(f.text)
        llm = _LLM_CALL.search(code)
        login = _LOGIN_PATH.search(f.path) and re.search(r"route\.(?:ts|js)$|api/", f.path.lower())
        if not (llm or login) or _AUTH_WORDS.search(code) and not login:
            continue
        ln = line_of(f.text, llm.start()) if llm else 1
        yield rule.finding(f, ln, f.lines[ln - 1] if f.lines else f.path)


no_rate_limit = custom_rule(
    "ai-endpoint-no-rate-limit",
    CAT,
    "medium",
    "rewrite",
    "Anyone can call this AI or login endpoint as often as they like. That can run up costs.",
    "Add a per-user or per-IP rate limit and a daily quota before the model call or login check.",
    _no_rate_limit,
)

weak_jwt = line_rule(
    "weak-jwt-secret",
    CAT,
    "high",
    "rewrite",
    "The key that signs logins is a short or typed-in word. Attackers can forge logins.",
    "Load a long random JWT secret from the environment. Never allow the none algorithm.",
    pattern=re.compile(
        r"""jwt\.sign\([^)]*,\s*['"][^'"]+['"]"""
        r"""|\bjwt_?secret\w*\s*[:=]\s*['"][^'"]{1,}['"]"""
        r"""|algorithms?\s*[:=]\s*\[?\s*['"]none['"]"""
        r"""|^\s*JWT_SECRET\s*=\s*['"]?(?:change|secret|test|dev|password|123)""",
        re.I | re.M,
    ),
    suffixes=SRC + ENVFILE,
    skip_scripts=False,
)

tls_off = line_rule(
    "tls-checks-off",
    CAT,
    "high",
    "rewrite",
    "The app skips the check that proves a server is who it claims to be.",
    "Turn certificate checks back on. Add the issuer certificate instead of disabling verification.",
    pattern=re.compile(
        r"rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*[=:]\s*['\"]?0|verify\s*=\s*False"
        r"|InsecureSkipVerify\s*:\s*true"
    ),
    suffixes=SRC + ENVFILE,
    skip_scripts=False,
)

_COOKIE_CALL = re.compile(
    r"(?:res\.cookie|cookies\(\)\.set|response\.cookies\.set|cookies\.set|set_cookie)\("
)
_AUTH_COOKIE = re.compile(r"token|session|auth|jwt|\bsid\b", re.I)


def _cookies(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, SRC):
        code = code_only(f.text)
        for m in _COOKIE_CALL.finditer(code):
            end = match_close(code, m.end() - 1)
            if end is None:
                continue
            args_raw = f.text[m.end() : end]
            if not _AUTH_COOKIE.search(args_raw):
                continue
            low = args_raw.lower()
            if "httponly" in low and "secure" in low:
                continue
            ln = line_of(f.text, m.start())
            yield rule.finding(f, ln, f.lines[ln - 1])


cookie_flags = custom_rule(
    "cookie-missing-flags",
    CAT,
    "medium",
    "rewrite",
    "A login cookie can be read by page scripts or sent over plain HTTP.",
    "Set httpOnly, secure, and sameSite on session cookies.",
    _cookies,
)

_URL_NAMES = r"url|uri|link|target|endpoint|imageUrl|fileUrl|webhookUrl"
_REQ_URL = re.compile(
    rf"(?:const|let)\s*\{{[^}}]*\b({_URL_NAMES})\b[^}}]*\}}\s*=\s*(?:await\s+)?(?:req|request)\.json\(\)"
    rf"|(?:const|let)\s+({_URL_NAMES})\s*=\s*(?:body|req\.body|req\.query|params)\.\w+"
    rf"|(?:const|let)\s+({_URL_NAMES})\s*=\s*[\w.]*searchParams\.get\("
)
_SAFE_HOST = re.compile(
    r"allowlist|ALLOWED_HOSTS|isPrivateIp|isPublicUrl|\.hostname\s*(?:===|!==|\.endsWith|\.includes)",
    re.I,
)


def _ssrf(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, SRC):
        if not is_server(f) or _SAFE_HOST.search(f.text):
            continue
        code = code_only(f.text)
        for m in _REQ_URL.finditer(f.text):
            name = next(g for g in m.groups() if g)
            call = re.search(rf"\b(?:fetch|axios(?:\.get)?|got)\(\s*{name}\b", code)
            if call:
                ln = line_of(f.text, call.start())
                yield rule.finding(f, ln, f.lines[ln - 1])
                break


ssrf = custom_rule(
    "ssrf-user-url",
    CAT,
    "high",
    "rewrite",
    "The server fetches any web address a visitor gives it. That can expose internal systems.",
    "Allow only known hosts, block private IP ranges, and do not follow redirects blindly.",
    _ssrf,
)

path_traversal = line_rule(
    "path-traversal",
    CAT,
    "high",
    "rewrite",
    "A visitor-supplied file name is used to open a file. They can read files outside the folder.",
    "Resolve the path, then check that it stays inside one allowed folder before opening it.",
    pattern=re.compile(
        r"(?:readFile(?:Sync)?|createReadStream|sendFile|readdir|unlink|writeFile(?:Sync)?)\(\s*"
        r"(?:path\.join\([^)\n]*|[^)\n]*?)(?:req\.(?:query|body|params)\.\w+|params\.\w+|query\.\w+|searchParams\.get\([^)]*\))"
    ),
    suffixes=SRC,
    absent=re.compile(r"startsWith\(|path\.resolve\([^)]*\)\.startsWith|normalize\(|basename\("),
)

firebase = line_rule(
    "firebase-open-rules",
    CAT,
    "high",
    "rewrite",
    "The Firebase rules let anyone read and write the whole database.",
    "Replace allow read, write: if true with rules that check request.auth and the document owner.",
    pattern=re.compile(
        r"allow\s+(?:read\s*,\s*write|read|write)\s*:\s*if\s+true|allow\s+read\s*,\s*write\s*;"
        r"|\"\.(?:read|write)\"\s*:\s*true"
    ),
    suffixes=(".rules", ".json"),
    skip_scripts=False,
)

public_bucket = line_rule(
    "public-storage-bucket",
    CAT,
    "medium",
    "check",
    "Files in this storage bucket can be opened by anyone with the link.",
    "Check that the bucket holds only public files. Use private buckets and signed URLs for user uploads.",
    pattern=re.compile(
        r"insert\s+into\s+storage\.buckets[^;]*?\btrue\b|createBucket\([^)]*public\s*:\s*true",
        re.I | re.S,
    ),
    suffixes=SQL + UI,
    skip_scripts=False,
)

_USERISH = r"(?:req\.|body\.|user\w*|input|message|query|prompt|name|\w*Name|\w*Input|email)"
prompt_injection = line_rule(
    "user-input-in-system-prompt",
    CAT,
    "medium",
    "check",
    "User-supplied text is joined into the AI's instructions. A visitor can rewrite the rules.",
    "Keep user text in the user message. Pass only checked values into the system prompt.",
    pattern=re.compile(
        rf"role\s*:\s*['\"]system['\"]\s*,\s*content\s*:\s*`[^`]*\$\{{\s*{_USERISH}"
        rf"|\b(?:system|systemPrompt|instructions)\s*[:=]\s*`[^`]*\$\{{\s*{_USERISH}",
        re.I,
    ),
    suffixes=UI,
    per_file=3,
)

RULES: list[Rule] = [
    xss,
    eval_rule,
    cors,
    sql_concat,
    ls_token,
    trusted_amount,
    open_redirect,
    debug_route,
    no_rate_limit,
    weak_jwt,
    tls_off,
    cookie_flags,
    ssrf,
    path_traversal,
    firebase,
    public_bucket,
    prompt_injection,
]
