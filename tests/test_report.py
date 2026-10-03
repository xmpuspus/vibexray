"""Report tests. Every scan here runs the real rules on real prototype code."""

import copy
import dataclasses
import re
from html import escape, unescape
from pathlib import Path

import pytest
from conftest import corpus_repo
from test_history import ROOT, _claude_home_with_prompt

from vibexray.cli import scan
from vibexray.history import read_history
from vibexray.questions import build_questions
from vibexray.report import write_reports
from vibexray.report.html import render_html
from vibexray.report.markdown import render_markdown
from vibexray.rules.base import SECRET_VALUE as KEY

FIXTURES = Path(__file__).parent / "fixtures"
SESSIONS = FIXTURES / "sessions"
SECTIONS = ("decisions", "parts", "fake", "risks", "app", "chat", "engineer")


def scan_fixture(name: str, tmp_path: Path):
    return scan(FIXTURES / name, tmp_path / "out", run=False, history_mode="none")


def with_history(result, monkeypatch, claude_home: Path = SESSIONS / "claude"):
    """Attach the real build chat from the session fixtures to a real scan."""
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(claude_home))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(SESSIONS / "codex"))
    history = read_history(ROOT, "auto")
    assert history.prompts, "session fixtures gave no prompts"
    return dataclasses.replace(
        result, history=history, questions=build_questions(result.findings, history)
    )


def visible_text(html: str) -> str:
    html = re.sub(r"<(style|script)\b.*?</\1>", " ", html, flags=re.S)
    return unescape(re.sub(r"<[^>]+>", " ", html)).replace("\u00a0", " ")


def headline_text(html: str) -> str:
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S).group(1)
    return unescape(re.sub(r"<[^>]+>", "", h1)).replace("\u00a0", " ")


def own_copy(html: str, result) -> str:
    """Visible text minus everything that came from the scanned repo or the rules."""
    text = visible_text(html)
    data = [result.app_name, result.target, result.app_run.reason, result.history.note]
    for f in result.findings:
        data += [f.snippet, f.related_snippet or "", f.pm_text, f.engineer_text, f.file]
        data += [f.related_file or ""]
    for p in result.parts:
        data += [p.file, *p.reasons]
    for q in result.questions:
        data += [q.text, q.why, q.file or ""]
    data += [p.text for p in result.history.prompts]
    for item in sorted(filter(None, data), key=len, reverse=True):
        text = text.replace(item, " ")
    return text


@pytest.fixture
def sliceiq(tmp_path, monkeypatch):
    return with_history(scan_fixture("SliceIQ", tmp_path), monkeypatch)


@pytest.fixture
def empty(tmp_path):
    target = tmp_path / "empty-app"
    target.mkdir()
    return scan(target, tmp_path / "out", run=False, history_mode="none")


def test_full_report_has_every_section_with_a_heading(sliceiq):
    html = render_html(sliceiq)
    for sid in SECTIONS:
        block = re.search(rf'<section id="{sid}".*?</section>', html, re.S)
        assert block, sid
        assert re.search(r"<h2[^>]*>[^<]+</h2>", block.group(0)), sid


def test_headline_states_the_counts(sliceiq):
    html = render_html(sliceiq)
    fake = len({f.file for f in sliceiq.findings if f.group == "fake"})
    risky = len({f.file for f in sliceiq.findings if f.group != "fake"})
    h1 = headline_text(html)
    assert f"{fake} parts of SliceIQ are fake." in h1
    assert f"{risky} can break." in h1


def test_one_finding_uses_singular_copy(tmp_path):
    result = scan_fixture("ai-customer-support-agent", tmp_path)
    assert len(result.findings) == 1
    html = render_html(result)
    h1 = headline_text(html)
    assert "1 part of ai-customer-support-agent can break" in h1
    assert "1 parts" not in visible_text(html)


def test_every_finding_location_appears_in_both_documents(sliceiq):
    html, md = render_html(sliceiq), render_markdown(sliceiq)
    assert sliceiq.findings
    for f in sliceiq.findings:
        where = f"{f.file}:{f.line}"
        assert escape(where) in html, where
        assert where in md, where
        if f.related_file:
            assert f"{f.related_file}:{f.related_line}" in md


def test_snippets_are_escaped_not_rendered(sliceiq):
    html = render_html(sliceiq)
    tagged = [f for f in sliceiq.findings if "<" in f.snippet]
    assert tagged, "SliceIQ has a JSX snippet; the fixture changed"
    for f in tagged:
        assert escape(f.snippet) in html
        assert f.snippet not in html


def test_empty_scan_shows_explicit_text_in_every_section(empty):
    html = render_html(empty)
    text = visible_text(html)
    for phrase in (
        "No app code found",
        "No open questions found",
        "No fake parts found",
        "No security risks found",
        "No AI risks found",
        "The app did not run",
        "No build chat found",
        "handoff.md",
    ):
        assert phrase in text, phrase
    # An empty folder had nothing to check, so no sentence may claim a check.
    for claim in ("vibexray checked", "Send handoff.md to your engineer."):
        assert claim not in text, claim
    for sid in SECTIONS:
        block = re.search(rf'<section id="{sid}".*?</section>', html, re.S).group(0)
        assert len(visible_text(block).split()) > 8, sid


