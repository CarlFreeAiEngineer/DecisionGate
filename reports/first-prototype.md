# First Mac prototype: working component, insufficient judgment

Measured on 2026-09-17: Apple M1 Pro, 32 GiB unified memory, macOS 26.6.2. The complete local bundle is `released/macos-arm64/`. It contains a real fine-tuned transformer, not handwritten keyword rules, and runs through a Rust C-compatible interface with no server or Python dependency in the native host.

## What works

- Training completed on the local MPS GPU: 224 training examples, 12 epochs in about 40 seconds after model loading, with validation and checkpoint writes included in the loop timing. Downloads/setup are excluded.
- Validation selected epoch 11, with 48/56 correct. A separate 32-example calibration partition set temperature to 1.05925.
- Rust's four unit tests and 107 native interface checks passed, including errors, Unicode, criteria, repeated loading, metadata, and concurrent calls.
- Native predictions matched the PyTorch checkpoint within 0.00000205 across 366 cases, including all seed records and two extra text fixtures.
- A C host compiled against a relocated bundle and ran with all networking denied and development tools absent from its path. It exited cleanly.
- Training data, training/export/calibration code, native source, Python binding, C example, dependency locks, and editable correction example are present locally. Nothing has been published or uploaded.

## What does not work well enough

The frozen model answered **32/52 synthetic test cases correctly (61.5%)**, against a 50% majority baseline. Permission questions were 5/10; timeline questions were 7/10. Tiny family counts are not reliable estimates of deployment performance.

Probability quality also failed to beat a constant 0.5 prediction: test Brier score was **0.2683** versus **0.25**, and log loss was **0.7607** versus **0.6931**. Lower is better for both. Calibration on a small synthetic partition does not solve unfamiliar questions.

The C demonstration exposes a clear mistake: “Please cancel my subscription before the next renewal” receives only **0.1146** for whether cancellation is requested. The Python refund request example also receives a low score. These failures are deliberately visible. A valid probability and working interface do not mean that the model understood the request.

All 364 seed records are synthetic and unreviewed. Related wording and policy constructions cross splits, although exact inputs and source-group IDs do not. There is no independent human-reviewed benchmark, no demonstrated broad generalization, and no security-detection claim. We did not tune on the final test results. The broader product release gates remain unmet.

## Measured footprint and speed

| Measurement | Result |
| --- | ---: |
| Rust library | 3,662,336 bytes |
| Full-precision model | 133,692,193 bytes |
| Complete bundle, including runtime and notices | 195,860,137 bytes |
| C process peak resident memory, short request | 350,191,616 bytes |
| Native load time in parity process | 1.84 seconds |
| Warm CPU p50, 256 total tokens | 41.48 ms |
| Warm CPU p95, 256 total tokens | 43.99 ms |

Timing used four inference threads, batch size one, 20 warm-up calls, and 1,000 measured calls. It includes native tokenization. The timing input was a repeated-word 256-token fixture, not an accuracy example. The benchmark process also loaded a PyTorch reference; its memory is reported separately in the raw parity report and must not be confused with the C-only memory figure. Cold-load timing is one observation, not a statistical benchmark. Power mode was not controlled, and no other Mac or minimum OS version has been qualified.

## Integration limits

Only the arm64 Mac bundle is built. Windows x64 and Linux x64 remain planned. Inputs are limited to 256 total tokens with explicit overlength errors. Library calls serialize per model handle; independent handles have separate sessions. This prototype requires the library to remain loaded until process exit; release model handles normally, but do not `dlclose` the library. Join inference threads before exiting and do not call it from exit callbacks.

Testing found an ONNX Runtime macOS teardown crash after otherwise successful inference. The native adapter now releases the runtime environment at process exit, following the lifecycle fix in newer `ort` versions; source comments link the upstream references. Testing also caught an absolute build-directory library identity; packaging now sets `@rpath/libdecisionmodel.dylib`, signs the staged library, and verifies a relocated C host.

No quantization was necessary to fit this prototype's size budget. Next priority is better data and a measured NLI baseline or other question-aware foundation, followed by fresh independent evaluation. Runtime speed is already adequate for further experiments; judgment quality is the blocker.

## Reproduce and inspect

The optional correction workflow was also exercised: add one cancellation example, fine-tune the saved checkpoint for one epoch while retaining the original training data, resume the completed run, export, calibrate, and load a separate native bundle. The example remained incorrectly classified (yes probability 0.1146 to 0.1596), and the same development test score declined to 31/52. We kept the original bundle. [Correction scores](correction-example.json), [training history](correction-training-history.json), and [test comparison](correction-test.json) make that regression visible. This one-epoch check is not a claim that larger reviewed contributions cannot help.

Follow [the first-version recipe](../specs/first-version.md). Raw evidence:

- [Training configuration](pilot-training-config.json) and [epoch history](pilot-training-history.json).
- [Initial random-head validation](pilot-initial-validation.json), which is a setup baseline, not an NLI benchmark.
- [Calibration results](pilot-calibration.json) and [frozen test predictions](pilot-test.json).
- [Native/PyTorch parity and timing](pilot-parity.json).
- [Relocated, network-denied C test](pilot-package.json).

The 52-example test set is now exposed development evidence. Any future tuning informed by its failures needs fresh held-out evaluation before making stronger accuracy claims.
