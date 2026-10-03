"""The PM's report: one self-contained HTML file with no network requests."""

from __future__ import annotations

import base64
import mimetypes
from html import escape
from pathlib import Path

from vibexray.model import LABELS, Finding, Page, ScanResult
from vibexray.report.assets import CSS, JS
from vibexray.report.common import (
    LABEL_MEANING,
    LABEL_NAMES,
    by_group,
    cards,
    chat_source,
    found_by,
    headline,
    hide_secrets,
    parts_with,
    plural,
)

EMPTY_FINDINGS = "No fake parts found"
EMPTY_RUN = "The app did not run"
EMPTY_HISTORY = "No build chat found for this folder"

# Long lists show this many rows. The rest sit behind a "Show more" toggle.
SHOWN = 8
SHOWN_PROMPTS = 12
PRIORITY = {"high": "High priority", "medium": "Medium priority", "low": "Low priority"}
RISK = {"high": "High risk", "medium": "Medium risk", "low": "Low risk"}
# A no-break space keeps "4 can break." together, so "4" never ends a line alone.
NB_BREAK = "\u00a0can\u00a0break."


def e(text: object) -> str:
    return escape(hide_secrets(str(text)))


def _where(file: str, line: int | None) -> str:
    return e(f"{file}:{line}" if line else file)


def _more(items: list[str], shown: int, tag: str = "ul", cls: str = "files") -> str:
    head = "".join(items[:shown])
    out = f'<{tag} class="{cls}">{head}</{tag}>' if head else ""
    rest = items[shown:]
    if rest:
        label = f"Show {len(rest):,} more" if head else f"Show all {len(rest):,}"
        out += (
            f'<details class="more"><summary>{label}</summary>'
            f'<{tag} class="{cls}">{"".join(rest)}</{tag}></details>'
        )
    return out


def _section(sid: str, title: str, body: str, sub: str = "") -> str:
    sub_html = f'<p class="sub">{sub}</p>' if sub else ""
    return f'<section id="{sid}" class="sec"><h2>{title}</h2>{sub_html}{body}</section>'


def _h1(r: ScanResult) -> str:
    h1 = e(headline(r)).replace(" can break.", NB_BREAK)
    # A short name like "yana-contabila" must not split at its hyphen. A long name may wrap.
    if len(r.app_name) <= 20:
        h1 = h1.replace(e(r.app_name), f'<span class="nw">{e(r.app_name)}</span>', 1)
    return h1


def _hero(r: ScanResult) -> str:
    fake, risky = parts_with(r, True), parts_with(r, False)
    counts = r.counts()
    n_q = len(r.questions)
    if r.files_scanned == 0:
        lede = "The folder has no source files that vibexray can read."
        step = "Run vibexray again on the folder that holds the app code."
    else:
        lede = (
            f"vibexray read {plural(r.files_scanned, 'file')} "
            f"and flagged {plural(len(r.findings), 'place')} to fix."
        )
        step = "Send <code>handoff.md</code> to your engineer. vibexray has no questions for you."
        if n_q:
            step = (
                f"Answer the {plural(n_q, 'question')} below. "
                "Then send <code>handoff.md</code> to your engineer."
            )

    def stat(n: int, label: str, detail: str, risk: bool) -> str:
        cls = "zero" if n == 0 else "risk" if risk else ""
        detail = detail if n else "None found"
        return (
            f'<div class="stat"><div class="n {cls}">{n:,}</div>'
            f'<div class="l">{label}</div><div class="d">{detail}</div></div>'
        )

    stats = (
        stat(
            fake,
            "fake part" if fake == 1 else "fake parts",
            f"{plural(counts['fake'], 'place')} with sample data, fake actions, or fixed values",
            True,
        )
        + stat(
            risky,
            "part can break" if risky == 1 else "parts can break",
            f"{plural(counts['security'], 'security risk')} and {plural(counts['ai'], 'AI risk')}",
            True,
        )
        + stat(
            n_q,
            "decision for you" if n_q == 1 else "decisions for you",
            "Answer them before the build starts",
            False,
        )
    )
    toc = "".join(
        f'<li><a href="#{sid}">{name}</a></li>'
        for sid, name in (
            ("decisions", "Decisions"),
            ("parts", "Real and fake"),
            ("fake", "What is fake"),
            ("risks", "What can break"),
            ("app", "What the app does"),
            ("chat", "Build chat"),
            ("engineer", "For your engineer"),
        )
    )
    return (
        f'<div class="hero"><h1>{_h1(r)}</h1><p class="lede">{lede}</p>'
        f'<div class="stats">{stats}</div>'
        f'<p class="next"><b>Next step.</b> {step}</p><ul class="toc">{toc}</ul></div>'
    )


