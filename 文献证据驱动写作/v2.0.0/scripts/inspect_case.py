#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""阶段0预检：解析 /input/case.json 与 task.md，生成 /app/work/brief.json。
只读取事实，不做任何假设性补全；解析失败如实记入 issues。
用法: python3 inspect_case.py [INPUT_DIR] [WORK_DIR]
"""
import json, os, sys

INPUT = sys.argv[1] if len(sys.argv) > 1 else "/input"
WORK = sys.argv[2] if len(sys.argv) > 2 else "/app/work"
os.makedirs(WORK, exist_ok=True)

def read_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, "file not found"
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)

case, err = read_json(os.path.join(INPUT, "case.json"))
issues = []
brief = {
    "input_dir": INPUT,
    "case_id": None,
    "case_fields": [],
    "output_contract": {},
    "contract_keys": [],
    "contract_nested": False,
    "materials_hint": [],
    "input_files": [],
    "task_md_excerpt": None,
    "issues": issues,
}

if case is None:
    issues.append("case.json 解析失败: %s（将尝试从任务文本推断，所有推断须写入 assumptions）" % err)
else:
    brief["case_fields"] = sorted(case.keys())
    cid = case.get("case_id") or case.get("id") or case.get("caseId")
    brief["case_id"] = cid
    if not cid:
        issues.append("case.json 中未找到 case_id/id 字段，须在 result.json 中回填真实案例标识")
    oc = case.get("output_contract") or case.get("outputContract")
    if isinstance(oc, dict):
        brief["output_contract"] = oc
        brief["contract_keys"] = list(oc.keys())
        brief["contract_nested"] = any(isinstance(v, dict) for v in oc.values())
    elif oc is not None:
        issues.append("output_contract 不是对象（类型 %s），须按原样结构回填 result.json" % type(oc).__name__)
    else:
        issues.append("case.json 无 output_contract 字段；仍须交付三段产物并在 result.json 说明")
    # 材料清单可能在 case 内声明
    for key in ("materials", "material", "files", "documents", "references", "refs", "papers", "sources"):
        v = case.get(key)
        if isinstance(v, list):
            for m in v:
                if isinstance(m, str):
                    brief["materials_hint"].append(m)
                elif isinstance(m, dict):
                    brief["materials_hint"].append(m.get("path") or m.get("file") or m.get("title")
                                                   or json.dumps(m, ensure_ascii=False)[:120])

allfiles = []
for root, _dirs, fs in os.walk(INPUT):
    for fn in sorted(fs):
        p = os.path.join(root, fn)
        try:
            allfiles.append({"path": os.path.relpath(p, INPUT), "bytes": os.path.getsize(p)})
        except OSError:
            allfiles.append({"path": os.path.relpath(p, INPUT), "bytes": None})
brief["input_files"] = allfiles

tm = os.path.join(INPUT, "task.md")
if os.path.exists(tm):
    with open(tm, encoding="utf-8", errors="replace") as f:
        brief["task_md_excerpt"] = f.read()[:6000]
else:
    issues.append("task.md 不存在；任务要求须完全依据 case.json")

with open(os.path.join(WORK, "brief.json"), "w", encoding="utf-8") as f:
    json.dump(brief, f, ensure_ascii=False, indent=1)

print(json.dumps({
    "case_id": brief["case_id"],
    "contract_keys": brief["contract_keys"],
    "input_files": len(allfiles),
    "issues": issues,
}, ensure_ascii=False))
