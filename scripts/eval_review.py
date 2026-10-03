"""Score pattern rules plus the host AI's review against the hand labels.

For each corpus repo and each run, the script:
1. copies the repo to a new temp folder outside this repository, so the session cannot
   read this repository's guide or the answer key;
2. puts the skill at project scope in the copy (.claude/skills/ or .agents/skills/);
3. runs one headless Claude Code or Codex session on the subscription login;
4. re-applies the session's review.json, and scores rules plus kept review findings with
   the matching in tests/test_corpus_accuracy.py.

It prints totals only, never label rows. Results go to tmp/eval-review-<runtime>.json and .md,
and each session's files go to tmp/eval-review-<runtime>/<repo>/run-<n>/.

    uv run python scripts/eval_review.py --runtime claude --runs 1 Snodrod__ai-support-agent
    uv run python scripts/eval_review.py --runtime codex --runs 3 --split heldout --jobs 3
"""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "src"), str(REPO / "tests")]

from conftest import CORPUS_DIR  # noqa: E402
from test_corpus_accuracy import IGNORED, LABELS_DIR, SPLIT, hits, reviewed_files  # noqa: E402

from vibexray.cli import scan  # noqa: E402
from vibexray.report import write_reports  # noqa: E402
from vibexray.review import ReviewError, apply_review  # noqa: E402

SKILL = REPO / "skills" / "vibexray"
OUT = REPO / "tmp"
PROMPT = (
    "Use the vibexray skill to x-ray this prototype. Write review.json and run the review step."
)
SKILL_HOME = {"claude": ".claude/skills/vibexray", "codex": ".agents/skills/vibexray"}
# A key in the environment switches the CLI from the subscription login to API billing.
KEY_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY", "CODEX_API_KEY")
CLAUDE_TOOLS = ",".join(
    [
        "Read",
        "Write",
        "Edit",
        "Glob",
        "Grep",
        "Skill",
        "Bash(python3:*)",
        "Bash(ls:*)",
        "Bash(cat:*)",
        "Bash(head:*)",
        "Bash(wc:*)",
        "Bash(grep:*)",
        "Bash(find:*)",
    ]
)


def bundle_is_fresh() -> bool:
    src, dst = REPO / "src" / "vibexray", SKILL / "scripts" / "vibexray"
    return all(
        (dst / p.relative_to(src)).is_file()
        and filecmp.cmp(p, dst / p.relative_to(src), shallow=False)
        for p in src.rglob("*.py")
    )


def command(runtime: str, copy: Path, max_turns: int, model: str | None) -> list[str]:
    if runtime == "claude":
        cmd = ["claude", "-p", PROMPT, "--max-turns", str(max_turns), "--output-format", "json"]
        # project,local skips the user's own hooks, skills, and CLAUDE.md, like a PM's machine.
        cmd += ["--setting-sources", "project,local", "--no-session-persistence"]
        cmd += ["--permission-mode", "acceptEdits", "--allowedTools", CLAUDE_TOOLS]
    else:
        cmd = ["codex", "exec", "--skip-git-repo-check", "--ephemeral", "--json"]
        cmd += ["-C", str(copy), "-s", "workspace-write", PROMPT]
    if model:
        cmd[2:2] = ["--model", model]
    return cmd


def find_one(copy: Path, name: str) -> Path | None:
    preferred = copy / "vibexray-report" / name
    if preferred.is_file():
        return preferred
    found = [
        p
        for p in copy.rglob(name)
        if not p.relative_to(copy).as_posix().startswith((".claude/", ".agents/", ".git/"))
    ]
    return found[0] if found else None


def score(name: str, findings: list[dict]) -> dict:
    data = json.loads((LABELS_DIR / f"{name}.json").read_text())
    labels = [
        lb
        for lb in data["labels"]
        if lb["category"] not in IGNORED and lb.get("confidence") != "low"
    ]
    reviewed = reviewed_files(data, labels)
    fs = [SimpleNamespace(**f) for f in findings if f["file"] in reviewed]
    return {
        "labels": len(labels),
        "found": sum(any(hits(f, lb) for f in fs) for lb in labels),
        "findings": len(fs),
        "correct": sum(any(hits(f, lb) for lb in data["labels"]) for f in fs),
    }


def score_parts(name: str, findings: list[dict]) -> dict:
    # The review-only score shows whether rule noise or the review misses the precision bar.
    source = {"rules": "rule", "review": "review"}
    out = {
        k: score(name, [f for f in findings if f.get("source", "rule") == v])
        for k, v in source.items()
    }
    out["all"] = score(name, findings)
    return out


