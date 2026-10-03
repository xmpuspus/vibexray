"""History reader tests. The sessions are real Claude Code and Codex runs on a corpus repo."""

import json
import shutil
from pathlib import Path

import pytest

from vibexray.history import read_history

FIXTURES = Path(__file__).parent / "fixtures" / "sessions"
ROOT = Path("/home/pm/sample-bot")
ASKED = (
    "In this support bot, refunds over 100 dollars must need a manager's approval, "
    "and only paid customers can request a refund. Point to where the code would change. "
    "Do not edit files."
)


@pytest.fixture
def homes(monkeypatch):
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(FIXTURES / "claude"))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(FIXTURES / "codex"))


@pytest.fixture
def only_claude(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(FIXTURES / "claude"))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(tmp_path / "no-codex"))


@pytest.fixture
def only_codex(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(tmp_path / "no-claude"))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(FIXTURES / "codex"))


def test_none_mode_skips_even_when_chats_exist(homes):
    h = read_history(ROOT, "none")
    assert h.source == "none"
    assert h.prompts == []
    assert "no-history" in h.note


def test_claude_reader_finds_the_pm_prompt(only_claude):
    h = read_history(ROOT, "auto")
    assert h.source == "claude-code"
    assert h.sessions == 1
    assert [p.text for p in h.prompts] == [ASKED]
    assert h.prompts[0].when == "2026-10-03"


def test_codex_reader_finds_the_pm_prompt_and_skips_the_subagent(only_codex):
    h = read_history(ROOT, "auto")
    assert h.source == "codex"
    # The second rollout file is a helper agent Codex spawned, not the PM.
    assert h.sessions == 1
    assert [p.text for p in h.prompts] == [ASKED]
    assert h.prompts[0].when == "2026-10-03"


def test_both_sources_merge_in_time_order(homes):
    h = read_history(ROOT, "auto")
    assert h.source == "claude-code+codex"
    assert h.sessions == 2
    assert len(h.prompts) == 2
    assert [p.when for p in h.prompts] == sorted(p.when for p in h.prompts)


def test_other_folder_matches_nothing(homes):
    h = read_history(Path("/home/pm/some-other-app"), "auto")
    assert h.source == "none"
    assert h.sessions == 0
    assert h.prompts == []
    assert "No Claude Code or Codex chat found" in h.note


def test_missing_homes_return_none_with_note(monkeypatch, tmp_path):
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(tmp_path / "a"))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(tmp_path / "b"))
    h = read_history(ROOT, "auto")
    assert h.source == "none"
    assert h.note


def test_no_tool_output_or_agent_text_leaks_into_prompts(homes):
    h = read_history(ROOT, "auto")
    blob = "\n".join(p.text for p in h.prompts)
    # Words that only appear in tool results, the injected AGENTS.md block, or agent replies.
    for leak in ("<INSTRUCTIONS>", "AGENTS.md", "tool_result", "system-reminder", "executor.ts"):
        assert leak not in blob
    assert all(len(p.text) <= 600 for p in h.prompts)


def test_codex_session_of_other_cwd_is_never_read(tmp_path, monkeypatch):
    # Copy the real codex tree, then change the cwd on the first line of every file.
    dest = tmp_path / "codex"
    shutil.copytree(FIXTURES / "codex", dest)
    for f in dest.rglob("rollout-*.jsonl"):
        lines = f.read_text().splitlines()
        meta = json.loads(lines[0])
        meta["payload"]["cwd"] = "/home/pm/elsewhere"
        f.write_text("\n".join([json.dumps(meta), *lines[1:]]) + "\n")
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(tmp_path / "no-claude"))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(dest))
    assert read_history(ROOT, "auto").source == "none"


def _claude_home_with_prompt(tmp_path, new_text):
    """Copy the real Claude session and swap the typed prompt text."""
    src = next((FIXTURES / "claude" / "projects").glob("*/*.jsonl"))
    dest_dir = tmp_path / "claude" / "projects" / src.parent.name
    dest_dir.mkdir(parents=True)
    out = []
    for line in src.read_text().splitlines():
        d = json.loads(line)
        if d["type"] == "user" and isinstance(d["message"]["content"], str):
            d["message"]["content"] = new_text
        out.append(json.dumps(d))
    (dest_dir / src.name).write_text("\n".join(out) + "\n")
    return tmp_path / "claude"


def test_secret_in_prompt_is_hidden(tmp_path, monkeypatch):
    key = "sk-" + "A1b2C3d4" * 4
    home = _claude_home_with_prompt(
        tmp_path, f"Use this key {key} for the bot. Refunds are manual."
    )
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(home))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(tmp_path / "no-codex"))
    h = read_history(ROOT, "auto")
    text = h.prompts[0].text
    assert key not in text
    assert "[hidden]" in text
    assert "Refunds are manual." in text


def test_long_prompt_is_capped_at_600(tmp_path, monkeypatch):
    home = _claude_home_with_prompt(tmp_path, "word " * 400)
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(home))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(tmp_path / "no-codex"))
    h = read_history(ROOT, "auto")
    assert 0 < len(h.prompts[0].text) <= 600


def test_injected_text_inside_a_prompt_is_stripped(tmp_path, monkeypatch):
    home = _claude_home_with_prompt(
        tmp_path,
        "<system-reminder>internal notes</system-reminder>Only paid users can refund.",
    )
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(home))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(tmp_path / "no-codex"))
    h = read_history(ROOT, "auto")
    assert h.prompts[0].text == "Only paid users can refund."
