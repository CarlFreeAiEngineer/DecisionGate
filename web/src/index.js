import { DecisionGateError, validate, validateChoice } from './core.js';
export { DecisionGateError };
let worker;
let nextId = 0;
let settings = { maxQueue: 64 };
const pending = new Map();

/** Configure advanced hosting before the first call, or after close(). */
export function configure(options = {}) {
  if (worker || pending.size) throw new DecisionGateError('DG_RESOURCE_ERROR', 'Call close() before changing configuration');
  if (!options || typeof options !== 'object' || Array.isArray(options)) throw new DecisionGateError('DG_INVALID_ARGUMENT', 'Configuration must be an object');
  const maxQueue = options.maxQueue ?? 64;
  if (!Number.isSafeInteger(maxQueue) || maxQueue < 1 || maxQueue > 4096) throw new DecisionGateError('DG_INVALID_ARGUMENT', 'maxQueue must be an integer from 1 to 4096');
  settings = { maxQueue };
  for (const name of ['assetBaseUrl', 'workerUrl']) if (options[name] !== undefined) {
    const url = new URL(options[name], globalThis.location?.href ?? import.meta.url);
    if (!['http:', 'https:'].includes(url.protocol)) throw new DecisionGateError('DG_INVALID_ARGUMENT', `${name} must be an HTTP(S) URL`);
    settings[name] = url.href;
  }
}
function failAll(error) {
  for (const request of pending.values()) request.reject(error);
  pending.clear();
  worker?.terminate(); worker = undefined;
}
function getWorker() {
  if (worker) return worker;
  const created = new Worker(settings.workerUrl ?? new URL('./worker.js', import.meta.url), { type: 'module', name: 'DecisionGate' });
  created.onmessage = ({ data }) => {
    const request = pending.get(data.id);
    if (!request) return;
    pending.delete(data.id);
    if (data.error) request.reject(new DecisionGateError(data.error.code, data.error.message));
    else request.resolve(data.value);
  };
  created.onerror = event => { if (worker !== created) return; event.preventDefault(); failAll(new DecisionGateError('DG_RESOURCE_ERROR', 'DecisionGate worker failed. Check its assets and content security policy.')); };
  created.onmessageerror = () => { if (worker !== created) return; failAll(new DecisionGateError('DG_RESOURCE_ERROR', 'Invalid worker response')); };
  worker = created;
  return created;
}
/** Release the worker and its memory. Pending calls reject; later calls can restart. */
export function close() { failAll(new DecisionGateError('DG_CLOSED', 'DecisionGate was closed')); }
export async function isYesP(content, question, options = {}) {
  validate(content, question, options);
  if (pending.size >= settings.maxQueue) throw new DecisionGateError('DG_RESOURCE_ERROR', 'DecisionGate queue is full');
  let target;
  try { target = getWorker(); } catch (error) { throw new DecisionGateError('DG_RESOURCE_ERROR', error.message); }
  const id = ++nextId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    // Copy only the API's data; caller-owned objects cannot change queued work.
    const criteria = options.criteria ? { yes: options.criteria.yes, no: options.criteria.no } : null;
    try { target.postMessage({ id, content, question, criteria, assetBaseUrl: settings.assetBaseUrl }); }
    catch (error) { pending.delete(id); reject(new DecisionGateError('DG_RESOURCE_ERROR', error.message)); }
  });
}
export async function isYes(content, question, options = {}) {
  const threshold = validate(content, question, options, true);
  return (await isYesP(content, question, options)) >= threshold;
}
export async function chooseP(content, question, options, opts = {}) {
  validateChoice(content, question, options, opts);
  if (pending.size >= settings.maxQueue) throw new DecisionGateError('DG_RESOURCE_ERROR', 'DecisionGate queue is full');
  let target;
  try { target = getWorker(); } catch (error) { throw new DecisionGateError('DG_RESOURCE_ERROR', error.message); }
  const id = ++nextId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    // Copy only the API's data; caller-owned objects cannot change queued work.
    const criteria = opts.criteria ? { yes: opts.criteria.yes, no: opts.criteria.no } : null;
    const copiedOptions = Array.from(options);
    try { target.postMessage({ kind: 'choose', id, content, question, options: copiedOptions, criteria, assetBaseUrl: settings.assetBaseUrl }); }
    catch (error) { pending.delete(id); reject(new DecisionGateError('DG_RESOURCE_ERROR', error.message)); }
  });
}
export async function choose(content, question, options, opts = {}) {
  const threshold = validateChoice(content, question, options, opts, true);
  const ranking = await chooseP(content, question, options, opts);
  const { index, p } = ranking[0];
  return p >= threshold ? index : -1;
}
