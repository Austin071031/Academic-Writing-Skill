#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""revisions_apply — 把 edit_plan 中的定点修改以 DOCX 原生修订形式落地。

产出：
  revised_tracked.docx   含 w:ins/w:del 的原生修订稿（Word/WPS 可逐条接受或拒绝）
  changes.json           逐条改动台账：位置、原文、改后、依据、状态（可逐条接受/拒绝）
  accepted.docx          接受全部修订的净稿
  rejected.docx          拒绝全部修订的原稿（应与输入逐字节级内容一致）

用法：
  python3 revisions_apply.py <input.docx> <edit_plan.json> <out_dir> \
      [--edits-json <json>]  # 可选：每条 edit 的 applied 细节（由 Agent 给出）
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docxkit as dk  # noqa: E402


def apply_edits(docx, plan, detail_map, author="weekly-skill"):
    """按 plan 应用修订。detail_map: {edit_id: {type, old, new, para_hint}}。

    type: replace | delete | insert_after | note(仅核对，不改写)
    返回 changes 台账列表。
    """
    dk._build_parent_map(docx.tree().getroot())
    paras = list(docx.paragraphs())
    changes = []
    for edit in plan.get("edits", []):
        eid = edit.get("id")
        d = detail_map.get(eid, {})
        etype = d.get("type", "replace" if d.get("old") else "note")
        rec = {"edit_id": eid, "target": edit.get("target"),
               "instruction": edit.get("instruction"),
               "anchor_para": edit.get("anchored_para"),
               "anchor": edit.get("anchor"),
               "type": etype, "status": "applied",
               "basis": d.get("basis", "task instruction + anchored evidence"),
               "old": d.get("old"), "new": d.get("new")}
        if etype == "note":
            rec["status"] = "verified-no-change"
            changes.append(rec)
            continue
        old = d.get("old", "")
        new = d.get("new", "")
        if etype == "delete":
            new = ""
        # 定位段落：优先锚点段，其次全文精确查找
        para = None
        ap = edit.get("anchored_para")
        if ap is not None and ap < len(paras):
            para = paras[ap]
        if para is None or (old and old not in dk_doc_text(docx, para)):
            para = None
            for p in paras:
                if old and old in docx.para_text(p):
                    para = p
                    break
        if para is None:
            rec["status"] = "failed-anchor-not-found"
            changes.append(rec)
            continue
        if etype == "insert_after":
            anchor_text = d.get("anchor_text", "")
            idx = list(docx.body()).index(para)
            np = _new_para_like(docx, para, new)
            docx.body().insert(idx + 1, np)
            rec["status"] = "applied-insert"
            changes.append(rec)
            paras = list(docx.paragraphs())
            continue
        r = {}
        hits = 0
        if d.get("replace_all") or "统一" in edit.get("instruction", ""):
            # 全量替换：范围内所有出现处各记一条
            for p in paras:
                while old and old in docx.para_text(p):
                    rr = {}
                    if dk.tracked_replace(p, old, new, author=author,
                                          record=rr):
                        hits += 1
                    else:
                        break
        else:
            ok = dk.tracked_replace(para, old, new, author=author, record=r)
            if ok:
                hits = 1
        if not hits:
            rec["status"] = "failed-text-not-found"
            changes.append(rec)
            continue
        rec["occurrences"] = hits
        if r:
            rec.update(r)
        rec["status"] = "applied"
        changes.append(rec)
    return changes


def dk_doc_text(docx, para):
    return docx.para_text(para)


def _new_para_like(docx, ref_para, text):
    """在 ref_para 后插入同样式新段落（无修订标记的新增内容用 w:ins 包裹）。"""
    import copy
    np = copy.deepcopy(ref_para)
    # 清空 runs
    for child in list(np):
        if dk.wtag(child) == "r" or dk.wtag(child) == "ins":
            np.remove(child)
    ins = dk.make_ins(text)
    np.append(ins)
    return np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx")
    ap.add_argument("plan_json")
    ap.add_argument("out_dir")
    ap.add_argument("--edits-json", default=None,
                    help="Agent 提供的修改明细 {edit_id: {...}}")
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    plan = json.load(open(args.plan_json, encoding="utf-8"))
    detail_map = {}
    if args.edits_json and os.path.exists(args.edits_json):
        detail_map = json.load(open(args.edits_json, encoding="utf-8"))

    docx = dk.Docx(args.docx)
    changes = apply_edits(docx, plan, detail_map)
    tracked = os.path.join(args.out_dir, "revised_tracked.docx")
    docx.save(tracked)

    # 接受/拒绝两个变体
    acc = dk.Docx(tracked)
    dk._build_parent_map(acc.tree().getroot())
    dk.accept_all(acc)
    accepted = os.path.join(args.out_dir, "accepted.docx")
    acc.save(accepted)

    rej = dk.Docx(tracked)
    dk._build_parent_map(rej.tree().getroot())
    dk.reject_all(rej)
    rejected = os.path.join(args.out_dir, "rejected.docx")
    rej.save(rejected)

    changes_path = os.path.join(args.out_dir, "changes.json")
    ledger = {"case_id": plan.get("case_id"), "changes": changes,
              "tracked_document": tracked, "accepted_document": accepted,
              "rejected_document": rejected,
              "counts": {
                  "applied": sum(1 for c in changes
                                 if c["status"].startswith("applied")),
                  "verified": sum(1 for c in changes
                                  if c["status"] == "verified-no-change"),
                  "failed": sum(1 for c in changes
                                if c["status"].startswith("failed")),
              }}
    with open(changes_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=1)
    print(json.dumps({"ok": True, "changes": changes_path,
                      "tracked": tracked, "counts": ledger["counts"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
