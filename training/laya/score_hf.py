import json, sys, torch
import training.pipeline as p
from transformers import AutoModelForSequenceClassification, AutoTokenizer
TESTS = {'v4test_480': [f'data/v4/test-{i}.jsonl' for i in range(1, 5)], 'fresh_80': ['data/evaluation-v2.jsonl'],
         'old_52': ['data/seed.jsonl', 'data/plain-questions.jsonl'], 'choice_20': ['data/choices.jsonl']}
ck = sys.argv[1]
m = AutoModelForSequenceClassification.from_pretrained(ck, attn_implementation='eager').cuda().eval()
tok = AutoTokenizer.from_pretrained(ck)
out = {}
for name, paths in TESTS.items():
    rows = p.expand([r for r in p.read_data(paths) if r['split'] == 'test'])
    probs = p.predict(m, tok, rows, 'cuda')
    out[name] = p.choice_metrics(rows, probs) if name == 'choice_20' else p.metrics(rows, probs)
    out[name].pop('choice_predictions', None)
    print(ck, name, round(out[name].get('accuracy', out[name].get('choice_accuracy')), 4), flush=True)
json.dump(out, open(ck.rstrip('/') + '-tests.json', 'w'), indent=1)
