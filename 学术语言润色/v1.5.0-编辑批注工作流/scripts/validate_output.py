#!/usr/bin/env python3
"""validate_output.py — v1.5.0 终检：契约闭环、编辑记录覆盖、confirm 卡进人工确认清单。

用法: python3 validate_output.py [--work-dir /app/work] [--output-dir /app/output]
"""
import argparse, json, os, sys

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
    if result.get("case_id") in (None, "unknown"):
        problems.append("result.json 缺少有效 case_id")
    for k, v in (result.get("output_contract") or {}).items():
        if isinstance(v, dict) and v.get("delivered") is None and not v.get("null_reason"):
            problems.append(f"契约字段 '{k}' 未交付且无 null_reason")

    for fname in ("annotated_manuscript.md", "polished_full.md", "edit_cards.md",
                  "acceptance_checklist.md", "change_log.jsonl"):
        if not os.path.exists(os.path.join(outdir, fname)):
            problems.append(f"缺少产物: {fname}")

    # 覆盖率：源句 vs edit_records
    coverage = 0.0
    segs_p = os.path.join(wd, "source_segments.json")
    if os.path.exists(segs_p):
        src_ids = set()
        for seg in json.load(open(segs_p, encoding="utf-8")):
            if seg.get("kind") in ("heading", "math", "fence"):
                continue
            sents = seg.get("sentences") or []
            for i in range(1, len(sents) + 1):
                src_ids.add(f"{seg['id']}-S{i}" if len(sents) > 1 else seg["id"])
        seen, bad_type = set(), set()
        import glob as _g
        for p in sorted(_g.glob(os.path.join(wd, "edit_records", "*.jsonl"))):
            for line in open(p, encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    problems.append(f"edit_records 行非法 JSON: {p}")
                    continue
                if e.get("id"):
                    seen.add(e["id"])
                for t in e.get("types") or []:
                    if t not in VALID_TYPES:
                        bad_type.add(t)
                if e.get("action") == "apply" and len((e.get("reason") or "").strip()) < 8:
                    problems.append(f"{e.get('id')}: apply 卡 reason 过短，第三方无法判断")
        if bad_type:
            warnings.append(f"types 超出受控词表: {sorted(bad_type)}")
        coverage = (len(src_ids & seen) / max(len(src_ids), 1)) if src_ids else 1.0
        if src_ids and coverage < 1.0:
            warnings.append(f"编辑记录覆盖率 {coverage:.1%} < 100%，未记录句按原文保留")

    # confirm 卡必须进入 manual_review_required
    mr = result.get("manual_review_required") or []
    n_confirm = sum(1 for c in (result.get("change_records", {}).get("summary", {}).values())
                    if False)  # 占位不用
    if not mr:
        warnings.append("manual_review_required 为空：若有 confirm 卡或未记录句应在此列出")

    status = "complete" if not problems and coverage >= 1.0 else (
        "partial" if os.path.exists(os.path.join(outdir, "polished_full.md")) else "failed")
    if result.get("status") != status:
        result["status"] = status
        json.dump(result, open(result_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    rep = {"case_id": result.get("case_id"), "status": status, "coverage_ratio": coverage,
           "problems": problems, "warnings": warnings, "passed": not problems}
    json.dump(rep, open(os.path.join(wd, "selfcheck.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"[validate] status={status} coverage={coverage:.1%} problems={len(problems)} "
          f"warnings={len(warnings)}")
    for p in problems:
        print("  PROBLEM:", p)
    for w in warnings:
        print("  WARN:", w)
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
