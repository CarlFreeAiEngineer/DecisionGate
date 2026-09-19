# Can a smaller pretrained foundation match the released model?

No. Every small foundation that could actually be trained, exported, calibrated and fresh-tested through this project's pipeline lands 30 or more fresh-test percentage points below the released cross-encoder/nli-MiniLM2-L6-H768 model, even after fine-tuning on the same expanded data with the same recipe. One promising 70.8M-parameter candidate (cross-encoder/nli-deberta-v3-xsmall's foundation) reached validation accuracy close to the release, but it cannot be exported through the current pipeline at all because of an architecture mismatch, so it never reached fresh testing. The bundle should stay on the current 82M-parameter foundation until either the pipeline is extended to support token-type-free architectures or a genuinely different small candidate is found.

## Results compared with the release

The released model: cross-encoder/nli-MiniLM2-L6-H768 (Apache-2.0), 82,119,938 parameters, trained with `--nli-head --template 2 --learning-rate 1e-5 --epochs 10 --batch-size 16 --seed 42 --extra-data data/expansion-v2.jsonl`. Validation accuracy 80.2% (96 records), fresh test 59/80 (73.8%), model.onnx 328,609,581 bytes (328.6 MB).

| Candidate | Params (M) | ONNX (MB) | Val acc | Val logloss | Fresh test | Fresh Brier | Fresh logloss | p50 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Released (nli-MiniLM2-L6-H768) | 82.1 | 328.6 | 80.2% | 0.423 | 59/80 (73.8%) | 0.181 | 0.552 | 20.3 |
| MiniLM-L12 lr1e-5 | 33.4 | 133.7 | 55.2% | 0.664 | 37/80 (46.3%) | 0.271 | 0.736 | 8.0 |
| MiniLM-L12 lr3e-5 | 33.4 | 133.7 | 62.5% | 0.675 | 36/80 (45.0%) | 0.251 | 0.696 | 7.8 |
| bert-small lr1e-5 | 28.8 | 115.1 | 58.3% | 0.619 | 33/80 (41.3%) | 0.286 | 0.773 | 3.9 |
| bert-small lr3e-5 | 28.8 | 115.1 | 66.7% | 0.604 | 33/80 (41.3%) | 0.296 | 0.797 | 4.0 |
| bert-small lr3e-5 int8 | 28.8 | 76.8 | 65.6% | 0.593 | 35/80 (43.8%) | 0.293 | 0.789 | 3.8 |
| deberta-v3-xsmall lr1e-5 (no export) | 70.8 | n/a | 65.6%* | 0.654* | not exported | -- | -- | -- |
| deberta-v3-xsmall lr3e-5 (no export) | 70.8 | n/a | 79.2%* | 0.513* | not exported | -- | -- | -- |

Rows marked with `*` are the raw training-loop validation numbers from `history.json` (uncalibrated, computed with PyTorch, not through an exported ONNX bundle), included for reference only because that candidate could not be exported or calibrated; they are not directly comparable to the other rows' calibrated ONNX-evaluate numbers. p50 latency figures come from the pipeline's `evaluate` command on this machine, not the release's 1,000-call benchmark, so compare candidates to each other, not to any published release latency claim.

## The four candidates and what happened to each

**1. cross-encoder/nli-MiniLM2-L6-H384.** Does not exist. A search of the cross-encoder org (`https://huggingface.co/api/models?author=cross-encoder&search=nli`) turns up no RoBERTa-family NLI cross-encoder smaller than the released nli-MiniLM2-L6-H768 (82,121,221 safetensors parameters). The closest same-family option, cross-encoder/nli-distilroberta-base (Apache-2.0), is 82,121,221 parameters too, i.e. no size reduction, so it was not trained. The next-smallest RoBERTa-family NLI models in that org (nli-roberta-base, nli-deberta-base, nli-deberta-v3-base/large) are all larger. There is no smaller RoBERTa-architecture NLI cross-encoder to test here.

