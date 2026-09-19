# Shrinking the ONNX export

Goal: find the smallest ONNX export of the released yes/no model whose predictions stay close to the float32 reference (`released/macos-arm64`, `model.onnx` = 328,609,581 bytes, template_version 2), so the shipped bundle can shrink below 394 MB. Nothing under `released/`, `code/`, `decisiongate/`, `specs/`, `README.md`, or `training/pipeline.py` was modified. All scripts live in `reports/shrink/`, all candidate bundles live in `models/shrink-*/`.

The float reference used for building/evaluating candidates is `models/v2-nli-expanded`, which is byte-identical to `released/macos-arm64/model.onnx` (same sha256 `fa57f3fe...`) and carries the same calibrated temperature (1.1350108156723155). Evaluation used `training/pipeline.py`'s own `evaluate`/`calibrate` commands unmodified (CPUExecutionProvider, 4 intra-op threads, ONNX Runtime 1.22.1, matching the pinned version) so results are directly comparable to how the project already measures the released model. Two frozen splits were used throughout: the 96-record `validation` split (seed+plain-questions+expansion-v2) and the 80-record frozen `test` split from `data/evaluation-v2.jsonl`.

For every candidate two variants were measured:

- **default**: the quantized/converted bundle as produced, manifest `temperature` reset to 1.0 (matching the existing project convention in `quantize()`, which also resets calibration after quantization).
- **recal**: a copy of the same bundle recalibrated with `decisiongate-train calibrate` on the 52-record `calibration` split, to see whether refitting the temperature restores agreement with the float reference.

"maxdiff"/"meandiff" are the max/mean absolute difference in `p_yes` versus the float reference on the same records; "flips" counts records whose 0.5-threshold decision differs from the float reference.

## Candidate sizes

| model | model.onnx bytes | % of float | size change |
|-------|------------------|-----------:|------------:|
| float reference (`models/v2-nli-expanded`, = `released/macos-arm64`) | 328,609,581 | 100.0% | - |
| C1 `shrink-1-int8-matmul` (dynamic int8, MatMul/Gemm) | 199,747,964 | 60.8% | -39.2% |
| C2 `shrink-2-int8-matmul-embed` (dynamic int8, +Gather/embeddings) | 82,752,416 | 25.2% | -74.8% |
| C3a `shrink-3a-static-qdq-minmax` (static QDQ int8, MinMax) | 199,728,815 | 60.8% | -39.2% |
| C3b `shrink-3b-static-qdq-percentile` (static QDQ int8, Percentile) | 199,728,707 | 60.8% | -39.2% |
| C3c `shrink-3c-static-qdq-percentile-noclf` (as 3b, classifier head excluded) | 201,488,915 | 61.3% | -38.7% |
| C4 `shrink-4-fp16` (fp16 weight storage, Cast back to fp32) | 164,387,295 | 50.0% | -50.0% |
| C5 `shrink-5-int8-ffn-only` (dynamic int8, FFN MatMuls only; optional) | 242,090,666 | 73.7% | -26.3% |

## Validation split (96 records)

| model       | acc   | logloss | brier | temp  | maxdiff | meandiff | flips | p50ms | p95ms |
|-------------|-------|---------|-------|-------|---------|----------|-------|-------|-------|
| float ref   | 0.802 | 0.415   | 0.130 | 1.135 |    -    |    -     |  0/96 | 19.0  | 23.9  |
| C1 default  | 0.833 | 0.388   | 0.126 | 1.000 | 0.340   | 0.074    | 9/96  | 16.0  | 19.5  |
| C1 recal    | 0.833 | 0.392   | 0.127 | 1.303 | 0.318   | 0.078    | 9/96  | 16.3  | 21.1  |
| C2 default  | 0.844 | 0.356   | 0.112 | 1.000 | 0.662   | 0.073    | 14/96 | 15.9  | 20.4  |
| C2 recal    | 0.844 | 0.364   | 0.115 | 1.202 | 0.634   | 0.078    | 14/96 | 16.2  | 20.3  |
| C3a default | 0.698 | 0.608   | 0.202 | 1.000 | 0.908   | 0.210    | 24/96 | 17.3  | 20.8  |
| C3a recal   | 0.698 | 0.558   | 0.189 | 2.427 | 0.721   | 0.216    | 24/96 | 17.0  | 20.6  |
| C3b default | 0.719 | 0.536   | 0.189 | 1.000 | 0.935   | 0.181    | 26/96 | 16.2  | 19.5  |
| C3b recal   | 0.719 | 0.514   | 0.179 | 1.413 | 0.876   | 0.180    | 26/96 | 16.1  | 20.9  |
| C3c default | 0.708 | 0.536   | 0.189 | 1.000 | 0.936   | 0.181    | 27/96 | 16.8  | 21.1  |
| C4 default  | 0.802 | 0.423   | 0.130 | 1.000 | 0.029   | 0.014    | 0/96  | 20.0  | 27.2  |
| C4 recal    | 0.802 | 0.415   | 0.130 | 1.135 | 0.001   | 0.000    | 0/96  | 20.5  | 27.7  |
| C5 default  | 0.865 | 0.399   | 0.125 | 1.000 | 0.414   | 0.060    | 12/96 | 17.1  | 21.1  |
| C5 recal    | 0.865 | 0.398   | 0.125 | 1.035 | 0.408   | 0.059    | 12/96 | 17.2  | 21.3  |

