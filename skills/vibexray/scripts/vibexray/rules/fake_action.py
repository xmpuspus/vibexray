"""Buttons and messages that do nothing real."""

from __future__ import annotations

import re
from collections.abc import Iterable

from vibexray.model import Finding
from vibexray.rules.ai import tools_in
from vibexray.rules.base import Rule
from vibexray.rules.util import (
    NETWORK,
    SRC,
    UI,
    code_only,
    custom_rule,
    enclosing_function,
    function_bodies,
    line_of,
    line_rule,
    live,
)
from vibexray.walker import SourceFile

_SUCCESS = re.compile(
    r"set(?:Success|Submitted|Sent|Saved|Done|Complete)\w*\(|toast(?:\.success)?\(|setStatus\(['\"](?:success|sent|done)",
)
_TIMER = re.compile(r"\bsetTimeout\(")
_AWAIT_TIMER = re.compile(
    r"await\s+new\s+Promise\(\s*\(?\w*\)?\s*=>\s*setTimeout\(\s*\w*\s*,\s*\d{3,5}\s*\)\s*\)"
)
_HANDLER_NAME = re.compile(r"^(?:handle|on[A-Z]|submit|send|save|login|checkout)", re.I)


def _handler_for(f: SourceFile, pos: int) -> str | None:
    """Body text of the named function around pos, or a 12-line window when there is none."""
    code = code_only(f.text)
    fn = enclosing_function(f.text, pos)
    if fn is not None:
        return code[fn[1] : fn[2]]
    ln = line_of(f.text, pos)
    lines = code.splitlines()
    return "\n".join(lines[max(0, ln - 12) : ln + 10])


def _in_demo(f: SourceFile, pos: int) -> bool:
    """A wait inside a function named for demo mode paces a labeled demo, not a fake save."""
    fn = enclosing_function(f.text, pos)
    return bool(fn and re.search("demo", fn[0], re.I))


def _settimeout_success(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, UI):
        code = code_only(f.text)
        for m in _TIMER.finditer(code):
            ln = line_of(f.text, m.start())
            region = "\n".join(code.splitlines()[ln - 1 : ln + 10])
            if not _SUCCESS.search(region):
                continue
            body = _handler_for(f, m.start())
            if body is None or NETWORK.search(body) or _in_demo(f, m.start()):
                continue
            yield rule.finding(f, ln, f.lines[ln - 1])


settimeout_success = custom_rule(
    "settimeout-success",
    "fake_action",
    "high",
    "throwaway",
    "The button waits a moment, then says done. Nothing went out.",
    "Replace the timer with the real request. Show success only after the server confirms.",
    _settimeout_success,
    UI,
)

promise_resolve = line_rule(
    "promise-resolve-success",
    "fake_action",
    "high",
    "throwaway",
    "A function claims success and does no work.",
    "Implement the call this function stands in for. Return success only after real work finishes.",
    pattern=re.compile(
        r"Promise\.resolve\(\s*\{\s*(?:success|ok|status)\s*:\s*(?:true|['\"](?:ok|success)['\"])"
        r"|\bresolve\(\s*\{\s*success"
        r"|(?:async\s+function\s+\w+\s*\([^)]*\)|async\s*\([^)]*\)\s*=>)\s*\{\s*return\s*\{\s*(?:success|ok)\s*:\s*true\s*\}"
    ),
    suffixes=UI,
)


_AWAIT_PROMISE = re.compile(r"await\s+new\s+Promise\(\s*\(?\w*\)?\s*=>\s*setTimeout\([^)]*\)\s*\)")
_REAL_WORK = re.compile(r"\bawait\b|clipboard|\bcopy|download|\.then\(|\bprint\(")
_TOAST_CALL = re.compile(r"\b(?:toast(?:\.success)?|notify|message\.success|alert)\(")
_OK_WORD = re.compile(r"saved|sent|submitted|created|updated|deleted|booked", re.I)


def _toast_without_network(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, UI):
        code = code_only(f.text)
        for name, a, b in function_bodies(f.text):
            if not _HANDLER_NAME.match(name):
                continue
            body = _AWAIT_PROMISE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), code[a:b])
            if NETWORK.search(body) or _REAL_WORK.search(body):
                continue
            for m in _TOAST_CALL.finditer(body):
                near = f.text[a + m.start() : a + m.start() + 160]
                if _OK_WORD.search(near):
                    ln = line_of(f.text, a + m.start())
                    yield rule.finding(f, ln, f.lines[ln - 1])
                    break


