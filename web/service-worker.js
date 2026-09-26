// Example host-owned offline cache. The build inserts a digest of this release.
const PREFIX = `decisiongator-web:${self.registration.scope}:`;
const VERSION = PREFIX + '__RELEASE_DIGEST__';
const FILES = ['./', './index.html', './index.js', './worker.js', './manifest.json', './model.onnx', './tokenizer.json', './ort-wasm-simd-threaded.mjs', './ort-wasm-simd-threaded.wasm'];
// The weight files are named in the manifest.
self.addEventListener('install', event => event.waitUntil((async()=>{
 const cache=await caches.open(VERSION);
 // Sequential requests avoid retaining several large responses simultaneously.
 try {
  const manifest=await (await fetch(new URL('./manifest.json',self.registration.scope),{cache:'reload'})).json();
  for(const file of [...FILES,...(manifest.weights??[]).map(weight=>`./${weight.file}`)]) await cache.add(new Request(new URL(file,self.registration.scope),{cache:'reload'}));
 } catch(error) { await caches.delete(VERSION); throw error; }
 await self.skipWaiting();
})()));
self.addEventListener('activate', event=>event.waitUntil((async()=>{
 for(const key of await caches.keys()) if(key.startsWith(PREFIX)&&key!==VERSION) await caches.delete(key);
 await self.clients.claim();
})()));
self.addEventListener('fetch',event=>{
 if(event.request.method!=='GET'||new URL(event.request.url).origin!==self.location.origin) return;
 event.respondWith((async()=>{const cache=await caches.open(VERSION);return (await cache.match(event.request))??fetch(event.request);})());
});
