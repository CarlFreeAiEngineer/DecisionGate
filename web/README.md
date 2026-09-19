# DecisionGate in a browser

Import a function. The decision runs on the browser's CPU inside a worker, using the same weights, tokenization, criteria, calibration, and thresholds as the native component. No API key, external service, GPU, or CDN is used.

```javascript
import { isYes } from './decisiongate/index.js';

if (await isYes(
  'Could you let me know when my order will arrive?',
  'Is the customer asking for a reply?',
)) {
  showReplyButton();
}
```

To pick among several options instead of a yes or no answer, use `chooseP`:

```javascript
import { chooseP } from './decisiongate/index.js';

const ranking = await chooseP(
  "My card was charged twice for last month's invoice.",
  'Which team should handle this message?',
  ['billing', 'technical support', 'sales'],
);
routeTo(ranking[0].index); // billing, most probable first
```

With the supplied npm package, the equivalent import is `decisiongate/web`. A bundler must preserve or copy the worker and its adjacent assets; importing an npm entry does not teach every bundler how to publish an 872 MB data file. The most predictable integration is to copy the entire `released/web/` directory into your website's public assets, then import its `index.js` directly. The included `index.html` is a working example.

## Hosting

Serve this directory over HTTPS (or localhost for development). Preserve filenames and relative locations. Serve `.js` and `.mjs` as JavaScript and `.wasm` as `application/wasm`. The component uses single-threaded CPU WebAssembly in a dedicated module worker. Cross-origin isolation and GPU setup are unnecessary. Assets are about 890 MB uncompressed, including 872 MB of weights; startup and memory depend on the device.

For a bundler that relocates the entry module, set the worker and assets once before use:

```javascript
import { configure, isYes } from 'decisiongate/web';
configure({
  workerUrl: '/decisiongate/worker.js',
  assetBaseUrl: '/decisiongate/',
});
const yes = await isYes(content, question);
```

A compatible component policy is `script-src 'self' 'wasm-unsafe-eval'; worker-src 'self'; connect-src 'self'`. The demo also needs inline script and style allowances; production apps can put those in separate files. The worker, runtime glue, WebAssembly, tokenizer, and weights must be served from permitted locations. Browsers without WebAssembly SIMD or module workers are not supported.

## API and lifetime

`isYesP(content, question, { criteria })` returns `Promise<number>`. `isYes(content, question, { criteria, threshold })` returns `Promise<boolean>`, with an inclusive threshold of 0.5 by default. Criteria, when supplied, contains nonempty `yes` and `no` strings. The default is no criteria. Always await these functions; a Promise itself is truthy.

`chooseP(content, question, options, { criteria })` returns `Promise<Choice[]>`, one `{ index, p }` entry per option, ranked from most to least probable; the probabilities sum to one. `options` takes 2 to 256 nonempty strings. `choose(content, question, options, { criteria, threshold })` returns `Promise<number>`, the index of the most probable option, or `-1` when its probability is below an inclusive threshold of 0 by default. Equal probabilities keep the order given in `options`.

Invalid text, unmatched UTF-16 surrogates, invalid thresholds, excessive token length, missing or mismatched assets, a full queue, and execution failures reject with `DecisionGateError`, carrying a `code`. They never become a false decision. Each text argument is limited to 1 MiB of UTF-8, matching the native component. Tokenization and the 256-token limit match the native release, without truncation. Initialization is shared and retried after failure. Evaluations are serialized. At most 64 pending calls are accepted by default; `configure({ maxQueue: 16 })` changes the limit before first use.

`close()` immediately terminates the worker and rejects outstanding requests with `DG_CLOSED`. Later calls start a fresh worker. Call `close()` before changing configuration. Ordinary applications need no explicit initialization or disposal unless they want to recover the worker's memory early.

The worker verifies the pinned manifest, weights, tokenizer, and Wasm bytes with SHA-256. `SHA256SUMS.json` records the release's top-level files for deployment checks. Serve a complete release together; mixing versions fails integrity validation.

## Offline operation

A website must deliver its assets before they can work offline. The demo's **Keep offline** button installs the included service worker and saves the application and component. Once installation finishes, reloading the page without networking still works. Browser storage can be cleared or evicted. Private browsing may not provide enough cache space for this release, even if ordinary browsing does; report the storage error rather than promising success.

The service worker is an example owned by the host application. Integrate its asset list and version into an existing application service worker rather than replacing one. It caches only same-origin GET requests and does not send input text anywhere. The build derives its cache version from the release's contents. Updating the component requires deploying the matching assets together.

## Verified browsers

Chromium 153, Firefox 155, and Playwright WebKit 26.6 passed 691 exact tokenization cases, 87 native probability comparisons, and cached offline reload followed by inference on this Apple silicon Mac. Maximum probability difference was 0.00000059. The same runs also compared 5 `chooseP` rankings to native `choose` results, including a tied pair of options and a threshold that always returns -1; maximum probability difference was 0.0000002. Typical warm calls in this 0.4.0 release took about 570 ms, against about 80 ms for the much smaller 0.3.0 model. These measurements cover desktop browsers; mobile devices and the installed Safari application have not been tested. The full evidence is in the project’s `reports/browser-webassembly.md`.

## Rebuilding and testing

From the repository root, run `npm ci --prefix web`, `node web/build.mjs`, and `node web/tests/tokens.mjs`. Build output goes to `released/web/` by default; pass a directory argument, such as `node web/build.mjs /tmp/staging`, to stage a build elsewhere without touching the released one. `uv run --script web/tests/fixtures.py` regenerates the checked-in native reference fixtures on a Mac with the released native bundle. `uv run --script web/tests/fixtures_choice.py` regenerates `web/tests/fixtures-choice.json`, the native `choose` references, from the released native bundle through the Python binding.

Use Node 22 or 24 for browser test tooling. Install test browsers with `node web/node_modules/playwright/cli.js install chromium firefox webkit`, then run `node web/tests/browser.mjs chromium firefox webkit`. The tests use isolated temporary browser profiles and a localhost server, compare probabilities and choice rankings to native results, check validation and lifecycle, and reload offline with networking disabled. By default the tests serve `released/web/`; set `DECISIONGATE_RELEASE_DIR` to point them at a different staged build instead, such as the output of `node web/build.mjs /tmp/staging`. Test reports are written under `reports/browser-*.json`. Playwright's WebKit is a WebKit test browser, not a claim that the installed Safari application has been tested.

The component's experimental accuracy is unchanged by this packaging. Passing runtime parity does not make its decisions more accurate than the shared trained release. See the main project README and accuracy reports for the current evaluation.
