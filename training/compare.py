"""Evaluate a saved checkpoint or three-way NLI baseline without exporting it."""
import argparse
import json
from pathlib import Path
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from training.pipeline import read_data, expand, metrics, predict, digest, prompt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--revision')
    parser.add_argument('--nli-baseline',action='store_true')
    parser.add_argument('--data',action='append',required=True)
    parser.add_argument('--split',choices=['train','validation','calibration','test'],required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    torch.set_num_threads(4)
    device='mps' if torch.backends.mps.is_available() else 'cpu'
    options={'revision':args.revision} if args.revision else {}
    tokenizer=AutoTokenizer.from_pretrained(args.checkpoint,**options)
    model=AutoModelForSequenceClassification.from_pretrained(args.checkpoint,attn_implementation='eager',**options).to(device).eval()
    rows=[r for r in expand(read_data(args.data)) if r['split']==args.split]
    if args.nli_baseline:
        if model.config.id2label != {0:'contradiction',1:'entailment',2:'neutral'}:
            raise ValueError('Unexpected NLI label order')
        probabilities=[]
        with torch.no_grad():
            for row in rows:
                # Explicit heuristic baseline. No neutral score is discarded.
                hypothesis=row['criteria']['yes'] if row.get('criteria') else row['question']
                encoded=tokenizer(row['content'],hypothesis,return_tensors='pt',truncation=False)
                if encoded['input_ids'].shape[1]>256: raise ValueError('Overlength baseline input')
                p=model(**{k:v.to(device) for k,v in encoded.items()}).logits.softmax(-1)[0]
                probabilities.append((p[1]+.5*p[2]).item())
    else:
        probabilities=predict(model,tokenizer,rows,device)
    report=metrics(rows,probabilities)
    report.update({'checkpoint':args.checkpoint,'revision':args.revision,'split':args.split,
                   'data_sha256':{str(p):digest(p) for p in args.data},
                   'method':'NLI heuristic: entailment + half neutral; question is hypothesis without criteria, yes rule otherwise' if args.nli_baseline else 'uncalibrated binary checkpoint',
                   'predictions':[{'id':r['id'],'label':r['label'],'p_yes':p} for r,p in zip(rows,probabilities)]})
    Path(args.output).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('count','accuracy','brier','log_loss')},indent=2))

if __name__=='__main__': main()
