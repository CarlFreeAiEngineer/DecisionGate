# v4 training and test data

Sixteen task families, each in its own file, written on 2026-09-19 by AI sub-agents following [AUTHORING.md](AUTHORING.md). Every record is `synthetic_unreviewed` and intended to be CC0-1.0, like the earlier seed data. No customer records or scraped text were used.

| File | Family | Records | Splits (train / validation / calibration) |
| --- | --- | ---: | --- |
| `appointment_intent.jsonl` | request, reschedule, cancel, confirm, decline an appointment | 220 | 186 / 22 / 12 |
| `cancellation_intent.jsonl` | cancel, pause, downgrade a service or order | 220 | 186 / 22 / 12 |
| `refund_intent.jsonl` | money back versus replacement, credit, complaint, policy question | 220 | 186 / 22 / 12 |
| `routing.jsonl` | billing, technical, shipping, sales, account access, feedback | 220 | 186 / 22 / 12 |
| `urgency.jsonl` | urgency under stated criteria, not tone | 220 | 186 / 22 / 12 |
| `everyday.jsonl` | notes, chats, lists, short stories | 220 | 186 / 22 / 12 |
| `permissions.jsonl` | rule set plus case: may X do Y | 220 | 186 / 22 / 12 |
| `eligibility.jsonl` | either/or, both/and, unless, boundaries, exclusions | 220 | 186 / 22 / 12 |
| `numeric_criteria.jsonl` | limits, units, sums, counts, boundary values | 220 | 186 / 22 / 12 |
| `events_timeline.jsonl` | before/after, already/not yet, deadlines, plans that did not happen | 220 | 186 / 22 / 12 |
| `negation.jsonl` | neither/nor, not except, double negation, all but one | 220 | 186 / 22 / 12 |
| `quoted_instructions.jsonl` | drafts marked wrong, reported speech, embedded commands | 220 | 186 / 22 / 12 |
| `duplicate_reports.jsonl` | do two of several reports describe the same event | 220 | 186 / 22 / 12 |
| `evidence_presence.jsonl` | mentioned versus happened, hedged, promised versus done | 220 | 186 / 22 / 12 |
| `spam_promotion.jsonl` | promotional spam under explicit criteria | 224 | 190 / 22 / 12 |
| `email_screening.jsonl` | observable scam indicators in email text | 222 | 188 / 22 / 12 |

Every group holds one yes and one no record; about two thirds of groups share one content across two questions, the rest share one question across two contents that differ in the decisive detail. Splits are assigned by group number, so no group crosses a split.

## Held-out test

`test-1.jsonl` to `test-4.jsonl` hold 480 records, 30 per family, written by four separate agents that saw only the authoring brief, not the training files. Group numbers 901 to 915 keep them apart from training groups. They are the project's primary accuracy measurement from version 0.4.0 on. They were used once to compare foundations and once to score the release candidate; treat them as seen for the next release and write a fresh test before claiming a new accuracy figure.

## Audit

A blind audit on 2026-09-19 re-labelled a fixed-seed random sample of 232 records (12 per training file, 10 per test file) and agreed with all 232 stored labels; five were noted as arguable. Two weaknesses were recorded for future authors: criteria text sometimes echoes the specific case instead of stating a general policy (a model can shortcut by matching words), and some families reuse a fixed content shape (for example a two-sentence policy-then-case form in eligibility). Neither was corrected before training.

## Loading

Pass each file with `--extra-data` (see the reproduce section of [the version 0.4.0 report](../../reports/accuracy-v4.md)). `uv run decisiongator-train validate --data FILE` checks any file alone; adding `--extra-data` for the rest checks cross-file duplicates.
