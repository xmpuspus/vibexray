"""Turn findings and the build chat into questions the PM answers before handoff."""

from __future__ import annotations

from vibexray.model import Finding, History, Question


def build_questions(findings: list[Finding], history: History) -> list[Question]:
    return []
