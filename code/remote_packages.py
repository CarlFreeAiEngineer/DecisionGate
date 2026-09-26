#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Build and test consumer packages on the native bundle's own platform.

Run after code/build.py created released/<platform>. No training assets are
fetched. npm dependencies and, when missing, matching official Node build
headers/import library are downloaded. Windows inherits its VS developer shell.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def fetch(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as response, target.open('wb') as output:
        shutil.copyfileobj(response, output)


def node_headers(node, env, report):
    version = subprocess.check_output([node, '--version'], text=True).strip()
    if not re.fullmatch(r'v\d+\.\d+\.\d+', version):
        raise RuntimeError('Unsupported Node version: ' + version)
    if int(version.split('.')[0][1:]) < 24:
        raise RuntimeError('Node 24 or newer is required')
    report['node_version'] = version
    cache = ROOT / 'tools/node-build' / version
    cache.mkdir(parents=True, exist_ok=True)
    candidates = [Path(env['NODE_INCLUDE_DIR'])] if env.get('NODE_INCLUDE_DIR') else []
    candidates += [Path(node).resolve().parent.parent / 'include/node', Path('/usr/include/node'), Path('/opt/homebrew/include/node')]
    selected = None
    wanted = version[1:].split('.')
    for candidate in candidates:
        header = candidate / 'node_version.h'
        if not header.is_file() or not (candidate / 'node_api.h').is_file():
            continue
        text = header.read_text(encoding='utf-8')
        found = [re.search(r'#define\s+NODE_' + name + r'_VERSION\s+(\d+)', text) for name in ['MAJOR','MINOR','PATCH']]
        if all(found) and [match.group(1) for match in found] == wanted:
            selected = candidate
            break
    needs_library = os.name == 'nt' and not env.get('NODE_LIB')
    if selected is None or needs_library:
        base = f'https://nodejs.org/dist/{version}/'
        checksums_path = cache / 'SHASUMS256.txt'
        fetch(base + 'SHASUMS256.txt', checksums_path)
        checksums = {line.split()[1].lstrip('*'): line.split()[0] for line in checksums_path.read_text(encoding='utf-8').splitlines() if line.strip()}

        def verified(name):
            destination = cache / name
            expected = checksums.get(name)
            if not expected:
                raise RuntimeError('Official checksum missing: ' + name)
            if not destination.is_file() or hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
                fetch(base + name, destination)
            actual = hashlib.sha256(destination.read_bytes()).hexdigest()
            if actual != expected:
                raise RuntimeError('Node build asset checksum mismatch: ' + name)
            report.setdefault('node_build_assets', {})[name] = actual
            return destination

        if selected is None:
            archive = verified(f'node-{version}-headers.tar.gz')
            with tarfile.open(archive, 'r:gz') as source:
                for member in source.getmembers():
                    target = (cache / member.name).resolve()
                    if not target.is_relative_to(cache.resolve()) or member.issym() or member.islnk():
                        raise RuntimeError('Unsafe Node archive member')
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    elif member.isfile():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with source.extractfile(member) as stream, target.open('wb') as output:
                            shutil.copyfileobj(stream, output)
            selected = cache / f'node-{version}/include/node'
        if needs_library:
            env['NODE_LIB'] = str(verified('win-x64/node.lib'))
    env['NODE_INCLUDE_DIR'] = str(selected)
    report['node_headers'] = str(selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skip-python', action='store_true')
    parser.add_argument('--skip-node', action='store_true')
    parser.add_argument('--java', action='store_true', help='Also build and test Java with tools/jdk and tools/maven')
    parser.add_argument('--jdk', type=Path)
    parser.add_argument('--maven', type=Path)
    args = parser.parse_args()
    target = {('Darwin','arm64'):'macos-arm64',('Linux','x86_64'):'linux-x64',('Windows','AMD64'):'windows-x64',('Windows','x86_64'):'windows-x64'}.get((platform.system(),platform.machine()))
    if not target:
        raise SystemExit('Unsupported build platform: ' + platform.platform())
    if not (ROOT / 'released' / target / 'manifest.json').is_file():
        raise SystemExit('Build the native bundle first: released/' + target)
    uv = shutil.which('uv')
    if not uv:
        raise SystemExit('uv is required')
    report = {'platform':target, 'system':platform.platform(), 'steps':[], 'status':'running'}
    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    destination = reports / f'remote-packages-{target}.json'
    env = os.environ.copy()

    def run(name, command, cwd=ROOT):
        log = reports / f'remote-{target}-{name}.log'
        print(f'{name}: running (log: {log})', flush=True)
        started = time.monotonic()
        with log.open('w', encoding='utf-8') as output:
            completed = subprocess.run(list(map(str, command)), cwd=cwd, env=env, stdout=output, stderr=subprocess.STDOUT)
        report['steps'].append({'name':name,'exit_code':completed.returncode,'seconds':round(time.monotonic()-started,2),'log':str(log.relative_to(ROOT))})
        destination.write_text(json.dumps(report, indent=2)+'\n', encoding="utf-8")
        if completed.returncode:
            print(log.read_text(encoding='utf-8', errors='replace')[-8000:], flush=True)
            raise RuntimeError(f'{name} failed; see {log}')
        print(f'{name}: passed', flush=True)

    def script(path, *options):
        return [uv, 'run', '--no-project', ROOT / path, *options]

    try:
        if not args.skip_python:
            run('python-build', script('code/build_python.py', '--target', target))
            tags = {'macos-arm64':'macosx_14_0_arm64','linux-x64':'linux_x86_64','windows-x64':'win_amd64'}
            version = re.search(r"^VERSION = '([^']+)'", (ROOT / 'code/build_python.py').read_text(encoding='utf-8'), re.M).group(1)
            wheel = ROOT / 'released/python' / f'decisiongator-{version}-py3-none-{tags[target]}.whl'
            run('python-consumer', script('tests/python_wheel_check.py', wheel, '--output', reports / f'python-wheel-{target}.json'))
        if not args.skip_node:
            node = shutil.which('node')
            if not node:
                raise RuntimeError('Install Node 24+ and npm with the platform package manager')
            node_headers(node, env, report)
            # Resolve npm's JavaScript entry without invoking .cmd through a shell.
            helper = "import {npmCommand} from './npm-command.mjs'; console.log(JSON.stringify(npmCommand([])));"
            command = json.loads(subprocess.check_output([node,'--input-type=module','-e',helper],cwd=ROOT/'javascript',env=env,text=True))
            npm_node, npm_args = command
            env['NODE_NPM_CLI'] = npm_args[0]
            run('node-dependencies', [npm_node,*npm_args,'ci','--ignore-scripts','--no-audit','--no-fund'], ROOT/'javascript')
            run('node-build', [node, ROOT/'javascript/build.mjs'])
            run('node-tests', [node,'--test',ROOT/'javascript/test/component.test.mjs'])
            run('node-pack', [node,ROOT/'javascript/pack.mjs'])
            run('node-consumer', [node,ROOT/'javascript/test/consumer.mjs'])
        if args.java:
            options = ['--install']
            if args.jdk: options += ['--jdk', args.jdk]
            if args.maven: options += ['--maven', args.maven]
            run('java-build', script('java/build.py', *options))
            run('java-consumer', script('java/check_bundle.py', *(['--jdk',args.jdk] if args.jdk else [])))
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = str(error)
        raise
    finally:
        destination.write_text(json.dumps(report, indent=2)+'\n', encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
