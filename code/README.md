# Native builds

Build on each target machine: Mac arm64, Windows x64 with MSVC, or Linux x64 with glibc. The build helper refuses other hosts and toolchains. A successful Mac build does not establish Windows or Linux compatibility.

Use an existing exported model directory containing `manifest.json`, `model.onnx`, and `tokenizer.json`. Training and PyTorch are unnecessary on build machines. The build verifies both asset hashes before compiling.

## Prerequisites

- Install `uv` and `rustup` with the machine's package manager, or provide a matching existing Rust toolchain to the setup command below.
- Mac: Apple command-line tools.
- Linux: a C compiler and linker, typically the distribution's `build-essential` package, plus `binutils` for `readelf`. Build on the oldest glibc environment you intend to support; the recorded build-host glibc version is not a measured minimum.
- Windows: Visual Studio Build Tools with the C++ workload and Windows SDK, plus the Microsoft Visual C++ 2015–2022 x64 Redistributable required by ONNX Runtime. Run the build in an x64 Native Tools shell. The Rust DLL and ONNX Runtime both rely on normal Windows system/runtime libraries.

Set up Rust 1.98.1 inside this checkout:

```text
uv run code/setup.py
```

The helper uses rustup with project-local homes, then copies the matching toolchain into `tools/rust/`. It does not change global compiler settings. To copy an already installed matching toolchain instead:

```text
uv run code/setup.py --rust-from PATH_TO_TOOLCHAIN
```

The directory must contain `bin/rustc` and `bin/cargo` (`.exe` on Windows). Existing project tools are never overwritten. Downloaded tools and Cargo crates stay under `tools/`.

## Build without training dependencies

Choose a fresh output directory; the helper preserves existing bundles. These commands use a small isolated uv environment with ONNX Runtime, not the project's training group:

```text
uv run --python 3.12 --with onnxruntime==1.22.1 code/build.py --model MODEL_DIRECTORY --output released/macos-arm64
uv run --python 3.12 --with onnxruntime==1.22.1 code/build.py --model MODEL_DIRECTORY --output released/windows-x64
uv run --python 3.12 --with onnxruntime==1.22.1 code/build.py --model MODEL_DIRECTORY --output released/linux-x64
```

Use only the command matching the current host. On Windows, `code/windows_build.ps1 -Root C:\path\to\checkout` runs the whole sequence (MSVC environment, Rust setup, native build, relocation check, Python and Node packages) from an ordinary shell; its header explains how to start it detached over SSH. For an already downloaded official ONNX Runtime 1.22.1 CPU package, pass `--runtime-dir EXTRACTED_PACKAGE_DIRECTORY` and omit `--with onnxruntime==1.22.1`. The directory must contain the library under `lib/` (or `capi/`) and its `LICENSE` and `ThirdPartyNotices.txt`. An installed `onnxruntime` Python package directory also works. The helper checks the runtime's actual version and that it loads on this machine.

The build runs Rust tests, compiles the release library and a C host, then runs real inference and the native/Python checks. For the released model, it also checks the frozen platform comparison cases. A different model gets an explicit “not applicable” report until a matching reference is frozen. Only successful completion produces `build-checks.json`. A failed build may leave an incomplete output directory; inspect it and use a fresh destination for a retry. A separate network-denial check is still needed to establish offline behavior on a newly supported platform.

`system-dependencies.json` records linked libraries and binary compatibility metadata: Mac minimum OS versions, Linux GLIBC/GLIBCXX/CXXABI symbol requirements, or Windows DLL dependencies. These are compatibility floors, not evidence of testing on older operating systems. The Mac binaries inspected during development require macOS 13.3 because of ONNX Runtime; a wrapper supporting an older OS does not lower the bundle's requirement.

Windows bundles include `decisiongate.dll`, `decisiongate.lib` for C linking, and `onnxruntime.dll`. Linux bundles contain `libdecisiongate.so` and `libonnxruntime.so`; Mac bundles contain the corresponding `.dylib` files. All include the model, tokenizer, header, manifest, notices, and C smoke host. Runtime dependencies are copied when present. Loading the native component by absolute path allows automatic discovery of adjacent model files regardless of the application's working directory.

Do not dynamically unload the DecisionGate library: it retains its default session until process exit. Advanced session handles can be released and reloaded normally. Shut down inference threads before process exit and do not call DecisionGate from exit hooks.

On Windows, the operating system reclaims the default session and ONNX Runtime environment when the process terminates. The library deliberately avoids an `atexit` cleanup callback on Windows: DLL detach can occur after ONNX Runtime has detached and worker threads have stopped. Unix retains its explicit session/environment cleanup before runtime teardown. This difference does not affect `dg_release`, which releases an explicit session during normal execution.
