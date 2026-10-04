# vibexray command line demo (VHS, https://github.com/charmbracelet/vhs)
#
# A real scan of the pinned support-bot prototype, with no AI host. Regenerate with:
#   make cli-gif
#
# make cli-gif copies the prototype to /tmp/vibexray-demo-cli first. The scan uses
# --no-run and --no-history, so it starts nothing and reads no chats.

Output tmp/cli/cli.mp4

Set Theme "Github"
Set FontSize 15
Set Width 1600
Set Height 720
Set Padding 20
Set TypingSpeed 40ms
Set Shell "bash"

Hide
Type `export PATH="$PWD/.venv/bin:$PATH" && cd /tmp/vibexray-demo-cli && export PS1='$ ' && clear`
Enter
Sleep 800ms
Show

Type "vibexray scan support-bot --no-run --no-history --out report"
Sleep 500ms
Enter
Sleep 5s
Type "vibexray rules | head -n 10"
Sleep 500ms
Enter
Sleep 5s
