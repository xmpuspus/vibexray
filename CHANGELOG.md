# Changelog

All notable changes to this project are in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - Unreleased

### Added

- The `vibexray` command line tool with the `scan`, `review`, and `rules` commands.
- 72 pattern rules for fake data, fake actions, open access, database rules, secrets, and AI tools.
- The app run: start the prototype in a temporary copy, visit up to 8 pages, and save screenshots.
- The build-chat reader for Claude Code and Codex sessions of the scanned folder.
- The PM report (`report.html`), the engineer handoff (`handoff.md`), and `vibexray.json`.
- The AI review step: `vibexray review` keeps a host finding only if its quote is on the cited line.
- The Agent Skill in `skills/vibexray/`, with a bundled copy of the package and a launcher.
- Plugin manifests for Claude Code and Codex.
- A corpus of 42 pinned public prototypes: 23 tuning repos with 320 labels, and 19 sealed repos with 846 labels from two independent labelers.
- A sealed benchmark run at `587a03a`: Claude Code F1 0.62, Codex F1 0.59.
- Real demo recordings: `docs/hero.gif` from a live Claude Code session and `docs/report.gif` from a browser.
- CI on Linux, macOS, and Windows with Python 3.11 to 3.13.
- A publish workflow with a fresh-venv smoke job.
