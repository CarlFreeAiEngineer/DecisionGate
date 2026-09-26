# DecisionGator yes/no API validation

2026-09-17, Mac arm64. The ordinary APIs are now Python `is_yes_p` / `is_yes`, Java `Decisions.isYesP` / `Decisions.isYes`, and C `dm_is_yes_p` / `dm_is_yes`. Boolean calls compare probability inclusively against 0.5 by default. Python and Java accept a custom threshold; C provides `dm_is_yes_at_threshold`. Invalid thresholds fail before initialization; evaluation failures never become false.

Six Rust tests, [144 native checks](yes-api-native.json), [Python checks](yes-api-python.txt), and 13 Java tests passed. Native and Java checks include thresholds 0 and 1, equality, invalid/non-finite thresholds, and error propagation. The [relocated C component](yes-api-package.json) and [packaged Java API](java-bundle.json) passed with networking denied and clean process exit. Java additionally denied access to the original native release directory.

The rebuilt Mac library/header/manifest are installed under `released/macos-arm64`; rebuilt Java API, platform, source, and Javadoc JARs are under `released/java`. Model weights and calibration are unchanged. These remain local experimental artifacts, not published packages. Other platforms are untested.

The product is now branded DecisionGator. Existing package identifiers and binary names are retained; see [the component specification](../specs/component-api.md).
