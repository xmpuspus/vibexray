"""Rule contract. A rule turns source files into findings with a file and a line."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from vibexray.model import Finding
from vibexray.walker import SourceFile

SNIPPET_MAX = 160
SECRET_VALUE = re.compile(
    r"(sk-[A-Za-z0-9_\-]{8,}|sk_live_[A-Za-z0-9]{8,}|eyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}"
    r"|AKIA[0-9A-Z]{12,}|ghp_[A-Za-z0-9]{20,}|xox[bap]-[A-Za-z0-9\-]{10,})"
)


def redact(text: str) -> str:
    """Hide anything that looks like a key, and cap the length."""
    text = SECRET_VALUE.sub(lambda m: m.group(0)[:6] + "...[hidden]", text.strip())
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
