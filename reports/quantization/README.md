# Compressing the 0.4.0 model to 8-bit and 4-bit weights

Experiment, 2026-09-23. The goal was a smaller, faster model that keeps held-out accuracy above 90%. The best version is 34% smaller, uses about a quarter of the memory, and keeps accuracy above 90%. It is faster natively, slightly slower in browsers, and no longer gives bit-identical answers on every platform. Nothing here has been released.

## What was tried

| Version | Main, 480 | Fresh, 80 | Original, 52 | Choice, 20 | File |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.4.0 shipped, float16 storage | 92.3% | 92.5% | 94.2% | 95% | 872 MB |
| Every layer 8-bit | 55.8% | 68.8% | 61.5% | 80% | 1,036 MB |
| 8-bit, feed-forward output of layers 6-17 kept float | 90.8% | 93.8% | 94.2% | 90% | 1,191 MB |
| Same, word table also 8-bit | 91.7% | 91.3% | 94.2% | 85% | 797 MB |
| Every layer 4-bit in blocks of 32 | 91.2% | 92.5% | 94.2% | 90% | 482 MB |
| **Combined:** 8-bit, with layers 6-17 and the word table 4-bit | 91.5% | 93.8% | 94.2% | 95% | 578 MB |

Scores are on the Mac after refitting the calibration temperature for each version. One case is 0.2 points on the main test, 1.3 on the fresh test, and 5 on the choice test.

**Why plain 8-bit failed.** Quantizing one layer type at a time (`training/quant/int8_scan.py`) showed that only the feed-forward output layers break, and only in layers 6 to 17: quantizing layers 12 to 17 alone dropped validation accuracy from 96.9% to 67.5%. Their inputs contain a few very large values, and 8-bit dynamic quantization uses one scale for a whole row of activations, so everything else is rounded to nothing. Block-wise 4-bit weights with block-wise activation scaling cope with this.

## Speed and memory

Warm p50 per call, 8 threads on the Mac and 6 on Linux. Memory is the process peak.

| Version | Mac, 96 tokens | Mac, 256 | Intel i7-10750H, 96 | Intel, 256 | Mac memory |
| --- | ---: | ---: | ---: | ---: | ---: |
| Shipped | 121 ms | 322 ms | 1,126 ms | 1,853 ms | 5.2 GB |
| Combined | 103 ms | 277 ms | about 540 ms | about 1,500 ms | 1.45 GB |
| 4-bit only | 120 ms | 324 ms | 814 ms | 2,201 ms | 1.35 GB |

The Intel figures for the combined version are from the 8-bit-with-float-layers version, which uses the same fast kernels. Apple silicon already multiplies floats quickly, so 8-bit gains less there. The shipped model's memory is high because ONNX Runtime keeps a float32 copy of every float16 weight.

In browsers with threads enabled, the combined version ran at 226 ms in Chromium, 131 ms in WebKit, and 356 ms in Firefox, against 188, 119, and 317 ms for the shipped model. Its download is 578 MB instead of 872 MB.

## The catch: platforms no longer agree exactly

Float models give the same probabilities on every platform to within 0.0001, and the release checks require that. Quantized arithmetic rounds differently on Apple, Intel, and WebAssembly:

- Mac against browser, 87 comparison cases: largest difference 0.09, one decision flipped.
- Mac against Linux, same cases: largest difference 0.24, three decisions flipped.
- With 7-bit weight range (`--reduce-range`), which avoids an overflow in older Intel instructions: largest difference 0.13, one flip in 87. Over all 612 held-out cases, 9 decisions differ; Mac scores 90.6% on the main test and Linux 91.0%.

The disagreements are cases the model is unsure about. Accuracy stays above 90% on each platform, but the same input can get a different answer on different platforms.

## Reproduce

```text
uv run --locked python training/quant/mixed_quant.py models/v4-large models/v4-large-mixed 6 17 [--reduce-range]
uv run --locked decisiongate-train calibrate --bundle models/v4-large-mixed --output reports/quantization/mixed-calibration.json <training --extra-data list>
uv run --locked decisiongate-train evaluate --bundle models/v4-large-mixed --data data/v4/test-1.jsonl ... --split test --output ...
```

`decisiongate-train quantize` gained `--keep-float FRAGMENT` for 8-bit with chosen layers left float. `training/quant/` also holds the 4-bit script, the layer scan, the CPU benchmark, a standalone scorer used on Linux, and a quick browser timing script. `web/build.mjs` accepts `DECISIONGATE_NATIVE_DIR` to stage a browser build from another bundle.
