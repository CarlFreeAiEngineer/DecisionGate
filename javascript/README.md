# DecisionGate for Node.js and TypeScript

Your software probably needs this.

```typescript
import { isYes } from 'decisiongate';

if (await isYes('Can we meet on Friday?', 'Is the user asking for an appointment?')) {
  showAvailableTimes();
}
```

```typescript
import { choose } from 'decisiongate';

const team = await choose(
  "My card was charged twice for last month's invoice.",
  'Which team should handle this message?',
  ['billing', 'technical support', 'sales'],
);
routeTo(team); // 0, meaning "billing"
```

Install the supplied local tarball with `npm install /path/to/decisiongate-0.4.1-darwin-arm64.tgz`. JavaScript and TypeScript, ES modules and CommonJS are supported. The package includes its native library, weights, tokenizer and CPU runtime. Consumers need no compiler, runtime download, API key or inference server. Packaged native targets include Apple silicon macOS, Linux x64, and Windows x64. Windows requires the Microsoft Visual C++ 2015-2022 x64 Redistributable.

`isYesP(content, question, options?)` returns a Promise containing a number between 0 and 1. `isYes` returns a Promise containing a boolean. Always use `await`. Options accept `criteria: { yes, no }` and `threshold` (default 0.5, inclusive). `chooseP(content, question, options, opts?)` scores each string in `options` (at least two, nonempty) and returns a Promise containing an array of `{ index, p }` objects ranked best first, one per option, with probabilities summing to one; ties keep the order you supplied. `choose` returns a Promise containing just the best option's index, or -1 when its probability is below `opts.threshold` (default 0, inclusive). `opts` accepts the same `criteria` and `threshold` as `isYes`. Invalid input and unavailable resources reject with `DecisionGateError`, whose `code` identifies the problem. These scores are not guarantees of correctness.

The first call initializes the component and takes longer. Calls run outside the event loop and share one serialized native session. At most 64 calls can be outstanding; excess calls reject with `DG_RESOURCE_ERROR`. Failed initialization can be retried. Input must be nonempty, valid Unicode and fit the component's token limit. Content is not logged or sent anywhere.

Await outstanding calls before shutting down. Native libraries and the shared session stay loaded until process exit. Do not use forced process exits while inference is active. Worker-thread environments may call the API, but native initialization and execution are shared across the process; independent sessions and unloading are not supplied by this interface.

## Building locally

Run `npm ci`, `npm run build`, `npm test`, then `npm run pack:release` from this directory. The build copies the matching bundle from `released/` and compiles a small Node-API addon. Build machines require a C++17 compiler and Node headers. Set `NODE_INCLUDE_DIR` if headers are outside common locations. Windows also needs `NODE_LIB` pointing to the matching `node.lib` and a Visual Studio developer shell. `DECISIONGATE_BUNDLE` can select a different native bundle, for example `DECISIONGATE_BUNDLE=/path/to/another/bundle npm run build` to test against a development bundle before `choose`/`chooseP` support reaches `released/`. Consumers never run these build steps.

Node 24 is the baseline. The development lockfile pins Node 24.14.0 and TypeScript 5.9.3; the addon uses Node-API 8. ABI compatibility alone does not establish support for an untested operating system or Node release. See `reports/node-package.md` for recorded verification.

If `released/web/` exists, the build also stages the browser entry and its assets. Browser use has its own deployment instructions in that entry's README. The full precision weights are large, so this is a local distribution artifact until registry size and hosting limits have been settled.

`uv run code/remote_packages.py` from the project root builds and checks the Python and Node packages on the current native platform. It uses the installed Node 24+ runtime, installs development npm dependencies without their install scripts, and obtains missing build headers/import libraries from the matching official Node release with SHA-256 verification. Windows must run inside a Visual Studio developer environment. The script writes per-platform logs and a summary to `reports/`. Its `--java` option also builds and checks Java when JDK/Maven are available; `--skip-python` and `--skip-node` select individual stages. The browser release must be staged before packaging the combined JavaScript distribution.
