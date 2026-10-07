#!/usr/bin/env python3
"""広聴AIの意見抽出（analysis_core.steps.extraction.extract_arguments）を、既定のプロンプトのまま
ローカルLLMごとに回して、結果を JSONL に残す。kouchou-ai の api コンテナの中で動かす（同じコードで測るため）。

  docker cp bench kouchou-ai-api-1:/tmp/bench
  docker exec kouchou-ai-api-1 python /tmp/bench/run_extraction.py <モデル> <アドレス> [出力名]
"""
import json, sys, time
from analysis_core.prompts import get_default_prompt
from analysis_core.steps.extraction import extract_arguments

model, address = sys.argv[1], sys.argv[2]
name = sys.argv[3] if len(sys.argv) > 3 else model.replace("/", "_").replace(":", "_")
import os
rows = json.load(open("/tmp/bench/data/comments.json", encoding="utf-8"))[: int(os.environ.get("LIMIT", "100000"))]
prompt = open(os.environ["PROMPT_FILE"], encoding="utf-8").read() if os.environ.get("PROMPT_FILE") else get_default_prompt("extraction")
out = open(f"/tmp/bench/results/{name}.jsonl", "w", encoding="utf-8")
for r in rows:
    t0 = time.time()
    rec = {**r, "model": model}
    try:
        items, ti, to, tt = extract_arguments(r["text"], prompt, model, provider="local", local_llm_address=address, timeout_seconds=300)
        rec.update(items=items, tokens_out=to)
    except Exception as e:
        rec.update(items=None, error=f"{type(e).__name__}: {str(e)[:300]}")
    rec["sec"] = round(time.time() - t0, 2)
    out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush()
print(name, "done", len(rows))
