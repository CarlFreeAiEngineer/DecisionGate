import { build } from 'esbuild';
import { mkdir, readFile, writeFile, copyFile, cp, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.dirname(here);
const destination = path.resolve(process.argv[2] ?? path.join(root, 'released/web'));
await mkdir(destination, { recursive: true });
// DECISIONGATE_NATIVE_DIR stages a different native bundle (its manifest, weights, tokenizer, and notices).
const native = path.resolve(process.env.DECISIONGATE_NATIVE_DIR ?? path.join(root, 'released/macos-arm64'));
const manifest = JSON.parse(await readFile(path.join(native, 'manifest.json')));
manifest.sha256 = { 'model.onnx': manifest.sha256['model.onnx'], 'tokenizer.json': manifest.sha256['tokenizer.json'] };
manifest.build = { target: 'browser-wasm', onnxruntime: '1.22.0', tokenizer: '@huggingface/tokenizers@0.2.0', threads: 'all logical cores when the page is cross-origin isolated, otherwise 1' };
const ort = path.join(here,'node_modules/onnxruntime-web/dist');
for (const file of ['ort-wasm-simd-threaded.wasm','ort-wasm-simd-threaded.mjs']) {
 await copyFile(path.join(ort,file),path.join(destination,file));
 manifest.sha256[file] = createHash('sha256').update(await readFile(path.join(destination,file))).digest('hex');
}
const data = JSON.stringify(manifest,null,2)+'\n';
await writeFile(path.join(destination,'manifest.json'),data);
const digest = createHash('sha256').update(data).digest('hex');
for (const entry of ['index','worker']) await build({entryPoints:[path.join(here,`src/${entry}.js`)],outfile:path.join(destination,`${entry}.js`),bundle:true,format:'esm',platform:'browser',target:['es2022'],minify:true,define:{DG_MANIFEST_SHA:JSON.stringify(digest)}});
for(const file of ['model.onnx','tokenizer.json']) await copyFile(path.join(native,file),path.join(destination,file));
await copyFile(path.join(here,'src/index.d.ts'),path.join(destination,'index.d.ts'));
await writeFile(path.join(destination,'package.json'),JSON.stringify({name:'decisiongate-web',version:'0.4.1',private:true,type:'module',exports:{'.':{types:'./index.d.ts',import:'./index.js'}}},null,2)+'\n');
await cp(path.join(native,'notices'),path.join(destination,'notices'),{recursive:true});
for(const [pkg,name] of [['@huggingface/tokenizers','tokenizers-js'],['onnxruntime-web','onnxruntime-web'],['onnxruntime-common','onnxruntime-common']]) {
 const pkgDir=path.join(here,'node_modules',pkg);
 for(const file of await readdir(pkgDir)) if(/^(LICENSE|NOTICE)/i.test(file)) await copyFile(path.join(pkgDir,file),path.join(destination,'notices',`${name}-${file}`));
}
await copyFile(path.join(here,'README.md'),path.join(destination,'README.md'));
await copyFile(path.join(here,'demo.html'),path.join(destination,'index.html'));
const serviceWorker = await readFile(path.join(here,'service-worker.js'),'utf8');
const cacheDigest = createHash('sha256').update(data).update(await readFile(path.join(destination,'index.js'))).update(await readFile(path.join(destination,'worker.js'))).update(await readFile(path.join(destination,'index.html'))).update(serviceWorker).digest('hex');
await writeFile(path.join(destination,'service-worker.js'),serviceWorker.replace('__RELEASE_DIGEST__',cacheDigest));
const hashes={};
for(const file of await readdir(destination)) if(!['SHA256SUMS.json','notices'].includes(file)) hashes[file]=createHash('sha256').update(await readFile(path.join(destination,file))).digest('hex');
await writeFile(path.join(destination,'SHA256SUMS.json'),JSON.stringify(hashes,null,2)+'\n');
console.log(`Staged browser component: ${destination}`);
