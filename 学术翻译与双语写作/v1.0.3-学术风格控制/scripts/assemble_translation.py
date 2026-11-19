#!/usr/bin/env python3
"""assemble_translation.py — 由 segments.json + Agent 译文（translations*.jsonl）
组装交付物，并生成覆盖率统计、缺译清单、溯源 evidence_map 与修订 change_log。

产物（写入 --out，缺省 /app/output）：
- translation_full.md   纯译文（结构/标题层级/图表题注/公式/参考文献原位保留）
- bilingual.md          双语对照（逐段：原文段落后紧跟译文段落，带段 ID）
- work/stats.json       覆盖率统计
- work/evidence_map.json 逐句段溯源（seg_id → 原文/译文对照）
- work/change_log.json  与上一次组装的译文差异（自动 diff，幂等追加）
- work/uncertainty.json 缺译与异常句段

缺译句段：纯译文中保留原文并加 **【缺译:seg_id】** 标记；如实计入 uncertainty，
不得静默跳过。用法: python3 assemble_translation.py --work /app/work --out /app/output
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trans_utils as tu

def join_sentences(parts, target_lang):
    if target_lang == "en":
        return " ".join(p.strip() for p in parts if p.strip())
    # 中文：句间不留空格；译文本身已含句末标点
    return "".join(p.strip() for p in parts if p.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    segdata = tu.load_json(os.path.join(args.work, "segments.json"))
    if not segdata:
        print("[assemble][FATAL] 缺少 work/segments.json", file=sys.stderr)
        return 1
    insp = tu.load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    target_lang = (insp.get("translation_task") or {}).get("target_lang") or "zh"
    segments = segdata["segments"]
    merged, sources = tu.load_translations(args.work)

    # 变更追踪：与上次合并快照 diff
    prev = tu.load_json(os.path.join(args.work, "translations_snapshot.json"), {}) or {}
    change_log = tu.load_json(os.path.join(args.work, "change_log.json"), []) or []
    for sid, tr in merged.items():
        if sid in prev and prev[sid] != tr:
            change_log.append({
                "op": "revise_translation", "location": sid,
                "before": prev[sid][:120], "after": tr[:120],
                "reason": "译文修订（机检发现/Agent 复核）"})
    tu.save_json(os.path.join(args.work, "translations_snapshot.json"), merged)

    missing, unknown = [], []
    seg_ids = {s["seg_id"] for s in segments}
    for sid in merged:
        if sid not in seg_ids:
            unknown.append(sid)

    # ---- 纯译文 ----
    full_lines = []
    cur_para, para_parts = None, []

    def flush_para():
        nonlocal para_parts
        if para_parts:
            full_lines.append(join_sentences(para_parts, target_lang))
            full_lines.append("")
        para_parts = []

    for seg in segments:
        sid, kind = seg["seg_id"], seg["kind"]
        tr = merged.get(sid)
        if seg["needs_translation"] and not tr:
            missing.append({"seg_id": sid, "section": seg.get("section"),
                            "source_head": seg["source"][:80]})
        if kind == "heading":
            flush_para()
            lvl = min(max(seg.get("level") or 1, 1), 6)
            text = tr or f"**【缺译:{sid}】** {seg['source']}"
            full_lines.append("#" * lvl + " " + text)
            full_lines.append("")
            continue
        if kind in ("reference", "formula"):
            flush_para()
            full_lines.append(seg["source"])  # 原样保留
            full_lines.append("")
            continue
        if kind in ("caption", "footnote", "list"):
            flush_para()
            full_lines.append(tr or f"**【缺译:{sid}】** {seg['source']}")
            full_lines.append("")
            continue
        # body 句：按段落聚合
        if cur_para != seg["para_id"]:
            flush_para()
            cur_para = seg["para_id"]
        para_parts.append(tr if tr else f"**【缺译:{sid}】** {seg['source']}")
    flush_para()

    with open(os.path.join(args.out, "translation_full.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(full_lines).rstrip() + "\n")

    # ---- 双语对照 ----
    bi = ["# 双语对照稿",
          "",
          "> 说明：每个原文段落后紧跟对应译文段落；段首 〔PID〕 为结构模型稳定 ID，",
          "> 与 segments.json / 机检报告一一对应，可逐段定位修改而不破坏结构。",
          ""]
    cur_sec = None
    para_buf = {}

    def para_text(pid):
        segs = [s for s in segments if s["para_id"] == pid and s["kind"] == "body"]
        src = " ".join(s["source"] for s in segs)
        trs = [merged.get(s["seg_id"]) for s in segs]
        if any(t is None for t in trs):
            tr = None
        else:
            tr = join_sentences(trs, target_lang)
        return src, tr

    for seg in segments:
        if seg["section_id"] != cur_sec:
            cur_sec = seg["section_id"]
            sec_head = seg.get("section") or ""
            hseg = next((s for s in segments
                         if s["seg_id"] == cur_sec + "-h"), None)
            htr = merged.get(cur_sec + "-h") if hseg else None
            bi.append(f"\n## 〔{cur_sec}〕 {sec_head}")
            if htr:
                bi.append(f"## 〔{cur_sec}·译〕 {htr}")
        pid = seg["para_id"] or seg["seg_id"]
        if pid in para_buf:
            continue
        para_buf[pid] = True
        if seg["kind"] == "body":
            src, tr = para_text(pid)
            bi.append(f"\n〔{pid}·原文〕 {src}")
            if tr:
                bi.append(f"\n〔{pid}·译文〕 {tr}")
            else:
                bi.append(f"\n〔{pid}·译文〕 **【缺译】**")
        elif seg["kind"] in ("reference", "formula"):
            bi.append(f"\n〔{pid}·{seg['kind']}·原样保留〕 {seg['source']}")
        else:
            tr = merged.get(seg["seg_id"])
            bi.append(f"\n〔{pid}·{seg['kind']}·原文〕 {seg['source']}")
            bi.append(f"\n〔{pid}·{seg['kind']}·译文〕 {tr or '**【缺译】**'}")
    with open(os.path.join(args.out, "bilingual.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(bi).rstrip() + "\n")

    # ---- 统计 / 溯源 / 不确定性 ----
    needs = [s for s in segments if s["needs_translation"]]
    done = [s for s in needs if s["seg_id"] in merged]
    stats = tu.load_json(os.path.join(args.work, "stats.json"), {}) or {}
    stats.update({
        "segments_total": len(segments),
        "segments_need_translation": len(needs),
        "segments_translated": len(done),
        "segments_missing": len(missing),
        "coverage": round(len(done) / max(len(needs), 1), 4),
        "protected_spans_total": sum(len(s["protected"]) for s in segments),
        "translation_files": sources,
        "target_lang": target_lang,
    })
    tu.save_json(os.path.join(args.work, "stats.json"), stats)
    tu.save_json(os.path.join(args.work, "change_log.json"), change_log)

    evidence = [{
        "claim_id": s["seg_id"],
        "location": {"seg_id": s["seg_id"], "section": s.get("section"),
                     "kind": s["kind"]},
        "source": s["source"][:200],
        "target": merged.get(s["seg_id"], "")[:200] if s["needs_translation"]
                  else "(原样保留，不译)",
        "support": "segment_translation",
        "verification": "translated" if s["seg_id"] in merged else
                        ("not_required" if not s["needs_translation"] else "missing"),
    } for s in segments]
    tu.save_json(os.path.join(args.work, "evidence_map.json"), evidence)

    uncertainty = tu.load_json(os.path.join(args.work, "uncertainty.json"), []) or []
    uncertainty = [u for u in uncertainty if u.get("kind") != "missing_translation"]
    for m_ in missing:
        uncertainty.append({"kind": "missing_translation", "seg_id": m_["seg_id"],
                            "section": m_["section"],
                            "note": "该句段未提供译文，交付物中以【缺译】标记并保留原文"})
    for sid in unknown:
        uncertainty.append({"kind": "unknown_seg_id", "seg_id": sid,
                            "note": "译文中出现 segments.json 之外的 ID，已忽略（疑似新增/笔误）"})
    tu.save_json(os.path.join(args.work, "uncertainty.json"), uncertainty)

    print(f"[assemble] 待译={len(needs)} 已译={len(done)} 缺译={len(missing)} "
          f"未知ID={len(unknown)} 覆盖率={stats['coverage']:.1%}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
