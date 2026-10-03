"""AI risks: browser calls, tools with no limit, rules that live only in the prompt."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from vibexray.model import Finding
from vibexray.rules.base import Rule
from vibexray.rules.util import (
    ENVFILE,
    SRC,
    UI,
    code_only,
    custom_rule,
    function_bodies,
    is_client,
    line_of,
    line_rule,
    live,
    match_close,
)
from vibexray.walker import SourceFile

PROVIDERS = (
    "OPENAI|ANTHROPIC|CLAUDE|GEMINI|GOOGLE_AI|GROQ|OPENROUTER|MISTRAL|COHERE|DEEPSEEK|XAI|REPLICATE"
    "|TOGETHER|PERPLEXITY|ELEVENLABS|HUGGING"
)
MONEY_TOOL = re.compile(
    r"refund|charge|pay|transfer|payout|credit|discount|price|invoice|delete|cancel", re.I
)
CHANGE_TOOL = re.compile(
    r"refund|charge|pay|transfer|payout|credit|discount|price|invoice|delete|cancel|order|book|update|send|create"
    r"|adjust|withdraw|deposit",
    re.I,
)
ACTION_TOOL = re.compile(
    r"send|email|sms|refund|charge|payout|transfer|delete|remove|cancel|update|book|post|publish|reply|pay",
    re.I,
)
GATE_GLOBAL = re.compile(
    r"toolApproval|needsApproval|requireApproval|requires_approval|human_?approval|addToolApprovalResponse"
    r"|\binterrupt\(|dryRun|pending_?approval|awaiting_?approval|\bapprove\w*\("
)
GATE_RAW = re.compile(
    r"awaiting_?(?:customer_|human_)?approval|pending_?approval|needs_?approval|requires_?approval"
)
GATE_LOCAL = re.compile(r"\b(?:confirm|confirmed|approved|approval|human|manager)\b", re.I)
GENERIC = {
    "get",
    "set",
    "find",
    "list",
    "lookup",
    "search",
    "check",
    "fetch",
    "read",
    "create",
    "update",
    "issue",
    "make",
    "send",
    "call",
    "tool",
    "info",
    "data",
    "order",
    "orders",
}

_FUNC_TYPE = re.compile(r"""type\s*:\s*['"]function['"]""")
_INPUT_SCHEMA = re.compile(r"\binput_schema\b")
_VERCEL = re.compile(r"\b(\w+)\s*:\s*tool\(\s*\{")
_DEFINE = re.compile(r"\b(?:defineTool|createTool|registerTool|tool)\(\s*\{")
_NAME = re.compile(r"""\bname\s*:\s*['"](\w+)['"]""")
_HANDLER_MAP = re.compile(
    r"\b(?:handlers|toolHandlers|HANDLERS|TOOL_HANDLERS|toolMap|registry)\s*(?::[^=\n]+)?=\s*\{"
)
_PY_TOOL = re.compile(
    r"^@(?:\w+\.)?tool\b[^\n]*\n(?:@[^\n]*\n)*(?:async\s+)?def\s+(\w+)\(([^)]*)\)", re.M
)


@dataclass
class Tool:
    name: str
    file: SourceFile
    line: int
    schema: str = ""
    handlers: list[tuple[SourceFile, int, int]] = field(default_factory=list)
    start_line: int = 0
    end_line: int = 0

    @property
    def raw(self) -> str:
        return "\n".join(f.text[a:b] for f, a, b in self.handlers)

    @property
    def code(self) -> str:
        return "\n".join(code_only(f.text)[a:b] for f, a, b in self.handlers)


def _enclosing_object(code: str, pos: int) -> tuple[int, int] | None:
    depth = 0
    for i in range(pos - 1, -1, -1):
        c = code[i]
        if c == "}":
            depth += 1
        elif c == "{":
            if depth == 0:
                end = match_close(code, i)
                return (i, end) if end else None
            depth -= 1
    return None


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(w.title() for w in rest)


def _after_key(code: str, obj: tuple[int, int], keys: str) -> tuple[int, int] | None:
    """Span of the function value for execute, run, or handler inside a tool object."""
    m = re.search(rf"\b(?:{keys})\s*[:(]", code[obj[0] : obj[1]])
    if not m:
        return None
    return (obj[0] + m.start(), obj[1])


