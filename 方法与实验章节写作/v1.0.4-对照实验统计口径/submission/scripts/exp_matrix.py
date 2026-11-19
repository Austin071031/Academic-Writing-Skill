#!/usr/bin/env python3
"""exp_matrix.py — 实验矩阵与可比性闸门（v1.0.4 方向核心引擎）。

对 work/experiment_matrix.json 中的实验行（变体×数据集×划分×指标×预算×种子×重复×结果）检查：
1. 至少一行基线；2. 全部行共享数据集/划分/指标，否则须注明可比性豁免理由；
3. 对照须同预算或注明差异；4. 重复次数>1 时须给均值与离散度，=1 时须标注单次运行口径；
5. 章节"5 对照实验"小节须引用每个实验行编号（R#）。
用法: python3 exp_matrix.py --work /app/work --out /app/output
输出: comparability_report.json {rows, issues:[...], verdict}
"""
import argparse, json, os, re, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    mp = os.path.join(args.work, "experiment_matrix.json")
    rows = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else []
    issues = []
    if not rows:
        issues.append({"kind": "empty_matrix", "note": "experiment_matrix.json 为空或无此文件"})
    baselines = [r for r in rows if r.get("is_baseline")]
    if rows and not baselines:
        issues.append({"kind": "no_baseline", "note": "未登记任何基线行"})

    def key(r, k):
        return str(r.get(k, "")).strip()

    for field in ("dataset", "split", "metric"):
        vals = {key(r, field) for r in rows if key(r, field)}
        if len(vals) > 1:
            for r in rows:
                if not r.get(f"{field}_waiver"):
                    issues.append({"kind": f"mixed_{field}", "row": r.get("rid"),
                                   "value": key(r, field), "note": f"{field} 不一致且无豁免理由"})
    for r in rows:
        if r.get("is_baseline") and rows:
            main_budget = key([x for x in rows if not x.get("is_baseline")][0] if [x for x in rows if not x.get("is_baseline")] else r, "budget")
            if key(r, "budget") and main_budget and key(r, "budget") != main_budget and not r.get("budget_waiver"):
                issues.append({"kind": "budget_mismatch", "row": r.get("rid"),
                               "note": f"基线预算 {key(r,'budget')} ≠ 主实验预算 {main_budget}，未注明理由"})
        reps = r.get("repeats", 1)
        try:
            reps = int(reps)
        except (TypeError, ValueError):
            reps = 1
        if reps > 1 and not (r.get("mean") and (r.get("std") or r.get("ci") or r.get("sem"))):
            issues.append({"kind": "missing_stats", "row": r.get("rid"),
                           "note": "repeats>1 但缺 mean 与离散度(std/ci/sem)"})
        if reps <= 1 and not r.get("single_run_note"):
            issues.append({"kind": "single_run_no_note", "row": r.get("rid"),
                           "note": "单次运行须标注口径（如单次种子结果，未做显著性检验）"})

    chap_path = os.path.join(args.work, "sections", "05_baselines.md")
    chap = open(chap_path, encoding="utf-8").read() if os.path.exists(chap_path) else ""
    absent = [r.get("rid") for r in rows if r.get("rid") and str(r.get("rid")) not in chap]
    for a in absent:
        issues.append({"kind": "row_not_cited", "row": a, "note": "实验行未在'5 对照实验'小节被引用"})

    verdict = "pass" if not issues else "fail"
    report = {"rows": len(rows), "baselines": len(baselines), "issues": issues, "verdict": verdict}
    rp = os.path.join(args.out, "comparability_report.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[exp] 行 {len(rows)} 基线 {len(baselines)} 问题 {len(issues)} verdict={verdict} -> {rp}")
    sys.exit(0 if verdict == "pass" else 1)

if __name__ == "__main__":
    sys.exit(main())
