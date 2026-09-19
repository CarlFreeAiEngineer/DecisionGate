#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Build and test the current host's native DecisionGate bundle.

Existing model exports need no training dependencies. Supply --runtime-dir with
an extracted ONNX Runtime 1.22.1 CPU package, or let uv supply the runtime:
  uv run --python 3.12 --with onnxruntime==1.22.1 code/build.py --model MODEL --output BUNDLE
Uses only project-local Rust under tools/rust; see code/setup.py.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
ORT_VERSION = '1.22.1'
TARGETS = {
    ('Darwin', 'arm64'): ('macos-arm64', 'aarch64-apple-darwin', 'libdecisiongate.dylib', 'libonnxruntime.dylib'),
    ('Windows', 'x86_64'): ('windows-x64', 'x86_64-pc-windows-msvc', 'decisiongate.dll', 'onnxruntime.dll'),
    ('Linux', 'x86_64'): ('linux-x64', 'x86_64-unknown-linux-gnu', 'libdecisiongate.so', 'libonnxruntime.so'),
}


def host_target():
    machine = platform.machine().lower()
    machine = {'amd64': 'x86_64', 'aarch64': 'arm64'}.get(machine, machine)
    try:
        target = TARGETS[(platform.system(), machine)]
    except KeyError:
        raise SystemExit(f'Unsupported native build host: {platform.system()} {machine}')
    if platform.system() == 'Linux' and platform.libc_ver()[0] != 'glibc':
        raise SystemExit('Linux builds require glibc; musl/Alpine is not a supported target.')
    return target


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def runtime_location(explicit, runtime_name):
    roots = [Path(explicit).resolve()] if explicit else []
    if not explicit:
        spec = importlib.util.find_spec('onnxruntime')
        if spec and spec.origin:
            roots.append(Path(spec.origin).parent)
        roots.extend(sorted((ROOT / '.venv/lib').glob('python*/site-packages/onnxruntime')))
        roots.append(ROOT / '.venv/Lib/site-packages/onnxruntime')
    filenames = [runtime_name]
    if platform.system() == 'Darwin':
        filenames.insert(0, f'libonnxruntime.{ORT_VERSION}.dylib')
    elif platform.system() == 'Linux':
        filenames.insert(0, f'libonnxruntime.so.{ORT_VERSION}')
    for root in roots:
        for directory in (root, root / 'lib', root / 'capi'):
            for name in filenames:
                candidate = directory / name
                if candidate.is_file():
                    return root, candidate
    raise SystemExit('ONNX Runtime 1.22.1 not found. Use --runtime-dir PACKAGE_DIRECTORY or uv run --python 3.12 --with onnxruntime==1.22.1 code/build.py ...')


def check_runtime(runtime):
    # A separate process checks architecture, dependent libraries, and the actual
    # runtime version without importing the Python ONNX package or loading a model.
    program = '''import ctypes as c, sys
class ApiBase(c.Structure):
    _fields_ = [('get_api', c.c_void_p), ('get_version', c.CFUNCTYPE(c.c_char_p))]
runtime = c.CDLL(sys.argv[1])
runtime.OrtGetApiBase.restype = c.POINTER(ApiBase)
print(runtime.OrtGetApiBase().contents.get_version().decode())
'''
    checked = subprocess.run([sys.executable, '-c', program, str(runtime)], capture_output=True, text=True)
    if checked.returncode or checked.stdout.strip() != ORT_VERSION:
        hint = ' On Windows, install the Microsoft Visual C++ 2015-2022 x64 Redistributable; a DLL can exist but fail to load when its dependencies are missing.' if platform.system() == 'Windows' else ''
        raise SystemExit(f'Expected a loadable ONNX Runtime {ORT_VERSION} for this host.{hint} Got: {checked.stdout.strip()} {checked.stderr.strip()}')


