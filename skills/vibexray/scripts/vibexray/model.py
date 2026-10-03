"""Shared data model. Every stage of a scan reads and writes these types."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

# category -> (short name a PM reads, group)
CATEGORIES: dict[str, tuple[str, str]] = {
    "mock_data": ("Sample data shown as real", "fake"),
    "fake_action": ("Button or message that does nothing real", "fake"),
    "hardcoded_config": ("Hardcoded value", "fake"),
    "ai_fake_tool": ("AI tool that returns sample data", "fake"),
    "auth_gap": ("Page or action with no login check", "security"),
    "database_rules": ("Database open to anyone", "security"),
    "secret_exposure": ("Secret key anyone can read", "security"),
    "security_other": ("Other security risk", "security"),
    "ai_browser_call": ("AI called straight from the browser", "ai"),
    "ai_tool_unbounded": ("AI tool with no limit in code", "ai"),
    "ai_prompt_only_rule": ("Rule that lives only in the AI prompt", "ai"),
    "ai_no_human_review": ("AI acts with no human check", "ai"),
}

GROUPS: dict[str, str] = {
    "fake": "What is fake",
    "security": "What can break: security",
    "ai": "What can break: the AI",
}

SEVERITIES = ("high", "medium", "low")

# keep: fine to build on. rewrite: the idea is real, the build is not.
# throwaway: demo only. check: a person must look.
LABELS = ("keep", "rewrite", "throwaway", "check")

APP_RUN_STATES = ("ran", "could_not_boot", "not_attempted")


@dataclass
class Finding:
    rule_id: str
    category: str
    severity: str
    file: str
    line: int
    snippet: str
    pm_text: str
    engineer_text: str
    label: str
    end_line: int | None = None
    related_file: str | None = None
    related_line: int | None = None
    related_snippet: str | None = None

    @property
    def group(self) -> str:
        return CATEGORIES[self.category][1]


@dataclass
class Page:
    path: str
    title: str = ""
    screenshot: str | None = None
    buttons: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    console_errors: list[str] = field(default_factory=list)
    status: int | None = None


@dataclass
class AppRun:
    state: str = "not_attempted"
    reason: str = ""
    url: str | None = None
    command: str | None = None
    missing_env: list[str] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)


@dataclass
class Prompt:
    when: str
    text: str


@dataclass
class History:
    source: str = "none"
    sessions: int = 0
    prompts: list[Prompt] = field(default_factory=list)
    note: str = ""


@dataclass
class Question:
    text: str
    why: str
    source: str
    file: str | None = None
    line: int | None = None


@dataclass
class Part:
    """One file of the prototype, with the label the engineer acts on."""

    file: str
    label: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    version: str
    target: str
    app_name: str
    generated_at: str
    files_scanned: int
    stack: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    parts: list[Part] = field(default_factory=list)
    app_run: AppRun = field(default_factory=AppRun)
    history: History = field(default_factory=History)
    questions: list[Question] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        out = dict.fromkeys(GROUPS, 0)
        for f in self.findings:
            out[f.group] += 1
        return out

    def label_counts(self) -> dict[str, int]:
        out = dict.fromkeys(LABELS, 0)
        for p in self.parts:
            out[p.label] += 1
        return out

    def to_dict(self) -> dict:
        data = asdict(self)
        data["counts"] = self.counts()
        data["label_counts"] = self.label_counts()
        return data
