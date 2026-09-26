# Laya trial: not adopted

Laya (`convaiinnovations/laya`, Apache-2.0, ModernBERT-large encoder plus a two-layer decision head, 421M parameters, package version 0.3.7) was tried as a replacement foundation for version 0.4.0 on 2026-09-23. It was less accurate on every held-out test after fine-tuning on the same data, and it was no faster on a laptop CPU. The shipped DeBERTa-v3-large model stays.

## Accuracy

Held-out tests are the same ones used in [the v0.4 report](../accuracy-v4.md). Training data, splits, and checkpoint selection (lowest validation log loss) match the 0.4.0 recipe.

| Model | New test, 480 | Fresh, 80 | Original, 52 | Choice, 20 |
| --- | ---: | ---: | ---: | ---: |
| 0.4.0 shipped, DeBERTa-v3-large | 92.3% | 92.5% | 94.2% | 95% |
| Laya as downloaded, no training | 69.0% | 80.0% | 57.7% | 70% |
| Laya, whole model fine-tuned, its own head | 80.8% | 86.3% | 86.5% | 65% |
| Laya encoder, DecisionGator head, lr 1e-5 | 79.8% | 83.8% | 84.6% | 85% |
| Laya encoder, DecisionGator head, lr 3e-5 | 79.8% | 90.0% | 80.8% | 90% |

Validation accuracy told the same story before any test was scored: 81 to 86% for every Laya run against 93 to 95% for DeBERTa-v3-large. The whole-model run kept Laya's input format (question, option markers, then content) and trained with cross-entropy over the option markers, which is the log-score part of Laya's own training rule. Its weakest families on the new test were permissions (63%), eligibility, numeric criteria, and urgency (70%).

The likely reason is the starting point, not the head: 0.4.0 starts from a DeBERTa-v3-large already trained on natural-language-inference data, which is close to "does this text satisfy this rule". Laya's encoder has seen far less of that kind of reasoning.

## Speed

Laya's published 33 ms is a GPU figure. On the M1 Pro CPU with ONNX Runtime 1.22.1, four threads, a 256-token input, and 200 warm calls:

| Model | p50 | p95 |
| --- | ---: | ---: |
| 0.4.0 DeBERTa-v3-large, float32 ONNX | 543 ms | 584 ms |
| Laya encoder, eager attention export | 548 ms | 606 ms |
| Laya encoder, SDPA attention export | 556 ms | 596 ms |

ModernBERT's speed advantage comes mainly from GPU kernels and from skipping padding. At 256 tokens on a CPU its 28 layers cost about the same as DeBERTa's 24. The exported ONNX file was 1.58 GB in float32, a little smaller than DeBERTa's 1.74 GB.

## What changed in the code

`training/pipeline.py` now drops segment ids for encoders whose forward call does not accept them, so ModernBERT-family foundations can be trained and exported with the normal commands. The trial scripts are in `training/laya/`; they ran on a Colab A100 from `/content/dg` and are kept for reproduction, not as part of the release pipeline.
