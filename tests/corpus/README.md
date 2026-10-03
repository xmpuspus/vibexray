# The corpus holds 23 real prototype repos and 320 hand labels

- `corpus.lock.json` pins each public repo to one commit. All are MIT or Apache-2.0.
- `make corpus` clones them into `.cache/corpus/`. This repo does not copy their code.
- `labels/` holds the answer key. A reviewer who never saw the rules marked each fake part and risk by file and line.
- Never edit a label to make a test pass. Fix the rule, or record the disagreement in the commit body.
- `split.json` puts 16 repos in `dev` and 7 Claude Code or Codex repos in `heldout`. Tune only on `dev`.

## The audits judge findings that match no label

- `audit/unmatched-audit.json` judges the unmatched rule findings on `dev`. The rule precision test counts its `labeler_missed` and `duplicate` verdicts as correct.
- `audit/heldout-review-audit.json` judges the 118 unmatched findings of the final held-out round, from both hosts.
- An auditor who did not build vibexray read the code at each finding. Neither audit changed a label.

## Run the review test again

The review test runs real Claude Code or Codex sessions on your subscription login. It strips API keys from the session environment.

```bash
make corpus
uv run python scripts/eval_review.py --split heldout --runtime claude --runs 3 --jobs 4
uv run python scripts/eval_review.py --split heldout --runtime codex --runs 3 --jobs 3
```

Each command writes `tmp/eval-review-<runtime>.md` and keeps each session's files in `tmp/eval-review-<runtime>/`. The summary opens with the number of sessions that wrote a review.

To add the held-out audit to a saved round, run:

```bash
uv run python scripts/audit_precision.py tmp/eval-review-claude
```

The audit covers only the findings of the round it judged. A new round makes new findings, so its audited number needs a new audit.
