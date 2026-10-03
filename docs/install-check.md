# Both Claude Code and Codex accept the vibexray plugin

Checked on 2026-10-03 with `claude` 2.1.288 and `codex-cli` 0.160.0. No command wrote to `~/.claude`, `~/.codex`, or `~/.agents`.

## Claude Code validation passes

Command: `claude plugin validate <worktree>` (exit 0).

```text
Validating marketplace manifest: <worktree>/.claude-plugin/marketplace.json

Validation passed
```

## Codex installs the plugin from a clean copy of the repo

The run used a scratch `CODEX_HOME` and left `HOME` unchanged. The source was a copy of the repo without `.venv`, `tmp`, and `.git`.

The first try used the worktree itself as the source, with the scratch folder inside it. It failed with `File name too long (os error 63)`. Codex copied the scratch folder into itself. Keep the scratch folder outside the plugin source.

```text
$ codex plugin marketplace add /tmp/vibexray-install-src
Added marketplace `vibexray` from /private/tmp/vibexray-install-src.
Installed marketplace root: /private/tmp/vibexray-install-src

$ codex plugin add vibexray@vibexray
Added plugin `vibexray` from marketplace `vibexray`.
Installed plugin root: <scratch>/plugins/cache/vibexray/vibexray/0.1.0

$ codex plugin list
Marketplace `vibexray`
/private/tmp/vibexray-install-src/.agents/plugins/marketplace.json
PLUGIN             STATUS              VERSION  SOURCE
vibexray@vibexray  installed, enabled  0.1.0    /private/tmp/vibexray-install-src
```

The cached plugin held `skills/vibexray/SKILL.md` and `skills/vibexray/scripts/run_vibexray.py`. Running `python3 scripts/run_vibexray.py --version` from the cached skill folder printed `vibexray 0.1.0`.

## Not checked

- Install from the real GitHub repository. Only local paths ran.
- Cowork install.