**2. cross-encoder/nli-deberta-v3-xsmall (Apache-2.0), 70,831,619 safetensors parameters.** Loading this checkpoint through the pipeline's plain `num_labels=2` path (the path used for any base other than a RoBERTa three-class NLI head) fails immediately: the checkpoint's existing classifier already has 3 output labels, and `AutoModelForSequenceClassification.from_pretrained(..., num_labels=2)` in `training/pipeline.py` does not pass `ignore_mismatched_sizes=True`, so it raises `RuntimeError: size mismatch ... torch.Size([3]) ... torch.Size([2])`. To still test this backbone size, training used the pre-NLI-finetune foundation microsoft/deberta-v3-xsmall (MIT license, same architecture, revision `4b419818330868dff6a60ad3e6b1c730f8b8c0c6`), which has no classifier head, so the plain path attaches a fresh one cleanly (70,830,722 parameters after that head is added). This needed `sentencepiece` and `protobuf`, which are not in the project's `training` dependency group; they were added transiently with `uv run --with sentencepiece --with protobuf ...` rather than editing `pyproject.toml`/`uv.lock`. Training succeeded and gave the best validation numbers of any small candidate: 65.6% at lr 1e-5, 79.2% at lr 3e-5 (close to the release's 80.2%). But `export` then fails: DeBERTa v3's config has `type_vocab_size: 0` (it never consumes `token_type_ids`), so `torch.onnx.export` drops that unused input from the traced graph, and the pipeline's export step, which always feeds and verifies all three named inputs (`input_ids`, `attention_mask`, `token_type_ids`), fails with `onnxruntime...InvalidArgument: Invalid input name: token_type_ids`. This is an architecture-level incompatibility with the project's fixed 3-input ONNX contract, not a numeric or licensing problem, and fixing it would mean changing `training/pipeline.py`'s export function, which was out of scope here. So despite the best validation accuracy observed, this candidate could not be exported, calibrated, or fresh-tested, and cannot ship as-is.

**3. microsoft/MiniLM-L12-H384-uncased (MIT), the project's original default base, 33,360,770 parameters.** The task noted it reaches only 42/80 on the original data and said to skip unless cheap; each 10-epoch run took about 60-70 seconds on the local mps device (already cached locally), so both learning rates were run on the expanded data anyway. Best validation rose to 62.5% (lr 3e-5) versus the previously known 71.9%/similar range for other bases, but fresh-test accuracy stayed at 36-37/80 (45-46%), well below both the release and even the original 42/80 baseline on the smaller original dataset. Expanding the training data did not fix this base's generalization problem.

**4. prajjwal1/bert-small (MIT), 28,764,674 parameters, hidden size 512, 4 layers, 30,522-token WordPiece vocabulary.** The smallest candidate tested, chosen because it is explicitly MIT-licensed, in the 20-40M range, and its tokenizer already supports sentence pairs. Best validation accuracy 66.7% (lr 3e-5), the best among the three candidates that actually reached a working ONNX bundle, but fresh test still lands at 33/80 (41.3%), similar to MiniLM-L12 and far below the release.

## Quantization

Dynamic int8 quantization (`decisiongate-train quantize`) was run on the best exported small candidate, bert-small lr 3e-5, since it had the lowest validation log loss (0.604) of the candidates with working bundles. `model.onnx` shrank from 115,147,542 to 76,772,077 bytes (33.3% smaller). After recalibrating, validation accuracy went from 66.7% to 65.6% and fresh test moved from 33/80 to 35/80; both changes are within noise for an 80-96 example split and do not change the overall conclusion that this foundation underperforms the release by a wide margin.

## Exact commands

