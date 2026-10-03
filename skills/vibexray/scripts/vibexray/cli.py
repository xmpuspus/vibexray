"""vibexray command line."""

from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from datetime import UTC, datetime
from pathlib import Path

from vibexray import __version__
from vibexray.apprun import run_app
from vibexray.history import read_history
from vibexray.model import ScanResult
from vibexray.parts import build_parts
from vibexray.questions import build_questions
from vibexray.report import write_reports
from vibexray.report.common import app_line, headline, parts_with, plural
from vibexray.review import ReviewError, apply_review
from vibexray.rules import all_rules, run_rules
from vibexray.walker import collect_files, detect_stack


def _color(code: str, text: str) -> str:
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def scan(target: Path, out_dir: Path, run: bool, history_mode: str) -> ScanResult:
    files = collect_files(target)
    findings = run_rules(files)
    app_run = run_app(target, out_dir, enabled=run)
    history = read_history(target, history_mode)
    return ScanResult(
        version=__version__,
        target=str(target),
        app_name=target.name,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        files_scanned=len(files),
        stack=detect_stack(target, files),
        findings=findings,
        parts=build_parts(files, findings),
        app_run=app_run,
        history=history,
        questions=build_questions(findings, history),
    )


def print_summary(result: ScanResult, paths: dict[str, Path]) -> None:
    # The same words and numbers as the top of report.html.
    counts = result.counts()
    labels = result.label_counts()
    stack = " · ".join(result.stack) if result.stack else "stack not detected"
    rows = (
        ("Fake parts", parts_with(result, True), plural(counts["fake"], "place")),
        (
            "Parts that can break",
            parts_with(result, False),
            f"{plural(counts['security'], 'security risk')}, {plural(counts['ai'], 'AI risk')}",
        ),
        ("Decisions for you", len(result.questions), ""),
    )
    print(f"{_color('1', 'vibexray')} {__version__}  {result.app_name}")
    print(f"  {plural(result.files_scanned, 'file')} · {stack}")
    print()
    print(f"  {_color('1', headline(result))}")
    print()
    for title, n, detail in rows:
        print(f"  {title:<22} {n:>3}   {detail if n else ''}".rstrip())
    print()
    print(
        f"  Keep {labels['keep']} · Rewrite {labels['rewrite']} · "
        f"Throw away {labels['throwaway']} · Check {labels['check']}"
    )
    print(f"  App run   {app_line(result)}")
    print()
    print(f"  Report   {paths['html']}")
    print(f"  Handoff  {paths['markdown']}")


def cmd_scan(args: argparse.Namespace) -> int:
    target = Path(args.path).expanduser().resolve()
    if not target.is_dir():
        print(f"vibexray: {args.path} is not a folder.", file=sys.stderr)
        return 2
    out_dir = Path(args.out).expanduser().resolve() if args.out else Path.cwd() / "vibexray-report"
    history_mode = "none" if args.no_history else "auto"
    result = scan(target, out_dir, run=not args.no_run, history_mode=history_mode)
    paths = write_reports(result, out_dir)
    if args.json:
        print(paths["json"].read_text())
    else:
        print_summary(result, paths)
    if args.open:
        webbrowser.open(paths["html"].as_uri())
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    report_dir = Path(args.report_dir).expanduser().resolve()
    review_path = (
        Path(args.input).expanduser().resolve() if args.input else report_dir / "review.json"
    )
    try:
        result = apply_review(report_dir, review_path)
    except ReviewError as exc:
        print(f"vibexray: {exc}", file=sys.stderr)
        return 2
    print(
        f"Kept {len(result.kept)} of {result.total} review findings. "
        f"Dropped {len(result.dropped)}. "
        f"Skipped {len(result.duplicates)} that repeat a finding."
    )
    for drop in result.dropped:
        print(f"  dropped #{drop.index} {drop.file}:{drop.line}  {drop.reason}")
    for dup in result.duplicates:
        print(f"  skipped #{dup.index} {dup.file}:{dup.line}  {dup.reason}")
    if result.rejected:
        print(f"Removed {plural(len(result.rejected), 'rule finding')} as false alarms.")
    for rej in result.rejected:
        print(f"  removed #{rej.index} {rej.file}:{rej.line}  {rej.reason}")
    if result.dropped:
        print(
            "  Drops are normal. vibexray keeps a finding only if its file, line, and quote match."
        )
    print()
    print(f"  Report   {report_dir / 'report.html'}")
    print(f"  Handoff  {report_dir / 'handoff.md'}")
    return 0


def cmd_rules(_: argparse.Namespace) -> int:
    for rule in all_rules():
        print(f"{rule.id:<34} {rule.category:<22} {rule.severity:<7} {rule.pm_text}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vibexray",
        description="X-ray an AI-built prototype: what is real, what is fake, what can break.",
    )
    parser.add_argument("--version", action="version", version=f"vibexray {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="Scan a prototype folder and write the report")
    p_scan.add_argument("path", help="Folder of the prototype")
    p_scan.add_argument("--out", help="Output folder (default: ./vibexray-report)")
    p_scan.add_argument("--no-run", action="store_true", help="Do not start the app")
    p_scan.add_argument("--no-history", action="store_true", help="Do not read the build chat")
    p_scan.add_argument("--open", action="store_true", help="Open the report in a browser")
    p_scan.add_argument("--json", action="store_true", help="Print the JSON result")
    p_scan.set_defaults(func=cmd_scan)

    p_review = sub.add_parser(
        "review", help="Check the host AI's review.json line by line and merge it"
    )
    p_review.add_argument("report_dir", help="Folder that holds vibexray.json from a scan")
    p_review.add_argument("--input", help="Review file (default: <report_dir>/review.json)")
    p_review.set_defaults(func=cmd_review)

    p_rules = sub.add_parser("rules", help="List every rule")
    p_rules.set_defaults(func=cmd_rules)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
