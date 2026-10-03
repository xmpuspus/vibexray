"""Turn findings and the build chat into questions the PM answers before handoff."""

from __future__ import annotations

import re

from vibexray.model import Finding, History, Question

MAX_QUESTIONS = 10
MAX_WORDS = 25
_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Words in a build-chat prompt that state a rule the code should follow.
_RULE_WORD = re.compile(
    r"\b(only|never|must|limit\w*|approv\w*|manager\w*|up to|no more than)\b", re.I
)
_CLAUSE_SPLIT = re.compile(r"[.;!?\n]+|,")
_LEAD_FILLER = re.compile(r"^(and|but|so|then|also)\s+", re.I)
_QUOTE_WORDS = 8

_STOP = frozenset(
    [
        "only",
        "never",
        "must",
        "limit",
        "over",
        "need",
        "needs",
        "with",
        "that",
        "this",
        "have",
        "when",
        "from",
        "into",
        "will",
        "should",
        "your",
        "they",
        "them",
        "then",
        "than",
        "what",
        "which",
        "there",
        "their",
        "would",
        "could",
        "about",
        "after",
        "before",
        "each",
        "every",
        "code",
        "also",
        "just",
        "make",
        "sure",
        "only",
        "can",
        "does",
    ]
)
_STEM = 5

_NUMBER = re.compile(
    r"\$?\d+(?:[.,]\d+)?%?(?:\s?(days?|hours?|minutes?|seconds?|weeks?|months?|years?|items?|dollars?|usd))?",
    re.I,
)
_ROUTE = re.compile(r"""["'](/[A-Za-z0-9_\-/{}:.]*)["']""")
_TOOL_NAME = re.compile(
    r"""name\s*[:=]\s*["']([A-Za-z_][\w\-]*)["']|(?:def|function)\s+([A-Za-z_]\w*)"""
    r"""|([A-Za-z_]\w*)\s*[:=]\s*(?:tool|createTool|defineTool)\("""
)
_PAGE_FILES = ("route", "page")


def _words(text: str) -> int:
    return len(text.split())


def _clip(text: str, budget: int) -> str:
    words = text.split()
    return text if len(words) <= budget else " ".join(words[:budget]) + "..."


def _prompt_rule(f: Finding) -> Question:
    quote = re.sub(r"^[\s\-*#>/]+", "", f.snippet).strip(" `'\";,.")
    quote = _clip(quote, 10)
    return Question(
        text=f"Your bot's prompt says '{quote}'. The code does not enforce it. Should the code enforce it?",
        why="A rule that lives only in the prompt can be talked around. Code is the only place it always holds.",
        source="finding",
        file=f.file,
        line=f.line,
    )


def _sample_data(f: Finding, subject: str) -> Question:
    where = f.related_file or f.file
    return Question(
        text=f"{subject} sample data from {where}. Where does the real data come from?",
        why="The engineer needs the real source before the sample data can go.",
        source="finding",
        file=f.file,
        line=f.line,
    )


def _web_address(path: str) -> str | None:
    """Next.js turns app/api/orders/[id]/route.ts and pages/api/orders.ts into a URL."""
    parts = path.split("/")
    stem = parts[-1].rsplit(".", 1)[0]
    if "app" in parts and stem in _PAGE_FILES:
        segs = parts[parts.index("app") + 1 : -1]
    elif "pages" in parts:
        segs = parts[parts.index("pages") + 1 : -1] + ([] if stem == "index" else [stem])
    else:
        return None
    # A folder in brackets, such as (dashboard), groups files and is not part of the URL.
    return "/" + "/".join(s for s in segs if not (s.startswith("(") and s.endswith(")")))


def _auth_target(f: Finding) -> str:
    route = _ROUTE.search(f.snippet)
    return route.group(1) if route else _web_address(f.file) or f.file


def _auth(gaps: list[Finding]) -> Question:
    places = list(dict.fromkeys(_auth_target(f) for f in gaps))
    if len(places) == 1:
        text = f"Who may open {places[0]}?"
        why = "Nothing in the code checks who is asking, so anyone who finds it can use it."
    else:
        rest = (
            f"and {places[1]}"
            if len(places) == 2
            else f"{places[1]}, and {len(places) - 2} more places"
        )
        sep = " " if len(places) == 2 else ", "
        text = f"Who may open {places[0]}{sep}{rest}?"
        why = (
            f"Nothing in the code checks who is asking at {len(places)} places, "
            "so anyone who finds them can use them."
        )
    return Question(text=text, why=why, source="finding", file=gaps[0].file, line=gaps[0].line)


