"""Turn a screen recording into a small GIF for the README.

The script can cut the still screen at the end of a recording, speed the video up to a
target length, and hold the last frame so a reader can finish it. It uses ffmpeg palettegen
and gifsicle. It never adds or edits frames.

    uv run python scripts/video_to_gif.py tmp/hero/hero.mp4 docs/hero.gif \
        --trim-tail --seconds 45 --hold 8
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def duration(video: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(video)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def active_end(video: Path, keep: float = 3.0) -> float | None:
    """Seconds into the video where the last still stretch starts, plus `keep`."""
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "freezedetect=n=0.002:d=4"]
        + ["-map", "0:v:0", "-f", "null", "-"],
        capture_output=True,
        text=True,
    ).stderr
    starts = re.findall(r"freeze_start: ([\d.]+)", out)
    ends = re.findall(r"freeze_end: ([\d.]+)", out)
    if len(starts) > len(ends):
        return float(starts[-1]) + keep
    return None


def to_gif(
    video: Path,
    gif: Path,
    width: int = 960,
    fps: int = 10,
    speed: float = 1.0,
    lossy: int = 80,
    upto: float | None = None,
    hold: float = 0.0,
    decimate: str = "hi=512:lo=256:frac=0.5",
) -> None:
    # mpdecimate drops frames that only differ by video noise, so a still screen costs one frame.
    chain = f"setpts=PTS/{speed},fps={fps},mpdecimate={decimate},scale={width}:-1:flags=lanczos"
    with tempfile.TemporaryDirectory() as tmp:
        palette = Path(tmp) / "palette.png"
        raw = Path(tmp) / "raw.gif"
        cut = ["-t", f"{upto:.2f}"] if upto else []
        ff = ["ffmpeg", "-y", "-loglevel", "error", *cut, "-i", str(video)]
        subprocess.run(
            [*ff, "-vf", f"{chain},palettegen=stats_mode=diff", str(palette)], check=True
        )
        subprocess.run(
            [
                *ff,
                "-i",
                str(palette),
                "-lavfi",
                f"{chain}[x];[x][1:v]paletteuse=dither=none:diff_mode=rectangle",
                "-fps_mode",
                "vfr",
                str(raw),
            ],
            check=True,
        )
        if hold:
            # Show the last real frame longer. Both selections read the same file, so every
            # frame stays as recorded and only the last one gets the new delay.
            info = subprocess.run(["gifsicle", "--info", str(raw)], capture_output=True, text=True)
            n = int(re.search(r"(\d+) images?", info.stdout).group(1))
            held = Path(tmp) / "held.gif"
            subprocess.run(
                ["gifsicle", str(raw), f"#0-{n - 2}", f"-d{int(hold * 100)}", str(raw)]
                + [f"#{n - 1}", "-o", str(held)],
                check=True,
            )
            raw = held
        gif.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["gifsicle", "-O3", f"--lossy={lossy}", "--colors", "128", str(raw), "-o", str(gif)],
            check=True,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("video", type=Path)
    parser.add_argument("gif", type=Path)
    parser.add_argument("--seconds", type=float, help="Speed the video up to this length")
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--fps", type=int, default=10)
    parser.add_argument("--trim-tail", action="store_true", help="Cut the still screen at the end")
    parser.add_argument("--hold", type=float, default=0.0, help="Seconds to show the last frame")
    args = parser.parse_args(argv)
    upto = active_end(args.video) if args.trim_tail else None
    length = upto or duration(args.video)
    speed = max(1.0, length / args.seconds) if args.seconds else 1.0
    to_gif(
        args.video,
        args.gif,
        width=args.width,
        fps=args.fps,
        speed=speed,
        upto=upto,
        hold=args.hold,
    )
    size = args.gif.stat().st_size // 1024
    print(f"Wrote {args.gif} ({size} KB, {speed:.1f}x speed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
