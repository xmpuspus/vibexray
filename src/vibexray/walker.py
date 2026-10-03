"""Find the prototype's own source files and detect its stack."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".vercel",
    ".turbo",
    ".cache",
    "dist",
    "build",
    "out",
    "coverage",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "vibexray-report",
    ".expo",
    "ios",
    "android",
}
TEXT_SUFFIXES = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".vue",
    ".svelte",
    ".astro",
    ".py",
    ".sql",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".html",
    ".md",
    ".mdx",
    ".prisma",
    ".env",
    ".example",
    ".local",
    ".sample",
    ".rules",
}
# Files with no useful suffix that still carry risk signals.
TEXT_NAMES = {".gitignore", "Dockerfile", "vercel.json", "netlify.toml"}
SKIP_FILES = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lockb",
    "bun.lock",
    "uv.lock",
    "poetry.lock",
    "Cargo.lock",
}
MAX_BYTES = 400_000
# A project-scope install of this skill carries a copy of vibexray. It is not the PM's code.
SELF_DIRS = (".claude/skills/vibexray/", ".agents/skills/vibexray/")


@dataclass
class SourceFile:
    path: str
    text: str

    @property
    def lines(self) -> list[str]:
        return self.text.splitlines()

    @property
    def suffix(self) -> str:
        return Path(self.path).suffix.lower()


def _is_text_candidate(path: Path) -> bool:
    name = path.name
    if name in SKIP_FILES:
        return False
    if name.startswith(".env") or name in TEXT_NAMES:
        return True
    return path.suffix.lower() in TEXT_SUFFIXES


def collect_files(root: Path) -> list[SourceFile]:
    files: list[SourceFile] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if rel.as_posix().startswith(SELF_DIRS):
            continue
        if not path.is_file() or not _is_text_candidate(path):
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        files.append(SourceFile(path=rel.as_posix(), text=text))
    return files


def _package_deps(root: Path) -> dict[str, str]:
    pkg = root / "package.json"
    if not pkg.is_file():
        return {}
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    deps: dict[str, str] = {}
    for key in ("dependencies", "devDependencies"):
        section = data.get(key)
        if isinstance(section, dict):
            deps.update(section)
    return deps


STACK_MARKERS = [
    ("next", "Next.js"),
    ("vite", "Vite"),
    ("react", "React"),
    ("vue", "Vue"),
    ("svelte", "Svelte"),
    ("@supabase/supabase-js", "Supabase"),
    ("firebase", "Firebase"),
    ("@prisma/client", "Prisma"),
    ("ai", "Vercel AI SDK"),
    ("openai", "OpenAI SDK"),
    ("@anthropic-ai/sdk", "Anthropic SDK"),
    ("langchain", "LangChain"),
    ("@langchain/core", "LangChain"),
    ("lovable-tagger", "Lovable"),
]


def detect_stack(root: Path, files: list[SourceFile]) -> list[str]:
    deps = _package_deps(root)
    stack: list[str] = []
    for dep, label in STACK_MARKERS:
        if dep in deps and label not in stack:
            stack.append(label)
    if any(f.path.endswith(".py") for f in files) and "Python" not in stack:
        stack.append("Python")
    return stack