def ratio(a: int, b: int) -> float:
    return round(a / b, 4) if b else 1.0


def one_run(args: argparse.Namespace, name: str, run: int) -> dict:
    keep_dir = OUT / f"eval-review-{args.runtime}" / name / f"run-{run}"
    if keep_dir.exists():
        shutil.rmtree(keep_dir)
    keep_dir.mkdir(parents=True)
    work = Path(tempfile.mkdtemp(prefix=f"vibexray-eval-{name[:24]}-"))
    copy = work / name
    shutil.copytree(args.corpus / name, copy, symlinks=True)
    shutil.copytree(SKILL, copy / SKILL_HOME[args.runtime])

    env = {k: v for k, v in os.environ.items() if k not in KEY_VARS}
    env["NO_COLOR"] = "1"
    row: dict = {"repo": name, "run": run, "workdir": str(copy) if args.keep else None}
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command(args.runtime, copy, args.max_turns, args.model),
            cwd=copy,
            env=env,
            capture_output=True,
            text=True,
            timeout=args.timeout,
            stdin=subprocess.DEVNULL,
        )
        (keep_dir / "session.out").write_text(proc.stdout)
        (keep_dir / "session.err").write_text(proc.stderr)
        row["exit_code"] = proc.returncode
    except subprocess.TimeoutExpired:
        row["exit_code"] = "timeout"
    row["minutes"] = round((time.monotonic() - started) / 60, 1)

    report = find_one(copy, "vibexray.json")
    review = find_one(copy, "review.json")
    row["skill_scanned"] = report is not None
    row["review_written"] = review is not None
    if report is None:
        # The skill never ran. Score the rule floor so the run still counts, and flag it.
        result = scan(copy, keep_dir / "report", run=False, history_mode="none")
        report = write_reports(result, keep_dir / "report")["json"]
    if review is not None:
        shutil.copy(review, keep_dir / "review.json")
        try:
            checked = apply_review(report.parent, review)
            row.update(entries=checked.total, kept=len(checked.kept))
            row.update(dropped=len(checked.dropped), duplicates=len(checked.duplicates))
            row["drop_reasons"] = [d.reason for d in checked.dropped]
        except ReviewError as exc:
            row["review_error"] = str(exc)
    for extra in ("vibexray.json", "review-result.json", "handoff.md"):
        if (report.parent / extra).is_file():
            shutil.copy(report.parent / extra, keep_dir / extra)

    findings = json.loads(report.read_text())["findings"]
    row.update(score_parts(name, findings))
    if not args.keep:
        shutil.rmtree(work, ignore_errors=True)
    return row


def pooled(rows: list[dict], key: str) -> dict:
    t = {k: sum(r[key][k] for r in rows) for k in ("labels", "found", "findings", "correct")}
    return {
        "recall": ratio(t["found"], t["labels"]),
        "precision": ratio(t["correct"], t["findings"]),
        **t,
    }


def summarize(args: argparse.Namespace, repos: list[str], rows: list[dict]) -> dict:
    per_run = []
    for run in range(1, args.runs + 1):
        mine = [r for r in rows if r["run"] == run]
        per_run.append({"run": run, **{k: pooled(mine, k) for k in ("all", "rules", "review")}})
    recalls = [p["all"]["recall"] for p in per_run]
    precisions = [p["all"]["precision"] for p in per_run]
    entries = sum(r.get("entries", 0) for r in rows)
    dropped = sum(r.get("dropped", 0) for r in rows)
    return {
        "runtime": args.runtime,
        "repos": repos,
        "runs": args.runs,
        "prompt": PROMPT,
        "recall_mean": round(sum(recalls) / len(recalls), 4),
        "recall_min": min(recalls),
        "precision_mean": round(sum(precisions) / len(precisions), 4),
        "precision_min": min(precisions),
        # A run with no review scores the rules alone. Show the count first so it never hides.
        "reviews_written": sum(1 for r in rows if r["review_written"]),
        "sessions": len(rows),
        "citation_drop_rate": ratio(dropped, entries) if entries else None,
        "review_entries": entries,
        "review_dropped": dropped,
        "per_run": per_run,
        "per_repo_run": rows,
    }


