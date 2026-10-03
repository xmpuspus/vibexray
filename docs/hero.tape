# vibexray hero demo (VHS, https://github.com/charmbracelet/vhs)
#
# A real Claude Code session runs the vibexray skill on a real support-bot prototype.
# Regenerate with:
#   scripts/bootstrap-demo.sh
#   vhs docs/hero.tape
#   uv run python scripts/video_to_gif.py tmp/hero/hero.mp4 docs/hero.gif --seconds 45
#
# The session takes several minutes in real time. video_to_gif.py speeds it up to the
# target length. The alias allows the skill's tools and refuses others without a prompt, so the GIF shows no permission
# prompts, and loads project settings only, so the maintainer's own settings stay out.
# The loop drops API keys and the recorder's own session variables, so the session uses
# the subscription login. Answer Claude Code's folder trust question once before recording.

Output tmp/hero/hero.mp4

Set Theme "Catppuccin Mocha"
Set FontSize 16
Set Width 1280
Set Height 760
Set Padding 20
Set TypingSpeed 40ms
Set Shell "bash"

Hide
Type `for v in $(compgen -e | grep -E '^(CLAUDE|ANTHROPIC|OPENAI|CODEX)'); do unset $v; done; cd /tmp/vibexray-demo/support-bot && export PS1='$ ' && alias claude='claude --setting-sources project,local --permission-mode dontAsk --allowedTools "Read,Write,Edit,Glob,Grep,Skill,Bash(python3:*),Bash(ls:*),Bash(cat:*),Bash(head:*),Bash(wc:*),Bash(grep:*),Bash(find:*)"' && clear`
Enter
Sleep 800ms
Show

Type "claude"
Enter
Sleep 6s
Type "/vibexray Is this support bot ready for engineering?"
Sleep 800ms
Enter
# The skill ends with the top 3 decisions. That phrase starts a line, so it never wraps.
Wait+Screen@25m /[Tt]op (3|three) decisions/
Sleep 10s
