# Accuracy experiment 2

The original model achieves 212/224 on its training examples (94.6%) but only 32/52 on the original synthetic test. This experiment targets generalization rather than merely fitting the original examples more closely.

## Frozen comparison plan

Keep the original model bundle unchanged while experimenting. Compare a question-aware NLI foundation (`cross-encoder/nli-MiniLM2-L6-H768`, revision `b95119ce93d3e065de6214e38cd4a97b0f2f2c6d`) against the original MiniLM foundation. NLI means predicting whether one passage supports another. Retain its learned language/relationship representation, initialize a binary output head from its existing three-way head, and fine-tune on explicit yes/no labels. The initial no row averages contradiction and neutral weights; this is only initialization, not a claim that unknown evidence means no.

Use content first, question plus optional criteria second for the new model (template version 2). Preserve version 1 input ordering for the original bundle. Never change model input ordering without recording it in the manifest.

An additional independently assigned authoring task supplies training, validation, and calibration examples without inspecting the fresh test. Another task writes 80 new test records without reading previous model results or the training collections beyond the schema. This separates authoring tasks but is still same-model synthetic data, not independent human evaluation.

Select checkpoint and training recipe using training and validation results only. Compare both models on identical validation data, including any expansion data. Freeze the selected candidate and calibrate using the calibration partition before opening the new test results. If quantization is used, choose it by validation fidelity and recalibrate the chosen export.

Replace the default local bundle only if the frozen candidate improves fresh-test accuracy by at least five percentage points and improves Brier score against the original model on the same examples, passes native parity/integration checks, and shows no new failure on the explicit refund/cancellation smoke cases. Report all original and fresh-test results, per-family weaknesses, and size/speed tradeoffs. These are local experiment acceptance criteria, not the broader public-release accuracy requirements.

## Trials

Begin with the new foundation on the unchanged 224-example training collection, then compare expanded-data runs on the same fixed validation collection. Use small local runs, record all completed trials, and avoid selecting by the fresh test. Preserve prior checkpoints and reports. No cloud training or paid teacher is required.

## Outcome and current recipe

The selected expanded-data NLI model passed the local comparison gate: 59/80 fresh-test answers correct versus the original's 42/80, with better Brier score. See [the complete report](../reports/accuracy-v2.md), including regressions. Full precision was retained after quantization caused large per-example changes. The bundle is about 394 MB, exceeding the initial size budget; model quality is still experimental.

Reproduce the selected training run and export into new directories:

```text
uv sync --locked
uv run --locked decisiongator-train validate --extra-data data/expansion-v2.jsonl
uv run --locked decisiongator-train train --base cross-encoder/nli-MiniLM2-L6-H768 --revision b95119ce93d3e065de6214e38cd4a97b0f2f2c6d --nli-head --template 2 --learning-rate 0.00001 --epochs 10 --extra-data data/expansion-v2.jsonl --output runs/my-v2
uv run --locked decisiongator-train export --checkpoint runs/my-v2/best --output models/my-v2 --model-id my-v2
uv run --locked decisiongator-train calibrate --bundle models/my-v2 --extra-data data/expansion-v2.jsonl --output reports/my-v2-calibration.json
uv run --locked decisiongator-train evaluate --bundle models/my-v2 --data data/evaluation-v2.jsonl --split test --output reports/my-v2-fresh-test.json
uv run code/build.py --model models/my-v2 --output released/my-v2-mac
uv run tests/native_check.py --bundle released/my-v2-mac
```

The `evaluate` command also accepts `--split train` for measuring fitting accuracy. `--data` replaces the default dataset list; `--extra-data` appends to it. Do not accidentally supply test-only `--data` files to training. Training explicitly selects `train` and `validation` partitions and calibration selects `calibration`.

To adapt the current model to your own examples, use `--start runs/v2-nli-expanded/best`, include `--extra-data data/expansion-v2.jsonl` and your correction file, and choose a fresh run directory. The saved checkpoint retains its base-model identity and template order. Native ONNX files are deployment assets; use the saved training checkpoint or reproduce it for further training. Compare the new candidate with the current release and retain both until gains are demonstrated.

Quantization is available experimentally through `decisiongator-train quantize --bundle SOURCE --output NEW_DIRECTORY --model-id NEW_ID`; `--quantize-embeddings` additionally compresses embedding tables. It resets calibration. Always evaluate prediction changes, recalibrate the chosen variant, and verify native parity before considering it for use. Neither quantized variant tested in this experiment was accepted. Version 0.3.0 instead ships float16 weight storage through `decisiongator-train compress --bundle SOURCE --output NEW_DIRECTORY --model-id NEW_ID`, which keeps float32 arithmetic and moved no test decision; see [the v0.3 report](../reports/accuracy-v3.md).
