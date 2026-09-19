#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Publish the local released/ tree to https://ordinarydata.com/DecisionGate/files/<version>/.

Maintainers only: needs SSH access to the web host. Writes SHA256SUMS.txt from
the local files, then copies everything with rsync into a versioned folder.
code/fetch_released.py reads that same SHA256SUMS.txt, so publishing a version
is what makes it downloadable.

  uv run code/publish_released.py --version 0.3.0
  uv run code/publish_released.py --version 0.3.0 --dry-run
"""
import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = 'ace@ordinarydata.com'
DEFAULT_REMOTE_DIR = 'domains/ordinarydata.com/DecisionGate/files'
SKIP_DIRS = {'__pycache__', 'node_modules'}


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def write_sums(source):
    lines = [f'# DecisionGate release files. Verify with: sha256sum -c SHA256SUMS.txt']
    for path in sorted(source.rglob('*')):
        if not path.is_file() or path.name == 'SHA256SUMS.txt' or path.suffix == '.part':
            continue
        if SKIP_DIRS & set(path.relative_to(source).parts):
            continue
        lines.append(f'{sha256(path)}  {path.relative_to(source).as_posix()}')
    (source / 'SHA256SUMS.txt').write_text('\n'.join(lines) + '\n')
    return len(lines) - 1


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version', required=True, help='folder name on the server, for example 0.3.0')
    parser.add_argument('--source', type=Path, default=ROOT / 'released')
    parser.add_argument('--host', default=DEFAULT_HOST)
    parser.add_argument('--remote-dir', default=DEFAULT_REMOTE_DIR, help='path under the SSH user home')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    if not shutil.which('rsync'):
        sys.exit('rsync is required; install it with your package manager')
    if not args.source.is_dir():
        sys.exit(f'{args.source} does not exist')
    count = write_sums(args.source)
    print(f'{count} files listed in {args.source / "SHA256SUMS.txt"}')

    destination = f'{args.host}:{args.remote_dir}/{args.version}/'
    subprocess.run(['ssh', args.host, f'mkdir -p {args.remote_dir}/{args.version}'], check=True)
    command = ['rsync', '-az', '--partial', '--info=progress2', '--chmod=D755,F644']  # web server must be able to read
    command += [f'--exclude={d}' for d in SKIP_DIRS] + ['--exclude=*.part']
    if args.dry_run:
        command.append('--dry-run')
    command += [f'{args.source}/', destination]
    subprocess.run(command, check=True)
    print(f'published {args.version} to https://ordinarydata.com/DecisionGate/files/{args.version}/')


if __name__ == '__main__':
    main()
