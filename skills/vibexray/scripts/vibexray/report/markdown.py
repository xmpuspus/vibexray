"""The engineer's handoff. The report builder replaces this first version."""

from __future__ import annotations

from vibexray.model import ScanResult


def render_markdown(result: ScanResult) -> str:
    lines = [f"# Handoff: {result.app_name}", ""]
    if not result.findings:
        lines.append("No fake parts or risks found.")
    for f in result.findings:
        lines.append(f"- `{f.file}:{f.line}` {f.engineer_text}")
    return "\n".join(lines) + "\n"
