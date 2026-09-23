"""Experiment: block-wise weight quantization (ONNX Runtime MatMulNBits) of an exported bundle.
usage: uv run --locked python training/blockwise.py SOURCE_BUNDLE OUTPUT_BUNDLE BITS BLOCK [--embeddings]"""
import json, shutil, sys
from pathlib import Path
import onnx
from onnxruntime.quantization import matmul_nbits_quantizer as q
from onnxruntime.quantization.quant_utils import QuantFormat

source, output, bits, block = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
ops = ('MatMul', 'Gather') if '--embeddings' in sys.argv else ('MatMul',)
output.mkdir(parents=True)
config = q.DefaultWeightOnlyQuantConfig(block_size=block, is_symmetric=True, accuracy_level=4, quant_format=QuantFormat.QOperator,
                                        op_types_to_quantize=ops, quant_axes=(('MatMul', 0), ('Gather', 1)), bits=bits)
quantizer = q.MatMulNBitsQuantizer(onnx.load(str(source / 'model.onnx')), algo_config=config)
quantizer.process()
quantizer.model.save_model_to_file(str(output / 'model.onnx'), use_external_data_format=False)
shutil.copy2(source / 'tokenizer.json', output / 'tokenizer.json')
m = json.loads((source / 'manifest.json').read_text())
from training.pipeline import digest
m.update({'model_id': output.name, 'temperature': 1.0, 'calibration': 'unfitted after quantization',
          'quantization': {'runtime': 'ONNX Runtime MatMulNBits', 'bits': bits, 'block_size': block, 'accuracy_level': 4, 'operators': list(ops)}})
m.pop('calibration_data', None)
m['sha256'] = {n: digest(output / n) for n in ('model.onnx', 'tokenizer.json')}
(output / 'manifest.json').write_text(json.dumps(m, indent=2) + '\n')
print(output, (output / 'model.onnx').stat().st_size)
