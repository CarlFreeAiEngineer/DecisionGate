// DecisionGator from Node.js 24 or later. Run from examples/node: node example.mjs
// It installs the package for this computer from released/node/ on first run; an application
// would run `npm install` on that .tgz file once instead.
import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';

const here = new URL('.', import.meta.url);
if (!existsSync(new URL('node_modules/decisiongator', here))) {
  const archive = `../../released/node/decisiongator-0.4.1-${process.platform}-${process.arch}.tgz`;
  execFileSync('npm', ['install', '--no-save', '--no-package-lock', archive],
               { cwd: here, stdio: 'inherit', shell: process.platform === 'win32' });
}
const { isYes, isYesP, chooseP } = await import('decisiongator');

const ticket = "Our whole warehouse can't print shipping labels and trucks leave in an hour.";
const question = 'Is the customer describing an urgent problem?';

// A yes/no decision at the usual 0.5 cutoff. Always await; a Promise itself is truthy.
console.log('urgent:', await isYes(ticket, question));

// The probability, so you can keep an uncertain range for a person.
console.log(`p_yes = ${(await isYesP(ticket, question)).toFixed(3)}`);

// Criteria and a stricter threshold.
const criteria = {
  yes: 'Work is blocked and there is a deadline within hours.',
  no: 'The problem is an inconvenience with no near deadline.',
};
console.log('confident urgent:', await isYes(ticket, question, { criteria, threshold: 0.9 }));

// Several options instead of yes or no.
const teams = ['billing', 'technical support', 'sales'];
for (const { index, p } of await chooseP("My card was charged twice for last month's invoice.",
                                         'Which team should handle this message?', teams))
  console.log(`${teams[index].padEnd(18)} ${p.toFixed(3)}`);
