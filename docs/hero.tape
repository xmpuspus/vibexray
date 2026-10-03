# vibexray hero demo (VHS, https://github.com/charmbracelet/vhs)
#
# A real Claude Code session runs the vibexray skill on a real support-bot prototype.
# Regenerate with:
#   scripts/bootstrap-demo.sh
#   vhs docs/hero.tape
#   uv run python scripts/video_to_gif.py tmp/hero/hero.mp4 docs/hero.gif --seconds 45
#
# The session takes several minutes in real time. video_to_gif.py speeds it up to the
# target length. The alias pre-approves the skill's tools, so the GIF shows no permission
# prompts, and loads project settings only, so the maintainer's own settings stay out.

Output tmp/hero/hero.mp4

Set Theme "Catppuccin Mocha"
Set FontSize 16
Set Width 1280
Set Height 760
Set Padding 20
Set TypingSpeed 40ms
Set Shell "bash"

Hide
Type `cd /tmp/vibexray-demo/support-bot && export PS1='$ ' && alias claude='claude --setting-sources project,local --permission-mode acceptEdits --allowedTools "Read,Write,Edit,Glob,Grep,Skill,Bash(python3:*),Bash(ls:*),Bash(cat:*),Bash(head:*),Bash(wc:*),Bash(grep:*),Bash(find:*)"' && clear`
Enter
Sleep 800ms
Show

Type "claude"
Enter
Sleep 6s
Type "/vibexray Is this support bot ready for engineering?"
Sleep 800ms
Enter
Wait+Screen@25m /Want me to open|open report\.html|Open report\.html|open the report/
Sleep 6s