```
uv run --locked decisiongate-train validate --extra-data data/expansion-v2.jsonl

# MiniLM-L12-H384-uncased (project default base, MIT)
uv run --locked decisiongate-train train --template 2 --learning-rate 0.00001 --epochs 10 --batch-size 16 --seed 42 --device mps --extra-data data/expansion-v2.jsonl --output runs/small-minilm-l12-lr1e5
uv run --locked decisiongate-train train --template 2 --learning-rate 0.00003 --epochs 10 --batch-size 16 --seed 42 --device mps --extra-data data/expansion-v2.jsonl --output runs/small-minilm-l12-lr3e5

# prajjwal1/bert-small (MIT)
uv run --locked decisiongate-train train --base prajjwal1/bert-small --revision 0ec5f86f27c1a77d704439db5e01c307ea11b9d4 --template 2 --learning-rate 0.00001 --epochs 10 --batch-size 16 --seed 42 --device mps --extra-data data/expansion-v2.jsonl --output runs/small-bert-small-lr1e5
uv run --locked decisiongate-train train --base prajjwal1/bert-small --revision 0ec5f86f27c1a77d704439db5e01c307ea11b9d4 --template 2 --learning-rate 0.00003 --epochs 10 --batch-size 16 --seed 42 --device mps --extra-data data/expansion-v2.jsonl --output runs/small-bert-small-lr3e5

# microsoft/deberta-v3-xsmall (MIT foundation behind cross-encoder/nli-deberta-v3-xsmall, Apache-2.0)
# needs sentencepiece + protobuf, added transiently, not persisted to pyproject.toml/uv.lock
uv run --with sentencepiece --with protobuf --locked decisiongate-train train --base microsoft/deberta-v3-xsmall --revision 4b419818330868dff6a60ad3e6b1c730f8b8c0c6 --template 2 --learning-rate 0.00001 --epochs 10 --batch-size 16 --seed 42 --device mps --extra-data data/expansion-v2.jsonl --output runs/small-deberta-v3-xsmall-lr1e5
uv run --with sentencepiece --with protobuf --locked decisiongate-train train --base microsoft/deberta-v3-xsmall --revision 4b419818330868dff6a60ad3e6b1c730f8b8c0c6 --template 2 --learning-rate 0.00003 --epochs 10 --batch-size 16 --seed 42 --device mps --extra-data data/expansion-v2.jsonl --output runs/small-deberta-v3-xsmall-lr3e5
# export then fails for both: onnxruntime.capi.onnxruntime_pybind11_state.InvalidArgument: Invalid input name: token_type_ids

# export, calibrate, evaluate (repeat --checkpoint/--bundle/--output for each successful run)
uv run --locked decisiongate-train export --checkpoint runs/small-bert-small-lr3e5/best --output models/small-bert-small-lr3e5 --model-id small-bert-small-lr3e5
uv run --locked decisiongate-train calibrate --bundle models/small-bert-small-lr3e5 --extra-data data/expansion-v2.jsonl --output reports/small-foundation/small-bert-small-lr3e5-calibration.json
uv run --locked decisiongate-train evaluate --bundle models/small-bert-small-lr3e5 --split validation --extra-data data/expansion-v2.jsonl --output reports/small-foundation/small-bert-small-lr3e5-validation.json
uv run --locked decisiongate-train evaluate --bundle models/small-bert-small-lr3e5 --data data/evaluation-v2.jsonl --split test --output reports/small-foundation/small-bert-small-lr3e5-fresh-test.json

# quantization of the best exported small candidate
uv run --locked decisiongate-train quantize --bundle models/small-bert-small-lr3e5 --output models/small-bert-small-lr3e5-int8 --model-id small-bert-small-lr3e5-int8
uv run --locked decisiongate-train calibrate --bundle models/small-bert-small-lr3e5-int8 --extra-data data/expansion-v2.jsonl --output reports/small-foundation/small-bert-small-lr3e5-int8-calibration.json
uv run --locked decisiongate-train evaluate --bundle models/small-bert-small-lr3e5-int8 --split validation --extra-data data/expansion-v2.jsonl --output reports/small-foundation/small-bert-small-lr3e5-int8-validation.json
uv run --locked decisiongate-train evaluate --bundle models/small-bert-small-lr3e5-int8 --data data/evaluation-v2.jsonl --split test --output reports/small-foundation/small-bert-small-lr3e5-int8-fresh-test.json
```

Full epoch histories, initial-validation baselines and training configs are in `runs/small-*/history.json` and `runs/small-*/config.json`. Exported bundles are in `models/small-*/`. Per-candidate calibration/validation/fresh-test JSON (including per-question predictions) are alongside this file in `reports/small-foundation/`.

## Recommendation

Keep shipping the released cross-encoder/nli-MiniLM2-L6-H768 bundle; none of the four candidate families produced a working, delivered model that comes close to its 73.8% fresh-test accuracy, and validation accuracy alone was a poor predictor of fresh-test generalization for the smaller bases (bert-small and MiniLM-L12 both reached 62-67% validation while still landing at 41-46% fresh test, barely above chance). The one genuinely interesting result, microsoft/deberta-v3-xsmall's foundation reaching 79.2% validation accuracy at 70.8M parameters (14% smaller than the release), is blocked by a real pipeline limitation rather than a modeling one: `training/pipeline.py`'s `export()` always feeds and checks a `token_type_ids` input that DeBERTa v3 architecturally never uses, so the ONNX export's own self-check fails before any fresh-test number can be produced. If shrinking the bundle stays a priority, the highest-value next step is a scoped change to the export path (outside this task's boundaries) to make `token_type_ids` optional for architectures that do not use it, so this candidate can actually be fresh-tested; only after that is a real accuracy comparison possible. Quantizing the released model itself, rather than swapping foundations, is also worth revisiting: a prior experiment (`reports/accuracy-v2.md`) rejected int8 quantization of an earlier NLI checkpoint over large per-example probability swings, but that was on a different checkpoint and data mix than the current release, and quantization tested here on bert-small shrank the ONNX file by a third with only noise-level accuracy change.