def _definitions(files: list[SourceFile]) -> list[Tool]:
    tools: list[Tool] = []
    for f in live(files, UI):
        code = code_only(f.text)
        for m in _FUNC_TYPE.finditer(f.text):
            obj = _enclosing_object(code, m.start())
            if not obj or "parameters" not in code[obj[0] : obj[1]]:
                continue
            nm = _NAME.search(f.text, obj[0], obj[1])
            if nm:
                tools.append(
                    Tool(
                        nm.group(1),
                        f,
                        line_of(f.text, nm.start()),
                        f.text[obj[0] : obj[1]],
                        start_line=line_of(f.text, obj[0]),
                        end_line=line_of(f.text, obj[1]),
                    )
                )
        for m in _INPUT_SCHEMA.finditer(f.text):
            obj = _enclosing_object(code, m.start())
            nm = _NAME.search(f.text, obj[0], obj[1]) if obj else None
            if obj and nm:
                tools.append(
                    Tool(
                        nm.group(1),
                        f,
                        line_of(f.text, nm.start()),
                        f.text[obj[0] : obj[1]],
                        start_line=line_of(f.text, obj[0]),
                        end_line=line_of(f.text, obj[1]),
                    )
                )
        for m in _VERCEL.finditer(f.text):
            start = f.text.index("{", m.end() - 2)
            end = match_close(code, start)
            if end:
                t = Tool(
                    m.group(1),
                    f,
                    line_of(f.text, m.start()),
                    f.text[start:end],
                    start_line=line_of(f.text, start),
                    end_line=line_of(f.text, end),
                )
                span = _after_key(code, (start, end), "execute")
                if span:
                    t.handlers.append((f, span[0], span[1]))
                tools.append(t)
        for m in _DEFINE.finditer(f.text):
            start = f.text.index("{", m.end() - 2)
            end = match_close(code, start)
            nm = _NAME.search(f.text, start, end) if end else None
            if end and nm:
                t = Tool(
                    nm.group(1),
                    f,
                    line_of(f.text, nm.start()),
                    f.text[start:end],
                    start_line=line_of(f.text, start),
                    end_line=line_of(f.text, end),
                )
                span = _after_key(code, (start, end), "run|handler|execute")
                if span:
                    t.handlers.append((f, span[0], span[1]))
                tools.append(t)
    for f in live(files, (".py",)):
        for m in _PY_TOOL.finditer(f.text):
            block = re.search(r"\n(?=\S)", f.text[m.end() :])
            end = m.end() + (block.start() if block else len(f.text) - m.end())
            t = Tool(
                m.group(1),
                f,
                line_of(f.text, m.start(2) - 1),
                m.group(2),
                start_line=line_of(f.text, m.start()),
                end_line=line_of(f.text, end),
            )
            t.handlers.append((f, m.end(), end))
            tools.append(t)
    return tools


def _fn_index(files: list[SourceFile]) -> dict[str, list[tuple[SourceFile, int, int]]]:
    index: dict[str, list[tuple[SourceFile, int, int]]] = {}
    for f in live(files, UI):
        for n, a, b in function_bodies(f.text):
            index.setdefault(n, []).append((f, a, b))
    return index


def _function_span(index: dict, name: str) -> list[tuple[SourceFile, int, int]]:
    return index.get(name, []) + (index.get(_camel(name), []) if _camel(name) != name else [])


def _join_handlers(tools: list[Tool], files: list[SourceFile], index: dict) -> None:
    for t in tools:
        if t.handlers:
            continue
        for f in live(files, UI):
            m = re.search(rf"""case\s+['"]{re.escape(t.name)}['"]\s*:""", f.text)
            if not m:
                continue
            nxt = re.search(r"\n\s*(?:case\s+['\"]|default\s*:)", f.text[m.end() :])
            end = m.end() + (nxt.start() if nxt else min(1500, len(f.text) - m.end()))
            t.handlers.append((f, m.end(), end))
            for call in re.finditer(r"\b(\w+)\(", code_only(f.text)[m.end() : end]):
                t.handlers.extend(_function_span(index, call.group(1))[:1])
            break
        if not t.handlers:
            t.handlers.extend(_function_span(index, t.name)[:1])
        if not t.handlers:
            for f in live(files, (".py",)):
                dm = re.search(rf"^(?:async\s+)?def\s+{re.escape(t.name)}\(", f.text, re.M)
                if dm:
                    nxt = re.search(r"\n(?=\S)", f.text[dm.end() :])
                    t.handlers.append((f, dm.end(), dm.end() + (nxt.start() if nxt else 1500)))
                    break


