# Auditors judge each unmatched finding from the code alone

This file fixed the sealed audit on 2026-10-04, before the sealed run. An auditor gets this text and a list of findings. The list holds only findings that matched no label.

## The auditor sees the code and the finding, never the labels

- The auditor did not build vibexray. The auditor never sees vibexray's code, its skill, or the label files.
- Each finding gives a repo, a file, a line span, a category, a snippet, and two short texts.
- The auditor opens the file at those lines. The auditor also reads the code that calls it or that it calls, when the verdict depends on it.

## Each finding gets one of three verdicts

- `real`: the code at those lines has the problem, and the category fits [LABELING.md](../LABELING.md).
- `wrong_category`: the code has a real problem, but another category fits better. Name it in `right_category`.
- `false_alarm`: the code at those lines does not have the problem.

## The reason names the code that decides the verdict

- Write one or two plain sentences, with 12 or more characters.
- Name the file and line that decide the verdict, when they differ from the finding's own lines.
- If the auditor cannot tell, the verdict is `false_alarm`, and the reason says what is unclear.

## The audit file keeps one entry per finding

```json
{"repo": "...", "file": "...", "line": 12, "end_line": 14, "category": "auth_gap",
 "verdict": "real", "reason": "...", "right_category": null}
```

`scripts/audit_precision.py RUNS --audit FILE` counts `real` as right. It counts `wrong_category` and `false_alarm` as wrong.
