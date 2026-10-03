"""Merge two independent label files per repo into one answer key.

Every label of the first labeler stays. A label of the second labeler joins unless it
names the same problem as a first label: same category, same file, and lines that overlap
with 3 lines of slack, the same rule that scoring uses. The files each labeler read join too.

    uv run python scripts/merge_labels.py FIRST_DIR SECOND_DIR OUT_DIR REPO...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SLACK = 3


def same_problem(a: dict, b: dict) -> bool:
    if a["category"] != b["category"] or a["file"] != b["file"]:
        return False
    a_end = a.get("line_end") or a["line_start"]
    b_end = b.get("line_end") or b["line_start"]
    return a["line_start"] - SLACK <= b_end and b["line_start"] <= a_end + SLACK


def merge(first: dict, second: dict) -> dict:
    labels = list(first["labels"])
    added = [b for b in second["labels"] if not any(same_problem(a, b) for a in first["labels"])]
    reviewed = list(
        dict.fromkeys((first.get("files_reviewed") or []) + (second.get("files_reviewed") or []))
    )
    return {
        "repo": first["repo"],
        "sha": first["sha"],
        "labeler": f"{first['labeler']}+{second['labeler']}",
        "files_reviewed": reviewed,
        "note": f"{first.get('note', '')} | Second labeler: {second.get('note', '')}".strip(" |"),
        "labels": labels + added,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("first", type=Path)
    parser.add_argument("second", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("repos", nargs="+")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    for repo in args.repos:
        first = json.loads((args.first / f"{repo}.json").read_text())
        second = json.loads((args.second / f"{repo}.json").read_text())
        if first["sha"] != second["sha"]:
            parser.error(f"{repo}: the two labelers labeled different commits")
        merged = merge(first, second)
        (args.out / f"{repo}.json").write_text(json.dumps(merged, indent=2) + "\n")
        n1, n2, n = len(first["labels"]), len(second["labels"]), len(merged["labels"])
        print(f"{repo:<45} first {n1:>4}  second {n2:>4}  merged {n:>4}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
