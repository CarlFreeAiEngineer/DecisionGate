# Java artifacts

Local version 0.4.1 artifacts, not yet published to Maven Central:

- `decisiongate-java-0.4.1.jar`: Java 17 API, including `Decisions.isYes(...)`, `Decisions.isYesP(...)`, `Decisions.choose(...)`, and `Decisions.chooseP(...)`.
- `decisiongate-java-0.4.1-macos-arm64.jar`: bundled Mac native libraries, weights, tokenizer, manifest, and notices.
- `decisiongate-java-0.4.1-linux-x64.jar`: the corresponding Linux x64 bundle.
- `decisiongate-java-0.4.1-windows-x64.jar`: the corresponding Windows x64 bundle.
- `decisiongate-java-0.4.1-sources.jar` and `decisiongate-java-0.4.1-javadoc.jar`: sources and API documentation.
- `decisiongate-java-0.4.1.pom`: dependency metadata, including JNA.

Use both the API and platform bundle dependencies; the API JAR alone does not contain native assets. Maven resolves JNA as a normal dependency. See [the Java guide](../../java/README.md) for Maven/Gradle examples and local installation instructions. The first call extracts bundled assets to a verified local cache and initializes the component, without runtime downloads.

Mac arm64, Linux x64 and Windows x64 are built and tested with OpenJDK 17. Mac and Linux Java checks also blocked networking. The Windows Java check verified packaged inference and clean shutdown. Decisions remain experimental; Java uses the same weights and interface semantics as C and Python.
