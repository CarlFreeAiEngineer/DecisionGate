#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Freeze native reference probabilities, or compare another platform to them.

Float models must agree within 0.0001 with no changed decisions. A quantized model's manifest may declare a looser
`parity` tolerance, because 8-bit arithmetic rounds differently on each processor: probabilities then agree within
`probability`, and at most `max_flip_fraction` of cases may change their decision at 0.5. The frozen reference keeps
the tolerance it was frozen with."""
import argparse
import json
from pathlib import Path
import platform
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
STRICT = {'probability': 1e-4, 'max_flip_fraction': 0.0}
sys.path.insert(0, str(ROOT))
from decisiongator import Session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--reference', type=Path, default=ROOT / 'tests/fixtures/platform-parity.json')
    parser.add_argument('--freeze', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.freeze:
        if args.reference.exists():
            raise SystemExit('Reference already exists; do not overwrite a frozen baseline')
        rows = [json.loads(line) for line in (ROOT / 'data/evaluation-v2.jsonl').read_text(encoding='utf-8').splitlines()]
        rows += [dict(id='unicode-criteria', content='Please cancel Renée’s café subscription. ☕',
                      question='Is cancellation requested?',
                      criteria={'yes': 'An explicit request to cancel.', 'no': 'No cancellation request.'})]
        cases = [{key: row.get(key) for key in ('id', 'content', 'question', 'criteria')} for row in rows]
    else:
        reference = json.loads(args.reference.read_text(encoding='utf-8'))
        cases = reference['cases']
    started = time.monotonic()
    differences = []
    boolean_disagreements = []
    with Session.load(args.bundle) as session:
        manifest = session.metadata
        if not args.freeze:
            for name in ('model.onnx', 'tokenizer.json'):
                assert manifest['sha256'][name] == reference['sha256'][name], name
        for case in cases:
            actual = session.evaluate(case['content'], case['question'], case['criteria'])
            if args.freeze:
                case['probability'] = actual
            else:
                differences.append(abs(actual - case['probability']))
                for threshold in (.05, .5, .9, .95):
                    if (actual >= threshold) != (case['probability'] >= threshold):
                        boolean_disagreements.append({'id': case['id'], 'threshold': threshold})
    if args.freeze:
        args.reference.parent.mkdir(parents=True, exist_ok=True)
        args.reference.write_text(json.dumps({'platform': platform.platform(),
            'sha256': {key: manifest['sha256'][key] for key in ('model.onnx', 'tokenizer.json')},
            'temperature': manifest['temperature'], 'tolerance': manifest.get('parity', STRICT), 'cases': cases}, indent=2, ensure_ascii=False) + '\n', encoding="utf-8")
        print(f'Frozen {len(cases)} reference cases at {args.reference}')
    else:
        tolerance = reference.get('tolerance', STRICT)
        flips = sum(1 for d in boolean_disagreements if d['threshold'] == .5)
        passed = max(differences) <= tolerance['probability'] and flips <= tolerance['max_flip_fraction'] * len(cases)
        if tolerance['max_flip_fraction'] == 0 and boolean_disagreements:
            passed = False
        report = {'status': 'passed' if passed else 'failed', 'tolerance': tolerance, 'decision_changes_at_half': flips,
                  'platform': platform.platform(), 'cases': len(cases), 'max_absolute_difference': max(differences),
                  'boolean_disagreements': boolean_disagreements, 'seconds': time.monotonic() - started}
        if args.output:
            args.output.write_text(json.dumps(report, indent=2) + '\n', encoding="utf-8")
        print(json.dumps(report, indent=2))
        if report['status'] != 'passed':
            raise SystemExit(1)


if __name__ == '__main__':
    main()
