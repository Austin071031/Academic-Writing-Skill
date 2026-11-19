#!/usr/bin/env python3
"""boundary_engine.py — 引用保留与语义边界引擎（v1.0.4 边界清方向）。

子命令：
  index  预抽取 work/citation_index.json：逐句段引用标记清单（数字型/著者-年型）、
         参考文献条目数、语气/否定/限定标记清单（六类词表）。
  audit  译后核对：
         - 引用标记逐句段多重集比对（[1]、(Zhang et al., 2023) 必须原样保留）→ 缺失/新增=高
         - 参考文献条目原样保留（逐条比对源条目是否仍在译稿中）→ 缺失=高
         - 否定范围：源句段含否定标记而译文无任何否定标记 → 否定丢失=高
         - 语气强度：源含可能性/表明类/约数/限定标记而译文同类标记为空 → 强度丢失=中；
           源无确定性标记而译文出现「证明/必然/完全」类 → 强度升格=高
         - 增译数字：译文数字在源句段无对应（跨语言归一后）→ 疑似增译=高
         输出 work/boundary_audit.json、work/audit_annotated.md（⚠ 标注稿）、
         work/findings.json（语义边界维度）。
用法:
  python3 boundary_engine.py index --work /app/work
  python3 boundary_engine.py audit --work /app/work
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trans_utils as tu

RE_CITE_NUM = re.compile(r"[\[［]\s*\d+(?:\s*[-–,，]\s*\d+)*\s*[\]］]")
RE_CITE_AY_PAREN = re.compile(
    r"[（(](?:[A-Z][A-Za-zÀ-ÿ'’-]+(?:\s+(?:and|&|与)\s+[A-Z][A-Za-zÀ-ÿ'’-]+)?"
    r"(?:\s+et\s+al\.)?[，,]?\s+\d{4}[a-z]?(?:\s*[;；]\s*[^)）]*\d{4}[a-z]?)*"
    r")[)）]")
RE_CITE_AY_NARR = re.compile(
    r"[A-Z][A-Za-zÀ-ÿ'’-]+(?:\s+et\s+al\.)?\s*[（(]\d{4}[a-z]?[)）]")

def _norm_cite(raw):
    """归一：去空白、全角转半角、小写，供跨书写习惯比对。"""
    s = re.sub(r"\s+", "", raw).lower()
    for a, b in (("（", "("), ("）", ")"), ("［", "["), ("］", "]"), ("，", ",")):
        s = s.replace(a, b)
    return s

def cite_markers(text):
    ms = []
    for pat, style in ((RE_CITE_NUM, "numeric"), (RE_CITE_AY_PAREN, "author_year_paren"),
                       (RE_CITE_AY_NARR, "author_year_narrative")):
        for m in pat.finditer(text):
            ms.append({"raw": m.group(0), "style": style, "norm": _norm_cite(m.group(0))})
    ms.sort(key=lambda x: text.find(x["raw"]))
    return ms

def apply_custom_lexicon(work):
    """读取 work/custom_lexicon.json（{"add": {lang: {cat: [tokens]}}}）扩展语气词表。"""
    custom = tu.load_json(os.path.join(work, "custom_lexicon.json"))
    if not custom:
        return False
    added = 0
    for lang, cats in (custom.get("add") or {}).items():
        for cat, toks in cats.items():
            if cat in tu.HEDGE_LEXICON and lang in tu.HEDGE_LEXICON[cat]:
                for tok in toks:
                    if tok not in tu.HEDGE_LEXICON[cat][lang]:
                        tu.HEDGE_LEXICON[cat][lang].append(tok)
                        added += 1
    if added:
        print(f"[boundary_engine] custom_lexicon 扩展词表 +{added}")
    return added > 0

def cmd_index(work):
    segdata = tu.load_json(os.path.join(work, "segments.json"))
    if not segdata:
        print("[boundary_engine][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    apply_custom_lexicon(work)
    insp = tu.load_json(os.path.join(work, "inspection.json"), {}) or {}
    source_lang = (insp.get("translation_task") or {}).get("source_lang") or "en"
    entries = []
    refs = []
    for s in segdata["segments"]:
        if s["kind"] == "reference":
            refs.append({"seg_id": s["seg_id"], "text": s["source"]})
            continue
        if not s["needs_translation"]:
            continue
        cites = cite_markers(s["source"])
        hedges = tu.find_markers(s["source"], source_lang)
        if cites or hedges:
            entries.append({"seg_id": s["seg_id"], "section": s.get("section"),
                            "citations": cites, "hedges": hedges,
                            "source": s["source"][:200]})
    tu.save_json(os.path.join(work, "citation_index.json"), {
        "instructions": "翻译约束：引用标记原样保留（[1] 不译、(Zhang et al., 2023) "
                        "保持作者-年份）；否定/可能性/约数/限定标记必须等强译出；"
                        "参考文献条目原样保留。",
        "source_lang": source_lang,
        "reference_entries": len(refs),
        "entries": entries, "references": refs})
    print(f"[boundary_engine index] 含引用/语气句段={len(entries)} "
          f"参考文献条目={len(refs)}")
    return 0

def cmd_audit(work):
    segdata = tu.load_json(os.path.join(work, "segments.json"))
    if not segdata:
        print("[boundary_engine][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    apply_custom_lexicon(work)
    insp = tu.load_json(os.path.join(work, "inspection.json"), {}) or {}
    tt = insp.get("translation_task") or {}
    source_lang = tt.get("source_lang") or "en"
    target_lang = tt.get("target_lang") or "zh"
    merged, _ = tu.load_translations(work)

    findings = []
    audit_entries = []
    annotated = ["# 语义边界机检标注稿", "",
                 "> ⚠ 标记处为机检发现；逐条含句段 ID 可回查原文。本文件为复核辅助，",
                 "> 正式交付以 translation_full.md / bilingual.md 为准。", ""]
    n_find = 0
    cite_total = cite_ok = 0
    refs_missing = []

    for s in segdata["segments"]:
        sid = s["seg_id"]
        if s["kind"] == "reference":
            refs_missing.append((sid, s["source"]))  # 占位，后面统一比对
            continue
        if not s["needs_translation"]:
            continue
        tr = merged.get(sid)
        if not tr:
            continue
        src_cites = cite_markers(s["source"])
        tgt_cites = cite_markers(tr)
        cite_total += len(src_cites)
        seg_issues = []

        src_norm = sorted(c["norm"] for c in src_cites)
        tgt_norm = sorted(c["norm"] for c in tgt_cites)
        missing = list(src_norm)
        for t in tgt_norm:
            if t in missing:
                missing.remove(t)
        added = list(tgt_norm)
        for c in src_norm:
            if c in added:
                added.remove(c)
        cite_ok += len(src_cites) - len(missing)
        for c in missing:
            seg_issues.append(("引用标记缺失", "高", 0.95,
                               f"源引用标记 {c} 未在译文句段出现",
                               f"恢复引用标记 {c} 于对应论断句末（原位原格式）"))
        for c in added:
            seg_issues.append(("引用标记新增", "高", 0.9,
                               f"译文出现源句段没有的引用标记 {c}",
                               f"删除或回查 {c} 的来源句段"))

        # 语气/否定/限定
        src_h = tu.find_markers(s["source"], source_lang)
        tgt_h = tu.find_markers(tr, target_lang)
        tgt_cats = {h["category"] for h in tgt_h}
        src_cats = {}
        for h in src_h:
            src_cats.setdefault(h["category"], []).append(h["token"])
        for cat, toks in src_cats.items():
            if cat == "certainty":
                continue  # 确定性只在升格方向检查
            if cat not in tgt_cats:
                sev = "高" if cat == "negation" else "中"
                seg_issues.append((
                    {"negation": "否定范围丢失", "possibility": "可能性限定丢失",
                     "suggestion": "表明类语气丢失", "approximation": "约数限定丢失",
                     "limitation": "限定条件丢失"}.get(cat, "语气标记丢失"),
                    sev, 0.75,
                    f"源句段含 {cat} 标记 {sorted(set(toks))}，译文无同类标记",
                    "补出等强限定语；不得把「可能/约/仅」译丢或译强"))
        if "certainty" not in src_cats and "certainty" in tgt_cats:
            seg_issues.append(("语气升格", "高", 0.8,
                               "源句段无确定性表述，译文出现确定性词 "
                               f"{sorted({h['token'] for h in tgt_h if h['category']=='certainty'})}",
                               "删除升格表述，恢复与原文等强的克制语气"))

        # 增译数字
        src_nums = tu.extract_numbers(s["source"])
        tgt_nums = tu.extract_numbers(tr)
        src_vals = sorted(n["value"] for n in src_nums)
        for tn in tgt_nums:
            if tn["value"] in src_vals:
                src_vals.remove(tn["value"])
            elif any(abs(v - tn["value"]) <= 1e-12 * max(1, abs(v)) for v in src_vals):
                pass
            elif src_nums and any(
                    abs(v - tn["value"]) <= 0.02 * max(abs(v), 1e-12)
                    for v in [n["value"] for n in src_nums]):
                pass  # 与源数字末位级相近：属于“数字被改动”，由数字引擎报告，避免重复
            else:
                seg_issues.append(("增译数字", "高", 0.85,
                                   f"译文数字 {tn['raw']} 在源句段无对应",
                                   "删除该数字或回查其真实来源句段"))

        for label, sev, conf, ev, instr in seg_issues:
            n_find += 1
            findings.append({
                "id": f"BND-{n_find:03d}", "dimension": "语义边界", "type": label,
                "location": {"seg_id": sid, "section": s.get("section")},
                "quote": s["source"][:150],
                "evidence": ev + f"。译文：{tr[:150]}",
                "action": {"op": "fix_translation", "instruction": instr},
                "severity": sev, "confidence": conf, "status": "脚本候选"})
        if seg_issues:
            annotated.append(f"\n### 〔{sid}〕 {s.get('section') or ''}")
            annotated.append(f"\n原文：{s['source']}")
            annotated.append(f"\n译文：{tr}")
            for label, sev, conf, ev, instr in seg_issues:
                annotated.append(f"\n> ⚠ [{sev}] {label}：{ev}")
        audit_entries.append({"seg_id": sid, "section": s.get("section"),
                              "src_citations": src_norm, "tgt_citations": tgt_norm,
                              "issues": [x[0] for x in seg_issues]})

    # 参考文献条目完整性：译文交付物中参考文献原样保留检查
    tf_path = os.path.join(work, "..", "output", "translation_full.md")
    missing_refs = []
    if refs_missing:
        ref_texts = [r[1] for r in refs_missing]
        body = ""
        for cand in (os.path.normpath(tf_path),
                     os.path.join(work, "translation_full.md")):
            if os.path.exists(cand):
                with open(cand, encoding="utf-8") as f:
                    body = f.read()
                break
        for sid, txt in refs_missing:
            head = txt.strip()[:60]
            if body and head not in body:
                n_find += 1
                missing_refs.append(sid)
                findings.append({
                    "id": f"BND-{n_find:03d}", "dimension": "语义边界",
                    "type": "参考文献条目缺失",
                    "location": {"seg_id": sid, "section": "参考文献"},
                    "quote": txt[:150],
                    "evidence": "该参考文献条目未在译文交付物中检索到（按前60字符匹配）",
                    "action": {"op": "restore_citation",
                               "instruction": "参考文献条目原样保留，不译不删"},
                    "severity": "高", "confidence": 0.85, "status": "脚本候选"})

    summary = {"segments_checked": len(audit_entries),
               "citations_total": cite_total, "citations_preserved": cite_ok,
               "citation_fidelity": round(cite_ok / max(cite_total, 1), 4),
               "reference_entries_missing": len(missing_refs),
               "issues": len(findings)}
    tu.save_json(os.path.join(work, "boundary_audit.json"),
                 {"summary": summary, "entries": audit_entries})
    if len(annotated) > 5:
        with open(os.path.join(work, "audit_annotated.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(annotated) + "\n")
    old = tu.load_json(os.path.join(work, "findings.json"), []) or []
    old = [f for f in old if f.get("dimension") != "语义边界"]
    tu.save_json(os.path.join(work, "findings.json"), old + findings)
    print(f"[boundary_engine audit] 引用={cite_ok}/{cite_total} "
          f"文献缺失={len(missing_refs)} findings+{len(findings)}")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["index", "audit"])
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    return cmd_index(args.work) if args.cmd == "index" else cmd_audit(args.work)

if __name__ == "__main__":
    sys.exit(main())
