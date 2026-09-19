# Accuracy improvement: version 2

The new frozen model improves the fresh synthetic test from **42/80 (52.5%) to 59/80 (73.75%)**. It remains experimental: 21 fresh-test errors, weak negation and rule interpretation, and no independent human-reviewed accuracy evidence.

## Compared on the same examples

| Measurement | Original | Version 2 |
| --- | ---: | ---: |
| Fresh test, 80 cases | 42/80 (52.5%) | 59/80 (73.75%) |
| Fresh-test Brier score; lower is better | 0.2946 | 0.1810 |
| Fresh-test log loss; lower is better | 0.8054 | 0.5516 |
| Original test, 52 cases | 32/52 (61.5%) | 38/52 (73.1%) |
| Shared validation, 96 cases | 69/96 (71.9%) | 77/96 (80.2%) |
| Fresh contrasting question pairs, both answers correct | 5/20 | 9/20 |

A constant 0.5 prediction has Brier 0.25 and log loss 0.6931. The new model beats that probability baseline on the fresh set, unlike the original. Temperature scaling still does not establish calibrated probabilities on real application data.

On the fresh test, the new model fixes 30 original mistakes but introduces 13 new ones. Negation falls from 3/5 to 2/5; quoted-instruction cases fall from 4/5 to 3/5. Eligibility is only 3/7, and numerical criteria 7/11. These tiny counts cannot establish broad domain accuracy. See [per-family and paired results](v2-comparison.json).

The original gets **212/224 (94.6%) on its own training examples**. The selected new checkpoint gets **362/404 (89.6%) on its larger training set**. Those training percentages are not directly comparable because the collections differ. High training accuracy alone did not make the original generalize.

## What changed

We replaced the 33.4-million-parameter generic language foundation with an 82.1-million-parameter foundation already trained on natural language inference: [cross-encoder/nli-MiniLM2-L6-H768](https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768), pinned to revision `b95119ce93d3e065de6214e38cd4a97b0f2f2c6d`. It was adapted to the project's binary labels; there are still no generated tokens or remote inference calls.

We added 240 original synthetic records, including 180 training examples. Each added passage has contrasting questions requiring different answers. The resulting training/validation/calibration counts are 404/96/52. The existing 52 test examples and a separately authored fresh 80-example test remain excluded from training. The public seed and expansion together contain 604 examples; the fresh test brings the complete collection to 684, excluding the separate worked correction.

The new model reads content first and question/criteria second, recorded as template version 2. The Rust library supports both versions; the public `evaluate(content, question, criteria=None)` interface is unchanged. The new foundation and derivative weights use Apache-2.0 terms; project source remains MIT, original example data CC0 as documented.

## How we selected it

We wrote [the comparison plan](../specs/accuracy-v2.md) before opening fresh-test results. A separate authoring task created the fresh test without inspecting prior scores or training collections beyond the schema; another created the expansion without accessing that test. Exact duplicate/group checks passed, with no cross-collection content similarity above 0.85 under the recorded character-based screen. This is still same-model synthetic authorship, not independent human evaluation.

We compared all candidates on the same 96 validation examples. Best checkpoint means lowest validation log loss:

| Candidate | Validation accuracy | Log loss |
| --- | ---: | ---: |
| Original released model | 71.9% | 0.560 |
| Original foundation, expanded data, best epoch 9 | 72.9% | 0.622 |
| NLI foundation, original data, best epoch 8 | 80.2% | 0.474 |
| NLI foundation, expanded data, best epoch 7 | 80.2% | 0.423 |

Values are rounded; original released probabilities include their existing calibration, while candidate selection scores are uncalibrated. A direct three-way NLI heuristic baseline on the original 56 validation examples scored 60.7%; fine-tuning the yes/no task matters. We did not equate NLI's neutral class with a definite no or discard it when reporting that baseline.

The selected full-precision checkpoint was temperature-scaled on the 52 calibration examples (temperature 1.13501), then frozen in [the selection record](v2-selection.json) before fresh testing. Fresh-test gains exceeded the predeclared five-percentage-point improvement gate and improved Brier score. Both explicit refund and cancellation smoke cases are now correctly above 0.5; the invoice request remains below it.

The expanded NLI run took approximately 90 seconds for ten epochs, including training-set/validation measurements and checkpoint writes, after setup and loading. It used the local M1 Pro MPS GPU, batch size 16, learning rate 0.00001, seed 42. No Colab or paid teacher was used.

## Size and compression tradeoff

The complete bundle is **393,640,057 bytes (about 394 MB)**, compared with about 196 MB before. The model itself is 328,609,581 bytes; the native library is still 3,662,336 bytes. A relocated C process used peak resident memory of 892,436,480 bytes in the short-request test. The bundle exceeds our initial 250 MB experiment budget; that is an explicit tradeoff for the measured accuracy gain, not a claim that the original budget was met.

Two int8 compression variants of the original-data NLI candidate were rejected before fresh testing. Although one preserved aggregate validation accuracy, individual probability changes exceeded 0.65; the other reduced accuracy and changed a probability by over 0.60. We retained full precision. Compression needs more work before shipping it as equivalent behavior.

Native verification includes six Rust tests, 107 C/Python interface checks, and a relocated C host running with networking denied. Floating-point parity and the 1,000-call benchmark are recorded in [the native report](v2-native-parity.json); [the package report](v2-native-package.json) measures the C process rather than a process also containing PyTorch.

On the M1 Pro, 1,000 warm CPU calls at 256 total tokens used four inference threads and 20 warm-up calls: p50 was 68.4 ms and p95 85.9 ms. Native predictions matched PyTorch within 0.00000803 over 686 cases. Power mode and other system activity were not controlled, so these are local experiment measurements rather than service guarantees.

## Reproduce and inspect

Follow [the version 2 recipe](../specs/accuracy-v2.md). All completed trials have configurations and epoch histories in `reports/v2-*-config.json` and `reports/v2-*-history.json`. Compare [original fresh-test predictions](v2-original-fresh-test.json), [candidate fresh-test predictions](v2-candidate-fresh-test.json), [old-test results](v2-candidate-old-test.json), [training results](v2-candidate-training.json), and [smoke decisions](v2-smoke-decisions.json).

The old local bundle is preserved at `models/macos-arm64-v1/`. Neither version has been uploaded or published. The fresh test is now exposed development evidence; future tuning informed by these failures needs another fresh test before stronger accuracy claims.
