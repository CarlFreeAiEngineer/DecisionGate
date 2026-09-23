#!/bin/bash
# usage: ft.sh BASE OUT LR
set -e
cd /content/dg
EXTRA="--extra-data data/expansion-v2.jsonl --extra-data data/choices.jsonl"
for f in data/v4/*.jsonl; do case "$f" in *test-*) ;; *) EXTRA="$EXTRA --extra-data $f";; esac; done
python -c "import training.pipeline as p; p.main()" train --output "$2" --base "$1" --revision main --template 2 --learning-rate "$3" --epochs 5 --batch-size 16 --seed 42 --device cuda $EXTRA
