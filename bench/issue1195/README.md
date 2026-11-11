# Issue #1195 の測定（x86・GPU なし・gemma4:e4b・レポート全体）

digitaldemocracy2030/kouchou-ai の Issue #1195 に答えるための測定の記録です。

## 条件

- 本体: upstream/main 4f506750（#1193・#1198 が入った版）
- 測定スクリプト: `experiments/local_llm_bench/bench.py`（本体のもの。変更なし）
- モデル: `gemma4:e4b`、`--reasoning-effort none`、`--workers` は既定の 1
- 入力: 管理画面のサンプル（bench.py の既定）の先頭 100 件・400 件
- PC: AMD Ryzen 7 5700X のうち 4 コア 8 スレッドだけを使用（`cpuset 0-3,8-11`）、Ubuntu 22.04.5、Docker 28.4.0
- Ollama: 0.33.2 のコンテナ、メモリ上限 12GB、GPU の予約なし、`CUDA_VISIBLE_DEVICES=-1`・`OLLAMA_VULKAN=false`・`GGML_VK_VISIBLE_DEVICES=-1`、起動ログで `library=cpu` を確認
- 分析のプロセス: `taskset -c 0-3,8-11`、`MemoryMax=4G`、torch CPU 版、`CUDA_VISIBLE_DEVICES=` を空に

## 実行したコマンド

```
systemd-run --user --scope -q -p MemoryMax=4G taskset -c 0-3,8-11 env CUDA_VISIBLE_DEVICES= \
  .venv/bin/python <kouchou-ai>/experiments/local_llm_bench/bench.py \
  --model gemma4:e4b --address 127.0.0.1:18389 --reasoning-effort none \
  --n 100 --n 400 --workdir bench-work --out results/bench-results.csv
```

Ollama のコンテナは `../pr1194/compose.bench.yaml` と同じ設定です。

## 結果

- `results/bench-results.csv` … bench.py が書いた記録（1 回 1 行）
- `results/bench.log` … 画面の出力
- `results/logs/` … 分析の記録
- `results/status/` … `hierarchical_status.json` と概要の文
- `results/configs/` … bench.py が作った設定

| | 100 件 | 400 件 |
|---|---|---|
| 完走 | した | した |
| 全体 | 37.9 分 | 104.1 分 |
| 抽出 | 1312.3 秒 | 4615.4 秒 |
| 分析プロセスのメモリ最大 | 2,091 MB | 1,791 MB |
