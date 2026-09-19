'use strict';
const path = require('node:path');
class DecisionGateError extends Error {
  constructor(code, message, options) { super(message, options); this.name = 'DecisionGateError'; this.code = code; }
}
let addon;
let pending = 0;
let tail = Promise.resolve();
const codes = ['DG_OK', 'DG_INVALID_ARGUMENT', 'DG_LOAD_ERROR', 'DG_INCOMPATIBLE', 'DG_RESOURCE_ERROR', 'DG_INFERENCE_ERROR', 'DG_INTERNAL_ERROR', 'DG_INPUT_TOO_LONG'];
function text(value, name) {
  if (typeof value !== 'string' || /^\p{White_Space}*$/u.test(value) || !value.isWellFormed() || Buffer.byteLength(value) > 1048576)
    throw new DecisionGateError('DG_INVALID_ARGUMENT', `${name} must be nonempty, well-formed text of at most 1 MiB`);
}
function validate(content, question, options) {
  text(content, 'content'); text(question, 'question');
  if (!options || typeof options !== 'object' || Array.isArray(options)) throw new DecisionGateError('DG_INVALID_ARGUMENT', 'options must be an object');
  if (options.threshold !== undefined && (typeof options.threshold !== 'number' || !Number.isFinite(options.threshold) || options.threshold < 0 || options.threshold > 1)) throw new DecisionGateError('DG_INVALID_ARGUMENT', 'threshold must be between 0 and 1');
  if (options.criteria !== undefined && options.criteria !== null) {
    if (!options.criteria || typeof options.criteria !== 'object') throw new DecisionGateError('DG_INVALID_ARGUMENT', 'criteria must have yes and no descriptions');
    text(options.criteria.yes, 'criteria.yes'); text(options.criteria.no, 'criteria.no');
  }
}
function validateChoices(choices) {
  if (!Array.isArray(choices) || choices.length < 2) throw new DecisionGateError('DG_INVALID_ARGUMENT', 'options must be an array of at least two nonempty strings');
  choices.forEach((choice, i) => text(choice, `options[${i}]`));
}
function ensureAddon() {
  if (!addon) {
    const dir = path.join(__dirname, 'native', `${process.platform}-${process.arch}`);
    const candidate = require(path.join(dir, 'decisiongate.node'));
    candidate.initialize(path.join(dir, process.platform === 'win32' ? 'decisiongate.dll' : process.platform === 'darwin' ? 'libdecisiongate.dylib' : 'libdecisiongate.so'));
    addon = candidate;
  }
  return addon;
}
function queue(run) {
  if (pending >= 64) throw new DecisionGateError('DG_RESOURCE_ERROR', 'DecisionGate queue is full (64 requests)');
  pending++;
  const result = tail.then(async () => {
    try {
      return await run();
    } catch (error) {
      if (error instanceof DecisionGateError) throw error;
      throw new DecisionGateError(codes[error.status] || 'DG_LOAD_ERROR', error.message, { cause: error });
    }
  });
  tail = result.catch(() => {});
  return result.finally(() => { pending--; });
}
async function isYesP(content, question, options = {}) {
  validate(content, question, options);
  // Copy mutable caller options before queuing.
  const yes = options.criteria?.yes ?? null, no = options.criteria?.no ?? null;
  return queue(() => ensureAddon().evaluate(content, question, yes, no));
}
async function isYes(content, question, options = {}) {
  const threshold = options?.threshold ?? 0.5;
  return (await isYesP(content, question, options)) >= threshold;
}
async function chooseP(content, question, options, opts = {}) {
  validate(content, question, opts);
  validateChoices(options);
  // Copy mutable caller options before queuing.
  const choices = Array.from(options);
  const yes = opts.criteria?.yes ?? null, no = opts.criteria?.no ?? null;
  return queue(() => ensureAddon().chooseP(content, question, choices, yes, no));
}
async function choose(content, question, options, opts = {}) {
  const threshold = opts?.threshold ?? 0;
  const ranked = await chooseP(content, question, options, opts);
  return ranked[0].p >= threshold ? ranked[0].index : -1;
}
module.exports = { isYes, isYesP, choose, chooseP, DecisionGateError };
