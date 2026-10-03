"""Start the prototype and record what it does. The app-run builder fills this in."""

from __future__ import annotations

from pathlib import Path

from vibexray.model import AppRun


def run_app(root: Path, out_dir: Path, enabled: bool) -> AppRun:
    if not enabled:
        return AppRun(state="not_attempted", reason="Skipped: the scan ran with --no-run.")
    return AppRun(state="not_attempted", reason="App run is not built yet.")
