"""Record docs/media/showcase.gif: one square GIF of a real report, sized for a LinkedIn post.

    uv run --with pillow python scripts/record_showcase.py tmp/hero/report/report.html

A title card opens the GIF, and an install card ends it. Each report section plays in a real
Chromium window under a caption band that names what it shows. The GIF is 1080 x 1080, with
at most 500 frames and 5 MB, so LinkedIn takes it as an image.
"""

from __future__ import annotations

import argparse
import base64
import io
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright
from record_report import settle

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "media" / "showcase.gif"
SIZE = 1080
BAND = 200
# The report draws at this width, and the frame scales it up into the area under the band.
# 820 px keeps the desktop layout (it switches at 760 px) and makes the text big on a phone.
VIEW = {"width": 820, "height": 668}
APP = (SIZE, SIZE - BAND)

# Report section -> the caption above it. Each caption says what the section shows.
STORY = [
    ("top", "One scan of an AI-built prototype.", "What is real, and what is fake."),
    ("decisions", "The decisions the PM must make,", "each with its file and line."),
    ("parts", "A label for every file.", "Keep, rewrite, throw away, or check."),
    ("fake", "What is fake:", "sample data and actions that do nothing."),
    ("risks", "What can break:", "open pages, open data, AI with no limits."),
    ("app", "It starts the app in a copy", "and opens every page."),
    ("chat", "It reads your build chat,", "so the rules you typed get checked."),
    ("engineer", "The engineer gets handoff.md,", "with every file, line, and fix."),
]
INTRO_SECONDS = 3.0
OUTRO_SECONDS = 5.0
# Scenes play this many times faster than they ran, so the GIF takes about a minute.
SPEED = 1.4
# Each scene keeps its first frame this long, so the caption can be read.
FIRST_SECONDS = 1.6
HOLD_SECONDS = 1.6
FPS = 10
MAX_FRAMES = 500
MAX_BYTES = 5_000_000

NAVY, STEEL, MIST, WHITE = "#0B2545", "#9DB8DE", "#C9D3DF", "#FFFFFF"
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', Menlo, monospace"
LOGO = (REPO / "docs" / "media" / "logo.svg").read_text()


def page_html(body: str, height: int) -> str:
    return f"""<!doctype html><html><head><style>
html, body {{ margin: 0; width: {SIZE}px; height: {height}px; background: {NAVY};
  font-family: {FONT}; color: {WHITE}; -webkit-font-smoothing: antialiased; }}
svg {{ display: block; }}
</style></head><body>{body}</body></html>"""


def logo(px: int) -> str:
    return LOGO.replace('width="120" height="120"', f'width="{px}" height="{px}"')


def band_html(line1: str, line2: str) -> str:
    return page_html(
        f"""<div style="height:{BAND}px; box-sizing:border-box; padding:28px 56px 0;
  border-bottom:1px solid #1d3a63">
  <div style="display:flex; align-items:center; gap:12px; font-size:22px; color:{MIST};
    font-weight:600">{logo(30)} vibexray</div>
  <div style="margin-top:18px; font-size:44px; line-height:52px; font-weight:700;
    letter-spacing:-.6px">{line1} <span style="color:{STEEL}">{line2}</span></div>
</div>""",
        BAND,
    )


def intro_html() -> str:
    return page_html(
        f"""<div style="height:{SIZE}px; display:flex; flex-direction:column; justify-content:center;
  padding:0 96px; box-sizing:border-box">
  {logo(132)}
  <div style="margin-top:44px; font-size:96px; font-weight:800; letter-spacing:-2.5px">vibexray</div>
  <div style="margin-top:22px; font-size:48px; line-height:60px; font-weight:600; color:{MIST}">
    See what is real and what is fake in an AI-built prototype,
    <span style="color:{STEEL}">before the engineer builds it</span>.</div>
  <div style="margin-top:48px; font-size:30px; color:{MIST}">A skill for Claude Code and Codex</div>
</div>""",
        SIZE,
    )


def outro_html() -> str:
    cmd = (
        f"margin-top:20px; font-family:{MONO}; font-size:30px; padding:22px 28px; border-radius:14px;"
        " background:#071a33; border:1px solid #1d3a63"
    )
    return page_html(
        f"""<div style="height:{SIZE}px; display:flex; flex-direction:column; justify-content:center;
  padding:0 96px; box-sizing:border-box">
  <div style="display:flex; align-items:center; gap:24px; font-size:60px; font-weight:800;
    letter-spacing:-1.5px">{logo(88)} vibexray</div>
  <div style="margin-top:56px; font-size:30px; color:{MIST}">In Claude Code</div>
  <div style="{cmd}"><span style="color:#6f86a6">/</span>plugin marketplace add
    <span style="color:{STEEL}">xmpuspus/vibexray</span></div>
  <div style="margin-top:36px; font-size:30px; color:{MIST}">Or the command line</div>
  <div style="{cmd}"><span style="color:#6f86a6">$</span> pipx install
    <span style="color:{STEEL}">vibexray</span></div>
  <div style="margin-top:52px; font-size:34px; font-weight:600">github.com/xmpuspus/vibexray</div>
</div>""",
        SIZE,
    )


