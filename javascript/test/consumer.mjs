import { npmCommand } from '../npm-command.mjs';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, rmSync, createReadStream } from 'node:fs';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { resolve, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const namespace = process.argv.includes('--network-namespace');
if (namespace) {
  const interfaces = process.platform === 'linux' ? readFileSync('/proc/net/dev','utf8').trim().split('\n').slice(2).map(line=>line.split(':')[0].trim()) : [];
  if (interfaces.length !== 1 || interfaces[0] !== 'lo') throw new Error('--network-namespace requires Linux with only loopback available');
}
const version = JSON.parse(readFileSync(resolve(root, 'javascript/package.json'), 'utf8')).version;
const tarball=resolve(root,`released/node/decisiongator-${version}-${process.platform}-${process.arch}.tgz`);
const temp = mkdtempSync(join(tmpdir(), 'decisiongator-node-'));
try {
  writeFileSync(join(temp,'package.json'), JSON.stringify({name:'offline-consumer',private:true,type:'module'}));
  execFileSync(...npmCommand(['install','--offline','--ignore-scripts','--no-audit','--no-fund',tarball]),{cwd:temp,stdio:'inherit'});
  const script = `
import assert from 'node:assert/strict';
import {renameSync} from 'node:fs';
import {isYes,isYesP,DecisionGatorError} from 'decisiongator';
import {isYes as browserIsYes} from 'decisiongator/web';
assert.equal(typeof browserIsYes, 'function');
import {createRequire} from 'node:module';
import {parse} from 'node:path';
const require=createRequire(import.meta.url);
const path=require.resolve('decisiongator').replace('index.cjs','native/${process.platform}-${process.arch}/manifest.json');
renameSync(path,path+'.hold');
try {await assert.rejects(isYes('Book a visit.','Is this asking for an appointment?'),e=>e instanceof DecisionGatorError&&e.code==='DG_LOAD_ERROR');} finally {renameSync(path+'.hold',path);}
process.chdir(parse(process.cwd()).root);
const p=await isYesP('Could I book an appointment for Tuesday?','Is this person asking for an appointment?');
assert.equal(await isYes('Could I book an appointment for Tuesday?','Is this person asking for an appointment?'),p>=.5);
assert.equal(await require('decisiongator').isYesP('Could I book an appointment for Tuesday?','Is this person asking for an appointment?'),p);
console.log(JSON.stringify({node:process.version,pYes:p,retry:true,esm:true,cjs:true,offline:${process.platform === 'darwin' || namespace}}));
`;
  writeFileSync(join(temp,'consumer.mjs'),script);
  writeFileSync(join(temp,'consumer.ts'),"import {isYes,isYesP,DecisionGatorError} from 'decisiongator';\nconst yes:boolean=await isYes('book','appointment?',{threshold:.9,criteria:{yes:'book',no:'other'}});\nconst p:number=await isYesP('book','appointment?');\nconst e:Error=new DecisionGatorError('DG_INVALID_ARGUMENT','bad');\n");
  execFileSync(process.execPath,[join(root,'javascript/node_modules/typescript/bin/tsc'),'--strict','--noEmit','--target','ES2022','--module','NodeNext','--moduleResolution','NodeNext',join(temp,'consumer.ts')],{cwd:temp,stdio:'inherit'});
  const profile='(version 1)(allow default)(deny network*)(deny file-read* (subpath '+JSON.stringify(join(root,'released/macos-arm64'))+'))(deny file-read* (subpath '+JSON.stringify(join(root,'javascript/native'))+'))';
  const result=process.platform==='darwin'?execFileSync('/usr/bin/sandbox-exec',['-p',profile,process.execPath,join(temp,'consumer.mjs')],{cwd:temp,encoding:'utf8'}):execFileSync(process.execPath,[join(temp,'consumer.mjs')],{cwd:temp,encoding:'utf8'});
  const resultData = JSON.parse(result.trim().split('\n').at(-1));
  const hash=createHash('sha256');
  for await (const chunk of createReadStream(tarball)) hash.update(chunk);
  const report={status:'passed',...resultData,platform:`${process.platform}-${process.arch}`,typescript_compilation:true,browser_subpath_import:true,network_denied:process.platform==='darwin'||namespace,network_isolation:namespace?'Linux network namespace (loopback only)':process.platform==='darwin'?'macOS sandbox':null,original_native_bundle_reads_denied:process.platform==='darwin',tarball,tarball_sha256:hash.digest('hex')};
  const classifier={'darwin-arm64':'macos-arm64','linux-x64':'linux-x64','win32-x64':'windows-x64'}[`${process.platform}-${process.arch}`];
  writeFileSync(join(root,`reports/node-consumer-${classifier}.json`),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
// The inference child has exited before cleanup, so Windows DLL handles are closed.
} finally {rmSync(temp,{recursive:true,force:true,maxRetries:8,retryDelay:150});}