def _human_review(f: Finding) -> Question:
    m = _TOOL_NAME.search(f.snippet)
    name = next((g for g in m.groups() if g), None) if m else None
    text = (
        f"Should a person approve '{re.sub(r'[_-]+', ' ', name)}' before it happens?"
        if name
        else f"The AI acts on its own in {f.file}. Should a person approve its actions first?"
    )
    return Question(
        text=text,
        why="The AI does this on its own today. A person check costs time but stops a bad action.",
        source="finding",
        file=f.file,
        line=f.line,
    )


def _first_number(text: str | None) -> tuple[str, str] | None:
    m = _NUMBER.search(text or "")
    if not m:
        return None
    unit = (m.group(1) or "").lower().rstrip("s")
    return m.group(0).strip(), unit


def _conflict(f: Finding) -> Question | None:
    a, b = _first_number(f.snippet), _first_number(f.related_snippet)
    if not a or not b or a[1] != b[1]:
        return None
    if a[0].lower() == b[0].lower():
        return None
    return Question(
        text=f"Which is right: {a[0]} or {b[0]}?",
        why="The same kind of value is set to two different numbers. The code and the user will disagree.",
        source="finding",
        file=f.file,
        line=f.line,
    )


def _from_finding(f: Finding) -> Question | None:
    if f.category == "ai_prompt_only_rule":
        return _prompt_rule(f)
    if f.category == "mock_data":
        return _sample_data(f, "The app uses")
    if f.category == "ai_fake_tool":
        return _sample_data(f, "This tool returns")
    if f.category == "ai_no_human_review":
        return _human_review(f)
    if f.category == "hardcoded_config" and f.related_snippet:
        return _conflict(f)
    return None


def _stems(text: str) -> set[str]:
    out = set()
    for w in re.findall(r"[a-z]+", text.lower().replace("'s", "")):
        if len(w) >= 4 and w not in _STOP:
            out.add(w[:_STEM])
    return out


def _short_quote(clause: str) -> str:
    words = clause.split()
    if len(words) <= _QUOTE_WORDS:
        return clause
    tail = words[-_QUOTE_WORDS:]
    if _RULE_WORD.search(" ".join(tail)):
        return " ".join(tail)
    first = next((i for i, w in enumerate(words) if _RULE_WORD.search(w)), 0)
    return " ".join(words[first : first + _QUOTE_WORDS])


def _chat_questions(findings: list[Finding], history: History) -> list[Question]:
    covered = set()
    for f in findings:
        covered |= _stems(f"{f.snippet} {f.pm_text} {f.engineer_text} {f.related_snippet or ''}")
    out = []
    for prompt in history.prompts:
        for raw in _CLAUSE_SPLIT.split(prompt.text):
            clause = _LEAD_FILLER.sub("", raw.strip())
            if not clause or not _RULE_WORD.search(clause):
                continue
            # A rule counts as covered when a finding talks about the same things.
            if len(_stems(clause) & covered) >= 2:
                continue
            quote = _short_quote(clause).strip(" '\"")
            out.append(
                Question(
                    text=f"In your build chat you asked: '{quote}'. "
                    "vibexray found no code for it. Is it still in scope?",
                    why=f"You wrote this rule on {prompt.when or 'an earlier day'}. "
                    "The scan found no matching check in the code.",
                    source="history",
                )
            )
    return out


def build_questions(findings: list[Finding], history: History) -> list[Question]:
    ranked = sorted(findings, key=lambda f: _SEVERITY_ORDER.get(f.severity, 3))
    gaps = [f for f in ranked if f.category == "auth_gap"]
    questions = []
    for f in ranked:
        # One question covers every open place, so the PM does not answer the same thing 8 times.
        if f.category == "auth_gap":
            if f is gaps[0]:
                questions.append(_auth(gaps))
        elif q := _from_finding(f):
            questions.append(q)
    questions += _chat_questions(findings, history)
    seen: set[str] = set()
    out = []
    for q in questions:
        if q.text in seen:
            continue
        seen.add(q.text)
        out.append(q)
    return out[:MAX_QUESTIONS]
