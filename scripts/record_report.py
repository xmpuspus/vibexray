"""Record a real browser walk through a vibexray report and save it as a GIF.

The script opens report.html in Chromium and scrolls to each section in the order a PM
reads it. Chromium's screencast streams every painted frame as a lossless PNG with its
time. ffmpeg joins the frames with their real timing, and gifsicle makes the GIF small.

    uv run python scripts/record_report.py tmp/hero/report/report.html docs/media/report.gif
"""

from __future__ import annotations

import argparse
import base64
import shutil
import subprocess
import sys
import tempfile
import time
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


def settle(page) -> None:
    """Wait until a smooth scroll stops, so each stop holds still for its full time."""
    last, same = None, 0
    for _ in range(60):
        y = page.evaluate("window.scrollY")
        same = same + 1 if y == last else 0
        if same >= 3:
            return
        last = y
        page.wait_for_timeout(100)


def walk_section(page, sid: str) -> None:
    """Scroll into one section, hold, then scroll through it until its end is on screen."""
    page.wait_for_timeout(800)
    page.evaluate("id => document.getElementById(id).scrollIntoView({behavior: 'smooth'})", sid)
    settle(page)
    page.wait_for_timeout(2500)
    for _ in range(4):
        rest = page.evaluate(
            "id => document.getElementById(id).getBoundingClientRect().bottom - innerHeight", sid
        )
        if rest <= 40:
            break
        page.evaluate("dy => window.scrollBy({top: dy, behavior: 'smooth'})", min(rest + 24, 480))
        settle(page)
        page.wait_for_timeout(2200)
    page.wait_for_timeout(800)


def record(report: Path, work: Path, section: str | None = None) -> Path:
    frames: list[tuple[float, bytes]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport=SIZE)
        page.goto(report.resolve().as_uri())
        page.wait_for_load_state("networkidle")
        if section:
            if not page.locator(f"#{section}").count():
                raise SystemExit(f"{report} has no #{section} section")
            # A feature GIF opens just above its own section, so the jump from the top stays out.
            page.evaluate("id => document.getElementById(id).scrollIntoView()", section)
            page.evaluate("window.scrollBy(0, -280)")
            settle(page)
        cdp = page.context.new_cdp_session(page)

        def on_frame(params: dict) -> None:
            frames.append((params["metadata"]["timestamp"], base64.b64decode(params["data"])))
            cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})

        cdp.on("Page.screencastFrame", on_frame)
        cdp.send("Page.startScreencast", {"format": "png", "everyNthFrame": 1})
        for sid, seconds in [] if section else STOPS:
            if sid == "top":
                page.evaluate("window.scrollTo({top: 0})")
            elif page.locator(f"#{sid}").count():
                page.evaluate(
                    "id => document.getElementById(id).scrollIntoView({behavior: 'smooth'})", sid
                )
            else:
                continue
            settle(page)
            page.wait_for_timeout(int(seconds * 1000))
        if section:
            walk_section(page, section)
        end = time.time()
        cdp.send("Page.stopScreencast")
        browser.close()
    # The screencast sends a frame only when the page changes, so each frame lasts until the next.
    lines = []
    for i, (stamp, png) in enumerate(frames):
        path = work / f"f{i:05d}.png"
        path.write_bytes(png)
        nxt = frames[i + 1][0] if i + 1 < len(frames) else end
        lines += [f"file '{path}'", f"duration {max(nxt - stamp, 0.01):.3f}"]
    lines.append(f"file '{work / f'f{len(frames) - 1:05d}.png'}'")
    (work / "frames.txt").write_text("\n".join(lines) + "\n")
    video = work / "walk.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0"]
        + ["-i", str(work / "frames.txt"), "-fps_mode", "vfr", "-c:v", "libx264"]
        + ["-crf", "0", "-preset", "veryfast", "-pix_fmt", "yuv444p", str(video)],
        check=True,
    )
    return video


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", type=Path, help="report.html from a vibexray scan")
    parser.add_argument("gif", type=Path, help="Output GIF path")
    parser.add_argument(
        "--section",
        choices=[sid for sid, _ in STOPS if sid != "top"],
        help="Record one section only, for a feature GIF",
    )
    args = parser.parse_args(argv)
    if not args.report.is_file():
        parser.error(f"{args.report} is not a file")
    for tool in ("ffmpeg", "gifsicle"):
        if shutil.which(tool) is None:
            parser.error(f"{tool} is not installed")
    with tempfile.TemporaryDirectory() as tmp:
        video = record(args.report, Path(tmp), args.section)
        # The screencast sends no frame for a still screen, so the last frame needs its hold.
        to_gif(video, args.gif, width=900, fps=8, lossy=30, hold=2.5 if args.section else 0.0)
    print(f"Wrote {args.gif} ({args.gif.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
