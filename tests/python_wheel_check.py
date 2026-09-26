#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Install a local wheel into an isolated consumer and exercise it offline."""
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CONSUMER = '''
import concurrent.futures, json, pathlib, decisiongator
from decisiongator import is_yes, is_yes_p, DecisionGatorError
text = "Please cancel my subscription before the next renewal."
question = "Is the customer asking to cancel their subscription?"
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    values = list(pool.map(lambda _: is_yes_p(text, question), range(8)))
assert max(values) - min(values) < 1e-12
p = values[0]
assert is_yes(text, question) == (p >= .5)
assert is_yes(text, question, threshold=p)
assert is_yes(text, question, threshold=0)
assert not is_yes(text, question, threshold=1)
for threshold in (True, -1, 2, float('nan'), float('inf')):
    try: is_yes(text, question, threshold=threshold)
    except ValueError: pass
    else: raise AssertionError('invalid threshold accepted')
try: is_yes('', question)
except DecisionGatorError: pass
else: raise AssertionError('empty text accepted')
custom = is_yes_p(text, question, {'yes': 'An explicit cancellation request.', 'no': 'Anything else.'})
assert 0 <= custom <= 1
bundle = pathlib.Path(decisiongator.__file__).parent / '_bundle'
assert (bundle / 'model.onnx').is_file()
print(json.dumps({'probability': p, 'custom_probability': custom, 'module': decisiongator.__file__, 'concurrent_calls': 8}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wheel', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/python-wheel.json')
    parser.add_argument('--network-namespace', action='store_true')
    args = parser.parse_args()
    if args.network_namespace and (platform.system() != 'Linux' or {name for _,name in socket.if_nameindex()} != {'lo'}):
        raise SystemExit('--network-namespace requires Linux with only loopback available')
    with tempfile.TemporaryDirectory(prefix='decisiongator-wheel-') as temporary:
        directory = Path(temporary)
        wheel = directory / args.wheel.name
        shutil.copy2(args.wheel, wheel)
        command = [shutil.which('uv'), 'run', '--offline', '--no-project', '--isolated',
                   '--with', str(wheel), 'python', '-I', '-c', CONSUMER]
        denied = platform.system() == 'Darwin'
        if denied:
            policy = '(version 1)(allow default)(deny network*)(deny file-read* (subpath ' + json.dumps(str(ROOT)) + '))'
            command = ['sandbox-exec', '-p', policy, *command]
        env = os.environ.copy()
        env.pop('PYTHONPATH', None)
        result = subprocess.run(command, cwd=directory, env=env, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + '\n' + result.stderr)
        report = {'status': 'passed', 'platform': platform.platform(), 'wheel': args.wheel.name,
                  'network_denied': denied or args.network_namespace, 'checkout_read_denied': denied,
                  'network_isolation': 'Linux network namespace (loopback only)' if args.network_namespace else 'macOS sandbox' if denied else None,
                  'consumer': json.loads(result.stdout), 'stderr': result.stderr}
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
