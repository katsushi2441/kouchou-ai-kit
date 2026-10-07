#!/bin/bash
# GPU が空いたときだけ1モデルずつ抽出を回す（ほかの処理とGPUを取り合わない・メインメモリにはみ出させない）。
#   bash run_when_idle.sh "<モデル> <アドレス> <名前>" ...
# 空き＝ホストの Ollama に読み込み中のモデルが無く、GPU の使用量が 15GB 未満、メインメモリの使える残りが 8GB 以上。
set -u
B=/home/kojima/work/kouchou-ai-kit/bench
idle() {
  n=$(curl -s http://127.0.0.1:11434/api/ps | /usr/bin/python3 -c "import sys,json;print(len(json.load(sys.stdin)['models']))")
  g=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
  a=$(free -g | awk '/^Mem:/{print $7}')
  [ "$n" = 0 ] && [ "$g" -lt 15000 ] && [ "$a" -ge 8 ]
}
for spec in "$@"; do
  set -- $spec; model=$1; addr=$2; name=$3
  until idle; do sleep 60; done
  echo "$(date +%T) start $name"
  docker exec kouchou-ai-api-1 python /tmp/bench/run_extraction.py "$model" "$addr" "$name"
  docker cp kouchou-ai-api-1:/tmp/bench/results/$name.jsonl $B/results/
  # 終わったらすぐ降ろす
  if [ "$addr" = "ollama:11434" ]; then docker exec kouchou-ai-ollama-1 ollama stop "$model"; else curl -s http://127.0.0.1:11434/api/generate -d "{\"model\":\"$model\",\"keep_alive\":0}" >/dev/null; fi
  echo "$(date +%T) done $name $(wc -l < $B/results/$name.jsonl)"
done