def _decisions(r: ScanResult) -> str:
    if not r.questions:
        return _section(
            "decisions",
            "You have no open decisions",
            '<p class="empty">No open questions found. '
            "vibexray found nothing that needs your answer before the build.</p>",
        )
    items = []
    for i, q in enumerate(r.questions, start=1):
        src = f"From <code>{_where(q.file, q.line)}</code>" if q.file else "From your build chat"
        items.append(
            f'<li class="q"><span class="qn">{i}</span><div><p class="qt">{e(q.text)}</p>'
            f'<p class="qw">{e(q.why)}</p><p class="qf">{src}</p></div></li>'
        )
    n = len(r.questions)
    title = f"You have {plural(n, 'decision')} to make"
    sub = "Answer these before your engineer starts. The most important come first."
    return _section("decisions", title, f'<ol class="qs">{"".join(items)}</ol>', sub)


def _parts(r: ScanResult) -> str:
    if not r.parts:
        return _section(
            "parts",
            "No app code found",
            '<p class="empty">vibexray found no source files to sort into keep, rewrite, '
            "throw away, or check. Check that you scanned the right folder.</p>",
        )
    labels = r.label_counts()
    total = len(r.parts)
    other = total - labels["keep"]
    if other:
        title = f"Keep {labels['keep']:,} parts. Rewrite, remove, or check the other {other:,}."
    else:
        title = f"Keep all {plural(total, 'part')}. vibexray found nothing to rewrite or remove."
    sub = (
        "A part is one file of app code. Each part gets one label. The worst finding in it decides."
    )
    bar = "".join(
        f'<span class="b-{lbl}" style="flex:{labels[lbl]} 0 0"></span>'
        for lbl in LABELS
        if labels[lbl]
    )
    aria = ", ".join(f"{LABEL_NAMES[lbl]} {labels[lbl]}" for lbl in LABELS)
    legend = "".join(
        f'<li><i class="b-{lbl}"></i>{LABEL_NAMES[lbl]} {labels[lbl]:,}</li>' for lbl in LABELS
    )
    blocks = []
    for lbl in LABELS:
        parts = [p for p in r.parts if p.label == lbl]
        rows = []
        for p in parts:
            why = f'<span class="why">{e(", ".join(p.reasons))}</span>' if p.reasons else ""
            rows.append(f"<li><code>{e(p.file)}</code>{why}</li>")
        if not rows:
            name = "throw away" if lbl == "throwaway" else lbl
            body = f'<p class="none">No parts to {name}.</p>'
        else:
            body = _more(rows, 0 if lbl == "keep" else SHOWN)
        blocks.append(
            f'<div class="lab {lbl}"><h3>{LABEL_NAMES[lbl]} <span class="c">{len(parts):,}</span>'
            f'</h3><p class="m">{LABEL_MEANING[lbl]}</p>{body}</div>'
        )
    body = (
        f'<div class="bar" role="img" aria-label="{aria}">{bar}</div>'
        f'<ul class="legend">{legend}</ul><div class="labels">{"".join(blocks)}</div>'
    )
    return _section("parts", title, body, sub)


def _location(f: Finding, show_fix: bool) -> str:
    rel = ""
    if f.related_file:
        rel = f'<p class="rel">Related: <code>{_where(f.related_file, f.related_line)}</code></p>'
        if f.related_snippet:
            rel += f"<pre><code>{e(f.related_snippet)}</code></pre>"
    own = f'<p class="own"><b>Fix:</b> {e(f.engineer_text)}</p>' if show_fix else ""
    return (
        f"<li><details><summary><code>{_where(f.file, f.line)}</code>"
        f'<span class="show"><span class="op">Show code</span><span class="cl">Hide code</span>'
        "</span></summary>"
        f"<pre><code>{e(f.snippet)}</code></pre>{rel}{own}</details></li>"
    )


