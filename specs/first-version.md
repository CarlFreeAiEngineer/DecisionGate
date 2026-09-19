# First local prototype

This is the historical version 1 recipe. The current default bundle uses [the version 2 accuracy recipe](accuracy-v2.md); both remain reproducible.

This is an experimental Mac build, not the general-purpose release described by the product goals. It implements the complete path from editable examples to a trained model to an in-process Rust library. Production accuracy gates in `evaluation.md` still apply to a public supported release.

The API and dataset field formerly called `state` is now `content`. Existing model weights remain compatible because the input text and encoding are unchanged. Historical data hashes are preserved in reports with a mapping in `reports/content-field-rename.json`. Start a new run when training against the renamed files; the old optimizer-resume configurations correctly reject changed dataset hashes. Existing saved model checkpoints still work with `--start`.

## Concrete recipe

Use MiniLM-L12-H384-uncased, 33,360,770 parameters including a two-output classification head, at the pinned revision in `training/pipeline.py`. Read the question and optional criteria as the first text and the evidence as the second. Fine-tune all weights with binary cross-entropy (two-class cross-entropy), AdamW, learning rate 0.00003, batch size 16, seed 42, and 12 epochs. Select the checkpoint with lowest validation log loss. The Mac uses PyTorch MPS; inference uses ONNX Runtime CPU with four threads.

The data consists of 364 original synthetic examples: 224 training, 56 validation, 32 calibration, and 52 test. Every label is explicitly unreviewed. Several task families and wording patterns share the same author, so even held-out results can be optimistic. The two unseen test families are permission and event ordering. Phishing and jailbreak detection are not covered by this seed.

Export full-precision ONNX before attempting quantization. Fit one temperature on the separate calibration split, then freeze the bundle before running the test partition. The small synthetic calibration set cannot establish real-world probability reliability. Preserve failed and earlier experiments separately.

## Train and export

From the project root, with `uv` available:

```text
uv sync --locked
uv run --locked decisiongate-train validate
uv run --locked decisiongate-train train --output runs/my-first-run --epochs 12
uv run --locked decisiongate-train export --checkpoint runs/my-first-run/best --output models/my-first-model --model-id my-first-model
uv run --locked decisiongate-train calibrate --bundle models/my-first-model --output reports/my-calibration.json
uv run --locked decisiongate-train evaluate --bundle models/my-first-model --split test --output reports/my-test.json
```

The initial run downloads the pinned upstream checkpoint and dependencies; afterward cached assets can be used offline. Set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` to require cached inputs. There is no hosted teacher or training API. `--device cpu`, `--device mps`, and `--device cuda` explicitly select the backend; CUDA is the Colab alternative. No Colab run has been tested yet.

For a short setup check, use `--epochs 1` and a separate output directory. Resume an interrupted run by repeating the same training command with `--resume`. Checkpoints are saved after complete epochs; an interrupted epoch is rerun. Resume loads the locally generated optimizer checkpoint: never pass an untrusted downloaded `resume.pt` file. Seeds and pinned inputs make runs traceable, but identical floating-point results across devices are not guaranteed.

## Add a correction

Copy a record from `data/plain-questions.jsonl` into a new JSONL file. Give it a new ID and group, edit the evidence/question/answer/rationale, and set `split` to `train`. Keep related records in that group and split. Use `data/local/my-examples.jsonl` for private data; that directory is ignored by Git. Publishable contributions can be separate files under `data/contributions/`.

```text
uv run --locked decisiongate-train validate --extra-data data/local/my-examples.jsonl
uv run --locked decisiongate-train train --start runs/my-first-run/best --extra-data data/local/my-examples.jsonl --output runs/my-correction --epochs 12
```

`--start` fine-tunes a saved Transformers checkpoint. For reproducing the foundation recipe, omit it. Each epoch includes all original training examples and the explicitly supplied additions once, shuffled together. No file is uploaded. Existing output directories are protected unless resuming. Export to a new model ID and directory, calibrate, and evaluate both variants against the same untouched test set. Compare the JSON reports, especially per-family regressions. Do not count the correction used in training as independent evidence that the model generalized.

A complete worked correction is included in `data/contributions/example-correction.jsonl`: the initial model misunderstands the cancellation request in the C smoke example. We ran `train --start runs/pilot-v2/best --extra-data data/contributions/example-correction.jsonl --output runs/correction-smoke --epochs 1`, checked `--resume`, exported to `models/correction-smoke`, calibrated it, and assembled `models/native-correction-smoke`. Both bundles load through the same interface. The correction's estimated yes probability moved from 0.1146 to 0.1596, still wrong at 0.5, while test accuracy fell from 32/52 to 31/52. The original bundle was retained. This proves the editable-data workflow, not a successful model improvement; see [the recorded comparison](../reports/correction-example.json).

Validation currently rejects malformed fields, exact duplicate inputs/IDs, and groups crossing splits. It does not yet automate semantic near-duplicate detection or rights/privacy review; those remain review obligations. The prototype permits explicitly marked unreviewed synthetic data for development, unlike a reviewed public release.

## Build the Mac library

The repository uses the portable Rust layout in [development.md](development.md). Rust 1.98.1 lives under `tools/rust/`, with a project-local Cargo cache. `uv run code/setup.py` installs the pinned toolchain through rustup using project-local directories; `--rust-from PATH` copies an existing matching toolchain as ordinary files. The host still needs its linker and SDK. See [native build instructions](../code/README.md) for Mac, Linux, and Windows prerequisites.

```text
uv run code/build.py --model models/my-first-model --output released/my-mac-build
uv run tests/native_check.py --bundle released/my-mac-build
uv run --locked python -m tests.parity --bundle released/my-mac-build --checkpoint runs/my-first-run/best --data data/seed.jsonl --data data/plain-questions.jsonl --output reports/my-parity.json
```

The shared build helper now supports macOS arm64, Linux x64/glibc, and Windows x64/MSVC. It preserves existing output directories, runs Rust and native integration tests, and assembles a complete bundle. Consult [the release inventory](../released/README.md) for tested artifacts. The native component needs neither Python nor Rust on the application user's machine. The optional Python wrapper uses only the standard library; PyTorch and other training packages belong to the development dependency group.

Compile the C example on macOS:

```text
clang examples/c_smoke.c -I released/my-mac-build -L released/my-mac-build -ldecisiongate -Wl,-rpath,@executable_path/../released/my-mac-build -o examples/c_smoke
./examples/c_smoke released/my-mac-build
```

The library, runtime, model, tokenizer, and manifest are ordinary adjacent files. Model and runtime hashes are checked when loading. The runtime remains loaded for the host process's lifetime; model handles release their inference sessions. This prototype must not be unloaded with `dlclose`: keep the library loaded until process exit, join inference threads before exit, and do not call it from exit callbacks. See the header for the complete lifecycle contract.

## Remaining release work

The [version 2 work](accuracy-v2.md) expanded the data, measured and fine-tuned an NLI starting point, improved fresh-test accuracy, and evaluated quantization. Toolchain setup and platform packaging are implemented separately from this historical training recipe. Remaining release work includes independent human-reviewed examples, broader evaluation, numeric product accuracy gates, representative probability calibration, automated near-duplicate review, final licensing review, and public distribution. The experimental packages do not waive those quality requirements.
