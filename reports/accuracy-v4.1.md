# Version 0.4.1: the 0.4.0 model, compressed, on every fast core

Version 0.4.1 ships the 0.4.0 weights stored as 8-bit and 4-bit integers instead of float16, and uses one thread per fast core instead of four. No weights were retrained. The download falls from 872 MB to 578 MB, a running process holds about 1.5 GB instead of 5.2 GB, native calls are faster, and held-out accuracy stays above 90%. How the compression was chosen is in [the quantization report](quantization/README.md); the thread change is in [the thread report](threads.md).

## Accuracy

Same held-out tests as [the 0.4.0 report](accuracy-v4.md), scored on the Mac with the fitted temperature (1.603).

| Test | 0.4.0 | 0.4.1 |
| --- | ---: | ---: |
| New test, 480 | 92.3% | 90.6% |
| Fresh test, 80 | 92.5% | 92.5% |
| Original test, 52 | 94.2% | 94.2% |
| Choice test, 20 | 95% | 90% |
| Spam test, 32 | 90.6% | 93.8% |
| Email test, 40 | 82.5% | 85.0% |

Log loss on the new test is 0.213 against 0.206. One case is 0.2 points on the new test and 5 points on the choice test.

## What the model is

Feed-forward output layers 6 to 17 and the word-embedding table use 4-bit weights in blocks of 32 (ONNX Runtime `MatMulNBits` and `GatherBlockQuantized`). Every other weight multiplication uses 8-bit weights with a 7-bit range and per-channel scales (`MatMulInteger`). Plain 8-bit everywhere dropped accuracy to 56%, because those middle layers carry a few very large activations. The 7-bit range avoids an overflow in older Intel processors' 8-bit instructions.

## Answers can differ slightly between platforms

Quantized arithmetic rounds differently on Apple silicon, Intel, and WebAssembly. Confident answers match; cases near 50% can come out on different sides. The release checks therefore allow a probability difference up to 0.25 and changed decisions on at most 5% of the comparison cases, recorded as `parity` in each bundle's `manifest.json`. Measured on the 87 browser comparison cases: largest difference 0.088, 2 changed decisions, in Chromium, Firefox, and WebKit. Over all 612 held-out cases, the Mac and the Intel Linux machine gave different decisions on 9 (1.5%) and both stayed above 90% on the new test.

## Speed and memory

Warm p50 per call on the M1 Pro with 8 threads: 115 ms at 96 tokens and about 300 ms at 256 tokens, against 121 and 322 ms for 0.4.0 on the same threads (535 ms at 256 tokens with 0.4.0's old four threads). Peak process memory 1.45 GB against 5.2 GB. On the Intel i7-10750H with 6 threads, short inputs take about half as long as with 0.4.0.

Browsers, 87 comparison cases on the M1 Pro:

| Browser | Isolated page, threaded | Not isolated, one thread |
| --- | ---: | ---: |
| Chromium | 257 ms | 676 ms |
| Firefox | 403 ms | 757 ms |
| WebKit (Playwright) | 146 ms | 682 ms |

Single-threaded browser calls are about 20% slower than 0.4.0's 570 ms because WebAssembly lacks fast 8-bit kernels; cross-origin isolation, described in the browser README, more than recovers it.

## Reproduce

```text
uv run --locked python training/quant/mixed_quant.py models/v4-large models/v4.1 6 17 --reduce-range
uv run --locked decisiongator-train calibrate --bundle models/v4.1 --output reports/v4.1/calibration.json <training --extra-data list>
uv run --python 3.12 --with onnxruntime==1.22.1 code/build.py --model models/v4.1 --output released/macos-arm64
```

`models/v4-large` is the float32 export of the 0.4.0 checkpoint. Evaluation reports are in `reports/v4.1/`.
