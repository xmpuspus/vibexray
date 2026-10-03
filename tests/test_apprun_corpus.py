"""App-run tests on copies of real corpus repos. Copies live in tmp/ and are deleted after."""

import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import REPO, corpus_repo

from vibexray.apprun import run_app

pytestmark = pytest.mark.corpus


def port_free(port: int) -> bool:
    out = subprocess.run(["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True)
    return out.stdout.strip() == ""


def leftover_processes(root: Path) -> list[str]:
    """Processes whose command line points into the scanned copy."""
    out = subprocess.run(["ps", "-axo", "command"], capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if str(root) in line]


def copy_repo(name: str) -> Path:
    src = corpus_repo(name)
    dest = REPO / "tmp" / "apprun-tests" / name
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", "node_modules"))
    return dest


@pytest.fixture(scope="module")
def cleanup():
    yield
    shutil.rmtree(REPO / "tmp" / "apprun-tests", ignore_errors=True)


def ports_used(result) -> list[int]:
    return [int(result.url.rsplit(":", 1)[1].strip("/"))] if result.url else []


@pytest.mark.browser
def test_next_app_boots_and_crawls(cleanup, tmp_path):
    root = copy_repo("ai-customer-support-agent")
    result = run_app(root, tmp_path, enabled=True)
    assert result.state == "ran", result.reason
    assert result.url and result.command
    assert result.pages
    shot = result.pages[0].screenshot
    assert shot and not Path(shot).is_absolute()
    assert (tmp_path / shot).is_file()
    assert result.pages[0].status == 200
    paths = [p.path for p in result.pages]
    assert "/chat" in paths and "/admin/login" in paths
    assert len(result.pages) <= 8
    for port in ports_used(result):
        assert port_free(port)
    assert not (left := leftover_processes(root)), left


def test_bun_app_with_missing_build_could_not_boot(cleanup, tmp_path):
    root = copy_repo("mj-deving__ai-support-agent")
    result = run_app(root, tmp_path, enabled=True)
    assert result.state == "could_not_boot"
    assert result.reason and "Traceback" not in result.reason
    assert result.command
    assert isinstance(result.missing_env, list)
    assert result.log_tail
    assert not (left := leftover_processes(root)), left


def test_repo_without_root_entry_not_attempted(cleanup, tmp_path):
    root = corpus_repo("SliceIQ")
    result = run_app(root, tmp_path, enabled=True)
    assert result.state == "not_attempted"
    assert result.reason


def test_no_run_flag_not_attempted(tmp_path):
    result = run_app(tmp_path, tmp_path, enabled=False)
    assert result.state == "not_attempted"
    assert "--no-run" in result.reason
