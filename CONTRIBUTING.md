# Contributing

## Set up

```bash
uv venv && uv pip install -e ".[dev]"
```

## Check your change

Run these commands before you open a pull request.

```bash
make lint
make test
```

## Rules

- Run `make bundle` after any change in `src/`. A test fails if the bundled copy is stale.
- Write tests against real code from public prototype repos. Do not write made-up fixtures.
- Never edit a hand label in `tests/corpus/labels/` to make a test pass.
- Every finding must name a file and a line from the scanned repo.
- Write prose in short sentences. Use the active voice.

## Commits

- Write one plain sentence as the subject.
- Give the cause, the fix, and the proof in the body.
