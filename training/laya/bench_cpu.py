# /// script
# requires-python = ">=3.11"
# dependencies = ["onnxruntime==1.22.1", "numpy"]
# ///
"""Warm CPU latency of an exported bundle at a fixed 256-token input, 4 threads."""
import sys, time, numpy as np, onnxruntime as ort
path, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 300
o = ort.SessionOptions(); o.intra_op_num_threads = 4
t = time.monotonic(); s = ort.InferenceSession(path, o, providers=['CPUExecutionProvider']); load = time.monotonic() - t
rng = np.random.default_rng(0)
feed = {'input_ids': rng.integers(1000, 20000, (1, 256)).astype(np.int64),
        'attention_mask': np.ones((1, 256), np.int64), 'token_type_ids': np.zeros((1, 256), np.int64)}
feed = {i.name: feed[i.name] for i in s.get_inputs()}
for _ in range(10): s.run(None, feed)
times = []
for _ in range(n):
    t = time.perf_counter(); s.run(None, feed); times.append((time.perf_counter() - t) * 1000)
print(f'{path}: load {load:.1f}s p50 {np.percentile(times,50):.0f} ms p95 {np.percentile(times,95):.0f} ms over {n}')
