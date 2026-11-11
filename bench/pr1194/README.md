# kouchou-ai #1194 の検証（PR #1193：Ollama の既定モデル gemma4:e4b と LOCAL_LLM_REASONING_EFFORT）

2026年11月11日に測りました。PR #1193 のブランチ（`fix/local-llm-thinking-default-model`・d7bed3b8）を別フォルダに展開し、
`compose.bench.yaml` を重ねて、api と ollama の2つのコンテナだけを動かしています。

## 環境

- CPU: AMD Ryzen 7 5700X のうち 4コア（8スレッド）だけを割り当て（`cpuset: "0-3,8-11"`）
- メモリ: ollama 12GB ＋ api 4GB（`mem_limit`）
- GPU: 使わない（compose の GPU の予約を外した。起動ログは `library=cpu`）
- OS: Ubuntu 22.04.5 LTS、Docker 28.4.0、Docker Compose v2.39.2
- Ollama: 0.33.2（`ollama/ollama:latest` のコンテナ）

## やり方

```
git fetch upstream pull/1193/head:pr-1193 && git worktree add ../kouchou-ai-pr1193 pr-1193
cd ../kouchou-ai-pr1193 && cp .env.example .env    # OLLAMA_HOST_PORT だけ空きポートに変更
docker compose -p kouchou1194 -f compose.yaml -f <このフォルダ>/compose.bench.yaml --profile ollama up -d ollama
docker compose -p kouchou1194 -f compose.yaml -f <このフォルダ>/compose.bench.yaml --profile ollama up -d --build api
/usr/bin/python3 run_report.py <slug> <モデル> 20 2
```

`run_report.py` は、管理画面が送るのと同じ `POST /admin/reports` を直接呼びます（admin はビルドしていません）。
データは管理画面のサンプル（`apps/admin/public/sample_comments.csv`）の先頭20件、プロンプトは admin の既定値、並列数は2、クラスタは 3 → 6 です。

## 結果（20件）

| | gemma4:e4b・指定なし | gemma4:e4b・`none` | ELYZA-JP-8B・`none` |
|---|---|---|---|
| 最後まで作れたか | 作れず（統合ラベルで待ち時間切れ） | 作れた | 作れた |
| 全体 | 50分24秒で中止 | 11分51秒 | 9分11秒 |
| 抽出（20件） | 18分40秒 | 3分40秒 | 3分50秒 |
| 抽出の1回の呼び出し（中央値・2件同時） | 107.5秒 | 21.1秒 | 19.5秒 |
| 初期ラベル | 12分41秒（1回 約4分） | 2分20秒 | 2分30秒 |
| 統合ラベル | 5分の待ち時間切れが6回 | 1分40秒 | 1分40秒 |
| 呼び出しの失敗 | 33回中6回 | 30回中0回 | 29回中0回 |

段ごとの時間は、10秒おきに状態を見た記録（`results/*.log`）から出しています。
`hierarchical_status.json` の `completed_jobs[].duration` は、3本とも全段 0.0 でした。

## ファイル

- `compose.bench.yaml` … 重ねた設定（ポート・CPU・メモリ・GPU なし）
- `run_report.py` … 投入と記録
- `results/<slug>.log` `.json` … 状態の移り変わりと結果
- `results/ollama_requests_all.txt` … Ollama 側の呼び出しの記録（時刻・応答コード・かかった時間）
- `results/e4b-empty-20.analysis.log` … 指定なしで失敗したときの広聴AIのログ
