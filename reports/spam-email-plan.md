# Combined email and spam training experiment

Continue from `runs/v2-nli-expanded/best` with the original data, `data/expansion-v2.jsonl`, and both contribution files: `email-address-correction.jsonl` and `spam-comments.jsonl`. This preserves the previous tasks while adding address detection and spam-like marketing. The combined partitions contain 488 training, 124 validation, and 80 calibration records. The independently authored test files are excluded from training and calibration.

Use seed 42, ten epochs, batch size 16, learning rate 0.00001, and the Mac GPU. Select by lowest combined validation log loss and calibrate the selected export before inspecting test results. This is one fixed trial, not a test-driven parameter search.

Compare the frozen candidate with the current release on the 32-case spam test, 40-case email test, and existing 80-case and 52-case general tests. Report accuracy, probability error, policy-pair behavior, and per-family regressions. The email and general tests have previous development exposure; the spam test has not yet been evaluated. The user's Java examples are development examples, not independent evaluation.

For this experiment, consider replacement only if spam accuracy improves, email accuracy does not regress, and the total correct answers across the 132 general examples does not decrease. Also report each general set separately so aggregation cannot hide a regression. Verify the exact earlier email correction, clear Java spam examples, and native/Java integration. Preserve the current release and package the candidate separately for comparison. Rebuilding all platform releases is a separate promotion step; a local candidate must not silently make Mac/Windows/Linux/browser version 0.2.0 assets disagree.
