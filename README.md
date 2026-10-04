<p align="center"><img src="https://raw.githubusercontent.com/xmpuspus/vibexray/main/docs/media/logo.svg" alt="vibexray logo: a page under a green scan line, with one line marked in coral" width="96"></p>

<h1 align="center">vibexray</h1>
<p align="center"><strong>See what is real and what is fake in an AI-built prototype, before the engineer builds it.</strong></p>
<p align="center">
A skill for Claude Code and Codex. It reads the prototype and starts it.
It writes a report for the PM and a handoff for the engineer.
Every finding points to a file and a line.
</p>

<p align="center">
  <a href="https://github.com/xmpuspus/vibexray/actions/workflows/ci.yml"><img src="https://github.com/xmpuspus/vibexray/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue" alt="Python 3.11 to 3.13">
  <img src="https://img.shields.io/badge/runs%20in-Claude%20Code%20%7C%20Codex-6b4fbb" alt="Runs in Claude Code and Codex">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License MIT"></a>
</p>

<p align="center"><img src="https://raw.githubusercontent.com/xmpuspus/vibexray/main/docs/media/hero.gif" alt="Claude Code runs /vibexray on a support bot and lists its fake parts and risks." width="900"></p>

```bash
claude plugin marketplace add xmpuspus/vibexray
claude plugin install vibexray@vibexray
```

Then open your prototype folder in Claude Code and type `/vibexray`. That is the whole loop.

<p align="center">
<a href="#install">Install</a> &middot;
<a href="#features">Features</a> &middot;
<a href="#how-a-scan-works">How a scan works</a> &middot;
<a href="#on-19-unseen-prototypes-vibexray-finds-about-half-of-the-labeled-problems-and-3-in-4-findings-match-a-label">Results</a> &middot;
<a href="#compared-with-other-tools">Compared</a> &middot;
<a href="#fix-common-problems">Fix problems</a> &middot;
<a href="CHANGELOG.md">Changelog</a>
</p>

