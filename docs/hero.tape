# vibexray hero demo (VHS, https://github.com/charmbracelet/vhs)
#
# A real Claude Code session runs the vibexray skill on a real support-bot prototype.
# Regenerate with:
#   scripts/bootstrap-demo.sh
#   vhs docs/hero.tape
#   uv run python scripts/video_to_gif.py tmp/hero/hero.mp4 docs/hero.gif --trim-tail --seconds 50 --hold 10
#
# The session takes several minutes in real time. video_to_gif.py speeds it up to the
# target length. The alias allows the tools the skill uses, so the GIF shows no permission
# prompts. It loads project settings only, so the maintainer's own settings stay out.
# Record in a throwaway copy only, because the alias allows every shell command.
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
Type `for v in $(compgen -e | grep -E '^(CLAUDE|ANTHROPIC|OPENAI|CODEX)'); do unset $v; done; cd /tmp/vibexray-demo/support-bot && export PS1='$ ' && alias claude='claude --setting-sources project,local --allowedTools "Read,Write,Edit,Glob,Grep,Skill,Bash"' && clear`
Enter
Sleep 800ms
Show

Type "claude"
Enter
Sleep 6s
Type "/vibexray Is this support bot ready for engineering?"
Sleep 800ms
Enter
# The session needs about 5 minutes. video_to_gif.py --trim-tail cuts the still screen at the end.
Sleep 10m
