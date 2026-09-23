"""Fine-tune the whole Laya model (encoder + its own decision head) on DecisionGate data, then score the test sets.
Plain cross-entropy over option markers (the log score, Laya's main proper scoring rule). usage: laya_full_ft.py OUT LR"""
import glob, json, random, sys, time
from pathlib import Path
import numpy as np, torch
import laya
from laya.common import QTYPES, build_sequence, collate_items

OUT, LR, EPOCHS, BS = Path(sys.argv[1]), float(sys.argv[2]), 4, 16
OUT.mkdir(parents=True, exist_ok=True)
random.seed(42); torch.manual_seed(42)
files = ['data/seed.jsonl', 'data/plain-questions.jsonl', 'data/expansion-v2.jsonl', 'data/choices.jsonl'] + \
        [f for f in sorted(glob.glob('data/v4/*.jsonl')) if 'test-' not in f]
TESTS = {'v4test_480': [f'data/v4/test-{i}.jsonl' for i in range(1, 5)], 'fresh_80': ['data/evaluation-v2.jsonl'],
         'old_52': ['data/seed.jsonl', 'data/plain-questions.jsonl'], 'choice_20': ['data/choices.jsonl']}


def load(paths, split):
    return [r for p in paths for r in map(json.loads, filter(str.strip, open(p))) if r['split'] == split]


def q_of(r):
    if r['label_type'] == 'choice':
        return {'t': 'choice', 'ins': r['question'], 'crit': {o: None for o in r['options']}}
    c = r.get('criteria')
    return {'t': 'noul', 'ins': r['question'], 'crit': {'true': c['yes'], 'false': c['no']} if c else None}


def item(r):
    q = q_of(r)
    ids, markers = build_sequence(agent.tok, r['content'], q, 512, 192)
    label = r['label'] if r['label_type'] == 'choice' else int(r['label'])  # noul options are [false, true]
    return {'ids': ids, 'markers': markers, 'qtype': QTYPES[q['t']], 'label': label}


def logits(batch):
    with torch.autocast('cuda', dtype=torch.bfloat16):
        lg, _ = model(*(batch[k].cuda() for k in ('input_ids', 'attention_mask', 'marker_pos', 'marker_mask', 'qtype')))
    return lg.float()


@torch.no_grad()
def score(rows):
    model.eval()
    probs = []
    for s in range(0, len(rows), 32):
        b = collate_items([[item(r) for r in rows[s:s + 32]]], agent.tok.pad_token_id)
        probs += [p[:len(it)].cpu().numpy() for p, it in zip(logits(b).softmax(-1), [r.get('options', [0, 1]) for r in rows[s:s + 32]])]
    correct = [int(np.argmax(p) == r['label']) for p, r in zip(probs, rows)]
    ll = [-np.log(max(float(p[r['label']]), 1e-7)) for p, r in zip(probs, rows)]
    fam = {}
    for c, r in zip(correct, rows): fam.setdefault(r['task_family'], []).append(c)
    return {'count': len(rows), 'accuracy': float(np.mean(correct)), 'log_loss': float(np.mean(ll)),
            'by_family': {k: round(float(np.mean(v)), 3) for k, v in sorted(fam.items())}}


agent = laya.load('convaiinnovations/laya', device='cuda')
model = agent.model.float().cuda()
train, val = load(files, 'train'), load(files, 'validation')
opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=.01)
best, history, t0 = 9e9, [], time.monotonic()
history.append({'epoch': 0, 'validation': score(val)}); print(json.dumps(history[-1])[:300], flush=True)
for epoch in range(1, EPOCHS + 1):
    model.train(); random.shuffle(train); tot = 0
    for s in range(0, len(train), BS):
        rows = train[s:s + BS]
        b = collate_items([[item(r) for r in rows]], agent.tok.pad_token_id)
        loss = torch.nn.functional.cross_entropy(logits(b), b['label'].cuda())
        opt.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.); opt.step(); tot += loss.item() * len(rows)
    v = score(val)
    history.append({'epoch': epoch, 'train_loss': tot / len(train), 'validation': v, 'elapsed_seconds': time.monotonic() - t0})
    print(json.dumps(history[-1])[:300], flush=True)
    if v['log_loss'] < best:
        best = v['log_loss']; torch.save(model.state_dict(), OUT / 'best.pt')
json.dump(history, open(OUT / 'history.json', 'w'), indent=1)
model.load_state_dict(torch.load(OUT / 'best.pt'))
tests = {name: score(load(paths, 'test')) for name, paths in TESTS.items()}
json.dump(tests, open(OUT / 'tests.json', 'w'), indent=1)
for k, v in tests.items(): print(k, v['count'], round(v['accuracy'], 4), round(v['log_loss'], 3), flush=True)
