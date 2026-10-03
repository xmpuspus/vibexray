"""Start the prototype in a clean environment, crawl it, and always stop it again."""

from __future__ import annotations

import re
import shutil
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

BOOT_SECONDS = 90
BUILD_MISSING = re.compile(r"(not found|ENOENT|Cannot find).*\b(dist|build|\.next)\b", re.I)
INSTALL_SECONDS = 600
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
    home = out_dir / ".vibexray-home"
    home.mkdir(parents=True, exist_ok=True)
    try:
        if pkg is not None:
            script = detect_script(pkg)
            if script is None:
                return _not_attempted(
                    "package.json has no dev, start, or preview script, so vibexray cannot start it."
                )
            manager = detect_package_manager(root)
            command = f"{manager} run {script}"
            return _boot_and_crawl(root, out_dir, home, command, [manager, "run", script], manager)
        cmd = ["python3", entry]
        if entry == "manage.py":
            cmd = ["python3", entry, "runserver"]
        return _boot_and_crawl(root, out_dir, home, " ".join(cmd), cmd, None)
    finally:
        reap_strays(root)
        shutil.rmtree(home, ignore_errors=True)


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
        result.reason = f"The app started and {len(result.pages)} page(s) were visited."
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
