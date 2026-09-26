# Windows deployment

This bundle targets Windows x64. Keep the DLLs, model, tokenizer, and manifest together. C applications link against `decisiongator.lib` and load `decisiongator.dll`; place the DLLs beside the application executable or configure its DLL search directory explicitly.

The destination machine needs the Microsoft Visual C++ 2015–2022 x64 Redistributable. These Microsoft runtime DLLs are system prerequisites and are not included in this bundle. Installing Visual Studio, Rust, Python, or Node is unnecessary for a C application using the bundle. Install the redistributable through your package manager (`winget install --id Microsoft.VCRedist.2015+.x64 --exact`) or use the [official Microsoft distribution](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

See `system-dependencies.json` for DLL imports and the build host. A passing build or relocation check establishes behavior on that host; it does not certify older Windows releases. Relocation tests remove developer tools from PATH but retain installed Windows system runtimes.

Do not unload DecisionGator with FreeLibrary. Join inference threads before process exit and do not call DecisionGator from exit hooks.
