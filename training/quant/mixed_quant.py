"""Experiment: 4-bit block-wise weights for the layers that cannot take 8-bit dynamic quantization and for the
embedding table, 8-bit dynamic quantization for every other weight multiplication.
usage: uv run --locked python training/mixed_quant.py SOURCE_BUNDLE OUTPUT_BUNDLE FIRST_LAYER LAST_LAYER"""
import json, shutil, sys, tempfile
from pathlib import Path
import onnx
from onnxruntime.quantization import QuantType, quantize_dynamic
from onnxruntime.quantization import matmul_nbits_quantizer as q
from onnxruntime.quantization.quant_utils import QuantFormat
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from training.pipeline import digest

source, output, first, last = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])  # optional --reduce-range
output.mkdir(parents=True)
model = onnx.load(str(source / 'model.onnx'))
sensitive = [n.name for n in model.graph.node if n.op_type == 'MatMul'
             and any(f'layer.{i}/output/dense/' in n.name for i in range(first, last + 1))]
embeddings = [n.name for n in model.graph.node if n.op_type == 'Gather' and any('word_embeddings' in x for x in n.input)]
config = q.DefaultWeightOnlyQuantConfig(block_size=32, is_symmetric=True, accuracy_level=4, quant_format=QuantFormat.QOperator,
                                        op_types_to_quantize=('MatMul', 'Gather'), quant_axes=(('MatMul', 0), ('Gather', 1)), bits=4)
# ONNX Runtime 1.22 ignores nodes_to_include here, so exclude everything else instead.
others = [n.name for n in model.graph.node if n.op_type in ('MatMul', 'Gather') and n.name not in sensitive + embeddings]
quantizer = q.MatMulNBitsQuantizer(model, nodes_to_exclude=others, algo_config=config)
quantizer.process()
with tempfile.TemporaryDirectory() as tmp:
    middle = Path(tmp) / 'middle.onnx'
    quantizer.model.save_model_to_file(str(middle), use_external_data_format=False)
    graph = onnx.load(str(middle), load_external_data=False).graph
    rest = [n.name for n in graph.node if n.op_type in ('MatMul', 'Gemm')]
    quantize_dynamic(str(middle), str(output / 'model.onnx'), nodes_to_quantize=rest, weight_type=QuantType.QInt8, reduce_range='--reduce-range' in sys.argv,
                     per_channel=True, extra_options={'MatMulConstBOnly': True, 'DefaultTensorType': onnx.TensorProto.FLOAT})
shutil.copy2(source / 'tokenizer.json', output / 'tokenizer.json')
m = json.loads((source / 'manifest.json').read_text())
m.update({'model_id': output.name, 'temperature': 1.0, 'calibration': 'unfitted after quantization',
          'quantization': {'dynamic_int8': 'every other MatMul, per channel', 'block_int4': {'block_size': 32, 'accuracy_level': 4,
                           'nodes': sensitive + embeddings}}, 'float_model_sha256': digest(source / 'model.onnx')})
m.pop('calibration_data', None)
m['sha256'] = {n: digest(output / n) for n in ('model.onnx', 'tokenizer.json')}
(output / 'manifest.json').write_text(json.dumps(m, indent=2) + '\n')
print(output, (output / 'model.onnx').stat().st_size)
