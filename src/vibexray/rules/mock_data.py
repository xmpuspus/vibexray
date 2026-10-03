"""Sample data shown as real."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable

from vibexray.model import Finding
from vibexray.rules.base import Rule
from vibexray.rules.util import (
    PY,
    SRC,
    UI,
    code_only,
    custom_rule,
    is_script_or_seed,
    line_of,
    line_rule,
    live,
    match_close,
)
from vibexray.walker import SourceFile

MOCK_NAME = r"(?:mock|sample|dummy|fake|demo|seed|placeholder)\w*"
_MOCK_ARRAY = re.compile(rf"(?:const|let|var)\s+{MOCK_NAME}\s*(?::[^=\n]+)?=\s*\[\s*\{{", re.I)
_MOCK_ARRAY_PY = re.compile(r"^(MOCK|SAMPLE|DUMMY|FAKE)_\w+\s*=\s*[\[{]", re.M)


def _mock_array_check(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, SRC):
        if is_script_or_seed(f.path):
            continue
        rx = _MOCK_ARRAY_PY if f.suffix == ".py" else _MOCK_ARRAY
        for m in rx.finditer(f.text):
            ln = line_of(f.text, m.start())
            yield rule.finding(f, ln, f.lines[ln - 1])


mock_array = custom_rule(
    "mock-array-literal",
    "mock_data",
    "high",
    "throwaway",
    "A list on screen was typed into the code. No database supplies it.",
    "Replace the hardcoded array with a query or API call, then delete the sample list.",
    _mock_array_check,
)

_RECORD_ARRAY = re.compile(r"\b(?:const|let)\s+(\w+)\s*(?::[^=\n]+)?=\s*\[\s*\{")
_SAFE_LIST = re.compile(
    r"link|nav|menu|tab|option|column|route|icon|faq|breadcrumb|step|plan|tier|social", re.I
)
_BIZ_KEYS = re.compile(r"\b(email|customer|order|status|amount|invoice|balance)\b")
_NO_FETCH = re.compile(r"\bfetch\(|axios|useQuery|supabase|\bawait\b|useSWR|trpc")


def _inline_records(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, (".tsx", ".jsx", ".vue", ".svelte")):
        if _NO_FETCH.search(f.text) or is_script_or_seed(f.path):
            continue
        code = code_only(f.text)
        for m in _RECORD_ARRAY.finditer(code):
            name = m.group(1)
            if _SAFE_LIST.search(name) or not re.search(rf"\b{name}\.map\(", code):
                continue
            end = match_close(code, code.index("[", m.start()))
            if end is None:
                continue
            body = f.text[m.start() : end]
            if len(re.findall(r"\{\s*(?:id|name|title|label)\s*:", body)) < 3:
                continue
            ln = line_of(f.text, m.start())
            hit = rule.finding(f, ln, f.lines[ln - 1])
            if _BIZ_KEYS.search(body):
                hit.severity = "high"
            yield hit


inline_records = custom_rule(
    "inline-record-array",
    "mock_data",
    "medium",
    "throwaway",
    "A screen shows a list of records that the code never fetches.",
    "Check whether this list is real content. If it is business data, load it from the database.",
    _inline_records,
    (".tsx", ".jsx", ".vue", ".svelte"),
)

_FAKE_LIB = r"@faker-js/faker|faker|chance|casual|json-server|miragejs|@mswjs/data|msw"
_LIB_IMPORT = re.compile(rf"""(?:from\s+|require\()['"](?:{_FAKE_LIB})['"]""")
_LIB_IMPORT_PY = re.compile(r"^\s*(?:from faker import|import factory\b)", re.M)


def _mock_lib(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    for f in live(files, SRC + (".json",)):
        if f.suffix == ".json":
            if not f.path.endswith("package.json"):
                continue
            try:
                deps = json.loads(f.text).get("dependencies") or {}
            except ValueError:
                continue
            for name in deps:
                if re.fullmatch(_FAKE_LIB, name) and name != "msw":
                    ln = next((i for i, x in enumerate(f.lines, 1) if f'"{name}"' in x), 1)
                    yield rule.finding(f, ln, f.lines[ln - 1])
            continue
        rx = _LIB_IMPORT_PY if f.suffix == ".py" else _LIB_IMPORT
        for m in rx.finditer(f.text):
            ln = line_of(f.text, m.start())
            yield rule.finding(f, ln, f.lines[ln - 1])


mock_lib = custom_rule(
    "mock-library-import",
    "mock_data",
    "medium",
    "throwaway",
    "The app imports a tool that makes fake data.",
    "Remove the fake-data package from app code and load real records instead.",
    _mock_lib,
    SRC + (".json",),
)

_MOCK_SPEC = re.compile(
    r"(^|/)([\w-]*[-_.])?(mocks?|dummy|fakes?|stubs?|fixtures?|seed[-_]?data|sample[-_]?data|demo[-_]?data)"
    r"([-_.][\w-]*)?$",
    re.I,
)
_IMPORT_SPEC = re.compile(r"""(?:from\s+|import\(\s*|require\(\s*)['"]([^'"]+)['"]""")


def _stem(path: str) -> str:
    return re.sub(r"\.\w+$", "", path)


def _mock_path(rule: Rule, files: list[SourceFile]) -> Iterable[Finding]:
    mocks = [f for f in files if _MOCK_SPEC.search(_stem(f.path)) and f.suffix in SRC + (".json",)]
    if not mocks:
        return
    for f in live(files, SRC):
        if is_script_or_seed(f.path):
            continue
        for m in _IMPORT_SPEC.finditer(f.text):
            spec = m.group(1)
            tail = re.sub(r"^(@/|~/|\.{1,2}/)+", "", _stem(spec))
            if not _MOCK_SPEC.search(tail):
                continue
            for mock in mocks:
                if _stem(mock.path).endswith(tail) and mock.path != f.path:
                    ln = line_of(f.text, m.start())
                    yield rule.finding(
                        f, ln, f.lines[ln - 1], related_file=mock.path, related_line=1
                    )
                    break


mock_path = custom_rule(
    "mock-path-segment",
    "mock_data",
    "medium",
    "check",
    "Real code loads a file that holds fake data.",
    "Check what this import feeds. Swap the mock module for a real data source before launch.",
    _mock_path,
    SRC,
)

json_db = line_rule(
    "json-file-as-database",
    "mock_data",
    "high",
    "rewrite",
    "The app reads its data from a file in the code. Nothing a user does can save there.",
    "Move this data to a database. Static JSON in the repo cannot take user writes.",
    pattern=re.compile(
        r"""import\s+\w+\s+from\s+['"][^'"]*\b(?:data|db|mock|mocks|fixtures?)\b[^'"]*\.json['"]"""
        r"""|fetch\(['"]/?(?:data|api)/[\w-]+\.json['"]"""
        r"""|fs\.(?:writeFileSync|writeFile)\([^)\n]*\.json"""
    ),
    suffixes=UI + PY,
    refine=lambda f, m, t: (
        None if re.search(r"locales?|i18n|messages|tsconfig|package\.json", t) else {}
    ),
)

lorem = line_rule(
    "lorem-ipsum",
    "mock_data",
    "low",
    "throwaway",
    "Filler text still shows on a screen.",
    "Replace the filler text with real copy.",
    pattern=re.compile(
        r"lorem ipsum|dolor sit amet|consectetur adipiscing|Your (?:text|content|description) here",
        re.I,
    ),
    suffixes=UI + (".html",),
    per_file=2,
)

_PH_ID = re.compile(
    r"\b(?:john|jane)[ ._-]?doe\b|@example\.(?:com|org|net)|test@test\.com|foo@bar\.com"
    r"|user@domain\.com|\b555-?01\d\d\b|\b123 Main St\b",
    re.I,
)

placeholder_identity = line_rule(
    "placeholder-identity",
    "mock_data",
    "medium",
    "throwaway",
    "Test people, emails, or phone numbers sit in real code.",
    "Remove stock names and example.com addresses from live code paths. Read real records instead.",
    pattern=_PH_ID,
    suffixes=SRC + (".sql",),
    refine=lambda f, m, t: None if re.search(r"placeholder\s*[=:]|mailto:", t) else {},
    per_file=3,
)

_MEDIA = re.compile(
    r"https?://(?:via\.placeholder\.com|placehold\.co|placekitten\.com|picsum\.photos|dummyimage\.com"
    r"|source\.unsplash\.com|images\.unsplash\.com)"
)

placeholder_media = line_rule(
    "placeholder-media",
    "mock_data",
    "medium",
    "throwaway",
    "Pictures come from a stand-in image service.",
    "Host the real images yourself. A stock photo host is fine only if the choice is deliberate.",
    pattern=_MEDIA,
    suffixes=SRC + (".sql", ".html"),
    refine=lambda f, m, t: {"severity": "low"} if "unsplash" in m.group(0) else {},
    per_file=2,
)

RULES: list[Rule] = [
    mock_array,
    inline_records,
    mock_lib,
    mock_path,
    json_db,
    lorem,
    placeholder_identity,
    placeholder_media,
]
