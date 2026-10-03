"""The engineer's handoff. A coding agent reads it too, so every fact names a file and a line."""

from __future__ import annotations

import re

from vibexray.model import GROUPS, LABELS, Finding, ScanResult
from vibexray.report.common import (
    APP_STATES,
    LABEL_MEANING,
    LABEL_NAMES,
    app_line,
    by_group,
    chat_source,
    found_by,
    hide_secrets,
    plural,
)

GROUP_TITLES = {"fake": "Fake", "security": "Security", "ai": "AI"}
FENCE_LANG = {
    ".ts": "ts",
    ".tsx": "tsx",
    ".js": "js",
    ".jsx": "jsx",
    ".mjs": "js",
    ".cjs": "js",
    ".py": "python",
    ".sql": "sql",
    ".vue": "vue",
    ".svelte": "svelte",
    ".json": "json",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def _code(text: str) -> str:
    text = hide_secrets(text)
    ticks = max((len(m) for m in re.findall(r"`+", text)), default=0)
    fence = "`" * ticks + "`"
    pad = " " if ticks else ""
    return f"{fence}{pad}{text}{pad}{fence}"


def _block(text: str, file: str) -> list[str]:
    # A fence must be longer than any backtick run inside the snippet.
    text = hide_secrets(text)
    ticks = max((len(m) for m in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, ticks + 1)
    suffix = "." + file.rsplit(".", 1)[-1] if "." in file else ""
    return [f"{fence}{FENCE_LANG.get(suffix, '')}", text, fence]


def _where(file: str, line: int | None) -> str:
    return _code(f"{file}:{line}" if line else file)


def _summary(r: ScanResult) -> list[str]:
    c, lbl = r.counts(), r.label_counts()
    stack = ", ".join(r.stack) if r.stack else "not detected"
    run = app_line(r)
    text = (
        f"vibexray {r.version} scanned `{r.app_name}` on {r.generated_at}. "
        f"It read {plural(r.files_scanned, 'file')}. Stack: {stack}. "
        f"It found {plural(len(r.findings), 'finding')}: {c['fake']} fake, "
        f"{c['security']} security, {c['ai']} AI. "
        f"Parts: keep {lbl['keep']}, rewrite {lbl['rewrite']}, "
        f"throw away {lbl['throwaway']}, check {lbl['check']}. "
        f"App run: {run} Open questions for the PM: {len(r.questions)}."
    )
    return [hide_secrets(text), ""]


def _parts(r: ScanResult) -> list[str]:
    out = [
        "## Parts map",
        "",
        "A part is one file. The worst finding in a file decides its label.",
        "",
    ]
    for lbl in LABELS:
        parts = [p for p in r.parts if p.label == lbl]
        out += [f"### {LABEL_NAMES[lbl]} ({len(parts)})", "", LABEL_MEANING[lbl], ""]
        if not parts:
            out += ["None.", ""]
            continue
        for p in parts:
            why = f": {', '.join(p.reasons)}" if p.reasons else ""
            out.append(f"- {_code(p.file)}{why}")
        out.append("")
    return out


def _finding(f: Finding) -> list[str]:
    out = [f"#### `{f.rule_id}` at {_where(f.file, f.line)}", ""]
    if f.related_file:
        out.append(f"- Related: {_where(f.related_file, f.related_line)}")
    out += [
        f"- {found_by(f)}.",
        f"- Severity: {f.severity}. Label: {LABEL_NAMES.get(f.label, f.label)}.",
        f"- The PM sees: {hide_secrets(f.pm_text)}",
        f"- Fix: {hide_secrets(f.engineer_text)}",
        "",
        *_block(f.snippet, f.file),
        "",
    ]
    if f.related_snippet and f.related_file:
        out += ["Related code:", "", *_block(f.related_snippet, f.related_file), ""]
    return out


def _findings(r: ScanResult) -> list[str]:
    out = ["## Findings", ""]
    for group in GROUPS:
        found = by_group(r, group)
        out += [f"### {GROUP_TITLES[group]} ({len(found)})", ""]
        if not found:
            out += [f"No {GROUP_TITLES[group].lower() if group != 'ai' else 'AI'} findings.", ""]
            continue
        for f in found:
            out += _finding(f)
    return out


def _rejected(r: ScanResult) -> list[str]:
    # The engineer sees every rule finding that the review removed, and why.
    if not r.rejected:
        return []
    n = len(r.rejected)
    out = [
        "## Rule findings the AI review removed",
        "",
        f"The AI review removed {plural(n, 'rule finding')} as false alarms. "
        "Check each reason before you trust it.",
        "",
    ]
    for rej in r.rejected:
        f = rej.finding
        out.append(f"- {_where(f.file, f.line)} `{f.rule_id}`: {hide_secrets(rej.reason)}")
    return out + [""]


def _app(r: ScanResult) -> list[str]:
    run = r.app_run
    out = ["## What the app does", ""]
    state = APP_STATES.get(run.state, "The app did not run.")
    out.append(f"{state} {hide_secrets(run.reason)}".strip())
    out.append("")
    if run.command:
        out.append(f"- Command: {_code(run.command)}")
    if run.url:
        out.append(f"- URL: {_code(run.url)}")
    if run.missing_env:
        out.append(f"- Missing settings: {', '.join(_code(v) for v in run.missing_env)}")
    if run.command or run.url or run.missing_env:
        out.append("")
    if run.state == "ran" and not run.pages:
        out += ["No pages found.", ""]
    for p in run.pages:
        status = f" (status {p.status})" if p.status else ""
        title = f" {hide_secrets(p.title)}" if p.title else ""
        out += [f"### {_code(p.path)}{title}{status}", ""]
        for name, items in (
            ("Buttons", p.buttons),
            ("Inputs", p.inputs),
            ("Console errors", p.console_errors),
        ):
            out.append(f"- {name}: {'none' if not items else len(items)}")
            out += [f"  - {_code(i)}" for i in items]
        out.append("")
    return out


def _questions(r: ScanResult) -> list[str]:
    out = ["## Open questions for the PM", ""]
    if not r.questions:
        return [*out, "No open questions.", ""]
    for i, q in enumerate(r.questions, start=1):
        src = f"Source: {_where(q.file, q.line)}" if q.file else "Source: the PM's build chat"
        out += [f"{i}. {hide_secrets(q.text)}", f"   Why: {hide_secrets(q.why)} {src}."]
    return [*out, ""]


def _chat(r: ScanResult) -> list[str]:
    h = r.history
    out = ["## What the PM asked for in the build chat", ""]
    if h.source == "none" or not h.prompts:
        return [*out, f"No build chat found for this folder. {h.note}".strip(), ""]
    out += [f"From {chat_source(h.source)}, {plural(h.sessions, 'chat')}, oldest first.", ""]
    for p in h.prompts:
        text = hide_secrets(p.text).replace("\n", " ")
        out.append(f"- {p.when or 'No date'}: {text}")
    return [*out, ""]


AGENT_STEPS = [
    "Do not trust the Throw away parts. They show sample data or fake an action. "
    "Do not build on them.",
    "Fix the Rewrite parts first. Start with high severity findings.",
    "Keep the Keep parts. Change them only when a fix needs it.",
    "Treat Check parts as unknown until a person reads them.",
    "Ask the PM the open questions before you build. Do not guess the answers.",
    "Each finding names a file and a line. Read the code there before you change it.",
]


def render_markdown(result: ScanResult) -> str:
    r = result
    lines = [f"# Handoff: {r.app_name}", "", *_summary(r)]
    lines += _parts(r) + _findings(r) + _rejected(r) + _app(r) + _questions(r) + _chat(r)
    lines += ["## Instructions for a coding agent", ""]
    lines += [f"{i}. {step}" for i, step in enumerate(AGENT_STEPS, start=1)]
    return "\n".join(lines) + "\n"
