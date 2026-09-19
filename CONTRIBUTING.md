# Contributing to DecisionGate

The most valuable contribution is a wrong answer with the right answer attached. You do not need a GPU or machine-learning experience. This page is the short path; [the open training specification](specs/open-training.md) has the full rules.

## 1. Clone and get the prebuilt component

```text
git clone https://github.com/freeideas/DecisionGate.git
cd DecisionGate
uv run code/fetch_released.py --only macos-arm64    # or linux-x64, windows-x64, web, python, java, node
```

The prebuilt bundles are too large for GitHub, so they are downloaded from `https://ordinarydata.com/DecisionGate/files/` and verified by checksum into `released/`. After that, [EXAMPLE_USAGE.md](EXAMPLE_USAGE.md) shows the calls in every language and `uv run examples/python_smoke.py` proves it works.

## 2. Record the wrong answer

Copy [data/contributions/example-correction.jsonl](data/contributions/example-correction.jsonl) to a new file under `data/contributions/` and edit it. Each line is one example with the content, the question, optional criteria, the correct label, and a one-sentence rationale. Use only text you have the right to publish; never paste real customer data. The [data guide](data/README.md) explains every field.

Check it:

```text
uv run --locked decisiongate-train validate --extra-data data/contributions/my-fix.jsonl
```

## 3. Retrain locally

Start from the current release checkpoint and add your file. Training runs on an ordinary laptop CPU; the recipe and timings are in [the v0.3 report](reports/accuracy-v3.md).

```text
uv run --locked decisiongate-train train \
  --base cross-encoder/nli-MiniLM2-L6-H768 --revision b95119ce93d3e065de6214e38cd4a97b0f2f2c6d \
  --nli-head --template 2 --learning-rate 1e-5 --epochs 10 \
  --extra-data data/expansion-v2.jsonl --extra-data data/choices.jsonl \
  --extra-data data/contributions/my-fix.jsonl \
  --output runs/my-fix
uv run --locked decisiongate-train export --checkpoint runs/my-fix/best --output models/my-fix --model-id my-fix
uv run --locked decisiongate-train calibrate --bundle models/my-fix --extra-data data/expansion-v2.jsonl --extra-data data/choices.jsonl --output reports/my-fix-calibration.json
uv run --locked decisiongate-train evaluate --bundle models/my-fix --data data/evaluation-v2.jsonl --split test --output reports/my-fix-test.json
```

Then build a native bundle for your platform and use it from your language of choice; see [native builds](code/README.md). Point `DECISIONGATE_BUNDLE` at the new bundle to test it without replacing the release.

You can stop here and ship your private variant. Nothing is uploaded anywhere.

## 4. Send the examples back

Open a pull request that adds your `data/contributions/*.jsonl` file and a short `.md` note beside it saying where the examples came from and what they fix. Include the before and after numbers from the evaluate step if you have them. Do not include trained weights or bundles in the pull request; maintainers retrain from the merged data, run the release checks, and publish new bundles with `code/publish_released.py`.

Reviewers check the rights statement, the question wording, the label, and whether the new examples overlap the evaluation sets. A correction that helps one family but hurts another is still welcome; just report both.

## Code changes

Code is Apache-2.0. Keep the C interface in `code/include/decisiongate.h` and every language wrapper in agreement; `tests/` and the per-language READMEs describe the checks each change must pass. Run the smoke tests for any language you touch before opening the pull request.
