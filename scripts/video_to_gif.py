"""Turn a screen recording into a small GIF for the README.

The script speeds the video up to a target length when asked, then uses ffmpeg
palettegen and gifsicle. It never adds or removes frames by hand.

    uv run python scripts/video_to_gif.py tmp/hero/hero.mp4 docs/hero.gif --seconds 45
"""

from __future__ import annotations

import argparse
import json
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


def to_gif(
    video: Path, gif: Path, width: int = 960, fps: int = 10, speed: float = 1.0, lossy: int = 80
) -> None:
    # mpdecimate drops frames that only differ by video noise, so a still screen costs one frame.
    chain = f"setpts=PTS/{speed},fps={fps},mpdecimate=hi=512:lo=256:frac=0.5,scale={width}:-1:flags=lanczos"
    with tempfile.TemporaryDirectory() as tmp:
        palette = Path(tmp) / "palette.png"
        raw = Path(tmp) / "raw.gif"
        ff = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video)]
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
    args = parser.parse_args(argv)
    speed = 1.0
    if args.seconds:
        speed = max(1.0, duration(args.video) / args.seconds)
    to_gif(args.video, args.gif, width=args.width, fps=args.fps, speed=speed)
    size = args.gif.stat().st_size // 1024
    print(f"Wrote {args.gif} ({size} KB, {speed:.1f}x speed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
