# Release bundles

This directory holds installable local DecisionGate releases. Every target uses the same full-precision weights, tokenizer, input rules, and calibration. Packaging does not improve or reduce decision accuracy: the current version answered 59/80 fresh synthetic cases correctly. See [the accuracy report](../reports/accuracy-v2.md).

Native bundles:

| Platform | Bundle directory | Native library |
| --- | --- | --- |
| Windows x64 | `windows-x64/` | `decisiongate.dll` |
| Mac M1 and newer (Apple silicon) | `macos-arm64/` | `libdecisiongate.dylib` |
| Linux x64, glibc | `linux-x64/` | `libdecisiongate.so` (ELF) |

Each native bundle contains the component, its CPU runtime, weights, tokenizer, C header, checksums, and license notices. Windows packaging also includes the import library for C applications. No separate inference service or consumer-side compiler is needed.

The Mac build is tested on Apple silicon with macOS 26.6.2. Binary metadata requires macOS 13.3 or later; the Python wheel conservatively targets macOS 14+. The Linux build is tested on emeraldslate, an Omarchy Linux x64 machine with glibc 2.44. Its symbols require glibc 2.34+, GLIBCXX 3.4.22+, and CXXABI 1.3.11+, plus the system libraries listed in `linux-x64/system-dependencies.json`. Those minimum symbol versions do not mean every older distribution has been tested. The Windows DLL is built and tested on Windows 11 x64, build 26200, in emeraldslate's existing `omarchy-windows` guest. It requires the Microsoft Visual C++ 2015-2022 x64 Redistributable. Older Windows releases have not been tested.

Build each native bundle on its own platform with [the portable build helper](../code/README.md). Alpine/musl, Linux ARM, Intel Macs, Windows ARM, and mobile devices are outside this release's tested scope.

The [Windows verification report](../reports/windows-release.md) records native, Python, Node, and Java checks, cross-platform agreement, and deployment requirements.

## Language packages

- [Python wheels](python/README.md) include all native assets and have no Python runtime dependencies.
- [Java JARs](../java/README.md) provide an ordinary Java 17 API, platform classifier bundles, sources, and Javadoc. JNA is a normal transitive dependency.
- [Node.js packages](../javascript/README.md) include a Node-API addon, JavaScript/TypeScript interfaces, native assets, and the browser entry. Install the tarball matching the operating system and architecture.
- [Browser assets](../web/README.md) include the WebAssembly runtime, worker, declarations, weights, tokenizer, and an offline-capable example. Copy `web/` into your application's assets. Chromium, Firefox, and WebKit engines passed real inference and offline tests on the Mac.

The browser bundle is approximately 345 MB; the Mac native bundle is approximately 394 MB and Linux native bundle approximately 359 MB. The combined npm tarball contains separate native and browser assets, including two copies of the weights, so it is larger. Browser use requires the web app's initial asset delivery and sufficient storage for offline installation. See [browser measurements and limitations](../reports/browser-webassembly.md).

Binary hosting is undecided. Git LFS, release downloads, or a separate website can be considered after the local version works. This directory defines the local release layout regardless of the eventual download service; it does not require committing large binaries to ordinary Git.

No artifacts have been published to PyPI, Maven Central, npm, or a public download host. Local installation and packaging are implemented independently of that future publishing decision.
