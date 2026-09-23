# /// script
# requires-python = ">=3.11"
# dependencies = ["onnxruntime==1.22.1", "numpy"]
# ///
"""usage: bench2.py MODEL THREADS TOKENS CALLS -> p50 ms and peak memory"""
import resource, sys, time, numpy as np, onnxruntime as ort
path, threads, tokens, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
o = ort.SessionOptions(); o.intra_op_num_threads = threads
s = ort.InferenceSession(path, o, providers=['CPUExecutionProvider'])
rng = np.random.default_rng(0)
feed = {'input_ids': rng.integers(1000, 20000, (1, tokens)).astype(np.int64), 'attention_mask': np.ones((1, tokens), np.int64), 'token_type_ids': np.zeros((1, tokens), np.int64)}
for _ in range(3): s.run(None, feed)
t = []
for _ in range(n):
    a = time.perf_counter(); s.run(None, feed); t.append((time.perf_counter() - a) * 1000)
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / (1 if sys.platform == 'darwin' else 1 / 1024) / 1e9
print(f'{path.split("/")[-2]:24} {tokens:4} tokens  p50 {np.median(t):6.0f} ms  peak memory {peak:5.2f} GB')