def _card(fs: list[Finding], words: dict[str, str], heading: str) -> str:
    first = fs[0]
    same_fix = len({f.engineer_text for f in fs}) == 1
    fix = (
        f'<p class="fix"><b>For the engineer:</b> {e(first.engineer_text)}</p>' if same_fix else ""
    )
    files = len({f.file for f in fs})
    count = plural(len(fs), "place")
    if files > 1:
        count += f" in {files:,} files"
    sev = first.severity if first.severity in words else "low"
    src_cls = "unchecked" if found_by(first).endswith("not checked") else ""
    locs = [_location(f, not same_fix) for f in fs]
    return (
        f'<article class="card {sev}"><div class="tags"><span class="tag {sev}">'
        f'{words[sev]}</span><span class="cnt">{count}</span>'
        f'<span class="src {src_cls}">{found_by(first)}</span></div>'
        f'<{heading} class="ct">{e(first.pm_text)}</{heading}>{fix}'
        f"{_more(locs, SHOWN, cls='locs')}</article>"
    )


def _checked(r: ScanResult, claim: str) -> str:
    # An empty folder had nothing to check, so a sentence about checks would be false.
    return claim if r.files_scanned else "vibexray found no source files to check in this folder."


def _fake(r: ScanResult) -> str:
    found = by_group(r, "fake")
    if not found:
        return _section(
            "fake",
            EMPTY_FINDINGS,
            f'<p class="empty">{_checked(r, "It found no sample data, fake buttons, or fixed values posing as real ones.")}</p>',
        )
    files = len({f.file for f in found})
    verb = "is" if len(found) == 1 else "are"
    title = f"{plural(len(found), 'place')} in {plural(files, 'part')} {verb} fake"
    sub = (
        "Each place shows sample data, fakes an action, or fixes a value in the code. "
        "Open a place to see the code."
    )
    return _section("fake", title, "".join(_card(c, PRIORITY, "h3") for c in cards(found)), sub)


def _risks(r: ScanResult) -> str:
    sec, ai = by_group(r, "security"), by_group(r, "ai")
    blocks = []
    for name, found, empty in (
        (
            "Security",
            sec,
            "No security risks found. "
            + _checked(r, "vibexray checked logins, database rules, and keys."),
        ),
        (
            "The AI",
            ai,
            "No AI risks found. "
            + _checked(r, "vibexray checked how the app calls the AI and what its tools do."),
        ),
    ):
        if found:
            body = "".join(_card(c, RISK, "h4") for c in cards(found))
            blocks.append(f"<h3>{name}: {plural(len(found), 'place')}</h3>{body}")
        else:
            blocks.append(f'<h3>{name}</h3><p class="empty">{empty}</p>')
    found = sec + ai
    if found:
        files = len({f.file for f in found})
        title = f"{plural(len(found), 'place')} in {plural(files, 'part')} can break"
        sub = (
            "A security risk lets the wrong person in. An AI risk lets the bot do the wrong thing."
        )
    else:
        title = "Nothing found that can break"
        sub = _checked(r, "vibexray found no security or AI risk in the code it read.")
    return _section("risks", title, "".join(blocks), sub)


def _image(path: str | None) -> str:
    # Screenshots go into the file as data, so the report stays one file with no requests.
    if not path:
        return '<p class="none">No screenshot for this page.</p>'
    file = Path(path)
    if not file.is_file():
        return '<p class="none">The screenshot file is missing.</p>'
    mime = mimetypes.guess_type(file.name)[0] or "image/png"
    data = base64.b64encode(file.read_bytes()).decode("ascii")
    return f'<img alt="Screenshot of this page" src="data:{mime};base64,{data}">'


def _chips(items: list[str], none: str, cls: str = "chips") -> str:
    if not items:
        return f'<p class="none">{none}</p>'
    return f'<ul class="{cls}">{"".join(f"<li>{e(i)}</li>" for i in items)}</ul>'


def _page(p: Page) -> str:
    status = f" returned {p.status}" if p.status else ""
    title = e(p.title) if p.title else f"<code>{e(p.path)}</code>"
    return (
        f'<div class="page">{_image(p.screenshot)}<h3>{title}</h3>'
        f'<p class="none"><code>{e(p.path)}</code>{status}</p>'
        f'<p class="k">Buttons</p>{_chips(p.buttons, "No buttons found.")}'
        f'<p class="k">Inputs</p>{_chips(p.inputs, "No inputs found.")}'
        f'<p class="k">Errors in the browser</p>'
        f"{_chips(p.console_errors, 'No errors.', 'errs')}</div>"
    )


