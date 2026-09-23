"""Find which weight multiplications lose accuracy when stored as 8-bit.
usage: uv run --locked python training/int8_scan.py BUNDLE WORKDIR GROUP [GROUP ...]
A GROUP is a comma-separated list of name fragments (e.g. 'output/dense,intermediate/dense'); 'all' means every
constant-weight MatMul/Gemm. Each group is quantized alone and compared with the float model on validation rows."""
import json, random, sys, time
from pathlib import Path
import numpy as np, onnx, onnxruntime as ort
from onnxruntime.quantization import quantize_dynamic, QuantType
from tokenizers import Tokenizer
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from training.pipeline import read_data, prompt

bundle, work, groups = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
work.mkdir(parents=True, exist_ok=True)
files = ['data/seed.jsonl', 'data/plain-questions.jsonl', 'data/expansion-v2.jsonl'] + sorted(str(p) for p in Path('data/v4').glob('*.jsonl') if 'test-' not in p.name)
rows = [r for r in read_data(files) if r['split'] == 'validation' and r['label_type'] == 'binary']
random.Random(0).shuffle(rows); rows = rows[:160]
tok = Tokenizer.from_file(str(bundle / 'tokenizer.json'))
model = onnx.load(str(bundle / 'model.onnx'), load_external_data=False)
weights = {i.name for i in model.graph.initializer}
candidates = [n.name for n in model.graph.node if n.op_type in ('MatMul', 'Gemm') and any(x in weights for x in n.input)]

def logits(path):
    o = ort.SessionOptions(); o.intra_op_num_threads = 8
    s = ort.InferenceSession(str(path), o, providers=['CPUExecutionProvider'])
    out = []
    for r in rows:
        e = tok.encode(r['content'], prompt(r))
        feed = {k: np.array([v], dtype=np.int64) for k, v in [('input_ids', e.ids), ('attention_mask', e.attention_mask), ('token_type_ids', e.type_ids)]}
        z = s.run(None, feed)[0][0]
        out.append(float(z[1] - z[0]))
    return np.array(out)

labels = np.array([r['label'] for r in rows])
base = logits(bundle / 'model.onnx')
print(json.dumps({'group': 'float', 'accuracy': float(((base >= 0) == labels).mean())}), flush=True)
for group in groups:
    nodes = candidates if group == 'all' else [n for n in candidates if any(f in n for f in group.split(','))]
    out = work / 'q.onnx'
    t = time.time()
    quantize_dynamic(str(bundle / 'model.onnx'), str(out), nodes_to_quantize=nodes, weight_type=QuantType.QInt8, per_channel=True, extra_options={'MatMulConstBOnly': True})
    z = logits(out)
    print(json.dumps({'group': group, 'nodes': len(nodes), 'accuracy': float(((z >= 0) == labels).mean()),
                      'flips': int(((z >= 0) != (base >= 0)).sum()), 'mean_abs_logit_change': float(np.abs(z - base).mean()),
                      'seconds': round(time.time() - t)}), flush=True)
