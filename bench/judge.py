#!/usr/bin/env python3
"""意見抽出の結果を、元のコメントと見比べて誤読を判定する（claude -p に、どのモデルの出力かを伏せて渡す）。

  /usr/bin/python3 judge.py results/<name>.jsonl      → results/<name>.judged.jsonl

判定の決まり（言い換え・要約・翻訳・分割は誤読にしない。意味が変わったものだけを数える）:
  meaning   意味が変わった（下のどれにも当てはまらない変化）
  polarity  賛否・肯定否定・要望の向きが逆になった
  subject   主体・対象の取り違え（誰が／何を、が入れ替わる・別のものになる）
  compare   比較・優先の向きが逆になった（AよりB → BよりA）
  added     原文にない主張・条件・事実が足された
  dropped   原文の主要な意見が抜けた（複数の意見のうち一部が消えた）
  hedge     確信の度合いが変わった（「かもしれない」→断定、その逆）。軽微として別に数える
  format    抽出が空・失敗、または日本語でない
"""
import json
import subprocess
import sys

BATCH = 26
RUBRIC = """あなたは、意見抽出の結果を検査する校閲者です。各項目について、元のコメント（original）と、そこから抽出された意見のリスト（extracted）を見比べ、抽出によって意味が変わっていないかを判定してください。

# 誤読として数えないもの
- 言い換え・要約・語尾の変更（「〜です」→「〜すべき」等で趣旨が同じもの）
- 英語のコメントを日本語に訳したこと（訳が正しければよい）
- 1つのコメントを複数の意見に分けたこと、または複数の文を1つにまとめたこと（中身が保たれていればよい）

# 誤読として数えるもの（当てはまるものをすべて）
- polarity: 賛否・肯定否定・要望の向きが逆
- subject: 主体や対象の取り違え（誰が・何を、が入れ替わる、別のものになる）
- compare: 比較・優先の向きが逆（AよりB → BよりA など）
- added: 原文にない主張・条件・事実が足された
- dropped: 原文の主要な意見の一部が抜けた
- meaning: 上のどれでもないが、意味が変わった
- hedge: 確信の度合いが変わった（推量→断定など）。軽微
- format: extracted が空、または日本語でない

迷ったときは誤読にしないでください（明らかに意味が変わったものだけを数えます）。

# 出力
JSON の配列だけを返してください。各要素は {"id": 項目のid, "errors": [上の記号の配列。問題なければ空], "note": "誤読があるときだけ、どこがどう変わったかを日本語で1文"} です。項目の数と順番を入力と同じにしてください。
"""


def judge(batch):
    items = [{"id": r["id"], "original": r["text"], "extracted": r.get("items")} for r in batch]
    prompt = RUBRIC + "\n# 項目\n" + json.dumps(items, ensure_ascii=False, indent=1)
    p = subprocess.run(["claude", "-p", "--model", "opus", "--output-format", "text"], input=prompt,
                       capture_output=True, text=True, timeout=900)
    t = p.stdout.strip()
    t = t[t.find("["): t.rfind("]") + 1]
    out = json.loads(t)
    assert [o["id"] for o in out] == [r["id"] for r in batch], "id がずれた"
    return out


def main(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    dst = path.replace(".jsonl", ".judged.jsonl")
    done = {}
    try:
        done = {json.loads(l)["id"]: json.loads(l) for l in open(dst, encoding="utf-8")}
    except FileNotFoundError:
        pass
    todo = [r for r in rows if r["id"] not in done]
    with open(dst, "a", encoding="utf-8") as f:
        for i in range(0, len(todo), BATCH):
            b = todo[i:i + BATCH]
            for r, j in zip(b, judge(b)):
                errs = j["errors"] if r.get("items") else ["format"]
                f.write(json.dumps({**r, "errors": errs, "note": j.get("note", "")}, ensure_ascii=False) + "\n")
                f.flush()
            print(f"  {min(i + BATCH, len(todo))}/{len(todo)}", flush=True)
    print("judged ->", dst)


if __name__ == "__main__":
    main(sys.argv[1])
