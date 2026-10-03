"""Copy src/vibexray into the skill folder and write the launcher."""

import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "vibexray"
SKILL_SCRIPTS = REPO / "skills" / "vibexray" / "scripts"
DEST = SKILL_SCRIPTS / "vibexray"

LAUNCHER = '''"""Run vibexray from this skill folder without installing it."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vibexray.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
'''


def bundle() -> None:
    if DEST.exists():
        shutil.rmtree(DEST)
    shutil.copytree(SRC, DEST, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    (SKILL_SCRIPTS / "run_vibexray.py").write_text(LAUNCHER)
    print(f"Bundled {SRC.relative_to(REPO)} into {DEST.relative_to(REPO)}")


if __name__ == "__main__":
    bundle()
