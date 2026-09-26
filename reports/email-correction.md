# Email-address correction experiment

The user's reported false positive is fixed in the retrained candidate: “I wish people would stop emailing me spam” now returns NO when asked whether an email address is embedded in the comment. All five of the user's example decisions are correct in the candidate. These five examples are development checks, not independent test evidence.

| Evaluation | Current | Retrained |
| --- | --- | --- |
| Independently authored email test | 26/40 | 32/40 |
| Existing newer general test | 59/80 | 61/80 |
| Existing original general test | 38/52 | 37/52 |

The candidate remains separate from the default release because the original general test lost one correct answer, failing the no-regression condition set before training. On that test, refund and timeline decisions regressed while coding routing improved. All three sets have better Brier scores (a measure of probability error) after retraining. These small synthetic collections cannot establish production accuracy or a statistically reliable improvement. The existing general tests have been used in earlier development; the email test was separately authored for this experiment without seeing training examples or outputs.

Training used the existing checkpoint plus [36 new training examples](../data/contributions/email-address-correction.jsonl), 12 validation examples, and 12 calibration examples. All 404 earlier training examples remained, for a total of 440. Ten epochs on the Mac GPU took about 94 seconds. The second epoch had the lowest combined validation log loss and was selected automatically; the held-out tests were evaluated only after that selection and calibration. No second trial or test-driven parameter tuning was performed.

The exported candidate is in `models/email-correction-v1/`, its retrainable checkpoint in `runs/email-correction-v1/best/`, and its working Mac native bundle in `models/email-correction-v1-macos/`. The native build passed six Rust tests, 144 ABI/Python checks, and C loading, inference, and clean exit. [Native/export comparison](email-correction-native-parity.json) checks all 40 email test probabilities. No Windows, Linux, browser, or Java release packages were replaced.

The editable Java example is `tmp/TryDecisionGator.java`; run it with `uv run --offline --no-project tmp/run_java.py`. It uses the current released Java package. To compare the current and retrained native versions using the question and text in `tmp/try_decisiongator.py`, run `uv run --offline --no-project tmp/compare_decisiongator.py`. These personal examples are gitignored.

## Reproduce

Choose new output directories when repeating these commands. Existing run and export directories are protected.

```sh
uv run --locked decisiongator-train validate --extra-data data/expansion-v2.jsonl --extra-data data/contributions/email-address-correction.jsonl
uv run --locked decisiongator-train train --start runs/v2-nli-expanded/best --extra-data data/expansion-v2.jsonl --extra-data data/contributions/email-address-correction.jsonl --learning-rate 0.00001 --epochs 10 --device mps --output runs/email-correction-v1
uv run --locked decisiongator-train export --checkpoint runs/email-correction-v1/best --output models/email-correction-v1 --model-id email-correction-v1
uv run --locked decisiongator-train calibrate --bundle models/email-correction-v1 --extra-data data/expansion-v2.jsonl --extra-data data/contributions/email-address-correction.jsonl --output reports/email-correction-calibration.json
uv run --locked decisiongator-train evaluate --bundle models/email-correction-v1 --data data/email-address-test.jsonl --split test --output reports/email-correction-after-email-test.json
uv run --locked decisiongator-train evaluate --bundle models/email-correction-v1 --data data/evaluation-v2.jsonl --split test --output reports/email-correction-after-general-test.json
uv run --locked decisiongator-train evaluate --bundle models/email-correction-v1 --split test --output reports/email-correction-after-old-test.json
uv run --with onnxruntime==1.22.1 code/build.py --model models/email-correction-v1 --output models/email-correction-v1-macos
```

The actual training command also set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` to use cached inputs. See [configuration](email-correction-config.json), [epoch history](email-correction-history.json), [comparison](email-correction-comparison.json), and [native build log](email-correction-native-build.log). The source checkpoint can be reproduced using [the earlier training recipe](../specs/accuracy-v2.md).
