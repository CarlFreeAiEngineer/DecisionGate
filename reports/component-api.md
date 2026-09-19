# Ordinary component API validation

2026-09-17, development Mac arm64. The release now includes automatic initialization through Python `probability`, C `dm_probability`, and Java `Decisions.probability`. Explicit session APIs remain available. The model weights, tokenizer, template, calibration, and accuracy are unchanged from [accuracy v2](accuracy-v2.md).

- Rust: six unit tests passed in `code/build.py`; rebuilt library, header, and manifest installed in `released/macos-arm64`.
- Native ABI: [122 checks passed](component-native.json), including concurrent first use, working-directory independence, initialization failure followed by successful retry, and errors leaving the probability output unchanged.
- C packaging: [relocated component passed](component-package.json) with networking denied, no development tools on PATH, and no bundle path passed to the application. Process exit was clean.
- Python: [automatic initialization checks passed](component-python.txt), including failed-load recovery, concurrent session reuse, working-directory independence, errors, and known native probabilities.
- Java: 12 unit/integration tests passed on the project-local OpenJDK 17; API, platform, source, and Javadoc JARs rebuilt and installed locally. The [packaged facade test passed](java-bundle.json) with networking and reads from the original native release directory denied. Predictions matched native fixtures, including Unicode criteria; JVM shutdown was clean.

Java artifacts are in `released/java`; none have been published to Maven Central. Maven builds were exercised; Gradle dependency syntax is documented but no Gradle consumer build was run. Only Mac arm64 is tested. Python distributable platform wheels remain future work; the simple API currently discovers checkout assets or an application-supplied `decisionmodel/_bundle` directory.
