"""List the unique findings of saved sessions that match no label, as input for an audit.

The output holds vibexray's findings only. It holds no label text, so the auditor never sees
the labels. tests/corpus/audit/AUDIT.md tells the auditor what to do with each entry.

    uv run python scripts/unmatched_findings.py OUT.json RUNS_DIR... [--sample 300]

With --sample N and more than N findings, OUT holds a random sample of N, drawn with a fixed
seed. OUT-all.json keeps the full list.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests")]

from test_corpus_accuracy import LABELS_DIR, UNLABELED, hits, reviewed_files  # noqa: E402

FIELDS = ("snippet", "pm_text", "engineer_text")


def unmatched(runs_dirs: list[Path]) -> list[dict]:
    out: dict[tuple, dict] = {}
    for runs in runs_dirs:
        for repo_dir in sorted(p for p in runs.iterdir() if p.is_dir()):
            data = json.loads((LABELS_DIR / f"{repo_dir.name}.json").read_text())
            reviewed = reviewed_files(data, data["labels"])
            for run in sorted(repo_dir.glob("run-*")):
                report = run / "vibexray.json"
                if not report.is_file():
                    continue
                for f in json.loads(report.read_text())["findings"]:
                    if f["file"] not in reviewed or f["category"] in UNLABELED:
                        continue
                    if any(hits(SimpleNamespace(**f), lb) for lb in data["labels"]):
                        continue
                    key = (repo_dir.name, f["file"], f["line"], f.get("end_line"), f["category"])
                    item = out.setdefault(
                        key,
                        {
                            "repo": repo_dir.name,
                            "file": f["file"],
                            "line": f["line"],
                            "end_line": f.get("end_line"),
                            "category": f["category"],
                            **{k: f.get(k, "") for k in FIELDS},
                            "seen_in": [],
                        },
                    )
                    item["seen_in"].append(f"{runs.name}/{run.name}")
    return sorted(out.values(), key=lambda x: (x["repo"], x["file"], x["line"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    parser.add_argument("runs_dirs", type=Path, nargs="+")
    parser.add_argument("--sample", type=int, help="Audit only this many, drawn at random")
    parser.add_argument("--seed", type=int, default=20261004)
    args = parser.parse_args(argv)
    items = unmatched(args.runs_dirs)
    print(
        f"{len(items)} unique unmatched findings in {len(Counter(i['repo'] for i in items))} repos"
    )
    if args.sample and len(items) > args.sample:
        args.out.with_name(args.out.stem + "-all.json").write_text(
            json.dumps(items, indent=1) + "\n"
        )
        items = sorted(
            random.Random(args.seed).sample(items, args.sample),
            key=lambda x: (x["repo"], x["file"], x["line"]),
        )
        print(f"sampled {len(items)} with seed {args.seed}")
    args.out.write_text(json.dumps(items, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
