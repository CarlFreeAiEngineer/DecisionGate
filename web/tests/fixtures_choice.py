#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Freeze browser choose/chooseP references from the native choice-capable library.

released/macos-arm64 predates dg_evaluate_choice; models/choose-dev-macos carries
the identical model.onnx and tokenizer.json (same sha256 in both manifests) plus
the choice entry points, so it is used here instead. Writes a small, separate
JSON file (not fixtures.json) so the existing tokenizer/pYes fixture pipeline,
which still targets released/macos-arm64, is left untouched.
"""
import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from decisiongate import Session

bundle = root / 'models/choose-dev-macos'
cases = [
    {'content': "My card was charged twice for last month's invoice.",
     'question': 'Which team should handle this message?',
     'options': ['billing', 'technical support', 'sales']},
    {'content': 'Please route this ticket to the right queue.',
     'question': 'Which option applies?',
     'options': ['same', 'same']},
    {'content': 'The app crashes whenever I open settings.',
     'question': 'Which team should handle this message?',
     'options': ['billing', 'technical support', 'sales'],
     'criteria': {'yes': 'a technical malfunction', 'no': 'a billing or sales question'}},
    {'content': 'I would like to cancel my subscription and get a refund.',
     'question': 'What is the best next step?',
     'options': ['escalate to a manager', 'send a refund policy link', 'close the ticket', 'offer a discount', 'transfer to billing']},
    {'content': 'Where is your office located?',
     'question': 'Which category fits best?',
     'options': ['location', 'hours']},
]
fixtures = []
with Session.load(bundle) as session:
    for case in cases:
        criteria = case.get('criteria')
        ranking = session.evaluate_choice(case['content'], case['question'], case['options'], criteria)
        fixtures.append({
            'content': case['content'], 'question': case['question'], 'options': case['options'],
            'criteria': criteria, 'ranking': [[int(index), probability] for index, probability in ranking],
        })
(root / 'web/tests/fixtures-choice.json').write_text(json.dumps(fixtures, ensure_ascii=True) + '\n')
print(f'{len(fixtures)} native choice references')
