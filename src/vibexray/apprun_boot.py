"""Pure helpers and process control for the app run: detection, URL parsing, safe start and stop."""

from __future__ import annotations

import contextlib
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

from vibexray.rules.base import redact

ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
URL = re.compile(r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1?\]):(\d{2,5})")
ENV_CODE = re.compile(r"(?:process\.env|import\.meta\.env)\.([A-Za-z_][A-Za-z0-9_]*)")
ENV_KEY = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", re.M)
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".nuxt", ".svelte-kit", "tmp"}
# Set by the runtime or by the clean environment itself, so never "missing".
BUILTIN_ENV = {"NODE_ENV", "PORT", "PATH", "HOME", "MODE", "DEV", "PROD", "SSR", "BASE_URL", "CI"}
USUAL_PORTS = (3000, 5173, 4173, 8080, 8000, 4321, 3001)
PYTHON_ENTRIES = ("app.py", "main.py", "server.py", "manage.py")
SCRIPT_ORDER = ("dev", "start", "preview")


def parse_url(line: str) -> str | None:
    """Return the local URL a dev server prints, or None. Network lines are skipped."""
    text = ANSI.sub("", line)
    if "Network" in text:
        return None
    m = URL.search(text)
    if not m:
        return None
    host = "127.0.0.1" if m.group(1) == "127.0.0.1" else "localhost"
    return f"http://{host}:{m.group(2)}"


def detect_package_manager(root: Path) -> str:
    # Bun first: a repo with both bun.lock and package-lock.json usually runs its scripts with bun.
    if (root / "bun.lock").exists() or (root / "bun.lockb").exists():
        return "bun"
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    return "npm"


def detect_script(pkg: dict) -> str | None:
    scripts = pkg.get("scripts") or {}
    return next((s for s in SCRIPT_ORDER if s in scripts), None)


def read_package(root: Path) -> dict | None:
    try:
        data = json.loads((root / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def python_entry(root: Path) -> str | None:
    return next((e for e in PYTHON_ENTRIES if (root / e).is_file()), None)


def iter_source(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            path = Path(dirpath) / name
            if path.suffix in SOURCE_SUFFIXES:
                yield path


def find_env_names(root: Path) -> list[str]:
    names: set[str] = set()
    for path in iter_source(root):
        try:
            names.update(ENV_CODE.findall(path.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue
    for example in (".env.example", ".env.sample", ".env.template"):
        try:
            names.update(ENV_KEY.findall((root / example).read_text(encoding="utf-8")))
        except OSError:
            continue
    return sorted(names - BUILTIN_ENV)


def clean_env(home: Path, port: int) -> dict[str, str]:
    """The only variables a scanned app sees. The user's own keys never pass through."""
    return {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "PORT": str(port)}


def port_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def log_tail(path: Path, n: int = 20) -> list[str]:
    try:
        lines = ANSI.sub("", path.read_text(encoding="utf-8", errors="replace")).splitlines()
    except OSError:
        return []
    return [redact(line) for line in lines if line.strip()][-n:]


def url_from_log(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        url = parse_url(line)
        if url:
            return url
    return None


class Process:
    """A child in its own process group, so one call stops it and everything it spawned."""

    def __init__(self, cmd: list[str], cwd: Path, env: dict[str, str], log: Path):
        log.parent.mkdir(parents=True, exist_ok=True)
        self.log = log
        self._fh = open(log, "wb")  # noqa: SIM115 - closed in stop()
        try:
            self.proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=self._fh,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError:
            self._fh.close()
            raise

    def alive(self) -> bool:
        return self.proc.poll() is None

    def wait(self, timeout: float) -> int | None:
        try:
            return self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            return None

    def stop(self) -> None:
        pgid = self.proc.pid
        # Some tools start helpers in their own session (Next.js telemetry does). The group
        # kill misses those, so list every descendant first and stop them by pid too.
        kids = _descendants(pgid)
        for sig in (signal.SIGTERM, signal.SIGKILL):
            _signal_all(pgid, kids, sig)
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline and (_group_alive(pgid) or _any_alive(kids)):
                time.sleep(0.1)
            if not _group_alive(pgid) and not _any_alive(kids):
                break
        with contextlib.suppress(subprocess.TimeoutExpired):
            self.proc.wait(timeout=1)
        self._fh.close()


def _descendants(pid: int) -> list[int]:
    out = subprocess.run(["ps", "-axo", "pid=,ppid="], capture_output=True, text=True).stdout
    children: dict[int, list[int]] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            children.setdefault(int(parts[1]), []).append(int(parts[0]))
    found, todo = [], [pid]
    while todo:
        for kid in children.get(todo.pop(), []):
            found.append(kid)
            todo.append(kid)
    return found


def _signal_all(pgid: int, pids: list[int], sig: int) -> None:
    if pgid > 0:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(pgid, sig)
    for pid in pids:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, sig)


def _any_alive(pids: list[int]) -> bool:
    for pid in pids:
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, PermissionError):
            continue
        return True
    return False


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except (ProcessLookupError, PermissionError):
        return False
    return True


def wait_for_port_free(port: int, seconds: float = 10.0) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not port_open(port):
            return True
        time.sleep(0.2)
    return not port_open(port)


def reap_strays(home: Path, seconds: float = 10.0) -> None:
    """Stop leftovers that escaped the process group, such as the detached telemetry flush
    that Next.js starts at exit. Only processes that carry our unique HOME in their
    environment count, so the user's own processes are never touched."""
    marker = f"HOME={home.resolve()}"
    start = time.monotonic()
    for _ in range(int(seconds / 0.2)):
        pids = _pids_with_env(marker)
        if not pids:
            return
        if time.monotonic() - start > 2.0:
            _signal_all(-1, pids, signal.SIGKILL)
        time.sleep(0.2)


def _pids_with_env(marker: str) -> list[int]:
    me = os.getpid()
    if sys.platform == "darwin":
        # -E appends each process's environment to its command line.
        out = subprocess.run(["ps", "-axE", "-o", "pid=,command="], capture_output=True, text=True)
        found = []
        for line in out.stdout.splitlines():
            pid, _, rest = line.strip().partition(" ")
            if pid.isdigit() and int(pid) != me and f" {marker}" in f" {rest} ":
                found.append(int(pid))
        return found
    found = []
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            env = (entry / "environ").read_bytes().split(b"\0")
        except OSError:
            continue
        if marker.encode() in env and int(entry.name) != me:
            found.append(int(entry.name))
    return found