> **Note:** vibexray finds part of what a careful engineer finds, not all of it. The [measured results](#on-19-unseen-prototypes-vibexray-finds-about-half-of-the-labeled-problems-and-3-in-4-findings-match-a-label) say how much. Use the report to start the handoff, not to skip the engineer's review.

## I built this to help product managers help me build their dreams

I am an engineer. I do my best work when the product manager is at the top of their game.

Product managers now build working prototypes with Claude Code and Codex. The prototype looks done. Some parts are real. Some parts show sample data or fake a button. Some parts let any user read any other user's data. The PM cannot tell which is which, and the first engineering meeting turns into a list of surprises.

vibexray tells the PM which is which before the handoff. The PM answers a few decisions, then sends the engineer a handoff that names every file and line.

## Why vibexray

- **A real-versus-fake ledger.** Each part of the app gets one label: keep, rewrite, throw away, or check.
- **Every finding has a receipt.** It names a file and a line. The line check drops any quote that is not there.
- **It starts the app.** It runs the prototype in a temporary copy and saves screenshots of up to 8 pages.
- **It reads the build chat.** A rule that the PM typed, but the code lacks, becomes a question.
- **Decisions in plain words.** Up to 10 questions for the PM, such as "Who may open /api/orders/[id]?"
- **Two readers, two files.** The PM reads `report.html`. The engineer and their coding agent read `handoff.md`.
- **It runs where the PM works.** One skill for Claude Code and Codex. The scan itself needs only Python.

[Compared with other tools](#compared-with-other-tools) shows how the closest tools differ.

## The PM gets one page that answers four questions

<p align="center"><img src="https://raw.githubusercontent.com/xmpuspus/vibexray/main/docs/media/report.gif" alt="A walk through report.html: the headline, the PM's decisions, the real and fake parts, the risks, and app screenshots." width="900"></p>

The scan writes three files to `vibexray-report/`:

| File | Reader | What it holds |
|---|---|---|
| `report.html` | The PM | What is fake, what can break, what the app does, and the decisions the PM must make |
| `handoff.md` | The engineer and their coding agent | Every finding with its file, line, code, and fix |
| `vibexray.json` | Tools | All findings, parts, questions, and build-chat prompts |

The report answers these questions:

1. **What is fake?** Sample data shown as real, buttons that do nothing, and fixed values that belong in settings.
2. **What can break?** Pages with no login check, open database rules, keys in browser code, and AI risks.
3. **What does the app do?** vibexray starts the app in a copy, visits up to 8 pages, and saves screenshots.
4. **What must the PM decide?** Up to 10 plain questions, such as "Who may open /api/orders/[id]?"

Each file of the prototype gets one label:

- **Keep**: real code. The engineer can build on it.
- **Rewrite**: the idea is real, but the code is not ready.
- **Throw away**: demo only. Remove it before launch.
- **Check**: vibexray is not sure. A person looks at it.

## Features

Every GIF below is a real recording of one report. vibexray made the report from a public support-bot prototype.

### See the decisions that the PM must make

The report opens with the questions that block the engineer, the most important first. Each question names the file and line that raised it.

<p align="center"><img src="https://raw.githubusercontent.com/xmpuspus/vibexray/main/docs/media/decisions.gif" alt="The decisions section of a report lists five numbered questions for the PM, each with its source file and line." width="900"></p>

### See which parts to keep, rewrite, or throw away

A bar shows the share of each label. Each part lists the finding that decided its label.

<p align="center"><img src="https://raw.githubusercontent.com/xmpuspus/vibexray/main/docs/media/parts.gif" alt="The parts section shows a bar of keep, rewrite, throw away, and check, then the files under each label." width="900"></p>

### See what is fake

Each card names one fake place, what the PM sees, and what the engineer must change. Open a card to see the code.

<p align="center"><img src="https://raw.githubusercontent.com/xmpuspus/vibexray/main/docs/media/fake.gif" alt="The fake section shows cards for a keyword bot that poses as an AI and for invented store policies." width="900"></p>

### See what can break

Risks sort by priority. A high risk, such as an order page that any visitor can open, comes first.

<p align="center"><img src="https://raw.githubusercontent.com/xmpuspus/vibexray/main/docs/media/risks.gif" alt="The risks section lists high risks first, such as ticket and order pages with no login check." width="900"></p>

### See what the app does

vibexray starts the app in a temporary copy and opens each page. The report shows each screenshot with its buttons, inputs, and browser errors.

<p align="center"><img src="https://raw.githubusercontent.com/xmpuspus/vibexray/main/docs/media/app.gif" alt="The app section shows screenshots of seven pages, each with its buttons, inputs, and browser errors." width="900"></p>

## Install

### Claude Code

```bash
claude plugin marketplace add xmpuspus/vibexray
claude plugin install vibexray@vibexray
```

Inside Claude Code, the same two steps are `/plugin marketplace add xmpuspus/vibexray` and `/plugin install vibexray@vibexray`. Then type `/vibexray` in your prototype folder, or ask "is this ready for engineering?"

### Codex

```bash
codex plugin marketplace add xmpuspus/vibexray
codex plugin add vibexray@vibexray
```

Then ask Codex to "x-ray this prototype". The Codex sandbox blocks local servers by default, so the report says that the app did not start. The code review still runs.

### Let vibexray start the app

The scan needs only Python 3.11 or newer. To start the app and take screenshots, vibexray also needs Node and Playwright:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

Without Playwright, the report says how to add it, and every other section still fills in.

### The command line, with no AI host

```bash
pipx install vibexray
vibexray scan ./my-prototype --open
```

The command line runs the pattern rules, the app run, and the build-chat reader. It does not run the AI review, so it finds fewer problems than the skill.

<p align="center"><img src="https://raw.githubusercontent.com/xmpuspus/vibexray/main/docs/media/cli.gif" alt="A terminal runs vibexray scan on the support-bot prototype, prints the summary, then lists the first ten pattern rules." width="900"></p>

## How a scan works

1. **Pattern rules.** 72 rules look for known shapes, such as a mock data import. Run `vibexray rules` to list them.
2. **App run.** vibexray copies the prototype to a temporary folder, without your `.env` files. It reuses your installed packages through a copy-on-write clone, or installs them with `--ignore-scripts`. It starts the app, visits its pages, and stops every process it started.
3. **Build chat.** vibexray reads the Claude Code and Codex chats for this folder on this computer. It keeps only the prompts you typed. If you said "refunds over 100 dollars need a manager's approval" and the code has no such check, the report asks about it.
4. **AI review.** The host agent, Claude Code or Codex, reads the code with a fixed checklist and writes `review.json`. Each finding must quote the exact code on the cited line.
5. **Line check.** `vibexray review` opens each cited file and line. It keeps a finding only if the quote is on that line. It drops the others, so an invented finding never reaches the report.

## On 19 unseen prototypes, vibexray finds about half of the labeled problems, and 3 in 4 findings match a label

The test set holds 19 public prototypes built with Claude Code or Codex. Nobody ran vibexray on them before the test. Two independent reviewers labeled the problems by file and line, with no access to vibexray. The test ran once, at commit `587a03a`.

| Host | Labeled problems found (recall) | Findings that match a label (precision) | F1 |
|---|---|---|---|
| Claude Code | 53% | 75% | 0.62 |
| Codex | 48% | 76% | 0.59 |
| Pattern rules only | 5% | 37% | 0.10 |

- Each AI number pools 3 runs of each repo. All 114 sessions wrote a review.
- The line check dropped 0 of 3,286 AI findings. Each one cited a real file, line, and quote.
- The two reviewers agree with each other at F1 0.82 to 0.84 on these repos. That is the practical top score of this test.
- The labels miss some real problems, so the precision column is a floor.
- The Codex runs loaded the maintainer's own `AGENTS.md`. The Codex sandbox blocked the app run, so Codex read the code only.
- [docs/results/sealed-1/](docs/results/sealed-1/) holds the full summaries. [docs/benchmark.md](docs/benchmark.md) defines the metric.

[tests/corpus/README.md](tests/corpus/README.md) explains how to run the test again.

## Compared with other tools

We read the README or the docs page of each tool in the table on 3 October 2026. No other tool in the table has all six features. Three of them turn a codebase into a product spec. No page mentions an app run.

A dot means that the page does not mention the feature. It does not prove that the tool lacks it.

| Tool | Reads a finished repo | Lists fake parts | Lists security risks | Starts the app | Separate PM and engineer docs | Checks each cited line |
|---|---|---|---|---|---|---|
| **vibexray** | Yes | Yes | Yes | Yes, with screenshots | Yes | Yes |
| [code-to-prd](https://github.com/alirezarezvani/claude-skills/tree/main/product-team/code-to-prd) | Yes | · | · | · | · | · |
| [pm-ai-shipping](https://github.com/phuryn/pm-skills/tree/main/pm-ai-shipping) | Yes | · | Yes, as audits | · | · | · |
| [code-to-prd-generator](https://mcpmarket.com/tools/skills/code-to-prd-generator-2) | Yes | Claims mock detection | · | · | · | · |
| [Reverse_Spec_and_PRD](https://github.com/WindowHyun/Reverse_Spec_and_PRD) | Frontend code only | · | · | · | Yes | · |
| [OpenLore](https://github.com/clay-good/OpenLore) | Yes | · | · | · | · | · |

- **code-to-prd** writes a PRD folder with per-page docs, an API list, and a navigation map.
- **pm-ai-shipping** writes system docs, a permissions matrix, a secrets list, and gap and security audits.
- **code-to-prd-generator** writes a business PRD. Its listing claims mock detection. We did not read its source.
- **Reverse_Spec_and_PRD** writes a spec for developers and a PRD for PMs, from frontend code.
- **OpenLore** writes a code graph and `CODEBASE.md` for coding agents.
- Lovable's own handoff guide exports the code to GitHub and writes no spec (Lovable blog, 19 March 2026).

## What vibexray never does

- It never edits the prototype. The app runs in a temporary copy, and the copy goes when the scan ends.
- It sends no code anywhere itself. The AI review runs in your own Claude Code or Codex session, under that tool's terms.
- It goes online only for the app run, to download packages as `npm install` does. Use `--no-run` to stay offline.
- It never shows a secret. Key-shaped values show as `sk-pro...[hidden]` in every output.
- It never passes your keys to the app. The copy leaves out your `.env` files, and the app starts with `PATH`, a temporary `HOME`, and `PORT` only.
- It never reads another folder's chats. Use `--no-history` to skip the build chat.

## Fix common problems

- **"npm is not installed on this computer, so the app did not start":** install Node, or scan with `--no-run`. The message names the missing tool.
- **"Install the run extra: pip install 'vibexray[run]'":** the app run needs Playwright. Install it, then run `playwright install chromium`.
- **"The browser could not open the app":** run `playwright install chromium`.
- **"The app did not answer within 90 seconds":** check if the app needs a database or keys. The copy leaves out `.env` files on purpose.
- **"Installing the app's packages failed":** vibexray installs with `--ignore-scripts`, and some packages need their scripts. Scan with `--no-run`.
- **Every Codex report says that the app did not start:** the Codex sandbox blocks local servers by default. The code review still runs.
- **"vibexray.json not found. Run vibexray scan first.":** run `vibexray scan`, then pass its `--out` folder to `vibexray review`.
- **"the scanned folder ... no longer exists":** the review reads each cited line from that folder. Run the review before you move it.
- **A review finding is not in the report:** the line check dropped it. `review-result.json` lists each dropped finding.

## Command reference

```text
vibexray scan PATH [--out DIR] [--no-run] [--no-history] [--open] [--json]
vibexray review REPORT_DIR [--input review.json]
vibexray rules
vibexray --version
```

| Flag | Effect |
|---|---|
| `--out DIR` | Write the three files to `DIR`. The default is `./vibexray-report`. |
| `--no-run` | Do not start the app. |
| `--no-history` | Do not read the build chat. |
| `--open` | Open `report.html` in a browser. |
| `--json` | Print `vibexray.json` to the terminal. |

## Development

```bash
uv venv && uv pip install -e ".[dev]"
uv run playwright install chromium
make corpus   # clone the 42 pinned prototype repos
make lint     # ruff check and ruff format --check
make test     # unit and CLI tests
make e2e      # corpus accuracy, app runs, and browser tests
```

Every GIF in this README is a real recording. These targets record them again:

```bash
make demo          # docs/media/hero.gif, from a live Claude Code session
make gif           # docs/media/report.gif, a browser walk through the report
make feature-gifs  # one GIF per report section
make cli-gif       # docs/media/cli.gif, a real terminal scan
```

[AGENTS.md](AGENTS.md) lists the repository contracts. [CONTRIBUTING.md](CONTRIBUTING.md) explains how to add a rule.

## License

MIT. See [LICENSE](LICENSE). Changes are in [CHANGELOG.md](CHANGELOG.md).
