import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createTokenizer,encode} from '../src/core.js';
const bundle = new URL('../../released/macos-arm64/',import.meta.url);
const tokenizer = createTokenizer(JSON.parse(fs.readFileSync(new URL('tokenizer.json',bundle))));
const manifest = JSON.parse(fs.readFileSync(new URL('manifest.json',bundle)));
const fixtures = JSON.parse(fs.readFileSync(new URL('fixtures.json',import.meta.url)));
for (const [i,f] of fixtures.entries()) {
 const got = encode(tokenizer,manifest,f.content,f.question,f.criteria);
 for(const key of ['ids','attention_mask','token_type_ids']) assert.deepEqual(got[key],f[key],`fixture ${i} ${key}`);
}
console.log(`${fixtures.length} exact tokenization cases passed`);
