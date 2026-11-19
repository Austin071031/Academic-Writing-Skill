#!/usr/bin/env python3
"""contribution_align.py — V4 贡献-证据对齐：每条贡献必须能指回稿件中的具体证据。

用法: python3 contribution_align.py --work /app/work --out /app/output
读 work/contributions.json:
  {"items":[{"cid","statement","type":"method|experiment|conclusion",
              "evidence_locs":["P012","图3","表2"],"scope_words":["首次"]}]}
校验（每条贡献）:
  1) statement 非空；type ∈ {method, experiment, conclusion}；
  2) evidence_locs ≥1，且每个 loc 可解析：P### 必须是稿件段落 pid；"图N"/"表N" 必须出现在稿件文本中；
  3) 数字可回溯：statement 中的每个数字必须能在某个 evidence_loc 指向的段落文本中找到；
  4) 范围词检查：scope_words 含 首次/最优/最佳/全面/显著/大幅/极大 等时，若证据段落中没有
     比较性数字（优于/超过/相比/提升/%），则登记 manual_confirmations（人工确认项）。
渲染 contributions_check.md 对照表；verdict ∈ {pass, warn, fail}。
"""
import argparse, json, os, re, sys

NUM_TOKEN = re.compile(r"\d+(?:\.\d+)?")
SCOPE_WORDS = ("首次", "最先", "最优", "最佳", "最好", "全面", "系统", "显著", "大幅", "极大", "明显")
COMPARATIVE = re.compile(r"优于|超过|相比|相对|提升|提高|降低|减少|快\s*\d|%|％|倍")

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    doc = load_json(os.path.join(args.work, "contributions.json"), {}) or {}
    items = doc.get("items", []) if isinstance(doc, dict) else []
    ms = load_json(os.path.join(args.work, "manuscript.json"), {}) or {}
    paras = {p.get("pid"): p.get("text", "") for p in ms.get("paragraphs", [])}
    ms_all = "\n".join(paras.values())

    manual_path = os.path.join(args.work, "manual_confirmations.json")
    manual = load_json(manual_path, []) or []

    rows = []
    for it in items:
        cid = it.get("cid") or f"C{len(rows)+1}"
        issues = []
        stmt = (it.get("statement") or "").strip()
        if not stmt:
            issues.append("贡献表述为空")
        typ = it.get("type") or ""
        if typ not in ("method", "experiment", "conclusion"):
            issues.append(f"type 非法: {typ or '缺失'}")
        locs = it.get("evidence_locs") or []
        if not locs:
            issues.append("无 evidence_locs")
        resolved_text = ""
        for loc in locs:
            if loc in paras:
                resolved_text += "\n" + paras[loc]
            elif re.match(r"^(图|表)\s*\d+", loc or ""):
                if re.search(re.escape(loc.replace(" ", "")), ms_all.replace(" ", "")):
                    resolved_text += "\n" + loc
                else:
                    issues.append(f"{loc} 在稿件中找不到")
            else:
                issues.append(f"loc 无法解析: {loc}")
        num_bad = []
        for n in NUM_TOKEN.findall(stmt):
            if resolved_text and n not in NUM_TOKEN.findall(resolved_text):
                num_bad.append(n)
        if num_bad:
            issues.append(f"数字不可回溯: {', '.join(num_bad[:5])}")
        flagged_scopes = []
        for w in (it.get("scope_words") or []):
            if w in SCOPE_WORDS:
                if not COMPARATIVE.search(resolved_text or ""):
                    flagged_scopes.append(w)
                    manual.append({"item": cid, "type": "overclaim_risk",
                                   "detail": f"贡献表述含范围词「{w}」，但证据位置未见比较性数据，需作者确认",
                                   "statement": stmt[:100], "evidence_locs": locs})
        rows.append({"cid": cid, "type": typ, "locs": locs, "issues": issues,
                     "scope_flags": flagged_scopes})

    if not items:
        verdict = "fail"
    elif all(not r["issues"] for r in rows) and not any(r["scope_flags"] for r in rows):
        verdict = "pass"
    elif any(r["issues"] for r in rows) and all(r["issues"] for r in rows):
        verdict = "fail"
    else:
        verdict = "warn"

    report = {"version": "v1.0.3-贡献证据对齐",
              "n_items": len(items), "items": rows, "verdict": verdict}
    os.makedirs(args.work, exist_ok=True)
    with open(os.path.join(args.work, "version_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    if manual:
        with open(manual_path, "w", encoding="utf-8") as f:
            json.dump(manual, f, ensure_ascii=False, indent=2)

    lines = ["# 贡献-证据对照表", "",
             "| 贡献 | 类型 | 证据位置 | 数字回溯 | 范围词 | 结论 |",
             "|---|---|---|---|---|---|"]
    for r, it in zip(rows, items):
        cid = r["cid"]
        stmt = (it.get("statement") or "")[:80]
        nums_ok = "✅" if not any("数字不可回溯" in i for i in r["issues"]) else "⚠"
        scopes = "、".join(r["scope_flags"]) if r["scope_flags"] else "—"
        result = "✅" if not r["issues"] and not r["scope_flags"] else "⚠ " + "；".join(r["issues"][:2])
        lines.append(f"| {cid} {stmt} | {r['type']} | {', '.join(r['locs']) or '—'} | "
                     f"{nums_ok} | {scopes} | {result} |")
    if not items:
        lines.append("| — | — | — | — | — | 未登记任何贡献条目 |")
    lines.append("")
    lines.append(f"总体结论：**{verdict}**")

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "contributions_check.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    n_bad = sum(1 for r in rows if r["issues"])
    print(f"[contrib] 贡献={len(items)} 有问题={n_bad} 范围词={sum(len(r['scope_flags']) for r in rows)} verdict={verdict}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
