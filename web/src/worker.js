import * as ort from 'onnxruntime-web/wasm';
import { createTokenizer, encode, DecisionGateError, validate, validateChoice, rank } from './core.js';
let initialization;
let queue = Promise.resolve();
async function checked(url, expected) {
  const response = await fetch(url, { credentials: 'same-origin' });
  if (!response.ok) throw new DecisionGateError('DG_RESOURCE_ERROR', `Unable to read ${new URL(url).pathname}: HTTP ${response.status}`);
  const bytes = await response.arrayBuffer();
  const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
  if (digest !== expected) throw new DecisionGateError('DG_INCOMPATIBLE', `Integrity check failed for ${new URL(url).pathname}`);
  return bytes;
}
async function initialize(assetBaseUrl) {
  const base = assetBaseUrl ? new URL(assetBaseUrl.endsWith('/') ? assetBaseUrl : `${assetBaseUrl}/`) : new URL('./', import.meta.url);
  const manifest = JSON.parse(new TextDecoder().decode(await checked(new URL('manifest.json', base), DG_MANIFEST_SHA)));
  if (manifest.format_version !== 1 || ![1, 2].includes(manifest.template_version) || !Number.isSafeInteger(manifest.max_tokens) || manifest.max_tokens < 1 || !Number.isFinite(manifest.temperature) || manifest.temperature <= 0) throw new DecisionGateError('DG_INCOMPATIBLE', 'Unsupported component manifest');
  if (manifest.choice_template_version !== undefined && manifest.choice_template_version !== 1) throw new DecisionGateError('DG_INCOMPATIBLE', 'Unsupported choice template version');
  const tokenizer = createTokenizer(JSON.parse(new TextDecoder().decode(await checked(new URL('tokenizer.json', base), manifest.sha256['tokenizer.json']))));
  ort.env.wasm.numThreads = 1;
  ort.env.wasm.proxy = false;
  ort.env.wasm.wasmPaths = base.href;
  ort.env.wasm.wasmBinary = await checked(new URL('ort-wasm-simd-threaded.wasm', base), manifest.sha256['ort-wasm-simd-threaded.wasm']);
  const bytes = await checked(new URL('model.onnx', base), manifest.sha256['model.onnx']);
  const session = await ort.InferenceSession.create(bytes, { executionProviders: ['wasm'], graphOptimizationLevel: 'all' });
  return { manifest, tokenizer, session };
}
// Calibrated logit z = (logits[yes] - logits[no]) / temperature, matching the native `logit` function.
async function runLogit(session, encoded, temperature) {
  const tensor = values => new ort.Tensor('int64', BigInt64Array.from(values, BigInt), [1, values.length]);
  const inputs = { input_ids: tensor(encoded.ids), attention_mask: tensor(encoded.attention_mask), token_type_ids: tensor(encoded.token_type_ids) };
  let result;
  try {
    result = await session.run(inputs);
    const logits = result.logits;
    if (!logits || logits.dims.length !== 2 || logits.dims[0] !== 1 || logits.dims[1] !== 2 || !Array.from(logits.data).every(Number.isFinite)) throw new DecisionGateError('DG_INFERENCE_ERROR', 'Invalid component output');
    const z = (Number(logits.data[1]) - Number(logits.data[0])) / temperature;
    if (!Number.isFinite(z)) throw new DecisionGateError('DG_INFERENCE_ERROR', 'Invalid logit');
    return z;
  } finally {
    Object.values(inputs).forEach(value => value.dispose());
    if (result) Object.values(result).forEach(value => value.dispose());
  }
}
async function evaluate(message) {
  validate(message.content, message.question, { criteria: message.criteria });
  if (!initialization) initialization = initialize(message.assetBaseUrl).catch(error => { initialization = undefined; throw error; });
  const { manifest, tokenizer, session } = await initialization;
  const encoded = encode(tokenizer, manifest, message.content, message.question, message.criteria);
  const z = await runLogit(session, encoded, manifest.temperature);
  const p = 1 / (1 + Math.exp(-z));
  if (!Number.isFinite(p) || p < 0 || p > 1) throw new DecisionGateError('DG_INFERENCE_ERROR', 'Invalid yes probability');
  return p;
}
// Ranks options by calibrated probability; matches the native GateSession::choose / rank functions.
async function evaluateChoice(message) {
  validateChoice(message.content, message.question, message.options, { criteria: message.criteria });
  if (!initialization) initialization = initialize(message.assetBaseUrl).catch(error => { initialization = undefined; throw error; });
  const { manifest, tokenizer, session } = await initialization;
  const logits = [];
  for (const option of message.options) {
    const encoded = encode(tokenizer, manifest, message.content, `${message.question}\nAnswer: ${option}`, message.criteria);
    logits.push(await runLogit(session, encoded, manifest.temperature));
  }
  return rank(logits);
}
self.onmessage = ({ data }) => {
  queue = queue.then(async () => {
    try { self.postMessage({ id: data.id, value: await (data.kind === 'choose' ? evaluateChoice(data) : evaluate(data)) }); }
    catch (error) { self.postMessage({ id: data.id, error: { code: error.code ?? 'DG_RESOURCE_ERROR', message: error.message ?? 'DecisionGate failed' } }); }
  });
};
