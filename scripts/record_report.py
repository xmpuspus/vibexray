"""Record a real browser walk through a vibexray report and save it as a GIF.

The script opens report.html in Chromium, records video, and scrolls to each section
in the order a PM reads it. ffmpeg and gifsicle turn the video into a small GIF.

    uv run python scripts/record_report.py docs/demo/report.html docs/report.gif
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright
from video_to_gif import to_gif

SIZE = {"width": 1280, "height": 800}
# Section id and seconds to stay on it.
STOPS = [
    ("top", 3.5),
    ("decisions", 4.0),
    ("parts", 3.0),
    ("fake", 3.0),
    ("risks", 3.5),
    ("app", 3.5),
    ("chat", 2.5),
    ("engineer", 3.0),
]


def record(report: Path, video_dir: Path) -> Path:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport=SIZE, record_video_dir=str(video_dir), record_video_size=SIZE
        )
        page = context.new_page()
        page.goto(report.resolve().as_uri())
        page.wait_for_load_state("networkidle")
        for sid, seconds in STOPS:
            if sid == "top":
                page.evaluate("window.scrollTo({top: 0})")
            elif page.locator(f"#{sid}").count():
                page.evaluate(
                    "id => document.getElementById(id).scrollIntoView({behavior: 'smooth'})", sid
                )
            else:
                continue
            page.wait_for_timeout(int(seconds * 1000))
        video = page.video.path()
        context.close()
        browser.close()
    return Path(video)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", type=Path, help="report.html from a vibexray scan")
    parser.add_argument("gif", type=Path, help="Output GIF path")
    args = parser.parse_args(argv)
    if not args.report.is_file():
        parser.error(f"{args.report} is not a file")
    for tool in ("ffmpeg", "gifsicle"):
        if shutil.which(tool) is None:
            parser.error(f"{tool} is not installed")
    with tempfile.TemporaryDirectory() as tmp:
        video = record(args.report, Path(tmp))
        to_gif(video, args.gif)
    print(f"Wrote {args.gif} ({args.gif.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
