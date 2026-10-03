"""Pages and actions with no login check."""

from __future__ import annotations

import re
from collections.abc import Iterable

from vibexray.model import Finding
from vibexray.rules.base import Rule
from vibexray.rules.util import (
    ENVFILE,
    SRC,
    UI,
    code_only,
    custom_rule,
    function_bodies,
    is_noise,
    line_of,
    line_rule,
    live,
)
from vibexray.walker import SourceFile

_GUARD_STRONG = re.compile(
    r"getUser\b|getSession\b|\bauth\(\)|getServerSession|currentUser|redirect\(|notFound\(|requireAuth|requireAdmin"
    r"|requireRole|getCurrentUser|verifyToken|withAuth|\bsession\b|\bcookies\(\)"
)
_GUARD_WEAK = re.compile(
    r"useUser|useSession|useAuth|ProtectedRoute|RequireAuth|navigate\(|router\.push"
)
_ADMIN_PAGE = re.compile(
    r"(^|/)(admin|dashboard|settings|billing|manage|internal|backoffice)(/|\.|$)", re.I
)
_PAGE_FILE = re.compile(
    r"(^|/)app/.*page\.(tsx|jsx|ts|js)$|(^|/)pages/.*\.(tsx|jsx|vue)$|(^|/)src/(routes|views)/.*\.(tsx|jsx|vue|svelte)$"
)
_ALWAYS_SENSITIVE = re.compile(r"(^|/)(admin|billing|backoffice)(/|\.|$)", re.I)
_LOGIN_PAGE = re.compile(r"(^|/)(login|signin|sign-in|signup|register|auth)(/|\.|$)", re.I)
_WRAPPER = re.compile(r"<(?:Protected|Private|Require|Admin)\w*Route\b")


def _guarded_by_chain(f: SourceFile, files: list[SourceFile]) -> bool:
    folder = f.path.rsplit("/", 1)[0] if "/" in f.path else ""
    for other in files:
        name = other.path.rsplit("/", 1)[-1]
        if not re.match(r"(layout|_layout|middleware)\.(tsx|ts|jsx|js)$", name):
            continue
        odir = other.path.rsplit("/", 1)[0] if "/" in other.path else ""
        covers = name.startswith("middleware") or folder == odir or folder.startswith(odir + "/")
        if covers and _GUARD_STRONG.search(code_only(other.text)):
            return True
    return False


