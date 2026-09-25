#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["onnx==1.19.0"]
# ///
"""Split a model into a small graph file plus a few weight files, for browsers.

Loading one ONNX file makes the browser runtime copy every weight at least twice,
which pushed a phone's Safari tab past its memory limit. With the weights in
separate files the runtime uses them in place, and several smaller files avoid
one huge memory block and can download side by side.

  uv run web/split_model.py MODEL.onnx OUT_DIR [PIECES]

Writes OUT_DIR/model.onnx and OUT_DIR/weights-1.bin ... weights-PIECES.bin, and
prints the weight file names as JSON. Tensors are never split across files.
"""
import json
import sys
from pathlib import Path

import onnx
from onnx.external_data_helper import set_external_data

source, out = Path(sys.argv[1]), Path(sys.argv[2])
pieces = int(sys.argv[3]) if len(sys.argv) > 3 else 4
model = onnx.load(source)
tensors = [t for t in model.graph.initializer if len(t.raw_data) >= 1024]
target = sum(len(t.raw_data) for t in tensors) / pieces
names, filled, index = [], 0, 1
for tensor in tensors:
    if filled >= target * index and index < pieces:
        index += 1
    name = f'weights-{index}.bin'
    if name not in names:
        names.append(name)
    set_external_data(tensor, location=name)
    filled += len(tensor.raw_data)
out.mkdir(parents=True, exist_ok=True)
for name in names:
    (out / name).unlink(missing_ok=True)  # the writer appends, so start each file empty
onnx.save_model(model, out / 'model.onnx')
print(json.dumps(names))
