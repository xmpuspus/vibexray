"""Rule registry. Each category module exposes RULES: list[Rule]."""

from __future__ import annotations

from vibexray.model import Finding
from vibexray.rules.base import Rule
from vibexray.walker import SourceFile


def all_rules() -> list[Rule]:
    from vibexray.rules import catalog

    return list(catalog.RULES)


def run_rules(files: list[SourceFile]) -> list[Finding]:
    findings: list[Finding] = []
    seen: set[tuple[str, str, int]] = set()
    for rule in all_rules():
        for f in rule.run(files):
            key = (f.rule_id, f.file, f.line)
            if key in seen:
                continue
            seen.add(key)
            findings.append(f)
    findings.sort(key=lambda f: (f.file, f.line, f.rule_id))
    return findings
