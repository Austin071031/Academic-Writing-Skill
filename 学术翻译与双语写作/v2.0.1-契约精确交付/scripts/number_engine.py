#!/usr/bin/env python3
"""number_engine.py — 事实与数字忠实性引擎（v1.0.1 数字实方向）。

子命令：
  ledger  预抽取：每个待译句段的全部数字（值/单位/原文/上下文）→ work/number_ledger.json
  audit   译后核对：译文句段数字 vs 源句段数字，逐条比对：
          - 值缺失（源有译无）→ 高严重度
          - 值改动（不等值）→ 区分疑似四舍五入/笔误（末位级）与实质篡改（量级/大幅偏差）
          - 值新增（译有源无）→ 疑似增译数字，高严重度
          - 单位错配（值同单位异）→ 中严重度
          跨语言表达（万/亿/million/billion、千分位、科学计数）按归一值比对，
          等值即通过并记录换算映射。输出 work/number_audit.json + work/findings.json。
用法:
  python3 number_engine.py ledger --work /app/work
  python3 number_engine.py audit  --work /app/work
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trans_utils as tu

def nums_key(n):
    """(归一值, 单位) 用于比对；单位 None 视为无量纲。"""
    return (n["value"], (n["unit"] or "").lower() or None)

def classify_change(src_val, tgt_val):
    """返回值改动类型：rounding / typo / altered。"""
    if src_val == 0:
        return "altered"
    rel = abs(tgt_val - src_val) / abs(src_val)
    if rel == 0:
        return None
    # 末位级差异：相对偏差 ≤ 源值末位单位量级（按源值有效位数估计）
    s = f"{abs(src_val):.10g}"
    digits = len(re.sub(r"\D", "", s).lstrip("0"))
    ulp_rel = 10 ** (-(digits - 1)) if digits else 0.05
    if rel <= ulp_rel * 0.6:
        return "rounding"
    if rel <= 0.02:
        return "rounding"
    # 常见笔误：数字重排/落一位（如 23.4 vs 24.3 / 2.34）
    for scale in (10, 0.1, 100, 0.01):
        if abs(tgt_val * scale - src_val) / abs(src_val) <= 1e-9:
            return "typo"
    return "altered"

def cmd_ledger(work):
    segdata = tu.load_json(os.path.join(work, "segments.json"))
    if not segdata:
        print("[number_engine][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    entries = []
    for s in segdata["segments"]:
        if not s["needs_translation"]:
            kind_note = "不译段"
        else:
            kind_note = None
        nums = tu.extract_numbers(s["source"])
        if not nums:
            continue
        entries.append({"seg_id": s["seg_id"], "section": s.get("section"),
                        "kind": s["kind"], "needs_translation": s["needs_translation"],
                        "note": kind_note,
                        "numbers": [{"raw": n["raw"], "value": n["value"],
                                     "unit": n["unit"]} for n in nums],
                        "source": s["source"][:200]})
    tu.save_json(os.path.join(work, "number_ledger.json"), {
        "instructions": "翻译约束：每个数字的值、单位、量级、有效位数必须原样落地；"
                        "万/亿↔million/billion 只允许等值换算，不允许四舍五入或改整。",
        "total_segments_with_numbers": len(entries),
        "total_numbers": sum(len(e["numbers"]) for e in entries),
        "entries": entries})
    print(f"[number_engine ledger] 含数字句段={len(entries)} "
          f"数字总数={sum(len(e['numbers']) for e in entries)}")
    return 0

def match_numbers(src_nums, tgt_nums):
    """贪心匹配：先 (值,单位) 精确，再仅值，再单位无关近似。返回 matched/missed/added/pairs。"""
    remaining = list(range(len(tgt_nums)))
    matched, pairs = [], []
    # 第一轮：值+单位精确
    for sn in src_nums:
        hit = None
        for i in remaining:
            tn = tgt_nums[i]
            if nums_key(sn) == nums_key(tn):
                hit = i
                break
        if hit is not None:
            remaining.remove(hit)
            matched.append(sn)
            pairs.append((sn, tgt_nums[hit], "exact"))
    # 第二轮：仅值精确（单位可能形式差异）
    rest_src = [s for s in src_nums if s not in matched]
    matched2 = []
    for sn in rest_src:
        hit = None
        for i in remaining:
            if abs(tgt_nums[i]["value"] - sn["value"]) <= 1e-12 * max(1, abs(sn["value"])):
                hit = i
                break
        if hit is not None:
            remaining.remove(hit)
            matched2.append(sn)
            pairs.append((sn, tgt_nums[hit], "value_only"))
    missed = [s for s in rest_src if s not in matched2]
    added = [tgt_nums[i] for i in remaining]
    return pairs, missed, added

def cmd_audit(work):
    segdata = tu.load_json(os.path.join(work, "segments.json"))
    if not segdata:
        print("[number_engine][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    merged, _ = tu.load_translations(work)
    findings = []
    audit_entries = []
    n_find = 0
    tot_src = tot_ok = 0
    for s in segdata["segments"]:
        if not s["needs_translation"]:
            continue
        src_nums = tu.extract_numbers(s["source"])
        if not src_nums:
            continue
        tr = merged.get(s["seg_id"])
        if not tr:
            continue
        tgt_nums = tu.extract_numbers(tr)
        pairs, missed, added = match_numbers(src_nums, tgt_nums)
        tot_src += len(src_nums)
        tot_ok += len(pairs)
        issues = []
        for sn, tn, how in pairs:
            if how == "value_only" and (sn["unit"] or "").lower() != (tn["unit"] or "").lower():
                issues.append(("单位形式差异", sn, tn, "低",
                               f"值相等（{sn['raw']}↔{tn['raw']}）但单位写法不同："
                               f"{sn['unit']} vs {tn['unit']}；确认系等值换算或统一写法"))
        for sn in missed:
            best = min(tgt_nums, key=lambda t: abs(t["value"] - sn["value"]), default=None)
            if best is not None:
                chg = classify_change(sn["value"], best["value"])
                if chg and best["value"] != sn["value"]:
                    sev = "中" if chg == "rounding" else "高"
                    label = {"rounding": "疑似四舍五入/笔误", "typo": "疑似数字笔误",
                             "altered": "数字被改动"}[chg]
                    issues.append((label, sn, best, sev,
                                   f"源值 {sn['raw']} 与最接近译文值 {best['raw']} 不等"
                                   f"（{sn['value']} vs {best['value']}）"))
                    # 该目标数字已被归因于源数字的改动，不再计入“增译”
                    if best in added:
                        added.remove(best)
                    continue
            issues.append(("数字缺失", sn, None, "高",
                           f"源数字 {sn['raw']}（值 {sn['value']}，单位 {sn['unit']}）"
                           "在译文句段中不存在"))
        for tn in added:
            issues.append(("增译数字", None, tn, "高",
                           f"译文数字 {tn['raw']}（值 {tn['value']}）在源句段中无对应，"
                           "疑似凭空补写或串段"))
        for label, sn, tn, sev, ev in issues:
            n_find += 1
            findings.append({
                "id": f"NUM-{n_find:03d}", "dimension": "事实与数字", "type": label,
                "location": {"seg_id": s["seg_id"], "section": s.get("section")},
                "quote": s["source"][:150],
                "evidence": ev + f"。译文：{tr[:150]}",
                "action": {"op": "restore_number",
                           "instruction": (f"恢复源数字「{sn['raw']}」原值与单位"
                                           if sn else
                                           f"删除或回查译文数字「{tn['raw']}」的来源")},
                "severity": sev, "confidence": 0.9 if sev == "高" else 0.75,
                "status": "脚本候选"})
        audit_entries.append({"seg_id": s["seg_id"], "section": s.get("section"),
                              "source_numbers": [n["raw"] for n in src_nums],
                              "target_numbers": [n["raw"] for n in tgt_nums],
                              "matched": [{"src": a["raw"], "tgt": b["raw"], "how": h}
                                          for a, b, h in pairs],
                              "issues": [i[0] for i in issues]})
    summary = {"segments_checked": len(audit_entries),
               "source_numbers": tot_src, "matched_numbers": tot_ok,
               "fidelity": round(tot_ok / max(tot_src, 1), 4),
               "issues": len(findings)}
    tu.save_json(os.path.join(work, "number_audit.json"),
                 {"summary": summary, "entries": audit_entries})
    old = tu.load_json(os.path.join(work, "findings.json"), []) or []
    old = [f for f in old if f.get("dimension") != "事实与数字"]
    tu.save_json(os.path.join(work, "findings.json"), old + findings)
    print(f"[number_engine audit] 句段={len(audit_entries)} 数字={tot_src} "
          f"匹配={tot_ok} 忠实率={summary['fidelity']:.1%} findings+{len(findings)}")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["ledger", "audit"])
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    return cmd_ledger(args.work) if args.cmd == "ledger" else cmd_audit(args.work)

if __name__ == "__main__":
    sys.exit(main())
