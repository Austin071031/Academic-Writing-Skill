#!/usr/bin/env python3
"""revision_engine.py — 把 edit_plan.json 真实应用到基线稿件，产出修订稿与修改报告。

设计要点（对应评分"改得准""对得上"）：
- 每处编辑以【原文锚点 quote】定位，锚点必须真实存在于基线当前文本；
- 解析顺序：段内精确 → 全局精确（须唯一）→ 空白归一化 → difflib 模糊（≥0.75，记录比值）；
- 锚点解析失败的编辑不静默跳过：状态 failed_anchor 写入报告，交由 Agent 处置；
- 输出修订稿 = 结构模型重排（标题 + 段落），插入的新段落获得稳定新 ID（P005a）；
- new_text 中允许占位标记【待补：...】，如实记录，不冒充已完成。

edit_plan.json schema:
[{"op_id":"E1","comment_ref":"R1-C1-s1","action":"replace|insert_after|insert_before|
   delete|replace_paragraph|append_section",
  "para_id":"P005"(可选),"section":"结果"(可选),"anchor_quote":"基线原文片段",
  "new_text":"替换或插入文本","rationale":"修改理由(对应意见)"}]

输出: /app/output/revised_manuscript.md ; work/edit_report.json
用法: python3 revision_engine.py --work /app/work --out /app/output [--plan work/edit_plan.json]
"""
import argparse, difflib, json, os, re, sys

PLACEHOLDER = re.compile(r"【待补[:：].*?】|TODO|XXX_PLACEHOLDER")

def norm_ws(s):
    return re.sub(r"\s+", " ", s).strip()

class Doc:
    """可变稿件模型：sections 顺序 + paragraphs（含新增段落）。"""
    def __init__(self, model):
        self.sections = [dict(s) for s in model["sections"]]
        self.paras = []          # [{id, text, section_id}]
        self.by_id = {}
        for p in model["paragraphs"]:
            q = {"id": p["id"], "text": p["text"], "section_id": p["section_id"],
                 "origin": "baseline"}
            self.paras.append(q)
            self.by_id[q["id"]] = q
        self._new_counter = {}

    def new_pid(self, base_id):
        n = self._new_counter.get(base_id, 0) + 1
        self._new_counter[base_id] = n
        suffix = ""
        x = n
        while x:
            x, r = divmod(x - 1, 26)
            suffix = chr(97 + r) + suffix
        return f"{base_id}{suffix}"

    def find_para_index(self, pid):
        for i, q in enumerate(self.paras):
            if q["id"] == pid:
                return i
        return None

    def section_para_ids(self, section_id):
        return [q["id"] for q in self.paras if q["section_id"] == section_id]

def resolve_anchor(doc, quote, para_id=None, section=None):
    """返回 (para, method, ratio) 或 (None, reason, 0)。"""
    if not quote or not quote.strip():
        return None, "锚点为空", 0
    q = quote.strip()
    # 1. 指定段落内精确
    if para_id and para_id in doc.by_id and q in doc.by_id[para_id]["text"]:
        return doc.by_id[para_id], "exact-in-para", 1.0
    # 2. 全局精确（计数）
    hits = [p for p in doc.paras if q in p["text"]]
    if len(hits) == 1:
        return hits[0], "exact-global", 1.0
    if len(hits) > 1:
        if section:
            sec_hits = [p for p in hits
                        if any(s["id"] == p["section_id"] and section in s["heading"]
                               for s in doc.sections)]
            if len(sec_hits) == 1:
                return sec_hits[0], "exact-global-section", 1.0
        return None, f"锚点不唯一（{len(hits)} 处出现），需加长 quote 或指定 para_id", 0
    # 3. 空白归一化
    nq = norm_ws(q)
    nhits = [p for p in doc.paras if nq in norm_ws(p["text"])]
    if len(nhits) == 1:
        return nhits[0], "normalized", 1.0
    # 4. 模糊匹配（句级 → 段级）
    best, br = None, 0.0
    for p in doc.paras:
        for sent in re.split(r"(?<=[。！？!?；;])\s*", p["text"]):
            r = difflib.SequenceMatcher(None, nq, norm_ws(sent)).ratio()
            if r > br:
                best, br = p, r
        r = difflib.SequenceMatcher(None, nq, norm_ws(p["text"])[:len(nq) * 2]).ratio()
        if r > br:
            best, br = p, r
    if best is not None and br >= 0.75:
        return best, "fuzzy", round(br, 3)
    return None, f"锚点在基线中未找到（最佳相似度 {br:.2f}）", round(br, 3)

