"""Roll findings up into one keep, rewrite, throwaway, or check label per file."""

from __future__ import annotations

from collections import defaultdict

from vibexray.model import CATEGORIES, Finding, Part
from vibexray.walker import SourceFile

# A worse label wins when one file carries several findings.
LABEL_RANK = {"keep": 0, "check": 1, "rewrite": 2, "throwaway": 3}

APP_SUFFIXES = (
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".vue",
    ".svelte",
    ".py",
    ".sql",
    ".rules",
)
SKIP_PARTS = ("components/ui/", "test", "spec", ".config.", "vite-env.d.ts")

# Prompt, knowledge-base, and data files hold problems too: invented policies, sample records.
CONTEXT_SUFFIXES = (".md", ".mdx", ".json", ".yaml", ".yml", ".html")
CONTEXT_DIRS = ("knowledge", "kb", "prompt", "data", "seed", "fixture", "mock", "faq", "polic")
NOT_CONTEXT_NAMES = (
    "package.json",
    "tsconfig",
    "jsconfig",
    "components.json",
    "readme",
    "changelog",
    "license",
    "contributing",
    "agents.md",
    "claude.md",
    "gemini.md",
    "index.html",
    "manifest.json",
    "vercel.json",
    ".eslintrc",
)
MAX_CONTEXT = 60


def context_files(files: list[SourceFile]) -> list[str]:
    code = "\n".join(src.text for src in files if src.path.endswith(APP_SUFFIXES))
    out = []
    for src in files:
        low = src.path.lower()
        name = low.rsplit("/", 1)[-1]
        # Dot folders hold the coding agent's instructions and tool configs, not the app.
        if not low.endswith(CONTEXT_SUFFIXES) or low.startswith((".", "docs/")) or "test" in low:
            continue
        if any(n in name for n in NOT_CONTEXT_NAMES):
            continue
        in_data_dir = any(d in part for part in low.split("/")[:-1] for d in CONTEXT_DIRS)
        if in_data_dir or src.path.rsplit("/", 1)[-1] in code:
            out.append(src.path)
    return out[:MAX_CONTEXT]


def build_parts(files: list[SourceFile], findings: list[Finding]) -> list[Part]:
    by_file: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_file[f.file].append(f)

    parts: list[Part] = []
    for src in files:
        if not src.path.endswith(APP_SUFFIXES) or any(s in src.path for s in SKIP_PARTS):
            continue
        hits = by_file.get(src.path, [])
        if not hits:
            parts.append(Part(file=src.path, label="keep"))
            continue
        label = max((h.label for h in hits), key=lambda lbl: LABEL_RANK[lbl])
        reasons = sorted({CATEGORIES[h.category][0] for h in hits})
        parts.append(Part(file=src.path, label=label, reasons=reasons))

    known = {p.file for p in parts}
    for path, hits in by_file.items():
        if path in known:
            continue
        label = max((h.label for h in hits), key=lambda lbl: LABEL_RANK[lbl])
        parts.append(
            Part(file=path, label=label, reasons=sorted({CATEGORIES[h.category][0] for h in hits}))
        )

    parts.sort(key=lambda p: (-LABEL_RANK[p.label], p.file))
    return parts