## Fresh test split (80 records, `data/evaluation-v2.jsonl`)

| model       | acc   | logloss | brier | temp  | maxdiff | meandiff | flips | p50ms | p95ms |
|-------------|-------|---------|-------|-------|---------|----------|-------|-------|-------|
| float ref   | 0.738 | 0.552   | 0.181 | 1.135 |    -    |    -     |  0/80 | 11.8  | 15.3  |
| C1 default  | 0.713 | 0.592   | 0.194 | 1.000 | 0.450   | 0.091    | 6/80  | 9.8   | 15.1  |
| C1 recal    | 0.713 | 0.534   | 0.181 | 1.303 | 0.423   | 0.084    | 6/80  | 9.5   | 13.2  |
| C2 default  | 0.700 | 0.729   | 0.226 | 1.000 | 0.574   | 0.104    | 9/80  | 9.9   | 15.2  |
| C2 recal    | 0.700 | 0.660   | 0.215 | 1.202 | 0.536   | 0.099    | 9/80  | 9.5   | 13.1  |
| C3a default | 0.637 | 0.830   | 0.275 | 1.000 | 0.895   | 0.260    | 26/80 | 9.5   | 13.5  |
| C3a recal   | 0.637 | 0.646   | 0.230 | 2.427 | 0.736   | 0.262    | 26/80 | 10.0  | 13.2  |
| C3b default | 0.713 | 0.596   | 0.198 | 1.000 | 0.733   | 0.153    | 12/80 | 9.5   | 12.7  |
| C3b recal   | 0.713 | 0.552   | 0.188 | 1.413 | 0.667   | 0.162    | 12/80 | 10.1  | 13.9  |
| C3c default | 0.713 | 0.595   | 0.197 | 1.000 | 0.732   | 0.153    | 12/80 | 9.8   | 13.2  |
| C4 default  | 0.738 | 0.581   | 0.186 | 1.000 | 0.029   | 0.016    | 0/80  | 13.2  | 17.8  |
| C4 recal    | 0.738 | 0.552   | 0.181 | 1.135 | 0.002   | 0.000    | 0/80  | 13.2  | 18.5  |
| C5 default  | 0.725 | 0.639   | 0.208 | 1.000 | 0.614   | 0.092    | 11/80 | 10.2  | 14.0  |
| C5 recal    | 0.725 | 0.627   | 0.207 | 1.035 | 0.606   | 0.091    | 11/80 | 10.3  | 13.6  |

Raw `decisiongate-train evaluate` outputs (with per-record predictions) are in `reports/shrink/<name>-<split>.json` and `reports/shrink/<name>-recal-<split>.json`; the merged comparison numbers are in `reports/shrink/compare-summary.json`.

## Load checks and op inventory (ONNX Runtime 1.22.1, CPUExecutionProvider, 4 threads)

Every candidate above loaded and ran successfully under the pinned onnxruntime 1.22.1 via `decisiongate-train evaluate` (that command builds the session with `CPUExecutionProvider` and `intra_op_num_threads = 4`, so a successful evaluate run is the load/run confirmation). Op inventory per candidate (all opset 17, same as the float export):