def apply_op(doc, op):
    para, method, ratio = None, None, 0
    action = op.get("action", "replace")
    if action == "append_section":
        target_sec = None
        for s in doc.sections:
            if op.get("section") and op["section"] in s["heading"]:
                target_sec = s
        if target_sec is None and doc.sections:
            target_sec = doc.sections[-1]  # 缺省文末
        if target_sec is None:
            return {"status": "failed", "reason": "无任何章节可追加"}
        ids = doc.section_para_ids(target_sec["id"])
        anchor_id = ids[-1] if ids else None
        newp = {"id": doc.new_pid(anchor_id or target_sec["id"]), "text": op["new_text"],
                "section_id": target_sec["id"], "origin": op["op_id"]}
        if anchor_id:
            doc.paras.insert(doc.find_para_index(anchor_id) + 1, newp)
        else:
            doc.paras.append(newp)
        doc.by_id[newp["id"]] = newp
        return {"status": "applied", "method": "append_section", "para_id": newp["id"],
                "section": target_sec["heading"], "old_text": None}

    para, method, ratio = resolve_anchor(doc, op.get("anchor_quote", ""),
                                         op.get("para_id"), op.get("section"))
    if para is None:
        return {"status": "failed_anchor", "reason": method, "best_ratio": ratio}
    anchor = op.get("anchor_quote", "").strip()
    new_text = op.get("new_text", "")
    old = para["text"]

    if action == "replace":
        if anchor in para["text"]:
            para["text"] = para["text"].replace(anchor, new_text, 1)
        else:  # normalized/fuzzy: 整段替换并以 change_log 说明
            para["text"] = new_text
            method += "+whole-para-fallback"
    elif action == "replace_paragraph":
        para["text"] = new_text
    elif action == "delete":
        if anchor in para["text"]:
            para["text"] = norm_ws(para["text"].replace(anchor, "", 1))
        else:
            return {"status": "failed", "reason": "delete 锚点非精确命中，拒绝模糊删除"}
    elif action in ("insert_after", "insert_before"):
        newp = {"id": doc.new_pid(para["id"]), "text": new_text,
                "section_id": para["section_id"], "origin": op["op_id"]}
        idx = doc.find_para_index(para["id"])
        doc.paras.insert(idx + (1 if action == "insert_after" else 0), newp)
        doc.by_id[newp["id"]] = newp
        return {"status": "applied", "method": method, "ratio": ratio,
                "para_id": newp["id"], "anchor_para": para["id"], "old_text": None}
    else:
        return {"status": "failed", "reason": f"未知 action: {action}"}
    return {"status": "applied", "method": method, "ratio": ratio,
            "para_id": para["id"], "old_text": old[:400]}

def reassemble(doc):
    lines = []
    for s in doc.sections:
        paras = [q for q in doc.paras if q["section_id"] == s["id"]]
        if s["heading"] and not s["heading"].startswith("(文首"):
            lines.append("#" * min(max(s["level"], 1), 6) + " " + s["heading"])
            lines.append("")
        for q in paras:
            if q["text"].strip():
                lines.append(q["text"])
                lines.append("")
    return "\n".join(lines).strip() + "\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--plan", default=None)
    args = ap.parse_args()

    structure_p = os.path.join(args.work, "structure.json")
    plan_p = args.plan or os.path.join(args.work, "edit_plan.json")
    for p, name in ((structure_p, "structure.json"), (plan_p, "edit_plan.json")):
        if not os.path.exists(p):
            print(f"[revision_engine][FATAL] 缺少 {name}: {p}", file=sys.stderr)
            return 1
    with open(structure_p, encoding="utf-8") as f:
        model = json.load(f)
    with open(plan_p, encoding="utf-8") as f:
        plan = json.load(f)
    if not isinstance(plan, list) or not plan:
        print("[revision_engine][FATAL] edit_plan.json 为空或非列表", file=sys.stderr)
        return 1

    doc = Doc(model)
    report, applied, failed = [], 0, 0
    for op in plan:
        for req in ("op_id", "action"):
            if req not in op:
                print(f"[revision_engine][FATAL] 编辑操作缺字段 {req}: {op}", file=sys.stderr)
                return 1
        r = apply_op(doc, op)
        r.update({"op_id": op["op_id"], "comment_ref": op.get("comment_ref"),
                  "action": op["action"], "anchor_quote": (op.get("anchor_quote") or "")[:120],
                  "new_text_head": (op.get("new_text") or "")[:120],
                  "has_placeholder": bool(PLACEHOLDER.search(op.get("new_text") or "")),
                  "rationale": op.get("rationale")})
        if r["status"] == "applied":
            applied += 1
        else:
            failed += 1
            print(f"[revision_engine][WARN] {op['op_id']} {r['status']}: "
                  f"{r.get('reason', '')}", file=sys.stderr)
        report.append(r)

    revised = reassemble(doc)
    # 标注修订稿行号
    line_map = {}
    for i, q in enumerate(doc.paras):
        pass
    rev_lines = revised.splitlines()
    for r in report:
        if r["status"] == "applied" and r.get("new_text_head"):
            head = r["new_text_head"][:30]
            for ln, txt in enumerate(rev_lines, 1):
                if head and head in txt:
                    r["revised_line"] = ln
                    break

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "revised_manuscript.md"), "w", encoding="utf-8") as f:
        f.write(revised)
    summary = {"n_ops": len(plan), "applied": applied, "failed": failed,
               "placeholders": sum(1 for r in report if r["has_placeholder"]),
               "fuzzy_anchors": [r["op_id"] for r in report
                                 if str(r.get("method", "")).startswith("fuzzy")],
               "baseline_chars": sum(p["n_char"] for p in model["paragraphs"]),
               "revised_chars": len(revised)}
    with open(os.path.join(args.work, "edit_report.json"), "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "ops": report}, f, ensure_ascii=False, indent=1)
    print(f"[revision_engine] 应用={applied} 失败={failed} 占位={summary['placeholders']} "
          f"→ revised_manuscript.md ({len(revised)} chars)")
    return 0 if failed == 0 else 2  # 2 = 有失败锚点，需 Agent 处置

if __name__ == "__main__":
    sys.exit(main())
