#!/usr/bin/env python3
"""term_engine.py — 术语一致性引擎（v1.0.0 术语锁定方向）。

子命令：
  seed   从 segments.json 抽取术语候选（缩写定义、首字母大写复合词、
         高频小写名词短语 2-4 元），生成 work/glossary_seed.json
  audit  依据 work/glossary.json（Agent 锁定译名）逐句段核对译文：
         源句段含术语而译文不含锁定译名 → 术语未锁定（候选）；
         同一术语跨章节译名漂移（译文中出现的其他写法）→ 译名不一致；
         缩写首现未给全称。输出 work/term_audit.json + work/findings.json。
用法:
  python3 term_engine.py seed  --work /app/work
  python3 term_engine.py audit --work /app/work
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trans_utils as tu

EN_STOP = set("""the a an and or of to in for on with by from at as is are was were be been
being this that these those it its we our their they he she his her not no can could may might
shall should will would do does did have has had than then thus hence also such more most other
another between among within without into over under above below after before during through
both each all any some none only same different new used using use based via et al fig figure
table eq equation ref refs see shown shows show given where when while which who whom whose what
how however therefore moreover furthermore respectively""".split())

RE_ACRO_FULL = re.compile(
    r"([A-Z][A-Za-z-]*(?:\s+[a-zA-Z][A-Za-z-]*){1,4}|[a-z][A-Za-z-]*(?:\s+[a-zA-Z][A-Za-z-]*){1,4})"
    r"\s*\(([A-Z][A-Za-z0-9]{1,7})\)")
RE_CAP_PHRASE = re.compile(r"\b([A-Z][a-zA-Z-]+(?:\s+(?:of|the|for|and|de|van)\s+)?"
                           r"(?:\s+[A-Z][a-zA-Z-]+){0,3})\b")
RE_TOKEN = re.compile(r"[a-z][a-z-]{2,}")

def norm_phrase(words):
    return " ".join(words).lower()

def extract_candidates(segments, max_terms=60):
    """术语候选：缩写定义对、大写复合词、高频小写 n-gram（2-4）。"""
    acro, cap, ngram = {}, {}, {}
    seg_texts = [(s["seg_id"], s.get("section") or "", s["source"])
                 for s in segments if s["needs_translation"]]
    for sid, sec, text in seg_texts:
        for m in RE_ACRO_FULL.finditer(text):
            full, ab = m.group(1).strip(), m.group(2)
            # 去掉全称前导冠词/停用词（"The hole transport layer" → "hole transport layer"）
            words = full.split()
            while words and words[0].lower() in EN_STOP:
                words.pop(0)
            full = " ".join(words) or m.group(1).strip()
            key = ab
            e = acro.setdefault(key, {"term": full, "acronym": ab, "occurrences": 0,
                                      "sections": set(), "contexts": []})
            e["occurrences"] += 1
            e["sections"].add(sec)
            if len(e["contexts"]) < 3:
                e["contexts"].append(sid)
        for m in RE_CAP_PHRASE.finditer(text):
            ph = m.group(1).strip()
            if len(ph) < 4 or ph.lower() in EN_STOP:
                continue
            e = cap.setdefault(ph, {"term": ph, "acronym": None, "occurrences": 0,
                                    "sections": set(), "contexts": []})
            e["occurrences"] += 1
            e["sections"].add(sec)
            if len(e["contexts"]) < 3:
                e["contexts"].append(sid)
        toks = [t for t in RE_TOKEN.findall(text.lower()) if t not in EN_STOP]
        for n in (2, 3, 4):
            for i in range(len(toks) - n + 1):
                gram = norm_phrase(toks[i:i + n])
                e = ngram.setdefault(gram, {"term": gram, "acronym": None,
                                            "occurrences": 0, "sections": set(),
                                            "contexts": []})
                e["occurrences"] += 1
                e["sections"].add(sec)
                if len(e["contexts"]) < 3:
                    e["contexts"].append(sid)

    cands = []
    for pool, min_occ, tag in ((acro, 1, "acronym"), (cap, 2, "capitalized"),
                               (ngram, 3, "frequent_phrase")):
        for e in pool.values():
            # n-gram 若为更长高频串的子串且频次相同则跳过（保留信息量大者）
            e["sections"] = sorted(e["sections"])
            e["source"] = tag
            if e["occurrences"] >= min_occ and len(e["term"]) >= 4:
                cands.append(e)
    # 子串去重：若 A 是 B 的子串且频次相同，删 A
    terms = sorted(cands, key=lambda e: (-e["occurrences"], -len(e["term"])))
    keep, seen = [], []
    for e in terms:
        t = e["term"].lower()
        merged = False
        for kept in keep:
            kt = kept["term"].lower()
            if (t in kt or kt in t) and e["occurrences"] <= kept["occurrences"]:
                # 子串去重：但缩写定义信息要并到保留条目上
                if e.get("acronym") and not kept.get("acronym") and t == kt:
                    kept["acronym"] = e["acronym"]
                    kept["source"] = kept["source"] + "+acronym"
                merged = True
                break
        if merged:
            continue
        keep.append(e)
        if len(keep) >= max_terms:
            break
    for i, e in enumerate(keep, 1):
        e["term_id"] = f"T{i:03d}"
        e["locked_translation"] = None
        e["locked"] = False
        e["rationale"] = None
        e["discipline_note"] = None
    return keep

def cmd_seed(work):
    segdata = tu.load_json(os.path.join(work, "segments.json"))
    if not segdata:
        print("[term_engine][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    cands = extract_candidates(segdata["segments"])
    tu.save_json(os.path.join(work, "glossary_seed.json"), {
        "instructions": "Agent：为每个候选给出 locked_translation（全篇唯一译名）"
                        "并将 locked 置 true；不合术语者删除该行；"
                        "同一英文词在不同语境译法不同者填 discipline_note；"
                        "rationale 简述依据（学科惯例/材料内定义/权威用法）。",
        "terms": cands})
    print(f"[term_engine seed] 术语候选={len(cands)} → work/glossary_seed.json")
    return 0

def cmd_audit(work):
    segdata = tu.load_json(os.path.join(work, "segments.json"))
    if not segdata:
        print("[term_engine][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    insp = tu.load_json(os.path.join(work, "inspection.json"), {}) or {}
    target_lang = (insp.get("translation_task") or {}).get("target_lang") or "zh"
    merged, _ = tu.load_translations(work)
    gl = tu.load_json(os.path.join(work, "glossary.json"))
    seed_used = False
    if not gl:
        gl = tu.load_json(os.path.join(work, "glossary_seed.json"), {"terms": []})
        seed_used = True
    terms = [t for t in gl.get("terms", []) if t.get("locked") and t.get("locked_translation")]

    findings = []
    audit_entries = []
    n_find = 0
    for t in terms:
        term, locked_zh = t["term"], t["locked_translation"]
        acro = t.get("acronym")
        variants = t.get("declared_variants") or []
        total, ok, viol = 0, 0, []
        first_seen = None
        for s in segdata["segments"]:
            if not s["needs_translation"]:
                continue
            src = s["source"]
            hit_term = re.search(re.escape(term), src, re.I)
            hit_acro = acro and re.search(r"(?<![A-Za-z])" + re.escape(acro) + r"(?![A-Za-z])", src)
            if not (hit_term or hit_acro):
                continue
            total += 1
            tr = merged.get(s["seg_id"])
            if first_seen is None:
                first_seen = (s, bool(hit_term), tr)
            if not tr:
                continue
            if locked_zh in tr or any(v in tr for v in variants):
                ok += 1
            else:
                viol.append({"seg_id": s["seg_id"], "section": s.get("section"),
                             "source": src[:120], "translation": tr[:120]})
        for v in viol:
            n_find += 1
            findings.append({
                "id": f"TERM-{n_find:03d}", "dimension": "术语一致性",
                "type": "术语未锁定",
                "location": {"seg_id": v["seg_id"], "section": v["section"]},
                "quote": v["source"],
                "evidence": f"术语 {term}（锁定译名「{locked_zh}」）在源句段出现，"
                            f"译文未使用该锁定译名。译文：{v['translation']}",
                "action": {"op": "unify_term",
                           "instruction": f"将该句段中 {term} 的译法改为锁定译名"
                                          f"「{locked_zh}」（如确有学科理由改译，"
                                          f"在 glossary.json 的 declared_variants 登记）"},
                "severity": "中", "confidence": 0.85,
                "status": "脚本候选"})
        # 缩写首现全称检查：定位含「全称 (ABBR)」定义的句段，核对译文保留缩写
        if acro:
            def_seg = None
            for s in segdata["segments"]:
                if not s["needs_translation"]:
                    continue
                if re.search(re.escape("(" + acro + ")"), s["source"]) or \
                        re.search(re.escape("（" + acro + "）"), s["source"]):
                    def_seg = s
                    break
            if def_seg is not None:
                s, tr = def_seg, merged.get(def_seg["seg_id"])
                has_pair = tr and (acro in tr) and ("（" in tr or "(" in tr)
                if tr and not has_pair:
                    n_find += 1
                    findings.append({
                        "id": f"TERM-{n_find:03d}", "dimension": "术语一致性",
                        "type": "缩写首现未给全称",
                        "location": {"seg_id": s["seg_id"], "section": s.get("section")},
                        "quote": s["source"][:120],
                        "evidence": f"{term} ({acro}) 首现句段译文未保留"
                                    f"「中文全称（{acro}）」式定义。译文：{(tr or '')[:120]}",
                        "action": {"op": "fix_translation",
                                   "instruction": f"首现处译为「{locked_zh}（{acro}）」，"
                                                  "其后可单用缩写"},
                        "severity": "低", "confidence": 0.7,
                        "status": "脚本候选"})
        audit_entries.append({"term_id": t.get("term_id"), "term": term,
                              "acronym": acro, "locked_translation": locked_zh,
                              "occurrences": total, "compliant": ok,
                              "violations": viol})

    unlocked = [t for t in gl.get("terms", []) if not t.get("locked")]
    summary = {"terms_locked": len(terms), "terms_unlocked": len(unlocked),
               "seed_fallback": seed_used,
               "total_occurrences": sum(e["occurrences"] for e in audit_entries),
               "compliant_occurrences": sum(e["compliant"] for e in audit_entries),
               "violations": sum(len(e["violations"]) for e in audit_entries)}
    tu.save_json(os.path.join(work, "term_audit.json"),
                 {"summary": summary, "entries": audit_entries})
    old = tu.load_json(os.path.join(work, "findings.json"), []) or []
    old = [f for f in old if f.get("dimension") != "术语一致性"]
    tu.save_json(os.path.join(work, "findings.json"), old + findings)
    print(f"[term_engine audit] 锁定术语={len(terms)} 违规={summary['violations']} "
          f"findings+{len(findings)}" + ("（警告：使用 seed 未锁定表）" if seed_used else ""))
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["seed", "audit"])
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    return cmd_seed(args.work) if args.cmd == "seed" else cmd_audit(args.work)

if __name__ == "__main__":
    sys.exit(main())