def render_cards() -> dict[str, Image.Image]:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": SIZE, "height": SIZE})

        def shot(html: str, height: int) -> Image.Image:
            page.set_viewport_size({"width": SIZE, "height": height})
            page.set_content(html)
            page.wait_for_timeout(150)
            return Image.open(io.BytesIO(page.screenshot())).convert("RGB")

        cards = {"intro": shot(intro_html(), SIZE), "outro": shot(outro_html(), SIZE)}
        for name, line1, line2 in STORY:
            cards[name] = shot(band_html(line1, line2), BAND)
        browser.close()
    return cards


def capture(page, cdp, sid: str) -> tuple[list[tuple[float, bytes]], float]:
    """Record one section: hold on its top, then scroll through it in steps."""
    if sid == "top":
        page.evaluate("window.scrollTo(0, 0)")
    else:
        page.evaluate("id => document.getElementById(id).scrollIntoView()", sid)
    settle(page)
    frames: list[tuple[float, bytes]] = []

    def on_frame(params: dict) -> None:
        frames.append((params["metadata"]["timestamp"], base64.b64decode(params["data"])))
        cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})

    cdp.on("Page.screencastFrame", on_frame)
    cdp.send("Page.startScreencast", {"format": "png", "everyNthFrame": 1})
    page.wait_for_timeout(2200)
    for _ in range(2 if sid != "top" else 0):
        rest = page.evaluate(
            "id => document.getElementById(id).getBoundingClientRect().bottom - innerHeight", sid
        )
        if rest <= 40:
            break
        page.evaluate("dy => window.scrollBy({top: dy, behavior: 'smooth'})", min(rest + 24, 460))
        settle(page)
        page.wait_for_timeout(1800)
    end = time.time()
    cdp.send("Page.stopScreencast")
    cdp.remove_listener("Page.screencastFrame", on_frame)
    return frames, end


def timeline(frames: list[tuple[float, bytes]], end: float) -> list[tuple[bytes, float]]:
    """Sample at FPS of play time, keep a frame only when the page changed, and cut long waits."""
    picks: list[list] = []
    i, t = 0, frames[0][0]
    while t < end:
        while i + 1 < len(frames) and frames[i + 1][0] <= t:
            i += 1
        if picks and picks[-1][0] == i:
            picks[-1][1] += 1 / FPS
        else:
            picks.append([i, 1 / FPS])
        t += SPEED / FPS
    out = [(frames[i][1], min(sec, HOLD_SECONDS)) for i, sec in picks]
    out[0] = (out[0][0], max(out[0][1], FIRST_SECONDS))
    return out


def compose(band: Image.Image, png: bytes) -> Image.Image:
    shot = Image.open(io.BytesIO(png)).convert("RGB")
    frame = Image.new("RGB", (SIZE, SIZE), NAVY)
    frame.paste(band, (0, 0))
    frame.paste(shot.resize(APP, Image.LANCZOS), (0, BAND))
    return frame


def encode(listing: Path, gif: Path) -> None:
    vf = (
        f"fps={FPS},mpdecimate,split[a][b];"
        "[a]palettegen=max_colors=96:stats_mode=diff[p];"
        "[b][p]paletteuse=dither=none:diff_mode=rectangle"
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing)]
        + ["-vf", vf, "-fps_mode", "vfr", str(gif)],
        check=True,
    )


def hold_last(gif: Path, seconds: float) -> None:
    """ffmpeg gives the last frame one tick, so the install card needs its delay set again."""
    n = count_frames(gif)
    held = gif.with_suffix(".held.gif")
    subprocess.run(
        ["gifsicle", str(gif), f"#0-{n - 2}", f"-d{int(seconds * 100)}", str(gif), f"#{n - 1}"]
        + ["-o", str(held)],
        check=True,
    )
    held.replace(gif)


def count_frames(gif: Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0"]
        + ["-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(gif)],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(out.stdout.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("report", type=Path, help="report.html from a vibexray scan")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args(argv)
    if not args.report.is_file():
        parser.error(f"{args.report} is not a file")
    cards = render_cards()
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        lines: list[str] = []

        def add(image: Image.Image, seconds: float) -> Path:
            path = tmp / f"{len(lines) // 2:05d}.png"
            image.save(path)
            lines.extend([f"file '{path}'", f"duration {seconds:.3f}"])
            return path

        add(cards["intro"], INTRO_SECONDS)
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport=VIEW)
            page.goto(args.report.resolve().as_uri())
            page.wait_for_load_state("networkidle")
            cdp = page.context.new_cdp_session(page)
            for sid, *_ in STORY:
                if sid != "top" and not page.locator(f"#{sid}").count():
                    parser.error(f"{args.report} has no #{sid} section")
                frames, end = capture(page, cdp, sid)
                for png, seconds in timeline(frames, end):
                    add(compose(cards[sid], png), seconds)
            browser.close()
        last = add(cards["outro"], OUTRO_SECONDS)
        # The concat format needs the last file twice, or it drops the last duration.
        lines.append(f"file '{last}'")
        listing = tmp / "frames.txt"
        listing.write_text("\n".join(lines) + "\n")
        args.out.parent.mkdir(parents=True, exist_ok=True)
        encode(listing, args.out)
        hold_last(args.out, OUTRO_SECONDS)
    frames, size = count_frames(args.out), args.out.stat().st_size
    seconds = sum(float(x.split()[1]) for x in lines if x.startswith("duration"))
    print(f"Wrote {args.out}: {frames} frames, {size // 1024} KB, {seconds:.0f} s")
    if frames > MAX_FRAMES or size > MAX_BYTES:
        print(f"Over the LinkedIn limit of {MAX_FRAMES} frames and 5 MB", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
