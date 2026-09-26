import { cpSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
const root = dirname(fileURLToPath(import.meta.url));
const platform = `${process.platform}-${process.arch}`;
const sourceName = { 'darwin-arm64': 'macos-arm64', 'linux-x64': 'linux-x64', 'win32-x64': 'windows-x64' }[platform];
if (!sourceName) throw new Error(`Unsupported platform ${platform}`);
const source = resolve(process.env.DECISIONGATOR_BUNDLE || join(root, '..', 'released', sourceName));
const output = join(root, 'native', platform);
mkdirSync(output, { recursive: true });
cpSync(source, output, { recursive: true });
cpSync(join(root, '..', 'LICENSE'), join(root, 'LICENSE'));
const headers = [process.env.NODE_INCLUDE_DIR, resolve(dirname(process.execPath), '../include/node'), '/opt/homebrew/include/node', '/usr/include/node'].filter(Boolean).find(p => existsSync(join(p, 'node_api.h')));
if (!headers) throw new Error('Set NODE_INCLUDE_DIR to Node headers (build machine only)');
const addon = join(output, 'decisiongator.node');
if (process.platform === 'win32') {
  const lib = process.env.NODE_LIB;
  if (!lib) throw new Error('Set NODE_LIB to the matching node.lib on the Windows build machine');
  const buildDirectory = join(root, 'build');
  mkdirSync(buildDirectory, { recursive: true });
  execFileSync('cl', ['/nologo', '/std:c++17', '/EHsc', '/LD', `/Fo${join(buildDirectory, 'addon.obj')}`,  `/I${headers}`, join(root, 'src/addon.cc'), lib, '/link', `/IMPLIB:${join(buildDirectory, 'decisiongator-addon.lib')}`, `/OUT:${addon}`], { cwd: root, stdio: 'inherit' });
} else {
  execFileSync(process.env.CXX || 'c++', ['-std=c++17', '-O2', '-shared', '-fPIC', `-I${headers}`, join(root, 'src/addon.cc'), '-o', addon, ...(process.platform === 'darwin' ? ['-undefined', 'dynamic_lookup'] : ['-ldl', '-pthread'])], { stdio: 'inherit' });
}
console.log(`Built ${addon}`);
const browser = join(root, '..', 'released', 'web');
if (existsSync(join(browser, 'index.js'))) cpSync(browser, join(root, 'web'), {recursive:true});
