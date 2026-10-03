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

The scan has pattern rules, and the rules find only some problems. Most problems need judgment, for example "any customer can look up any order by its number". You, the host agent, find those problems in a review.

vibexray checks each review finding line by line. It keeps a finding only if the file exists, the line exists, and your quote is on that line. It drops the other findings. Drops are normal.

## Steps

1. Find the prototype folder. If the user did not name one, use the current folder.
2. Run the bundled scanner. Resolve the script path from this skill folder.

   ```bash
   python3 scripts/run_vibexray.py scan <folder> --out <folder>/vibexray-report
   ```

   Add `--no-run` only if the user says not to start the app. If the scan fails, show the error and stop.
3. Read `<folder>/vibexray-report/vibexray.json`. Use the rule findings as anchors. Open each cited file and line, and look for related problems near it.
4. Read the prototype's own source files. Skip `node_modules`, build output, lock files, tests, `vibexray-report`, and this skill folder. Walk the checklist below for each file.
5. Write `<folder>/vibexray-report/review.json` in the format below. Give an exact quote for each finding. Never paraphrase a quote.
6. Run the review step:

   ```bash
   python3 scripts/run_vibexray.py review <folder>/vibexray-report --input <folder>/vibexray-report/review.json
   ```

   The command prints the kept count, the dropped count, and the reason for each drop. If a drop comes from a wrong line or a wrong quote, fix that entry and run the step again. Do not add new findings to replace drops.
7. Tell the PM the result in 3 short sentences. Then list the top 3 decisions.
8. Offer to open `report.html`.

## Review checklist

Each item names the category to write in `review.json`.

- Fake data and fake actions:
  - `mock_data`: sample or seed data that the app shows as real.
  - `fake_action`: a button, form, or message that says it did something but did nothing real.
  - `hardcoded_config`: a fixed value that must come from settings or data. Examples are a price, a limit, or a URL.
- Login and access, for every route, page, API handler, and AI tool:
  - `auth_gap`: anyone can call it, or it does not check that the caller owns the record.
  - For example, any customer can open any order by its number alone.
- Database rules:
  - `database_rules`: open Firebase or Supabase rules, or a policy that lets any user read or change all rows.
  - A table with no row-level policy also counts.
- Secrets:
  - `secret_exposure`: a key or token in client code, in a committed `.env` file, or in a public variable.
  - `ai_browser_call`: the browser calls an AI provider with a key.
- Every AI tool. Find the tool list that the model can call, and check each tool:
  - `ai_tool_unbounded`: the tool can change data, send messages, or spend money, and the code puts no limit on it.
  - `ai_prompt_only_rule`: the prompt states a limit or a rule, but the code does not enforce it.
  - `ai_no_human_review`: the tool acts with no person's approval where a person must approve, for example a refund.
  - `ai_fake_tool`: the tool returns sample data or a fixed answer, not real data.
- The AI as a whole:
  - `ai_no_cost_limit`: nothing caps how much the AI writes or spends per request, for example no `max_tokens`.
  - `ai_no_tests`: no tests check the AI's answers, so a prompt change can break the product.
- Other security risks, all as `security_other`:
  - HTML from users or from the AI shown with no escape (XSS).
  - SQL built from strings.
  - Open CORS.
  - No rate limit on a paid AI endpoint.
  - User text that can change the AI's instructions (prompt injection).

Report each problem once. If a rule finding already covers the same file, category, and lines, skip it. vibexray skips repeats.

## Format of review.json

The file holds a JSON list. Each entry is one finding:

```json
[
  {
    "category": "<one category from the checklist>",
    "file": "<path relative to the scanned folder, with forward slashes>",
    "line": 0,
    "end_line": 0,
    "quote": "<exact code text from the cited line or lines>",
    "pm_text": "<one plain sentence for the PM>",
    "engineer_text": "<the problem and the fix, for the engineer>",
    "label": "keep | rewrite | throwaway | check",
    "severity": "high | medium | low",
    "related_file": "<optional second file>",
    "related_line": 0
  }
]
```

- `line` starts at 1. Cite the line where the problem is.
- If the problem covers a whole function, route, or tool, cite its first line. Set `end_line` to its last line.
- Leave out `end_line` for a problem on one line.
- `quote` must be on the cited line or lines. Copy it from the file. Do not include the line numbers that a file viewer shows.
- A short part of the line is enough for `quote`, for example `orders.find((o) => o.id === id)`.
- If the line holds a secret value, quote the part without the value, for example the variable name.
- Use `related_file` and `related_line` for a second place. An example is the prompt line that states a limit the code does not enforce.
- Write `pm_text` with no jargon. Write `engineer_text` with the file, the problem, and the fix.

## Rules

- Never edit the PM's code.
- Never print a secret. If a finding holds a key, name the file and line only.
- Never invent a file, a line, or a quote. vibexray drops findings that do not match the code.
- Keep the PM message plain. Do not use jargon.
- If the review step fails, show the error. The scan report stays valid without the review.

## Labels

- Keep: the part is real and the engineer can build on it.
- Rewrite: the part works but needs a new build.
- Throw away: the part is fake or a demo stub. Write `throwaway` in `review.json`.
- Check: the scan cannot decide. A person must look.

## Output files

- `report.html`: the PM report. Review findings show "AI review, line checked".
- `handoff.md`: the engineer handoff.
- `vibexray.json`: findings, parts, questions, and build-chat prompts. Each finding has `source`: `rule` or `review`.
- `review-result.json`: the kept count, and each dropped or skipped entry with its reason.
