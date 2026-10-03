"""Read the PM's own build chat for this folder, from Claude Code and Codex."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from vibexray.model import History, Prompt
from vibexray.rules.base import redact

PROMPT_MAX = 600

# Text the tools inject into a user turn. The PM did not type any of it.
_INJECTED_PREFIXES = (
    "<command-",
    "<local-command",
    "<system-reminder",
    "<environment_context",
    "<user_instructions",
    "<user_action",
    "<turn_aborted",
    "<skill",
    "<teammate-message",
    "<task-notification",
    "# AGENTS.md instructions",
    "Caveat:",
    "[Request interrupted",
    "Base directory for this skill",
)
_SELF = re.compile(r"\bvibe\s?x-?ray\b", re.I)
_REMINDER_BLOCK = re.compile(r"<(system-reminder|local-command-[a-z]+)>.*?</\1>", re.S)


@dataclass
class _Chat:
    when: str
    text: str


def _home(env: str, default: str) -> Path:
    return Path(os.environ.get(env) or Path.home() / default)


def _clean(text: str) -> str:
    text = _REMINDER_BLOCK.sub("", text).strip()
    if not text or text.startswith(_INJECTED_PREFIXES):
        return ""
    # A request to run vibexray itself is not part of the build.
    if _SELF.search(text):
        return ""
    # redact() also truncates, so hide secrets word by word and cap the whole prompt after.
    text = " ".join(redact(word) for word in text.split())
    return text if len(text) <= PROMPT_MAX else text[: PROMPT_MAX - 3] + "..."


def _day(stamp: object) -> str:
    return stamp[:10] if isinstance(stamp, str) and len(stamp) >= 10 else ""


def _root_forms(root: Path) -> list[str]:
    """The folder as the tools may have recorded it: as given, and with symlinks resolved."""
    forms = [os.path.abspath(root)]
    try:
        real = str(root.resolve())
    except OSError:
        real = forms[0]
    if real not in forms:
        forms.append(real)
    return forms


def _claude_dir_name(path: str) -> str:
    # Claude Code names a project folder after the path, with every
    # character outside [A-Za-z0-9] turned into "-".
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def _text_of(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_result":
            return ""
        if block.get("type") in ("text", "input_text"):
            parts.append(str(block.get("text", "")))
    return "\n".join(parts)


def _jsonl(path: Path) -> list[dict]:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if isinstance(d, dict):
            out.append(d)
    return out


def _read_claude_session(path: Path) -> list[_Chat]:
    chats = []
    for d in _jsonl(path):
        if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
            continue
        message = d.get("message")
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        text = _clean(_text_of(message.get("content")))
        if text:
            chats.append(_Chat(_day(d.get("timestamp")), text))
    return chats


def _claude_sessions(root: Path) -> list[list[_Chat]]:
    projects = _home("VIBEXRAY_CLAUDE_HOME", ".claude") / "projects"
    out = []
    for name in sorted({_claude_dir_name(p) for p in _root_forms(root)}):
        folder = projects / name
        if not folder.is_dir():
            continue
        for f in sorted(folder.glob("*.jsonl")):
            chats = _read_claude_session(f)
            if chats:
                out.append(chats)
    return out


def _first_line(path: Path) -> dict | None:
    try:
        with path.open(errors="replace") as fh:
            first = json.loads(fh.readline())
    except (OSError, ValueError):
        return None
    return first if isinstance(first, dict) else None


def _read_codex_session(path: Path) -> list[_Chat]:
    chats = []
    for d in _jsonl(path)[1:]:
        p = d.get("payload")
        if d.get("type") != "response_item" or not isinstance(p, dict):
            continue
        if p.get("type") != "message" or p.get("role") != "user":
            continue
        text = _clean(_text_of(p.get("content")))
        if text:
            chats.append(_Chat(_day(d.get("timestamp")), text))
    return chats


def _codex_sessions(root: Path) -> list[list[_Chat]]:
    sessions = _home("VIBEXRAY_CODEX_HOME", ".codex") / "sessions"
    if not sessions.is_dir():
        return []
    forms = set(_root_forms(root))
    out = []
    for f in sorted(sessions.rglob("rollout-*.jsonl")):
        # Read only the first line until the folder matches.
        meta = _first_line(f)
        payload = meta.get("payload") if meta else None
        if not isinstance(payload, dict) or payload.get("cwd") not in forms:
            continue
        # A helper agent that Codex started on its own is not the PM typing.
        source = payload.get("source")
        if isinstance(source, dict) and "subagent" in source:
            continue
        chats = _read_codex_session(f)
        if chats:
            out.append(chats)
    return out


def read_history(root: Path, mode: str) -> History:
    if mode == "none":
        return History(source="none", note="Skipped: the scan ran with --no-history.")
    claude = _claude_sessions(root)
    codex = _codex_sessions(root)
    if not claude and not codex:
        return History(source="none", note="No Claude Code or Codex chat found for this folder.")
    source = "+".join(name for name, found in (("claude-code", claude), ("codex", codex)) if found)
    chats = sorted((c for s in claude + codex for c in s), key=lambda c: c.when)
    count = len(claude) + len(codex)
    return History(
        source=source,
        sessions=count,
        prompts=[Prompt(when=c.when, text=c.text) for c in chats],
        note=f"{len(chats)} of your own prompts from {count} chat(s) for this folder.",
    )
