#!/usr/bin/env python3
"""validate_output.py — 终检：result.json 契约字段、修改清单完备性、守恒检查闭环。

用法: python3 validate_output.py [--work-dir /app/work] [--output-dir /app/output]

返回码: 0 通过 / 1 发现问题（selfcheck.json 仍写出，问题分为 problems 与 warnings）。
status 规则: 覆盖率 <100% 或 critical 未处置 → partial；产物缺失/契约未交付 → 保持并注明。
"""
import argparse, json, os, sys

REQUIRED_LOG_FIELDS = ("id", "original", "polished", "decision", "reason")
VALID_TYPES = {"grammar", "syntax", "collocation", "punctuation", "spelling", "long-sentence",
               "terminology", "abbreviation", "register", "redundancy", "logic", "clarity",
               "hedging", "formatting", "other"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", default="/app/work")
    ap.add_argument("--output-dir", default="/app/output")
    args = ap.parse_args()
    wd, outdir = args.work_dir, args.output_dir
    problems, warnings = [], []

    result_p = os.path.join(outdir, "result.json")
    if not os.path.exists(result_p):
        problems.append("result.json 不存在")
        result = {}
    else:
        try:
            result = json.load(open(result_p, encoding="utf-8"))
        except Exception as e:
            problems.append(f"result.json 解析失败: {e}")
            result = {}

    brief_p = os.path.join(wd, "brief.json")
    brief = json.load(open(brief_p, encoding="utf-8")) if os.path.exists(brief_p) else {}

    if result.get("case_id") in (None, "unknown"):
        problems.append("result.json 缺少有效 case_id")

    # 1) output_contract 全部键已交付或注明 null_reason
    oc = result.get("output_contract") or {}
    for k, v in oc.items():
        if not isinstance(v, dict):
            continue
        if v.get("delivered") is None and not v.get("null_reason"):
            problems.append(f"契约字段 '{k}' 未交付且无 null_reason")
        ap_ = v.get("artifact_path") or v.get("delivered")
        if v.get("delivered") is not None and isinstance(ap_, str):
            cands = [ap_] if os.path.isabs(ap_) else [os.path.join(outdir, ap_),
                                                      os.path.join(outdir, os.path.basename(ap_))]
            if not any(os.path.exists(c) for c in cands):
                warnings.append(f"契约字段 '{k}' 指向的产物不存在: {ap_}")

    # 2) 核心产物
    for fname, label in (("polished_full.md", "润色后全文"),
                         ("change_log.jsonl", "逐句修改清单"),
                         ("change_log.md", "修改清单可读版"),
                         ("review_report.md", "审校报告")):
        if not os.path.exists(os.path.join(outdir, fname)):
            problems.append(f"缺少产物: {fname}（{label}）")
    if not os.path.exists(os.path.join(wd, "term_table.csv")):
        warnings.append("术语表缺失（terminology.py build 未运行或被跳过）")

    # 3) change log 结构完备
    log_p = os.path.join(outdir, "change_log.jsonl")
    n_log = 0
    if os.path.exists(log_p):
        bad_type = set()
        for ln, line in enumerate(open(log_p, encoding="utf-8"), 1):
            line = line.strip()
            if not line:
                continue
            n_log += 1
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                problems.append(f"change_log.jsonl 第 {ln} 行非法 JSON")
                continue
            for fld in REQUIRED_LOG_FIELDS:
                if fld not in e:
                    problems.append(f"change_log 第 {ln} 行缺字段 {fld}")
            for t in e.get("types") or []:
                if t not in VALID_TYPES:
                    bad_type.add(t)
            if e.get("decision") == "modify" and not e.get("types"):
                warnings.append(f"{e.get('id')}: modify 但 types 为空")
            if e.get("decision") == "modify" and not (e.get("reason") or "").strip():
                problems.append(f"{e.get('id')}: modify 但无理由（第三方无法判断该不该改）")
        if bad_type:
            warnings.append(f"出现受控词表之外的修改类型: {sorted(bad_type)}")

    # 4) 覆盖与守恒闭环
    guard_p = os.path.join(wd, "guard_report.json")
    if not os.path.exists(guard_p):
        problems.append("guard_report.json 缺失（guard_check.py 未运行）")
        coverage, crit = 0.0, None
    else:
        guard = json.load(open(guard_p, encoding="utf-8"))
        coverage = guard.get("coverage_ratio") or 0.0
        crit_flags = [x for x in guard.get("flags", []) if x.get("level") == "critical"]
        resolutions = set()
        res_p = os.path.join(wd, "resolutions.jsonl")
        if os.path.exists(res_p):
            for line in open(res_p, encoding="utf-8"):
                line = line.strip()
                if line:
                    try:
                        r = json.loads(line)
                        resolutions.add((r.get("flag_id"), r.get("kind")))
                    except json.JSONDecodeError:
                        pass
        unresolved = [x for x in crit_flags if (x.get("id"), x["kind"]) not in resolutions]
        crit = len(unresolved)
        if unresolved:
            problems.append(f"{crit} 条 critical 标记未处置: "
                            + "; ".join(f"{x['kind']}@{x.get('id')}" for x in unresolved[:8]))
        if coverage < 1.0:
            warnings.append(f"句子覆盖率 {coverage:.1%} < 100%，未覆盖句子按原文保留并需人工确认")

    # 5) status 判定
    status = result.get("status", "")
    if problems:
        new_status = "partial" if any(os.path.exists(os.path.join(outdir, f))
                                      for f in ("polished_full.md", "change_log.jsonl")) else "failed"
    elif coverage < 1.0:
        new_status = "partial"
    else:
        new_status = "complete"
    if status != new_status:
        result["status"] = new_status
        json.dump(result, open(result_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    report = {"case_id": result.get("case_id"), "status": new_status,
              "contract_keys": len(oc), "log_entries": n_log,
              "coverage_ratio": coverage, "problems": problems, "warnings": warnings,
              "passed": not problems}
    with open(os.path.join(wd, "selfcheck.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[validate] status={new_status} log={n_log} coverage={coverage:.1%} "
          f"problems={len(problems)} warnings={len(warnings)}")
    for p in problems:
        print("  PROBLEM:", p)
    for w in warnings:
        print("  WARN:", w)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
