export interface Criteria { yes: string; no: string; }
export interface DecisionOptions { criteria?: Criteria | null; threshold?: number; }
export interface Choice { index: number; p: number; }
export interface ChooseOptions { criteria?: Criteria | null; threshold?: number; }
export declare class DecisionGatorError extends Error { readonly code: string; constructor(code: string, message: string); }
export declare function isYes(content: string, question: string, options?: DecisionOptions): Promise<boolean>;
export declare function isYesP(content: string, question: string, options?: DecisionOptions): Promise<number>;
export declare function choose(content: string, question: string, options: string[], opts?: ChooseOptions): Promise<number>;
export declare function chooseP(content: string, question: string, options: string[], opts?: ChooseOptions): Promise<Choice[]>;