def _map_tools(files: list[SourceFile], index: dict) -> list[Tool]:
    out = []
    for f in live(files, UI):
        code = code_only(f.text)
        for m in _HANDLER_MAP.finditer(f.text):
            start = m.end() - 1
            end = match_close(code, start)
            if not end:
                continue
            for e in re.finditer(r"['\"]?(\w+)['\"]?\s*:\s*(\w+)\s*[,}\n]", f.text[start:end]):
                spans = _function_span(index, e.group(2))
                if spans:
                    t = Tool(e.group(1), f, line_of(f.text, start + e.start()))
                    t.start_line = t.end_line = t.line
                    t.handlers.extend(spans[:1])
                    out.append(t)
    return out


_MEMO: dict = {"key": None, "tools": []}


def tools_in(files: list[SourceFile]) -> list[Tool]:
    key = (tuple(f.path for f in files), sum(len(f.text) for f in files))
    if _MEMO["key"] == key:
        return _MEMO["tools"]
    index = _fn_index(files)
    defs = _definitions(files)
    _join_handlers(defs, files, index)
    known = {t.name for t in defs}
    tools = defs + [t for t in _map_tools(files, index) if t.name not in known]
    _MEMO.update(key=key, tools=tools)
    return tools


def _gated(tool: Tool, files: list[SourceFile]) -> bool:
    if GATE_RAW.search(tool.raw):
        return True
    if GATE_LOCAL.search(tool.code + code_only(tool.schema)):
        return True
    return any(GATE_GLOBAL.search(code_only(f.text)) for f in live(files, SRC))


_NUM_PARAM = re.compile(
    r"(\w+)\s*:\s*\{\s*type\s*:\s*['\"](?:number|integer)['\"]([^}]*)\}|(\w+)\s*:\s*z\.(?:coerce\.)?number\(\)([^,\n}]*)"
)


