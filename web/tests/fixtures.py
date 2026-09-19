#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["tokenizers==0.21.4"]
# ///
"""Freeze browser references from the released native tokenizer and C library."""
import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from tokenizers import Tokenizer
from decisiongate import Session
bundle = root / 'released/macos-arm64'
tokenizer = Tokenizer.from_file(str(bundle / 'tokenizer.json'))
rows = []
for name in ['seed', 'plain-questions', 'expansion-v2', 'evaluation-v2']:
    rows.extend(json.loads(line) for line in (root / f'data/{name}.jsonl').read_text().splitlines() if line.strip())
for content in ['Café e\u0301 中文 العربية 👨‍👩‍👧‍👦 𐐀', 'a\u0085b\u00a0c\u2003d\u2028e\u2029f\uFEFFg', 'hello\t \n\r\v\f there', '<s>word</s><mask> <pad> <unk>', "I'm not asking for a visit. DON'T book one.", 'a\x00b\u200bc', 'Could I arrange a meeting next Tuesday?']:
    rows.append({'content':content,'question':'Is this an appointment request?'})
fixtures=[]
with Session.load(bundle) as session:
    for i,row in enumerate(rows):
        criteria = row.get('criteria')
        prompt=row['question']
        if criteria: prompt += '\nYes: '+criteria['yes']+'\nNo: '+criteria['no']
        enc=tokenizer.encode(row['content'], prompt)
        item={'content':row['content'],'question':row['question'],'criteria':criteria,'ids':enc.ids,'attention_mask':enc.attention_mask,'token_type_ids':enc.type_ids}
        if i >= len(rows)-87: item['pYes']=session.evaluate(row['content'],row['question'],criteria)
        fixtures.append(item)
(root / 'web/tests/fixtures.json').write_text(json.dumps(fixtures,ensure_ascii=True)+'\n')
print(f'{len(fixtures)} token references; {sum("pYes" in row for row in fixtures)} native output references')
