"""Read the PM's own build chat for this project. The history builder fills this in."""

from __future__ import annotations

from pathlib import Path

from vibexray.model import History


def read_history(root: Path, mode: str) -> History:
    if mode == "none":
        return History(source="none", note="Skipped: the scan ran with --no-history.")
    return History(source="none", note="No Claude Code or Codex chat found for this folder.")
