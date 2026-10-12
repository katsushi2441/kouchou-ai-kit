# GPUなし（CPUだけ）で広聴AIのローカルLLMを測る（kouchou-ai #471）

2026年10月12日に測りました。自治体の普通のPCを想定し、同じ機械で使えるCPUとメモリを絞っています。

## 環境

- CPU: AMD Ryzen 7 5700X のうち **4コア（8スレッド）だけ**を割り当て（systemd の CPUAffinity）
- メモリ: **上限16GB**（systemd の MemoryMax）
- GPU: **使わない**（Ollama 0.30.9・`library=cpu`）
- モデル: ELYZA-JP-8B（GGUF・4.9GB）、gemma4:e4b、gemma4:12b-it-qat

### GPUを本当に切るには

`CUDA_VISIBLE_DEVICES=-1` だけでは足りませんでした。Ollama は Vulkan 経由で GPU（RTX 3090）を見つけて使おうとします。
CPUだけで測るには、次も要りました。起動ログに `inference compute ... library=cpu` と出ることを確かめてください。

```
CUDA_VISIBLE_DEVICES=-1 GGML_VK_VISIBLE_DEVICES=-1 OLLAMA_VULKAN=false OLLAMA_HOST=0.0.0.0:18396 ollama serve
```

## 1. モデルサーバ層（`tokps.py`）

既定の抽出プロンプト＋コメント1件を4回流し、2回目以降の中央値。

| モデル | 出力 tok/s | 入力 tok/s | 1件 | 初回の読み込み |
|---|---:|---:|---:|---:|
| ELYZA-JP-8B | 5.7 | 357 | 7.4秒 | 10秒 |
| gemma4:e4b | 8.1 | 50 | 11.5秒 | 70秒 |
| gemma4:12b-it-qat | 3.3 | 18 | 30.6秒 | 41秒 |

ELYZA の入力が速いのは、2回目以降にシステムプロンプトのキャッシュが効いているためと見ています。

## 2. パイプライン層・抽出（`../run_extraction.py`）

広聴AIの `analysis_core.steps.extraction.extract_arguments` を、`local` プロバイダのまま上のCPUサーバに向けて、サンプル20件。

| モデル | 1件（中央値） | 20件の合計 | 失敗 |
|---|---:|---:|---:|
| ELYZA-JP-8B | 7.9秒 | 3分5秒 | 0 |

この速さだと、抽出だけで100件 約13分、1,000件 約2時間10分の見込み。
埋め込み・クラスタリング・ラベル付け・概要を含めた全体の時間は、まだ測っていません。

結果: `results/tokps_cpu4c.json`、`results/cpu4c_elyza.jsonl`
