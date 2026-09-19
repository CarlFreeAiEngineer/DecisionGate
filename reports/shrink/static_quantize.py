"""Build static QDQ int8 candidates (candidate 3) using onnxruntime.quantization.quantize_static.

Usage:
  .venv/bin/python reports/shrink/static_quantize.py <output_dir> <calibration_method minmax|percentile> \
      [--exclude-classifier] [--data-scope calib|calib+train]

Calibration data: the 52-record calibration split (seed+plain-questions+expansion-v2), optionally
extended with a slice of train records. Does not modify training/pipeline.py or anything under
released/, code/, decisiongate/, specs/.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, encode_row, load_split, read_rows  # noqa: E402


PAD_TOKEN_ID = 1  # <pad> in the RoBERTa-style tokenizer.json


class RowsCalibrationReader:
    """Feeds one padded-to-common-length record per call.

    The Percentile/Entropy calibrators in onnxruntime.quantization stack the
    collected activation arrays across calibration steps, which requires a
    consistent shape; our records have different token lengths, so we pad
    every record (right-pad with <pad>/mask=0/type=0) to the longest record
    in the calibration set before feeding it in.
    """

    def __init__(self, tokenizer, rows, template_version=2):
        import numpy as np
        self.np = np
        self.tokenizer = tokenizer
        self.rows = rows
        self.template_version = template_version
        self.i = 0
        encoded = [encode_row(tokenizer, r, template_version) for r in rows]
        self.max_len = max(len(e.ids) for e in encoded)
        self.batches = []
        for e in encoded:
            pad = self.max_len - len(e.ids)
            self.batches.append({
                'input_ids': np.array([list(e.ids) + [PAD_TOKEN_ID] * pad], dtype=np.int64),
                'attention_mask': np.array([list(e.attention_mask) + [0] * pad], dtype=np.int64),
                'token_type_ids': np.array([list(e.type_ids) + [0] * pad], dtype=np.int64),
            })

    def get_next(self):
        if self.i >= len(self.batches):
            return None
        batch = self.batches[self.i]
        self.i += 1
        return batch

    def rewind(self):
        self.i = 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('output', help='models/shrink-... directory (must not exist)')
    ap.add_argument('method', choices=['minmax', 'percentile'])
    ap.add_argument('--exclude-classifier', action='store_true', help='exclude the two classifier-head Gemm nodes')
    ap.add_argument('--extra-train', type=int, default=0, help='also calibrate on N train records')
    ap.add_argument('--model-id', default=None)
    ap.add_argument('--bundle', default=str(ROOT / 'models/v2-nli-expanded'))
    args = ap.parse_args()

    from tokenizers import Tokenizer
    from onnxruntime.quantization import quantize_static, QuantType, QuantFormat, CalibrationMethod

    output = Path(args.output)
    if output.exists():
        raise SystemExit(f'{output} already exists')
    output.mkdir(parents=True)

    bundle = Path(args.bundle)
    manifest = json.loads((bundle / 'manifest.json').read_text())
    template_version = manifest.get('template_version', 2)

    calib_rows = load_split('calibration')
    if args.extra_train:
        train_rows = load_split('train')
        calib_rows = calib_rows + train_rows[:args.extra_train]
    print(f'Calibrating on {len(calib_rows)} records', file=sys.stderr)

    tokenizer = Tokenizer.from_file(str(bundle / 'tokenizer.json'))
    reader = RowsCalibrationReader(tokenizer, calib_rows, template_version)

    method = CalibrationMethod.MinMax if args.method == 'minmax' else CalibrationMethod.Percentile
    nodes_to_exclude = None
    if args.exclude_classifier:
        nodes_to_exclude = ['/inner/classifier/dense/Gemm', '/inner/classifier/out_proj/Gemm']

    pre_processed = output / 'model.preproc.onnx'
    # Shape inference / preprocessing recommended by onnxruntime before static quantization.
    from onnxruntime.quantization.preprocess import quant_pre_process
    quant_pre_process(str(bundle / 'model.onnx'), str(pre_processed), skip_symbolic_shape=True)

    quantize_static(
        str(pre_processed),
        str(output / 'model.onnx'),
        reader,
        quant_format=QuantFormat.QDQ,
        op_types_to_quantize=['MatMul', 'Gemm'],
        per_channel=True,
        weight_type=QuantType.QInt8,
        activation_type=QuantType.QInt8,
        calibrate_method=method,
        nodes_to_exclude=nodes_to_exclude,
        extra_options={'ActivationSymmetric': False, 'WeightSymmetric': True},
    )
    pre_processed.unlink(missing_ok=True)
    extra = pre_processed.with_suffix('.onnx.data')
    if extra.exists():
        extra.unlink()

    shutil.copy2(bundle / 'tokenizer.json', output / 'tokenizer.json')

    import hashlib

    def digest(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    out_manifest = dict(manifest)
    out_manifest['model_id'] = args.model_id or output.name
    out_manifest['temperature'] = 1.0
    out_manifest['calibration'] = 'unfitted after quantization'
    out_manifest.pop('calibration_data', None)
    out_manifest['quantization'] = {
        'runtime': 'ONNX Runtime',
        'method': 'static QDQ int8',
        'calibrate_method': args.method,
        'operators': ['MatMul', 'Gemm'],
        'per_channel': True,
        'exclude_classifier_head': args.exclude_classifier,
        'calibration_records': len(calib_rows),
    }
    out_manifest['float_model_sha256'] = digest(bundle / 'model.onnx')
    out_manifest['sha256'] = {n: digest(output / n) for n in ('model.onnx', 'tokenizer.json')}
    (output / 'manifest.json').write_text(json.dumps(out_manifest, indent=2) + '\n')
    print(f'Wrote {output}, model.onnx = {(output / "model.onnx").stat().st_size} bytes')


if __name__ == '__main__':
    main()
