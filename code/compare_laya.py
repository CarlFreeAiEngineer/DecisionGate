#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["laya==0.3.20"]
# ///
"""Score Laya and DecisionGate on the same held-out tests, on this machine's CPU.

  uv run code/compare_laya.py [OUTPUT_DIR]

Runs each Laya checkpoint and the DecisionGate release for this platform over the
480-case new test, the 80-case fresh test and the 20-case choice test, one call at a
time, and writes accuracy plus per-call times to OUTPUT_DIR (default reports/laya).
Laya downloads its weights from Hugging Face on first use.
"""
import json
import statistics
import sys
import time
from pathlib import Path

import laya

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import decisiongate  # noqa: E402

TESTS = {
    'new-480': [ROOT / 'data' / 'v4' / f'test-{n}.jsonl' for n in range(1, 5)],
    'fresh-80': [ROOT / 'data' / 'evaluation-v2.jsonl'],
    'choice-20': [ROOT / 'data' / 'choices.jsonl'],
}
LAYA = {'laya-english': None, 'laya-multilingual': 'multilingual', 'laya-typed-decisions': 'typed-decisions'}


def records(name):
    rows = [json.loads(line) for path in TESTS[name] for line in path.read_text().splitlines() if line.strip()]
    return [r for r in rows if r.get('split') == 'test']


def laya_question(record):
    if record['label_type'] == 'choice':
        # Laya wants a description per option; the option text is the only one we have.
        return {'type': 'choice', 'instructions': record['question'], 'criteria': {o: o for o in record['options']}}
    question = {'type': 'noul', 'instructions': record['question']}
    if record.get('criteria'):
        question['criteria'] = {'true': record['criteria']['yes'], 'false': record['criteria']['no']}
    return question


def run_laya(agent, record):
    answer = agent.predict(record['content'], {'q': laya_question(record)})['answers']['q']
    if record['label_type'] == 'choice':
        return record['options'].index(answer['choice'])
    return int(answer['noul'] >= 0.5)


def run_decisiongate(session, record):
    if record['label_type'] == 'choice':
        return session.evaluate_choice(record['content'], record['question'], record['options'])[0][0]
    return int(session.evaluate(record['content'], record['question'], record.get('criteria')) >= 0.5)


def score(name, predict):
    result = {}
    for test in TESTS:
        rows = records(test)
        predict(rows[0])  # warm up
        right, times, families = 0, [], {}
        for record in rows:
            start = time.perf_counter()
            answer = predict(record)
            times.append((time.perf_counter() - start) * 1000)
            ok = answer == record['label']
            right += ok
            family = families.setdefault(record.get('task_family', ''), [0, 0])
            family[0] += ok
            family[1] += 1
        result[test] = {'count': len(rows), 'correct': right, 'accuracy': right / len(rows),
                        'p50_ms': statistics.median(times), 'mean_ms': statistics.fmean(times),
                        'by_family': {f: {'correct': c, 'count': n} for f, (c, n) in sorted(families.items())}}
        print(f'{name} {test}: {right}/{len(rows)} = {right / len(rows):.1%}, p50 {statistics.median(times):.0f} ms', flush=True)
    return result


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'reports' / 'laya'
    out.mkdir(parents=True, exist_ok=True)
    session = decisiongate.Session.load(decisiongate._bundled_directory())
    results = {'decisiongate': score('decisiongate', lambda r: run_decisiongate(session, r))}
    session.close()
    for name, subfolder in LAYA.items():
        agent = laya.load('convaiinnovations/laya', subfolder=subfolder, device='cpu')
        results[name] = score(name, lambda r: run_laya(agent, r))
        del agent
    (out / 'results.json').write_text(json.dumps({'laya_version': laya.__version__, 'results': results}, indent=2) + '\n')


if __name__ == '__main__':
    main()
