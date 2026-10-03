"""Score the scanner against hand labels on real prototype repos.

The labels came from a reviewer who never saw the rules. A finding matches a label
when it points at the same file, within 3 lines, with the same category.
The bar (80% recall, 70% precision) is the target the design critic proposed.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from conftest import CORPUS_DIR

from vibexray.rules import run_rules
from vibexray.walker import collect_files

LABELS_DIR = Path(__file__).parent / "corpus" / "labels"
REPORT = Path(__file__).resolve().parents[1] / "tmp" / "accuracy.txt"
SLACK = 3
MIN_RECALL = 0.80
MIN_PRECISION = 0.70
IGNORED = {"note_public_key"}

pytestmark = pytest.mark.corpus


def _label_files() -> list[Path]:
    return sorted(LABELS_DIR.glob("*.json"))


def _hits(finding, label) -> bool:
    if finding.category != label["category"]:
        return False
    lo = label["line_start"] - SLACK
    hi = (label.get("line_end") or label["line_start"]) + SLACK
    if finding.file == label["file"] and lo <= finding.line <= hi:
        return True
    related = label.get("related_file")
    return bool(
        related and finding.file == related and abs(finding.line - label["related_line"]) <= SLACK
    )


def score_repo(label_path: Path):
    data = json.loads(label_path.read_text())
    repo = CORPUS_DIR / data["repo"]
    if not repo.is_dir():
        pytest.skip(f"corpus repo {data['repo']} not fetched; run `make corpus`")
    labels = [
        lb
        for lb in data["labels"]
        if lb["category"] not in IGNORED and lb.get("confidence") != "low"
    ]
    reviewed = set(data.get("files_reviewed") or [lb["file"] for lb in labels])
    findings = [f for f in run_rules(collect_files(repo)) if f.file in reviewed]
    found = [lb for lb in labels if any(_hits(f, lb) for f in findings)]
    correct = [f for f in findings if any(_hits(f, lb) for lb in data["labels"])]
    return data["repo"], labels, found, findings, correct


@pytest.fixture(scope="module")
def scores():
    files = _label_files()
    if not files:
        pytest.skip("no hand labels in tests/corpus/labels")
    return [score_repo(p) for p in files]


def test_recall_and_precision_meet_the_bar(scores):
    total_labels = sum(len(s[1]) for s in scores)
    total_found = sum(len(s[2]) for s in scores)
    total_findings = sum(len(s[3]) for s in scores)
    total_correct = sum(len(s[4]) for s in scores)
    recall = total_found / total_labels if total_labels else 1.0
    precision = total_correct / total_findings if total_findings else 1.0

    missed = Counter(
        lb["category"] for _, labels, found, _, _ in scores for lb in labels if lb not in found
    )
    noisy = Counter(
        f.rule_id for _, _, _, findings, correct in scores for f in findings if f not in correct
    )
    lines = [
        f"recall {recall:.2f} ({total_found}/{total_labels})",
        f"precision {precision:.2f} ({total_correct}/{total_findings})",
        "",
    ]
    for repo, labels, found, findings, correct in scores:
        lines.append(
            f"{repo:<45} labels {len(found)}/{len(labels)}  findings {len(correct)}/{len(findings)}"
        )
    lines += ["", "missed by category:", *[f"  {k:<24} {v}" for k, v in missed.most_common()]]
    lines += [
        "",
        "unmatched findings by rule:",
        *[f"  {k:<34} {v}" for k, v in noisy.most_common()],
    ]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")

    assert recall >= MIN_RECALL, f"recall {recall:.2f} is under {MIN_RECALL}; see {REPORT}"
    assert precision >= MIN_PRECISION, (
        f"precision {precision:.2f} is under {MIN_PRECISION}; see {REPORT}"
    )
