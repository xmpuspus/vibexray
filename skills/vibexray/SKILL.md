---
name: vibexray
description: X-rays a prototype built with AI and writes a PM report, an engineer handoff, and a JSON file. It shows what is real, what is fake, what can break, and what the PM must decide. Use when the user asks "is this ready for engineering", "what is fake in my prototype", "hand this off", "x-ray my app", or "vibexray". Also use for a prototype built with Claude Code, Codex, Lovable, v0, or Bolt.
license: MIT
compatibility: The scan needs Python 3.11 or newer and no network. The app run is optional. It needs Node, Playwright, and network access to install packages.
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

   Run the scan in the foreground and wait until it ends. Never run it in the background. When it starts the app, it can take up to 10 minutes, so set the command timeout to 10 minutes.

   Add `--no-run` only if the user says not to start the app. If the command exits with an error, show the error and stop. If the app did not start, for example because a sandbox blocked it, the scan is still valid. Go on to step 3.
3. Read `<folder>/vibexray-report/vibexray.json`. Its `parts` list names every source file of the app. Its `findings` list holds the rule findings.
4. Check each rule finding. Open its file and line. If the code shows that the rule is wrong there, write a reject entry with the reason. Keep the rule findings that hold.
5. Read every file in the `parts` list. Also read the env examples, and the data or knowledge-base files that the app loads. Skip vendored UI library files, such as `components/ui/*` from shadcn. Then walk the checklist below one group at a time, over all the files:
   1. fake data and fake actions,
   2. login, access, and database rules,
   3. secrets,
   4. each AI tool, then the AI as a whole,
   5. other security risks.
6. Verify each finding before you keep it. Reread its cited lines. Keep it only if those lines show the problem. Drop a finding that guesses about code you did not read.
7. Write `<folder>/vibexray-report/review.json` in the format below. Give an exact quote for each finding. Never paraphrase a quote.
8. Run the review step:

   ```bash
   python3 scripts/run_vibexray.py review <folder>/vibexray-report --input <folder>/vibexray-report/review.json
   ```

   The command prints the kept count, the dropped count, and the reason for each drop. If a drop comes from a wrong line or a wrong quote, fix that entry and run the step again. Do not add new findings to replace drops.
9. Tell the PM the result in 3 short sentences. Then list the top 3 decisions.
10. Offer to open `report.html`.

## Review checklist

Each item names the category to write in `review.json`. The definitions match the guide that labeled vibexray's test set.

- Fake data and fake actions:
  - `mock_data`: hardcoded sample records, fixtures, sample customers or orders, or lorem ipsum, used as if real.
  - Seed scripts count, for example `seed.ts` or `seed.sql`. Cite each block of sample records.
  - Sample help articles or knowledge-base files with invented prices or policies count.
  - A mock AI provider that gives canned replies counts.
  - `fake_action`: UI that shows success with no real effect.
  - Examples: a setTimeout success, a toast with no call, a `console.log` in place of a send, a TODO handler.
  - `hardcoded_config`: localhost URLs, and hardcoded prices, limits, or feature flags that belong in config.
  - The same kind of value set to two different numbers also counts. Give the second place as `related_file`.
- Login and access, for every route, page, and API handler:
  - `auth_gap`: a protected page or action that works with no login check.
  - A hardcoded user or role counts. A check done only in client code counts.
  - A missing check that the caller owns the record counts, for example any customer can open any order.
- Database rules:
  - `database_rules`: a table with no row level security, or a permissive policy, such as `USING (true)` on user data.
  - Client writes to sensitive tables count. A service key in client code counts here.
- Secrets:
  - `secret_exposure`: a secret-looking key in client code or in a browser-exposed env var.
  - A committed `.env` file with secret values counts. A demo password in a seed file or `.env.example` counts.
  - A Supabase anon key alone is public by design. Do not report it.
  - `ai_browser_call`: browser code calls a model API, or a browser-exposed env var holds a model key.
- Every AI tool. Find every tool that the model can call, also in server functions such as `supabase/functions/`. Check each tool on its own:
  - `ai_tool_unbounded`: a tool changes money or data, or sends something, with no limit or validation in its code.
  - Examples: no check that the record belongs to the caller, no allowed-status rule, no length limit on its input.
  - `ai_no_human_review`: a tool sends, refunds, books, or changes records with no human approval step.
  - Report each such tool. One finding for the whole tool list is not enough.
  - `ai_prompt_only_rule`: the system prompt states a limit or rule, and the tool code has no matching check.
  - Cite the prompt line in `file` and `line`. Give the tool code as `related_file` and `related_line`.
  - `ai_fake_tool`: a tool returns hardcoded or sample results, or says it did an action that it did not do.
- The AI as a whole:
  - `ai_no_cost_limit`: nothing caps how much the AI writes or spends per request, for example no `max_tokens`.
  - `ai_no_tests`: no tests check the AI's answers, so a prompt change can break the product.
- `security_other`: any other security problem. Examples:
  - HTML from users or from the AI shown with no escape, `eval`, or SQL built from strings.
  - Open CORS, or user input joined into a prompt with no guard.
  - Tokens in localStorage, or prices that the server takes from the client.
  - No rate limit on a paid AI endpoint, or a webhook endpoint with no signature check.
  - An error handler that sends internal error text to the client.

Pick one category for each problem:

- A problem inside an AI tool gets an `ai_` category, not `auth_gap` or `fake_action`.
- A missing login or ownership check on a route or page is `auth_gap`, not `security_other`.
- A service key in client code is `database_rules`, not `secret_exposure`.

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
- Quote at least 6 characters, not counting spaces. For a span of more than 30 lines, quote at least 16.
- Never cite more than 300 lines in one finding.
- If the line holds a secret value, quote the part without the value, for example the variable name.
- Use `related_file` and `related_line` for a second place. For `ai_prompt_only_rule`, the second place is the tool code.
- Write `pm_text` with no jargon. Write `engineer_text` with the file, the problem, and the fix.

A reject entry removes one rule finding that the code shows to be wrong:

```json
{"reject": true, "file": "<file of the rule finding>", "line": 0, "rule_id": "<its rule_id>", "reason": "<what in the code shows that the rule is wrong>"}
```

- Reject only when the code clearly shows that the rule is wrong. When you are not sure, keep the rule finding.
- The reason needs 12 characters or more. The engineer sees every reason in `handoff.md`.

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
