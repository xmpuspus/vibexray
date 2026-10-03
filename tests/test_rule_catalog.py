import re

from conftest import run_cli

from vibexray.model import CATEGORIES, LABELS, SEVERITIES
from vibexray.rules import all_rules

WORD = re.compile(r"\S+")


def test_catalog_has_every_rule_family():
    ids = {r.id for r in all_rules()}
    assert len(ids) >= 70
    for needed in ("mock-array-literal", "rls-missing", "ai-browser-sdk", "xss-html-injection"):
        assert needed in ids


def test_rule_ids_are_unique():
    ids = [r.id for r in all_rules()]
    assert len(ids) == len(set(ids))


def test_every_category_label_and_severity_is_known():
    for r in all_rules():
        assert r.category in CATEGORIES, r.id
        assert r.label in LABELS, r.id
        assert r.severity in SEVERITIES, r.id


def test_texts_are_short_and_plain():
    for r in all_rules():
        assert 0 < len(WORD.findall(r.pm_text)) <= 20, (r.id, r.pm_text)
        assert 0 < len(WORD.findall(r.engineer_text)) <= 25, (r.id, r.engineer_text)
        for text in (r.pm_text, r.engineer_text):
            assert "—" not in text, r.id
            assert "–" not in text, r.id


def test_every_category_has_a_rule():
    used = {r.category for r in all_rules()}
    for cat in (
        "mock_data",
        "fake_action",
        "auth_gap",
        "database_rules",
        "secret_exposure",
        "hardcoded_config",
        "ai_browser_call",
        "ai_tool_unbounded",
        "ai_prompt_only_rule",
        "ai_no_human_review",
        "ai_fake_tool",
        "security_other",
    ):
        assert cat in used, cat


def test_rules_command_lists_every_rule():
    out = run_cli("rules")
    assert out.returncode == 0, out.stderr
    for r in all_rules():
        assert r.id in out.stdout, r.id
