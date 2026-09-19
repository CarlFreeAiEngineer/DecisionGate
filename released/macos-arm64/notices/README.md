# Third-party materials

The current v0.2 model is derived from `cross-encoder/nli-MiniLM2-L6-H768` at revision `b95119ce93d3e065de6214e38cd4a97b0f2f2c6d`, whose model card declares Apache-2.0. The model card and Apache license are included here. DecisionGate changes its classification head and fine-tunes its weights on the published project examples. Current derived weights retain Apache-2.0 terms; the older foundation described below applies to the v0.1 model. Project code is Apache-2.0. No claim is made that this repository contains the complete upstream pretraining or NLI training corpus.

The original v0.1 foundation is `microsoft/MiniLM-L12-H384-uncased` at revision `44acabbec0ef496f6dbc93adadea57f376b7c0ec`. Its model card declares MIT; the upstream UniLM MIT license and model card are preserved here. These notices do not assert that the upstream pretraining corpus is available.

The local bundle includes ONNX Runtime 1.22.1's MIT license and third-party notices. `code/build.py` also collects license/notice files for locally available locked Rust dependencies into each bundle. Review that inventory before a public distribution; this prototype is not a completed release audit.

Project source is Apache-2.0. Original example data is offered under the CC0 terms described in `data/README.md`. Fine-tuned weights retain their respective base model's terms (MIT for v0.1, Apache-2.0 for v0.2); the training recipe and exact source checkpoint are recorded with the bundle and reports.
