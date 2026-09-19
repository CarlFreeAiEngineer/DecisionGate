"""Build candidate 5 (optional): dynamic int8 restricted to the FFN MatMuls only.

Each encoder layer's attention Q/K/V/output-dense MatMuls are 768x768 (~2.4MB fp32
each); the two FFN MatMuls (intermediate + output dense) are 768x3072 (~9.4MB fp32
each) and dominate encoder weight size. This candidate quantizes only the FFN
MatMuls to int8 (dynamic, per-channel) and leaves the attention Q/K/V/O MatMuls,
embeddings, pooler and classifier head in float32, to see whether skipping the
(likely more precision-sensitive) attention projections preserves agreement
better than candidates 1/2 while still shrinking the biggest weights.

Run with: .venv/bin/python reports/shrink/partial_int8.py
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    import onnx
    from onnxruntime.quantization import quantize_dynamic, QuantType

    bundle = ROOT / 'models/v2-nli-expanded'
    output = ROOT / 'models/shrink-5-int8-ffn-only'
    if output.exists():
        raise SystemExit(f'{output} already exists')
    output.mkdir(parents=True)

    model = onnx.load(str(bundle / 'model.onnx'))
    exclude = [n.name for n in model.graph.node
               if n.op_type == 'MatMul' and ('attention/self/' in n.name or 'attention/output/dense' in n.name)]
    exclude += [n.name for n in model.graph.node if n.op_type == 'Gemm']  # pooler/classifier stay fp32 too
    print(f'Excluding {len(exclude)} nodes from quantization (attention Q/K/V/O + Gemm head)')

    quantize_dynamic(str(bundle / 'model.onnx'), str(output / 'model.onnx'),
                      op_types_to_quantize=['MatMul'], weight_type=QuantType.QInt8,
                      per_channel=True, nodes_to_exclude=exclude,
                      extra_options={'MatMulConstBOnly': True})

    shutil.copy2(bundle / 'tokenizer.json', output / 'tokenizer.json')

    manifest = json.loads((bundle / 'manifest.json').read_text())
    manifest['model_id'] = 'decisionmodel-shrink-5-int8-ffn-only'
    manifest['temperature'] = 1.0
    manifest['calibration'] = 'unfitted after quantization'
    manifest.pop('calibration_data', None)
    manifest['quantization'] = {
        'runtime': 'ONNX Runtime', 'weight_type': 'QInt8', 'operators': ['MatMul (FFN only)'],
        'per_channel': True, 'excluded_nodes': len(exclude),
        'note': 'attention Q/K/V/output-dense MatMuls and the pooler/classifier Gemm stay float32',
    }
    manifest['float_model_sha256'] = digest(bundle / 'model.onnx')
    manifest['sha256'] = {n: digest(output / n) for n in ('model.onnx', 'tokenizer.json')}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Wrote {output}, model.onnx = {(output / "model.onnx").stat().st_size} bytes')


if __name__ == '__main__':
    main()
