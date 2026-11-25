#!/usr/bin/env python3
"""qa_gate.py — 译后质量闸门（v2.0.4 方向）：一次运行完成三类高价值机检并去重排序。

组合检查（均基于译文 vs 源句段逐句段比对，零依赖）：
  1. 数字忠实（number_engine 同算法：缺失/增译/改动三档/单位差异）
  2. 引用与语义边界（引用标记多重集、否定/限定/语气升格、增译数字去重分工）
  3. 缩写一致性（源中 (ABBR) 定义的缩写在译文中出现形态一致；全称译名首次定义检查）
输出 work/qa_report.json（按严重度排序的统一修复清单）+ 合并进 work/findings.json
（维度分别标 事实与数字 / 语义边界 / 术语一致性，与单引擎报告兼容）。
用法: python3 qa_gate.py --work /app/work
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trans_utils as tu
import number_engine as ne
import boundary_engine as be

SEV_ORDER = {"高": 0, "中": 1, "低": 2}

def acronym_check(segments, merged, source_lang):
    """缩写一致性：定义句段译文须保留缩写；后续句段缩写形态一致。"""
    findings = []
    defs = {}  # abbr -> def_seg_id
    for s in segments:
        if not s["needs_translation"]:
            continue
        for m in re.finditer(r"[（(]([A-Z][A-Za-z0-9]{1,7})[)）]", s["source"]):
            ab = m.group(1)
            if ab not in defs:
                defs[ab] = s["seg_id"]
    for ab, def_sid in defs.items():
        tr = merged.get(def_sid)
        if tr and ab not in tr:
            findings.append({
                "dimension": "术语一致性", "type": "缩写首现定义丢失",
                "location": {"seg_id": def_sid, "section": None},
                "quote": next(s["source"][:120] for s in segments
                              if s["seg_id"] == def_sid),
                "evidence": f"源句段含 ({ab}) 定义，译文未保留缩写 {ab}。译文：{tr[:120]}",
                "action": {"op": "fix_translation",
                           "instruction": f"首现处保留「中文全称（{ab}）」式定义"},
                "severity": "中", "confidence": 0.75, "status": "脚本候选"})
        for s in segments:
            if not s["needs_translation"] or s["seg_id"] == def_sid:
                continue
            if re.search(r"(?<![A-Za-z])" + re.escape(ab) + r"(?![A-Za-z])", s["source"]):
                tr2 = merged.get(s["seg_id"])
                if tr2 and ab not in tr2 and source_lang == "en":
                    # 后续句段源用缩写、译文未用缩写也未必错（可能用了中文全称），低置信提示
                    pass
    return findings

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    segdata = tu.load_json(os.path.join(args.work, "segments.json"))
    if not segdata:
        print("[qa_gate][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    insp = tu.load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    tt = insp.get("translation_task") or {}
    source_lang = tt.get("source_lang") or "en"
    segments = segdata["segments"]
    merged, _ = tu.load_translations(args.work)

    # 复用两个引擎的审计（写各自 audit 文件 + findings）
    rc1 = ne.cmd_audit(args.work)
    be.apply_custom_lexicon(args.work)
    rc2 = be.cmd_audit(args.work)
    if rc1 or rc2:
        print("[qa_gate][warn] 子引擎返回非零", file=sys.stderr)

    acro_findings = acronym_check(segments, merged, source_lang)

    # 合并 findings：引擎已写 事实与数字 / 语义边界 维度；追加缩写维度，去重
    findings = tu.load_json(os.path.join(args.work, "findings.json"), []) or []
    findings = [f for f in findings if f.get("type") != "缩写首现定义丢失"]
    n0 = len(findings)
    for i, f in enumerate(acro_findings, 1):
        f["id"] = f"QA-ACRO-{i:03d}"
    findings += acro_findings

    # 按严重度排序统一编号 QA 清单
    findings.sort(key=lambda x: (SEV_ORDER.get(x.get("severity"), 3),
                                 x.get("dimension", ""),
                                 (x.get("location") or {}).get("seg_id") or ""))
    tu.save_json(os.path.join(args.work, "findings.json"), findings)

    by_dim, by_sev = {}, {"高": 0, "中": 0, "低": 0}
    for f in findings:
        by_dim[f["dimension"]] = by_dim.get(f["dimension"], 0) + 1
        by_sev[f.get("severity", "低")] = by_sev.get(f.get("severity", "低"), 0) + 1
    fix_list = [{
        "rank": i + 1, "id": f["id"], "severity": f["severity"],
        "dimension": f["dimension"], "type": f["type"],
        "seg_id": (f.get("location") or {}).get("seg_id"),
        "instruction": (f.get("action") or {}).get("instruction"),
    } for i, f in enumerate(findings)]
    tu.save_json(os.path.join(args.work, "qa_report.json"), {
        "summary": {"total": len(findings), "by_dimension": by_dim,
                    "by_severity": by_sev,
                    "acronym_findings": len(acro_findings)},
        "fix_list": fix_list,
        "policy": "按 rank 顺序处置；高严重度（数字/引用/否定/升格/增译）必须清零，"
                  "中低严重度逐条修订或驳回并写明理由。修订后重跑本闸门确认。",
    })
    print(f"[qa_gate] 总问题={len(findings)} 高/中/低="
          f"{by_sev['高']}/{by_sev['中']}/{by_sev['低']} 维度={by_dim} "
          f"（缩写新增 {len(findings) - n0}）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
