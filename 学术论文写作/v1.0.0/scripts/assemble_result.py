#!/usr/bin/env python3
"""assemble_result.py — 按 case.json output_contract 逐字段组装 /app/output/result.json。

规则：
- 先照抄 output_contract 全部字段名，一个不漏；case_id 必含。
- 已知语义字段映射到真实产物；未知字段填结构化产物指针（不空、不造假）。
- status：manuscript 存在且一致性 PASS/WARN → success；manuscript 存在但 FAIL → partial；
  manuscript 缺失 → failed。一切如实，占位符与 FAIL 项自动进 uncertainty。
"""
import argparse, json, os, sys, datetime

FIELD_HINTS = [
    (r"^case_?id$", "case_id"),
    (r"^status$|状态", "status"),
    (r"manuscript|稿件|文稿|editable|draft|document|产物|deliverable|paper|target", "manuscript"),
    (r"evidence|证据|source|来源|溯源|provenance|map|映射|claim", "evidence"),
    (r"uncertaint|不确定|待确认|limit|边界|gap|缺口|exception|异常", "uncertainty"),
    (r"change|修改|留痕|diff|version|版本|log|记录", "change_log"),
    (r"consisten|一致|check|核验|quality|qa", "consistency"),
    (r"preview|预览|render|pdf|png|export|导出", "preview"),
    (r"summary|摘要|note|说明|备注", "summary"),
]

def load(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()
    out = args.out

    brief = load(os.path.join(args.work, "brief.json"), {}) or {}
    case_id = brief.get("case_id", "UNKNOWN-CASE")
    contract = brief.get("output_contract", []) or []
    consistency = load(os.path.join(out, "consistency_report.json"), {}) or {}
    preview = load(os.path.join(out, "preview_manifest.json"), {}) or {}
    evidence = load(os.path.join(args.work, "evidence_map.json"), None)
    biblio = load(os.path.join(args.work, "bibliography.json"), []) or []
    facts = load(os.path.join(args.work, "facts.json"), []) or []

    ms_path = os.path.join(out, "manuscript.md")
    ms_exists = os.path.isfile(ms_path) and os.path.getsize(ms_path) > 0
    verdict = consistency.get("verdict", "FAIL")
    if ms_exists and verdict in ("PASS", "WARN"):
        status = "success"
    elif ms_exists:
        status = "partial"
    else:
        status = "failed"

    artifacts = {}
    for fn in sorted(os.listdir(out)):
        p = os.path.join(out, fn)
        if os.path.isfile(p):
            artifacts[fn] = {"path": f"/app/output/{fn}", "bytes": os.path.getsize(p)}
    pngs = []
    pdir = os.path.join(out, "preview")
    if os.path.isdir(pdir):
        pngs = [f"/app/output/preview/{fn}" for fn in sorted(os.listdir(pdir)) if fn.endswith(".png")]

    uncertainty = list(consistency.get("warn_summary", []))
    placeholders = (consistency.get("checks", {}).get("placeholders", {}) or {}).get("items", [])
    for ph in placeholders:
        if not any(ph in u for u in uncertainty):
            uncertainty.append(f"待确认: {ph}")
    for it in (consistency.get("checks", {}).get("ref_fields", {}) or {}).get("warnings", []):
        uncertainty.append(it)
    if verdict == "FAIL":
        uncertainty = [f"一致性核验未通过: {x}" for x in consistency.get("fail_summary", [])] + uncertainty
    for step, info in (preview.get("steps", {}) or {}).items():
        if info.get("status") == "unavailable":
            uncertainty.append(f"预览产物 {step} 不可用: {info.get('reason', '')[:120]}")
    for iss in brief.get("issues", []):
        uncertainty.append(f"输入问题: {iss}")
    # 去重保序
    seen, uncertainty_d = set(), []
    for u in uncertainty:
        if u not in seen:
            seen.add(u); uncertainty_d.append(u)

    change_log = []
    cl_path = os.path.join(out, "change_log.md")
    if os.path.isfile(cl_path):
        change_log = [l.strip("- ").rstrip() for l in open(cl_path, encoding="utf-8", errors="replace")
                      if l.strip().startswith("- ")][:200]

    deliverables = {
        "manuscript_md": "/app/output/manuscript.md" if ms_exists else None,
        "manuscript_docx": "/app/output/manuscript.docx" if os.path.isfile(os.path.join(out, "manuscript.docx")) else None,
        "manuscript_pdf": "/app/output/manuscript.pdf" if os.path.isfile(os.path.join(out, "manuscript.pdf")) else None,
        "preview_png": pngs,
        "evidence_map": "/app/output/evidence_map.md" if os.path.isfile(os.path.join(out, "evidence_map.md")) else None,
        "consistency_report": "/app/output/consistency_report.md",
        "change_log": "/app/output/change_log.md" if os.path.isfile(cl_path) else None,
    }
    deliverables = {k: v for k, v in deliverables.items() if v}

    sources = {
        "materials_index": "/app/work/material_index.json",
        "facts_count": len(facts),
        "bibliography_count": len(biblio),
        "evidence_map_entries": len(evidence) if isinstance(evidence, list) else (
            len(evidence.get("entries", [])) if isinstance(evidence, dict) else 0),
        "note": "每条事实/数字/引用的锚点见 /app/output/evidence_map.md 与 /app/work/facts.json",
    }

    summary = (f"case {case_id}: manuscript={'ok' if ms_exists else 'missing'}, "
               f"consistency={verdict}, status={status}; "
               f"产物 {len(deliverables)} 项；待确认 {len(uncertainty_d)} 项")

    def fill(kind):
        return {
            "case_id": case_id,
            "status": status,
            "manuscript": deliverables,
            "evidence": {"evidence_map": deliverables.get("evidence_map"),
                         "facts_count": len(facts), "bibliography_count": len(biblio),
                         "detail": sources["note"]},
            "uncertainty": uncertainty_d,
            "change_log": change_log or "见 /app/output/change_log.md",
            "consistency": {"verdict": verdict,
                            "report": "/app/output/consistency_report.md",
                            "fails": consistency.get("fail_summary", [])},
            "preview": {"pdf": deliverables.get("manuscript_pdf"), "png": pngs,
                        "steps": {k: v.get("status") for k, v in (preview.get("steps", {}) or {}).items()}},
            "summary": summary,
        }[kind]

    result = {
        "case_id": case_id,
        "status": status,
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "deliverables": deliverables,
        "sources": sources,
        "consistency_verdict": verdict,
        "uncertainty": uncertainty_d,
        "change_log": change_log,
        "run_log": "/app/output/run_log.md",
        "stage": "final",
    }
    for field in contract:
        if field in result:
            continue
        kind = "summary"
        for pat, k in FIELD_HINTS:
            import re as _re
            if _re.search(pat, field, _re.I):
                kind = k; break
        result[field] = fill(kind)

    rj = os.path.join(out, "result.json")
    with open(rj, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    try:
        with open(os.path.join(out, "run_log.md"), "a", encoding="utf-8") as f:
            f.write(f"\n## assemble_result {result['generated_utc']} status={status} "
                    f"contract_fields={len(contract)} uncertainty={len(uncertainty_d)}\n")
    except Exception:
        pass
    print(json.dumps({"ok": True, "status": status, "verdict": verdict,
                      "contract_fields": len(contract)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
