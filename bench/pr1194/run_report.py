#!/usr/bin/env python3
"""kouchou-ai #1194 の検証: api コンテナにレポート作成を投入し、終わるまで待って時間を記録する。

管理画面（admin）が送るのと同じ POST /admin/reports を直接呼ぶ（admin のビルドは省いた）。
プロンプトは admin の既定値（apps/admin/app/create/*.ts）、データは管理画面のサンプル（apps/admin/public/sample_comments.csv）の先頭 N 件。

  /usr/bin/python3 run_report.py <slug> <model> <N> [workers]
環境変数: KOUCHOU_ROOT（PR のブランチの場所）, KOUCHOU_API
"""
import csv, json, os, re, sys, time, urllib.request

ROOT = os.environ.get("KOUCHOU_ROOT", "/home/kojima/work/kouchou-ai-pr1193")
API = os.environ.get("KOUCHOU_API", "http://127.0.0.1:18388")
HERE = os.path.dirname(os.path.abspath(__file__))
slug, model, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
workers = int(sys.argv[4]) if len(sys.argv) > 4 else 2

env = dict(l.rstrip("\n").split("=", 1) for l in open(f"{ROOT}/.env") if "=" in l and not l.startswith("#"))
KEY = env["ADMIN_API_KEY"].strip()
HDR = {"Content-Type": "application/json", "x-api-key": KEY}

def prompt_of(name):
    src = open(f"{ROOT}/apps/admin/app/create/{name}.ts", encoding="utf-8").read()
    return re.search(r"= `(.*)`", src, re.S).group(1)

rows = list(csv.DictReader(open(f"{ROOT}/apps/admin/public/sample_comments.csv", encoding="utf-8")))[:n]
comments = [{"id": str(i + 1), "comment": r["comment"], "source": None, "url": None} for i, r in enumerate(rows)]
body = {
    "input": slug, "question": f"#1194 検証 {model} {n}件", "intro": "PR #1193 の動作確認（管理画面のサンプル）",
    "cluster": [3, 6], "model": model, "workers": workers,
    "prompt": {k: prompt_of(v) for k, v in [("extraction", "extractionPrompt"), ("initial_labelling", "initialLabellingPrompt"),
                                            ("merge_labelling", "mergeLabellingPrompt"), ("overview", "overviewPrompt")]},
    "comments": comments, "is_pubcom": False, "inputType": "file",
    "is_embedded_at_local": True, "provider": "local", "local_llm_address": "ollama:11434",
}
def call(method, path, data=None, timeout=60):
    req = urllib.request.Request(API + path, data=json.dumps(data).encode() if data is not None else None, headers=HDR, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode() or "null")

t0 = time.time()
st, res = call("POST", "/admin/reports", body)
print(time.strftime("%H:%M:%S"), "投入", st, flush=True)
status, last = None, None
while True:
    time.sleep(10)
    try:
        _, reps = call("GET", "/admin/reports")
    except Exception as e:
        print("  一覧の取得に失敗", e, flush=True); continue
    me = next((r for r in reps if r.get("slug") == slug), None)
    status = me.get("status") if me else None
    step = None
    p = f"{ROOT}/apps/api/broadlistening/pipeline/outputs/{slug}/hierarchical_status.json"
    if os.path.exists(p):
        try:
            j = json.load(open(p)); step = j.get("current_job") or j.get("status")
        except Exception: pass
    if (status, step) != last:
        print(time.strftime("%H:%M:%S"), f"{time.time()-t0:6.0f}秒", "status=", status, "step=", step, flush=True); last = (status, step)
    if status in ("ready", "error"): break
    if time.time() - t0 > 3 * 3600: print("3時間で打ち切り"); break
total = time.time() - t0
out = {"slug": slug, "model": model, "n": n, "workers": workers, "status": status, "total_sec": round(total, 1),
       "reasoning_effort_env": env.get("LOCAL_LLM_REASONING_EFFORT", ""), "steps": {}}
p = f"{ROOT}/apps/api/broadlistening/pipeline/outputs/{slug}/hierarchical_status.json"
if os.path.exists(p):
    j = json.load(open(p))
    out["steps"] = {c.get("step"): round(float(c.get("duration") or 0), 1) for c in j.get("completed_jobs", [])}
    out["pipeline_status"] = j.get("status"); out["error"] = (j.get("error") or "")[:500]
a = f"{ROOT}/apps/api/broadlistening/pipeline/outputs/{slug}/args.csv"
if os.path.exists(a): out["args"] = sum(1 for _ in open(a, encoding="utf-8")) - 1
json.dump(out, open(f"{HERE}/results/{slug}.json", "w"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
