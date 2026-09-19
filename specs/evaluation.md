# Evaluation and milestones

## What success means

The component must answer new yes/no questions usefully, expose probabilities whose quality has been measured, and run offline on supported CPUs. A working library wrapper around an unreliable model is not completion.

Before training, version an evaluation protocol and a human-reviewed test collection. Define decision families, intended population, error costs, annotation rules, and missing-information policy. Keep final test labels out of model selection and calibration. Report sample counts and uncertainty intervals; a handful of examples cannot establish a 99% reliability claim.

## Required measurements

- Decision quality: balanced accuracy, precision and recall for yes, false-positive and false-negative rates, and results for each task family. Include a majority-class baseline and an existing pretrained model baseline.
- Probability quality: Brier score, log loss, and reliability plots, with bin definitions and sample counts. Report aggregate and domain-specific results; a good aggregate can hide poor behavior on an important subset.
- Generalization: unseen documents, unseen question families, unseen domains, paraphrases, and changed criteria. Keep these results separate from familiar-task results.
- Selective operation: accuracy/error rate versus the fraction of inputs acted on when callers defer uncertain cases. Set thresholds on validation data, not the final test. Report coverage so a model cannot appear useful merely by declining almost everything.
- Robustness: missing and conflicting evidence, negation, quoted requests, embedded instructions, irrelevant text, long inputs, repeated calls, and complementary questions.
- Deployment fidelity: training-runtime versus exported-runtime outputs; floating-point versus quantized outputs; calibration before and after deployment; decisions that cross application thresholds.
- System behavior: warm p50/p95 latency, cold load time, tokenizer time, throughput, installed size, peak memory, offline operation, and resource cleanup.

For timing, record hardware, OS, runtime, thread count, power mode, precision, input lengths, batch size, warm-up procedure, and repetition count. Measure short and maximum-length inputs separately. Compare models under the same conditions; do not import Jev's hosted latency as a local benchmark.

## Initial engineering targets

These are proposed experiment budgets, not measured capabilities or public guarantees:

- A compact-model search around 30–150 million total parameters.
- A complete installed bundle at or below 250 MB, including tokenizer and native dependencies.
- Peak inference memory at or below 1 GB for a single short request.
- Warm p95 at or below 200 ms on the development M1 Pro CPU for one request of 256 total tokens, using four inference threads and at least 1,000 measured calls after warm-up.

Measure these first, then retain or revise them with a recorded reason. Establish a separate practical CPU benchmark on Windows and Linux before claiming support or cross-platform speed. Context length must be selected through capability and memory tests; do not imply Jev's context size is inherited.

Accuracy gates require the evaluation corpus and intended uses. Set numeric minimums per family before tuning, including maximum tolerated false-positive rates and minimum automated coverage. A release is blocked while these gates are unspecified, or if aggregate gains conceal failure on a required family.

## Milestones

1. **Specify the task.** Use the transcript-derived families in [behavior.md](behavior.md), annotate and split evaluation data, document licenses, and freeze initial success criteria. Deliver a public dataset schema, contribution process, dataset manifest, and evaluation protocol.
2. **Measure pretrained baselines.** Run a compact inference model locally, profile memory and latency, and test a small export. Deliver a comparison report and a justified architecture choice.
3. **Fine-tune locally.** Complete a resumable pilot on the M1 Pro; use Colab only if measured constraints justify it. Deliver reproducible training commands, checkpoints, and validation results.
4. **Calibrate and compress.** Compare calibration and quantization variants on the appropriate held-out sets. Deliver a chosen model bundle and a locked configuration before final testing.
5. **Embed it.** Implement the native interface and Python binding, test without network or Python dependencies in the native host, and verify each target OS. Deliver a minimal host application and platform packages.
6. **Publish evidence and release.** Run the locked final evaluation, satisfy previously defined gates, and ship weights, project training data, training recipes, model documentation, notices, hashes, supported-platform details, and reproducible measurements. Follow [open training](open-training.md) for evaluation exposure and contribution handling. Update README claims to match the evidence.

If the compact candidates cannot meet useful accuracy on unseen questions, record the failure. Compare a larger model or propose a narrower supported scope explicitly. Do not quietly replace the general question-driven goal with a fixed-label classifier.
