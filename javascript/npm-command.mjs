import { existsSync, realpathSync } from 'node:fs';
import { dirname, join, delimiter } from 'node:path';
export function npmCommand(args) {
  const candidates=[process.env.NODE_NPM_CLI,process.env.npm_execpath];
  for (const folder of [dirname(process.execPath),...(process.env.PATH||'').split(delimiter)]) {
    candidates.push(join(folder,'node_modules/npm/bin/npm-cli.js'),join(folder,'../lib/node_modules/npm/bin/npm-cli.js'));
    const executable=join(folder,'npm');
    if (existsSync(executable)) candidates.push(realpathSync(executable));
  }
  const cli=candidates.find(p=>p&&existsSync(p)&&p.endsWith('.js'));
  if (!cli) throw new Error('Set NODE_NPM_CLI to npm/bin/npm-cli.js');
  return [process.execPath,[cli,...args]];
}
