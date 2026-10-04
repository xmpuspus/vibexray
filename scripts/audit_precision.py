"""Precision of saved sessions, with the independent audit of unmatched findings.

The labels stay unchanged. A finding counts as correct when it matches a label, or when the
auditor judged it real or labeler_missed, or duplicate with a label of the same category in the same
file. --loose counts a duplicate when any file of the repo has a label of that category.

If the audit judged only a random sample of the unmatched findings, the share of real findings
in the sample stands in for the rest. The output then gives a 95% interval (Wilson).

    uv run python scripts/audit_precision.py tmp/eval-rounds/heldout-claude-r2-runs
    uv run python scripts/audit_precision.py RUNS --audit tests/corpus/audit/sealed-review-audit.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests")]

from test_corpus_accuracy import LABELS_DIR, UNLABELED, hits, reviewed_files  # noqa: E402

AUDIT = REPO / "tests" / "corpus" / "audit" / "heldout-review-audit.json"


def accepted(audit: Path, loose: bool) -> tuple[set[tuple], set[tuple]]:
    ok, judged = set(), set()
    for x in json.loads(audit.read_text()):
        labels = json.loads((LABELS_DIR / f"{x['repo']}.json").read_text())["labels"]
        same = [lb for lb in labels if lb["category"] == x["category"]]
        if not loose:
            same = [lb for lb in same if lb["file"] == x["file"]]
        key = (x["repo"], x["file"], x["line"], x.get("end_line"), x["category"])
        judged.add(key)
        if x["verdict"] in ("labeler_missed", "real") or (x["verdict"] == "duplicate" and same):
            ok.add(key)
    return ok, judged


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    centre = (k + z * z / 2) / (n + z * z)
    half = z * math.sqrt(k * (n - k) / n + z * z / 4) / (n + z * z)
    return centre - half, centre + half


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("runs_dir", type=Path, help="Session folders of one saved round")
    parser.add_argument("--audit", type=Path, default=AUDIT, help="Audit verdicts of this round")
    parser.add_argument("--loose", action="store_true")
    args = parser.parse_args(argv)
    ok, judged = accepted(args.audit, args.loose)
    total, labeled, right, unjudged = Counter(), Counter(), Counter(), Counter()
    seen = set()
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
                elif key not in judged:
                    unjudged[run.name] += 1
                seen.add(key)
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
    rest = sum(unjudged.values())
    if rest:
        sample = seen & judged
        k, m = len(sample & ok), len(sample)
        lo, hi = wilson(k, m)
        base = sum(right.values())
        print(
            f"{rest} unmatched findings were outside the audit sample. "
            f"Real in the sample: {k}/{m} = {k / m:.2f}"
        )
        print(
            f"pooled estimate: audited {(base + k / m * rest) / n:.2f} "
            f"(95% interval {(base + lo * rest) / n:.2f} to {(base + hi * rest) / n:.2f})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
