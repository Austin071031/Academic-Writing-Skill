#!/usr/bin/env python3
"""coverage_audit.py — V5 引用覆盖审计：关键/代表/近期工作覆盖 + 论断-引用双向绑定。

用法: python3 coverage_audit.py --work /app/work --out /app/output
读 work/ref_classification.jsonl（Agent 填写）:
  每行 {"entry_id","role":"foundation|key|representative|recent|context|other","rationale":"≥6字"}
校验:
  1) 文献库每条记录都被分类，rationale 非空（≥6字符）；
  2) 论断-引用双向绑定：被引用的 entry 每条至少绑定 1 条论断（claim_bindings.jsonl）；
     每条绑定至少含 1 个 entry（claim_type=group_overview 时要求 ≥2 个）；
  3) 覆盖建议：role ∈ {foundation,key,representative} 但未被引用 → 提示"相关工作未覆盖"；
     近期文献（年份 ≥ 库中最大年份-2）中被引用比例过低（<1/3）→ 提示近期进展覆盖不足；
  4) 元数据完整性：被引 entry 的作者/题名/年份/来源字段缺失计数。
未覆盖的关键/代表文献与近期覆盖不足写入 manual_confirmations。
渲染 coverage_report.md；verdict ∈ {pass, warn, fail}。
"""
import argparse, json, os, re, sys

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    rows.append({"_error": line[:80]})
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    lib = load_json(os.path.join(args.work, "library.json"), {}) or {}
    records = {r.get("id"): r for r in lib.get("records", []) if r.get("id")}
    bindings = [b for b in load_jsonl(os.path.join(args.work, "claim_bindings.jsonl"))
                if isinstance(b, dict) and not b.get("_error")]
    cls_rows = [r for r in load_jsonl(os.path.join(args.work, "ref_classification.jsonl"))
                if isinstance(r, dict) and not r.get("_error")]

    manual_path = os.path.join(args.work, "manual_confirmations.json")
    manual = load_json(manual_path, []) or []

    cls = {}
    cls_issues = []
    for r in cls_rows:
        e = r.get("entry_id")
        if e not in records:
            cls_issues.append({"entry_id": e, "issue": "not_in_library"})
            continue
        role = r.get("role") or ""
        if role not in ("foundation", "key", "representative", "recent", "context", "other"):
            cls_issues.append({"entry_id": e, "issue": f"role 非法: {role or '缺失'}"})
            continue
        rationale = (r.get("rationale") or "").strip()
        if len(rationale) < 6:
            cls_issues.append({"entry_id": e, "issue": "rationale 过短或缺失"})
            continue
        cls[e] = {"role": role, "rationale": rationale}
    for e in records:
        if e not in cls:
            cls_issues.append({"entry_id": e, "issue": "未分类"})

    cited_count = {e: 0 for e in records}
    naked_claims = []
    for b in bindings:
        eids = [e for e in (b.get("entry_ids") or []) if e in records]
        for e in eids:
            cited_count[e] += 1
        if not eids:
            if not (b.get("claim_type") == "transition"):
                naked_claims.append({"sentence": (b.get("sentence") or "")[:60],
                                     "loc": b.get("loc")})
        elif b.get("claim_type") == "group_overview" and len(eids) < 2:
            naked_claims.append({"sentence": (b.get("sentence") or "")[:60],
                                 "loc": b.get("loc"), "reason": "group_overview 需 ≥2 文献"})

    uncovered = []
    for e, c in cls.items():
        if c["role"] in ("foundation", "key", "representative") and cited_count.get(e, 0) == 0:
            uncovered.append({"entry_id": e, "role": c["role"], "title": (records[e].get("title") or "")[:50]})
            manual.append({"item": "coverage", "type": "key_work_not_cited",
                           "detail": f"{e}（{c['role']}）未被引言/相关工作引用，请作者确认是否应覆盖",
                           "title": records[e].get("title", "")})

    def _year(v):
        try:
            return int(str(v).strip())
        except Exception:
            return None
    years = [y for y in (_year(r.get("year")) for r in records.values()) if y]
    recent_ids = []
    if years:
        cutoff = max(years) - 2
        recent_ids = [e for e, r in records.items()
                      if (_year(r.get("year")) or 0) >= cutoff]
    recent_cited = [e for e in recent_ids if cited_count.get(e, 0) > 0]
    recent_ratio = (len(recent_cited) / len(recent_ids)) if recent_ids else 1.0
    if recent_ids and recent_ratio < 1 / 3:
        manual.append({"item": "coverage", "type": "recent_coverage_low",
                       "detail": f"近三年文献 {len(recent_ids)} 条中仅引用 {len(recent_cited)} 条，近期进展覆盖可能不足"})

    meta_missing = {}
    for e, n in cited_count.items():
        if n == 0:
            continue
        r = records[e]
        miss = [k for k in ("authors", "title", "year", "venue") if not r.get(k)]
        if miss:
            meta_missing[e] = miss

    n_cited = sum(1 for v in cited_count.values() if v > 0)
    if not records:
        verdict = "fail"
    elif cls_issues or uncovered:
        verdict = "warn"
    elif naked_claims:
        verdict = "warn"
    else:
        verdict = "pass"

    report = {"version": "v1.0.4-引用覆盖审计",
              "library_size": len(records), "cited": n_cited,
              "classification_issues": cls_issues,
              "naked_claims": naked_claims,
              "uncovered_key_works": uncovered,
              "recent": {"window": "max_year-2", "total": len(recent_ids),
                         "cited": len(recent_cited), "ratio": round(recent_ratio, 3)},
              "metadata_missing": meta_missing,
              "verdict": verdict}
    os.makedirs(args.work, exist_ok=True)
    with open(os.path.join(args.work, "version_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    if manual:
        with open(manual_path, "w", encoding="utf-8") as f:
            json.dump(manual, f, ensure_ascii=False, indent=2)

    lines = ["# 引用覆盖审计报告", "",
             f"- 文献库 {len(records)} 条；被引 {n_cited} 条；分类问题 {len(cls_issues)} 处",
             f"- 未绑定文献的论断 {len(naked_claims)} 条",
             f"- 近三年进展：{len(recent_cited)}/{len(recent_ids)} 被引（{recent_ratio:.0%}）",
             f"- 未覆盖的关键/代表/奠基工作 {len(uncovered)} 条",
             f"- 结论：**{verdict}**", ""]
    if uncovered:
        lines.append("## 未覆盖的关键工作")
        for u in uncovered:
            lines.append(f"- {u['entry_id']}（{u['role']}）{u['title']}")
        lines.append("")
    if cls_issues:
        lines.append("## 分类问题")
        for c in cls_issues[:20]:
            lines.append(f"- {c['entry_id']}: {c['issue']}")
        lines.append("")
    if naked_claims:
        lines.append("## 未绑定文献的论断")
        for c in naked_claims[:10]:
            lines.append(f"- [{c['loc']}] {c['sentence']}")
        lines.append("")
    if meta_missing:
        lines.append("## 元数据字段缺失（被引条目）")
        for e, miss in meta_missing.items():
            lines.append(f"- {e}: 缺 {', '.join(miss)}")
        lines.append("")

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "coverage_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[coverage] 库={len(records)} 被引={n_cited} 未覆盖关键={len(uncovered)} "
          f"裸论断={len(naked_claims)} 近期={len(recent_cited)}/{len(recent_ids)} verdict={verdict}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
