"""Rule contract. A rule turns source files into findings with a file and a line."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from vibexray.model import Finding
from vibexray.walker import SourceFile

SNIPPET_MAX = 160
HIDDEN = "[hidden]"
# The lookbehind keeps words such as "task-runner" and "risk-enhanced" visible.
SECRET_VALUE = re.compile(
    r"(?<![A-Za-z0-9])(sk-[A-Za-z0-9_\-]{8,}|[sr]k_(?:live|test)_[A-Za-z0-9]{8,}"
    r"|eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}"
    r"|AKIA[0-9A-Z]{12,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[abprs]-[A-Za-z0-9\-]{10,}"
    r"|whsec_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|SG\.[A-Za-z0-9_\-]{16,}|sb_secret_[A-Za-z0-9_\-]{8,}|AIza[0-9A-Za-z_\-]{20,})"
)
# The whole block, header to footer. A key pasted on one line ends at the end of the text.
PRIVATE_KEY = re.compile(
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?(?:-----END [A-Z ]*PRIVATE KEY-----|\Z)", re.S
)
# postgres://admin:PASSWORD@host keeps the user and the host and hides the password.
URL_PASSWORD = re.compile(r"(\b[a-z][a-z0-9+.\-]*://[^\s:/@'\"`]+:)([^\s@'\"`/]+)(@)", re.I)
_NAME = r"(?:secret|token|passw(?:or)?d|pwd|api_?key|private_?key|access_?key|credentials?)"
# A quoted literal assigned to a key-like name: apiKey = "...", jwtSecret: '...'.
NAMED_LITERAL = re.compile(rf"(\b\w*{_NAME}\w*['\"]?\s*[:=]\s*)(['\"`])([^'\"`\s]{{4,}})\2", re.I)
# A .env line such as ADMIN_PASSWORD=value. Upper case only, so JS code stays readable.
ENV_ASSIGN = re.compile(
    r"^(\s*(?:export\s+)?[A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|PWD|API_KEY|APIKEY"
    r"|PRIVATE_KEY|ACCESS_KEY|CREDENTIALS?)[A-Z0-9_]*\s*=\s*)(\S.*)$",
    re.M,
)
# jwt.sign(payload, 'literal') and process.env.JWT_SECRET || 'literal'.
SIGNING_LITERAL = re.compile(r"(\bjwt\.(?:sign|verify)\([^)]*?,\s*)(['\"`])([^'\"`]+)\2")
FALLBACK_LITERAL = re.compile(
    r"((?:process\.env|import\.meta\.env)\.\w*(?:KEY|SECRET|TOKEN|PASSWORD|JWT)\w*\s*"
    r"(?:\|\||\?\?)\s*)(['\"`])([^'\"`]+)\2"
    r"|(os\.(?:environ\.get|getenv)\(\s*['\"]\w*(?:KEY|SECRET|TOKEN|PASSWORD|JWT)\w*['\"]\s*,\s*)"
    r"(['\"])([^'\"]+)\5",
    re.I,
)
ENV_LINE = re.compile(r"^(\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_.\-]*\s*[=:]\s*).*$")
ENV_EXAMPLES = (".example", ".sample", ".template", ".dist", ".defaults")


def _quoted(m: re.Match) -> str:
    return f"{m.group(1)}{m.group(2)}{HIDDEN}{m.group(2)}"


def _fallback(m: re.Match) -> str:
    if m.group(1) is not None:
        return f"{m.group(1)}{m.group(2)}{HIDDEN}{m.group(2)}"
    return f"{m.group(4)}{m.group(5)}{HIDDEN}{m.group(5)}"


def hide(text: str) -> str:
    """Hide key and password values anywhere in the text. Every output goes through this."""
    text = PRIVATE_KEY.sub("[private key hidden]", text)
    text = SECRET_VALUE.sub(lambda m: m.group(0)[:6] + "..." + HIDDEN, text)
    text = URL_PASSWORD.sub(lambda m: m.group(1) + HIDDEN + m.group(3), text)
    text = ENV_ASSIGN.sub(lambda m: m.group(1) + HIDDEN, text)
    text = NAMED_LITERAL.sub(_quoted, text)
    text = SIGNING_LITERAL.sub(_quoted, text)
    return FALLBACK_LITERAL.sub(_fallback, text)


def is_env_file(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name.startswith(".env") and not name.endswith(ENV_EXAMPLES)


def hide_env_line(line: str) -> str:
    """A line of a real .env file keeps its name only. Any value there can be private."""
    return ENV_LINE.sub(lambda m: m.group(1) + HIDDEN, line)


def redact(text: str) -> str:
    """Hide key and password values, and cap the length."""
    text = hide(text.strip())
    return text if len(text) <= SNIPPET_MAX else text[: SNIPPET_MAX - 3] + "..."


@dataclass(frozen=True)
class Rule:
    id: str
    category: str
    severity: str
    label: str
    pm_text: str
    engineer_text: str
    pattern: re.Pattern | None = None
    suffixes: tuple[str, ...] = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte")
    path_skip: tuple[str, ...] = ()
    check: Callable[[list[SourceFile]], Iterable[Finding]] | None = field(
        default=None, compare=False
    )

    def applies_to(self, f: SourceFile) -> bool:
        if any(part in f.path for part in self.path_skip):
            return False
        if f.path.split("/")[-1].startswith(".env") and ".env" in self.suffixes:
            return True
        return f.suffix in self.suffixes

    def finding(self, f: SourceFile, line: int, snippet: str, **extra) -> Finding:
        if is_env_file(f.path):
            snippet = hide_env_line(snippet)
        if extra.get("related_snippet"):
            related = extra["related_snippet"]
            if is_env_file(extra.get("related_file") or ""):
                related = hide_env_line(related)
            extra["related_snippet"] = redact(related)
        return Finding(
            rule_id=self.id,
            category=self.category,
            severity=self.severity,
            file=f.path,
            line=line,
            snippet=redact(snippet),
            pm_text=extra.pop("pm_text", self.pm_text),
            engineer_text=extra.pop("engineer_text", self.engineer_text),
            label=extra.pop("label", self.label),
            **extra,
        )

    def run(self, files: list[SourceFile]) -> list[Finding]:
        if self.check is not None:
            return list(self.check(files))
        out: list[Finding] = []
        if self.pattern is None:
            return out
        for f in files:
            if not self.applies_to(f):
                continue
            for i, line in enumerate(f.lines, start=1):
                if self.pattern.search(line):
                    out.append(self.finding(f, i, line))
        return out
