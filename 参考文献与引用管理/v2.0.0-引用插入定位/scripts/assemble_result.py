#!/usr/bin/env python3
"""assemble_result.py — 汇总各阶段产物，生成 /app/output/result.json 与交付文件清单。

用法: python3 assemble_result.py --work /app/work --out /app/output \
        --skill "name vX.Y.Z" --status success|partial|failed [--field k=v ...]
读取 work/ 下的 inspection.json / evidence_map.json / change_log.json / uncertainty.json /
report.md 等（缺则留空），并保留 case.json output_contract 字段的映射。
"""
import argparse, json, os, sys, datetime, glob

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
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--skill", required=True)
    ap.add_argument("--status", default="partial",
                    choices=["success", "partial", "failed", "running"])
    ap.add_argument("--field", action="append", default=[], help="额外字段 k=json 或 k=str")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    insp = load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    evidence = load_json(os.path.join(args.work, "evidence_map.json"), []) or []
    changes = load_json(os.path.join(args.work, "change_log.json"), []) or []
    uncertainty = load_json(os.path.join(args.work, "uncertainty.json"), []) or []
    manual = load_json(os.path.join(args.work, "manual_confirmations.json"), []) or []
    exceptions = load_json(os.path.join(args.work, "exceptions.json"), []) or []
    stats = load_json(os.path.join(args.work, "stats.json"), {}) or {}
    task_summary = None
    if insp.get("task_head"):
        task_summary = insp["task_head"][:400]

    # 输出产物清单（相对 /app/output）
    outputs = {}
    for name in ("edited_manuscript.md", "references.md", "report.md", "verification_report.json",
                 "dedup_report.md", "merge_report.md", "renumber_report.md", "consistency_audit.json",
                 "citation_decisions.jsonl", "library_deduped.json", "converted_refs.txt",
                 "evidence_map.json", "change_log.md"):
        p = os.path.join(args.out, name)
        if os.path.exists(p):
            key = name.rsplit(".", 1)[0]
            outputs[key] = name

    result = {
        "case_id": insp.get("case_id") or "unknown",
        "status": args.status,
        "skill": args.skill,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "task_summary": task_summary,
        "outputs": outputs,
        "evidence_map": evidence,
        "change_log": changes,
        "uncertainty": uncertainty,
        "manual_confirmations": manual,
        "exceptions": exceptions,
        "stats": stats,
        "sources": {"inspection": "work/inspection.json", "library": "work/library.json",
                    "manuscript": "work/manuscript.json"},
    }

    # output_contract 字段回填：若 case.json 声明了输出契约，逐项保证存在
    contract_names = []
    oc = {}
    if os.path.exists(args.case):
        case = load_json(args.case, {}) or {}
        oc = case.get("output_contract") or case.get("outputContract") or {}
        if isinstance(oc, dict):
            contract_names = list(oc.keys())
        elif isinstance(oc, list):
            contract_names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in oc]
    alias = {"result": "outputs", "deliverables": "outputs", "main_output": "outputs",
             "evidence": "evidence_map", "sources": "sources", "changes": "change_log",
             "uncertainties": "uncertainty", "verification": "outputs"}
    for name in contract_names:
        if name in result:
            continue
        tgt = alias.get(name)
        result[name] = result.get(tgt) if tgt else None
    if contract_names:
        result["output_contract_fields"] = contract_names

    for kv in args.field:
        k, _, v = kv.partition("=")
        try:
            result[k] = json.loads(v)
        except Exception:
            result[k] = v

    path = os.path.join(args.out, "result.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[assemble] status={args.status} outputs={list(outputs)} -> {path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
