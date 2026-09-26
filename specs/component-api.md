# Ordinary component interfaces

The default application interface is a function call. Callers should not need a model path, a load operation, or cleanup for ordinary use. Keep explicit sessions for custom bundles, metadata, independent sessions, and applications with deliberate memory-management requirements.

- Python: `decisiongator.is_yes_p(content, question, criteria=None)` lazily creates one synchronized session. Find assets in `decisiongator/_bundle`, with a checkout-only fallback to `released/<platform>` relative to the package, never the working directory. Python closes its shared session at interpreter shutdown. Packaged platform wheels are not built yet.
- C: `dg_is_yes_p(content, content_bytes, question, question_bytes, criteria, out_p_yes)` uses the component's adjacent bundle and a shared session. Return a status separately from the output probability; initialization and input failures must never become a negative answer.
- Java: `Decisions.isYesP(content, question)` and its typed `Criteria` overload use a shared bundled session. The API JAR has a normal JNA dependency; a separate platform classifier JAR supplies all native assets. Java applications write no JNI. See [Java packaging and usage](../java/README.md).

Initialization happens on the first call and may take longer than later calls. Serialize initialization and access to the shared session. A failed initialization must allow a later retry. No interface downloads missing assets. Shared sessions retain native memory for the process lifetime; explicit sessions can release their inference memory earlier. Native libraries must remain loaded until process exit, and inference must finish before shutdown. Hot class-loader unloading is unsupported.

The simple API does not change probability semantics, model accuracy, supported inputs, or thresholds. Keep the experimental status visible in documentation rather than repeating loading instructions in every application example.

Validation includes concurrent Python first use, initialization failure/retry, calls from a different working directory, native error behavior, Java unit/integration tests, and packaged inference with networking denied. Mac arm64 and Linux x64 have passed real native and language-package checks. Consult [the release inventory](../released/README.md) for current platform qualification, and [the JavaScript specification](javascript-and-webassembly.md) for Node.js and browser validation.

## Probability and boolean names

`P` means probability of yes. Python `is_yes_p`, Java `Decisions.isYesP`, and C `dg_is_yes_p` return the same probability as the explicit session evaluation API. The earlier prototype `probability` names have been replaced; rebuild consumers against the matching library and header.

Python `is_yes(content, question, criteria=None, *, threshold=0.5)` and Java `Decisions.isYes(content, question[, criteria][, threshold])` return a boolean using `p_yes >= threshold`. C `dg_is_yes` uses 0.5; `dg_is_yes_at_threshold` takes an explicit `double threshold` immediately before its `uint8_t *out_yes`. C writes 0 or 1 only on success and returns status separately. Outputs remain unchanged on any error.

Thresholds must be finite and in [0, 1], including both endpoints. Equality returns true. Invalid thresholds are rejected before initialization: Python raises `ValueError`, Java raises `IllegalArgumentException`, and C returns `DG_INVALID_ARGUMENT`. Loading, validation, and inference errors propagate normally; none are converted into false. The convenience threshold is a caller policy, not a new model or an accuracy guarantee. Applications needing an uncertain/review range should use the probability API.

## Choice names

`choose_p` ranks caller-supplied options and `choose` returns only the top index. Python `choose_p(content, question, options, criteria=None)` returns a list of `(index, probability)` tuples, best first; `choose(..., *, threshold=0.0)` returns an `int` or `None`. Java `Decisions.chooseP(content, question, options[, criteria])` returns an unmodifiable `List<Choice>` where `Choice` has `index()` and `p()`; `Decisions.choose(...)` returns `int`, with `-1` when the top probability is below the threshold overload. JavaScript `chooseP` resolves to `{ index, p }[]` and `choose` to a number, `-1` when deferred. C `dg_choose_p` and `dg_evaluate_choice` take the options as a pointer array plus a byte-length array and write caller-owned `int32_t` index and `double` probability arrays of `option_count` entries in rank order; `dg_choose` writes the index or `-1`. The library never allocates output memory, so there is nothing to free, and nothing is written on error. Explicit-session forms are Python `Session.evaluate_choice`, Java `DecisionGator.evaluateChoice`, and C `dg_evaluate_choice`.

Options must number at least two and each must be nonempty; every option prompt must fit the token limit. Invalid thresholds are rejected exactly as for the boolean calls. Validation, initialization, and inference errors propagate; a partial ranking is never returned. See [behavior](behavior.md) for the probability definition.

## Product identity

The product is **DecisionGator**, with the tagline **“Your software probably needs this.”** Describe it to application developers as an ordinary software component: include it, call a function, use the answer. Automatic initialization and simple boolean calls are part of that promise. Explain the learned implementation, training, and measured limits honestly where they matter; do not make model management the normal user experience.

Public names now use `decisiongator` for the Python package and training command, `org.decisiongator` and `decisiongator-java` for Java, `libdecisiongator` / `decisiongator.dll` for native binaries, and `dg_` / `DG_` for the C API. Python's explicit handle is `Session`; Java's is `DecisionGator`; C's is `dg_session`. Rebuild consumers with the matching package, header, and binary. No compatibility aliases are provided for the unpublished prototype.

Historical reports, data provenance, upstream identities, copyright notices, and saved experiment paths retain their original names. Existing checkpoint config keys beginning with `decisionmodel_` remain readable for reproducibility; `model.onnx` and manifest fields such as `model_id` describe the actual learned artifact and retain their technical names. The checkout directory itself need not be renamed.
