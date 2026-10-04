"""History reader tests. The sessions are real Claude Code and Codex runs on a corpus repo."""

import json
import shutil
from pathlib import Path

import pytest
from conftest import POSIX_SESSIONS

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


@POSIX_SESSIONS
def test_claude_reader_finds_the_pm_prompt(only_claude):
    h = read_history(ROOT, "auto")
    assert h.source == "claude-code"
    assert h.sessions == 1
    assert [p.text for p in h.prompts] == [ASKED]
    assert h.prompts[0].when == "2026-10-03"


@POSIX_SESSIONS
def test_codex_reader_finds_the_pm_prompt_and_skips_the_subagent(only_codex):
    h = read_history(ROOT, "auto")
    assert h.source == "codex"
    # The second rollout file is a helper agent Codex spawned, not the PM.
    assert h.sessions == 1
    assert [p.text for p in h.prompts] == [ASKED]
    assert h.prompts[0].when == "2026-10-03"


@POSIX_SESSIONS
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


@POSIX_SESSIONS
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


@POSIX_SESSIONS
def test_long_prompt_is_capped_at_600(tmp_path, monkeypatch):
    home = _claude_home_with_prompt(tmp_path, "word " * 400)
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(home))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(tmp_path / "no-codex"))
    h = read_history(ROOT, "auto")
    assert 0 < len(h.prompts[0].text) <= 600


@POSIX_SESSIONS
def test_injected_text_inside_a_prompt_is_stripped(tmp_path, monkeypatch):
    home = _claude_home_with_prompt(
        tmp_path,
        "<system-reminder>internal notes</system-reminder>Only paid users can refund.",
    )
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(home))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(tmp_path / "no-codex"))
    h = read_history(ROOT, "auto")
    assert h.prompts[0].text == "Only paid users can refund."


@pytest.mark.parametrize(
    "text",
    [
        '<teammate-message teammate_id="b-review" summary="Review done">The review is ready.'
        "</teammate-message>",
        "<task-notification><task-id>b0phjst2y</task-id><status>completed</status>"
        "</task-notification>",
    ],
)
def test_agent_team_messages_are_not_pm_prompts(tmp_path, monkeypatch, text):
    # Claude Code agent teams and background tasks write these as user turns.
    home = _claude_home_with_prompt(tmp_path, text)
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(home))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(tmp_path / "no-codex"))
    assert read_history(ROOT, "auto").prompts == []


def test_prompts_that_ask_for_vibexray_are_not_build_chat(tmp_path, monkeypatch):
    # A PM who runs the skill again in the same folder must not see that request as a rule.
    home = _claude_home_with_prompt(tmp_path, "Is this support bot ready? Run vibexray on it.")
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(home))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(tmp_path / "no-codex"))
    assert read_history(ROOT, "auto").prompts == []


@POSIX_SESSIONS
def test_key_block_pasted_in_a_prompt_is_hidden_across_its_lines(tmp_path, monkeypatch):
    begin, end = "-----BEGIN " + "PRIVATE KEY-----", "-----END " + "PRIVATE KEY-----"
    body = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldY"
    home = _claude_home_with_prompt(
        tmp_path, f"Use this key:\n{begin}\n{body}\n{end}\nOnly admins can export."
    )
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(home))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(tmp_path / "no-codex"))
    text = read_history(ROOT, "auto").prompts[0].text
    assert body not in text
    assert "Only admins can export." in text


def _claude_home_with_records(tmp_path, changes):
    """Copy the real Claude session, then add one user record per change to its first prompt."""
    src = next((FIXTURES / "claude" / "projects").glob("*/*.jsonl"))
    dest_dir = tmp_path / "claude" / "projects" / src.parent.name
    dest_dir.mkdir(parents=True)
    records = [json.loads(line) for line in src.read_text().splitlines()]
    first = next(d for d in records if d["type"] == "user")
    out = []
    for change in changes:
        d = json.loads(json.dumps(first))
        d["message"]["content"] = change.pop("content")
        d.update(change)
        out.append(json.dumps(d))
    (dest_dir / src.name).write_text("\n".join(out) + "\n")
    return tmp_path / "claude"


@POSIX_SESSIONS
def test_a_folder_with_the_same_claude_folder_name_reads_nothing(homes):
    # Claude Code names both /home/pm/sample-bot and /home/pm/sample_bot "-home-pm-sample-bot".
    # The records say cwd /home/pm/sample-bot, so a scan of sample_bot must not show them.
    assert read_history(Path("/home/pm/sample_bot"), "auto").prompts == []
    assert read_history(ROOT, "auto").prompts


@POSIX_SESSIONS
def test_summaries_and_shell_output_are_not_pm_words(tmp_path, monkeypatch):
    home = _claude_home_with_records(
        tmp_path,
        [
            {
                "content": "Summary: the user said only admins must refund.",
                "isCompactSummary": True,
            },
            {"content": "Earlier turns, shown for context.", "isVisibleInTranscriptOnly": True},
            {"content": "<bash-input>cat .env</bash-input>"},
            {
                "content": "<bash-stdout>DB_PASS=hunter2pass</bash-stdout><bash-stderr></bash-stderr>"
            },
            {"content": "Refunds over 100 dollars need a manager."},
        ],
    )
    monkeypatch.setenv("VIBEXRAY_CLAUDE_HOME", str(home))
    monkeypatch.setenv("VIBEXRAY_CODEX_HOME", str(tmp_path / "no-codex"))
    texts = [p.text for p in read_history(ROOT, "auto").prompts]
    assert texts == ["Refunds over 100 dollars need a manager."]
