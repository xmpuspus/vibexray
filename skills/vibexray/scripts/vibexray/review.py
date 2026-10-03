"""Merge the host AI's review into a scan.

Pattern rules miss most problems that need judgment, so the host AI (Claude Code or Codex)
reviews the code and writes review.json. An AI can cite a file, a line, or code that does
not exist. vibexray keeps a review finding only when the file exists under the scanned
folder, the line exists, and the quote appears on the cited lines.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from vibexray.model import (
    CATEGORIES,
    LABELS,
    SEVERITIES,
    AppRun,
    Finding,
    History,
    Page,
    Part,
    Prompt,
    Question,
    ScanResult,
)
from vibexray.parts import build_parts
from vibexray.questions import build_questions
from vibexray.report import write_reports
from vibexray.rules.base import SECRET_VALUE, redact
from vibexray.walker import collect_files

RESULT_NAME = "review-result.json"


class ReviewError(Exception):
    """The review step cannot run at all, for example with no scan output."""


@dataclass
class Drop:
    index: int
    file: str
    line: object
    reason: str


@dataclass
class ReviewResult:
    total: int
    kept: list[Finding] = field(default_factory=list)
    dropped: list[Drop] = field(default_factory=list)
    duplicates: list[Drop] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "kept": len(self.kept),
            "dropped": [asdict(d) for d in self.dropped],
            "duplicates": [asdict(d) for d in self.duplicates],
            "drop_rate": round(len(self.dropped) / self.total, 4) if self.total else 0.0,
        }


def norm(text: str) -> str:
    return " ".join(text.split())


def load_result(data: dict) -> ScanResult:
    """Rebuild a ScanResult from vibexray.json. Older files have no source or quote fields."""
    run = dict(data.get("app_run") or {})
    run["pages"] = [Page(**p) for p in run.get("pages") or []]
    history = dict(data.get("history") or {})
    history["prompts"] = [Prompt(**p) for p in history.get("prompts") or []]
    return ScanResult(
        version=data["version"],
        target=data["target"],
        app_name=data["app_name"],
        generated_at=data["generated_at"],
        files_scanned=data["files_scanned"],
        stack=data.get("stack") or [],
        findings=[Finding(**f) for f in data.get("findings") or []],
        parts=[Part(**p) for p in data.get("parts") or []],
        app_run=AppRun(**run),
        history=History(**history),
        questions=[Question(**q) for q in data.get("questions") or []],
    )


def hide_keys(text: str) -> str:
    """Hide key-shaped strings like redact() does, with no length cap for long review text."""
    return SECRET_VALUE.sub(lambda m: m.group(0)[:6] + "...[hidden]", text.strip())


def _whole(value: object) -> int | None:
    # JSON true loads as a Python int, and a line number of true is a mistake.
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _read(root: Path, rel: object) -> tuple[str, list[str] | None, str]:
    """Return the file's path relative to root, its lines, and a reason when it fails."""
    if not isinstance(rel, str) or not rel.strip():
        return "", None, "no file named"
    path = (root / rel.strip()).resolve()
    if not path.is_relative_to(root):
        return rel, None, f"file {rel} is outside the scanned folder"
    if not path.is_file():
        return rel, None, f"file {rel} not found in the scanned folder"
    clean = path.relative_to(root).as_posix()
    try:
        # splitlines() numbers lines the same way the rules do.
        return clean, path.read_text(encoding="utf-8").splitlines(), ""
    except (OSError, UnicodeDecodeError):
        return clean, None, f"file {clean} is not readable text"


