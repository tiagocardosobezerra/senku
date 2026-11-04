#!/bin/bash
# usage: runall.sh carta.json  -> runs every command with SENKU_DEPURAR=1, prints tracebacks
SK=/c/Users/tiago/AppData/Local/Temp/senku-review-r5/senku
C="$1"
export SENKU_DEPURAR=1 PYTHONIOENCODING=utf-8
for cmd in "validar $C" "lacunas $C --todas" "analisar $C --todas" "desenhar $C" "desenhar $C --pools -o $(dirname $C)/saida_pools" "documentar $C" "situacao $C"; do
  out=$(python $SK/senku.py $cmd 2>&1); rc=$?
  if echo "$out" | grep -q Traceback; then echo "### CRASH: $cmd"; echo "$out" | tail -6; else echo "### ok($rc): $cmd"; fi
done