def _unbounded(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for t in tools_in(files):
        if not t.schema or not CHANGE_TOOL.search(t.name):
            continue
        for m in _NUM_PARAM.finditer(t.schema):
            param = m.group(1) or m.group(3)
            spec = m.group(2) if m.group(1) else m.group(4)
            if re.search(r"maximum|enum|\.max\(|\.lte?\(|\.lt\(", spec or ""):
                continue
            code = t.code
            bound = re.search(
                rf"\b{param}\b\s*(?:>=?|<=?)\s*\w|(?:>=?|<=?)\s*{param}\b|Math\.(?:min|max)\([^)]*\b{param}\b|\bclamp\(",
                code,
            )
            if bound or not t.handlers:
                continue
            ln = line_of(t.file.text, t.file.text.index(t.schema) + m.start())
            fnd = rule.finding(
                t.file,
                t.start_line or ln,
                t.file.lines[ln - 1],
                end_line=t.end_line or None,
            )
            if MONEY_TOOL.search(t.name):
                fnd.severity = "high"
            else:
                fnd.severity = "medium"
                fnd.label = "check"
            yield fnd


unbounded = custom_rule(
    "tool-number-unbounded",
    "ai_tool_unbounded",
    "high",
    "rewrite",
    "The AI can call an action with any amount, and no code stops a huge number.",
    "Add a schema maximum and a check against the real limit inside the tool. Do not trust the model.",
    _unbounded,
    UI + (".py",),
)


def _no_approval(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for t in tools_in(files):
        if not ACTION_TOOL.search(t.name) or not t.handlers:
            continue
        if _gated(t, files):
            continue
        yield rule.finding(
            t.file,
            t.start_line or t.line,
            t.file.lines[t.line - 1],
            end_line=t.end_line or None,
        )


no_approval = custom_rule(
    "tool-action-no-approval",
    "ai_no_human_review",
    "high",
    "rewrite",
    "The AI can send, refund, or change things without approval from a person.",
    "Queue this action for human approval. Use a pending state or a tool approval option before it runs.",
    _no_approval,
    UI + (".py",),
)

_LIMIT = re.compile(
    r"\b(?:never|do not|don't|must not|must never|not allowed to|only if|at most|no more than|up to|maximum(?: of)?"
    r"|limit of|always (?:ask|confirm)|before (?:you )?\w+|over \$?\d+|(?:human|manager) approval|approval from"
    r"|requires? (?:human|manager|approval))\b",
    re.I,
)
_APPROVALISH = re.compile(r"confirm|approv|always ask|before (?:you )?\w+", re.I)
_PROMPT_PREFIX = re.compile(
    r"(?:(?:system|prompt|instruction)\w*\s*(?::[^=\n]+)?[=:]\s*(?:\([^)]*\)\s*(?::\s*\w+\s*)?=>\s*)?"
    r"|role\s*:\s*['\"]system['\"]\s*,\s*content\s*:\s*)$",
    re.I,
)
_LONG_STRING = re.compile(r"`(?:\\.|[^`\\])*`|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'")


def _tokens(name: str) -> list[str]:
    parts = re.split(r"[_\W]+|(?<=[a-z])(?=[A-Z])", name)
    return [p.lower() for p in parts if len(p) >= 4 and p.lower() not in GENERIC]


def _prompt_only(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    tools = [t for t in tools_in(files) if t.handlers]
    if not tools:
        return
    for f in live(files, UI):
        emitted = 0
        for lit in _LONG_STRING.finditer(f.text):
            body = lit.group(0)
            if len(body) < 80 or not _PROMPT_PREFIX.search(
                f.text[max(0, lit.start() - 90) : lit.start()]
            ):
                continue
            for sm in re.finditer(r"[^\n.!?]+[.!?]?", body):
                sentence = sm.group(0)
                if not _LIMIT.search(sentence):
                    continue
                low = sentence.lower()
                nums = re.findall(r"\d+(?:\.\d+)?", sentence)
                for t in tools:
                    if not any(re.search(rf"\b{tok}", low) for tok in _tokens(t.name)):
                        continue
                    scope = t.raw + t.schema
                    if nums:
                        missing = [n for n in nums if not re.search(rf"\b{re.escape(n)}\b", scope)]
                        if not missing:
                            continue
                    elif not _APPROVALISH.search(sentence) or _gated(t, files):
                        continue
                    ln = line_of(
                        f.text, lit.start() + sm.start() + len(sentence) - len(sentence.lstrip())
                    )
                    rel_f, rel_a, _ = t.handlers[0]
                    rel_line = line_of(rel_f.text, rel_a)
                    rel_end = line_of(rel_f.text, t.handlers[0][2])
                    yield rule.finding(
                        f,
                        ln,
                        sentence.strip(),
                        related_file=rel_f.path,
                        related_line=rel_line,
                        related_snippet=rel_f.lines[rel_line - 1],
                        related_end_line=rel_end,
                    )
                    emitted += 1
                    break
                if emitted >= 8:
                    break


prompt_only = custom_rule(
    "prompt-limit-not-in-code",
    "ai_prompt_only_rule",
    "high",
    "rewrite",
    "The rule is only a sentence that asks the AI to behave. No code enforces it.",
    "Enforce the limit in the tool code or the database. Prompts are not a security boundary.",
    _prompt_only,
    UI,
)


def _canned(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    real = re.compile(
        r"\bawait\b|\bfetch\(|\bdb\.|prisma|supabase|\.query\(|\.select\(|\.find\w*\(|axios|readFile|\.from\(|\.execute\("
    )
    literal = re.compile(
        r"\breturn\b[^;]{0,200}?\b(?!ok|success|found|error|message|note|hint|results|matches)\w+\s*:\s*(?:'[^']*'|\"[^\"]*\"|\d+)"
    )
    for t in tools_in(files):
        if not t.handlers:
            continue
        code = t.code
        m = literal.search(code)
        if real.search(code) or not m:
            continue
        f, a, b = t.handlers[0]
        pos = code_only(f.text).find(m.group(0), a)
        ln = line_of(f.text, pos if pos != -1 else a)
        yield rule.finding(
            f, line_of(f.text, a), f.lines[ln - 1], end_line=max(line_of(f.text, b), ln)
        )


canned = custom_rule(
    "tool-returns-canned",
    "ai_fake_tool",
    "medium",
    "throwaway",
    "The AI tool gives back made-up data, so the AI answers from fiction.",
    "Replace the literal return value with a real lookup against your data source.",
    _canned,
    UI + (".py",),
)

_BROWSER_FLAG = re.compile(
    r"dangerouslyAllowBrowser\s*:\s*true|anthropic-dangerous-direct-browser-access"
)
_CLIENT_NEW = re.compile(r"new\s+(?:OpenAI|Anthropic|GoogleGenerativeAI|Groq|Mistral|Cohere)\(")
_PROVIDER_FETCH = re.compile(
    r"fetch\(\s*['\"`]https://(?:api\.openai\.com|api\.anthropic\.com|api\.groq\.com|api\.mistral\.ai"
    r"|openrouter\.ai/api|generativelanguage\.googleapis\.com)"
)


def _browser_sdk(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, UI):
        client = is_client(f)
        for rx in (_BROWSER_FLAG, _CLIENT_NEW, _PROVIDER_FETCH):
            if rx is not _BROWSER_FLAG and not client:
                continue
            for m in rx.finditer(f.text):
                ln = line_of(f.text, m.start())
                if f.lines[ln - 1].strip().startswith("//"):
                    continue
                yield rule.finding(f, ln, f.lines[ln - 1])


browser_sdk = custom_rule(
    "ai-browser-sdk",
    "ai_browser_call",
    "high",
    "rewrite",
    "The page calls the AI company directly. Every visitor can copy the key and spend your money.",
    "Call the provider from a server route and keep the key there. Add auth and rate limits.",
    _browser_sdk,
    UI,
)


def _key_env(f: SourceFile, m: re.Match, t: str) -> dict | None:
    name = m.group(0)
    if re.search(r"(?:URL|ENDPOINT|MODEL|BASE|PROXY)$", name, re.I):
        return None
    return {"snippet": name}


key_in_client_env = line_rule(
    "ai-key-in-client-env",
    "ai_browser_call",
    "high",
    "rewrite",
    "The AI provider key sits in a setting that the build copies into the page.",
    "Remove the public prefix and read the key only in server code. Rotate the key.",
    pattern=re.compile(
        rf"\b(?:VITE_|NEXT_PUBLIC_|REACT_APP_|EXPO_PUBLIC_)\w*(?:{PROVIDERS})\w*", re.I
    ),
    suffixes=SRC + ENVFILE,
    refine=_key_env,
    skip_scripts=False,
)

_LLM_CALL = re.compile(
    r"\b(?:chat\.completions\.create|chat\.completions\.parse|responses\.create|generateText|streamText"
    r"|generateObject|streamObject|ChatOpenAI|ChatAnthropic|generateContent|messages\.create)\b"
)
_EVAL_PATH = re.compile(
    r"(^|/)(evals?|evaluations?)(/|\.)|promptfoo|\.eval\.(ts|js|py)$|test_.*prompt|prompt.*\.test\.|golden"
    r"|datasets?/.*\.jsonl"
)
_EVAL_DEP = re.compile(r"promptfoo|deepeval|ragas|braintrust|langsmith|openai-evals|inspect-ai")


def _no_eval(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    if any(_EVAL_PATH.search(f.path.lower()) for f in files):
        return
    if any(
        f.path.endswith(("package.json", "requirements.txt")) and _EVAL_DEP.search(f.text)
        for f in files
    ):
        return
    for f in live(files, SRC):
        m = _LLM_CALL.search(code_only(f.text))
        if m:
            ln = line_of(f.text, m.start())
            yield rule.finding(f, ln, f.lines[ln - 1])
            return


no_eval = custom_rule(
    "ai-no-eval-files",
    "ai_no_tests",
    "medium",
    "check",
    "Nobody tests the AI's answers, so a prompt change can break the product without notice.",
    "Add a small eval set of real questions with expected answers, and run it on each prompt change.",
    _no_eval,
    SRC,
)

_NO_MAX = re.compile(
    r"\b(?:chat\.completions\.create|chat\.completions\.parse|responses\.create|generateText|streamText"
    r"|generateObject|streamObject)\s*\("
)
_MAX_WORDS = re.compile(
    r"max_tokens|max_completion_tokens|max_output_tokens|maxOutputTokens|maxTokens"
)


def _cost(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, UI):
        code = code_only(f.text)
        for m in _NO_MAX.finditer(code):
            end = match_close(code, m.end() - 1)
            args = code[m.end() - 1 : end] if end else ""
            if "{" not in args or _MAX_WORDS.search(args):
                continue
            ln = line_of(f.text, m.start())
            fnd = rule.finding(f, ln, f.lines[ln - 1])
            if not is_client(f):
                fnd.label = "check"
            yield fnd
        if is_client(f):
            for m in re.finditer(
                r"""\bmodel\s*[:=]\s*['"](?:gpt-|claude-|gemini-|o1|o3)[\w.\-]*['"]""", f.text
            ):
                ln = line_of(f.text, m.start())
                fnd = rule.finding(
                    f,
                    ln,
                    f.lines[ln - 1],
                    pm_text="The page chooses which paid AI model runs.",
                    engineer_text="Pick the model on the server so visitors cannot switch to a costly one.",
                )
                fnd.severity = "low"
                yield fnd


cost_controls = custom_rule(
    "ai-cost-controls",
    "ai_no_cost_limit",
    "medium",
    "rewrite",
    "Nothing caps how much the AI writes, so one request can cost far more than expected.",
    "Set max_tokens or maxOutputTokens on every model call. Add a per-user quota.",
    _cost,
    UI,
)

RULES: list[Rule] = [
    browser_sdk,
    key_in_client_env,
    unbounded,
    no_approval,
    prompt_only,
    canned,
    no_eval,
    cost_controls,
]
