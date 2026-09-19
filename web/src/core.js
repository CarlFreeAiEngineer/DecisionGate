import { Tokenizer } from '@huggingface/tokenizers';

export class DecisionGateError extends Error {
  constructor(code, message) { super(message); this.name = 'DecisionGateError'; this.code = code; }
}
// Match Rust str::trim's Unicode White_Space property (JS trim differs for FEFF/0085).
const blank = /^\p{White_Space}*$/u;
export function text(value, name) {
  if (typeof value !== 'string') throw new DecisionGateError('DG_INVALID_ARGUMENT', `${name} must be nonempty text`);
  let bytes = 0;
  for (let i = 0; i < value.length; ++i) {
    const c = value.charCodeAt(i);
    bytes += c < 0x80 ? 1 : c < 0x800 ? 2 : 3;
    if (c >= 0xd800 && c <= 0xdbff) {
      bytes += 1;
      const next = value.charCodeAt(++i);
      if (!(next >= 0xdc00 && next <= 0xdfff)) throw new DecisionGateError('DG_INVALID_ARGUMENT', `${name} contains an unmatched surrogate`);
    } else if (c >= 0xdc00 && c <= 0xdfff) throw new DecisionGateError('DG_INVALID_ARGUMENT', `${name} contains an unmatched surrogate`);
    if (bytes > 1_048_576) throw new DecisionGateError('DG_INPUT_TOO_LONG', `${name} exceeds the byte limit`);
  }
  if (blank.test(value)) throw new DecisionGateError('DG_INVALID_ARGUMENT', `${name} must be nonempty text`);
}
export function validate(content, question, options = {}, boolean = false, defaultThreshold = 0.5) {
  text(content, 'content'); text(question, 'question');
  if (!options || typeof options !== 'object' || Array.isArray(options)) throw new DecisionGateError('DG_INVALID_ARGUMENT', 'options must be an object');
  if (options.criteria !== undefined && options.criteria !== null) {
    if (typeof options.criteria !== 'object' || Array.isArray(options.criteria)) throw new DecisionGateError('DG_INVALID_ARGUMENT', 'criteria must contain yes and no text');
    text(options.criteria.yes, 'criteria.yes'); text(options.criteria.no, 'criteria.no');
  }
  const threshold = options.threshold === undefined ? defaultThreshold : options.threshold;
  if (boolean && (typeof threshold !== 'number' || !Number.isFinite(threshold) || threshold < 0 || threshold > 1)) throw new DecisionGateError('DG_INVALID_ARGUMENT', 'threshold must be finite and within [0, 1]');
  return threshold;
}
const MIN_OPTIONS = 2;
const MAX_OPTIONS = 256;
// Options array: 2 to 256 strings, each passing the same nonblank/byte-limit check as other text.
export function validateOptions(options) {
  if (!Array.isArray(options) || options.length < MIN_OPTIONS || options.length > MAX_OPTIONS) throw new DecisionGateError('DG_INVALID_ARGUMENT', `options must be an array of ${MIN_OPTIONS} to ${MAX_OPTIONS} strings`);
  options.forEach((option, i) => text(option, `options[${i}]`));
}
// Shares content/question/criteria/threshold checks with validate(); choose's threshold defaults to 0, not 0.5.
export function validateChoice(content, question, options, opts = {}, boolean = false) {
  validateOptions(options);
  return validate(content, question, opts, boolean, 0);
}
// Stable descending ranking of softmax probabilities over calibrated logits; ties keep caller order.
export function rank(logits) {
  const peak = Math.max(...logits);
  const weights = logits.map(z => Math.exp(z - peak));
  const total = weights.reduce((sum, w) => sum + w, 0);
  const ranking = weights.map((weight, index) => ({ index, p: weight / total }));
  if (ranking.some(({ p }) => !Number.isFinite(p) || p < 0 || p > 1)) throw new DecisionGateError('DG_INFERENCE_ERROR', 'Invalid choice probability');
  // Array.prototype.sort is a stable sort (ECMA-262); equal probabilities keep their original relative order.
  ranking.sort((a, b) => b.p - a.p);
  return ranking;
}
export function createTokenizer(json) {
  if (json.post_processor?.type !== "RobertaProcessing") throw new DecisionGateError("DG_INCOMPATIBLE", "This release requires a RoBERTa tokenizer");
  return new Tokenizer(json, {});
}
export function encode(tokenizer, manifest, content, question, criteria) {
  const prompt = criteria ? `${question}\nYes: ${criteria.yes}\nNo: ${criteria.no}` : question;
  const pair = manifest.template_version === 2 ? [content, prompt] : [prompt, content];
  const encoded = tokenizer.encode(pair[0], { text_pair: pair[1], add_special_tokens: true, return_token_type_ids: true });
  if (encoded.ids.length > manifest.max_tokens) throw new DecisionGateError('DG_INPUT_TOO_LONG', 'Input exceeds the token limit; input was not truncated');
  // RoBERTa uses one segment for both sequences; the JS tokenizer defaults to BERT segment IDs.
  encoded.token_type_ids = new Array(encoded.ids.length).fill(0);
  return encoded;
}
