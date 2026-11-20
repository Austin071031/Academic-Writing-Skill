#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成稿数值逐值溯源核验（v2.0.3 增量；守恒思想迁移自 学术语言润色/v1.0.0 guard_check）。
抽取 draft.md 中全部数值（剔除 [C01] 等编号），归一化（空白/全半角/千分位）后：
  - 在 evidence.csv 摘录中命中 → traced；
  - 仅在材料原文命中、未入证据表 → in_source_not_evidence（warning 级，溯源缺口）；
  - 两者皆无 → untraced（error 级，无源数值）。
写 /app/output/number_trace.json。
用法: python3 number_trace.py [INPUT] [WORK] [OUTPUT] [SKILL_DIR]
"""
import csv, json, os, re, sys

INPUT = sys.argv[1] if len(sys.argv) > 1 else "/input"
WORK = sys.argv[2] if len(sys.argv) > 2 else "/app/work"
OUTPUT = sys.argv[3] if len(sys.argv) > 3 else "/app/output"

def norm(s):
    s = (s or "").replace("，", ",").replace("％", "%").replace(",", "")
    return re.sub(r"\s+", "", s).lower()

draft = ""
dp = os.path.join(OUTPUT, "draft.md")
if os.path.exists(dp):
    draft = open(dp, encoding="utf-8").read()
clean = re.sub(r"[\[【]C\d+[\]】]", "", draft)

quotes = []
ep = os.path.join(OUTPUT, "evidence.csv")
if os.path.exists(ep):
    quotes = [r.get("quote", "") for r in csv.DictReader(open(ep, encoding="utf-8", newline=""))]
nq = norm(" ".join(quotes))

texts = ""
tdir = os.path.join(WORK, "text")
if os.path.isdir(tdir):
    for fn in os.listdir(tdir):
        if fn.endswith(".txt"):
            texts += open(os.path.join(tdir, fn), encoding="utf-8").read()
nt = norm(texts)

NUM = re.compile(r"\d+(?:\.\d+)?\s*(?:%|mmhg|例|周|天|年|mg|g|ml|倍|岁|人|篇|mmol)?", re.I)
traced, in_src, untraced = [], [], []
for m in NUM.finditer(clean):
    tok = m.group(0).strip()
    if not tok or tok in ("0", "1") and len(tok) == 1:
        continue
    left = clean[max(0, m.start() - 5): m.start()]
    if re.search(r"(干预|研究|试验|案例|编号|版本|第|组|阶段)\s*[-–—\d]*$", left):
        continue  # 标识符编号，非数据数值
    ntok = norm(tok)
    bare = norm(re.match(r"\d+(?:\.\d+)?", tok).group(0))
    ctx = clean[max(0, m.start() - 20): m.end() + 20].replace("\n", " ")
    NUMWORDS = {"1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six",
                "7": "seven", "8": "eight", "9": "nine", "10": "ten", "11": "eleven",
                "12": "twelve", "13": "thirteen", "14": "fourteen", "15": "fifteen",
                "16": "sixteen", "17": "seventeen", "18": "eighteen", "19": "nineteen", "20": "twenty"}
    word = NUMWORDS.get(bare)
    def hit(pool):
        return ntok in pool or bare in pool or (word and word in pool)
    if hit(nq):
        traced.append({"number": tok, "context": ctx})
    elif hit(nt):
        in_src.append({"number": tok, "context": ctx})
    else:
        untraced.append({"number": tok, "context": ctx})

report = {"traced": traced, "in_source_not_evidence": in_src, "untraced": untraced,
          "rule": "成稿数值须经 evidence.csv 摘录溯源；归一化=去空白/全半角/千分位"}
with open(os.path.join(OUTPUT, "number_trace.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
print(json.dumps({"traced": len(traced), "in_source_not_evidence": len(in_src),
                  "untraced": len(untraced)}, ensure_ascii=False))
