"""The AI review step: keep a finding only when its file, line, and quote are real.

review.json under tests/fixtures/review/ came from a real headless Claude Code run of the
skill on Snodrod/ai-support-agent. The cited files sit beside it as full verbatim copies,
so the line numbers match. tests/fixtures/SOURCES.md records every changed entry.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vibexray.review import apply_review

FIX = Path(__file__).parent / "fixtures" / "review"
REPO_COPY = FIX / "Snodrod__ai-support-agent"
ENTRIES: list[dict] = json.loads((FIX / "review.json").read_text())

# Indexes into the real review.json. See tests/fixtures/SOURCES.md.
PLAIN = 0  # auth_gap at src/tools.ts:56-71, which no rule finding covers


def norm(text: str) -> str:
    return " ".join(text.split())


@pytest.fixture
def scanned(cli, tmp_path) -> Path:
    out = tmp_path / "report"
    result = cli("scan", str(REPO_COPY), "--out", str(out), "--no-run", "--no-history")
    assert result.returncode == 0, result.stderr
    return out


def write_review(out: Path, entries: list[dict]) -> Path:
    path = out / "review.json"
    path.write_text(json.dumps(entries, indent=2))
    return path


def rule_findings(out: Path) -> list[dict]:
    data = json.loads((out / "vibexray.json").read_text())
    return [f for f in data["findings"] if f["source"] == "rule"]


def test_fixture_is_a_real_run_with_no_home_paths_or_keys():
    text = (FIX / "review.json").read_text()
    assert "/Users/" not in text and "/home/" not in text
    for marker in ("sk-", "ghp_", "AKIA", "xoxb-", "eyJ"):
        assert marker not in text
    assert len(ENTRIES) >= 5


def test_every_real_entry_is_kept_or_dropped_with_a_reason(scanned):
    result = apply_review(scanned, write_review(scanned, ENTRIES))
    assert result.total == len(ENTRIES)
    assert len(result.kept) + len(result.dropped) + len(result.duplicates) == len(ENTRIES)
    assert result.kept, "a real review keeps at least one finding"
    for drop in result.dropped:
        assert drop.reason


def test_kept_entry_quote_appears_in_the_cited_lines(scanned):
    entry = ENTRIES[PLAIN]
    result = apply_review(scanned, write_review(scanned, [entry]))
    assert len(result.kept) == 1, [d.reason for d in result.dropped + result.duplicates]
    kept = result.kept[0]
    lines = (REPO_COPY / kept.file).read_text().splitlines()
    span = "\n".join(lines[kept.line - 1 : kept.end_line or kept.line])
    assert norm(kept.quote) in norm(span)
    assert kept.source == "review"
    assert kept.verified is True
    data = json.loads((scanned / "vibexray.json").read_text())
    review = [f for f in data["findings"] if f["source"] == "review"]
    assert len(review) == 1
    assert review[0]["file"] == entry["file"] and review[0]["line"] == entry["line"]
    assert all("source" in f and "verified" in f for f in data["findings"])


def test_missing_file_is_dropped(scanned):
    entry = dict(ENTRIES[PLAIN], file="src/no_such_file.ts")
    result = apply_review(scanned, write_review(scanned, [entry]))
    assert not result.kept
    assert len(result.dropped) == 1
    assert "not found" in result.dropped[0].reason


def test_path_outside_the_repo_is_dropped(scanned):
    entry = dict(ENTRIES[PLAIN], file="../../etc/hosts")
    result = apply_review(scanned, write_review(scanned, [entry]))
    assert not result.kept
    assert "outside" in result.dropped[0].reason


def test_line_out_of_range_is_dropped(scanned):
    entry = ENTRIES[PLAIN]
    n_lines = len((REPO_COPY / entry["file"]).read_text().splitlines())
    result = apply_review(scanned, write_review(scanned, [dict(entry, line=n_lines + 40)]))
    assert not result.kept
    assert "line" in result.dropped[0].reason
    assert str(n_lines) in result.dropped[0].reason


def test_quote_with_one_changed_character_is_dropped(scanned):
    entry = ENTRIES[PLAIN]
    quote = entry["quote"]
    # Change the first letter, so whitespace rules cannot hide the edit.
    i = next(i for i, ch in enumerate(quote) if ch.isalpha())
    changed = quote[:i] + ("X" if quote[i] != "X" else "Y") + quote[i + 1 :]
    result = apply_review(scanned, write_review(scanned, [dict(entry, quote=changed)]))
    assert not result.kept
    assert "quote" in result.dropped[0].reason


def test_whitespace_differences_in_the_quote_still_match(scanned):
    entry = ENTRIES[PLAIN]
    spaced = "  " + "   ".join(entry["quote"].split()) + "\n"
    result = apply_review(scanned, write_review(scanned, [dict(entry, quote=spaced)]))
    assert len(result.kept) == 1


def test_key_in_review_text_never_reaches_the_outputs(scanned):
    # Built the same way as the key in test_history.py, so no real key sits in the repo.
    key = "sk-" + "A1b2C3d4" * 4
    entry = dict(ENTRIES[PLAIN])
    entry["pm_text"] = f"{entry['pm_text']} The key {key} is in the code."
    entry["engineer_text"] = f"{entry['engineer_text']} Rotate {key}."
    result = apply_review(scanned, write_review(scanned, [entry]))
    assert len(result.kept) == 1
    for name in ("vibexray.json", "report.html", "handoff.md"):
        text = (scanned / name).read_text()
        assert key not in text, name
    assert "[hidden]" in (scanned / "handoff.md").read_text()
    assert result.kept[0].engineer_text.startswith(ENTRIES[PLAIN]["engineer_text"][:40])


def test_unknown_category_and_label_are_dropped(scanned):
    entry = ENTRIES[PLAIN]
    bad = [dict(entry, category="vibes"), dict(entry, label="maybe")]
    result = apply_review(scanned, write_review(scanned, bad))
    assert not result.kept
    reasons = " ".join(d.reason for d in result.dropped)
    assert "category" in reasons and "label" in reasons


def test_entry_that_repeats_a_rule_finding_is_skipped(scanned):
    rules = rule_findings(scanned)
    pairs = [
        (entry, rule)
        for entry in ENTRIES
        for rule in rules
        if rule["file"] == entry["file"] and rule["category"] == entry["category"]
    ]
    assert pairs, "no real entry shares a file and category with a rule finding"
    entry, rule = pairs[0]
    # The real run repeated no rule finding. Widen the real entry until it reaches the
    # rule's first line. The quote stays inside the new span.
    lo = min(entry["line"], rule["line"])
    hi = max(entry.get("end_line") or entry["line"], rule["line"])
    widened = dict(entry, line=lo, end_line=hi)
    result = apply_review(scanned, write_review(scanned, [widened]))
    assert not result.kept, [d.reason for d in result.dropped]
    assert len(result.duplicates) == 1
    assert f"rule finding at {rule['file']}:{rule['line']}" in result.duplicates[0].reason
    data = json.loads((scanned / "vibexray.json").read_text())
    assert len(data["findings"]) == len(rules)


def test_same_entry_twice_keeps_one(scanned):
    result = apply_review(scanned, write_review(scanned, [ENTRIES[PLAIN], ENTRIES[PLAIN]]))
    assert len(result.kept) == 1
    assert len(result.duplicates) == 1
    assert "review finding" in result.duplicates[0].reason


def test_running_review_twice_does_not_double_findings(scanned):
    path = write_review(scanned, ENTRIES)
    first = apply_review(scanned, path)
    second = apply_review(scanned, path)
    assert len(first.kept) == len(second.kept)
    data = json.loads((scanned / "vibexray.json").read_text())
    review = [f for f in data["findings"] if f["source"] == "review"]
    assert len(review) == len(first.kept)


def test_reports_show_the_review_finding_and_its_source(scanned):
    entry = ENTRIES[PLAIN]
    apply_review(scanned, write_review(scanned, [entry]))
    handoff = (scanned / "handoff.md").read_text()
    html = (scanned / "report.html").read_text()
    data = json.loads((scanned / "vibexray.json").read_text())
    assert f"`{entry['file']}:{entry['line']}`" in handoff
    assert "AI review" in handoff
    assert f"{entry['file']}:{entry['line']}" in html.replace("<wbr>", "")
    assert "AI review" in html
    part = next(p for p in data["parts"] if p["file"] == entry["file"])
    assert part["label"] != "keep" or entry["label"] == "keep"
    result = json.loads((scanned / "review-result.json").read_text())
    assert result["kept"] == 1 and result["dropped"] == []


def test_cli_review_prints_kept_and_dropped_with_reasons(cli, scanned):
    entries = [ENTRIES[PLAIN], dict(ENTRIES[PLAIN], file="src/no_such_file.ts")]
    path = write_review(scanned, entries)
    result = cli("review", str(scanned), "--input", str(path))
    assert result.returncode == 0, result.stderr
    assert "Kept 1" in result.stdout
    assert "Dropped 1" in result.stdout
    assert "src/no_such_file.ts" in result.stdout and "not found" in result.stdout


def test_cli_review_without_a_scan_fails_plainly(cli, tmp_path):
    path = tmp_path / "review.json"
    path.write_text("[]")
    result = cli("review", str(tmp_path), "--input", str(path))
    assert result.returncode == 2
    assert "vibexray.json" in result.stderr


@pytest.mark.parametrize("quote", [";", "l", "=> {"])
def test_quote_under_six_characters_is_dropped(scanned, quote):
    # Any short token sits on almost every line, so it proves nothing about the cited line.
    entry = dict(ENTRIES[PLAIN], quote=quote)
    result = apply_review(scanned, write_review(scanned, [entry]))
    assert not result.kept
    assert "quote is too short" in result.dropped[0].reason


def test_span_over_30_lines_needs_a_16_character_quote(scanned):
    short = dict(ENTRIES[PLAIN], line=1, end_line=71, quote="import { z }")
    long = dict(ENTRIES[PLAIN], line=1, end_line=71, quote="run: ({ order_id }) => {")
    result = apply_review(scanned, write_review(scanned, [short]))
    assert not result.kept
    assert "longer quote" in result.dropped[0].reason
    result = apply_review(scanned, write_review(scanned, [long]))
    assert len(result.kept) == 1


def test_span_over_300_lines_is_dropped(cli, tmp_path):
    # One real file built from three real fixture files, so it runs past 300 lines.
    app = tmp_path / "app"
    (app / "src").mkdir(parents=True)
    parts = ["tools.ts", "executor.ts", "server.ts"]
    text = "".join((REPO_COPY / "src" / p).read_text() for p in parts)
    (app / "src" / "all.ts").write_text(text)
    out = tmp_path / "report"
    assert cli("scan", str(app), "--out", str(out), "--no-run", "--no-history").returncode == 0
    entry = dict(
        ENTRIES[PLAIN], file="src/all.ts", line=1, end_line=320, quote="run: ({ order_id }) => {"
    )
    result = apply_review(out, write_review(out, [entry]))
    assert not result.kept
    assert "300" in result.dropped[0].reason