def check_entry(entry: object, root: Path) -> tuple[Finding | None, str]:
    """Return a verified finding, or None and the plain reason for the drop."""
    if not isinstance(entry, dict):
        return None, "entry is not an object"
    category = entry.get("category")
    if category not in CATEGORIES:
        return None, f"category {category!r} is not a vibexray category"
    rel, lines, why = _read(root, entry.get("file"))
    if lines is None:
        return None, why

    line = _whole(entry.get("line"))
    if line is None:
        return None, "line is not a whole number"
    end_line = None
    if entry.get("end_line") is not None:
        end_line = _whole(entry.get("end_line"))
        if end_line is None:
            return None, "end_line is not a whole number"
    if not 1 <= line <= len(lines):
        return None, f"line {line} is outside {rel}, which has {len(lines)} lines"
    last = end_line or line
    if not line <= last <= len(lines):
        return None, f"end_line {last} is outside lines {line} to {len(lines)} of {rel}"

    quote = entry.get("quote")
    if not isinstance(quote, str) or not norm(quote):
        return None, "quote is empty"
    span = f"line {line}" if last == line else f"lines {line} to {last}"
    if norm(quote) not in norm("\n".join(lines[line - 1 : last])):
        return None, f"quote not found on {rel} {span}"

    severity = str(entry.get("severity") or "").strip().lower()
    if severity not in SEVERITIES:
        return None, f"severity {entry.get('severity')!r} is not one of high, medium, low"
    # The skill names the label "throw away", so accept the spaced form too.
    label = "".join(str(entry.get("label") or "").lower().split()).replace("_", "")
    if label not in LABELS:
        return None, f"label {entry.get('label')!r} is not one of keep, rewrite, throwaway, check"
    texts = {k: entry.get(k) for k in ("pm_text", "engineer_text")}
    for key, value in texts.items():
        if not isinstance(value, str) or not value.strip():
            return None, f"{key} is empty"

    related_file = related_line = related_snippet = None
    rel_line = _whole(entry.get("related_line"))
    if entry.get("related_file") and rel_line:
        other, other_lines, _ = _read(root, entry["related_file"])
        if other_lines is not None and 1 <= rel_line <= len(other_lines):
            related_file, related_line = other, rel_line
            related_snippet = redact(other_lines[rel_line - 1])

    return Finding(
        rule_id="review",
        category=category,
        severity=severity,
        file=rel,
        line=line,
        snippet=redact(lines[line - 1]),
        pm_text=hide_keys(texts["pm_text"]),
        engineer_text=hide_keys(texts["engineer_text"]),
        label=label,
        end_line=end_line if end_line and end_line != line else None,
        related_file=related_file,
        related_line=related_line,
        related_snippet=related_snippet,
        source="review",
        verified=True,
        quote=redact(quote),
    ), ""


def _overlaps(a: Finding, b: Finding) -> bool:
    return (
        a.file == b.file
        and a.category == b.category
        and a.line <= (b.end_line or b.line)
        and (a.end_line or a.line) >= b.line
    )


def _load_entries(review_path: Path) -> list:
    try:
        entries = json.loads(review_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ReviewError(f"cannot read {review_path}: {exc.strerror}") from exc
    except ValueError as exc:
        raise ReviewError(f"{review_path} is not valid JSON: {exc}") from exc
    if isinstance(entries, dict):
        entries = entries.get("findings")
    if not isinstance(entries, list):
        raise ReviewError(f"{review_path} must hold a list of findings")
    return entries


def apply_review(report_dir: Path, review_path: Path) -> ReviewResult:
    """Check each review entry, merge the kept ones, and re-render all three outputs."""
    report_dir, review_path = Path(report_dir), Path(review_path)
    json_path = report_dir / "vibexray.json"
    if not json_path.is_file():
        raise ReviewError(f"{json_path} not found. Run vibexray scan first.")
    try:
        result = load_result(json.loads(json_path.read_text(encoding="utf-8")))
    except (ValueError, KeyError, TypeError) as exc:
        raise ReviewError(f"{json_path} is not a vibexray scan: {exc}") from exc
    root = Path(result.target).resolve()
    if not root.is_dir():
        raise ReviewError(f"the scanned folder {root} no longer exists")
    entries = _load_entries(review_path)

    # review.json is the whole review, so a second run replaces the first one.
    rule_findings = [f for f in result.findings if f.source != "review"]
    out = ReviewResult(total=len(entries))
    for index, entry in enumerate(entries, start=1):
        finding, why = check_entry(entry, root)
        if finding is None:
            file = entry.get("file") if isinstance(entry, dict) else None
            line = entry.get("line") if isinstance(entry, dict) else None
            out.dropped.append(Drop(index, str(file or ""), line, why))
            continue
        twin = next((f for f in rule_findings + out.kept if _overlaps(f, finding)), None)
        if twin is not None:
            reason = f"repeats the {twin.source} finding at {twin.file}:{twin.line}"
            out.duplicates.append(Drop(index, finding.file, finding.line, reason))
            continue
        out.kept.append(finding)

    result.findings = rule_findings + out.kept
    result.parts = build_parts(collect_files(root), result.findings)
    result.questions = build_questions(result.findings, result.history)
    write_reports(result, report_dir)
    (report_dir / RESULT_NAME).write_text(
        json.dumps(out.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    return out
