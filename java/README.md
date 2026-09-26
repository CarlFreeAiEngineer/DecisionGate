# DecisionGator for Java

A normal Java 17+ API, with Maven/Gradle dependencies and no application-written JNI. The Java wrapper calls the same Rust component as Python and C. Mac arm64, Linux x64 and Windows x64 classifier JARs are built and tested with OpenJDK 17.

```java
import org.decisiongator.Decisions;

boolean refundRequested = Decisions.isYes(
    "Please return my money. The item arrived broken.",
    "Is the customer asking for a refund?"
);
if (refundRequested) {
    // Your application decides what to do.
}
```

`isYes` returns `true` when the yes probability is at least `0.5`. Supply a threshold when the application needs another cutoff, or request the probability directly:

```java
boolean refundRequested = Decisions.isYes(content, question, 0.90);
double pYes = Decisions.isYesP(content, question);
```

Thresholds must be finite and between `0` and `1`, inclusive; invalid values throw `IllegalArgumentException`. A probability equal to the threshold counts as yes. Evaluation failures throw exceptions and never become `false`.

`Decisions` loads the packaged component on the first call and reuses one shared session. Calls are safe from multiple threads and run one at a time. Applications do not open or close anything. Initialization failures are reported normally, and later calls can retry. At JVM shutdown, an internal hook waits for any active evaluation and closes the session before the native runtime shuts down. The hook never loads a session or runs inference.

Optional criteria are a typed Java value:

```java
import org.decisiongator.Criteria;

var criteria = new Criteria(
    "The customer explicitly asks for money back.",
    "The customer does not ask for money back."
);
double pYes = Decisions.isYesP(content, question, criteria);
boolean yes = Decisions.isYes(content, question, criteria);
boolean yesAtCutoff = Decisions.isYes(content, question, criteria, 0.90);
```

Multiple choice ranks options instead of answering yes or no:

```java
import org.decisiongator.Choice;
import java.util.List;

List<String> teams = List.of("billing", "technical support", "sales");
List<Choice> ranked = Decisions.chooseP(content, "Which team should handle this message?", teams);
int bestTeam = ranked.get(0).index();

int team = Decisions.choose(content, "Which team should handle this message?", teams);
```

`chooseP` returns every option ranked best first, as index/probability pairs that sum to one; ties keep the caller's option order. `choose` returns the best option's index, or `-1` when its probability is below the threshold (default `0`, so plain `choose` never returns `-1`); equal to the threshold counts as chosen. Both accept an optional trailing `Criteria` and, for `choose`, an optional trailing threshold, the same way `isYes` does.

Native errors throw `DecisionGatorException` with a `statusCode()` and readable message. Invalid text, including unmatched UTF-16 surrogates, is rejected. Missing packaged assets produce an `IllegalStateException` explaining the missing dependency. Keep the component loaded for the JVM's lifetime; hot class-loader replacement is not supported by this native prototype. Finish inference before JVM exit and do not call it from shutdown hooks.

DecisionGator's accuracy is unchanged by the Java wrapper. It remains experimental: [current accuracy and limitations](../reports/accuracy-v2.md).

## Dependencies

These artifacts exist under [released/java/](../released/java/) after `uv run code/fetch_released.py --only java`. **They have not been published to Maven Central.** Coordinates are provisional. The build below installs them into the project's Maven repository; use that repository when testing the dependency declarations locally.

Maven:

```xml
<dependency>
  <groupId>org.decisiongator</groupId>
  <artifactId>decisiongator-java</artifactId>
  <version>0.4.1</version>
</dependency>
<dependency>
  <groupId>org.decisiongator</groupId>
  <artifactId>decisiongator-java</artifactId>
  <version>0.4.1</version>
  <classifier>macos-arm64</classifier>
  <scope>runtime</scope>
</dependency>
```

Gradle, Kotlin DSL:

```kotlin
implementation("org.decisiongator:decisiongator-java:0.4.1")
runtimeOnly("org.decisiongator:decisiongator-java:0.4.1:macos-arm64")
```

Choose `macos-arm64`, `linux-x64` or `windows-x64` for the platform classifier.

The small API JAR brings JNA 5.19.1 as a normal transitive dependency. The separate platform JAR contains the native libraries, model, tokenizer, manifest, and notices. Applications do not need Rust, C tooling, Python, ONNX installation, or a server. Sources and Javadoc JARs are included for IDEs.

Dependency resolution happens during application setup/build as usual. The first `Decisions.isYes(...)` or `Decisions.isYesP(...)` call makes no downloads or network calls. It extracts the packaged assets into a versioned local cache under `~/.cache/decisiongator`, verifies SHA-256 hashes, and loads the library. The unpacked 0.4.1 bundle needs about 900 MB; keep both archive and extraction space in mind when packaging an application. Set `-Ddecisiongator.cache=/your/cache/path` before the first call to choose another cache directory. Extraction is protected by a file lock and interrupted extraction can be retried.

Missing platform assets give a clear error, never a download fallback.