- **C1/C2/C5** (dynamic int8): add `DynamicQuantizeLinear`, `MatMulInteger`, and (C2 only) `DequantizeLinear` for the quantized `Gather` embedding tables. All are standard ONNX ops available in onnxruntime-web 1.22's wasm backend; nothing exotic.
- **C3a/C3b/C3c** (static QDQ int8): add `QuantizeLinear`/`DequantizeLinear` pairs around `MatMul`/`Gemm`. Also standard ops, wasm-safe.
- **C4** (fp16 weights): no new op types at all - it is the exact float graph plus one `Cast` node per converted initializer (`Cast` was already present in the original graph for the attention mask). `Cast` is trivially supported in onnxruntime-web wasm.

No candidate introduces a custom/contrib op, so none of them should need anything beyond the standard onnxruntime-web 1.22 wasm op set.

## What failed / what needed a workaround (reported honestly)

- **fp16 via `onnxconverter_common.float16.convert_float_to_float16` (the alternative the spec mentions) did not work as-is.** With `keep_io_types=True` it still fails to load: it leaves the extended-attention-mask `Cast` node computing float32 (its `to` attribute is untouched) while a downstream `Sub`/`Mul` on the same tensor gets converted to fp16, producing a genuine type mismatch (`Type parameter (T) of Optype (Sub) bound to different types (tensor(float16) and tensor(float))`). Clearing stale `value_info` and re-running shape inference fixed the first symptom (a Cast output-type mismatch) but not this second, real one. Rather than chase `op_block_list`/`node_block_list` tuning, C4 was built with the spec's *primary* method instead: every float32 initializer (105 of them, 100% of the graph's weight bytes) is stored as fp16 and immediately `Cast` back to float32, so the entire compute graph still runs in float32 - this is simpler, avoids all fp16-arithmetic type-matching issues, and is what "still computes in fp32" in the task actually asks for. Script: `reports/shrink/fp16_convert.py`.
- **`CalibrationMethod.Percentile` (and Entropy) crash on variable-length inputs.** `onnxruntime.quantization`'s histogram-based calibrators stack all collected activation values into one array per tensor name across the whole calibration set, which requires every calibration step to produce the same tensor shape; our records have different token lengths, so the first attempt raised `ValueError: setting an array element with a sequence ... inhomogeneous shape`. Fixed by right-padding all 52 calibration records to the longest one (`<pad>` token id 1, `attention_mask`=0, `token_type_ids`=0) before feeding them to the calibrator, in `reports/shrink/static_quantize.py`. `CalibrationMethod.MinMax` does not need this (it worked without padding too, but was rebuilt padded for consistency with the Percentile run).
- **Static QDQ int8 (C3a/b/c) does not reach acceptable agreement, with or without excluding the classifier head.** Even after recalibration, validation accuracy stays in the high 0.6s/low 0.7s (float reference: 0.80), and roughly a quarter to a third of records flip their 0.5-threshold decision. Excluding the two classifier-head `Gemm` nodes from quantization (C3c) barely moved the numbers (max diff 0.936 -> 0.936 on validation), so the degradation is coming from the encoder's MatMul quantization broadly, not the head. 52 calibration records is likely too few to capture good per-channel activation ranges for this graph; a much larger calibration set or per-tensor/asymmetric settings might help, but that is out of scope here. **C3a/b/c are rejected.**
- **C5 (FFN-only int8, optional)** was tried on the theory that skipping the attention Q/K/V/output-dense MatMuls (which dynamic quantization is more sensitive on) and only quantizing the larger FFN MatMuls would trade less size reduction for better agreement. It does not pay off: at 242 MB (only -26%) it still has a 0.41-0.61 max prob diff and 11-12/80-96 flips, worse agreement per MB saved than C1 (200 MB, -39%). Not recommended over C1, and neither is recommended for shipping (see below).

## Recommendation

