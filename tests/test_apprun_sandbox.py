"""A sandbox that blocks local servers and `ps` must not crash the scan.

Codex runs commands in a macOS sandbox that denies port binding and `ps`. The held-out
eval showed the scan crash there with a PermissionError traceback in 6 of 7 repos.
This test runs the real CLI under `sandbox-exec` with the same two denials.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import REPO, load_report_json

FIXTURE = Path(__file__).parent / "fixtures" / "ai-customer-support-agent"
PROFILE = '(version 1)(allow default)(deny network-bind)(deny process-exec (literal "/bin/ps"))'

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin" or shutil.which("sandbox-exec") is None,
    reason="needs the macOS sandbox-exec tool",
)


def test_scan_inside_a_sandbox_reports_the_block_and_finishes(tmp_path):
    app = tmp_path / "support-bot"
    shutil.copytree(FIXTURE, app)
    out = tmp_path / "report"
    env = {**os.environ, "PYTHONPATH": str(REPO / "src"), "NO_COLOR": "1"}
    cmd = [sys.executable, "-m", "vibexray", "scan", str(app), "--out", str(out), "--no-history"]
    result = subprocess.run(
        ["sandbox-exec", "-p", PROFILE, *cmd],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    run = load_report_json(out)["app_run"]
    assert run["state"] == "could_not_boot"
    assert "blocked" in run["reason"]
    html = (out / "report.html").read_text()
    assert "blocked" in html