The Java source is Apache-2.0; model weights and native dependencies retain the licenses in their bundled notices. [JNA](https://github.com/java-native-access/jna) uses its supplied native bridge internally; application developers write only Java. JNA's native bridge is distributed with its dependency JAR.

## Explicit sessions and bundle files

For applications that need separate sessions, bundle metadata, or a chosen bundle directory, `DecisionGator` provides explicit ownership:

```java
import java.nio.file.Path;
import org.decisiongator.DecisionGator;

try (var gate = DecisionGator.load(Path.of("components/decisiongator"))) {
    double pYes = gate.evaluate(content, question);
    String manifest = gate.metadataJson();
}
```

Ordinary bundle files need no classifier JAR. `DecisionGator.loadBundled()` opens a separate session from packaged assets, and `loadBundled(Path cacheDirectory)` chooses its extraction cache. These explicit sessions implement `AutoCloseable`; close each one when finished. Calls on a session are synchronized, including `close()`. Closing twice is harmless; use after close throws `DecisionGatorException`. Closing a session releases its inference resources; native libraries stay loaded until process exit.

## Build this repository's Java artifacts

`uv run java/build.py --install` builds the API, runs unit and native integration tests, creates the platform JAR, creates source/Javadoc JARs, and installs them to `tools/maven-repository`. The normal outputs are copied into `released/java/`. It packages the already built native bundle; it does not retrain the model or compile Rust.

The helper expects a platform-appropriate JDK at `tools/jdk/` and Maven at `tools/maven/`, with their `bin/` directories inside. On this Mac, OpenJDK 17 and Maven were installed through Homebrew and copied as ordinary files from their `libexec` distributions into these project-local directories. The copies use the host's normal OS dependencies. No shell profile or system Java selection was changed. Other machines need their own JDK/Maven distributions; these tools are not shipped to application users.

To use an existing Java development environment directly, run Maven against `java/pom.xml`. Without a `decisiongator.bundle` property, native integration tests are skipped; the build helper supplies it. For project-local dependency resolution, pass `-Dmaven.repo.local=/absolute/path/to/DecisionGator/tools/maven-repository`. A standalone Java consumer using that repository can resolve the normal coordinates above.

The helper chooses the current platform's bundle under `released/`; `--bundle PATH --classifier NAME` selects a different already built platform bundle. Do not label a Mac library as a Windows/Linux artifact.

For experimental weights, select `--bundle models/spam-email-v1-macos --output models/spam-email-v1-java` and supply both `--expected-probability NUMBER` and `--expected-unicode-probability NUMBER`, independently evaluated through the native API for the two fixtures in `DecisionGatorIntegrationTest.java`. Release fixture probabilities remain the default. The output directory defaults to `released/java/`; omit `--install` to keep experimental artifacts out of the shared local Maven repository. Integration tests check native prediction agreement and API behavior with the selected bundle, including repeatability, Unicode inputs, errors and concurrent calls; prediction accuracy is evaluated separately.

Run `uv run java/check_bundle.py` to compile the standalone [Java example](examples/BundledExample.java), load only the packaged JAR assets with networking denied on macOS, and verify agreement with native predictions. This checks the bundled path as well as the direct-directory path exercised by the JUnit tests.

Tested runtime: OpenJDK 17 on macOS arm64, Linux x64 and Windows x64. Linux packaged inference passed inside a network namespace with only loopback available. The Windows consumer verified packaged extraction, predictions, Unicode criteria, boolean boundaries, errors and clean JVM shutdown; that Java run did not block networking. Later JDKs have not been qualified here; they may require native-access JVM options. Maven declarations are verified locally; the Gradle declaration uses standard dependency notation but no Gradle build has been run. Publishing and wider JVM qualification remain release work.

### Building and checking another platform

The helper now chooses the current platform automatically. On Linux x64 run `uv run java/build.py --install` after placing its native files in `released/linux-x64/`; on Windows x64 use `released/windows-x64/`. Run `uv run java/check_bundle.py` on that same machine to test the packaged classifier. Both helpers accept `--jdk PATH`; the build accepts `--maven PATH_TO_MVN` and the package check accepts `--jna PATH_TO_JNA_JAR`. This permits a package-manager-installed JDK without copying it into the project. Use JDK 17 for the first platform qualification and Maven 3.9.x. The source compiles with Java 17's API baseline.

To assemble a classifier on a different operating system, use `uv run java/build.py --bundle released/linux-x64 --classifier linux-x64 --package-only`. This packages bytes and skips execution tests; it does not compile native code or establish platform support. The helper clears stale build output and preserves previously released classifier JARs. Transfer the resulting API JAR, matching classifier JAR, JNA 5.19.1 JAR, example source and package checker to the target machine for the actual JVM check. No Maven or Rust installation is needed to run that packaged consumer check.

For a packaged Windows check, place the API JAR and `windows-x64` classifier JAR in `released/java/`, JNA 5.19.1 at its normal `tools/maven-repository/` path (or supply `--jna`), and run `uv run --offline --no-project java/check_bundle.py --classifier windows-x64 --windows-firewall` from an elevated shell. This optional test flag creates a temporary outbound block for the selected `java.exe`, checks that the Windows Firewall service and profiles are enabled and the rule is active, and removes the rule when the test finishes. The report records this as a configured firewall rule; it does not claim independently proven network denial. Without the flag, the ordinary check requires no administrator rights and makes no firewall changes. The checker finds a JDK through `tools/jdk`, `JAVA_HOME`, `javac` on PATH, or common Windows JDK 17 installation directories; `--jdk` remains the explicit override. It compiles the Unicode example with UTF-8 on every operating system.