def _app(r: ScanResult) -> str:
    run = r.app_run
    if run.state == "ran":
        how = f" with <code>{e(run.command)}</code>" if run.command else ""
        at = f" at <code>{e(run.url)}</code>" if run.url else ""
        sub = f"vibexray started the app{how}{at} and opened each page it found."
        if not run.pages:
            body = '<p class="empty">The app ran, but vibexray found no pages to open.</p>'
            return _section("app", "The app ran with no pages to open", body, sub)
        pages = "".join(_page(p) for p in run.pages)
        title = f"The app ran. vibexray opened {plural(len(run.pages), 'page')}."
        return _section("app", title, f'<div class="pages">{pages}</div>', sub)
    booted = run.state == "could_not_boot"
    title = "The app did not start" if booted else "vibexray did not start the app"
    reason = f" {e(run.reason)}" if run.reason else ""
    body = (
        f'<p class="empty">{EMPTY_RUN}{"." if booted else " in this scan."}{reason} '
        "The rest of this report comes from reading the code.</p>"
    )
    if run.missing_env:
        body += f'<p class="k">It needs these settings first</p>{_chips(run.missing_env, "")}'
    if run.command:
        body += f'<p class="sub">vibexray tried <code>{e(run.command)}</code>.</p>'
    return _section("app", title, body)


def _chat(r: ScanResult) -> str:
    h = r.history
    if h.source == "none" or not h.prompts:
        note = f" {e(h.note)}" if h.note else ""
        skipped = h.note.startswith("Skipped")
        title = "vibexray skipped your build chat" if skipped else EMPTY_HISTORY
        body = (
            f'<p class="empty">{EMPTY_HISTORY}{" in this scan" if skipped else ""}.{note} '
            "vibexray looks for Claude Code and Codex chats that ran in this folder.</p>"
        )
        return _section("chat", title, body)
    # The same prompt can reach both Claude Code and Codex. Show it once, with a count.
    seen: dict[tuple[str, str], int] = {}
    for p in h.prompts:
        seen[(p.when, p.text)] = seen.get((p.when, p.text), 0) + 1
    rows = []
    for (when, text), times in seen.items():
        rep = f'<p class="rep">You sent this {times} times.</p>' if times > 1 else ""
        rows.append(f"<li><time>{e(when or 'No date')}</time><div><p>{e(text)}</p>{rep}</div></li>")
    title = f"You sent {plural(len(h.prompts), 'prompt')} in {plural(h.sessions, 'build chat')}"
    sub = f"From {e(chat_source(h.source))}. These are your own words, oldest first."
    return _section("chat", title, _more(rows, SHOWN_PROMPTS, "ol", "chat"), sub)


def _engineer(r: ScanResult) -> str:
    if r.files_scanned == 0:
        body = (
            '<p class="callout">Run vibexray again on the folder that holds the app code. '
            "Then send <code>handoff.md</code> to your engineer. Today it lists no work.</p>"
        )
        return _section("engineer", "The handoff has no work for your engineer yet", body)
    labels = r.label_counts()
    todo = "".join(
        f"<li><b>{labels[lbl]:,}</b> {'part' if labels[lbl] == 1 else 'parts'} {text}</li>"
        for lbl, text in (
            ("rewrite", "to rewrite first"),
            ("throwaway", "to remove before launch"),
            ("check", "for a person to check"),
            ("keep", "to build on"),
        )
    )
    body = (
        '<p class="callout">Send <code>handoff.md</code> to your engineer. It sits in the same '
        "folder as this report. It lists every file and line, how to fix each one, and your "
        "open questions. A coding agent can read it too.</p>"
        f'<h3>What the handoff asks for</h3><ul class="todo">{todo}</ul>'
        '<p class="sub after">The file <code>vibexray.json</code> holds the same data for other tools.</p>'
    )
    return _section("engineer", "Your engineer starts from handoff.md", body)


def render_html(result: ScanResult) -> str:
    r = result
    stack = ", ".join(r.stack) if r.stack else "Stack not found"
    meta = f"{e(r.app_name)} · {e(r.generated_at)} · {e(stack)}"
    sections = _decisions(r) + _parts(r) + _fake(r) + _risks(r) + _app(r) + _chat(r) + _engineer(r)
    foot = (
        f"vibexray {e(r.version)} read {e(r.app_name)} on {e(r.generated_at)}. "
        "A scan reads code. It cannot prove that an app is safe."
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<link rel="icon" href="data:,">'
        f"<title>vibexray: {e(r.app_name)}</title><style>{CSS}</style></head><body>"
        f'<header class="top"><div class="wrap"><span class="brand">vibexray report</span>'
        f'<span class="meta">{meta}</span></div></header>'
        f'<main class="wrap">{_hero(r)}{sections}</main>'
        f'<footer class="foot"><div class="wrap">{foot}</div></footer>'
        f"<script>{JS}</script></body></html>\n"
    )
