# Research notes

Research date: 2026-09-17. These notes separate source claims from the project's proposed implementation.

## Video transcript

The automatically generated English transcript of [the supplied video](https://www.youtube.com/watch?v=QbZBaQNDP-o) was retrieved and read using `youtube-transcript-api`. Automatic captions contain transcription errors, including inconsistent spellings of Jev. The video is inspiration, not a technical specification of Jev's internals.

- Around 2:38–3:10, the video describes yes/no probability, selection among options, and ratings as three software-facing decision types. Only the first is in current scope.
- Around 3:15–3:38, the support-ticket example demonstrates giving a state and questions to a model, then branching in application code.
- Around 5:26–5:36, it discusses several questions evaluated together. This project does not assume that ordinary batching reproduces Jev's execution efficiency.
- Around 6:42–8:05, it distinguishes valid output types from correct answers and emphasizes testing the probability estimates on application data.

The video's discussion of adding a “none of the above” option concerns a possible choice-style escape route; it is not a separate output in this project's binary contract.

## Primary references

- [TypeSafe's Noul documentation](https://docs.typesafe.ai/primitives/noul): a yes/no question or proposition, optional true/false criteria, and one probability of yes. No separate confidence field. This is the closest public behavioral reference.
- [TypeSafe introduction](https://docs.typesafe.ai/introduction): state plus questions, small individual judgments, and composition in code. This motivates separating model inference from application policy.
- [TypeSafe launch post](https://typesafe.ai/blog/introducing-system-one-models-and-jev): describes a proprietary architecture, parallel sampler, and calibration-oriented training. Its speed and quality claims do not establish what a small locally trained model can achieve.
- [ONNX Runtime C documentation](https://onnxruntime.ai/docs/get-started/with-c.html): native loading and inference facilities supporting the proposed packaging experiment. This does not establish export compatibility for a model we have not selected.
- [PyTorch MPS documentation](https://docs.pytorch.org/docs/stable/notes/mps.html): Apple GPU backend relevant to local training. Compatibility and performance still require a pilot with the chosen architecture.
- [DeBERTa small NLI model card](https://huggingface.co/cross-encoder/nli-deberta-v3-small): a candidate pretrained baseline with contradiction, entailment, and neutral outputs. Its declared Apache-2.0 license is a starting point for review, not proof of rights to redistribute all upstream training data. Native question-format training and binary calibration remain necessary experiments.
- [GLiClass model card](https://huggingface.co/knowledgator/gliclass-modern-base-v2.0): an alternative text-and-label classifier worth comparing if the compact NLI baseline is inadequate. Custom-model export and total footprint need investigation.
- [ONNX Runtime quantization guidance](https://onnxruntime.ai/docs/performance/model-optimizations/quantization.html): transformer quantization options and the need to assess accuracy changes.
- [On Calibration of Modern Neural Networks](https://arxiv.org/abs/1706.04599): primary research supporting temperature scaling as an initial calibration experiment, without guaranteeing reliability on new domains.

## Decisions still requiring evidence

Choose the pretrained checkpoint, tokenizer, input length, training dataset, deployment precision, and calibration method after baseline experiments. Determine whether a compact encoder can understand sufficiently varied runtime questions before committing to its footprint. Determine actual local training time through profiling. Set supported-domain claims from held-out results, not architecture names.

Reproducing a public input/output pattern is feasible to investigate. Matching Jev's competence, calibration, latency, or internal method has not been demonstrated and is not implied by these specifications.
