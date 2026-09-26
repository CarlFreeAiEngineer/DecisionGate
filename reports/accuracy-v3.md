# Version 0.3.0: multiple choice, half the size

Version 0.3.0 adds the `choose` and `choose_p` calls, retrains the same foundation on the yes/no data plus 120 new multiple-choice records, and stores the weights as float16. The Mac bundle shrinks from about 394 MB to about 229 MB and the browser bundle from about 345 MB to about 181 MB. Accuracy stays experimental: 62/80 on the fresh yes/no test (up from 59), 14/20 on the held-out multiple-choice test (up from 11 for the previous model used zero-shot), and 35/52 on the older yes/no test (down from 38). No independent human-reviewed benchmark exists yet.

## Compared with version 0.2.0 on the same examples

| Measurement | Version 0.2.0 | Version 0.3.0 |
| --- | ---: | ---: |
| Fresh yes/no test, 80 cases | 59/80 (73.8%) | 62/80 (77.5%) |
| Fresh-test Brier score; lower is better | 0.1810 | 0.1696 |
| Fresh-test log loss; lower is better | 0.5516 | 0.5151 |
| Fresh contrasting question pairs, both answers correct | 9/20 | 12/20 |
| Original yes/no test, 52 cases | 38/52 (73.1%) | 35/52 (67.3%) |
| Shared yes/no validation, 96 cases | 77/96 (80.2%) | 78/96 (81.3%) |
| Multiple-choice test, 20 cases, two unseen families | 11/20 (zero-shot) | 14/20 |
| Multiple-choice validation, 18 cases | 10/18 (zero-shot) | 12/18 |
| Weights on disk | 328.6 MB float32 | 164.4 MB float16 |
| Mac bundle | 393.6 MB | 229.5 MB |
| Peak resident memory, relocated C host, short request | 892 MB | 1,213 MB |

On the fresh test the new model fixes 5 previous mistakes and introduces 2. Per family it is equal or better everywhere except refund intent (7/9, was 8/9); negation rises from 2/5 to 3/5 and numeric criteria from 7/11 to 8/11, all on tiny counts. The older 52-case test loses three answers, mostly in the refund-policy and permission families, so this release trades a little on that set for the fresh set and the new capability. The 20-case choice test covers document type and animal-or-object families that appear nowhere in training: 7/7 on animal-or-object, 4/7 on document type, 3/6 on the rest.

Peak memory rose because ONNX Runtime materializes the float32 copy of every float16 tensor at load, so the process holds both. Disk and download size halve; resident memory does not. Applications that care more about memory than disk can build from the float32 export in `models/v3-nli-choices` instead.

## What changed

- **Multiple choice.** Each option is scored as a yes/no proposition (`question`, a line break, `Answer: option`), and the softmax over the options' calibrated log-odds gives probabilities that sum to one. See [behavior](../specs/behavior.md). The runtime, C header, Python, Java, Node.js, and browser packages all expose `choose`/`choose_p` with identical rules; the manifest records `choice_template_version: 1`.
- **Data.** [data/choices.jsonl](../data/choices.jsonl) adds 120 synthetic multiple-choice records (72 train, 18 validation, 10 calibration, 20 test), each expanded by the pipeline into one yes/no row per option. The yes/no data is unchanged from 0.2.0: 404 training, 96 validation, 52 calibration rows, plus the frozen 52-case and 80-case tests.
- **Model.** Same foundation and recipe as 0.2.0 (`cross-encoder/nli-MiniLM2-L6-H768`, NLI head initialization, template 2, learning rate 0.00001, batch 16, seed 42, 10 epochs on the M1 Pro GPU, about 135 seconds). Best validation log loss at epoch 8. Temperature scaling on the 52 calibration rows gave 1.16145.
- **Float16 storage.** The new `decisiongator-train compress` command stores every float32 tensor as float16 and inserts a cast back to float32, so all arithmetic stays float32. Against the float32 export, 560 fresh-test and choice predictions moved by at most 0.0017 (mean 0.00013) with no decision flips. Int8 alternatives were measured and rejected again: dynamic, static, and partial int8 all moved individual probabilities by 0.3 to 0.9 and flipped 6 to 27 decisions per split. See [the shrink report](shrink/README.md).
- **Smaller foundations were tested and rejected.** MiniLM-L12-H384, bert-small, and the original base all scored 41 to 46 percent on the fresh test. DeBERTa-v3-xsmall reached 79 percent validation but its export needs pipeline changes and its vocabulary makes it no smaller in practice. See [the foundation report](small-foundation/README.md). A closed-engine alternative was also considered and set aside because its inference engine is not open source; the project keeps only Apache-2.0 and MIT dependencies.

## Verification

Native: 8 Rust unit tests, 168 C and Python interface checks including the new choice entry points, the C smoke host, a relocated C process with networking denied, and frozen platform-parity references regenerated for this model (81 cases). Native predictions matched the PyTorch float32 checkpoint within 0.00215 over 806 cases (the float16 storage accounts for the difference; the 0.2.0 tolerance of 0.0001 no longer applies). On the M1 Pro, 1,000 warm CPU calls at 256 total tokens with four inference threads and 20 warm-up calls gave p50 68.5 ms and p95 79.8 ms, the same speed as 0.2.0. See [the native report](v3/native-parity.json) and [the package report](v3/native-package.json).

Packages on the Mac: the Python wheel passed the isolated consumer test with networking and checkout access denied; the Java build passed 24 tests including six choice integration tests and the packaged-JAR check; the Node package passed 11 tests including mixed concurrent yes/no and choice calls; the browser build passed 691 tokenization cases, 87 yes/no and 5 choice native-parity cases (maximum difference below 0.00001), validation, offline, and integrity tests in Chromium, Firefox, and WebKit. Reports are under `reports/v3/` and `reports/browser-*.json`.

Windows and Linux bundles were not rebuilt in this release and remain at 0.2.0.

## Reproduce

```text
uv run decisiongator-train train --output runs/v3-nli-choices --base cross-encoder/nli-MiniLM2-L6-H768 --revision b95119ce93d3e065de6214e38cd4a97b0f2f2c6d --nli-head --template 2 --learning-rate 1e-5 --epochs 10 --batch-size 16 --seed 42 --device mps --extra-data data/expansion-v2.jsonl --extra-data data/choices.jsonl
uv run decisiongator-train export --checkpoint runs/v3-nli-choices/best --output models/v3-nli-choices --model-id decisiongator-0.3.0-nli-choices-experimental
uv run decisiongator-train compress --bundle models/v3-nli-choices --output models/v3-nli-choices-fp16 --model-id decisiongator-0.3.0-nli-choices-fp16-experimental
uv run decisiongator-train calibrate --bundle models/v3-nli-choices-fp16 --output reports/v3/calibration.json --extra-data data/expansion-v2.jsonl --extra-data data/choices.jsonl
uv run decisiongator-train evaluate --bundle models/v3-nli-choices-fp16 --split test --output reports/v3/test.json --extra-data data/expansion-v2.jsonl --extra-data data/choices.jsonl
uv run decisiongator-train evaluate --bundle models/v3-nli-choices-fp16 --data data/evaluation-v2.jsonl --split test --output reports/v3/fresh-test.json
uv run --python 3.12 --with onnxruntime==1.22.1 code/build.py --model models/v3-nli-choices-fp16 --output released/macos-arm64
```

The fresh test and the choice test have now been seen during development; a future accuracy claim needs another fresh test. The previous Mac bundle is preserved at `models/macos-arm64-v2/`; nothing has been published.
