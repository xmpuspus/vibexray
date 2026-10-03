"""The app run works on a copy. The copy has no keys, and nothing it does reaches the user's folder.

These cases come from a code review of the app run:
- the copy took .env and .env.local, so the app started with the user's keys;
- a link to the user's node_modules let Vite and webpack write caches into the user's folder;
- a file the scan cannot read crashed the scan;
- a stop signal skipped the cleanup and left the server and the copy behind.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import time

import pytest
from conftest import REPO

from vibexray.apprun import _make_copy, run_app


def _project(root):
    root.mkdir(parents=True)
    (root / "package.json").write_text('{"name": "demo", "scripts": {"dev": "vite"}}\n')
    (root / ".env").write_text("OPENAI_API_KEY=live-value\n")
    (root / ".env.local").write_text("STRIPE_KEY=live-value\n")
    (root / ".env.example").write_text("OPENAI_API_KEY=\n")
    (root / "node_modules" / "vite").mkdir(parents=True)
    (root / "node_modules" / "vite" / "package.json").write_text('{"name": "vite"}\n')


def test_copy_leaves_out_env_files_but_keeps_the_examples(tmp_path):
    root = tmp_path / "app"
    _project(root)
    work = _make_copy(root, tmp_path / "run" / "app", tmp_path / "report")
    assert not (work / ".env").exists()
    assert not (work / ".env.local").exists()
    assert (work / ".env.example").is_file()


def test_copy_gets_its_own_node_modules(tmp_path):
    root = tmp_path / "app"
    _project(root)
    work = _make_copy(root, tmp_path / "run" / "app", tmp_path / "report")
    assert not (work / "node_modules").is_symlink()
    assert (work / "node_modules" / "vite" / "package.json").is_file()
    # A dev server writes its cache here. The user's folder must not change.
    (work / "node_modules" / ".vite").mkdir()
    assert not (root / "node_modules" / ".vite").exists()


@pytest.mark.skipif(os.geteuid() == 0, reason="root can read any file")
def test_unreadable_file_gives_a_plain_reason_not_a_crash(tmp_path):
    root = tmp_path / "app"
    _project(root)
    locked = root / "data.db"
    locked.write_text("rows")
    locked.chmod(0)
    try:
        run = run_app(root, tmp_path / "report", enabled=True)
    finally:
        locked.chmod(0o600)
    assert run.state == "could_not_boot"
    assert "copy" in run.reason


def test_named_pipe_in_the_project_does_not_stop_the_copy(tmp_path):
    root = tmp_path / "app"
    _project(root)
    os.mkfifo(root / "logs.pipe")
    work = _make_copy(root, tmp_path / "run" / "app", tmp_path / "report")
    assert (work / "package.json").is_file()
    assert not (work / "logs.pipe").exists()


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_stop_signal_cleans_up_the_server_and_the_copy(tmp_path):
    root = tmp_path / "app"
    root.mkdir()
    marker = f"vibexray-signal-test-{os.getpid()}"
    # A dev server that never answers keeps the scan in its boot wait.
    script = f'node -e "setInterval(() => {{}}, 1000)" {marker}'
    (root / "package.json").write_text(json.dumps({"name": "demo", "scripts": {"dev": script}}))
    (root / "node_modules").mkdir()
    temp = tmp_path / "temp"
    temp.mkdir()
    env = {**os.environ, "PYTHONPATH": str(REPO / "src"), "NO_COLOR": "1", "TMPDIR": str(temp)}
    cmd = [sys.executable, "-m", "vibexray", "scan", str(root), "--out", str(tmp_path / "out")]
    proc = subprocess.Popen([*cmd, "--no-history"], env=env, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline and not _running(marker):
        time.sleep(0.2)
    assert _running(marker), "the dev server did not start"
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=30)
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and _running(marker):
        time.sleep(0.2)
    assert not _running(marker), "the dev server outlived the scan"
    assert not any(temp.iterdir()), "the copy outlived the scan"


def _running(marker: str) -> bool:
    out = subprocess.run(["ps", "-axo", "command"], capture_output=True, text=True).stdout
    return any(marker in line and "node" in line for line in out.splitlines())
