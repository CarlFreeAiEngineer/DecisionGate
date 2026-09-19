#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Install a pinned, checkout-local Rust toolchain using rustup, or copy one.

Run: uv run code/setup.py
Or:  uv run code/setup.py --rust-from /path/to/matching/rust/toolchain
Requires rustup on PATH for installation; obtain it with the OS package manager.
Global rustup settings and the user's shell configuration are not changed.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from build import ROOT, host_target, sha256

RUST_VERSION = '1.98.1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rust-from', type=Path, help='Copy an existing toolchain directory containing bin/rustc and bin/cargo')
    args = parser.parse_args()
    _, target, _, _ = host_target()
    destination = ROOT / 'tools/rust'
    suffix = '.exe' if os.name == 'nt' else ''
    if destination.exists():
        raise SystemExit(f'{destination} already exists; existing tools are not overwritten.')
    if args.rust_from:
        source = args.rust_from.resolve()
        provenance = {'method': 'copy', 'source': str(source)}
    else:
        rustup = shutil.which('rustup')
        if not rustup:
            raise SystemExit('rustup not found. Install it with the OS package manager, or provide --rust-from TOOLCHAIN_DIRECTORY.')
        env = os.environ.copy()
        env['RUSTUP_HOME'] = str(ROOT / 'tools/rustup')
        env['CARGO_HOME'] = str(ROOT / 'tools/rustup-cargo')
        name = f'{RUST_VERSION}-{target}'
        subprocess.run([rustup, 'toolchain', 'install', name, '--profile', 'minimal', '--no-self-update'], env=env, check=True)
        executable = subprocess.check_output([rustup, 'which', '--toolchain', name, 'rustc'], env=env, text=True).strip()
        source = Path(executable).resolve().parent.parent
        provenance = {'method': 'rustup', 'toolchain': name, 'source': 'https://static.rust-lang.org', 'verification': 'rustup verifies distribution checksums'}
    rustc, cargo = source / 'bin' / ('rustc' + suffix), source / 'bin' / ('cargo' + suffix)
    if not rustc.is_file() or not cargo.is_file():
        raise SystemExit('Source is not a Rust toolchain: bin/rustc and bin/cargo are required.')
    details = subprocess.check_output([str(rustc), '-vV'], text=True)
    if f'release: {RUST_VERSION}\n' not in details or f'host: {target}\n' not in details:
        raise SystemExit(f'Expected Rust {RUST_VERSION} for {target}; source reports:\n{details}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, symlinks=False)
    provenance.update({'rust_version': RUST_VERSION, 'target': target, 'rustc_sha256': sha256(rustc), 'cargo_sha256': sha256(cargo)})
    (ROOT / 'tools/rust-toolchain.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding="utf-8")
    print(f'Local Rust ready: {destination}')


if __name__ == '__main__':
    main()
