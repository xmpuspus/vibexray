.PHONY: install lint fmt test e2e browser corpus bundle check demo gif clean

PY ?= uv run

install:
	uv venv
	uv pip install -e ".[dev]"
	$(PY) playwright install chromium

lint:
	$(PY) ruff check .
	$(PY) ruff format --check .

fmt:
	$(PY) ruff check --fix .
	$(PY) ruff format .

test:
	$(PY) pytest -q -m "not corpus and not browser"

corpus:
	$(PY) python scripts/fetch_corpus.py

e2e:
	$(PY) pytest -q -m "corpus or browser"

bundle:
	$(PY) python scripts/bundle_skill.py

check: lint test e2e
	claude plugin validate .

demo:
	vhs docs/demo.tape

gif: demo
	$(PY) python scripts/record_report.py

clean:
	rm -rf dist build .pytest_cache .ruff_cache vibexray-report tmp
