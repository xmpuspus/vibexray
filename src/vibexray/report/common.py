"""Words and counts that report.html and handoff.md share, so the two never disagree."""

from __future__ import annotations

import re
from collections import defaultdict

from vibexray.model import CATEGORIES, Finding, ScanResult
from vibexray.rules.base import SECRET_VALUE

LABEL_NAMES = {"keep": "Keep", "rewrite": "Rewrite", "throwaway": "Throw away", "check": "Check"}
LABEL_MEANING = {
    "keep": "Real code. Your engineer can build on it.",
    "rewrite": "The idea is real, but the code is not ready. Your engineer rebuilds it.",
    "throwaway": "Demo only. It shows sample data or fakes an action. Remove it before launch.",
    "check": "vibexray is not sure about these. A person must look at each one.",
}
SOURCE_NAMES = {"claude-code": "Claude Code", "codex": "Codex"}
SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n:,} {one if n == 1 else many or one + 's'}"


# A key starts a word. Without this guard, a path like "risk-enhanced" reads as an "sk-" key.
KEY = re.compile(r"(?<![A-Za-z0-9])(?:" + SECRET_VALUE.pattern + ")")


def hide_secrets(text: str) -> str:
    # Rules redact snippets already. This second pass covers every other string.
    return KEY.sub(lambda m: m.group(0)[:6] + "...[hidden]", text)


def parts_with(result: ScanResult, fake: bool) -> int:
    return len({f.file for f in result.findings if (f.group == "fake") == fake})


def headline(result: ScanResult) -> str:
    app = result.app_name
    if result.files_scanned == 0:
        return f"vibexray found no app code in {app}."
    fake, risky = parts_with(result, True), parts_with(result, False)
    if not fake and not risky:
        return f"vibexray found no fake parts and nothing that can break in {app}."
    if not fake:
        return f"{plural(risky, 'part')} of {app} can break. vibexray found no fake parts."
    first = f"{plural(fake, 'part')} of {app} {'is' if fake == 1 else 'are'} fake."
    if not risky:
        return f"{first} vibexray found nothing that can break."
    return f"{first} {risky:,} can break."


def chat_source(source: str) -> str:
    names = [SOURCE_NAMES.get(s, s) for s in source.split("+") if s and s != "none"]
    return " and ".join(names)


def by_group(result: ScanResult, group: str) -> list[Finding]:
    return [f for f in result.findings if f.group == group]


def found_by(f: Finding) -> str:
    if f.source != "review":
        return "Found by a rule"
    if f.verified:
        return "Found by AI review, line checked"
    return "Found by AI review, line not checked"


def cards(findings: list[Finding]) -> list[list[Finding]]:
    """One card per rule, message, and source, worst first, then the most places first."""
    grouped: dict[tuple[str, str, str], list[Finding]] = defaultdict(list)
    for f in findings:
        grouped[(f.rule_id, f.pm_text, found_by(f))].append(f)
    return sorted(
        grouped.values(),
        key=lambda fs: (SEVERITY_RANK.get(fs[0].severity, 3), -len(fs), fs[0].pm_text),
    )


def category_name(f: Finding) -> str:
    return CATEGORIES[f.category][0]
