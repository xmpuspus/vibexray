# vibexray repository guide

## Scope

vibexray reads an AI-built prototype and writes a handoff. The PM reads `report.html`. The engineer and the coding agent read `handoff.md`. Tools read `vibexray.json`.

## Layout

- `src/vibexray/` holds the package. `cli.py` runs the stages in order.
- `src/vibexray/rules/` holds the detection rules. Each rule returns findings with a file and a line.
- `src/vibexray/report/` makes the HTML report, the markdown handoff, and the JSON output.
- `skills/vibexray/` holds the Agent Skill for Claude Code and Codex.
- `tests/` holds unit tests, CLI tests, corpus tests, and browser tests.
- `tests/corpus/` holds the pinned list of real prototype repos and their hand labels.
- `scripts/` holds the corpus fetch, skill bundle, and demo recording scripts.
- `docs/` holds the GIFs, the logo, and their recipes.

## Setup

```bash
uv venv && uv pip install -e ".[dev]"
uv run playwright install chromium
make corpus
```

## Checks

```bash
make lint
make test
make e2e
```

## Contracts

- Every finding names a file and a line from the scanned repo. A rule never guesses.
- Tests use real code from public prototype repos. Never write mock or made-up fixtures.
- The hand labels in `tests/corpus/labels/` are the answer key. Never edit a label to make a test pass.
- The scan runs no third-party code unless the user asks for an app run. An app run installs with `--ignore-scripts` and a clean environment.
- The report never shows a secret value. `rules/base.py` hides key-shaped strings.
- Every report section shows explicit text when it has no data. A blank panel is a bug.
- The skill folder carries a copy of the package. Run `make bundle` after any change in `src/`. A test fails if the copy is stale.
