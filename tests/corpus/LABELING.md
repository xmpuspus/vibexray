# Labelers mark every fake part and risk by file and line, with no help from vibexray

This guide made every label in `labels/`. The labelers got the same words in their task. A labeler never reads vibexray's code, its skill, its rules, or its output, so the labels stay independent of the tool.

## Read the app's own code

Read the system prompts, every tool or function definition and its code, and the API routes. Also read the UI, the data and seed files, the database migrations, and the env examples.

Skip vendored UI library files, such as `components/ui/*` from shadcn. Skip lockfiles, images, and `node_modules`. Do not run, install, or build the repo.

## Mark every instance of these categories

- `ai_browser_call`: browser code calls a model API, or a browser-exposed env var holds a model key.
- `ai_tool_unbounded`: a tool changes money or data, or sends something, with no limit or validation in its code.
- `ai_prompt_only_rule`: the system prompt states a limit or rule, and the tool code has no matching check.
  - Put the prompt line in `file` and `line_start`. Put the tool code in `related_file` and `related_line`.
- `ai_no_human_review`: a tool sends, refunds, books, or changes records with no human approval step.
- `ai_fake_tool`: a tool returns hardcoded or sample results instead of results from a real system.
- `mock_data`: hardcoded sample records, fixtures, sample customers or orders, or lorem ipsum, used as if real.
- `fake_action`: UI that shows success with no real effect.
  - Examples: a setTimeout success, a toast with no call, a `console.log` in place of a send, a TODO handler.
- `auth_gap`: a protected page or action that works with no login check.
  - A hardcoded user or role counts. A check done only in client code counts.
- `database_rules`: a table with no row level security, or a permissive policy.
  - Client writes to sensitive tables count. A service key in client code counts.
- `secret_exposure`: a secret-looking key in client code or in a browser-exposed env var.
  - A committed `.env` file with secret values counts.
  - A Supabase anon key alone is public by design. Mark it only as `note_public_key`.
- `hardcoded_config`: localhost URLs, and hardcoded prices, limits, or feature flags that belong in config.
  - The same kind of value set to two different numbers also counts.
- `security_other`: any other security problem. Examples:
  - `eval`, open CORS, or SQL built from strings.
  - User input joined into a prompt with no guard.
  - Tokens in localStorage, or prices that the server takes from the client.
  - No rate limit on a paid AI endpoint, or a webhook endpoint with no signature check.

## Write one JSON file per repo

The file holds `repo`, `sha`, `labeler`, `files_reviewed`, `note`, and `labels`. Each label holds:

- `category`, `file`, `line_start`, and `line_end`.
- `related_file` and `related_line`, when a second place belongs to the problem.
- `what`: one plain sentence about the problem.
- `keep_rewrite_throwaway`: `keep`, `rewrite`, or `throwaway`.
- `confidence`: `high`, `medium`, or `low`. Scoring leaves out the `low` labels.

List every file you read in `files_reviewed`, so the answer key states what it covers. Scoring counts only findings in those files.

## Keep secrets out of the labels

- Quote nothing secret. For a secret, write "secret value present" only.
- If a permission rule blocks a file, such as a `.env` file, note it in `files_reviewed` as blocked and move on.