def rust_environment(target):
    compiler = ROOT / 'tools/rust/bin'
    suffix = '.exe' if platform.system() == 'Windows' else ''
    cargo, rustc = compiler / ('cargo' + suffix), compiler / ('rustc' + suffix)
    if not cargo.is_file() or not rustc.is_file():
        raise SystemExit('Missing project-local Rust. Run uv run code/setup.py --help.')
    env = os.environ.copy()
    env['PATH'] = str(compiler) + os.pathsep + env.get('PATH', '')
    env['CARGO_HOME'] = str(ROOT / 'tools/cargo-home')
    env['CARGO_TARGET_DIR'] = str(ROOT / 'code/target')
    details = subprocess.check_output([str(rustc), '-vV'], text=True, env=env)
    if f'host: {target}\n' not in details:
        raise SystemExit(f'Project-local Rust is not native target {target}:\n{details}')
    if platform.system() == 'Windows':
        missing = [name for name in ('cl.exe', 'link.exe', 'dumpbin.exe') if not shutil.which(name, path=env['PATH'])]
        if missing:
            raise SystemExit('Run in an x64 Native Tools shell for Visual Studio Build Tools (C++ workload and Windows SDK). Missing: ' + ', '.join(missing))
        if env.get('VSCMD_ARG_TGT_ARCH', 'x64').lower() != 'x64':
            raise SystemExit('Visual Studio must target x64. Reopen an x64 Native Tools shell.')
    elif not shutil.which('cc', path=env['PATH']):
        raise SystemExit('A C compiler/linker is required: Apple command-line tools or Linux build-essential.')
    return compiler, cargo, env, details


def crate_notices(output):
    destination_root = output / 'notices/rust-crates'
    destination_root.mkdir()
    packages = []
    lock = tomllib.loads((ROOT / 'code/Cargo.lock').read_text(encoding='utf-8'))
    for package in lock['package']:
        if 'source' not in package:
            continue
        name = package['name'] + '-' + package['version']
        matches = list((ROOT / 'tools/cargo-home/registry/src').glob('*/' + name))
        if not matches:
            continue  # Platform-specific crates not downloaded for this build.
        crate = matches[0]
        info = tomllib.loads((crate / 'Cargo.toml').read_text(encoding='utf-8'))['package']
        destination = destination_root / name
        destination.mkdir()
        for item in crate.rglob('*'):
            if item.is_file() and item.name.lower().startswith(('license', 'copying', 'notice', 'copyright')):
                relative = item.relative_to(crate)
                (destination / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, destination / relative)
        packages.append({'name': package['name'], 'version': package['version'], 'license': info.get('license'), 'repository': info.get('repository')})
    (destination_root / 'index.json').write_text(json.dumps(packages, indent=2) + '\n', encoding="utf-8")


def native_checks(output, env):
    source = ROOT / 'examples/c_smoke.c'
    executable = output / ('c_smoke.exe' if platform.system() == 'Windows' else 'c_smoke')
    if platform.system() == 'Windows':
        command = ['cl.exe', '/nologo', '/W4', '/WX', str(source), '/I' + str(output), '/Fe:' + str(executable), '/Fo:' + str(ROOT / 'code/target/c_smoke.obj'), '/link', str(output / 'decisiongate.lib')]
    else:
        command = ['cc', '-Wall', '-Wextra', '-Werror', '-I' + str(output), str(source), '-L' + str(output), '-ldecisiongate', '-Wl,-rpath,' + str(output), '-o', str(executable)]
    subprocess.run(command, env=env, check=True)
    subprocess.run([str(executable)], cwd=output, env=env, check=True)
    subprocess.run([sys.executable, str(ROOT / 'tests/native_check.py'), '--bundle', str(output)], env=env, check=True)
    checks = ['Rust unit tests', 'C host load/inference/exit', 'native ABI and Python tests']
    reference = json.loads((ROOT / 'tests/fixtures/platform-parity.json').read_text(encoding='utf-8'))
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    if all(manifest['sha256'].get(name) == digest for name, digest in reference['sha256'].items()) and manifest.get('temperature', 1.0) == reference['temperature']:
        subprocess.run([sys.executable, str(ROOT / 'tests/platform_parity.py'), '--bundle', str(output), '--output', str(output / 'platform-parity.json')], env=env, check=True)
        checks.append('frozen platform parity cases')
    else:
        (output / 'platform-parity.json').write_text(json.dumps({'status': 'not applicable', 'reason': 'This model differs from the frozen reference. Freeze a new reference with tests/platform_parity.py before claiming cross-platform parity.'}, indent=2) + '\n', encoding="utf-8")
    return checks


