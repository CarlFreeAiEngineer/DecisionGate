# Browser WebAssembly verification

Verified on the development Apple silicon Mac on 2026-09-17. The source is in `web/`; the deployable component, demo, declarations, and notices are in `released/web/`. Nothing was published.

The release contains 344,833,293 bytes (344.8 MB). It uses the exact released weights and tokenizer, ONNX Runtime Web 1.22.0, and the pinned Hugging Face JavaScript tokenizer 0.2.0. Each browser passed 691 exact token ID, attention mask, and type ID comparisons and 87 probability comparisons against the native C component. Maximum absolute probability difference was 0.000001637, below the 0.0001 limit. No default-threshold decisions disagreed.

| Browser engine | Version | Local cold start | Warm median | Warm p95 |
| --- | --- | --- | --- | --- |
| chromium | 153.0.8010.12 | 1.09 s | 81.2 ms | 115.3 ms |
| firefox | 155.0 | 1.45 s | 81.0 ms | 114.0 ms |
| webkit | 26.6 | 1.08 s | 79.0 ms | 115.0 ms |

Cold start includes three concurrent first evaluations and localhost asset delivery, not a download over a remote network. Warm timings use the 87 reference inputs, not a fixed maximum-length benchmark. The UI timer continued running during inference. Browser differences, input length, load, and hardware affect these measurements.

All three engines passed invalid-input and UTF-16 rejection, the native 1 MiB byte limit, the 256-token limit, inclusive and endpoint thresholds, failed initialization followed by retry, rejected manifest corruption, queue limits, cancellation, restart, and cached offline page reload followed by fresh-worker inference. There were no external requests.

Chromium and Firefox used Playwright browser offline mode. Playwright WebKit’s offline toggle failed the navigation itself, so its offline test instead rejected every connection at the local origin, while the page’s content security policy allowed only that origin. It still reloaded and evaluated from the service-worker cache. These tests used Playwright 1.63.0 and isolated temporary persistent profiles. WebKit 26.6 is a test browser, not a test of the installed Safari application.

The summed process RSS reached approximately 2.19 GB in Chromium and 2.67 GB in Firefox during the complete suite, including caching and reload. This is a coarse upper estimate sampled once per second; shared memory can be counted multiple times. WebKit launches XPC processes outside the tracked process tree, so its memory figure is omitted. JavaScript heap counters do not include all WebAssembly memory. This is a desktop release; mobile and low-memory devices have not been tested.

The ordinary persistent-profile offline tests passed. Chromium private-profile caching failed around 256 MB despite a larger reported storage quota; the demo now reports unsuccessful installation instead of waiting forever or claiming the content is saved. Offline use requires available storage, a completed first installation, and assets that have not been evicted.

The tokenizer initially produced BERT-style pair segment IDs. The adapter explicitly sets RoBERTa segment IDs to zero, matching the native tokenizer; all 691 cases were compared in each browser after that correction. Fixtures include all current dataset rows, special tokens, Unicode whitespace, combining accents, emoji, supplementary characters, and embedded control characters.

Reproduce with `node web/tests/tokens.mjs` and `node web/tests/browser.mjs chromium firefox webkit` after the documented build and browser installation. Use Node 22 or 24 for test tools; Node 26.7.0 stalled while Playwright extracted Firefox, while Node 22.23.2 completed the same installation. The machine-readable evidence is [browser-chromium-firefox-webkit.json](browser-chromium-firefox-webkit.json).
