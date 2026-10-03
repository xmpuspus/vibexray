"""Write the three outputs: report.html for the PM, handoff.md for the engineer, vibexray.json."""

from __future__ import annotations

import json
from pathlib import Path

from vibexray.model import ScanResult
from vibexray.report.html import render_html
from vibexray.report.markdown import render_markdown


def write_reports(result: ScanResult, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "html": out_dir / "report.html",
        "markdown": out_dir / "handoff.md",
        "json": out_dir / "vibexray.json",
    }
    paths["html"].write_text(render_html(result, out_dir), encoding="utf-8")
    paths["markdown"].write_text(render_markdown(result), encoding="utf-8")
    paths["json"].write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return paths
