#!/usr/bin/env bash
# Build the demo prototype for docs/hero.tape at /tmp/vibexray-demo/support-bot.
#
# The prototype is ai-customer-support-agent (MIT) at its pinned commit. Run `make corpus`
# first. The script installs its packages, puts the skill at project scope, and runs one
# real Claude Code session in which the PM states two business rules. The report then
# checks those rules against the code.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$REPO/.cache/corpus/ai-customer-support-agent"
DEMO=/tmp/vibexray-demo/support-bot

if [ ! -d "$SRC/.git" ]; then
  echo "Run make corpus first." >&2
  exit 1
fi

rm -rf /tmp/vibexray-demo
mkdir -p "$DEMO"
git -C "$SRC" archive HEAD | tar -x -C "$DEMO"
mkdir -p "$DEMO/.claude/skills"
cp -R "$REPO/skills/vibexray" "$DEMO/.claude/skills/vibexray"
(cd "$DEMO" && npm install --ignore-scripts --no-audit --no-fund --loglevel=error)

# The PM's build chat. --setting-sources keeps the maintainer's own settings out of it.
RULES="Two rules for this support bot: a customer must only see their own orders, and refunds over 100 dollars need a manager's approval. Point to where the code would change. Do not edit files."
(cd "$DEMO" && claude -p "$RULES" --setting-sources project,local --max-turns 8 \
  --allowedTools Read Glob Grep < /dev/null > /dev/null)

echo "Demo ready at $DEMO"
