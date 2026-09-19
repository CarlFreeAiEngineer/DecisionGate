"""Compare each candidate's evaluate() output JSON against the float reference.

Reads reports/shrink/<name>-<split>.json (produced by `decisiongate-train evaluate`)
and reports/shrink/float-<split>.json, matches predictions by record id, and prints
a compact table plus a JSON summary file per candidate.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHRINK = ROOT / 'reports/shrink'

CANDIDATES = [
    'shrink-1-int8-matmul',
    'shrink-2-int8-matmul-embed',
    'shrink-3a-static-qdq-minmax',
    'shrink-3b-static-qdq-percentile',
    'shrink-3c-static-qdq-percentile-noclf',
    'shrink-4-fp16',
    'shrink-5-int8-ffn-only',
]
SPLITS = ['validation', 'test']


def load(name, split):
    path = SHRINK / f'{name}-{split}.json'
    if not path.exists():
        return None
    return json.loads(path.read_text())


def compare(float_result, candidate_result):
    float_p = {p['id']: p['p_yes'] for p in float_result['predictions']}
    cand_p = {p['id']: p['p_yes'] for p in candidate_result['predictions']}
    ids = sorted(set(float_p) & set(cand_p))
    diffs = [abs(float_p[i] - cand_p[i]) for i in ids]
    flips = sum((float_p[i] >= .5) != (cand_p[i] >= .5) for i in ids)
    return {
        'n': len(ids),
        'max_abs_diff': max(diffs) if diffs else None,
        'mean_abs_diff': sum(diffs) / len(diffs) if diffs else None,
        'flips': flips,
    }


def main():
    summary = {}
    for split in SPLITS:
        float_result = load('float', split)
        for name in CANDIDATES:
            for variant, suffix in (('default', ''), ('recal', '-recal')):
                cand_name = f'{name}{suffix}'
                cand_result = load(cand_name, split)
                if cand_result is None:
                    continue
                cmp = compare(float_result, cand_result)
                key = f'{name}|{variant}|{split}'
                summary[key] = {
                    'accuracy': cand_result['accuracy'],
                    'balanced_accuracy': cand_result['balanced_accuracy'],
                    'log_loss': cand_result['log_loss'],
                    'brier': cand_result['brier'],
                    'p50_ms': cand_result['p50_ms'],
                    'p95_ms': cand_result['p95_ms'],
                    'temperature': cand_result['temperature'],
                    **cmp,
                }
    (SHRINK / 'compare-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    for k, v in summary.items():
        print(k, json.dumps(v))


if __name__ == '__main__':
    main()
