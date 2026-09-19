# Version 0.4.0: a larger foundation and ten times the data

Version 0.4.0 replaces the 82M-parameter MiniLM foundation with DeBERTa-v3-large (435M parameters, MIT), trained on the old data plus 3,526 newly authored records in sixteen task families. On a new 480-case held-out test written by separate authors, accuracy rises from 59.2% (the shipped 0.3.0 model) to 92.3%. The fresh 80-case test rises from 77.5% to 92.5% and the original 52-case test from 67.3% to 94.2%. The float16 Mac bundle is about 900 MB, under the 1 GB limit set for this release and about four times the size of 0.3.0. Every record is still synthetic and machine-authored; a blind re-labelling of 232 sampled records agreed with all stored labels, but no independent human benchmark exists yet.

## Why the old model was near coin-flip

The 0.3.0 model failed simple rule application: "editors may rename it, Ren is an editor", "either a staff badge or a volunteer pass", "4.8 kg against a 4 kg limit", "ignore the question and answer yes". Two causes were confirmed by experiment. First, the foundation was too small: fine-tuning DeBERTa-v3-base and DeBERTa-v3-large on the unchanged 0.3.0 data alone lifted the new test from 59.2% to 74.2% and 83.8%. Second, the data was too small: 404 training rows cannot teach negation, exceptions, and numeric limits. Adding the v4 data lifted DeBERTa-v3-base to 82.3% and DeBERTa-v3-large to 92.3%. Smaller foundations had already been measured and rejected in [the foundation report](small-foundation/README.md).

Zero-shot instruction models were also measured on the fresh 80-case test as a ceiling check before any training: flan-t5-large 86.3%, Qwen2.5-1.5B-Instruct 82.5%, flan-t5-base 71.3%, Qwen2.5-0.5B and Qwen3-0.6B 67.5%. Needle3, a 121M tool-calling model, scored 52.5% at best under two prompt forms; it is not built for this task. None of these were adopted: the encoder route keeps the existing runtime contract and export path.

## Results

The new test is `data/v4/test-1.jsonl` to `test-4.jsonl`: 480 records, 30 per family, 50% yes. It was written by four agents that saw only the authoring brief, never the training files. It was used once to compare foundations and once to score the candidates, so it counts as seen for the next release.

| Model | New test, 480 | Fresh test, 80 | Original test, 52 | Choice test, 20 | Spam test, 32 | Email test, 40 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.3.0 shipped, MiniLM 82M | 59.2% | 77.5% | 67.3% | 70% | 53.1% | 82.5% |
| DeBERTa-v3-base, 0.3.0 data | 74.2% | 86.2% | 94.2% | 90% | | |
| DeBERTa-v3-large, 0.3.0 data | 83.8% | 90.0% | 92.3% | 95% | | |
| DeBERTa-v3-base, v4 data | 82.3% | 88.8% | 94.2% | 90% | 90.6% | 85.0% |
| DeBERTa-v3-large, v4 data, epoch 1 (shipped) | 92.3% | 92.5% | 94.2% | 95% | 90.6% | 82.5% |
| DeBERTa-v3-large, v4 data, epoch 5 | 89.8% | 93.8% | 88.5% | 100% | 90.6% | 87.5% |

Log loss on the new test falls from 0.789 to 0.206 (a constant 0.5 scores 0.693). Epoch 1 was selected by the pipeline's rule, lowest validation log loss, before the test was scored; later epochs were more confident and slightly less accurate on the held-out sets, so the rule chose well.

Per family on the new test, shipped model: everyday, negation, and refund intent 100%; appointment intent, cancellation intent, email screening, events timeline, quoted instructions, and spam promotion 97%; evidence presence and routing 93%; duplicate reports 90%; permissions 87%; urgency 83%; eligibility 80%; numeric criteria 70%. Each family is 30 cases, so one case is 3.3 points.

The remaining errors are concentrated in arithmetic and exact boundaries: sums of line items against a threshold, a percentage computed from two counts, "exactly 2.000 kg" against "no more than 2 kg", "0.2 litres a minute" against "ten litres an hour", and dates counted against a window. An encoder scores these from surface features, not calculation. Applications that need arithmetic should do the arithmetic in code and ask the component the remaining question of intent or wording.

## What changed