def markdown(s: dict) -> str:
    drop = s["citation_drop_rate"]
    lines = [
        f"# Rules plus {s['runtime']} review: recall {s['recall_mean']:.2f} mean, "
        f"precision {s['precision_mean']:.2f} mean",
        "",
        f"- Review written in {s['reviews_written']} of {s['sessions']} sessions. "
        "A session with no review counts with the rule findings only.",
        f"- Repos: {', '.join(s['repos'])}",
        f"- Runs per repo: {s['runs']}",
        f"- Recall: mean {s['recall_mean']:.2f}, minimum {s['recall_min']:.2f}",
        f"- Precision: mean {s['precision_mean']:.2f}, minimum {s['precision_min']:.2f}",
        f"- Citation drop rate: {'no review entries' if drop is None else f'{drop:.2f}'} "
        f"({s['review_dropped']} of {s['review_entries']} entries)",
        "",
        "| Run | Findings | Recall | Precision |",
        "|---|---|---|---|",
    ]
    for p in s["per_run"]:
        for key, title in (("all", "rules plus review"), ("rules", "rules"), ("review", "review")):
            a = p[key]
            lines.append(
                f"| {p['run']} | {title} | {a['recall']:.2f} ({a['found']}/{a['labels']}) "
                f"| {a['precision']:.2f} ({a['correct']}/{a['findings']}) |"
            )
    lines += ["", "| Repo | Run | Scan | Review | Kept | Dropped | Repeats | Minutes |"]
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in s["per_repo_run"]:
        lines.append(
            f"| {r['repo']} | {r['run']} | {'yes' if r['skill_scanned'] else 'no'} "
            f"| {'yes' if r['review_written'] else 'no'} | {r.get('kept', 0)} "
            f"| {r.get('dropped', 0)} | {r.get('duplicates', 0)} | {r['minutes']} |"
        )
    return "\n".join(lines) + "\n"


def pinned_and_clean(path: Path) -> bool:
    # An earlier app run wrote package-lock.json into the clones. A changed tree changes the input.
    pins = {
        e["folder"]: e["sha"]
        for e in json.loads((REPO / "tests/corpus/corpus.lock.json").read_text())
    }
    git = ["git", "-C", str(path)]
    head = subprocess.run(
        [*git, "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    status = subprocess.run([*git, "status", "--porcelain"], capture_output=True, text=True).stdout
    return head == pins.get(path.name) and not status.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repos", nargs="*", help="Corpus repo names")
    splits = sorted(k for k, v in SPLIT.items() if isinstance(v, list))
    parser.add_argument("--split", choices=splits, help="Use every repo in this split")
    parser.add_argument("--runtime", choices=("claude", "codex"), default="claude")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--jobs", type=int, default=1, help="Sessions to run at the same time")
    parser.add_argument("--max-turns", type=int, default=60)
    parser.add_argument("--timeout", type=int, default=2400, help="Seconds per session")
    parser.add_argument("--model", help="Model for the session (default: the CLI default)")
    parser.add_argument("--corpus", type=Path, default=CORPUS_DIR)
    parser.add_argument("--keep", action="store_true", help="Keep the temp copies")
    args = parser.parse_args(argv)

    repos = args.repos or (SPLIT[args.split] if args.split else [])
    if not repos:
        parser.error("name at least one repo, or use --split")
    missing = [n for n in repos if not (args.corpus / n).is_dir()]
    if missing:
        parser.error(f"not in {args.corpus}: {', '.join(missing)}")
    if not bundle_is_fresh():
        parser.error("the skill bundle is stale; run `make bundle` first")
    changed = [n for n in repos if not pinned_and_clean(args.corpus / n)]
    if changed:
        parser.error(
            "these corpus repos are not at their pinned commit or have local changes: "
            f"{', '.join(changed)}. Use `make corpus` for clean clones in .cache/corpus, "
            "or restore each repo with `git -C <repo> reset -q --hard <sha> && git -C <repo> clean -qfd`."
        )

    jobs = [(n, run) for run in range(1, args.runs + 1) for n in repos]
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        rows = list(pool.map(lambda job: one_run(args, *job), jobs))
    summary = summarize(args, repos, rows)
    OUT.mkdir(exist_ok=True)
    base = OUT / f"eval-review-{args.runtime}"
    base.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n")
    base.with_suffix(".md").write_text(markdown(summary))
    print(markdown(summary).split("\n| Repo |")[0].rstrip())
    print(f"\nWrote {base.with_suffix('.json')} and {base.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
