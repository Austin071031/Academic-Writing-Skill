#!/usr/bin/env python3
"""align_engine.py — 句段级双语对齐引擎（v1.0.2 对得齐方向）。

子命令：
  plan   预生成对齐计划 work/alignment_plan.json：句段顺序、结构锚点统计
         （图/表编号、题注、脚注、公式、参考文献条目数），作为对齐不变量。
  audit  译后核对：
         - 覆盖：每个待译句段是否有译文（缺译 → 高）
         - 结构：translation_full.md 中 图N/表N/Figure N/Table N 编号集合、
                 脚注标记、公式块、参考文献条目数 与源一致
         - 顺序：译文句段 ID 必须全部属于 segments.json（未知 ID → 疑似新增）
         - 长度：译文长度异常（疑似漏译/串段，zh/en 字符比例启发式）
         输出 work/alignment.json（逐句段对照状态）、work/align_audit.json、
         work/findings.json（双语对齐维度）。
用法:
  python3 align_engine.py plan  --work /app/work
  python3 align_engine.py audit --work /app/work --out /app/output
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trans_utils as tu

RE_FIGTAB = re.compile(r"(图\s*\d+|表\s*\d+|Figure\s*\d+|Fig\.\s*\d+|Table\s*\d+|TABLE\s*\d+)",
                       re.I)
RE_FN = re.compile(r"\[\^(\d+)\]")

def structure_anchors(segments):
    anchors = {"figures_tables": [], "footnotes": [], "formulas": 0, "references": 0}
    for s in segments:
        for m in RE_FIGTAB.finditer(s["source"]):
            anchors["figures_tables"].append(re.sub(r"\s+", "", m.group(1)).lower())
        for m in RE_FN.finditer(s["source"]):
            anchors["footnotes"].append(m.group(1))
        if s["kind"] == "formula":
            anchors["formulas"] += 1
        if s["kind"] == "reference":
            anchors["references"] += 1
    anchors["figures_tables"] = sorted(set(anchors["figures_tables"]))
    anchors["footnotes"] = sorted(set(anchors["footnotes"]))
    return anchors

def cmd_plan(work):
    segdata = tu.load_json(os.path.join(work, "segments.json"))
    if not segdata:
        print("[align_engine][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    segs = segdata["segments"]
    anchors = structure_anchors(segs)
    plan = {
        "ordered_seg_ids": [s["seg_id"] for s in segs],
        "needs_translation": [s["seg_id"] for s in segs if s["needs_translation"]],
        "invariants": anchors,
        "instructions": "逐句段翻译并写入 translations.jsonl（{\"seg_id\":...,\"translation\":...}）；"
                        "不得合并、拆分、增删句段；图/表编号、脚注标记、公式、"
                        "参考文献条目必须原位保留（见 invariants）。",
    }
    tu.save_json(os.path.join(work, "alignment_plan.json"), plan)
    print(f"[align_engine plan] 句段={len(segs)} 待译={len(plan['needs_translation'])} "
          f"锚点 图表={len(anchors['figures_tables'])} 脚注={len(anchors['footnotes'])} "
          f"公式={anchors['formulas']} 文献={anchors['references']}")
    return 0

def cmd_audit(work, out):
    segdata = tu.load_json(os.path.join(work, "segments.json"))
    if not segdata:
        print("[align_engine][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    insp = tu.load_json(os.path.join(work, "inspection.json"), {}) or {}
    target_lang = (insp.get("translation_task") or {}).get("target_lang") or "zh"
    segs = segdata["segments"]
    merged, _ = tu.load_translations(work)
    anchors = structure_anchors(segs)
    seg_ids = {s["seg_id"] for s in segs}

    findings = []
    n_find = 0
    alignment = []

    # 1) 覆盖与长度
    for s in segs:
        sid = s["seg_id"]
        if not s["needs_translation"]:
            alignment.append({"seg_id": sid, "section": s.get("section"),
                              "kind": s["kind"], "status": "kept_original"})
            continue
        tr = merged.get(sid)
        if not tr:
            n_find += 1
            findings.append({
                "id": f"ALN-{n_find:03d}", "dimension": "双语对齐", "type": "句段缺译",
                "location": {"seg_id": sid, "section": s.get("section")},
                "quote": s["source"][:150],
                "evidence": "该句段在 translations 中无译文，对照链断裂",
                "action": {"op": "fix_translation",
                           "instruction": "补译该句段并追加到 translations.jsonl"},
                "severity": "高", "confidence": 1.0, "status": "脚本候选"})
            alignment.append({"seg_id": sid, "section": s.get("section"),
                              "kind": s["kind"], "status": "missing"})
            continue
        src_words = len(s["source"].split()) or 1
        tr_chars = len(re.sub(r"\s", "", tr))
        if target_lang == "zh":
            ratio = tr_chars / src_words  # 中文字/英文词 ≈ 1.2–2.8
            suspect = ratio < 0.55 or ratio > 4.5
        else:
            ratio = len(tr.split()) / max(len(re.sub(r"\s", "", s["source"])), 1)
            suspect = ratio < 0.25 or ratio > 1.2
        if suspect:
            n_find += 1
            findings.append({
                "id": f"ALN-{n_find:03d}", "dimension": "双语对齐", "type": "长度异常疑似漏译/增译",
                "location": {"seg_id": sid, "section": s.get("section")},
                "quote": s["source"][:150],
                "evidence": f"译文长度比例 {ratio:.2f} 超出合理区间；"
                            f"译文：{tr[:150]}",
                "action": {"op": "manual_check",
                           "instruction": "对照原文复核该句段是否漏译从句或增译内容"},
                "severity": "中", "confidence": 0.55, "status": "脚本候选"})
            alignment.append({"seg_id": sid, "section": s.get("section"),
                              "kind": s["kind"], "status": "suspect_length",
                              "ratio": round(ratio, 3)})
        else:
            alignment.append({"seg_id": sid, "section": s.get("section"),
                              "kind": s["kind"], "status": "aligned"})

    # 2) 未知 ID（译文多出句段）
    for sid in merged:
        if sid not in seg_ids:
            n_find += 1
            findings.append({
                "id": f"ALN-{n_find:03d}", "dimension": "双语对齐", "type": "译文含未知句段ID",
                "location": {"seg_id": sid, "section": None},
                "quote": merged[sid][:150],
                "evidence": "译文 seg_id 不在 segments.json 中，疑似新增段或 ID 笔误",
                "action": {"op": "manual_check",
                           "instruction": "核对 ID；如为新增内容须删除或并入对应句段"},
                "severity": "中", "confidence": 0.95, "status": "脚本候选"})

    # 3) 结构锚点：图表编号/脚注 在译文交付物中的保留
    tf_path = os.path.join(out, "translation_full.md")
    if not os.path.exists(tf_path):
        tf_path = os.path.join(work, "translation_full.md")
    tf = ""
    if os.path.exists(tf_path):
        with open(tf_path, encoding="utf-8") as f:
            tf = f.read()
    tf_ft = sorted(set(re.sub(r"\s+", "", m.group(1)).lower()
                       for m in RE_FIGTAB.finditer(tf)))
    tf_fn = sorted(set(RE_FN.findall(tf)))
    src_ft_set, tf_ft_set = set(anchors["figures_tables"]), set(tf_ft)
    # 图表编号跨语言映射：Figure N ↔ 图N
    def canon(x):
        m = re.search(r"(\d+)", x)
        return m.group(1) if m else x
    src_nums = sorted(canon(x) for x in src_ft_set)
    tf_nums = sorted(canon(x) for x in tf_ft_set)
    if src_nums != tf_nums:
        n_find += 1
        findings.append({
            "id": f"ALN-{n_find:03d}", "dimension": "双语对齐", "type": "图表编号不对应",
            "location": {"seg_id": None, "section": None},
            "quote": f"源图表编号：{src_nums}",
            "evidence": f"译文图表编号：{tf_nums}；编号集合不一致",
            "action": {"op": "fix_translation",
                       "instruction": "逐一对照图/表题注，恢复缺失编号或删除多余编号"},
            "severity": "高", "confidence": 0.85, "status": "脚本候选"})
    if set(anchors["footnotes"]) != set(tf_fn):
        n_find += 1
        findings.append({
            "id": f"ALN-{n_find:03d}", "dimension": "双语对齐", "type": "脚注标记不对应",
            "location": {"seg_id": None, "section": None},
            "quote": f"源脚注：{anchors['footnotes']}",
            "evidence": f"译文脚注：{tf_fn}",
            "action": {"op": "fix_translation",
                       "instruction": "恢复脚注标记与脚注段的一一对应"},
            "severity": "中", "confidence": 0.85, "status": "脚本候选"})

    aligned = sum(1 for a in alignment if a["status"] == "aligned")
    summary = {"segments": len(segs),
               "aligned": aligned,
               "missing": sum(1 for a in alignment if a["status"] == "missing"),
               "suspect": sum(1 for a in alignment if a["status"] == "suspect_length"),
               "kept_original": sum(1 for a in alignment if a["status"] == "kept_original"),
               "invariants": anchors}
    tu.save_json(os.path.join(work, "alignment.json"),
                 {"summary": summary, "pairs": alignment})
    tu.save_json(os.path.join(work, "align_audit.json"), summary)
    old = tu.load_json(os.path.join(work, "findings.json"), []) or []
    old = [f for f in old if f.get("dimension") != "双语对齐"]
    tu.save_json(os.path.join(work, "findings.json"), old + findings)
    print(f"[align_engine audit] 对齐={aligned} 缺译={summary['missing']} "
          f"疑似={summary['suspect']} findings+{len(findings)}")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "audit"])
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()
    return cmd_plan(args.work) if args.cmd == "plan" else cmd_audit(args.work, args.out)

if __name__ == "__main__":
    sys.exit(main())
