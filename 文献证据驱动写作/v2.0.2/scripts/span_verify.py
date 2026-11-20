#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分句级支撑范围核验（v2.0.2 增量）。
evidence.csv 可选列 support_span = 摘录中真正支撑论断的原句。三层嵌套机检：
  norm(span) ⊆ norm(quote) ⊆ 原文（页码反查）。
无 support_span 列或行为空 → 记 skipped，不报错（向后兼容）。
写 /app/output/span_report.json。
用法: python3 span_verify.py [INPUT] [WORK] [OUTPUT] [SKILL_DIR]
"""
import csv, json, os, re, sys

INPUT = sys.argv[1] if len(sys.argv) > 1 else "/input"
WORK = sys.argv[2] if len(sys.argv) > 2 else "/app/work"
OUTPUT = sys.argv[3] if len(sys.argv) > 3 else "/app/output"

def norm(s):
    return re.sub(r"\s+", "", (s or "")).lower()

texts = {}
tdir = os.path.join(WORK, "text")
if os.path.isdir(tdir):
    for fn in os.listdir(tdir):
        if fn.endswith(".txt"):
            texts[fn[:-4]] = open(os.path.join(tdir, fn), encoding="utf-8").read()

def find_span(span):
    q = norm(span)
    hits = []
    for did, t in texts.items():
        nt = norm(t)
        pos = nt.find(q)
        if pos >= 0:
            pg = None
            for m in re.finditer(r"===== \[PAGE (\d+)\] =====", t):
                if len(norm(t[: m.start()])) <= pos:
                    pg = int(m.group(1))
                else:
                    break
            hits.append({"doc": did, "page": pg})
            break
    return hits

rows = []
ep = os.path.join(OUTPUT, "evidence.csv")
if os.path.exists(ep):
    rows = list(csv.DictReader(open(ep, encoding="utf-8", newline="")))

checked, skipped, violations = 0, 0, []
for r in rows:
    eid = r.get("evidence_id")
    span = (r.get("support_span") or "").strip()
    if not span:
        skipped += 1
        continue
    checked += 1
    if len(norm(span)) < 6:
        violations.append({"evidence_id": eid, "reason": "support_span 过短（<6 字符），无法可靠核验"})
        continue
    if norm(span) not in norm(r.get("quote") or ""):
        violations.append({"evidence_id": eid, "reason": "support_span 不在 quote 摘录内（嵌套断裂）"})
        continue
    hits = find_span(span)
    if not hits:
        violations.append({"evidence_id": eid, "reason": "support_span 未在材料原文命中"})

report = {"checked": checked, "skipped": skipped, "violations": violations,
          "rule": "norm(span) ⊆ norm(quote) ⊆ 原文（页码反查）"}
with open(os.path.join(OUTPUT, "span_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
print(json.dumps({"checked": checked, "skipped": skipped, "violations": len(violations)}, ensure_ascii=False))
