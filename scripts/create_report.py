#!/usr/bin/env python3
"""広聴AIにサンプル意見48件のレポート生成を投入する(完全ローカル構成の実測用)。

- プロンプトは admin アプリの既定値(TSファイル)から抽出して同じものを使う
- provider=local (コンテナ内Ollama/ELYZA-JP-8B) + is_embedded_at_local=True
- 認証は kouchou-ai/.env の ADMIN_API_KEY
"""
import csv, json, os, re, sys, time, urllib.request

ROOT = "/home/kojima/work/kouchou-ai"
KIT  = "/home/kojima/work/kouchou-ai-kit"
API  = "http://127.0.0.1:18364"

env = dict(l.split("=",1) for l in open(f"{ROOT}/.env") if "=" in l and not l.startswith("#"))
KEY = env["ADMIN_API_KEY"].strip()

def prompt_of(name):
    src = open(f"{ROOT}/apps/admin/app/create/{name}.ts", encoding="utf-8").read()
    m = re.search(r"= `(.*)`", src, re.S)
    return m.group(1)

comments = [{"id": r["comment-id"], "comment": r["comment-body"], "source": r["source"]}
            for r in csv.DictReader(open(f"{KIT}/data/sample_comments.csv"))]

body = {
    "input": "nagoya-machizukuri-sample",
    "question": "まちづくりへの意見(架空サンプル48件)",
    "intro": "広聴AIの動作デモ用に用意した架空のサンプル意見48件を、完全ローカル構成(ELYZA-JP-8B+ローカル埋め込み)で分析したレポートです。実在の自治体・団体への意見ではありません。",
    "cluster": [3, 8],
    "model": "hf.co/elyza/Llama-3-ELYZA-JP-8B-GGUF:latest",
    "workers": 2,
    "prompt": {
        "extraction": prompt_of("extractionPrompt"),
        "initial_labelling": prompt_of("initialLabellingPrompt"),
        "merge_labelling": prompt_of("mergeLabellingPrompt"),
        "overview": prompt_of("overviewPrompt"),
    },
    "comments": comments,
    "is_pubcom": False,
    "inputType": "file",
    "is_embedded_at_local": True,
    "provider": "local",
    "local_llm_address": "ollama:11434",
}
req = urllib.request.Request(f"{API}/admin/reports", data=json.dumps(body).encode(),
    headers={"Content-Type": "application/json", "x-api-key": KEY}, method="POST")
t0 = time.time()
with urllib.request.urlopen(req, timeout=60) as r:
    print("投入:", r.status, r.read().decode()[:200])
print("slug: nagoya-machizukuri-sample / 開始:", time.strftime("%H:%M:%S"))
