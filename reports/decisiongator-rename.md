# DecisionGator rename validation

The public Python package is `decisiongator`, with `Session` for explicit ownership and `DecisionGatorError` for errors. The training command is `decisiongator-train`. Java uses `org.decisiongator`, artifact `decisiongator-java`, and the explicit `DecisionGator` session. The Rust crate and native library use `decisiongator`; the C header is `decisiongator.h`, functions use `dg_`, constants use `DG_`, and the opaque handle is `dg_session`. These replace unpublished prototype names without compatibility aliases.

Rebuilt the Mac library and Java API/platform/source/Javadoc JARs, updated examples and developer instructions, and refreshed the installed Python project and local Maven artifacts. Previous release binaries are retained in `models/pre-decisiongator-macos` and `models/pre-decisiongator-java`. The checkout directory itself is unchanged.

Validation: six Rust tests; [144 native checks](decisiongator-native.json); [relocated C inference with networking denied](decisiongator-package.json); [Python automatic initialization and boolean checks](decisiongator-python.txt); training data validation through the renamed command; 13 Java tests; and [JAR-only offline execution](java-bundle.json). The weights, tokenizer, runtime checksums, and calibration match the previous bundle. This is a packaging/API rename, not retraining or an accuracy change. Only Mac arm64 is tested.

Historical reports, data provenance, copyright notices, stored weight identifiers, and checkpoint configuration keys retain their original names. These are necessary records of the experiment and remain compatible with the training pipeline.
