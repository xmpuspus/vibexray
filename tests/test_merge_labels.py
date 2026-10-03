"""Two labelers' files merge into one key, and a problem both labelers marked counts once."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from merge_labels import merge  # noqa: E402


def _label(category, file, start, end=None):
    return {"category": category, "file": file, "line_start": start, "line_end": end or start}


def _key(labeler, labels, files):
    return {
        "repo": "r",
        "sha": "abc",
        "labeler": labeler,
        "files_reviewed": files,
        "labels": labels,
    }


def test_a_problem_both_labelers_marked_counts_once():
    first = _key("a", [_label("auth_gap", "api/orders.ts", 10, 20)], ["api/orders.ts"])
    second = _key("b", [_label("auth_gap", "api/orders.ts", 22, 25)], ["api/orders.ts"])
    assert len(merge(first, second)["labels"]) == 1


def test_other_category_or_file_or_far_lines_join_the_key():
    first = _key("a", [_label("auth_gap", "api/orders.ts", 10, 20)], ["api/orders.ts"])
    second = _key(
        "b",
        [
            _label("security_other", "api/orders.ts", 12),
            _label("auth_gap", "api/users.ts", 12),
            _label("auth_gap", "api/orders.ts", 40),
        ],
        ["api/users.ts"],
    )
    merged = merge(first, second)
    assert len(merged["labels"]) == 4
    assert merged["files_reviewed"] == ["api/orders.ts", "api/users.ts"]
    assert merged["labeler"] == "a+b"
