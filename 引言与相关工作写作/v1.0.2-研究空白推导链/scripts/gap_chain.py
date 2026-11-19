#!/usr/bin/env python3
"""gap_chain.py — V3 研究空白推导链：空白必须由已引文献的缺口推出。

用法: python3 gap_chain.py --work /app/work --out /app/output
读 work/gap_chain.json:
  {"gaps":[{"gid","premises":[{"entry_ids":[...],"manuscript_loc":"P007"(可选),"limitation":"<具体限制>","quote":"<材料摘录>"}],
             "gap_statement":"<空白陈述>","paper_response":"<本文如何填补>","response_evidence_loc":"P012|图3"}]}
校验（每条空白）:
  1) premises ≥1，且每条 premise 至少给出 entry_ids（存在于 library）或 manuscript_loc（存在于稿件 pid）；
  2) limitation 与 quote 非空（quote 是从材料摘录的具体文字，≤200字）；
  3) 数字泄漏检查：gap_statement 与 paper_response 中出现的数字，必须能在前提 quote 或
     response_evidence_loc 指向的稿件段落中找到；找不到 → number_leak 警告；
  4) paper_response 非空且 response_evidence_loc 可解析（pid 或 图N/表N 出现在稿件中）。
渲染 gap_derivation.md（逐条展示 前提→缺口→本文对应 的推导链）。
verdict ∈ {pass, warn, fail}；无空白（gaps 为空）→ fail 并提示"空白缺乏依据，须由材料推导或如实标注"。
"""
import argparse, json, os, re, sys

NUM_TOKEN = re.compile(r"\d+(?:\.\d+)?")

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

    gaps_doc = load_json(os.path.join(args.work, "gap_chain.json"), {}) or {}
    gaps = gaps_doc.get("gaps", []) if isinstance(gaps_doc, dict) else []
    lib = load_json(os.path.join(args.work, "library.json"), {}) or {}
    records = {r.get("id"): r for r in lib.get("records", []) if r.get("id")}
    ms = load_json(os.path.join(args.work, "manuscript.json"), {}) or {}
    paras = {p.get("pid"): p.get("text", "") for p in ms.get("paragraphs", [])}
    ms_all = "\n".join(paras.values())

    results = []
    for g in gaps:
        gid = g.get("gid") or f"G{len(results)+1}"
        issues = []
        premises = g.get("premises") or []
        if not premises:
            issues.append("无前提：空白缺乏依据")
        allowed_nums = set()
        for i, pr in enumerate(premises):
            eids = pr.get("entry_ids") or []
            loc = pr.get("manuscript_loc") or ""
            if not eids and not loc:
                issues.append(f"前提{i+1} 既无 entry_ids 也无 manuscript_loc")
            for e in eids:
                if e not in records:
                    issues.append(f"前提{i+1} 引用了不存在的文献 {e}")
            if loc and loc not in paras:
                issues.append(f"前提{i+1} manuscript_loc {loc} 不在稿件段落中")
            if not (pr.get("limitation") or "").strip():
                issues.append(f"前提{i+1} 缺少 limitation（具体限制）")
            quote = (pr.get("quote") or "").strip()
            if not quote:
                issues.append(f"前提{i+1} 缺少 quote（材料摘录）")
            else:
                allowed_nums.update(NUM_TOKEN.findall(quote))
                if loc and loc in paras:
                    allowed_nums.update(NUM_TOKEN.findall(paras[loc]))
        stmt = g.get("gap_statement") or ""
        if not stmt.strip():
            issues.append("gap_statement 为空")
        resp = g.get("paper_response") or ""
        if not resp.strip():
            issues.append("paper_response 为空（未说明本文如何填补）")
        rel = g.get("response_evidence_loc") or ""
        if rel:
            if rel in paras:
                allowed_nums.update(NUM_TOKEN.findall(paras[rel]))
            elif re.match(r"^(图|表)\s*\d+", rel) and re.search(re.escape(rel.replace(" ", "")), ms_all.replace(" ", "")):
                pass
            else:
                issues.append(f"response_evidence_loc {rel} 无法解析")
        else:
            issues.append("缺少 response_evidence_loc")
        leaks = []
        for field, text in (("gap_statement", stmt), ("paper_response", resp)):
            for n in NUM_TOKEN.findall(text):
                if n not in allowed_nums and n not in NUM_TOKEN.findall(ms_all):
                    leaks.append({"field": field, "number": n})
        if leaks:
            issues.append(f"数字泄漏 {len(leaks)} 处: " + ", ".join(f"{l['field']}:{l['number']}" for l in leaks[:5]))
        results.append({"gid": gid, "premises": len(premises), "issues": issues,
                        "number_leaks": leaks})

    if not gaps:
        verdict = "fail"
    elif any(not r["issues"] for r in results) and not any("无前提" in i or "泄漏" in i
             for r in results for i in r["issues"]):
        verdict = "pass"
    elif all(r["issues"] for r in results):
        verdict = "fail"
    else:
        verdict = "warn"

    report = {"version": "v1.0.2-研究空白推导链",
              "n_gaps": len(gaps), "gaps": results, "verdict": verdict}
    os.makedirs(args.work, exist_ok=True)
    with open(os.path.join(args.work, "version_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    lines = ["# 研究空白推导链", ""]
    if not gaps:
        lines.append('⚠ 未登记任何空白推导（gap_chain.json 为空）。研究空白必须由已引文献的缺口'
                     '或稿件材料推导；若材料确实不足，请在 uncertainty.json 中如实标注，'
                     '并在引言中以「作者判断」形式明示。')
    for g in gaps:
        gid = g.get("gid") or "?"
        lines.append(f"## {gid}")
        lines.append("")
        lines.append("**前提（已引文献/材料的缺口）**")
        for pr in (g.get("premises") or []):
            srcs = ", ".join(pr.get("entry_ids") or []) or pr.get("manuscript_loc", "")
            lines.append(f"- 来源 {srcs}：{pr.get('limitation', '')}")
            if pr.get("quote"):
                lines.append(f"  > 摘录：{pr['quote'][:150]}")
        lines.append("")
        lines.append(f"**缺口**：{g.get('gap_statement', '')}")
        lines.append("")
        lines.append(f"**本文对应**：{g.get('paper_response', '')}（证据位置：{g.get('response_evidence_loc', '未标注')}）")
        lines.append("")
    rmap = {r["gid"]: r for r in results}
    lines.append("## 校验结果")
    lines.append("")
    for g in gaps:
        gid = g.get("gid") or "?"
        r = rmap.get(gid, {"issues": ["未校验"]})
        status = "✅" if not r["issues"] else "⚠ " + "；".join(r["issues"])
        lines.append(f"- {gid}：{status}")
    lines.append("")
    lines.append(f"总体结论：**{verdict}**")

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "gap_derivation.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    n_bad = sum(1 for r in results if r["issues"])
    print(f"[gap_chain] 空白={len(gaps)} 有问题={n_bad} verdict={verdict}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
