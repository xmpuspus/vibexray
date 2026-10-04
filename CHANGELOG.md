# Changelog

All notable changes to this project are in this file. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The project follows [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-04

First release.

### Added

- The `vibexray` command line tool with the `scan`, `review`, and `rules` commands.
- 72 pattern rules for fake data, fake actions, open access, database rules, secrets, and AI tools.
- The app run. It starts the prototype in a temporary copy, visits up to 8 pages, and saves screenshots.
- The build-chat reader for Claude Code and Codex sessions of the scanned folder.
- The PM report (`report.html`), the engineer handoff (`handoff.md`), and `vibexray.json`.
- The AI review step. `vibexray review` keeps a host finding only if its quote is on the cited line.
- The Agent Skill in `skills/vibexray/`, with a bundled copy of the package and a launcher.
- Plugin manifests for Claude Code and Codex.

[0.1.0]: https://github.com/xmpuspus/vibexray/releases/tag/v0.1.0
