# Open training and community contributions

## Public by design

Open weights and open project training data are product requirements. Publish the data used for each project's fine-tuning run, its processing recipe, configuration, code revision, and resulting weights. Hugging Face is the likely model and dataset distribution host; no account, repository name, or publication has been established yet.

Each release must be reproducible from public inputs without privileged access to a private teacher, private labels, or an undisclosed dataset. If a hosted teacher helps create examples, release those examples and permitted labels so reproducing training does not require making the original calls again. Record generation provenance and cost separately.

This promise covers the project's training stages. Pretrained foundations may have incomplete or nonredistributable upstream corpora. Record that limitation plainly in the model card and prefer foundations with stronger provenance. Never describe open fine-tuning data as fully open pretraining history.

## Dataset record

Use a versioned, documented JSONL schema with a stable example identifier, content, question, optional yes/no criteria, label, label type, source/task family, provenance, license identifier, annotation rationale, review status, and split. The rationale is for human review and is not automatically an input to the model. Synthetic records also identify the generator and generation recipe where distributable. Separate contributor identity from the text needed for training.

Keep explicit revision history for corrections, withdrawals, and duplicate merges. Dataset releases have immutable versions, manifests, counts, hashes, and license notices. Model manifests identify the exact dataset version. Do not silently change labels beneath a published model's training record.

Accept only material contributors have the right to publish and allow others to use for training and redistribution. Use compatible explicit dataset terms; code licenses do not automatically settle data rights. Do not solicit real private tickets, email credentials, or personal information. Prefer original examples, licensed public material, or properly reviewed anonymized cases. Reject content whose rights or privacy cannot be resolved.

## Contribution workflow

1. A contributor submits an example, a correction, a documented failure, or a reproducible training experiment through the project's repository workflow.
2. Automated validation checks schema, allowed values, lengths, duplicate identifiers, near-duplicates across splits, and required provenance. Flag suspicious or sensitive material for review rather than claiming automated checks prove safety or ownership.
3. Reviewers assess the rights statement, question clarity, criteria, label, and rationale. Disagreements remain visible and receive adjudication or explicit uncertain status; contributor assertions are not automatically ground truth.
4. Accepted examples enter a staged dataset revision. Maintainers assign splits by related source and task family before training, preserving separation between training and evaluation.
5. A candidate run records its recipe and results. Improvements must pass regression, calibration, portability, and footprint checks before becoming an official release.

Contributors can help without training anything. Corrections and difficult counterexamples are first-class contributions. Contributions that improve one family but degrade another must report both. Do not automatically merge submitted weights or execute contributed training code as part of dataset review.

## Community training

Publish a local `uv` workflow and a Colab-compatible recipe backed by the same configuration and data loader. Offer a small smoke-run configuration to verify setup, alongside the full release recipe. Record actual hardware needs and approximate runtime once measured. Resume from checkpoints and keep experiment outputs tied to code and data hashes.

### Clone, correct, retrain, contribute

This is a required user workflow, not an internal maintainer convenience. Someone who encounters a wrong answer must be able to build a local variant without maintainer approval or a hosted training service. Public contribution is optional. Initial dependency and checkpoint downloads may require a connection; after all assets are available, local training must not require a service account or hidden remote step.

1. Clone the repository and install the locked training environment with `uv`. Fetch an explicitly versioned starting checkpoint and dataset using documented commands and verify their hashes.
2. Record a failure with the content, question, criteria if used, expected label, and explanation. Record the failing model version and observed probability separately from the training inputs. Offer a small example file to copy and edit.
3. Add examples either to a public contribution file or a local data directory excluded from Git by default. Load local additions explicitly through configuration; never automatically upload them or include them in public release data. A private-data variant is a local derivative, not a reproducible official release from public inputs.
4. Run validation before training. Report malformed records, conflicting labels, duplicate examples, and overlap with evaluation data in language a contributor can act on. Preserve source groups when assigning splits.
5. Run a small setup check, then the documented fine-tuning recipe. Support a pinned release checkpoint for local adaptation as well as the pinned foundation and full dataset recipe for reproducing an official release. Mix additions with existing training examples using explicit sampling settings so a few corrections do not overwrite broader behavior. Neither path promises that one example will fix a failure.
6. Compare the candidate with its starting model on the same untouched evaluation data. Report gains, regressions, and probability quality. A corrected example used in training may confirm that the model learned that example, but cannot establish generalization; use independently authored related cases for that assessment.
7. Export an independently versioned bundle loadable by the normal C and Python interfaces. Preserve the original bundle so the application can switch back. Record local data hashes and parent checkpoint without publishing private content.
8. Optionally submit a Git pull request containing publishable examples or label corrections and their provenance. No model weights, paid account, GPU, or completed training run is required for a data contribution. Maintainers review and integrate accepted data into the shared dataset and evaluate a candidate release.

Implement these steps as documented commands using one shared pipeline, with a complete worked example from a wrong answer to an exported local bundle. Do not require editing training internals or a notebook to add a dataset. Command names remain provisional until implementation exists. Include setup, data validation, training, comparison, and export in the release acceptance check on a clean checkout.

Keep small, reviewable contribution files in Git; store large versioned dataset releases and checkpoints outside ordinary Git history with manifests in the repository. CI for data-only pull requests should perform inexpensive validation; full retraining is a separate explicit job. Accepted data does not immediately change shipped weights: improvements arrive in a tested model release or in the contributor's own local build.

Contributors may submit model candidates with a model card, base-model revision, dataset manifest, configuration, seed, dependency lock, hardware details, metrics, and reproducible commands. Official releases should be rebuilt or independently reproduced rather than trusting a claimed score. Initial collaboration is reviewed shared data and reproducible runs, not a distributed training or federated-learning system.

## Open evaluation without misleading scores

Publish evaluation protocols and versioned benchmarks. Public benchmark labels make accidental or deliberate overfitting possible: training recipes must exclude evaluation partitions, and reports must disclose exposure. Add fresh independently reviewed evaluation rounds for release candidates; publish those rounds with the release evidence after evaluation. Keep historical benchmark results comparable and identify when a former evaluation example later enters training.

Open contributions do not remove the need for train/validation/calibration/test separation. A published test set remains a test set only for runs that have not trained or tuned on it. Report contaminated results as such and use a fresh split for new capability claims.
