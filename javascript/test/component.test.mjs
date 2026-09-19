import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { parse } from 'node:path';
import { isYes, isYesP, choose, chooseP, DecisionGateError } from '../index.mjs';
const text = 'Could I book an appointment for Tuesday?';
const question = 'Is this person asking for an appointment?';
test('concurrent first use, probability, inclusive boundaries, and event loop responsiveness', async () => {
  let ticks = 0; const timer = setInterval(() => ticks++, 10);
  let answers;
  try { answers = await Promise.all([isYesP(text, question), isYesP(text, question), isYes(text, question)]); }
  finally { clearInterval(timer); }
  assert.equal(answers[0], answers[1]); assert.equal(answers[2], answers[0] >= .5);
  assert.ok(ticks > 5); assert.ok(answers[0] >= 0 && answers[0] <= 1);
  assert.equal(await isYes(text, question, { threshold: answers[0] }), true);
  assert.equal(await isYes(text, question, { threshold: 0 }), true);
  assert.equal(await isYes(text, question, { threshold: 1 }), false);
  assert.equal(await createRequire(import.meta.url)('../index.cjs').isYesP(text, question), answers[0]);
});
test('criteria, Unicode, changing working directory', async () => {
  const original = process.cwd();
  try {
    process.chdir(parse(original).root);
    const p = await isYesP('Réservez-moi un rendez-vous, s’il vous plaît. 😀', question, { criteria: {yes:'A request to book a visit.', no:'Anything else.'} });
    assert.ok(Number.isFinite(p));
  } finally { process.chdir(original); }
});
test('invalid input never becomes a negative answer', async () => {
  for (const [content, q, options] of [['',question,{}], ['\ud800',question,{}], [text,'',{}], [text,question,{threshold:NaN}], [text,question,{threshold:2}], [text,question,{criteria:{yes:'ok',no:''}}], [text,question,null]]) {
    await assert.rejects(isYes(content,q,options), e => e instanceof DecisionGateError && e.code === 'DG_INVALID_ARGUMENT');
  }
  await assert.rejects(isYes('word '.repeat(1000), question), e => e.code === 'DG_INPUT_TOO_LONG');
});
test('bounded queue', async () => {
  const calls = Array.from({length:65}, () => isYesP(text,question));
  const all = await Promise.allSettled(calls);
  assert.equal(all.filter(v => v.status === 'fulfilled').length,64);
  assert.equal(all[64].reason.code,'DG_RESOURCE_ERROR');
});
test('addon boundary rejects invalid direct calls', () => {
  const addon=createRequire(import.meta.url)(`../native/${process.platform}-${process.arch}/decisiongate.node`);
  assert.throws(()=>addon.initialize());
  assert.throws(()=>addon.initialize(123));
  assert.throws(()=>addon.evaluate());
  assert.throws(()=>addon.evaluate(123,question,null,null));
  assert.throws(()=>addon.evaluate(text,question,'yes',null));
  assert.throws(()=>addon.evaluate('\ud800',question,null,null));
  assert.throws(()=>addon.chooseP());
  assert.throws(()=>addon.chooseP(123,question,['a','b'],null,null));
  assert.throws(()=>addon.chooseP(text,question,['a'],null,null));
  assert.throws(()=>addon.chooseP(text,question,'not-an-array',null,null));
  assert.throws(()=>addon.chooseP(text,question,['a','b'],'yes',null));
  assert.throws(()=>addon.chooseP('\ud800',question,['a','b'],null,null));
});
const routingContent = "My card was charged twice for last month's invoice.";
const routingQuestion = 'Which team should handle this message?';
const routingOptions = ['billing', 'technical support', 'sales'];
test('chooseP ranks options best first with probabilities summing to one', async () => {
  const ranked = await chooseP(routingContent, routingQuestion, routingOptions);
  assert.equal(ranked.length, 3);
  assert.equal(ranked[0].index, 0);
  for (let i = 1; i < ranked.length; i++) assert.ok(ranked[i - 1].p >= ranked[i].p);
  const sum = ranked.reduce((total, entry) => total + entry.p, 0);
  assert.ok(Math.abs(sum - 1) < 1e-9);
  assert.equal(await choose(routingContent, routingQuestion, routingOptions), 0);
});
test('choose keeps caller order on ties', async () => {
  const ranked = await chooseP('same content either way', 'same or different?', ['same', 'same']);
  assert.deepEqual(ranked, [{ index: 0, p: 0.5 }, { index: 1, p: 0.5 }]);
  assert.equal(await choose('same content either way', 'same or different?', ['same', 'same']), 0);
});
test('choose returns -1 when the best option is below threshold', async () => {
  assert.equal(await choose(routingContent, routingQuestion, routingOptions, { threshold: 1.0 }), -1);
});
test('chooseP validates content, question, options and opts', async () => {
  const cases = [
    ['', routingQuestion, routingOptions, {}],
    [routingContent, '', routingOptions, {}],
    [routingContent, routingQuestion, ['only-one'], {}],
    [routingContent, routingQuestion, [], {}],
    [routingContent, routingQuestion, 'not-an-array', {}],
    [routingContent, routingQuestion, ['ok', ''], {}],
    [routingContent, routingQuestion, ['ok', '\ud800'], {}],
    [routingContent, routingQuestion, routingOptions, { threshold: NaN }],
    [routingContent, routingQuestion, routingOptions, { threshold: 2 }],
    [routingContent, routingQuestion, routingOptions, { criteria: { yes: 'ok', no: '' } }],
  ];
  for (const [content, q, opts, extra] of cases) {
    await assert.rejects(chooseP(content, q, opts, extra), e => e instanceof DecisionGateError && e.code === 'DG_INVALID_ARGUMENT');
  }
  for (const [content, q, opts, extra] of cases) {
    await assert.rejects(choose(content, q, opts, extra), e => e instanceof DecisionGateError && e.code === 'DG_INVALID_ARGUMENT');
  }
});
test('isYesP and chooseP share one queue under concurrent use', async () => {
  const [yesAnswer, ranked, bestIndex] = await Promise.all([
    isYesP(text, question),
    chooseP(routingContent, routingQuestion, routingOptions),
    choose(routingContent, routingQuestion, routingOptions),
  ]);
  assert.ok(yesAnswer >= 0 && yesAnswer <= 1);
  assert.equal(ranked[0].index, 0);
  assert.equal(bestIndex, 0);
});
test('worker environments finish native work and exit cleanly', async () => {
  const {Worker}=await import('node:worker_threads');
  const location=new URL('../index.mjs',import.meta.url).href;
  const workers=Array.from({length:3},()=>new Worker(`const {parentPort}=require('node:worker_threads');import(${JSON.stringify(location)}).then(async api=>parentPort.postMessage(await api.isYes(${JSON.stringify(text)},${JSON.stringify(question)})));`,{eval:true}));
  await Promise.all(workers.map(w=>new Promise((resolve,reject)=>{w.on('error',reject);w.on('exit',code=>code?reject(new Error('Worker exit '+code)):resolve());})));
});
