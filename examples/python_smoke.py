#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Call the bundled component without training dependencies or load ceremony."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from decisiongate import is_yes_p, is_yes, choose, choose_p
for content, question in [
        ('Please return my money. The item arrived broken.', 'Is the customer asking for a refund?'),
        ('Could you send me a copy of the invoice?', 'Is the customer asking for a refund?'),
    ]:
    print(f'yes={is_yes(content,question)} p_yes={is_yes_p(content,question):.4f}  {content}')
teams = ['billing', 'technical support', 'sales']
message = 'My card was charged twice for last month\'s invoice.'
ranked = choose_p(message, 'Which team should handle this message?', teams)
print(f'ranked={[(teams[i], round(p, 3)) for i, p in ranked]}')
print(f"choose={choose(message, 'Which team should handle this message?', teams, threshold=0.6)}")
print('Experimental model: these estimates are not reliable enough for real decisions.')
