#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check automatic Python initialization, retry, reuse, and native parity."""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import decisiongate as dg

content = 'Please return my money. The item arrived broken.'
question = 'Is the customer asking for a refund?'
# A failed initialization must not poison subsequent calls.
with patch.object(dg.Session, 'load', side_effect=dg.DecisionGateError(2, 'test failure')):
    try:
        dg.is_yes_p(content, question)
    except dg.DecisionGateError as error:
        assert error.status == 2
    else:
        raise AssertionError('Expected initialization failure')
assert dg._default_session is None

# Threshold validation precedes loading, including non-finite and wrong types.
with patch.object(dg, 'is_yes_p', return_value=0.5) as estimate:
    assert dg.is_yes(content, question) is True
    assert dg.is_yes(content, question, threshold=0.500001) is False
    assert dg.is_yes(content, question, threshold=0) is True
    assert dg.is_yes(content, question, threshold=1) is False
    for invalid in (-0.1, 1.1, float('nan'), float('inf'), -float('inf'), None, '0.5', True):
        estimate.reset_mock()
        try:
            dg.is_yes(content, question, threshold=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid threshold accepted')
        estimate.assert_not_called()
with patch.object(dg, 'is_yes_p', side_effect=dg.DecisionGateError(5, 'test failure')):
    try:
        dg.is_yes(content, question)
    except dg.DecisionGateError as error:
        assert error.status == 5
    else:
        raise AssertionError('Boolean helper hid an inference error')

previous = Path.cwd()
with tempfile.TemporaryDirectory() as directory:
    os.chdir(directory)
    try:
        with patch.object(dg.Session, 'load', wraps=dg.Session.load) as load:
            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(lambda _: dg.is_yes_p(content, question), range(8)))
            assert load.call_count == 1, 'Concurrent calls must share one session'
        assert all(abs(value - 0.9962034385661188) < 1e-6 for value in results)
        assert dg.is_yes_p('Could you send me a copy of the invoice?', question) < 0.01
        assert dg.is_yes(content, question) is True
        assert dg.is_yes('Could you send me a copy of the invoice?', question) is False
        assert dg.is_yes(content, question, threshold=1) is False
        try:
            dg.is_yes('', question)
        except dg.DecisionGateError:
            pass
        else:
            raise AssertionError('Invalid input must raise, not return a probability')
    finally:
        os.chdir(previous)
print('Python automatic initialization, retry, concurrent reuse, cwd independence, and parity passed.')
