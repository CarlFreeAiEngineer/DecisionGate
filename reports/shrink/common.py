"""Shared helpers for the ONNX shrink experiments (reports/shrink/).

Read-only with respect to released/, code/, decisiongator/, specs/, README.md and
training/pipeline.py. This module duplicates the tiny bits of pipeline.py logic
we need (prompt building, data loading) instead of importing/modifying it, so
outputs live entirely under reports/shrink/ and models/shrink-*/.
"""
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_TOKENS = 256


def prompt(record):
    question = record['question']
    criteria = record.get('criteria')
    return question if criteria is None else question + '\nYes: ' + criteria['yes'] + '\nNo: ' + criteria['no']


def read_rows(paths):
    rows = []
    for path in paths:
        for line in Path(path).read_text().splitlines():
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def default_data_paths(extra=('data/expansion-v2.jsonl',)):
    return [ROOT / 'data/seed.jsonl', ROOT / 'data/plain-questions.jsonl', *[ROOT / p for p in extra]]


def load_split(split, data_paths=None, extra=('data/expansion-v2.jsonl',)):
    paths = data_paths if data_paths is not None else default_data_paths(extra)
    rows = read_rows(paths)
    return [r for r in rows if r['split'] == split]


def encode_row(tokenizer, row, template_version=2):
    if template_version == 2:
        return tokenizer.encode(row['content'], prompt(row))
    return tokenizer.encode(prompt(row), row['content'])


def run_bundle(bundle_dir, rows, threads=4, temperature=None):
    """Run an ONNX bundle over rows, return (probabilities, timings_seconds)."""
    import numpy as np
    import onnxruntime as ort
    from tokenizers import Tokenizer

    bundle_dir = Path(bundle_dir)
    manifest = json.loads((bundle_dir / 'manifest.json').read_text())
    temp = temperature if temperature is not None else manifest.get('temperature', 1.0)
    tokenizer = Tokenizer.from_file(str(bundle_dir / 'tokenizer.json'))
    options = ort.SessionOptions()
    options.intra_op_num_threads = threads
    session = ort.InferenceSession(str(bundle_dir / 'model.onnx'), options, providers=['CPUExecutionProvider'])
    probabilities, timings = [], []
    for row in rows:
        encoded = encode_row(tokenizer, row, manifest.get('template_version', 2))
        if len(encoded.ids) > MAX_TOKENS:
            raise ValueError('Overlength evaluation input')
        feed = {name: np.array([values], dtype=np.int64) for name, values in
                [('input_ids', encoded.ids), ('attention_mask', encoded.attention_mask), ('token_type_ids', encoded.type_ids)]}
        start = time.perf_counter()
        logits = session.run(None, feed)[0][0].astype(float) / temp
        timings.append(time.perf_counter() - start)
        p = np.exp(logits - logits.max())
        p /= p.sum()
        probabilities.append(float(p[1]))
    return probabilities, timings
