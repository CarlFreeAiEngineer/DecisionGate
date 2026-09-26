# Spam-like marketing comment holdout

`spam-comments-test.jsonl` contains 32 original English examples with 16 positive (`label: 1`, yes) and 16 negative (`label: 0`, no) answers. All records have `task_family: spam_marketing_comment`, `split: test`, and `review_status: synthetic_unreviewed`. They are dedicated under CC0-1.0. The schema was taken from `evaluation-v2.jsonl`; no training material, model outputs, selection results, or model evaluations were consulted during authoring.

Twenty-four records have null criteria: 12 clear unsolicited commercial pitches and 12 hard negatives covering discussion, complaints, quoted warnings, moderator reports, and explicitly requested support. Questions vary but consistently ask whether the comment is spam-like marketing or an unsolicited commercial pitch. The commercial examples make unwanted or unrelated placement explicit; the negative examples make their reporting, educational, or support context explicit.

The remaining eight records form four policy pairs. Each pair repeats identical content and question while changing explicit criteria. A broad policy treats unsolicited invitations to private contact from an unrelated public thread as spam-like solicitation; a narrower policy requires an explicit unsolicited commercial pitch. The invitations are expressly noncommercial, so each pair has one yes and one no answer. This distinction tests whether the stated policy controls the decision rather than assuming that every personal invitation is marketing spam.

Keep each `group_id` together in any later split or resampling. The file contains 24 independent one-record groups and four two-record policy groups, for 28 groups total. IDs are stable and unique. Every URL and email uses a reserved `.example` domain.

## Scope and limitations

These are hand-authored synthetic examples, not sampled platform comments or independently reviewed labels. They provide a small diagnostic test, not a representative estimate of production accuracy, spam prevalence, multilingual performance, or performance on deceptive links and obfuscated text. Explicit context and frequent policy cues may make the examples easier than real comments. No claim is made about any platform's actual moderation policy, and personal contact requests without clear context should not inherit these labels automatically.

The matched pairs deliberately differ only in policy and are correlated observations; 32 records are not 32 independent contents. Broad-policy positives measure instruction following on contact solicitation, not a claim that noncommercial invitations are inherently marketing. Source provenance is shared with other assistant-authored data, so separate authoring alone does not establish statistical independence from an eventual training set.

Local validation checked record and label counts, unique IDs, criteria counts, group sizes, identical content and question within each pair, opposite paired labels, and consistent test splits. The repository validator (`uv run --locked decisiongator-train validate --data data/spam-comments-test.jsonl`) also passed with `{"test": 32}`. Policy criteria use the schema’s explicit `yes` and `no` strings. No model was evaluated or retrained. Keep these examples held out from training and threshold selection; any later cross-file duplication check should preserve the held-out role.
