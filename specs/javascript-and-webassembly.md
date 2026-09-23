# JavaScript, TypeScript, and browser WebAssembly

Implemented in `javascript/` and `web/`. The Node package wraps the native library; the browser package runs CPU WebAssembly in a worker. Both expose ordinary asynchronous functions and use the exact released weights, tokenizer assets, input template, label mapping, and calibration. Neither requires retraining for its target. Packages are staged locally, not published to npm.

## Public interface

```typescript
import { isYes, isYesP } from 'decisiongate';

if (await isYes(content, 'Is this person asking for an appointment?')) {
    routeToAppointments();
}

const pYes = await isYesP(content, question, {
    criteria: { yes: 'An explicit request to book a visit.', no: 'Anything else.' },
});
const yes = await isYes(content, question, { threshold: 0.9 });

const ranked = await chooseP(message, 'Which team should handle this message?', ['billing', 'technical support', 'sales']);
// ranked[0] is { index, p } for the best option; entries are sorted best first and p sums to one.
const team = await choose(message, 'Which team should handle this message?', ['billing', 'technical support', 'sales'], { threshold: 0.6 });
// -1 when the best option is below the threshold.
```

Browser applications import the same functions from `decisiongate/web`, or directly from the staged browser `index.js`. `isYes` returns `Promise<boolean>`; `isYesP` returns `Promise<number>`. Always await them: a Promise itself is truthy. JavaScript needs no TypeScript compiler; declarations are supplied for TypeScript applications.

Criteria can be omitted or null. When supplied, both `yes` and `no` must be nonempty strings. `isYes` uses an inclusive threshold of 0.5 by default; an explicit threshold must be a finite number in [0,1]. Empty text, unmatched UTF-16 surrogates, invalid criteria, excessive length, missing assets, and execution failures reject with `DecisionGateError`, never false. Its constructor is `(code, message)`. Each text argument has the native 1 MiB UTF-8 byte limit, and the combined encoded pair has a 256-token limit. Nothing is silently truncated.

Both implementations initialize lazily, share initialization across simultaneous calls, serialize evaluation, retry failed initialization, and bound the pending queue at 64 requests. A full queue rejects with `DG_RESOURCE_ERROR`. Content is neither logged nor sent to an inference service.

## Node implementation and packaging

A Node-API 8 addon calls the existing `dg_` C interface on asynchronous native work. It reuses native tokenization, inference, and validation. ES module and CommonJS exports share the process-wide native session. Native libraries stay loaded until process exit; callers should await outstanding work before ending the process or terminating a worker thread. This interface does not offer native unloading.

Node 24 is the baseline; development dependencies pin Node 24.14.0 and TypeScript 5.9.3. The Mac package has also passed tests under Node 26.7.0. Node-API compatibility does not establish support for an untested OS or runtime. Native packages require matching OS and architecture builds.

`javascript/build.mjs` copies the corresponding native bundle and compiles the addon. Build machines need a C++17 compiler and Node headers; Windows additionally needs the matching `node.lib` and a Visual Studio developer environment. Consumers install a supplied platform tarball and need no compiler, installation download script, or separate runtime setup. Artifacts and checksums are staged under `released/node/`.

Build and test instructions are in [the Node guide](../javascript/README.md). [Mac verification](../reports/node-package.md) covers concurrent use, validation, event-loop responsiveness, thresholds, worker threads, and a fresh offline consumer using ESM, CommonJS, and TypeScript from a changed working directory. Platform qualification follows the actual per-platform reports and [release inventory](../released/README.md).

When the browser release is present, the Node build includes it under the `decisiongate/web` export. Native and browser assets currently duplicate the weights, making the combined Mac tarball about 627 MB compressed. Registry hosting and publication remain separate work; distribution must not introduce an inference API or runtime CDN dependency.

## Browser implementation

The dedicated module worker uses ONNX Runtime Web 1.22.0 with CPU WebAssembly and no GPU requirement. On a cross-origin isolated page it uses one thread per logical core, because browsers do not say which cores are fast; elsewhere it runs on one thread. Tokenization uses the pinned Hugging Face JavaScript tokenizer 0.2.0 with the released `tokenizer.json`; the adapter supplies RoBERTa's all-zero segment IDs. The input ordering, criteria formatting, special tokens, masks, temperature, and inclusive comparison match the native release.

Initialization verifies the pinned manifest, weights, tokenizer, and Wasm bytes with SHA-256. The build also writes `SHA256SUMS.json` for deployment checks. Deploy a complete matching release; mixing assets fails validation.

`web/build.mjs` stages roughly 345 MB under `released/web/`: entry module, declarations, worker, runtime glue, Wasm, tokenizer, weights, manifest, notices, and a working browser demo. The same unmodified weights account for roughly 329 MB. Build this browser target on any development platform with the pinned JavaScript dependencies; browser execution still needs testing on the intended devices.

Serve the directory over HTTPS or localhost, preserving relative paths and correct JavaScript/Wasm MIME types. A bundler must copy these assets or use the advanced `configure({ workerUrl, assetBaseUrl })` settings; importing an npm subpath does not automatically configure every bundler. Ordinary direct imports need no loading call. `configure({ maxQueue })` can change the queue limit before first use. `close()` terminates the worker and rejects pending calls with `DG_CLOSED`; subsequent calls restart it. Configuration changes require closing first.

A compatible component policy is `script-src 'self' 'wasm-unsafe-eval'; worker-src 'self'; connect-src 'self'`. The demo additionally uses inline script and styling. See [browser deployment instructions](../web/README.md) for the working example and asset configuration.

## Offline behavior and evidence

A website must first deliver its assets. The demo's **Keep offline** action saves the application and component through a service worker. Cache versions derive from release contents and are scoped to the host application. Installation failure is reported; cleared or evicted storage can require another download. Private browsing may lack enough cache space. Applications with an existing service worker should integrate the asset list into their own cache strategy.

Chromium 153, Firefox 155, and Playwright WebKit 26.6 each passed 691 exact token, mask, and segment comparisons plus 87 native probability comparisons on the Apple silicon development Mac. Maximum absolute probability difference was 0.000001637, below the 0.0001 tolerance, with no default-threshold boolean disagreements. Tests also cover validation, byte/token limits, manifest corruption, initialization retry, queue limits, cancellation, and cached offline reload followed by fresh-worker inference. Small floating-point differences remain possible near caller-selected thresholds.

Chromium and Firefox used browser offline mode. WebKit's test refused every origin connection with a self-only content policy because Playwright's offline toggle broke service-worker navigation. The WebKit engine test is not a test of the installed Safari application. No external requests occurred.

Measured warm calls were about 80 ms, with local cold startup around 1.1 to 1.5 seconds. Summed process RSS reached approximately 2.19 GB in Chromium and 2.67 GB in Firefox during the full suite; shared pages can be counted more than once. WebKit's separate XPC processes prevented a comparable memory measurement. These are desktop measurements, not mobile or low-memory support claims. See [the browser report](../reports/browser-webassembly.md) for methods, commands, and machine-readable evidence.

WebGPU, generic WASI hosts, mobile qualification, registry publication, and hosting are not part of this implementation. Runtime parity preserves the shared component's existing accuracy; it does not improve the underlying decision quality.
