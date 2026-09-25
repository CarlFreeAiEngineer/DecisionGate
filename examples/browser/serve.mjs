// A tiny local web server for the browser example, using only Node.js.
//   node examples/browser/serve.mjs      then open the address it prints
// It serves this checkout with the two headers that let the model use every CPU core.
import { createReadStream, statSync } from 'node:fs';
import { createServer } from 'node:http';
import { extname, join, normalize, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../..', import.meta.url));
const port = Number(process.env.PORT ?? 8000);
const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript',
                '.json': 'application/json', '.wasm': 'application/wasm' };

createServer((request, response) => {
  const path = normalize(join(root, decodeURIComponent(new URL(request.url, 'http://x').pathname)));
  let file = path.endsWith(sep) ? join(path, 'index.html') : path;
  try {
    if (!file.startsWith(root) || !statSync(file).isFile()) throw new Error();
  } catch {
    response.writeHead(404).end('Not found');
    return;
  }
  response.writeHead(200, {
    'Content-Type': types[extname(file)] ?? 'application/octet-stream',
    'Cross-Origin-Opener-Policy': 'same-origin',
    'Cross-Origin-Embedder-Policy': 'require-corp',
  });
  createReadStream(file).pipe(response);
}).listen(port, 'localhost', () => console.log(`Open http://localhost:${port}/examples/browser/`));
