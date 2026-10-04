# vibexray reports two numbers, and both come from a sealed test set

vibexray publishes two numbers together. One number alone is easy to game: a tool that flags every line finds every problem. This file fixed both definitions on 2026-10-04, before the sealed set existed. The scoring code in `tests/test_corpus_accuracy.py` and `scripts/eval_review.py` follows it.

## The first number is the share of labeled problems that vibexray finds

- The answer key is the label files in `tests/corpus/labels/`. [LABELING.md](../tests/corpus/LABELING.md) explains how independent labelers made them.
- Two labelers labeled each sealed repo on their own. `scripts/merge_labels.py` joins their files. A problem that both labelers marked counts once.
- A label counts unless its confidence is `low` or its category is `note_public_key`.
- A finding finds a label when both have the same category, in the same file.
- Their line spans must overlap, with 3 lines of slack on each side of the label. A finding on the label's related file and line also counts.

## The second number is the share of findings that match a label

- Only findings in files that the labeler read count, because the key covers only those files.
- The labelers had no `ai_no_tests` or `ai_no_cost_limit` category, so findings in those two categories do not count.
- A finding is right when it finds any label of the repo, low-confidence labels included.

The labels miss some real problems, so this number is a floor. A third line can add an independent audit:

- An auditor who did not build vibexray reads the code at each finding that matched no label.
- The auditor sees the code and the finding, but never the labels.
- A finding counts as right when the auditor says that it is a real problem of that category.
- The audit covers only the round it judged. A new round needs a new audit.
- The held-out audit of round 2 used an older form. Its auditors saw the labels and judged repeats against them.

## F1 joins the two numbers into one

- F1 is 2 x precision x recall / (precision + recall).
- The README computes it from the pooled counts of all runs of a host.

## Each host runs three times, and failed runs stay in the average

- The test runs Claude Code and Codex, each 3 times per repo, on the subscription login with no API keys.
- Each session copies the repo to a new temporary folder and installs the skill at project scope.
- The summary opens with the number of sessions that wrote a review. A session with no review scores the rule findings alone.
- Claude Code loads project settings only. Codex skips the user's config and rules, but it still loads the maintainer's global `AGENTS.md`.

## Tuning uses the dev split, and the sealed split runs once

- `split.json` names the splits. Rules and the skill change only in response to `dev` results.
- The `sealed` split follows [SELECTION.md](../tests/corpus/SELECTION.md). It runs once, at one commit, and its result goes out as it comes.
- The matching above never changes to raise a number.

## Run the test again

```bash
make corpus
uv run python scripts/eval_review.py --split sealed_1 --runtime claude --runs 3 --jobs 4
uv run python scripts/eval_review.py --split sealed_1 --runtime codex --runs 3 --jobs 3
```
