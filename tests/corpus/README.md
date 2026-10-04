# The corpus holds 42 real prototype repos and their hand labels

- `corpus.lock.json` pins each public repo to one commit. All are MIT or Apache-2.0.
- `make corpus` clones them into `.cache/corpus/`. This repo does not copy their code.
- `labels/` holds the answer key. Labelers who never saw vibexray marked each fake part and risk by file and line, with [LABELING.md](LABELING.md).
- Never edit a label to make a test pass. Fix the rule, or record the disagreement in the commit body.

## split.json names five lists

- `dev`: 23 repos with 320 labels from one labeler each. Tuning uses them. The 7 repos of `heldout` are among them.
- `heldout`: the test set of the first two rounds. It joined `dev` after round 2.
- `sealed_1`: the 19 repos of the v1 public test, with 846 labels from two labelers. [SELECTION.md](SELECTION.md) gives the rules. It joined tuning after its one run.
- `tune`: `dev` plus `sealed_1`, 42 repos.
- `sealed`: the next public test set. It stays empty until the maintainer picks its repos.

## The audits judge findings that match no label

- `audit/unmatched-audit.json` judges the unmatched rule findings on `dev`. The rule precision test counts its `labeler_missed` and `duplicate` verdicts as correct.
- `audit/heldout-review-audit.json` judges the 118 unmatched findings of the final held-out round, from both hosts.
- [audit/AUDIT.md](audit/AUDIT.md) gives the blind audit method for sealed rounds. Its auditors never see the labels.
- No audit changed a label.

## Run the review test again

The review test runs real Claude Code or Codex sessions on your subscription login. It strips API keys from the session environment. These commands repeat the v1 public test:

```bash
make corpus
uv run python scripts/eval_review.py --split sealed_1 --runtime claude --runs 3 --jobs 4
uv run python scripts/eval_review.py --split sealed_1 --runtime codex --runs 3 --jobs 3
uv run python scripts/score_rules.py sealed_1
```

Each command writes `tmp/eval-review-<runtime>.md` and keeps each session's files in `tmp/eval-review-<runtime>/`. The summary opens with the number of sessions that wrote a review, and the vibexray commit.

To test a skill variant from another folder, add `--skill <folder> --name <output name>`.

To add an audit to a saved round, run:

```bash
uv run python scripts/unmatched_findings.py tmp/unmatched.json tmp/eval-review-claude --sample 300
uv run python scripts/audit_precision.py tmp/eval-review-claude --audit <audit file>
```

The audit covers only the findings of the round it judged. A new round makes new findings, so its audited number needs a new audit.
