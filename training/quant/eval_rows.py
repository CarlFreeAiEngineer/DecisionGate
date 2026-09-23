# /// script
# requires-python = ">=3.11"
# dependencies = ["onnxruntime==1.22.1", "numpy", "tokenizers==0.21.4"]
# ///
"""Accuracy of a bundle on yes/no test rows, standalone. usage: eval_rows.py BUNDLE OUT.json FILE..."""
import json, sys, numpy as np, onnxruntime as ort
from tokenizers import Tokenizer
b, out, files = sys.argv[1], sys.argv[2], sys.argv[3:]
tok = Tokenizer.from_file(b + '/tokenizer.json')
o = ort.SessionOptions(); o.intra_op_num_threads = 4
s = ort.InferenceSession(b + '/model.onnx', o, providers=['CPUExecutionProvider'])
res = {}
for f in files:
    rows = [r for r in map(json.loads, filter(str.strip, open(f))) if r['split'] == 'test' and r['label_type'] == 'binary']
    for r in rows:
        c = r.get('criteria'); q = r['question'] + ('' if not c else '\nYes: ' + c['yes'] + '\nNo: ' + c['no'])
        e = tok.encode(r['content'], q)
        z = s.run(None, {k: np.array([v], dtype=np.int64) for k, v in [('input_ids', e.ids), ('attention_mask', e.attention_mask), ('token_type_ids', e.type_ids)]})[0][0]
        res[r['id']] = [float(z[1] - z[0]), r['label']]
json.dump(res, open(out, 'w'))
