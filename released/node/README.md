# DecisionGate JavaScript packages

Fetch the tarballs with `uv run code/fetch_released.py --only node` if they are not already here, then install the one matching your operating system and architecture, for example:

```sh
npm install /path/to/decisiongate-0.3.0-darwin-arm64.tgz
```

```javascript
import { isYes } from 'decisiongate';

if (await isYes('Could we meet on Friday?', 'Is this asking for an appointment?')) {
  showAvailableTimes();
}
```

The Mac package is tested with Node 24.14.0 and 26.7.0 on Apple silicon; the Linux x64 package is tested with Node 26.7.0 on emeraldslate; the Windows x64 package is tested with Node 24.19.0 on Windows 11. Windows requires the Microsoft Visual C++ 2015-2022 x64 Redistributable. Packages contain native assets and the browser entry `decisiongate/web`. No consumer compilation or runtime download is needed. Verify the accompanying SHA-256 file when copying the archive.

See [JavaScript API and build instructions](../../javascript/README.md) and [verification](../../reports/node-package.md). These local packages have not been published to npm.
