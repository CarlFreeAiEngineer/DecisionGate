import { chromium, firefox, webkit } from 'playwright';
import { createServer } from 'node:http';
import { readFile, stat, writeFile, mkdtemp, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import os from 'node:os';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { build } from 'esbuild';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
// DECISIONGATE_RELEASE_DIR lets a build be tested from a fresh staging directory
// without touching released/web (e.g. `node web/build.mjs /tmp/staging`).
const release=process.env.DECISIONGATE_RELEASE_DIR?path.resolve(process.env.DECISIONGATE_RELEASE_DIR):path.join(root,'released/web');
const tokenFixtures=JSON.parse(await readFile(path.join(root,'web/tests/fixtures.json')));
const fixtures=tokenFixtures.filter(f=>'pYes' in f);
const choiceFixtures=JSON.parse(await readFile(path.join(root,'web/tests/fixtures-choice.json')));
// Float models must match native within 1e-4. A quantized model's manifest declares a looser parity tolerance,
// because WebAssembly rounds 8-bit arithmetic differently from native code (see tests/platform_parity.py).
const parity=JSON.parse(await readFile(path.join(release,'manifest.json'))).parity??{probability:1e-4,max_flip_fraction:0};
const tokenizerModule=(await build({entryPoints:[path.join(root,'web/src/core.js')],bundle:true,format:'esm',platform:'browser',write:false})).outputFiles[0].contents;
let blockManifest=false;
let corruptManifest=false;
let denyTraffic=false;
const requests=[];
// DECISIONGATE_ISOLATED=1 serves every file with cross-origin isolation headers, which enables threaded WebAssembly.
const suffix=process.env.DECISIONGATE_ISOLATED==='1'?'-threaded':'';
const isolation=process.env.DECISIONGATE_ISOLATED==='1'?{'Cross-Origin-Opener-Policy':'same-origin','Cross-Origin-Embedder-Policy':'require-corp'}:{};
const server=createServer(async(req,res)=>{
 try {
  if(denyTraffic){req.socket.destroy();return;}
  const url=new URL(req.url,'http://local'); requests.push(url.pathname);
  if(url.pathname==='/_test/tokenizer.js'){res.writeHead(200,{'Content-Type':'text/javascript'});res.end(tokenizerModule);return;}
  if(url.pathname.endsWith('manifest.json')&&blockManifest){res.writeHead(503);res.end('test failure');return;}
  if(url.pathname.endsWith('manifest.json')&&corruptManifest){res.writeHead(200,{'Content-Type':'application/json'});res.end((await readFile(path.join(release,'manifest.json'),'utf8'))+' ');return;}
  const relative=decodeURIComponent(url.pathname).replace(/^\//,'')||'index.html';
  const file=path.resolve(release,relative);
  if(!file.startsWith(release+path.sep)){res.writeHead(403);res.end();return;}
  const size=(await stat(file)).size;
  const mime={'.js':'text/javascript','.mjs':'text/javascript','.wasm':'application/wasm','.json':'application/json','.html':'text/html'}[path.extname(file)]??'application/octet-stream';
  res.writeHead(200,{...isolation,'Content-Type':mime,'Content-Length':size,'Cache-Control':'no-store','Content-Security-Policy':"default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; worker-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'"});
  res.end(await readFile(file));
 } catch{res.writeHead(404);res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const origin=`http://127.0.0.1:${server.address().port}`;
const results=[];
try {
for(const name of (process.argv.slice(2).length?process.argv.slice(2):['chromium'])) {
 const launcher={chromium,firefox,webkit}[name];
 const profile=await mkdtemp(path.join(os.tmpdir(),'decisiongate-browser-'));
 let peakBrowserRssBytes=0;
 const memoryTimer=setInterval(()=>{if(process.platform==='win32')return;execFile('ps',['-axo','pid,ppid,rss'],(error,out)=>{if(error)return;const rows=out.trim().split('\n').slice(1).map(line=>line.trim().split(/\s+/).map(Number));const descendants=new Set([process.pid]);for(let i=0;i<8;i++)for(const [pid,ppid] of rows)if(descendants.has(ppid))descendants.add(pid);const rss=rows.filter(([pid])=>pid!==process.pid&&descendants.has(pid)).reduce((sum,row)=>sum+row[2]*1024,0);peakBrowserRssBytes=Math.max(peakBrowserRssBytes,rss);});},1000);
 const context=await launcher.launchPersistentContext(profile,{headless:true}).catch(async error=>{clearInterval(memoryTimer);await rm(profile,{recursive:true,force:true});throw error;});
 const browser=context.browser();
 const page=await context.newPage();
 const external=[];
 page.on('request',request=>{if(!request.url().startsWith(origin))external.push(request.url());});
 page.on('console',msg=>{if(msg.type()==='error')console.error(name,msg.text());});
 page.on('pageerror',err=>console.error(name,err));
 try {
  await page.goto(origin);
  await page.evaluate(async()=>{globalThis.dg=await import('./index.js');});
  const tokenCases=await page.evaluate(async fixtures=>{const {createTokenizer,encode}=await import('./_test/tokenizer.js');const manifest=await fetch('./manifest.json').then(r=>r.json());const tokenizer=createTokenizer(await fetch('./tokenizer.json').then(r=>r.json()));for(const [i,f] of fixtures.entries()){const actual=encode(tokenizer,manifest,f.content,f.question,f.criteria);for(const key of ['ids','attention_mask','token_type_ids'])if(JSON.stringify(actual[key])!==JSON.stringify(f[key]))throw new Error(`Tokenizer mismatch ${i} ${key}`);}return fixtures.length;},tokenFixtures);
  const invalid=await page.evaluate(async()=>{
   const calls=[()=>dg.isYes('', 'question'),()=>dg.isYes('x','\u0085'),()=>dg.isYes('x','q',{threshold:NaN}),()=>dg.isYes('x','q',{threshold:2}),()=>dg.isYes('x','q',{threshold:null}),()=>dg.isYes('x','q',{threshold:'0.5'}),()=>dg.isYes('\ud800','q'),()=>dg.isYes('x','q',{criteria:{yes:'yes'}}),
    ()=>dg.chooseP('x','q',['only one']),()=>dg.chooseP('x','q',Array(257).fill('opt')),()=>dg.chooseP('x','q',['a',' ']),()=>dg.chooseP('x','q',['a',5]),()=>dg.chooseP('x','q','not an array'),()=>dg.chooseP('','q',['a','b']),()=>dg.chooseP('x','q',['a','b'],{criteria:{yes:'yes'}}),
    ()=>dg.choose('x','q',['a','b'],{threshold:NaN}),()=>dg.choose('x','q',['a','b'],{threshold:2}),()=>dg.choose('x','q',['a','b'],{threshold:-1})];
   return Promise.all(calls.map(async call=>{try{await call();return 'UNEXPECTED';}catch(e){return e.code;}}));
  });
  console.log(name,'invalid inputs checked');
  assert(invalid.every(c=>c==='DG_INVALID_ARGUMENT'));
  const oversized=await page.evaluate(async()=>{try{await dg.isYes('é'.repeat(524289),'q');}catch(error){return error.code;}});assert.equal(oversized,'DG_INPUT_TOO_LONG');
  blockManifest=true;
  const firstFailure=await page.evaluate(async()=>{try{await dg.isYes('Please book a visit','Is this a request?');return 'UNEXPECTED';}catch(e){return e.code;}});
  console.log(name,'initialization failed as expected');
  assert.equal(firstFailure,'DG_RESOURCE_ERROR');blockManifest=false;
  corruptManifest=true;const integrityFailure=await page.evaluate(async()=>{try{await dg.isYes('x','q');return 'UNEXPECTED';}catch(e){return e.code;}});assert.equal(integrityFailure,'DG_INCOMPATIBLE');corruptManifest=false;
  const run=await page.evaluate(async fixtures=>{
   let ticks=0;const timer=setInterval(()=>ticks++,10);const start=performance.now();
   const warm=await Promise.all(fixtures.slice(0,3).map(f=>dg.isYesP(f.content,f.question,{criteria:f.criteria})));
   const coldMs=performance.now()-start;const samples=[];const differences=[];let disagree=0;
   for(const f of fixtures){const start=performance.now();const p=await dg.isYesP(f.content,f.question,{criteria:f.criteria});samples.push(performance.now()-start);differences.push(Math.abs(p-f.pYes));if((p>=.5)!==(f.pYes>=.5))disagree++;}
   clearInterval(timer);
   const f=fixtures[0];const p=await dg.isYesP(f.content,f.question,{criteria:f.criteria});
   const inclusive=await dg.isYes(f.content,f.question,{criteria:f.criteria,threshold:p});
   const atOne=await dg.isYes(f.content,f.question,{criteria:f.criteria,threshold:1});
   const atZero=await dg.isYes(f.content,f.question,{criteria:f.criteria,threshold:0});
   let overlength;try{await dg.isYes('hello '.repeat(300),'q');}catch(e){overlength=e.code;}
   const heap=performance.memory?{usedJSHeapSize:performance.memory.usedJSHeapSize,totalJSHeapSize:performance.memory.totalJSHeapSize}:null;
   return {coldMs,ticks,cases:fixtures.length,maxDifference:Math.max(...differences),disagree,inclusive,atOne,atZero,overlength,samples,heap};
  },fixtures);
  console.log(name,'inference complete',run.maxDifference);
  assert(run.maxDifference<=parity.probability,JSON.stringify(run));assert(run.disagree<=parity.max_flip_fraction*fixtures.length,JSON.stringify(run));assert.equal(run.inclusive,true);assert.equal(run.atOne,false);assert.equal(run.atZero,true);assert.equal(run.overlength,'DG_INPUT_TOO_LONG');assert(run.ticks>10);
  const choice=await page.evaluate(async fixtures=>{
   const content="My card was charged twice for last month's invoice.";
   const question='Which team should handle this message?';
   const options=['billing','technical support','sales'];
   const routing=await dg.chooseP(content,question,options);
   const tie=await dg.chooseP('Please route this ticket to the right queue.','Which option applies?',['same','same']);
   const atThresholdOne=await dg.choose(content,question,options,{threshold:1});
   const atThresholdZero=await dg.choose(content,question,options);
   const parity=[];
   for(const f of fixtures){parity.push({ranking:await dg.chooseP(f.content,f.question,f.options,{criteria:f.criteria}),native:f.ranking});}
   return {routing,tie,atThresholdOne,atThresholdZero,parity};
  },choiceFixtures);
  console.log(name,'choice checked');
  assert.equal(choice.routing[0].index,0,JSON.stringify(choice.routing));
  assert(choice.routing.every((c,i,arr)=>i===0||arr[i-1].p>=c.p),'choice probabilities must be descending');
  assert(Math.abs(choice.routing.reduce((sum,c)=>sum+c.p,0)-1)<1e-9,'choice probabilities must sum to one');
  assert.deepEqual(choice.tie.map(c=>c.index),[0,1]);
  assert.equal(choice.tie[0].p,0.5);assert.equal(choice.tie[1].p,0.5);
  assert.equal(choice.atThresholdOne,-1);
  assert.equal(choice.atThresholdZero,0);
  let maxChoiceDifference=0;
  for(const {ranking,native} of choice.parity){
   assert.equal(ranking.length,native.length);
   const byIndex=new Map(ranking.map(r=>[r.index,r.p]));
   for(let i=0;i<ranking.length;++i){
    // Exact order is required for float models; a quantized model may swap options whose probabilities are within tolerance.
    if(parity.max_flip_fraction===0)assert.equal(ranking[i].index,native[i][0],`choice order mismatch: ${JSON.stringify(ranking)} vs ${JSON.stringify(native)}`);
    maxChoiceDifference=Math.max(maxChoiceDifference,Math.abs(byIndex.get(native[i][0])-native[i][1]));
   }
  }
  assert(maxChoiceDifference<=parity.probability,`choice native parity ${maxChoiceDifference}`);
  console.log(name,'choice native parity',maxChoiceDifference);
  const lifecycle=await page.evaluate(async()=>{
   dg.close();dg.configure({maxQueue:1});
   const pending=dg.isYes('Please book a visit','Is this a request?').catch(e=>e.code);
   let full;try{await dg.isYes('x','q');}catch(e){full=e.code;}
   dg.close();return {full,cancelled:await pending};
  });
  assert.deepEqual(lifecycle,{full:'DG_RESOURCE_ERROR',cancelled:'DG_CLOSED'});
  console.log(name,'caching offline assets');
  await page.evaluate(async()=>{await navigator.serviceWorker.register('./service-worker.js');await Promise.race([navigator.serviceWorker.ready,new Promise((_,reject)=>setTimeout(async()=>reject(new Error(JSON.stringify({storage:await navigator.storage.estimate(),keys:await caches.keys(),state:(await navigator.serviceWorker.getRegistration())?.installing?.state}))),20000))]);});
  await page.reload();
  console.log(name,'cached; disconnecting');
  // Playwright WebKit's offline toggle breaks service-worker navigation itself.
  // Reject connections at the origin instead; CSP forbids other origins.
  if(name==='webkit') denyTraffic=true;else await context.setOffline(true);
  await page.reload();
  const offline=await page.evaluate(async()=>{const dg=await import('./index.js');const p=await dg.isYesP('Could you let me know when my order will arrive?','Is the customer asking for a reply?');dg.close();return p;});
  assert(Number.isFinite(offline));assert.deepEqual(external,[]);
  const sorted=run.samples.toSorted((a,b)=>a-b);delete run.samples;
  const report={browser:name,version:browser.version(),crossOriginIsolated:await page.evaluate(()=>self.crossOriginIsolated),hardwareConcurrency:await page.evaluate(()=>navigator.hardwareConcurrency),peakBrowserProcessRssBytes:name==='webkit'?null:peakBrowserRssBytes,memoryNote:'Sum of browser process RSS sampled each second; shared pages can be counted more than once. JS heap excludes Wasm memory. WebKit memory is omitted because its XPC processes are not descendants of the test process.',...run,p50Ms:sorted[Math.floor(sorted.length*.5)],p95Ms:sorted[Math.floor(sorted.length*.95)],tokenizationCases:tokenCases,invalidCases:invalid.length,initializationRetry:true,integrityFailureRejected:true,byteLimitRejected:true,choiceCases:choiceFixtures.length,choiceMaxDifference:maxChoiceDifference,lifecycle,offlineReload:true,offlineMethod:name==='webkit'?'origin connections rejected; self-only CSP':'browser offline mode',offlinePYes:offline,externalRequests:external.length};
  results.push(report);await writeFile(path.join(root,`reports/browser-${name}${suffix}.json`),JSON.stringify({date:new Date().toISOString(),tokenizationCases:691,results:[report]},null,2)+'\n');console.log(JSON.stringify(report,null,2));
 } finally {blockManifest=false;corruptManifest=false;denyTraffic=false;clearInterval(memoryTimer);await context.close();await rm(profile,{recursive:true,force:true});}
}
await writeFile(path.join(root,`reports/browser-${results.map(r=>r.browser).join('-')}${suffix}.json`),JSON.stringify({date:new Date().toISOString(),tokenizationCases:691,results},null,2)+'\n');
} finally {server.close();}
