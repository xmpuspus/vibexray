"""Load real fixture files and run one rule on them."""

from pathlib import Path

from vibexray.model import Finding
from vibexray.rules import all_rules
from vibexray.walker import SourceFile

FIXTURES = Path(__file__).parent / "fixtures"


def fx(key: str) -> SourceFile:
    """A fixture keeps the original repo path, so path rules see the real path."""
    text = (FIXTURES / key).read_text(encoding="utf-8")
    return SourceFile(path=key.split("/", 1)[1], text=text)


def rule(rule_id: str):
    return next(r for r in all_rules() if r.id == rule_id)


def run(rule_id: str, *keys: str) -> list[Finding]:
    return rule(rule_id).run([fx(k) for k in keys])


def hit_with(rule_id: str, snippet: str, *keys: str) -> list[Finding]:
    """Findings whose snippet contains the text copied from the real file."""
    return [f for f in run(rule_id, *keys) if snippet in f.snippet]
