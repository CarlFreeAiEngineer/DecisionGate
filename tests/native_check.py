#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Exercise the native ABI and Python binding against an exported model bundle."""
import argparse
import ctypes as c
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class Criteria(c.Structure):
    _fields_ = [("yes", c.c_char_p), ("yes_bytes", c.c_size_t),
                ("no", c.c_char_p), ("no_bytes", c.c_size_t)]


def check(bundle: Path) -> dict:
    name = {"Darwin": "libdecisiongator.dylib", "Windows": "decisiongator.dll", "Linux": "libdecisiongator.so"}[platform.system()]
    lib = c.CDLL(str(bundle / name))
    handle = c.c_void_p
    size = c.c_size_t
    lib.dg_load.argtypes = [c.c_char_p, size, c.POINTER(handle)]
    lib.dg_load.restype = c.c_int32
    lib.dg_evaluate.argtypes = [handle, c.c_char_p, size, c.c_char_p, size, c.POINTER(Criteria), c.POINTER(c.c_double)]
    lib.dg_evaluate.restype = c.c_int32
    lib.dg_is_yes_p.argtypes = [c.c_char_p, size, c.c_char_p, size, c.POINTER(Criteria), c.POINTER(c.c_double)]
    lib.dg_is_yes_p.restype = c.c_int32
    lib.dg_is_yes.argtypes = [c.c_char_p, size, c.c_char_p, size, c.POINTER(Criteria), c.POINTER(c.c_uint8)]
    lib.dg_is_yes.restype = c.c_int32
    lib.dg_is_yes_at_threshold.argtypes = [c.c_char_p, size, c.c_char_p, size, c.POINTER(Criteria), c.c_double, c.POINTER(c.c_uint8)]
    lib.dg_is_yes_at_threshold.restype = c.c_int32
    options_t = c.POINTER(c.c_char_p)
    lib.dg_evaluate_choice.argtypes = [handle, c.c_char_p, size, c.c_char_p, size, options_t, c.POINTER(size), size, c.POINTER(Criteria), c.POINTER(c.c_int32), c.POINTER(c.c_double)]
    lib.dg_evaluate_choice.restype = c.c_int32
    lib.dg_choose_p.argtypes = [c.c_char_p, size, c.c_char_p, size, options_t, c.POINTER(size), size, c.POINTER(Criteria), c.POINTER(c.c_int32), c.POINTER(c.c_double)]
    lib.dg_choose_p.restype = c.c_int32
    lib.dg_choose.argtypes = [c.c_char_p, size, c.c_char_p, size, options_t, c.POINTER(size), size, c.POINTER(Criteria), c.c_double, c.POINTER(c.c_int32)]
    lib.dg_choose.restype = c.c_int32
    lib.dg_metadata.argtypes = [handle, c.c_void_p, size, c.POINTER(size)]
    lib.dg_metadata.restype = c.c_int32
    lib.dg_last_error.argtypes = [c.c_void_p, size, c.POINTER(size)]
    lib.dg_last_error.restype = c.c_int32
    lib.dg_release.argtypes = [handle]
    lib.dg_release.restype = None
    checks = 0

    def expect(condition, message):
        nonlocal checks
        if not condition:
            raise AssertionError(message)
        checks += 1

    def error():
        needed = size()
        expect(lib.dg_last_error(None, 0, c.byref(needed)) == 0, "error size query")
        out = c.create_string_buffer(needed.value)
        expect(lib.dg_last_error(out, len(out), c.byref(needed)) == 0, "error copy")
        return out.value.decode()

    def load(path):
        model = handle(123)
        encoded = str(path).encode()
        status = lib.dg_load(encoded, len(encoded), c.byref(model))
        return status, model

    def evaluate(model, content=b"Please cancel my subscription.", question=b"Is cancellation requested?", criteria=None, expected=0):
        out = c.c_double(42)
        status = lib.dg_evaluate(model, content, len(content), question, len(question), criteria, c.byref(out))
        expect(status == expected, f"evaluate expected {expected}, got {status}: {error() if status else ''}")
        if status:
            expect(out.value == 42, "failed evaluation changed output")
            expect(bool(error()), "failed evaluation has error text")
        else:
            expect(math.isfinite(out.value) and 0 <= out.value <= 1, "invalid probability")
        return out.value

    expect(lib.dg_load(None, 0, None) == 1, "null load output")
    status, missing = load(bundle / "does-not-exist")
    expect(status == 2 and not missing.value, "missing bundle must reset handle")
    invalid = handle(123)
    expect(lib.dg_load(b"\xff", 1, c.byref(invalid)) == 1 and not invalid.value, "invalid UTF-8 path")
    expect(lib.dg_load(b"a\0b", 3, c.byref(invalid)) == 1, "NUL path")
    evaluate(None, expected=1)
    expect(lib.dg_is_yes_p(b"s", 1, b"Q?", 2, None, None) == 1, "lazy null probability output")
    lazy_invalid = c.c_double(42)
    expect(lib.dg_is_yes_p(b"\xff", 1, b"Q?", 2, None, c.byref(lazy_invalid)) == 1 and lazy_invalid.value == 42, "lazy invalid UTF-8")
    decision = c.c_uint8(42)
    for threshold in (-0.1, 1.1, float("inf"), float("-inf"), float("nan")):
        status = lib.dg_is_yes_at_threshold(b"s", 1, b"Q?", 2, None, threshold, c.byref(decision))
        expect(status == 1 and decision.value == 42, "invalid threshold must preserve decision output")
    expect(lib.dg_is_yes(b"s", 1, b"Q?", 2, None, None) == 1, "null boolean output")
    expect(lib.dg_is_yes(b"\xff", 1, b"Q?", 2, None, c.byref(decision)) == 1 and decision.value == 42, "boolean UTF-8 error preserves output")
    expect("UTF-8" in error(), "boolean call preserves inner error text")
    lib.dg_release(None)
    with tempfile.TemporaryDirectory(prefix="decisiongator-invalid-") as temporary:
        directory = Path(temporary)
        (directory / "manifest.json").write_text('{"format_version": 999}', encoding="utf-8")
        status, invalid = load(directory)
        expect(status == 3 and not invalid.value, "invalid manifest")
        # Tiny fake model with a deliberately wrong declared hash: rejection must
        # happen before tokenizer or runtime initialization is attempted.
        manifest = json.loads((bundle / "manifest.json").read_text(encoding='utf-8'))
        valid_temperature = manifest.get("temperature", 1.0)
        manifest["temperature"] = 0
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        status, invalid = load(directory)
        expect(status == 3 and not invalid.value, "invalid calibration temperature")
        manifest["temperature"] = valid_temperature
        manifest["sha256"]["model.onnx"] = "0" * 64
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        (directory / "model.onnx").write_bytes(b"corrupt model")
        status, invalid = load(directory)
        expect(status == 3 and not invalid.value, "corrupt model hash")
        expect("hash mismatch" in error(), "hash error explains rejection")

    status, model = load(bundle)
    expect(status == 0 and model.value, f"valid load failed: {error() if status else ''}")
    try:
        needed = size()
        expect(lib.dg_metadata(model, None, 0, c.byref(needed)) == 0 and needed.value > 1, "metadata size")
        small = c.create_string_buffer(b"sentinel")
        expect(lib.dg_metadata(model, small, 1, c.byref(needed)) == 4 and small.value == b"sentinel", "metadata undersized buffer")
        metadata = c.create_string_buffer(needed.value)
        expect(lib.dg_metadata(model, metadata, len(metadata), c.byref(needed)) == 0, "metadata copy")
        expect(json.loads(metadata.value)["model_id"] == json.loads((bundle / "manifest.json").read_text(encoding='utf-8'))["model_id"], "metadata identifier")
        expect(lib.dg_metadata(None, None, 0, c.byref(needed)) == 1, "null metadata model")
        expect(lib.dg_metadata(model, None, 0, None) == 1, "null metadata required")
        evaluate(model, content=b"\xff", expected=1)
        evaluate(model, question=b"\xff", expected=1)
        evaluate(model, content=b"", expected=1)
        evaluate(model, question=b" \n\t", expected=1)
        evaluate(model, content=b"word " * 600, expected=7)
        evaluate(model, content=b"x" * 1_048_577, expected=7)
        out = c.c_double(42)
        expect(lib.dg_evaluate(model, None, 5, b"Q?", 2, None, c.byref(out)) == 1 and out.value == 42, "null nonempty state")
        expect(lib.dg_evaluate(model, b"s", 1, b"Q?", 2, None, None) == 1, "null probability output")
        empty = Criteria(b"", 0, b"No request", 10)
        evaluate(model, criteria=c.byref(empty), expected=1)
        invalid_criteria = Criteria(b"\xff", 1, b"No", 2)
        evaluate(model, criteria=c.byref(invalid_criteria), expected=1)
        content = "Please cancel Renée’s café subscription. ☕".encode()
        question = b"Is cancellation requested?"
        yes, no = b"An explicit request to cancel.", b"No cancellation request."
        criteria = Criteria(yes, len(yes), no, len(no))
        probability = evaluate(model, content, question, c.byref(criteria))
        with ThreadPoolExecutor(max_workers=3) as workers:
            values = list(workers.map(lambda _: evaluate(model), range(6)))
        expect(max(values) - min(values) < 1e-7, "concurrent calls on shared handle differ")

        # Multiple choice: ranked outputs, untouched on error, sum to one.
        def options_of(items):
            pointers = (c.c_char_p * len(items))(*items)
            lengths = (size * len(items))(*[len(i) for i in items])
            return pointers, lengths
        teams = [b"billing", b"technical support", b"sales"]
        pointers, lengths = options_of(teams)
        indexes, probabilities = (c.c_int32 * 3)(7, 7, 7), (c.c_double * 3)(42, 42, 42)
        routing = b"My card was charged twice for last month's invoice."
        which = b"Which team should handle this message?"
        status = lib.dg_evaluate_choice(model, routing, len(routing), which, len(which), pointers, lengths, 3, None, indexes, probabilities)
        expect(status == 0, f"choice evaluation failed: {error() if status else ''}")
        ranked = list(zip(indexes, probabilities))
        expect(sorted(i for i, _ in ranked) == [0, 1, 2], "choice indexes are a permutation")
        expect(all(ranked[k][1] >= ranked[k + 1][1] for k in range(2)), "choice probabilities descend")
        expect(abs(sum(p for _, p in ranked) - 1) < 1e-9, "choice probabilities sum to one")
        expect(ranked[0][0] == 0, "billing example routes to billing")
        choice_probability = ranked[0][1]
        for bad_items, bad_count, reason in ((teams[:1], 1, "one option"), ([b"a", b" "], 2, "blank option"), ([b"a", b"\xff"], 2, "invalid UTF-8 option")):
            bp, bl = options_of(bad_items)
            bi, bq = (c.c_int32 * 2)(7, 7), (c.c_double * 2)(42, 42)
            expect(lib.dg_evaluate_choice(model, routing, len(routing), which, len(which), bp, bl, bad_count, None, bi, bq) == 1, f"choice rejects {reason}")
            expect(list(bi) == [7, 7] and list(bq) == [42, 42], f"choice outputs untouched: {reason}")
        expect(lib.dg_evaluate_choice(model, routing, len(routing), which, len(which), None, None, 3, None, indexes, probabilities) == 1, "null options rejected")
        expect(lib.dg_evaluate_choice(model, routing, len(routing), which, len(which), pointers, lengths, 3, None, None, probabilities) == 1, "null choice output rejected")
        long_pointers, long_lengths = options_of([b"word " * 600, b"short"])
        expect(lib.dg_evaluate_choice(model, routing, len(routing), which, len(which), long_pointers, long_lengths, 2, None, indexes, probabilities) == 7, "overlong option reported as too long")
        tie_pointers, tie_lengths = options_of([b"same", b"same"])
        ti, tp = (c.c_int32 * 2)(), (c.c_double * 2)()
        expect(lib.dg_evaluate_choice(model, routing, len(routing), which, len(which), tie_pointers, tie_lengths, 2, None, ti, tp) == 0 and list(ti) == [0, 1] and abs(tp[0] - 0.5) < 1e-9, "tied options keep caller order")
        # Explicit criteria are accepted for choices.
        expect(lib.dg_evaluate_choice(model, routing, len(routing), which, len(which), pointers, lengths, 3, c.byref(criteria), indexes, probabilities) == 0, "choice with criteria")
    finally:
        lib.dg_release(model)
    for _ in range(3):
        status, model = load(bundle)
        expect(status == 0, "repeat load")
        try:
            evaluate(model)
        finally:
            lib.dg_release(model)

    from decisiongator import Session
    wrapped = Session.load(str(bundle))
    try:
        wrapped_probability = wrapped.evaluate(content=content.decode(), question=question.decode(), criteria={"yes": yes.decode(), "no": no.decode()})
        expect(abs(wrapped_probability - probability) < 1e-7, "Python/native criteria parity")
    finally:
        wrapped.close()
    def lazy_probability(_):
        value = c.c_double(42)
        status = lib.dg_is_yes_p(content, len(content), question, len(question), c.byref(criteria), c.byref(value))
        expect(status == 0, f"lazy inference failed: {error() if status else ''}")
        expect(abs(value.value - probability) < 1e-7, "lazy/explicit native parity")
        return value.value

    # First lazy call happens from a directory containing none of the model's
    # assets. Parallel callers must share one initialization and produce parity.
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="decisiongator-cwd-") as temporary:
        try:
            os.chdir(temporary)
            with ThreadPoolExecutor(max_workers=3) as workers:
                list(workers.map(lazy_probability, range(6)))
        finally:
            # Windows cannot remove the process's current working directory.
            os.chdir(previous)
    lazy_p = c.c_double()
    expect(lib.dg_is_yes_p(content, len(content), question, len(question), c.byref(criteria), c.byref(lazy_p)) == 0, "probability for threshold boundary")
    decision = c.c_uint8(42)
    expect(lib.dg_is_yes(content, len(content), question, len(question), c.byref(criteria), c.byref(decision)) == 0, "default boolean call")
    expect(decision.value == int(probability >= 0.5), "default boolean/probability parity")
    for threshold in (0.0, 0.5, 1.0, lazy_p.value):
        decision.value = 42
        status = lib.dg_is_yes_at_threshold(content, len(content), question, len(question), c.byref(criteria), threshold, c.byref(decision))
        expect(status == 0, "valid threshold call")
        expect(decision.value == int(lazy_p.value >= threshold), "inclusive threshold boundary/parity")
    decision.value = 42
    expect(lib.dg_is_yes_at_threshold(b"", 0, question, len(question), None, 0.5, c.byref(decision)) == 1 and decision.value == 42, "threshold input failure preserves output")
    # Lazy choice entry points share the default session with dg_is_yes_p.
    lazy_indexes, lazy_probabilities = (c.c_int32 * 3)(), (c.c_double * 3)()
    expect(lib.dg_choose_p(routing, len(routing), which, len(which), pointers, lengths, 3, None, lazy_indexes, lazy_probabilities) == 0, "lazy choose_p")
    expect(abs(lazy_probabilities[0] - choice_probability) < 1e-7 and lazy_indexes[0] == 0, "lazy/explicit choice parity")
    chosen = c.c_int32(7)
    expect(lib.dg_choose(routing, len(routing), which, len(which), pointers, lengths, 3, None, 0.0, c.byref(chosen)) == 0 and chosen.value == 0, "choose default threshold")
    expect(lib.dg_choose(routing, len(routing), which, len(which), pointers, lengths, 3, None, choice_probability, c.byref(chosen)) == 0 and chosen.value == 0, "choose inclusive threshold")
    expect(lib.dg_choose(routing, len(routing), which, len(which), pointers, lengths, 3, None, 1.0, c.byref(chosen)) == 0 and chosen.value == -1, "choose defers below threshold")
    chosen.value = 7
    expect(lib.dg_choose(routing, len(routing), which, len(which), pointers, lengths, 3, None, 1.5, c.byref(chosen)) == 1 and chosen.value == 7, "choose rejects invalid threshold")
    from decisiongator import choose, choose_p
    import decisiongator
    if decisiongator._bundled_directory().resolve() == bundle:
        expect(choose_p(routing.decode(), which.decode(), [t.decode() for t in teams])[0][0] == 0, "Python choose_p")
        expect(choose(routing.decode(), which.decode(), [t.decode() for t in teams], threshold=1.0) is None, "Python choose defers")
    # A subprocess gets an independent lazy singleton. An initially missing
    # manifest must not permanently cache the failure: adding the remaining
    # ordinary bundle files should make the next call succeed.
    retry_program = r'''
import ctypes as c, pathlib, shutil, sys
source, target, library_name = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), sys.argv[3]
lib = c.CDLL(str(target / library_name))
lib.dg_is_yes_p.argtypes = [c.c_char_p, c.c_size_t, c.c_char_p, c.c_size_t, c.c_void_p, c.POINTER(c.c_double)]
lib.dg_is_yes_p.restype = c.c_int32
content, question = b"Please cancel my subscription.", b"Is cancellation requested?"
value = c.c_double(42)
assert lib.dg_is_yes_p(content, len(content), question, len(question), None, c.byref(value)) == 2
assert value.value == 42
for filename in ("manifest.json", "model.onnx", "tokenizer.json", sys.argv[4]):
    shutil.copy2(source / filename, target / filename)
assert lib.dg_is_yes_p(content, len(content), question, len(question), None, c.byref(value)) == 0
assert 0 <= value.value <= 1
'''
    runtime_name = {"Darwin": "libonnxruntime.dylib", "Windows": "onnxruntime.dll", "Linux": "libonnxruntime.so"}[platform.system()]
    with tempfile.TemporaryDirectory(prefix="decisiongator-retry-") as temporary:
        target = Path(temporary)
        shutil.copy2(bundle / name, target / name)
        retry = subprocess.run([sys.executable, "-c", retry_program, str(bundle), str(target), name, runtime_name], capture_output=True, text=True)
        expect(retry.returncode == 0, f"lazy failed-load retry or clean exit failed: {retry.stderr}")
    return {"checks": checks, "status": "passed", "unicode_criteria_p_yes": probability}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=ROOT / "released" / "macos-arm64")
    args = parser.parse_args()
    print(json.dumps(check(args.bundle.resolve()), indent=2))
