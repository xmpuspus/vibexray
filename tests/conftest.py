import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CORPUS_DIR = Path(os.environ.get("VIBEXRAY_CORPUS", REPO / ".cache" / "corpus"))


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONPATH": str(REPO / "src"), "NO_COLOR": "1"}
    return subprocess.run(
        [sys.executable, "-m", "vibexray", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=env,
        timeout=600,
    )


def load_report_json(out_dir: Path) -> dict:
    return json.loads((out_dir / "vibexray.json").read_text())


@pytest.fixture
def cli():
    return run_cli


def corpus_repo(name: str) -> Path:
    path = CORPUS_DIR / name
    if not path.is_dir():
        pytest.skip(f"corpus repo {name} not fetched; run `make corpus`")
    return path


# The recorded session files hold POSIX folders such as /home/pm/sample-bot.
POSIX_SESSIONS = pytest.mark.skipif(
    sys.platform == "win32", reason="the session fixtures hold POSIX paths"
)
