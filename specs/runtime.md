# Runtime and distribution

## Native delivery

Implement the native component in Rust with a C-compatible interface. Use the project-local toolchain and native platform builds described in [development.md](development.md).

The preferred first experiment is ONNX export with ONNX Runtime CPU inference behind a small C-compatible interface. ONNX is a portable model representation; ONNX Runtime executes it. Verify the selected model's operators, tokenizer integration, export fidelity, and quantization support before committing to this route.

The release bundle contains the native library, required runtime dependencies, model weights, tokenizer assets, calibration parameters, manifest, and notices. Ordinary adjacent files are the default. Embedding weights into a single library is optional later work; it is not required to provide an in-process component.

The product promise is an ordinary software component, comparable in integration style to a traditional native library. No Ollama, llama.cpp, agent harness, separate model-runner installation, or server process is part of the deployment. The necessary inference engine is an internal bundled dependency, not something the application user must operate. This does not promise a single dependency-free file or a 1990s-sized memory footprint. Any future architecture choice must preserve this integration requirement.

Build `.dll`, `.so`, and `.dylib` packages for the supported OS/processor combinations. One shared interface does not mean one binary runs everywhere. Publish minimum OS versions, CPU instruction requirements, and measured memory use for each supported build. CPU inference must work without GPU drivers. Acceleration may be added transparently, with a tested CPU path retained.

The three native targets are Windows x64 (MSVC), Mac M1 and newer (arm64), and Linux x64 with glibc (ELF shared library). Stage their bundles in [released/](../released/README.md), building and testing each on its own platform. The release inventory records tested systems and packages. Binary hosting and large-file storage remain separate publishing decisions.

## Interface requirements

The native interface must provide explicit load, evaluate, metadata, and release operations using opaque model handles. Specify ownership of handles, strings, and output buffers; do not expose C++ objects, exceptions, or allocator ownership across the boundary. Use length-delimited UTF-8 input, fixed-width status codes, and a documented floating-point result type.

Report load, compatibility, input, resource, and inference errors separately. Never return success with NaN, infinity, or an out-of-range value. A caller must be able to distinguish an ordinary negative prediction from a failed operation.

Define thread-safety before release. At minimum, separate model handles must be usable independently; document whether calls on one handle are serialized or concurrent. Each inference uses one thread per fast physical core: performance cores only on chips that mix fast and slow cores, and no hyperthreads, because ONNX Runtime splits every operation evenly and one slow thread holds up the rest. The `DECISIONGATOR_THREADS` environment variable, read when a model loads, sets a different count so the component can coexist with its host application. Make resource release explicit and test repeated load/unload cycles.

A Python binding is the first convenience layer and must preserve the native semantics. Other language bindings follow the same interface. The deployed native package must not require Python, PyTorch, a shell process, or a local HTTP server.

### Experimental C surface

The README's C example uses the following declarations. The implemented [header](../code/include/decisiongator.h) defines criteria, status codes, metadata, ownership, and lifetime rules. The interface remains experimental rather than a stable binary contract. The Mac prototype requires the library to remain loaded until process exit; individual model handles can be released normally.

```c
#include <stddef.h>
#include <stdint.h>

typedef struct dg_session dg_session;
typedef struct dg_criteria dg_criteria;
typedef int32_t dg_status;
#define DG_OK 0

dg_status dg_load(
    const char *path, size_t path_bytes, dg_session **out_model);
dg_status dg_evaluate(
    dg_session *model,
    const char *content, size_t content_bytes,
    const char *question, size_t question_bytes,
    const dg_criteria *criteria, double *out_p_yes);
void dg_release(dg_session *model);
```

Lengths are byte counts excluding any terminating NUL. Strings are borrowed for the duration of the synchronous call; the library does not retain their pointers. Paths use UTF-8 on every platform and reject embedded NUL bytes. On load failure, `*out_model` is set to null; on success, the caller owns the handle until `dg_release`. Releasing a null handle is harmless. A null criteria pointer means criteria are omitted. `out_p_yes` is written only on success and must not be read after a failed evaluation. Probability results use an IEEE 754 binary64 `double` on supported targets. A loaded handle can serve repeated evaluations without reloading weights.

## Fully offline operation

All runtime assets are supplied by the application. Disable telemetry, remote fallback, license-server checks, automatic updates, and lazy downloads in the component and its dependencies. Verify loading and inference with networking denied. Do not log input text by default.

A bundle manifest records format version, model identifier, checkpoint revision, tokenizer hash, input encoding/template version, maximum token count, calibration version, tensor precision, runtime compatibility, asset hashes, and license identifiers. Reject incompatible or incomplete bundles explicitly. Model updates are deliberate application releases, never silent replacements.

Tokenizer and input-template parity are as important as tensor parity. Test Unicode, whitespace, separators, criteria ordering, and token limits against the training pipeline. Reserve stable fixtures for these checks.

## Size and licensing

Investigate integer quantization to reduce weight size and CPU cost. Quantization is accepted only after measuring output changes and rerunning decision and calibration tests. Publish total installed bundle size, weight size, and peak resident memory separately.

The intended product permits royalty-free commercial embedding and redistribution. Before selecting a checkpoint or shipping, record the licenses and obligations for code, base weights, fine-tuned weights, tokenizer, runtime, and training datasets. An open repository or downloadable checkpoint alone is not sufficient evidence. Choose the project's license explicitly before the first release and include required notices. “No per-call fee” does not imply zero training, storage, electricity, or maintenance cost.

## Planned JavaScript targets

Node.js will wrap the native component; browser WebAssembly needs a separate runtime integration using the same weights and decision semantics. Neither is implemented. Proposed release directories are `released/node/` and `released/web/`; they do not imply additional native OS support. See [the implementation and validation plan](javascript-and-webassembly.md).