def test_no_decisions_state_when_findings_raise_no_question(tmp_path):
    result = scan_fixture("gpt-realtime-2-customer-support-voice-agent", tmp_path)
    assert result.findings and not result.questions
    assert "No open questions found" in visible_text(render_html(result))


def test_skipped_parts_say_vibexray_skipped_them(empty):
    text = visible_text(render_html(empty))
    assert "vibexray did not start the app" in text
    assert "vibexray skipped your build chat" in text


def test_a_prompt_sent_to_both_tools_shows_once_with_a_count(sliceiq):
    text = visible_text(render_html(sliceiq))
    prompt = sliceiq.history.prompts[0].text
    repeats = sum(p.text == prompt for p in sliceiq.history.prompts)
    assert repeats == 2, "the session fixtures hold the same prompt in Claude Code and Codex"
    assert text.count(prompt) == 1
    assert "You sent this 2 times." in text


def test_history_prompts_show_with_their_dates(sliceiq):
    text = visible_text(render_html(sliceiq))
    prompt = sliceiq.history.prompts[0]
    assert prompt.text in text
    assert prompt.when in text
    assert "Claude Code" in text


def test_no_secret_reaches_either_document(tmp_path, monkeypatch, sliceiq):
    key = "sk-" + "A1b2C3d4" * 4
    home = _claude_home_with_prompt(tmp_path, f"Use this key {key} for the bot.")
    result = with_history(scan_fixture("Snodrod__ai-support-agent", tmp_path), monkeypatch, home)
    for doc in (render_html(result), render_markdown(result), render_html(sliceiq)):
        assert key not in doc
        assert not KEY.search(doc)


def test_own_copy_has_no_dashes_or_semicolons(sliceiq, empty):
    for result in (sliceiq, empty):
        text = own_copy(render_html(result), result)
        assert "—" not in text and "–" not in text
        assert ";" not in text, text[max(0, text.find(";") - 80) : text.find(";") + 20]
        md = render_markdown(result)
        assert "—" not in md.replace(result.app_name, "")


def test_report_is_self_contained(sliceiq):
    html = render_html(sliceiq)
    assert not re.search(r"""(src|href)=["']?(https?:)?//""", html)
    assert "@import" not in html and "url(http" not in html
    assert '<meta name="viewport"' in html


def test_handoff_has_every_group_and_the_agent_section(sliceiq, empty):
    for result in (sliceiq, empty):
        md = render_markdown(result)
        assert md.startswith(f"# Handoff: {result.app_name}")
        for heading in (
            "## Parts map",
            "### Keep",
            "### Rewrite",
            "### Throw away",
            "### Check",
            "## Findings",
            "### Fake",
            "### Security",
            "### AI",
            "## What the app does",
            "## Open questions for the PM",
            "## Instructions for a coding agent",
        ):
            assert heading in md, (result.app_name, heading)
    md = render_markdown(empty)
    assert "No fake findings." in md
    assert "The app did not run." in md
    assert "No open questions." in md


def test_handoff_fences_hold_snippets_with_backticks(sliceiq):
    md = render_markdown(sliceiq)
    # Every fence opens and closes, so the count of fence lines is even.
    fences = [ln for ln in md.splitlines() if re.match(r"^`{3,}", ln)]
    assert fences and len(fences) % 2 == 0
    for f in sliceiq.findings:
        assert f.snippet in md


def test_every_card_and_finding_names_its_source(sliceiq):
    html, md = render_html(sliceiq), render_markdown(sliceiq)
    assert html.count("Found by a rule") == html.count('<article class="card')
    assert md.count("- Found by a rule.") == len(sliceiq.findings)


def test_review_findings_show_whether_the_line_was_checked(sliceiq):
    # No AI review output exists yet, so two real rule findings take the review source.
    # Their file, line, and snippet stay real. Only the source fields change.
    first, second = (copy.copy(f) for f in sliceiq.findings[:2])
    first.source, first.verified = "review", True
    second.source, second.verified = "review", False
    result = dataclasses.replace(sliceiq, findings=[first, second, *sliceiq.findings[2:]])
    html, md = render_html(result), render_markdown(result)
    for doc in (html, md):
        assert "Found by AI review, line checked" in doc
        assert "Found by AI review, line not checked" in doc
    assert "Found by a rule" in html


def test_write_reports_writes_the_new_documents(sliceiq, tmp_path):
    paths = write_reports(sliceiq, tmp_path / "out")
    assert "<h1" in paths["html"].read_text()
    assert "## Instructions for a coding agent" in paths["markdown"].read_text()


@pytest.mark.corpus
@pytest.mark.parametrize("name", ["yana-contabila", "Snodrod__ai-support-agent", "SliceIQ"])
def test_corpus_reports_carry_every_location(name, tmp_path):
    result = scan(corpus_repo(name), tmp_path / "out", run=False, history_mode="none")
    html, md = render_html(result), render_markdown(result)
    for f in result.findings:
        assert escape(f"{f.file}:{f.line}") in html
        assert f"{f.file}:{f.line}" in md
    for p in result.parts:
        assert escape(p.file) in html
    assert not KEY.search(html + md)
