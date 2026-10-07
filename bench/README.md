# 意見抽出の誤読をローカルLLMで測る（kouchou-ai #471 の続き）

広聴AI（[digitaldemocracy2030/kouchou-ai](https://github.com/digitaldemocracy2030/kouchou-ai)）の意見抽出
（`analysis_core.steps.extraction.extract_arguments`）を、そのままローカルLLMに当てて、元のコメントと意味が変わった抽出が
どのくらい出るかを数えたものです。2026年10月7日に測りました。

## 何を測ったか

- モデル：`gemma4:12b-it-qat`（Ollama・量子化版）。RTX 3090 1枚。
- 入力：広聴AIに同梱のサンプルから208件
  - `apps/admin/public/sample_comments.csv` から4件おきに100件（AIについての短い日本語の意見）
  - `apps/api/broadlistening/pipeline/inputs/nagoya-machizukuri-sample.csv` の48件（まちづくりの日本語の声・架空）
  - `apps/api/broadlistening/pipeline/inputs/example-polis.csv` から60件（英語。日本語にして抽出する）
- プロンプト：既定（`get_default_prompt("extraction")`）、v2（誤読を避ける指示を5行足したもの）、v3（v2 に「必ず1つ以上抜き出す」「英語は訳す」を足したもの）。`data/prompt_*.txt`
- 判定：抽出結果を、どのモデル・プロンプトの出力かを伏せて別のLLM（Claude）に渡し、次の型に分けた（`judge.py`）。
  引っかかったものは全件、問題なしとされたものからも24件を人が読んで確かめた。
  - 意味が変わった：賛否・主体の取り違え・比較の向き・原文にない追加・抜け・その他の意味の変化
  - 失敗：抽出が空、または日本語になっていない
  - 軽い：確信度の変化（推量→断定など）

## 結果（208件）

| 版 | 意味が変わった | 失敗（空・日本語でない） | 軽い（確信度） | 1件の平均 |
|---|---|---|---|---|
| 既定（1回目） | 6 | 0 | 3 | 8.8秒 |
| 既定（2回目・同じ条件） | 7 | 1 | 3 | 8.3秒 |
| v2 | 4 | 6 | 0 | 11.8秒 |
| v3 | 9 | 6 | 0 | 12.4秒 |

- 温度0でも結果は揺れる。既定のプロンプトを同じ条件で2回回すと、出力が完全に一致したのは208件中184件。誤読した文も入れ替わる。
- だから1回ずつの比較ではプロンプトの良し悪しを決められない（±3件ほどは揺れの範囲）。
- はっきり出たのは2点：指示を足すと確信度の変化は3件→0件に減るが、抽出が空・英語のままの失敗が0〜1件→6件に増える。
- 指示を増やした v3 では「交付」のような原文にない語が混ざって文が壊れる例が増えた（既定の2回目にも同じ壊れ方があり、このモデルの癖と見られる）。

件ごとの出力は `results/<版>.jsonl`、判定（型と理由）は `results/<版>.judged.jsonl`。

## 動かし方

```bash
# kouchou-ai の api コンテナの中で、同じコードで抽出する
docker cp bench kouchou-ai-api-1:/tmp/bench
docker exec kouchou-ai-api-1 python /tmp/bench/run_extraction.py gemma4:12b-it-qat <OllamaのホストIP>:11434 gemma4_12b
docker exec -e PROMPT_FILE=/tmp/bench/data/prompt_v2.txt kouchou-ai-api-1 python /tmp/bench/run_extraction.py gemma4:12b-it-qat <OllamaのホストIP>:11434 gemma4_12b_v2
docker cp kouchou-ai-api-1:/tmp/bench/results/gemma4_12b.jsonl bench/results/

# 判定（claude CLI が要る）
python3 bench/judge.py bench/results/gemma4_12b.jsonl
```

`run_when_idle.sh` は、GPU をほかの処理と分け合っている環境で、空いたときだけ1モデルずつ回すための当社用のスクリプトです。
