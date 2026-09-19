#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Compile a C host, relocate its bundle, and test without development tools.

Mac denies networking with sandbox-exec. Linux uses an isolated network
namespace when unshare permits it. Windows reports network denial as untested;
this helper does not install or change machine-wide firewall rules.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def clean_environment(temporary):
    if platform.system() == 'Windows':
        windows = Path(os.environ.get('SystemRoot', r'C:\Windows'))
        return {'PATH': str(windows / 'System32'), 'SystemRoot': str(windows),
                'WINDIR': str(windows), 'TEMP': str(temporary), 'TMP': str(temporary),
                'USERPROFILE': str(temporary)}
    empty_path = temporary / 'empty-path'
    empty_path.mkdir()
    return {'PATH': str(empty_path), 'HOME': str(temporary),
            'TMPDIR': str(temporary), 'LANG': 'C'}


def compile_host(temporary, bundle):
    system = platform.system()
    source = ROOT / 'examples/c_smoke.c'
    if system == 'Windows':
        # Windows resolves imported DLLs beside the executable. Place the host
        # there, while its working directory remains separate from the bundle.
        host = bundle / 'host.exe'
        command = ['cl.exe', '/nologo', '/W4', '/WX', str(source), '/I' + str(bundle),
                   '/Fe:' + str(host), '/Fo:' + str(temporary / 'host.obj'), '/link',
                   str(bundle / 'decisiongate.lib')]
    else:
        host = temporary / 'host'
        origin = '@executable_path/bundle' if system == 'Darwin' else '$ORIGIN/bundle'
        command = ['cc', '-Wall', '-Wextra', '-Werror', str(source), '-I', str(bundle),
                   '-L', str(bundle), '-ldecisiongate', '-Wl,-rpath,' + origin, '-o', str(host)]
    subprocess.run(command, check=True)
    return host


def check_links(host, original_bundle, compile_directory):
    system = platform.system()
    if system == 'Darwin':
        links = subprocess.check_output(['otool', '-L', str(host)], text=True)
        if '@rpath/libdecisiongate.dylib' not in links:
            raise AssertionError(f'C host does not use the relative native library: {links}')
        details = links.splitlines()[1:]  # Exclude tool's heading containing host path.
    elif system == 'Linux':
        links = subprocess.check_output(['readelf', '-d', str(host)], text=True)
        if '$ORIGIN/bundle' not in links or '[libdecisiongate.so]' not in links:
            raise AssertionError(f'C host is missing its relative library lookup: {links}')
        details = links.splitlines()
    else:
        links = subprocess.check_output(['dumpbin.exe', '/dependents', str(host)], text=True)
        if 'decisiongate.dll' not in links.lower():
            raise AssertionError(f'C host does not import decisiongate.dll: {links}')
        details = [line for line in links.splitlines() if re.match(r'^\s+[^\s]+\.dll\s*$', line, re.I)]
    for location in (ROOT, original_bundle, compile_directory):
        if any(str(location) in line for line in details):
            raise AssertionError(f'C host retains a build path in its library dependencies: {location}')
    return details


def network_command(environment):
    system = platform.system()
    if system == 'Darwin':
        sandbox = shutil.which('sandbox-exec', path='/usr/bin:/bin')
        if not sandbox:
            raise RuntimeError('sandbox-exec is required for the Mac offline check')
        return [sandbox, '-p', '(version 1)(allow default)(deny network*)'], True, 'denied by macOS sandbox'
    if system == 'Linux':
        unshare = shutil.which('unshare', path='/usr/bin:/bin')
        if not unshare:
            return [], False, 'not verified: unshare is unavailable'
        prefix = [unshare, '--user', '--map-root-user', '--net', '--']
        probe = subprocess.run(prefix + ['/bin/true'], env=environment, text=True, capture_output=True)
        if probe.returncode == 0:
            return prefix, True, 'isolated Linux user/network namespace; no external network interfaces'
        detail = ' '.join(probe.stderr.split())[:300]
        return [], False, f'not verified: network namespace unavailable ({detail})'
    return [], False, 'not verified on Windows: no firewall or system policy changes made'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    original_bundle = args.bundle.resolve()
    names = {'Darwin': 'libdecisiongate.dylib', 'Linux': 'libdecisiongate.so', 'Windows': 'decisiongate.dll'}
    if platform.system() not in names:
        raise SystemExit('Supported check hosts: Mac, Linux, and Windows')
    library_name = names[platform.system()]
    with tempfile.TemporaryDirectory(prefix='decisiongate-relocation-') as directory:
        temporary = Path(directory)
        # Compile first, then move the complete tree. A retained absolute path
        # to the compilation directory cannot satisfy the later execution.
        compilation = temporary / 'compile'
        compilation.mkdir()
        bundle = compilation / 'bundle'
        shutil.copytree(original_bundle, bundle)
        host = compile_host(compilation, bundle)
        linked_libraries = check_links(host, original_bundle, compilation)
        relative_host = host.relative_to(compilation)
        relocated = temporary / 'relocated'
        compilation.rename(relocated)
        host, bundle = relocated / relative_host, relocated / 'bundle'
        work = temporary / 'working-directory'
        work.mkdir()
        environment = clean_environment(temporary)
        prefix, denied, network = network_command(environment)
        command = prefix + [str(host)]
        timed = platform.system() == 'Darwin'
        if timed:
            command = ['/usr/bin/time', '-l'] + command
        process = subprocess.run(command, cwd=work, env=environment, text=True, capture_output=True, check=True)
        match = re.search(r'(\d+)\s+maximum resident set size', process.stderr) if timed else None
        result = {'status': 'passed', 'platform': platform.platform(), 'exit_code': process.returncode,
                  'network': network, 'network_denial_verified': denied,
                  'relocated': True, 'working_directory_separate': True,
                  'development_tools_on_path': False, 'stdout': process.stdout.strip(),
                  'native_process_peak_rss_bytes': int(match.group(1)) if match else None,
                  'bundle_bytes': sum(p.stat().st_size for p in bundle.rglob('*') if p.is_file()),
                  'library_bytes': (bundle / library_name).stat().st_size,
                  'model_bytes': (bundle / 'model.onnx').stat().st_size,
                  'host_link_dependencies': linked_libraries}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding="utf-8")
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