def _admin_route(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    wrapper = any(_WRAPPER.search(f.text) for f in files if not is_noise(f.path))
    repo_auth = any(
        _GUARD_STRONG.search(code_only(f.text)) or _GUARD_WEAK.search(f.text) for f in live(files)
    )
    for f in live(files, UI + (".vue", ".svelte")):
        if not _PAGE_FILE.search(f.path) or not _ADMIN_PAGE.search(f.path):
            continue
        if _LOGIN_PAGE.search(f.path) or (not repo_auth and not _ALWAYS_SENSITIVE.search(f.path)):
            continue
        code = code_only(f.text)
        if _GUARD_STRONG.search(code) or _guarded_by_chain(f, files):
            continue
        weak = bool(_GUARD_WEAK.search(code))
        fnd = rule.finding(f, 1, f.lines[0] if f.lines else f.path)
        if weak or wrapper:
            fnd.severity = "medium"
            fnd.label = "check"
            fnd.engineer_text = (
                "Only a browser check guards this page. Add a server-side session and role check."
            )
        yield fnd


admin_route = custom_rule(
    "admin-route-no-guard",
    "auth_gap",
    "high",
    "rewrite",
    "An admin page opens for anyone who types the address.",
    "Read the session on the server for this route and reject non-admins. Check layout and middleware too.",
    _admin_route,
    UI + (".vue", ".svelte"),
)

_ROLE_LINE = re.compile(
    r"\b(?:isAdmin|is_admin|isSuperuser|isStaff|isOwner)\s*[:=]\s*(?:true\b|True\b)"
    r"|\brole\s*[:=]\s*['\"](?:admin|owner|superuser)['\"](?!\s*\|)"
    r"|\b(?:const|let)\s+(?:user|currentUser|session)\s*=\s*\{[^}\n]*(?:email|id|role)"
)


def _role_ok(f: SourceFile, m: re.Match, t: str) -> dict | None:
    if re.search(
        r"where\s*:|\.eq\(|filter|count\(|\.find\(|=>|:\s*['\"]\w+['\"]\s*\|", t
    ) and "role" in m.group(0):
        return None
    return {}


hardcoded_role = line_rule(
    "hardcoded-role-or-user",
    "auth_gap",
    "high",
    "rewrite",
    "The code decides who the user is from a typed-in value.",
    "Read the user and role from the verified session. Remove fixed admin flags and fixed user objects.",
    pattern=_ROLE_LINE,
    suffixes=SRC,
    refine=_role_ok,
)

_PW = re.compile(
    r"(?<!typeof )\bpassword\s*(?:===|==|!==|!=)\s*['\"`](?!(?:string|undefined|object|number)['\"`])[^'\"`]+['\"`]"
    r"|['\"`][^'\"`]{4,}['\"`]\s*(?:===|==)\s*\w*password\b"
    r"|\bpassword\s*==\s*['\"][^'\"]+['\"]"
)
client_password = line_rule(
    "client-password-check",
    "auth_gap",
    "high",
    "rewrite",
    "The code checks the password against a typed-in value. Anyone can read it.",
    "Check passwords on the server against a salted hash. Never compare with a literal.",
    pattern=_PW,
    suffixes=SRC,
)

_AUTH_FLAG = re.compile(
    r"\b(?:SKIP_AUTH|DISABLE_AUTH|AUTH_DISABLED|NO_AUTH|BYPASS_AUTH|AUTH_BYPASS|DEV_AUTH|DEMO_MODE|FAKE_AUTH|MOCK_AUTH)\b"
    r"|requireAuth\s*[:=]\s*false|^\s*verify_jwt\s*=\s*false",
    re.I | re.M,
)
auth_flag = line_rule(
    "auth-disabled-flag",
    "auth_gap",
    "high",
    "check",
    "A switch can turn the login off.",
    "Check that production ignores this flag. Edge functions with the JWT check off need their own caller check.",
    pattern=_AUTH_FLAG,
    suffixes=SRC + ENVFILE + (".toml",),
    refine=lambda f, m, t: {"severity": "medium"} if "verify_jwt" in t else {},
    per_file=5,
)

ls_gate = line_rule(
    "localstorage-auth-gate",
    "auth_gap",
    "high",
    "rewrite",
    "The app trusts a value the visitor can edit in the browser.",
    "Decide access from a server-verified session. A browser flag can be changed by anyone.",
    pattern=re.compile(
        r"localStorage\.getItem\(\s*['\"](?:isLoggedIn|isAuthenticated|loggedIn|isAdmin|role|user|auth)['\"]\)"
        r"|document\.cookie[^\n]*(?:admin|loggedIn)="
    ),
    suffixes=UI,
)

_LOGIN_NAME = re.compile(r"^(?:login|signIn|handleLogin|handleSignIn|authenticate|onLogin)$")
_AUTH_CALL = re.compile(
    r"signInWith\w*|supabase|\bfetch\(|axios|\bauth\.|\bapi\.|mutate|\blogin\(|signIn\("
)
_SETS_USER = re.compile(r"setUser\(|setIsAuthenticated\(\s*true|navigate\(|setIsLoggedIn\(\s*true")


def _fake_login(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, UI):
        code = code_only(f.text)
        for name, a, b in function_bodies(f.text):
            if not _LOGIN_NAME.match(name):
                continue
            body = code[a:b]
            if _AUTH_CALL.search(body) or not _SETS_USER.search(body):
                continue
            if not re.search(r"===\s*['\"]|==\s*['\"]", f.text[a:b]):
                continue
            ln = line_of(f.text, a)
            yield rule.finding(f, ln, f.lines[ln - 1])


fake_login = custom_rule(
    "fake-login-handler",
    "auth_gap",
    "high",
    "throwaway",
    "The login form accepts a typed-in account and never asks a server.",
    "Send credentials to a real auth service. Remove the literal comparison.",
    _fake_login,
    UI,
)

_WRITE_ROUTE = re.compile(
    r"export\s+(?:async\s+)?function\s+(?:POST|PUT|PATCH|DELETE)\b|export\s+const\s+(?:POST|PUT|PATCH|DELETE)\b"
    r"|\b(?:app|router)\.(?:post|put|patch|delete)\(|@(?:app|router)\.(?:post|put|patch|delete)\("
)
_DATA_CALL = re.compile(
    r"\.(?:insert|update|upsert|delete|create|save|execute)\(|\bdb\.|prisma\.|supabase|sendMail|sendEmail|resend"
    r"|nodemailer"
)
_AUTH_WORDS = re.compile(
    r"getUser|getSession|\bauth\(|getServerSession|jsonwebtoken|\bjose\b|Authorization|req\.user|Depends\("
    r"|current_user|login_required|requireAdmin|requireRole|requireAuth|require_\w+|verifyToken|withAuth"
    r"|authenticate|getCurrentUser|\bsession\b|bearer",
    re.I,
)
_PUBLIC_ROUTE = re.compile(
    r"chat|contact|webhook|subscribe|public|waitlist|newsletter|login|register|signup|callback|auth|rate-limit|health|ping"
)
_TAKES_INPUT = re.compile(r"req\.json\(|formData\(|searchParams|req\.text\(|await req\b")
_FN_JWT_OFF = re.compile(r"^\[functions\.([\w-]+)\]\s*\n\s*verify_jwt\s*=\s*false", re.M)


def _api_no_auth(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    open_fns: set[str] = set()
    for f in files:
        if f.path.endswith("supabase/config.toml"):
            open_fns |= set(_FN_JWT_OFF.findall(f.text))
    for f in live(files, SRC):
        p = f.path.lower()
        is_edge = "supabase/functions/" in p
        is_route = bool(re.search(r"(^|/)route\.(ts|js)$|(^|/)pages/api/|(^|/)api/", p))
        if is_edge:
            fn = p.split("supabase/functions/")[1].split("/")[0]
            if fn.startswith("_") or fn not in open_fns:
                continue
        elif not (
            is_route
            or f.suffix == ".py"
            or re.search(r"\b(?:app|router)\.(?:post|put|patch|delete)\(", f.text)
        ):
            continue
        code = code_only(f.text)
        wm = _WRITE_ROUTE.search(code)
        if (not wm and not is_edge) or not _DATA_CALL.search(code) or _AUTH_WORDS.search(code):
            continue
        if is_edge and (not _TAKES_INPUT.search(code) or _PUBLIC_ROUTE.search(p)):
            continue
        ln = line_of(f.text, wm.start()) if wm else 1
        fnd = rule.finding(f, ln, f.lines[ln - 1] if f.lines else f.path)
        if _PUBLIC_ROUTE.search(p) or f.suffix == ".py":
            fnd.severity = "medium"
            fnd.label = "check"
            fnd.engineer_text = "Public by design? Then add a rate limit and input checks. Otherwise add a session check."
        yield fnd


api_no_auth = custom_rule(
    "api-route-no-auth",
    "auth_gap",
    "high",
    "rewrite",
    "A server endpoint that changes data does not check who calls it.",
    "Read the session or token in this handler and reject anonymous callers before the write.",
    _api_no_auth,
    SRC,
)

role_gate = line_rule(
    "client-only-role-gate",
    "auth_gap",
    "medium",
    "check",
    "The page hides a button from non-admins, but the server may still allow the action.",
    "Enforce the same role check on the server or in database rules. A hidden button is not a guard.",
    pattern=re.compile(
        r"(?:user|profile|session)\??\.(?:role|is_admin|isAdmin)\s*(?:===|==)\s*['\"]?(?:admin|true)['\"]?\s*&&"
    ),
    suffixes=UI,
)

RULES: list[Rule] = [
    admin_route,
    hardcoded_role,
    client_password,
    auth_flag,
    ls_gate,
    fake_login,
    api_no_auth,
    role_gate,
]
