"""Start the prototype in a clean environment, crawl it, and always stop it again."""

from __future__ import annotations

import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from vibexray.apprun_boot import (
    USUAL_PORTS,
    Process,
    clean_env,
    detect_package_manager,
    detect_script,
    find_env_names,
    free_port,
    log_tail,
    port_open,
    python_entry,
    read_package,
    reap_strays,
    url_from_log,
    wait_for_port_free,
)
from vibexray.apprun_crawl import RUN_EXTRA_HINT, crawl
from vibexray.model import AppRun
from vibexray.rules.base import is_env_file

BOOT_SECONDS = 90
COPY_SKIP = (".git", "node_modules", ".next", "dist", "build", "vibexray-report")
BUILD_MISSING = re.compile(r"(not found|ENOENT|Cannot find).*\b(dist|build|\.next)\b", re.I)
INSTALL_SECONDS = 300
INSTALL_ARGS = {
    "npm": ["install", "--ignore-scripts", "--no-audit", "--no-fund"],
    "pnpm": ["install", "--ignore-scripts"],
    "yarn": ["install", "--ignore-scripts"],
    "bun": ["install", "--ignore-scripts"],
}


def _not_attempted(reason: str) -> AppRun:
    return AppRun(state="not_attempted", reason=reason)


def run_app(root: Path, out_dir: Path, enabled: bool) -> AppRun:
    if not enabled:
        return _not_attempted("Skipped: the scan ran with --no-run.")
    pkg = read_package(root)
    entry = python_entry(root)
    if pkg is None and entry is None:
        return _not_attempted(
            "There is no package.json or Python start file in the top folder, so vibexray "
            "does not know how to start this app."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    # The copy lives outside the user's folder, so a killed scan never leaves it there.
    try:
        run_dir = Path(tempfile.mkdtemp(prefix="vibexray-run-"))
    except OSError as exc:
        return AppRun(
            state="could_not_boot",
            reason=f"vibexray could not make a temporary folder for the app ({exc.strerror}).",
        )
    home = run_dir / "home"
    home.mkdir()
    previous = _trap_stop_signals()
    try:
        # Install and start in a copy, so the user's folder never changes.
        try:
            work = _make_copy(root, run_dir / "app", out_dir)
        except (shutil.Error, OSError) as exc:
            return AppRun(
                state="could_not_boot",
                reason="vibexray could not copy the app to start it. " + _copy_problem(exc),
            )
        if pkg is not None:
            script = detect_script(pkg)
            if script is None:
                return _not_attempted(
                    "package.json has no dev, start, or preview script, so vibexray cannot start it."
                )
            manager = detect_package_manager(root)
            command = f"{manager} run {script}"
            return _boot_and_crawl(work, out_dir, home, command, [manager, "run", script], manager)
        cmd = ["python3", entry]
        if entry == "manage.py":
            cmd = ["python3", entry, "runserver"]
        return _boot_and_crawl(work, out_dir, home, " ".join(cmd), cmd, None)
    except PermissionError as exc:
        return AppRun(
            state="could_not_boot",
            reason=(
                "This computer blocked the app from starting "
                f"({exc.strerror or exc}). A sandbox, such as the one in Codex, does this. "
                "Run the scan in a normal terminal to see the app run."
            ),
        )
    finally:
        reap_strays(home)
        shutil.rmtree(run_dir, ignore_errors=True)
        _restore_signals(previous)


def _trap_stop_signals() -> dict | None:
    """Turn SIGTERM and SIGHUP into SystemExit, so the cleanup in run_app always runs."""
    if threading.current_thread() is not threading.main_thread():
        return None

    def stop(signum, _frame):
        raise SystemExit(128 + signum)

    return {s: signal.signal(s, stop) for s in (signal.SIGTERM, signal.SIGHUP)}


def _restore_signals(previous: dict | None) -> None:
    for sig, handler in (previous or {}).items():
        signal.signal(sig, handler)


def _copy_problem(exc: Exception) -> str:
    # shutil.Error carries a list of (source, destination, reason) for each failed file.
    if isinstance(exc, shutil.Error) and exc.args and isinstance(exc.args[0], list):
        src, _, why = exc.args[0][0]
        return f"It could not read {Path(src).name}: {str(why).split(': ')[0]}."
    return f"{getattr(exc, 'strerror', None) or exc}."


def _make_copy(root: Path, dest: Path, out_dir: Path) -> Path:
    skip = set(COPY_SKIP)
    out_resolved = out_dir.resolve()

    def ignore(folder: str, names: list[str]) -> set[str]:
        left_out = set()
        for n in names:
            path = Path(folder) / n
            # .env files hold the user's keys. The app starts without them.
            if (
                n in skip
                or is_env_file(n)
                or path.resolve() == out_resolved
                or not (path.is_symlink() or path.is_dir() or path.is_file())
            ):
                left_out.add(n)
        return left_out

    shutil.copytree(root, dest, ignore=ignore, symlinks=True)
    if (root / "node_modules").is_dir():
        _clone(root / "node_modules", dest / "node_modules")
    return dest


def _clone(src: Path, dest: Path) -> None:
    """Copy node_modules copy-on-write, so caches the dev server writes stay in the copy.

    APFS and Btrfs share the file blocks, so the clone costs almost no disk. If the clone
    fails, the copy has no node_modules and the app run installs the packages instead.
    """
    if sys.platform == "darwin":
        cmd = ["cp", "-cR", str(src), str(dest)]
    else:
        cmd = ["cp", "-R", "--reflink=auto", str(src), str(dest)]
    if subprocess.run(cmd, capture_output=True).returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)


