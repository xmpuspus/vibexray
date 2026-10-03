"""Write the three outputs: report.html for the PM, handoff.md for the engineer, vibexray.json."""

from __future__ import annotations

import json
from pathlib import Path

from vibexray.model import ScanResult
from vibexray.report.html import render_html
from vibexray.report.markdown import render_markdown
from vibexray.rules.base import hide


def _hide_all(value):
    # The last pass before vibexray.json: every string, in every field, goes through hide().
    if isinstance(value, str):
        return hide(value)
    if isinstance(value, list):
        return [_hide_all(v) for v in value]
    if isinstance(value, dict):
        return {k: _hide_all(v) for k, v in value.items()}
    return value


def write_reports(result: ScanResult, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "html": out_dir / "report.html",
        "markdown": out_dir / "handoff.md",
        "json": out_dir / "vibexray.json",
    }
    paths["html"].write_text(render_html(result, out_dir), encoding="utf-8")
    paths["markdown"].write_text(render_markdown(result), encoding="utf-8")
    data = _hide_all(result.to_dict())
    paths["json"].write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return paths
