---
name: vibexray
description: X-rays a prototype built with AI and writes a PM report, an engineer handoff, and a JSON file. It shows what is real, what is fake, what can break, and what the PM must decide. Use when the user asks "is this ready for engineering", "what is fake in my prototype", "hand this off", "x-ray my app", or "vibexray". Also use for a prototype built with Claude Code, Codex, Lovable, v0, or Bolt.
license: MIT
compatibility: Needs Python 3.11 or newer and no network. Running the app is optional and needs Node and Playwright.
metadata:
  version: "0.1.0"
  repository: https://github.com/xmpuspus/vibexray
---

# vibexray

vibexray scans a prototype folder. It writes `report.html` for the PM, `handoff.md` for the engineer, and `vibexray.json` for tools.

## Steps

1. Find the prototype folder. If the user did not name one, use the current folder.
2. Run the bundled scanner. Resolve the script path from this skill folder.

   ```bash
   python3 scripts/run_vibexray.py scan <folder> --out <folder>/vibexray-report
   ```

   Add `--no-run` only if the user says not to start the app.
3. Read `<folder>/vibexray-report/vibexray.json`.
4. Review each finding against the code at the file and line that the finding names.
   - Keep the label that the rule gave.
   - To change a label, write a one-line reason beside the new label.
   - Never invent a finding that the scan did not report.
5. Read the build-chat prompts in the JSON, if there are any. Add open questions for the PM in plain words.
6. Tell the PM the result in 3 short sentences. Then list the top 3 decisions.
7. Offer to open `report.html`.

## Rules

- Never edit the PM's code.
- Never print a secret. If a finding holds a key, name the file and line only.
- Keep the engineer handoff precise. Name the file, the line, and the fix.
- Keep the PM message plain. Do not use jargon.
- If the scan fails, show the error and stop. Do not guess a result.

## Labels

- Keep: the part is real and the engineer can build on it.
- Rewrite: the part works but needs a new build.
- Throw away: the part is fake or a demo stub.
- Check: the scan cannot decide. A person must look.

## Output files

- `report.html`: the PM report.
- `handoff.md`: the engineer handoff.
- `vibexray.json`: findings, parts, questions, and build-chat prompts.
