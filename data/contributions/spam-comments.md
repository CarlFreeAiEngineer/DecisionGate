# Spam-like marketing comments

[spam-comments.jsonl](spam-comments.jsonl) adds 80 original synthetic examples: 48 training, 16 validation, and 16 calibration records, each partition evenly balanced between YES and NO. These are proposed labels for review, not proven facts about a writer's intentions. The canonical editable source is the JSONL file.

Clear positives include sales pitches, off-platform picture bait, cryptocurrency rewards, referral offers, paid services, and requests to contact an advertiser. Clear negatives include customer questions, personal enthusiasm, spam complaints, scam warnings, quoted advertisements being discussed rather than endorsed, and requested support information. A link, email address, product name, or the word “spam” alone does not determine the answer. The task concerns the comment's apparent promotional purpose, not certainty that its author is a spammer.

Twenty-four records form twelve policy pairs. Each pair has identical content and question but different explicit criteria: one flags invitations to private contact even without a commercial offer; the other requires advertising, commercial offers, or reward bait. The labels change accordingly. Both members share a group and remain in the same split. Borderline personal invitations are not assigned a supposedly universal label without criteria.

The user's Java examples inspired several training cases. Contact details were replaced with reserved example domains. The spam complaint also appears in the email-address correction under a different question; it retains that training group's ID so it cannot silently cross partitions. The context-free “would love to meet you” example is represented through explicit-policy pairs. Questions and wording vary, but the same synthetic author and related constructions across partitions can make evaluation optimistic. All records are marked `synthetic_unreviewed` and offered under CC0-1.0, subject to the project's generated-data notice.

An independently authored [32-record test](../spam-comments-test.jsonl) is separate. Do not include it in training or choose checkpoints from its results. Public synthetic tests are development checks, not evidence of real-world spam-filter reliability. Missing surrounding conversation, consent, advertising rules, and platform context can change the right decision.

Validate the combined material:

```sh
uv run --locked decisiongator-train validate --extra-data data/expansion-v2.jsonl --extra-data data/contributions/email-address-correction.jsonl --extra-data data/contributions/spam-comments.jsonl
```

For a future training run, pass both correction files and `data/expansion-v2.jsonl` explicitly with `--extra-data`, retain the earlier data, choose a new output directory, and select using validation only. Freeze and calibrate the candidate before evaluating this test and the existing general tests. No training or default-release changes were made when this dataset was added.

The subsequent [combined retraining experiment](../../reports/spam-email.md) used these examples and produced a separate candidate for the local Java example. It improved the user's clear spam cases, but held-out spam accuracy remained weak and the policy pairs remained unresolved.
