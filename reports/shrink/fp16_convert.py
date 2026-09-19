"""Build the float16-weights candidate (candidate 4).

Converts every float32 initializer to float16 storage and inserts a Cast-to-float32
node right after each one, using the ORIGINAL initializer name as the Cast node's
output. Every consuming node keeps referencing that same name unchanged, so the
whole compute graph still runs in float32 on ONNX Runtime CPU; only the on-disk
weight storage shrinks. This is the primary approach from the task spec (as
opposed to onnxconverter_common's convert_float_to_float16, which converts the
whole compute graph to fp16 arithmetic and produced dtype-mismatch load errors
on this graph's attention-mask Cast/Sub subgraph -- see reports/shrink/README.md).

Run with: .venv/bin/python reports/shrink/fp16_convert.py
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    import numpy as np
    import onnx
    from onnx import TensorProto, numpy_helper

    bundle = ROOT / 'models/v2-nli-expanded'
    output = ROOT / 'models/shrink-4-fp16'
    if output.exists():
        raise SystemExit(f'{output} already exists')
    output.mkdir(parents=True)

    model = onnx.load(str(bundle / 'model.onnx'))
    graph = model.graph

    new_initializers = []
    cast_nodes = []
    kept = []
    converted_count = 0
    for init in graph.initializer:
        if init.data_type != TensorProto.FLOAT:
            kept.append(init)
            continue
        arr = numpy_helper.to_array(init).astype(np.float16)
        new_name = init.name + '.fp16'
        new_initializers.append(numpy_helper.from_array(arr, new_name))
        cast_nodes.append(onnx.helper.make_node('Cast', [new_name], [init.name], to=TensorProto.FLOAT,
                                                 name=f'CastToFp32__{init.name}'))
        converted_count += 1

    del graph.initializer[:]
    graph.initializer.extend(kept)
    graph.initializer.extend(new_initializers)

    new_nodes = cast_nodes + list(graph.node)
    del graph.node[:]
    graph.node.extend(new_nodes)

    onnx.checker.check_model(model)
    onnx.save(model, str(output / 'model.onnx'))
    print(f'Converted {converted_count} float32 initializers to float16 (+Cast back to float32)')

    shutil.copy2(bundle / 'tokenizer.json', output / 'tokenizer.json')

    manifest = json.loads((bundle / 'manifest.json').read_text())
    manifest['model_id'] = 'decisionmodel-shrink-4-fp16'
    manifest['temperature'] = 1.0
    manifest['calibration'] = 'unfitted after fp16 conversion'
    manifest.pop('calibration_data', None)
    manifest['quantization'] = {
        'runtime': 'ONNX Runtime',
        'method': 'float16 weight storage: initializers stored as fp16, Cast-to-float32 node inserted '
                  'after each one so compute graph runs entirely in float32',
        'converted_initializers': converted_count,
    }
    manifest['float_model_sha256'] = digest(bundle / 'model.onnx')
    manifest['sha256'] = {n: digest(output / n) for n in ('model.onnx', 'tokenizer.json')}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Wrote {output}, model.onnx = {(output / "model.onnx").stat().st_size} bytes')


if __name__ == '__main__':
    main()
