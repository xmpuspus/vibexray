# The sealed test set uses repos picked by fixed rules, before any scan

These rules picked the repos of the `sealed` split. I wrote them on 2026-10-04, before the search started. Nobody ran vibexray on a candidate before the set was sealed.

## A repo qualifies when it meets every rule

1. It is public on GitHub, and its license is MIT or Apache-2.0.
2. It shows that Claude Code or Codex built it. The evidence can be a `CLAUDE.md`, `AGENTS.md`, `.claude/` folder, or `.codex/` folder, or commit trailers that name Claude or Codex.
3. It is a web app prototype in JavaScript, TypeScript, or Python, with between 15 and 400 source files of its own.
4. Its last push is in 2025 or 2026.
5. It is not a fork. It is not one of the 23 earlier corpus repos, and it is not a near copy of one.
6. The lock file pins its default branch head by commit SHA on the day of the choice.

## The mix leans toward AI apps

- At least half of the repos call an AI model, best with tools or actions.
- Examples are a support bot or an agent that books, refunds, or sends.
- The rest are general prototypes, such as a dashboard, a booking app, or a Supabase app.

## The set stays sealed after labeling

- Two independent labelers label every repo with [LABELING.md](LABELING.md). They never see vibexray's code, its skill, or its output.
- The second labelers started after the first labels landed and before any vibexray run on the set. They never read the first labels.
- After both labels land, nobody reads them, changes them, or checks which of them vibexray missed.
- vibexray runs on the set once, at one commit, and the README publishes the result as it comes out.
- Before that run, one crash check scans each repo with no AI review. It keeps only the exit code and run time. Nobody opens its findings.
- If the crash check finds a crash, the fix goes into the changelog with the repo name.

## The two labelers gave 846 labels after the merge

- The first labelers gave 638 labels. The second labelers gave 702 labels.
- `scripts/merge_labels.py` joined them into 846 labels in `tests/corpus/labels/`.
- `labels-raw/sealed/first/` and `labels-raw/sealed/second/` keep both raw sets for audit.
- One second labeler used two helper agents on `mentee-global__mentee`. The helpers followed the same labeling prompt.

## The first sealed set ran once and then joined tuning

- vibexray v1 ran on the 19 repos once, at commit `587a03a`. [docs/results/sealed-1/](../../docs/results/sealed-1/) holds the result.
- After that run, the 19 repos moved to the `sealed_1` and `tune` lists in `split.json`. Skill changes after `587a03a` can use them.
- The next public test set follows the same rules, with 19 new repos and two new labelers.
