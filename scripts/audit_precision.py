"""Precision of saved held-out sessions, with the independent audit of unmatched findings.

The labels stay unchanged. A finding counts as correct when it matches a label, or when the
auditor judged it labeler_missed, or duplicate with a label of the same category in the same
file. --loose counts a duplicate when any file of the repo has a label of that category.

    uv run python scripts/audit_precision.py tmp/eval-rounds/heldout-claude-r2-runs
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests")]

from test_corpus_accuracy import LABELS_DIR, UNLABELED, hits, reviewed_files  # noqa: E402

AUDIT = REPO / "tests" / "corpus" / "audit" / "heldout-review-audit.json"


def accepted(loose: bool) -> set[tuple]:
    ok = set()
    for x in json.loads(AUDIT.read_text()):
        labels = json.loads((LABELS_DIR / f"{x['repo']}.json").read_text())["labels"]
        same = [lb for lb in labels if lb["category"] == x["category"]]
        if not loose:
            same = [lb for lb in same if lb["file"] == x["file"]]
        if x["verdict"] == "labeler_missed" or (x["verdict"] == "duplicate" and same):
            ok.add((x["repo"], x["file"], x["line"], x.get("end_line"), x["category"]))
    return ok


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs_dir", type=Path, help="Session folders of one saved round")
    parser.add_argument("--loose", action="store_true")
    args = parser.parse_args(argv)
    ok = accepted(args.loose)
    total, labeled, right = Counter(), Counter(), Counter()
    for repo_dir in sorted(p for p in args.runs_dir.iterdir() if p.is_dir()):
        data = json.loads((LABELS_DIR / f"{repo_dir.name}.json").read_text())
        reviewed = reviewed_files(data, data["labels"])
        for run in sorted(repo_dir.glob("run-*")):
            report = run / "vibexray.json"
            if not report.is_file():
                report = run / "report" / "vibexray.json"
            for f in json.loads(report.read_text())["findings"]:
                if f["file"] not in reviewed or f["category"] in UNLABELED:
                    continue
                total[run.name] += 1
                key = (repo_dir.name, f["file"], f["line"], f.get("end_line"), f["category"])
                if any(hits(SimpleNamespace(**f), lb) for lb in data["labels"]):
                    labeled[run.name] += 1
                    right[run.name] += 1
                elif key in ok:
                    right[run.name] += 1
    for run in sorted(total):
        print(
            f"{run}: labels only {labeled[run]}/{total[run]} = {labeled[run] / total[run]:.2f}, "
            f"audited {right[run]}/{total[run]} = {right[run] / total[run]:.2f}"
        )
    n = sum(total.values())
    print(
        f"pooled: labels only {sum(labeled.values()) / n:.2f}, "
        f"audited {sum(right.values()) / n:.2f} ({'loose' if args.loose else 'strict'})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
