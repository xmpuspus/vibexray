"""Score the pattern rules against hand labels on real prototype repos.

The labels came from reviewers who never saw the rules. A finding matches a label when
it names the same file and category, and its line span overlaps the labeled lines
within 3 lines. Tool-level rules report the tool's whole span through end_line.

Pattern rules are the precise floor, not the whole tool. The AI review layer adds
recall, and scripts/eval_review.py measures rules plus review on the held-out repos
against the 80% recall and 70% precision bar. This test gates rules-only precision
on the dev repos and records every number in tmp/accuracy.txt.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest
from conftest import CORPUS_DIR

from vibexray.rules import run_rules
from vibexray.walker import collect_files

CORPUS = Path(__file__).parent / "corpus"
LABELS_DIR = CORPUS / "labels"
SPLIT = json.loads((CORPUS / "split.json").read_text())
REPORT = Path(__file__).resolve().parents[1] / "tmp" / "accuracy.txt"
SLACK = 3
MIN_DEV_PRECISION = 0.60
IGNORED = {"note_public_key"}
# The reviewers labeled only these categories, so findings outside them cannot be scored.
UNLABELED = {"ai_no_tests", "ai_no_cost_limit"}

# A separate auditor read the code at every unmatched dev finding. Findings judged
# "labeler_missed" or "duplicate" count as correct. The labels themselves stay unchanged.
AUDIT = json.loads((CORPUS / "audit" / "unmatched-audit.json").read_text())


def audit_key(repo: str, finding) -> tuple[str, str, str, int]:
    return (repo, finding.rule_id, finding.file, finding.line)


ACCEPTED = {
    (a["repo"], a["rule_id"], a["file"], a["line"])
    for a in AUDIT
    if a["verdict"] in ("labeler_missed", "duplicate")
}

pytestmark = pytest.mark.corpus


def hits(finding, label: dict) -> bool:
    if finding.category != label["category"]:
        return False
    start = finding.line
    end = getattr(finding, "end_line", None) or finding.line
    lo = label["line_start"] - SLACK
    hi = (label.get("line_end") or label["line_start"]) + SLACK
    if finding.file == label["file"] and start <= hi and end >= lo:
        return True
    related = label.get("related_file")
    if not related or finding.file != related:
        return False
    return start <= label["related_line"] + SLACK and end >= label["related_line"] - SLACK


def reviewed_files(data: dict, labels: list[dict]) -> set[str]:
    # Reviewers wrote notes after some paths, for example "src/data.ts (header only)".
    entries = data.get("files_reviewed") or [lb["file"] for lb in labels]
    return {entry.split(" (")[0].strip() for entry in entries}


def score_repo(name: str) -> dict:
    data = json.loads((LABELS_DIR / f"{name}.json").read_text())
    repo = CORPUS_DIR / name
    if not repo.is_dir():
        pytest.skip(f"corpus repo {name} not fetched; run `make corpus`")
    labels = [
        lb
        for lb in data["labels"]
        if lb["category"] not in IGNORED and lb.get("confidence") != "low"
    ]
    reviewed = reviewed_files(data, labels)
    findings = [
        f
        for f in run_rules(collect_files(repo))
        if f.file in reviewed and f.category not in UNLABELED
    ]
    raw = [f for f in findings if any(hits(f, lb) for lb in data["labels"])]
    return {
        "repo": name,
        "labels": labels,
        "found": [lb for lb in labels if any(hits(f, lb) for f in findings)],
        "findings": findings,
        "correct_raw": raw,
        "correct": [f for f in findings if f in raw or audit_key(name, f) in ACCEPTED],
    }


def totals(rows: list[dict]) -> tuple[float, float, str]:
    n_labels = sum(len(r["labels"]) for r in rows)
    n_found = sum(len(r["found"]) for r in rows)
    n_findings = sum(len(r["findings"]) for r in rows)
    n_correct = sum(len(r["correct"]) for r in rows)
    recall = n_found / n_labels if n_labels else 1.0
    precision = n_correct / n_findings if n_findings else 1.0
    text = (
        f"recall {recall:.2f} ({n_found}/{n_labels})  "
        f"precision {precision:.2f} ({n_correct}/{n_findings})"
    )
    return recall, precision, text


@pytest.fixture(scope="module")
def scores() -> dict[str, list[dict]]:
    return {split: [score_repo(n) for n in SPLIT[split]] for split in ("dev", "heldout")}


def test_rules_precision_on_dev_repos(scores):
    lines = []
    for split, rows in scores.items():
        raw = sum(len(r["correct_raw"]) for r in rows)
        n = sum(len(r["findings"]) for r in rows)
        lines.append(f"{split}: {totals(rows)[2]}  (labels only: {raw}/{n})")
    dev = scores["dev"]
    lines.append("")
    for r in dev:
        lines.append(
            f"{r['repo']:<45} labels {len(r['found'])}/{len(r['labels'])}  "
            f"findings {len(r['correct'])}/{len(r['findings'])}"
        )
    missed = Counter(lb["category"] for r in dev for lb in r["labels"] if lb not in r["found"])
    noisy = Counter(f.rule_id for r in dev for f in r["findings"] if f not in r["correct"])
    lines += ["", "dev missed by category:", *[f"  {k:<24} {v}" for k, v in missed.most_common()]]
    lines += ["", "dev unmatched findings by rule:"]
    lines += [f"  {k:<34} {v}" for k, v in noisy.most_common()]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n")

    _, precision, text = totals(dev)
    assert precision >= MIN_DEV_PRECISION, f"dev rules precision too low: {text}; see {REPORT}"
