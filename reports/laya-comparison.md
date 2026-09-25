# DecisionGate 0.4.1 against Laya, on the same tests and the same CPU

Laya (Convai Innovations, Apache-2.0, released 2026-09-18) is an open decision model that answers yes/no, choice, and score questions. We ran its three published checkpoints and DecisionGate 0.4.1 over DecisionGate's held-out tests on one M1 Pro, CPU only, one call at a time.

## Results

| Model | New test, 480 | Fresh test, 80 | Choice test, 20 | Time per call (new / fresh / choice) |
| --- | ---: | ---: | ---: | ---: |
| DecisionGate 0.4.1 | 90.6% | 92.5% | 90% | 80 / 55 / 222 ms |
| Laya English | 69.0% | 78.8% | 70% | 123 / 105 / 107 ms |
| Laya typed-decisions | 69.2% | 81.2% | 65% | 125 / 106 / 108 ms |
| Laya multilingual | 54.0% | 61.3% | 70% | 52 / 46 / 45 ms |

Times are the median per call. On yes/no questions DecisionGate is more accurate than every Laya checkpoint and faster than the two English ones. The multilingual checkpoint is faster but close to a coin toss on the 480-case test. On choice questions Laya is faster, because it scores all options in one pass while DecisionGate checks each option.

DecisionGate led in all sixteen task families of the 480-case test except one, where it tied (evidence presence, 27 of 30 each). Per-family counts are in [laya/results.json](laya/results.json).

## How fair is this

- **The tests are ours.** They were written for DecisionGate's style of question, and DecisionGate was trained on separately written examples from the same sixteen families. Laya was not tuned for them. Laya's own reported figure, 76.6% for the typed-decisions checkpoint on its 400-case benchmark, was not re-run here.
- **Laya was given the same information.** The question became Laya's `instructions`, and the yes/no criteria, when a case had them, became its `true` and `false` criteria. For choice cases each option's name was also its description, since the tests have no separate descriptions. Both models used a 0.5 threshold with no tuning.
- **Different runtimes.** Laya ran in PyTorch 2.14 with 32-bit weights; DecisionGate ran its shipped native library with 8-bit and 4-bit weights. That is how each is delivered. Laya's GPU and batched modes, which it advertises as much faster, were not measured.
- **One machine.** Apple M1 Pro, default thread settings for both. Other processors will give other times.

## Reproduce

```text
uv run code/compare_laya.py
```

It uses laya 0.3.20, downloads the Laya weights from Hugging Face on first use, uses DecisionGate from `released/<platform>`, and writes [laya/results.json](laya/results.json). The run took about 20 minutes.
