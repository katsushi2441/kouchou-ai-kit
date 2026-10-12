#!/usr/bin/env python3
"""GPU なし（CPU だけ）の Ollama で、ローカルLLMの速さを測る（kouchou-ai #471・モデルサーバ層）。

広聴AIの意見抽出に近い長さの日本語の入力（コメント1件＋既定の抽出プロンプト）を渡し、
読み込み時間・入力の処理速度（prompt tok/s）・出力の速度（eval tok/s）を Ollama の応答の数字から出す。
1回目はモデルの読み込みを含むので別に記録し、2回目以降の中央値を速さとする。

  python3 tokps.py <ollamaのURL> <ラベル> <モデル>...
  例: python3 tokps.py http://127.0.0.1:18396 cpu4c gemma4:12b-it-qat
"""
import json
import statistics
import sys
import time
import urllib.request

url, label, models = sys.argv[1], sys.argv[2], sys.argv[3:]
here = __file__.rsplit("/", 1)[0]
prompt_sys = open(f"{here}/../data/prompt_default.txt", encoding="utf-8").read()
comments = [c["text"] for c in json.load(open(f"{here}/../data/comments.json", encoding="utf-8"))[:4]]


def gen(model, text):
    body = {"model": model, "stream": False, "think": False,
            "options": {"temperature": 0, "num_predict": 200},
            "messages": [{"role": "system", "content": prompt_sys}, {"role": "user", "content": text}]}
    req = urllib.request.Request(f"{url}/api/chat", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    r = json.loads(urllib.request.urlopen(req, timeout=1800).read())
    r["wall"] = time.time() - t0
    return r


out = []
for m in models:
    runs = []
    for i, text in enumerate(comments):
        r = gen(m, text)
        rec = {"label": label, "model": m, "run": i, "wall_s": round(r["wall"], 2),
               "load_s": round(r.get("load_duration", 0) / 1e9, 2),
               "prompt_tokens": r.get("prompt_eval_count"),
               "prompt_tok_s": round(r["prompt_eval_count"] / (r["prompt_eval_duration"] / 1e9), 1) if r.get("prompt_eval_duration") else None,
               "eval_tokens": r.get("eval_count"),
               "eval_tok_s": round(r["eval_count"] / (r["eval_duration"] / 1e9), 2) if r.get("eval_duration") else None}
        runs.append(rec)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
    warm = runs[1:]
    summ = {"label": label, "model": m, "first_wall_s": runs[0]["wall_s"], "load_s": runs[0]["load_s"],
            "median_wall_s": statistics.median(x["wall_s"] for x in warm),
            "median_prompt_tok_s": statistics.median(x["prompt_tok_s"] for x in warm if x["prompt_tok_s"]),
            "median_eval_tok_s": statistics.median(x["eval_tok_s"] for x in warm if x["eval_tok_s"])}
    print("SUMMARY", json.dumps(summ, ensure_ascii=False), flush=True)
    out.append({"summary": summ, "runs": runs})
    # 次のモデルの前にメモリを空ける（16GB に絞っているので2つ同時には載らない）
    urllib.request.urlopen(urllib.request.Request(f"{url}/api/generate", data=json.dumps({"model": m, "keep_alive": 0}).encode(),
                                                  headers={"Content-Type": "application/json"}), timeout=60).read()
json.dump(out, open(f"{here}/results/tokps_{label}.json", "w"), ensure_ascii=False, indent=1)