def dependency_report(output, library_name, runtime_name, env):
    """Record dependencies from the actual binaries, without guessing from host OS."""
    report = {'platform': platform.platform(), 'binaries': {}}
    for name in (library_name, runtime_name):
        binary = output / name
        if platform.system() == 'Darwin':
            linked = subprocess.check_output(['otool', '-arch', 'arm64', '-L', str(binary)], text=True, env=env)
            headers = subprocess.check_output(['otool', '-arch', 'arm64', '-l', str(binary)], text=True, env=env)
            versions = []
            for block in headers.split('Load command'):
                if 'cmd LC_BUILD_VERSION' in block:
                    versions.extend(re.findall(r'^\s*minos\s+(\d+(?:\.\d+)+)', block, re.M))
                elif 'cmd LC_VERSION_MIN_MACOSX' in block:
                    versions.extend(re.findall(r'^\s*version\s+(\d+(?:\.\d+)+)', block, re.M))
            report['binaries'][name] = {'minimum_macos': versions, 'linked_libraries': linked.splitlines()[1:]}
        elif platform.system() == 'Linux':
            if not shutil.which('readelf', path=env['PATH']):
                raise SystemExit('readelf (binutils) is required to record Linux binary compatibility.')
            symbols = subprocess.check_output(['readelf', '--version-info', str(binary)], text=True, env=env)
            dynamic = subprocess.check_output(['readelf', '-d', str(binary)], text=True, env=env)
            required = {}
            for namespace in ('GLIBC', 'GLIBCXX', 'CXXABI'):
                versions = set(re.findall(r'\b' + namespace + r'_(\d+(?:\.\d+)+)', symbols))
                required[namespace] = max(versions, key=lambda value: tuple(map(int, value.split('.')))) if versions else None
            report['binaries'][name] = {'minimum_symbol_versions': required, 'needed_libraries': re.findall(r'\(NEEDED\).*?\[(.*?)\]', dynamic)}
        else:
            dependencies = subprocess.check_output(['dumpbin.exe', '/dependents', str(binary)], text=True, env=env)
            report['binaries'][name] = {'needed_libraries': re.findall(r'^\s+([^\s]+\.dll)\s*$', dependencies, re.M | re.I)}
    report['limits'] = 'Binary metadata is a compatibility floor, not validation on older OS releases or every CPU. Native runtime checks ran only on the recorded build host.'
    if platform.system() == 'Windows':
        report['system_runtime'] = 'Microsoft Visual C++ 2015-2022 x64 Redistributable; minimum Windows release requires testing.'
    (output / 'system-dependencies.json').write_text(json.dumps(report, indent=2) + '\n', encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--runtime-dir', help='Extracted ONNX Runtime 1.22.1 CPU package, or Python onnxruntime package directory')
    args = parser.parse_args()
    platform_id, target, library_name, runtime_name = host_target()
    source, output = Path(args.model).resolve(), Path(args.output).resolve()
    if output.exists():
        raise SystemExit('Output exists; choose a fresh directory to preserve rollback')
    manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    for name in ('model.onnx', 'tokenizer.json'):
        if sha256(source / name) != manifest['sha256'].get(name):
            raise SystemExit(f'Source asset hash mismatch: {name}')
    runtime_root, runtime = runtime_location(args.runtime_dir, runtime_name)
    check_runtime(runtime)
    compiler, cargo, env, rust_details = rust_environment(target)
    for command in ('test', 'build'):
        subprocess.run([str(cargo), command, '--release', '--locked', '--manifest-path', str(ROOT / 'code/Cargo.toml')], env=env, check=True)
    # Only model assets are reused; old platform headers/library hashes must not
    # imply that absent files from a previous bundle are included in this one.
    manifest['sha256'] = {name: manifest['sha256'][name] for name in ('model.onnx', 'tokenizer.json')}
    output.mkdir(parents=True)
    for filename in ('model.onnx', 'tokenizer.json'):
        shutil.copy2(source / filename, output / filename)
    shutil.copy2(ROOT / 'code/target/release' / library_name, output / library_name)
    if platform.system() == 'Darwin':
        subprocess.run(['install_name_tool', '-id', '@rpath/' + library_name, str(output / library_name)], check=True)
        subprocess.run(['codesign', '--force', '--sign', '-', str(output / library_name)], check=True)
    shutil.copy2(runtime, output / runtime_name)
    if platform.system() == 'Windows':
        shutil.copy2(ROOT / 'code/target/release/decisiongate.dll.lib', output / 'decisiongate.lib')
        (output / 'DEPLOYMENT.md').write_text('''# Windows deployment

This bundle targets Windows x64. Keep the DLLs, model, tokenizer, and manifest together. C applications link against `decisiongate.lib` and load `decisiongate.dll`; place the DLLs beside the application executable or configure its DLL search directory explicitly.

The destination machine needs the Microsoft Visual C++ 2015–2022 x64 Redistributable. These Microsoft runtime DLLs are system prerequisites and are not included in this bundle. Installing Visual Studio, Rust, Python, or Node is unnecessary for a C application using the bundle. Install the redistributable through your package manager (`winget install --id Microsoft.VCRedist.2015+.x64 --exact`) or use the [official Microsoft distribution](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

See `system-dependencies.json` for DLL imports and the build host. A passing build or relocation check establishes behavior on that host; it does not certify older Windows releases. Relocation tests remove developer tools from PATH but retain installed Windows system runtimes.

Do not unload DecisionGate with FreeLibrary. Join inference threads before process exit and do not call DecisionGate from exit hooks.
''', encoding='utf-8')
    provider = runtime.parent / ('onnxruntime_providers_shared.dll' if platform.system() == 'Windows' else 'libonnxruntime_providers_shared.so')
    if provider.is_file():
        shutil.copy2(provider, output / provider.name)
    shutil.copy2(ROOT / 'code/include/decisiongate.h', output / 'decisiongate.h')
    (output / 'notices').mkdir()
    for name in ('LICENSE', 'ThirdPartyNotices.txt'):
        candidate = runtime_root / name
        if not candidate.is_file():
            raise SystemExit(f'Runtime package is missing required notice: {candidate}')
        shutil.copy2(candidate, output / 'notices' / ('onnxruntime-' + name))
    if (ROOT / 'notices').exists():
        shutil.copytree(ROOT / 'notices', output / 'notices', dirs_exist_ok=True)
    shutil.copy2(ROOT / 'LICENSE', output / 'notices/DecisionGate-LICENSE.txt')
    crate_notices(output)
    for asset in output.iterdir():
        if asset.is_file():
            manifest['sha256'][asset.name] = sha256(asset)
    manifest['build'] = {
        'platform': platform.platform(), 'target': target, 'platform_id': platform_id,
        'rustc': rust_details.splitlines()[0],
        'cargo_lock_sha256': sha256(ROOT / 'code/Cargo.lock'),
        'onnxruntime': ORT_VERSION, 'status': 'experimental native prototype',
        'build_host_libc': platform.libc_ver() if platform.system() == 'Linux' else None,
        'system_dependencies': 'Microsoft Visual C++ 2015-2022 x64 Redistributable' if platform.system() == 'Windows' else 'Host system libraries; inspect linked dependencies before redistribution',
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding="utf-8")
    dependency_report(output, library_name, runtime_name, env)
    checks = native_checks(output, env)
    (output / 'build-checks.json').write_text(json.dumps({'status': 'passed', 'checks': checks, 'platform_id': platform_id}, indent=2) + '\n', encoding="utf-8")
    print(f'Built and tested bundle: {output}')


if __name__ == '__main__':
    main()
