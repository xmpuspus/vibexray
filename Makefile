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

# Real recordings only. See the header of docs/hero.tape before you record.
demo:
	scripts/bootstrap-demo.sh
	vhs docs/hero.tape
	$(PY) python scripts/video_to_gif.py tmp/hero/hero.mp4 docs/hero.gif --trim-tail --seconds 35 --hold 10 --width 1100

# The report GIF uses a fresh scan plus the review.json that the hero session wrote.
gif:
	$(PY) vibexray scan /tmp/vibexray-demo/support-bot --out tmp/hero/report
	$(PY) vibexray review tmp/hero/report --input /tmp/vibexray-demo/support-bot/vibexray-report/review.json
	$(PY) python scripts/record_report.py tmp/hero/report/report.html docs/report.gif

clean:
	rm -rf dist build .pytest_cache .ruff_cache vibexray-report tmp
