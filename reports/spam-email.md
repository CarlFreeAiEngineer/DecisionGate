# Combined spam and email retraining

Completed on 17 September 2026. The local Java example now uses the retrained candidate. Its answers to the user's six comments are NO, YES, NO, NO, YES, YES. It fixes the two clear spam misses; the fifth answer concerns the agreed borderline personal invitation and is not counted as a known correct label. These examples inspired training material and are development checks, not independent evidence of generalization.

Run `uv run --offline --no-project tmp/run_java.py` to use the candidate, or add `--released` to compare with the original release. Edit `tmp/TryDecisionGator.java` as before. The Java source itself was not changed. The candidate JARs are in `models/spam-email-v1-java/`, and the native Mac bundle is in `models/spam-email-v1-macos/`. Existing `released/` packages and the ordinary Python example still use the original version. The temporary Python comparison script from the earlier experiment still compares against the email-only candidate.

## Evaluation

| Synthetic evaluation | Original release | Retrained |
| --- | --- | --- |
| Spam-like comments | 14/32 | 17/32 |
| Email-address presence | 26/40 | 33/40 |
| Newer general test | 59/80 | 61/80 |
| Original general test | 38/52 | 38/52 |

All four probability-error scores improved. The candidate met this experiment's predeclared comparison conditions and was selected for the local Java example, not promoted to a coordinated cross-platform release. General-test totals conceal individual changes: event decisions fell from 7/7 to 6/7 on the newer test, and refund decisions from 3/4 to 2/4 on the original test. See [the comparison](spam-email-comparison.json) for scores and regressions.

Spam performance remains poor: 17/32 is only one correct answer above the balanced constant-answer baseline. Clear spam cases improved from 10/24 to 13/24. Explicit-policy answers remained 4/8, with none of the four policy pairs fully correct. The candidate has not demonstrated reliable adherence to the distinction between broad solicitation rules and commercial-promotion-only rules. Its performance on the user's familiar examples should not be mistaken for general spam-filter quality.

The earlier email error is also corrected: “I wish people would stop emailing me spam” receives an email-address YES probability of about 0.035. [Native fixtures](spam-email-native-fixtures.json) include the exact Java-example probabilities and this correction.

## Training and verification

One fixed run continued from `runs/v2-nli-expanded/best` with all original examples, `data/expansion-v2.jsonl`, and both email-address and spam contributions. It used 488 training, 124 validation, and 80 calibration records. Ten epochs took about 102 seconds on the Mac GPU. Epoch two had the lowest combined validation log loss and was selected before test evaluation, then calibrated using only calibration records. No further trial or test-driven parameter tuning was performed. The spam test was newly evaluated; email and general tests had previous development exposure. All data is synthetic and unreviewed.

The native build passed six Rust tests, 144 ABI/Python checks, and C loading, inference, and clean exit. The [native/export comparison](spam-email-native-parity.json) passed all 72 spam and email cases. Java passed all 13 tests with fixture probabilities independently obtained through the native Python interface. The [packaged Java consumer](spam-email-java-consumer.json) matched all six user-example probabilities, with network access and reads of the original native bundle directories blocked by the macOS sandbox.

Java's build helper now accepts `--output` for an isolated artifact directory and paired expected-probability arguments for alternate-weight integration tests. Original release expectations remain the defaults. A different candidate must provide its own independently measured fixture values, not reuse this run's numbers.

## Reproduce

Use new output paths for another run. The actual training command also set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1`; the existing checkpoint and dependencies were cached locally.

```sh
uv run --locked decisiongator-train train --start runs/v2-nli-expanded/best --extra-data data/expansion-v2.jsonl --extra-data data/contributions/email-address-correction.jsonl --extra-data data/contributions/spam-comments.jsonl --learning-rate 0.00001 --epochs 10 --device mps --output runs/spam-email-v1
uv run --locked decisiongator-train export --checkpoint runs/spam-email-v1/best --output models/spam-email-v1 --model-id spam-email-v1
uv run --locked decisiongator-train calibrate --bundle models/spam-email-v1 --extra-data data/expansion-v2.jsonl --extra-data data/contributions/email-address-correction.jsonl --extra-data data/contributions/spam-comments.jsonl --output reports/spam-email-calibration.json
uv run --with onnxruntime==1.22.1 code/build.py --model models/spam-email-v1 --output models/spam-email-v1-macos
uv run java/build.py --bundle models/spam-email-v1-macos --output models/spam-email-v1-java --expected-probability 0.986122636194813 --expected-unicode-probability 0.29462769048942045
```

Evaluate each test separately with `decisiongator-train evaluate --bundle models/spam-email-v1 --data PATH --split test --output REPORT`: use `data/spam-comments-test.jsonl`, `data/email-address-test.jsonl`, or `data/evaluation-v2.jsonl`; omit `--data` for the original test. The unchanged original release provides the baseline. See [plan](spam-email-plan.md), [configuration](spam-email-config.json), [epoch history](spam-email-history.json), [native build log](spam-email-native-build.log), and [Java build log](spam-email-java-build.log).
