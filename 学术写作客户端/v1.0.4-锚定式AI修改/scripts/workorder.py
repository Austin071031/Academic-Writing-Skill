#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""workorder — 把修改指令锚定到稿件具体位置。

输入：case 目录（case.json / task.md / organizer-edit-workorder.json）+ 稿件清单。
输出：edit_plan.json —— 每条指令附：文档内定位（段落号/章节/锚句）、
      是否命中、命中方式（exact/heading/keyword/none）、需人工确认标记。

原则：改得准——先把指令落到具体句子，再动笔；找不到锚点不许猜。
"""
import json
import os
import re
import sys


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def read_text(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def norm(s):
    return re.sub(r"\s+", "", s or "")


def anchor_edit(doc_paras, instruction, target_hint):
    """在段落清单中定位编辑目标。

    doc_paras: [{index, style, text}]
    返回 (para_index, anchor_sentence, method) 或 (None, None, "none")。
    """
    hint = norm(target_hint)
    # 1) 按标题样式匹配 target 提示（如 "1 引言"、"摘要"）
    for p in doc_paras:
        if not p["text"].strip():
            continue
        pt = norm(p["text"])
        if hint and (pt.startswith(hint) or hint in pt[:40]):
            return p["index"], p["text"][:80], "heading"
    # 2) 从指令中抽取引号/书名号包裹的原文片段做精确锚定
    quoted = re.findall(r"[“\"『]([^”\"』]{2,60})[”\"』]", instruction)
    for q in quoted:
        for p in doc_paras:
            if q in p["text"]:
                return p["index"], q, "exact"
    # 3) 抽取指令中的关键名词串（>=4 字）做包含匹配
    keys = re.findall(r"[一-鿿][一-鿿A-Za-z0-9]{3,}", instruction)
    best = None
    for p in doc_paras:
        hit = sum(1 for k in keys if k in p["text"])
        if keys and hit == len(keys):
            return p["index"], p["text"][:80], "keyword"
        if hit and (best is None or hit > best[2]):
            best = (p["index"], p["text"][:80], hit)
    if best:
        return best[0], best[1], "keyword-weak"
    return None, None, "none"


def build_plan(input_dir, doc_paras):
    case = load_json(os.path.join(input_dir, "case.json"), {}) or {}
    wo = load_json(os.path.join(input_dir, "organizer-edit-workorder.json"),
                   None)
    edits = []
    if wo and isinstance(wo, dict):
        edits = wo.get("edits") or wo.get("workorder") or []
    if not edits and isinstance(wo, list):
        edits = wo
    plan = {
        "case_id": case.get("case_id") or case.get("id") or "unknown",
        "scope": (wo or {}).get("scope") if isinstance(wo, dict) else None,
        "output_contract": case.get("output_contract", {}),
        "edits": [],
    }
    for e in edits:
        if not isinstance(e, dict):
            continue
        idx, anchor, method = anchor_edit(
            doc_paras, e.get("instruction", ""), e.get("target", ""))
        plan["edits"].append({
            "id": e.get("id") or "E%d" % (len(plan["edits"]) + 1),
            "target": e.get("target", ""),
            "instruction": e.get("instruction", ""),
            "anchored_para": idx,
            "anchor": anchor,
            "anchor_method": method,
            "needs_human_confirmation": method in ("none", "keyword-weak"),
        })
    return plan


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    input_dir, paras_json = sys.argv[1], sys.argv[2]
    doc_paras = json.load(open(paras_json, encoding="utf-8"))
    plan = build_plan(input_dir, doc_paras)
    out = sys.argv[3] if len(sys.argv) > 3 else None
    s = json.dumps(plan, ensure_ascii=False, indent=1)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(s)
    else:
        print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