toast_no_network = custom_rule(
    "toast-without-network",
    "fake_action",
    "high",
    "rewrite",
    "The screen shows a saved message, but the app made no request.",
    "Call the real API in this handler. Show the success message only after it returns.",
    _toast_without_network,
    UI,
)

console_send = line_rule(
    "console-log-as-send",
    "fake_action",
    "high",
    "rewrite",
    "The send action only prints text in a developer console.",
    "Replace the console log with the real send call, such as an email or payment API.",
    pattern=re.compile(
        r"console\.log\(['\"`](?:sending|submitting|saving|email|order|payment|form)", re.I
    ),
    suffixes=UI,
    absent=re.compile(r"\bfetch\(|axios|supabase|\.post\(|sendMail|nodemailer"),
)

_TODO = re.compile(
    r"//\s*(?:TODO|FIXME)\b[^\n]*|/\*\s*(?:TODO|FIXME)\b|onClick=\{\s*\(\)\s*=>\s*\{\s*\}\s*\}"
    r"|onSubmit=\{\s*\(\)\s*=>\s*\{\s*\}\s*\}|#\s*(?:TODO|FIXME)\b[^\n]*|raise NotImplementedError"
    r"|alert\(['\"][^'\"]*(?:coming soon|demo|not implemented)",
    re.I,
)


def _todo(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    tool_spans: dict[str, list[tuple[int, int]]] = {}
    for t in tools_in(files):
        for hf, a, b in t.handlers:
            tool_spans.setdefault(hf.path, []).append((a, b))
    for f in live(files, SRC):
        spans = tool_spans.get(f.path, [])
        seen = 0
        for m in _TODO.finditer(f.text):
            # A TODO inside an AI tool body belongs to the fake-tool rule.
            if any(a <= m.start() <= b for a, b in spans):
                continue
            ln = line_of(f.text, m.start())
            yield rule.finding(f, ln, f.lines[ln - 1])
            seen += 1
            if seen >= 3:
                break


todo_handler = custom_rule(
    "todo-handler-body",
    "fake_action",
    "medium",
    "rewrite",
    "A button handler or tool is empty or says to do later.",
    "Implement the TODO body. Until then, the feature only looks finished.",
    _todo,
    SRC,
)

fake_delay = custom_rule(
    "fake-delay-loader",
    "fake_action",
    "medium",
    "throwaway",
    "A loading spinner runs on a timer, not on real work.",
    "Remove the fixed wait. Tie the loading state to the real request.",
    lambda r, files: _fake_delay(r, files),
    UI,
)


def _fake_delay(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, UI):
        for m in _AWAIT_TIMER.finditer(code_only(f.text)):
            fn = enclosing_function(f.text, m.start())
            if (
                fn is None
                or NETWORK.search(code_only(f.text)[fn[1] : fn[2]])
                or _in_demo(f, m.start())
            ):
                continue
            ln = line_of(f.text, m.start())
            yield rule.finding(f, ln, f.lines[ln - 1])


_ROUTE_OK = re.compile(
    r"export\s+async\s+function\s+(?:POST|PUT|PATCH|DELETE)\s*\([^)]*\)\s*\{\s*"
    r"return\s+(?:NextResponse|Response)\.json\(\s*\{\s*(?:ok|success)\s*:\s*true"
)
route_ok = line_rule(
    "route-returns-ok-only",
    "fake_action",
    "high",
    "rewrite",
    "The server endpoint says ok and does nothing else.",
    "Add the database write or outbound call this route stands in for before it returns ok.",
    pattern=_ROUTE_OK,
    suffixes=UI,
    server=True,
)

ls_backend = line_rule(
    "localstorage-as-backend",
    "fake_action",
    "medium",
    "rewrite",
    "Data that belongs on a server stays in the visitor's browser.",
    "Store business records in a database. Browser storage is lost when the visitor clears it.",
    pattern=re.compile(
        r"(?:local|session)Storage\.setItem\(\s*['\"](?:orders?|users?|cart|invoices?|messages?|tickets?|leads?|bookings?|todos?)['\"]"
    ),
    suffixes=UI,
    absent=re.compile(r"\bfetch\(|supabase|axios"),
)

RULES: list[Rule] = [
    settimeout_success,
    promise_resolve,
    toast_no_network,
    console_send,
    todo_handler,
    fake_delay,
    route_ok,
    ls_backend,
]
