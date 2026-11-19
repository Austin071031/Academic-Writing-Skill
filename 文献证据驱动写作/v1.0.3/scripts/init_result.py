#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""早存骨架：生成 /app/output/result.json。
- 逐字段复制 output_contract 的键结构（叶子置 null），保证契约字段一个不缺；
- 写入 case_id、status=partial、假设/不确定性/变更记录占位；
- 任何时刻中断，/app/output 里已有一份诚实的半成品。
用法: python3 init_result.py [INPUT_DIR] [OUTPUT_DIR]
"""
import json, os, sys

INPUT = sys.argv[1] if len(sys.argv) > 1 else "/input"
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else "/app/output"
os.makedirs(OUTPUT, exist_ok=True)

def contract_skeleton(v):
    if isinstance(v, dict):
        return {k: contract_skeleton(x) for k, x in v.items()}
    if isinstance(v, list):
        return [contract_skeleton(v[0])] if v else []
    return None

result_path = os.path.join(OUTPUT, "result.json")
old = None
if os.path.exists(result_path):
    try:
        with open(result_path, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        old = None

case = {}
cpath = os.path.join(INPUT, "case.json")
if os.path.exists(cpath):
    try:
        with open(cpath, encoding="utf-8") as f:
            case = json.load(f)
    except Exception:
        case = {}

oc = case.get("output_contract") or case.get("outputContract") or {}
skeleton = contract_skeleton(oc) if isinstance(oc, dict) else {}

if old is None:
    result = {}
else:
    result = old  # 保留已填写的字段，只补缺

cid = case.get("case_id") or case.get("id") or case.get("caseId")
if cid is not None:
    result["case_id"] = cid
elif "case_id" not in result:
    result["case_id"] = None

for k, v in skeleton.items():
    if k not in result:
        result[k] = v

result.setdefault("status", "partial")
result.setdefault("artifacts", {})
result.setdefault("assumptions", [])
result.setdefault("uncertainty", [])
result.setdefault("change_log", [])
result.setdefault("exceptions", [])
result.setdefault("validation", None)

with open(result_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=1)
print(json.dumps({"result": result_path, "status": result["status"],
                  "contract_fields": list(skeleton)}, ensure_ascii=False))
