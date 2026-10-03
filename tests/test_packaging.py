import filecmp
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from vibexray import __version__

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / "skills" / "vibexray"
SRC = REPO / "src" / "vibexray"
BUNDLE = SKILL / "scripts" / "vibexray"

CLAUDE_PLUGIN = REPO / ".claude-plugin" / "plugin.json"
CLAUDE_MARKET = REPO / ".claude-plugin" / "marketplace.json"
CODEX_PLUGIN = REPO / "plugin.json"
CODEX_MARKET = REPO / ".agents" / "plugins" / "marketplace.json"
MANIFESTS = [CLAUDE_PLUGIN, CLAUDE_MARKET, CODEX_PLUGIN, CODEX_MARKET]


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def py_files(root: Path) -> set[str]:
    return {
        str(p.relative_to(root))
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    }


def frontmatter(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert match, "SKILL.md has no frontmatter"
    return match.group(1)


def test_bundle_matches_src_byte_for_byte():
    assert BUNDLE.is_dir(), "run `make bundle`"
    assert py_files(SRC) == py_files(BUNDLE), "bundled file list differs; run `make bundle`"
    for rel in py_files(SRC):
        assert filecmp.cmp(SRC / rel, BUNDLE / rel, shallow=False), (
            f"{rel} is stale; run `make bundle`"
        )


def test_stale_bundle_is_detected(tmp_path):
    copy = tmp_path / "vibexray"
    shutil.copytree(BUNDLE, copy, ignore=shutil.ignore_patterns("__pycache__"))
    (copy / "__init__.py").write_text((copy / "__init__.py").read_text() + "\n# stale\n")
    assert not filecmp.cmp(SRC / "__init__.py", copy / "__init__.py", shallow=False)


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda p: str(p.relative_to(REPO)))
def test_manifest_parses(path):
    assert isinstance(load(path), dict)


def test_names_match():
    assert load(CLAUDE_PLUGIN)["name"] == "vibexray"
    assert load(CODEX_PLUGIN)["name"] == "vibexray"
    for market in (CLAUDE_MARKET, CODEX_MARKET):
        data = load(market)
        assert data["name"] == "vibexray"
        assert [p["name"] for p in data["plugins"]] == ["vibexray"]


def test_manifest_versions_equal_package_version():
    assert load(CLAUDE_PLUGIN)["version"] == __version__
    assert load(CODEX_PLUGIN)["version"] == __version__


def test_manifest_metadata():
    for path in (CLAUDE_PLUGIN, CODEX_PLUGIN):
        data = load(path)
        assert data["repository"] == "https://github.com/xmpuspus/vibexray"
        assert data["license"] == "MIT"
        assert data["author"]["name"] == "Xavier Puspus"


def test_skill_frontmatter_respects_agentskills_limits():
    text = (SKILL / "SKILL.md").read_text()
    fm = frontmatter(text)
    name = re.search(r"^name:\s*(.+)$", fm, re.M).group(1).strip()
    assert name == "vibexray" == SKILL.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(name) <= 64
    desc = re.search(r"^description:\s*(.+?)(?=^\S|\Z)", fm, re.M | re.S).group(1)
    desc = " ".join(desc.replace(">-", "").split())
    assert 1 <= len(desc) <= 1024, len(desc)
    for phrase in (
        "is this ready for engineering",
        "what is fake in my prototype",
        "hand this off",
        "x-ray my app",
        "vibexray",
    ):
        assert phrase in desc
    assert re.search(r"^license:\s*MIT$", fm, re.M)
    compat = re.search(r"^compatibility:\s*(.+)$", fm, re.M).group(1)
    assert len(compat) <= 500
    assert "metadata:" in fm
    body = text.split("---\n", 2)[2]
    assert len(body.splitlines()) < 150


def test_launcher_runs_version_from_skill_folder_alone(tmp_path):
    copy = tmp_path / "vibexray"
    shutil.copytree(SKILL, copy, ignore=shutil.ignore_patterns("__pycache__"))
    result = subprocess.run(
        [sys.executable, "scripts/run_vibexray.py", "--version"],
        cwd=copy,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "NO_COLOR": "1"},
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert __version__ in result.stdout