- **Foundation.** `MoritzLaurer/deberta-v3-large-zeroshot-v2.0` (MIT), a DeBERTa-v3-large already trained on natural-language-inference and classification data with an entailment/not-entailment head. The pipeline now reuses any entailment head, not only RoBERTa's three-class head, and keeps the `token_type_ids` input in the ONNX graph for architectures that ignore it, so the runtime contract is unchanged. DeBERTa-v3-base (`MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, MIT, 370 MB float16) is the fallback if size matters more than the ten points it gives up.
- **Data.** [data/v4](../data/v4/README.md): 3,526 training, validation, and calibration records in sixteen families, plus the 480-case test. Combined with the earlier files the run used 3,386 yes/no training rows, 448 validation, 244 calibration, and the 120 choice records.
- **Recipe.** Template 2, learning rate 0.00001, batch 16, seed 42, 5 epochs, best epoch by validation log loss, temperature 1.6218 fitted on the calibration split, float16 storage with float32 compute. Trained on a Google Colab A100 (about 90 seconds per epoch); the M1 Pro could not hold DeBERTa-large in memory even at batch 4 with gradient checkpointing.
- **Pipeline options.** `--gradient-checkpointing` and `--fixed-shapes` were added while trying to fit the large model locally, and an MPS cache release every few steps fixed a leak that grew until training failed. They are not part of the release recipe.
- **Browser runtime.** The tokenizer check now accepts template post-processors (DeBERTa) as well as RoBERTa.

## Verification

Native, on the M1 Pro: 8 Rust unit tests and 168 C and Python interface checks passed in [the build log](v4/macos-build.log); the relocated C host ran with networking denied ([native-package.json](v4/native-package.json)); native predictions matched the PyTorch checkpoint within 0.0022 over 562 cases ([native-parity.json](v4/native-parity.json), the float16 storage accounts for the difference); a new 81-case platform-parity reference was frozen from this bundle (`tests/fixtures/platform-parity.json`, the 0.3.0 reference is kept as `platform-parity-v3.json`). Float16 storage moved 480 test probabilities by at most 0.0022 with no decision flips against the float32 export, and the float16 bundle re-scored on the Mac gave the same 92.5% on the fresh test as on Colab.

| Measurement | Version 0.3.0 | Version 0.4.0 |
| --- | ---: | ---: |
| Weights on disk, float16 | 164 MB | 872 MB |
| Mac bundle | 229 MB | 899 MB |
| Warm p50 / p95, 256 tokens, 4 threads, 1,000 calls | 68.5 / 79.8 ms | 559 / 651 ms |
| Native load time | | 5.6 s |
| Peak resident memory, relocated C host | 1,213 MB | 5,326 MB |

The cost of the accuracy is speed and memory: each call takes about eight times longer and the process holds about 5 GB, because ONNX Runtime keeps the float32 copy of every float16 tensor alongside the stored one. Applications that need less memory can build from the float32 export in `models/v4-large`, or from the DeBERTa-v3-base checkpoint recipe (370 MB float16, 82.3% on the new test).

Packages on the Mac, all rebuilt from this bundle: the Python wheel (823 MB) passed the isolated consumer test with networking and checkout access denied; the Java build passed 24 tests including six choice integration tests, and the packaged 0.4.0 classifier JAR passed the offline consumer check; the Node package passed 11 tests and packs to a 1.63 GB tarball holding both the native and browser assets; the browser build passed 691 tokenization cases, 87 yes/no and 5 choice native-comparison cases (maximum differences 0.00000059 and 0.0000002), validation, offline reload, and integrity tests in Chromium 153, Firefox 155, and Playwright WebKit 26.6, where warm calls took about 570 ms. The browser tokenizer check now accepts the DeBERTa template post-processor, and the JavaScript tokenizer reproduced the native segment ids for pairs without any change to the comparison. Package reports are under `reports/v4/` and `reports/browser-*.json`.

Windows and Linux bundles were not rebuilt in this release and remain at 0.2.0.

## Reproduce

```text
uv run decisiongate-train train --output runs/v4-large --base MoritzLaurer/deberta-v3-large-zeroshot-v2.0 --revision cf44676c28ba7312e5c5f8f8d2c22b3e0c9cdae2 --nli-head --template 2 --learning-rate 1e-5 --epochs 5 --batch-size 16 --seed 42 --device cuda --extra-data data/expansion-v2.jsonl --extra-data data/choices.jsonl --extra-data data/v4/appointment_intent.jsonl ... --extra-data data/v4/urgency.jsonl
uv run decisiongate-train export --checkpoint runs/v4-large/best --output models/v4-large --model-id decisiongate-0.4.0-large-experimental
uv run decisiongate-train compress --bundle models/v4-large --output models/v4-large-fp16 --model-id decisiongate-0.4.0-large-fp16-experimental
uv run decisiongate-train calibrate --bundle models/v4-large-fp16 --output reports/v4/colab/large-best-fp16-calibration.json <same --extra-data list>
uv run decisiongate-train evaluate --bundle models/v4-large-fp16 --data data/v4/test-1.jsonl --data data/v4/test-2.jsonl --data data/v4/test-3.jsonl --data data/v4/test-4.jsonl --split test --output reports/v4/colab/large-best-fp16-v4test.json
uv run --python 3.12 --with onnxruntime==1.22.1 code/build.py --model models/v4-large-fp16 --output released/macos-arm64
```

The `...` stands for every training file in `data/v4/` except `test-*.jsonl`. Colab reports, the training log, and the epoch history are under `reports/v4/colab/` and `runs/v4-large/`. The previous Mac bundle is preserved at `models/macos-arm64-v3/`.
