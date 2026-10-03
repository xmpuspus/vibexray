"""Clone the pinned real prototype repos that the corpus tests scan.

The repos are public and MIT or Apache-2.0 licensed. They are not copied into this
repo. Each one is cloned at the exact commit that the hand labels describe.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LOCK = REPO / "tests" / "corpus" / "corpus.lock.json"
DEST = REPO / ".cache" / "corpus"


def fetch(entry: dict) -> str:
    target = DEST / entry["folder"]
    if (target / ".git").is_dir():
        head = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "HEAD"], capture_output=True, text=True
        ).stdout.strip()
        if head == entry["sha"]:
            return "ok"
        subprocess.run(["rm", "-rf", str(target)], check=True)
    target.mkdir(parents=True, exist_ok=True)
    git = ["git", "-C", str(target)]
    subprocess.run([*git, "init", "-q"], check=True)
    subprocess.run([*git, "remote", "add", "origin", entry["url"]], check=True)
    fetched = subprocess.run(
        [*git, "fetch", "-q", "--depth", "1", "origin", entry["sha"]], capture_output=True
    )
    if fetched.returncode != 0:
        return "fetch failed"
    subprocess.run([*git, "checkout", "-q", "FETCH_HEAD"], check=True)
    return "cloned"


def main() -> int:
    entries = json.loads(LOCK.read_text())
    DEST.mkdir(parents=True, exist_ok=True)
    failed = 0
    for entry in entries:
        status = fetch(entry)
        failed += status == "fetch failed"
        print(f"{status:<13} {entry['folder']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