**Ship candidate C4 (`models/shrink-4-fp16`, recalibrated copy `models/shrink-4-fp16-recal`).** It halves `model.onnx` (328.6 MB -> 164.4 MB, -50%), loads and runs cleanly under ONNX Runtime 1.22.1 CPU with no new/exotic ops, and its predictions are essentially indistinguishable from the float32 reference: 0 decision flips on all 176 combined validation+test records, and after recalibrating on the 52-record calibration split the fitted temperature comes back as *exactly* 1.1350108156723155 - the same value the float model was calibrated to - with max absolute probability difference of 0.001-0.002 and mean difference under 0.0002. In practice this means C4 can ship with the released manifest's existing temperature unchanged; recalibration is not even necessary, it just confirms the fp16 rounding is inconsequential. None of the int8 candidates (C1, C2, C3a/b/c, C5) are safe to ship as a drop-in replacement: all of them move individual probabilities well beyond what recalibration can fix (max diffs 0.32-0.94, with 6-27 decision flips out of 80-96 records even after recalibration), matching or exceeding the previously-rejected int8 attempt's 0.65 max movement. If more shrinkage than fp16's 50% is required, the next step would be revisiting static or dynamic int8 with a much larger calibration set and/or quantization-aware fine-tuning rather than post-hoc quantization of this checkpoint - none of the post-hoc int8 variants tried here are close enough to recommend.

## Exact commands used

```sh
# Float reference (identical to released/macos-arm64), used as the source bundle for every candidate
.venv/bin/decisiongate-train evaluate --bundle models/v2-nli-expanded --extra-data data/expansion-v2.jsonl \
  --split validation --output reports/shrink/float-validation.json
.venv/bin/decisiongate-train evaluate --bundle models/v2-nli-expanded --data data/evaluation-v2.jsonl \
  --split test --output reports/shrink/float-test.json

# C1: dynamic int8, MatMul/Gemm only
.venv/bin/decisiongate-train quantize --bundle models/v2-nli-expanded --output models/shrink-1-int8-matmul \
  --model-id decisionmodel-shrink-1-int8-matmul

# C2: dynamic int8, MatMul/Gemm + Gather/embeddings
.venv/bin/decisiongate-train quantize --bundle models/v2-nli-expanded --output models/shrink-2-int8-matmul-embed \
  --quantize-embeddings --model-id decisionmodel-shrink-2-int8-matmul-embed

# C3a/C3b/C3c: static QDQ int8 (custom script, calibrates on the 52-record calibration split)
.venv/bin/python reports/shrink/static_quantize.py models/shrink-3a-static-qdq-minmax minmax
.venv/bin/python reports/shrink/static_quantize.py models/shrink-3b-static-qdq-percentile percentile
.venv/bin/python reports/shrink/static_quantize.py models/shrink-3c-static-qdq-percentile-noclf percentile \
  --exclude-classifier

# C4: fp16 weight storage with Cast-to-float32 (custom script)
.venv/bin/python reports/shrink/fp16_convert.py
# (an earlier attempt used: uv run --with onnxconverter-common python -c "..." with
#  onnxconverter_common.float16.convert_float_to_float16(keep_io_types=True) - it failed to load; see above)

# C5 (optional): dynamic int8 restricted to the FFN MatMuls only (custom script)
.venv/bin/python reports/shrink/partial_int8.py

# For every candidate <name>: evaluate at the built-in temperature (reset to 1.0 by quantize()/our scripts)
.venv/bin/decisiongate-train evaluate --bundle models/<name> --extra-data data/expansion-v2.jsonl \
  --split validation --output reports/shrink/<name>-validation.json
.venv/bin/decisiongate-train evaluate --bundle models/<name> --data data/evaluation-v2.jsonl \
  --split test --output reports/shrink/<name>-test.json

# ...and a recalibrated copy of every candidate
cp models/<name>/model.onnx models/<name>/tokenizer.json models/<name>/manifest.json models/<name>-recal/
.venv/bin/decisiongate-train calibrate --bundle models/<name>-recal --extra-data data/expansion-v2.jsonl \
  --output reports/shrink/<name>-recal-calibration.json
.venv/bin/decisiongate-train evaluate --bundle models/<name>-recal --extra-data data/expansion-v2.jsonl \
  --split validation --output reports/shrink/<name>-recal-validation.json
.venv/bin/decisiongate-train evaluate --bundle models/<name>-recal --data data/evaluation-v2.jsonl \
  --split test --output reports/shrink/<name>-recal-test.json

# Merge every candidate's predictions against the float reference (max/mean abs diff, flips)
.venv/bin/python reports/shrink/compare.py
```
