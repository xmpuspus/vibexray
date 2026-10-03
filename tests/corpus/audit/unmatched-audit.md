# Corrected dev precision is 66.7 percent (84 of 126), up from 44.4 percent

Of the 70 unmatched findings, 36 are real problems. The formula counts 28 of them: 5 labeler_missed and 23 duplicate. So 56 + 28 = 84 of 126 findings count as correct.

I read the code at every finding line. I changed no label and no rule. The per-finding verdicts are in `unmatched-audit.json`.

## Verdict counts show that 34 of the 70 unmatched findings are false alarms

| Verdict | Count |
|---|---|
| rule_wrong | 34 |
| duplicate | 23 |
| wrong_category | 8 |
| labeler_missed | 5 |
| Total | 70 |

## Three rules cause 14 of the 34 false alarms

| rule_id | rule_wrong | duplicate | labeler_missed | wrong_category |
|---|---|---|---|---|
| xss-html-injection | 7 | 0 | 0 | 0 |
| ai-no-eval-files | 4 | 0 | 0 | 0 |
| auth-disabled-flag | 3 | 7 | 0 | 0 |
| hardcoded-price-or-limit | 2 | 3 | 1 | 6 |
| admin-route-no-guard | 2 | 2 | 0 | 0 |
| api-route-no-auth | 2 | 1 | 0 | 0 |
| preview-or-tunnel-url | 2 | 0 | 0 | 0 |
| prompt-limit-not-in-code | 2 | 0 | 0 | 0 |
| rls-enabled-no-policy-or-grants | 2 | 0 | 0 | 0 |
| token-in-localstorage | 2 | 0 | 0 | 0 |
| fake-delay-loader | 1 | 0 | 1 | 0 |
| mock-array-literal | 1 | 0 | 0 | 0 |
| placeholder-media | 1 | 0 | 0 | 0 |
| rpc-or-function-open | 1 | 0 | 0 | 0 |
| settimeout-success | 1 | 0 | 0 | 0 |
| tool-returns-canned | 1 | 0 | 0 | 0 |
| stripe-id-literal | 0 | 1 | 2 | 0 |
| ai-cost-controls | 0 | 0 | 1 | 0 |
| tool-action-no-approval | 0 | 3 | 0 | 0 |
| mock-path-segment | 0 | 2 | 0 | 0 |
| todo-handler-body | 0 | 0 | 0 | 2 |
| placeholder-identity | 0 | 1 | 0 | 0 |
| policy-using-true | 0 | 1 | 0 | 0 |
| tool-number-unbounded | 0 | 1 | 0 | 0 |
| user-input-in-system-prompt | 0 | 1 | 0 | 0 |

The main false-alarm patterns are these:

- xss-html-injection fires on every `innerHTML`. The 7 hits put in constants, icons, escaped text, a site-owner attribute, or a server sequence number.
- ai-no-eval-files reports a missing eval suite as `ai_no_human_review`. No label category covers missing evals.
- auth-disabled-flag fires on `verify_jwt = false` for public forms (donation, contact, newsletter).
- hardcoded-price-or-limit fires on prices inside sample-data arrays and on `cost: 0` counters.
- token-in-localstorage fires on a random chat session id, not a login token.
- rls-enabled-no-policy-or-grants fires on a table that the app reads only through SECURITY DEFINER functions, on purpose.

## The labelers missed 5 real problems

- vocal-note-keeper-ai `src/lib/whisperWeb.ts` 176: the default transcription provider waits 2 s on a timer and returns a fixed mock transcript.
- yana-contabila `stripe-webhook/index.ts` 379: the webhook types in a price ID and a 19900 cent cutoff. Four functions hold the same ID.
- yana-contabila `stripe-webhook/index.ts` 525: the webhook holds a second copy of the price-to-credits map from `AICreditsPurchase.tsx`.
- my-wealth-view `transactions.tsx` 74: a business limit of 15. The comment says the backend keeps its own copy in sync by hand.
- SliceIQ `react-loop.ts` 172: the model call sets no `max_tokens`. Impact is low, because a 10-turn loop cap exists.

## The duplicate count comes from my reading of the labels, not from a matched-findings list

I had no list of the 56 matched findings. So I called a finding `duplicate` when the label file marks the same problem. In most cases the label anchors in another file or at other lines. For example, the rule flags a tool schema in `react-loop.ts`, but the label sits on the tool body in `tools.ts`.

Two groups in the 23 duplicates need care:

- Four yana `verify_jwt = false` findings (lines 7, 10, 13, 16) are real auth gaps. The label puts them under `security_other` at `config.toml` 9-200. The same label file uses `auth_gap` for this pattern. If you do not count these four, precision is 80 of 126 (63.5 percent).
- Four findings repeat another unmatched finding on the same Stripe map (stripe-webhook lines 525 to 527). They are correct, but they count one problem more than once.

## Wrong-category findings do not count, but they point at real problems

The 8 wrong_category findings are real. Six are prices inside labeled sample data (`mock_data`). Two are TODO tool stubs that the labels mark as `ai_fake_tool`. If you count them, precision is 92 of 126 (73.0 percent).
