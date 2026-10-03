"""The PM's report. The report builder replaces this first version."""

from __future__ import annotations

from html import escape

from vibexray.model import Finding, ScanResult

EMPTY_FINDINGS = "No fake parts found. vibexray checked every source file it could read."
EMPTY_RUN = "The app did not run."
EMPTY_HISTORY = "No build chat found for this folder."


REVIEW_TAG = "AI review, line checked"


def _source(f: Finding) -> str:
    return f" <em class='source'>{REVIEW_TAG}</em>" if f.source == "review" else ""


def render_html(result: ScanResult) -> str:
    rows = "".join(
        f"<li>{escape(f.pm_text)} <code>{escape(f.file)}:{f.line}</code>{_source(f)}</li>"
        for f in result.findings
    )
    findings = f"<ul>{rows}</ul>" if rows else f"<p>{EMPTY_FINDINGS}</p>"
    run = (
        f"<p>{EMPTY_RUN} {escape(result.app_run.reason)}</p>"
        if result.app_run.state != "ran"
        else "<p>The app ran.</p>"
    )
    history = (
        f"<p>{EMPTY_HISTORY} {escape(result.history.note)}</p>"
        if result.history.source == "none"
        else f"<p>{len(result.history.prompts)} prompts read.</p>"
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>vibexray: {escape(result.app_name)}</title></head><body>"
        f"<h1>{escape(result.app_name)}</h1>{findings}{run}{history}</body></html>"
    )
