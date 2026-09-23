"""Score the stock Laya checkpoint, unmodified, on DecisionGate's held-out test sets."""
import json, sys, time
import numpy as np
import laya

SETS = {
    'v4test_480': ['data/v4/test-1.jsonl', 'data/v4/test-2.jsonl', 'data/v4/test-3.jsonl', 'data/v4/test-4.jsonl'],
    'fresh_80': ['data/evaluation-v2.jsonl'],
    'old_52': ['data/seed.jsonl', 'data/plain-questions.jsonl'],
    'choice_20': ['data/choices.jsonl'],
}


def rows(paths):
    for p in paths:
        for line in open(p):
            if line.strip():
                r = json.loads(line)
                if r['split'] == 'test':
                    yield r


def question(r):
    if r['label_type'] == 'choice':
        return {'type': 'choice', 'instructions': r['question'], 'criteria': list(dict.fromkeys(r['options']))}
    q = {'type': 'noul', 'instructions': r['question']}
    if r.get('criteria'):
        q['criteria'] = {'true': r['criteria']['yes'], 'false': r['criteria']['no']}
    return q


agent = laya.load('convaiinnovations/laya', device='cuda')
out = {}
for name, paths in SETS.items():
    data = list(rows(paths))
    correct, fams, ll = 0, {}, []
    for r in data:
        a = agent.system_one(r['content'], {'q': question(r)})['answers']['q']
        if r['label_type'] == 'choice':
            pred = r['options'].index(a['choice'])
            p = a['probabilities'][r['options'][r['label']]]
            ok = pred == r['label']
        else:
            p1 = a['noul']
            ok = (p1 >= .5) == bool(r['label'])
            p = p1 if r['label'] else 1 - p1
        ll.append(-np.log(max(p, 1e-7)))
        correct += ok
        f = fams.setdefault(r['task_family'], [0, 0]); f[0] += ok; f[1] += 1
    out[name] = {'count': len(data), 'accuracy': correct / len(data), 'log_loss': float(np.mean(ll)),
                 'by_family': {k: round(v[0] / v[1], 3) for k, v in sorted(fams.items())}}
    print(name, out[name]['count'], round(out[name]['accuracy'], 4), round(out[name]['log_loss'], 3), flush=True)
json.dump(out, open('laya-zeroshot.json', 'w'), indent=1)
