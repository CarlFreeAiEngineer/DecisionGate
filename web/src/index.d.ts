export interface Criteria { yes: string; no: string }
export interface Options { criteria?: Criteria | null }
export interface BooleanOptions extends Options { threshold?: number }
export interface Choice { index: number; p: number }
export class DecisionGatorError extends Error { readonly code: string; constructor(code: string, message: string) }
/** Returns the estimated chance of yes. Initializes the local component on first use. */
export function isYesP(content: string, question: string, options?: Options): Promise<number>;
/** Inclusive comparison: isYesP(...) >= threshold (default 0.5). */
export function isYes(content: string, question: string, options?: BooleanOptions): Promise<boolean>;
/** Ranks 2 to 256 options by estimated probability, best first; probabilities sum to one. */
export function chooseP(content: string, question: string, options: string[], opts?: Options): Promise<Choice[]>;
/** Index of the best option, or -1 when its probability is below opts.threshold (default 0, inclusive). */
export function choose(content: string, question: string, options: string[], opts?: BooleanOptions): Promise<number>;
export interface Progress { file: string; loaded: number; total: number }
/** Advanced hosting settings; call before first use or after close(). onProgress is called while each asset downloads. */
export function configure(options?: {assetBaseUrl?: string | URL; workerUrl?: string | URL; maxQueue?: number; onProgress?: (progress: Progress) => void}): void;
/** Terminates the worker and rejects pending calls. Later calls restart automatically. */
export function close(): void;
