# Windows release verification

Version 0.4.0 was rebuilt and verified on 19 and 20 September 2026 in the same Windows 11 x64 guest on emeraldslate (build 26200, two virtual CPUs, 4 GB RAM) with MSVC 14.44 and the project-local Rust 1.98.1 toolchain. The native bundle passes eight Rust unit tests, 168 native ABI/Python checks, C host loading, inference, and clean exit, and all 81 frozen comparison cases agree with the reference decisions (largest probability difference 0.00000085). The relocation check and the Python 3.12 wheel check pass. The Node 24.19.0 package and the Java classifier JAR checks are recorded in their JSON reports alongside this file.

The 0.4.0 model needs about 5 GB of process memory, more than the guest's 4 GB of RAM. The first 0.4.0 attempt failed with a "bad allocation" error from ONNX Runtime during the native check that loads a second session; the guest's system-managed pagefile had peaked at 6.4 GB. Setting a fixed 16 GB pagefile (registry key `PagingFiles` under `Memory Management`, then a reboot) let every check pass, slowly: the 168 native checks took about 25 minutes. A guest with 8 GB of RAM would be the better fix. The larger pagefile then exhausted the 64 GB virtual disk during Node packaging until the previous build directory was deleted. Processes started from an SSH session die when the session closes, so the build runs as a Task Scheduler task; see `code/windows_build.ps1`.

## Version 0.2.0 record (17 September 2026)

Verified on 17 September 2026 in the existing Windows 11 x64 guest on emeraldslate (build 26200, two virtual CPUs, 4 GB RAM). Compilation used MSVC 14.44 and the project-local Rust 1.98.1 toolchain. These results qualify this Windows installation; older Windows versions have not been tested.

The native bundle passes six Rust unit tests, 144 native ABI/Python checks, and C host loading, inference, and clean exit. All 81 frozen comparison cases agree with the reference boolean decisions; the largest probability difference is 0.000003046. The weights and tokenizer are identical to the Mac and Linux bundles. See [build checks](../released/windows-x64/build-checks.json), [comparison results](../released/windows-x64/platform-parity.json), and [build log](windows-build.log).

The [relocation check](windows-package.json) compiles a separate C application, copies the bundle, changes the working directory, and removes development tools from PATH. It passes with the installed Windows system runtimes. Deployment requires the Microsoft Visual C++ 2015-2022 x64 Redistributable; see [deployment requirements](../released/windows-x64/DEPLOYMENT.md).

Consumer packages also pass on Windows:

- [Python 3.12 wheel](python-wheel-windows-x64.json): isolated installation, concurrent initialization and calls, criteria, thresholds, and errors.
- [Node 24.19.0 package](node-consumer-windows-x64.json): six addon tests, installed tarball, TypeScript compilation, ESM/CommonJS, browser subpath import, initialization retry, and clean exit.
- [Java 17 package](java-bundle-windows-x64.json): ordinary classpath API and Windows classifier JAR, automatic native extraction, Unicode criteria, thresholds, errors, inference, and clean exit.

These consumer checks use local packages but do not themselves enforce a network block. The separate [native firewall test](windows-offline.json) passes: a TCP connection succeeds before the temporary executable-specific outbound block, fails with Windows access-denied error 10013 while blocked, and succeeds again after the rule is removed. The same C executable completes inference with the block active. SSH and other programs are unaffected.

The Windows build uncovered and fixed DLL shutdown cleanup under the Windows loader lock, temporary-directory cleanup while still inside that directory, locale-dependent JSON decoding, and an addon import-library filename collision. Windows keeps its default session for the process lifetime; explicit handle release remains available. The library must remain loaded until process exit, and applications must finish inference work before exiting.

Artifacts are in `released/windows-x64/`, `released/python/`, `released/node/`, and `released/java/`. These are local experimental packages, not public registry releases. Packaging does not improve decision accuracy: the existing fresh synthetic evaluation remains 59 correct answers out of 80.
