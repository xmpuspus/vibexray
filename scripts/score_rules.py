"""Score the pattern rules alone, with no AI review, on one corpus split.

uv run python scripts/score_rules.py sealed
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests")]

from test_corpus_accuracy import SPLIT, score_repo  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("split", choices=sorted(k for k, v in SPLIT.items() if isinstance(v, list)))
    args = parser.parse_args(argv)
    rows = [score_repo(name) for name in SPLIT[args.split]]
    labels = sum(len(r["labels"]) for r in rows)
    found = sum(len(r["found"]) for r in rows)
    findings = sum(len(r["findings"]) for r in rows)
    right = sum(len(r["correct_raw"]) for r in rows)
    print(
        f"{args.split}: rules only, recall {found / labels:.2f} ({found}/{labels}), "
        f"precision {right / max(1, findings):.2f} ({right}/{findings}), labels only"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