def _boot_and_crawl(root, out_dir, home, command, cmd, manager) -> AppRun:
    result = AppRun(command=command)
    port = free_port()
    env = clean_env(home, port)
    tool = cmd[0]
    if shutil.which(tool, path=env["PATH"]) is None:
        return _failed(
            result,
            root,
            f"{tool} is not installed on this computer, so the app did not start.",
            None,
        )
    if manager and not (root / "node_modules").is_dir():
        problem = _install(root, env, home, manager)
        if problem:
            return _failed(result, root, problem[0], problem[1])
    # Ports that were already busy before the start belong to someone else.
    fallback = [p for p in USUAL_PORTS if not port_open(p)]
    server = Process(cmd, root, env, home / "server.log")
    try:
        url, why = _wait_for_url(server, port, fallback)
        if url is None:
            return _failed(result, root, why, server.log)
        result.url = url
        try:
            result.pages = crawl(url, root, out_dir)
        except ImportError:
            return _failed(result, root, RUN_EXTRA_HINT, None, keep_url=True)
        except Exception as exc:  # noqa: BLE001 - browser launch problems must not leak a traceback
            return _failed(
                result,
                root,
                "The browser could not open the app: "
                + str(exc).splitlines()[0][:160]
                + " Run: playwright install chromium",
                None,
                keep_url=True,
            )
        result.state = "ran"
        n = len(result.pages)
        result.reason = f"vibexray started the app and visited {n} page{'' if n == 1 else 's'}."
        return result
    finally:
        server.stop()
        wait_for_port_free(port, 5.0)
        if result.url:
            wait_for_port_free(int(result.url.rsplit(":", 1)[1]), 5.0)


def _install(root: Path, env: dict, home: Path, manager: str) -> tuple[str, Path] | None:
    log = home / "install.log"
    proc = Process([manager, *INSTALL_ARGS[manager]], root, env, log)
    try:
        code = proc.wait(INSTALL_SECONDS)
    finally:
        proc.stop()
    if code is None:
        return (
            "Installing the app's packages took longer than 10 minutes, so vibexray stopped.",
            log,
        )
    if code != 0:
        return ("Installing the app's packages failed, so the app did not start.", log)
    return None


def _wait_for_url(server: Process, port: int, fallback: list[int]) -> tuple[str | None, str]:
    deadline = time.monotonic() + BOOT_SECONDS
    while time.monotonic() < deadline:
        if not server.alive():
            return None, "The app started and then stopped on its own, so it cannot run here."
        url = url_from_log(server.log)
        if url:
            port_in_url = int(url.rsplit(":", 1)[1])
            if port_open(port_in_url):
                return url, ""
        elif port_open(port):
            return f"http://localhost:{port}", ""
        else:
            for p in fallback:
                if port_open(p):
                    return f"http://localhost:{p}", ""
        time.sleep(0.5)
    return None, f"The app did not answer within {BOOT_SECONDS} seconds."


def _failed(
    result: AppRun, root: Path, reason: str, log: Path | None, keep_url: bool = False
) -> AppRun:
    result.state = "could_not_boot"
    missing = find_env_names(root)
    result.missing_env = missing
    tail = log_tail(log) if log is not None else []
    if any(BUILD_MISSING.search(line) for line in tail):
        reason += " A build step looks missing: the start file does not exist yet."
    elif missing and log is not None:
        reason += " It may need settings or keys that vibexray does not pass on."
    result.reason = reason
    result.log_tail = tail
    if not keep_url:
        result.url = None
    return result
