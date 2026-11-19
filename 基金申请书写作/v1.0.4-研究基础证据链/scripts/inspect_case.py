#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inspect_case.py --work W [--input-dir /input]

解析 case.json / task.md / organizer-workorder.json → work/inspection.json：
case_id、output_contract_fields[]、required_elements[]、deliverable_hints、
materials[{path,type,size}]、workorder_present、issues[]。
解析对 dict/list/嵌套宽容，任何失败记 work/exceptions.json 后继续。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "inspect_case"

# 常用扩展名 → 类型
_EXT_TYPE = {".md": "markdown", ".txt": "text", ".tex": "latex",
             ".docx": "docx", ".pdf": "pdf", ".json": "json",
             ".csv": "csv", ".tsv": "tsv", ".xlsx": "xlsx"}


def flatten_dicts(obj):
    """把嵌套 dict/list 中的所有字符串值收集为一个长文本（宽容解析）。"""
    parts = []

    def walk(o, depth=0):
        if depth > 8:
            return
        if isinstance(o, str):
            parts.append(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                walk(v, depth + 1)

    walk(obj)
    return "\n".join(parts)


def find_contract_fields(case):
    """宽容地从 case.json 找 output_contract 字段名（dict 键或 list 项）。"""
    candidates = []

    def walk(o, depth=0):
        if depth > 6:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "output_contract":
                    candidates.append(v)
                walk(v, depth + 1)
        elif isinstance(o, list):
            for v in o:
                walk(v, depth + 1)

    walk(case)
    for contract in candidates:
        fields = []
        if isinstance(contract, dict):
            fields = list(contract.keys())
        elif isinstance(contract, list):
            for item in contract:
                if isinstance(item, str):
                    fields.append(item)
                elif isinstance(item, dict):
                    for k in ("field", "name", "key"):
                        if isinstance(item.get(k), str):
                            fields.append(item[k])
                            break
        if fields:
            return fields
    return []


def find_case_id(case):
    if isinstance(case, dict):
        if case.get("case_id"):
            return case["case_id"]
        for item in case.values():
            cid = find_case_id(item)
            if cid:
                return cid
    elif isinstance(case, list):
        for item in case:
            cid = find_case_id(item)
            if cid:
                return cid
    return "unknown"


def find_workorder_elements(workorder):
    """workorder.required_elements 若存在且为字符串列表则采用。"""
    if not isinstance(workorder, dict):
        return []
    for k, v in workorder.items():
        if k == "required_elements" and isinstance(v, list):
            els = [x for x in v if isinstance(x, str) and x.strip()]
            if els:
                return els
    return []


def detect_elements(text):
    """从任务文本中识别七要素名出现情况。"""
    return [e for e in gu.DEFAULT_ELEMENTS if e in text]


def detect_deliverable_hints(text):
    hints = {}
    word_counts = re.findall(r"(?:不少于|至少|约|≤|不超过)?\s*(\d{2,5})\s*字", text)
    if word_counts:
        hints["word_counts"] = sorted({int(w) for w in word_counts})
    audiences = [w for w in ("评审专家", "评审人", "申请人", "同行", "导师", "委员会")
                 if w in text]
    if audiences:
        hints["audience"] = audiences
    langs = [w for w in ("中文", "英文", "双语") if re.search(w + r"(写作|撰写|书写)?", text)]
    if langs:
        hints["language"] = sorted(set(langs))
    sections = set()
    for line in text.splitlines():
        if re.search(r"撰写|完成|提交|覆盖|章节", line):
            for e in gu.DEFAULT_ELEMENTS:
                if e in line:
                    sections.add(e)
    if sections:
        hints["sections"] = sorted(sections, key=gu.DEFAULT_ELEMENTS.index)
    fmts = [w for w in ("Markdown", "docx", "pdf", "Word") if re.search(w, text, re.I)]
    if fmts:
        hints["format"] = sorted(set(fmts))
    return hints


def list_materials(input_dir, work):
    materials = []
    for full, rel in gu.iter_input_files(input_dir):
        ext = os.path.splitext(rel)[1].lower()
        try:
            size = os.path.getsize(full)
        except Exception as e:
            size = -1
            gu.record_exception(work, STAGE, rel, e, "size=-1 继续")
        materials.append({"path": rel, "type": _EXT_TYPE.get(ext, "unknown"),
                          "size": size})
    return materials


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--input-dir", default=None)
    args = ap.parse_args()
    work, input_dir = args.work, gu.env_input_dir(args.input_dir)
    gu.ensure_dir(work)
    issues = []

    case = gu.read_json(os.path.join(input_dir, "case.json"), None)
    if case is None:
        issues.append("case.json 缺失或无法解析")
        gu.record_exception(work, STAGE, "case.json", "missing/invalid",
                            "case_id=unknown 继续")
    task_text = ""
    try:
        with open(os.path.join(input_dir, "task.md"), "r", encoding="utf-8",
                  errors="replace") as f:
            task_text = f.read()
    except Exception as e:
        issues.append("task.md 缺失或无法读取")
        gu.record_exception(work, STAGE, "task.md", e, "task_text=空 继续")

    workorder_path = os.path.join(input_dir, "organizer-workorder.json")
    workorder = gu.read_json(workorder_path, None) if os.path.exists(workorder_path) else None
    workorder_present = workorder is not None

    corpus = flatten_dicts(case) + "\n" + task_text + "\n" + flatten_dicts(workorder)

    required = find_workorder_elements(workorder) or detect_elements(corpus)
    if not required:
        required = list(gu.DEFAULT_ELEMENTS)
        issues.append("未从任务文本识别到要素名，缺省采用全部七要素")

    inspection = {
        "case_id": find_case_id(case),
        "output_contract_fields": find_contract_fields(case),
        "required_elements": required,
        "deliverable_hints": detect_deliverable_hints(corpus),
        "materials": list_materials(input_dir, work),
        "workorder_present": workorder_present,
        "workorder_constraints": (workorder.get("constraints")
                                  if isinstance(workorder, dict) else []) or [],
        "issues": issues,
    }
    gu.write_json(os.path.join(work, "inspection.json"), inspection)
    print(f"[inspect_case] elements={len(required)} "
          f"materials={len(inspection['materials'])} issues={len(issues)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[inspect_case] ERROR: {e}")
        raise SystemExit(1)
