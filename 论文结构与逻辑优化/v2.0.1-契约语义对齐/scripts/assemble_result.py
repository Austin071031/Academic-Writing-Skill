#!/usr/bin/env python3
"""assemble_result.py — 汇总各阶段产物，生成 /app/output/result.json。

用法: python3 assemble_result.py --work /app/work --out /app/output \
        --skill "name vX.Y.Z" --status success|partial|failed [--field k=json ...]
自动把 work/ 下的关键产物复制到 /app/output（若 Agent 尚未复制），
读取 case.json 的 output_contract 并逐项保证字段存在。
"""
import argparse, json, os, sys, datetime, shutil

ARTIFACTS = ["diagnosis_report.md", "edit_plan.json", "findings.json",
             "rq_map.json", "section_map.json", "chain_audit.json",
             "redundancy_report.json", "boundary_audit.json",
             "annotated_manuscript.md", "restructured_outline.md"]

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
    # work → out 产物兜底复制
    for name in ARTIFACTS:
        src = os.path.join(args.work, name)
        dst = os.path.join(args.out, name)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copyfile(src, dst)

    insp = load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    evidence = load_json(os.path.join(args.work, "evidence_map.json"), []) or []
    changes = load_json(os.path.join(args.work, "change_log.json"), []) or []
    uncertainty = load_json(os.path.join(args.work, "uncertainty.json"), []) or []
    manual = load_json(os.path.join(args.work, "manual_confirmations.json"), []) or []
    exceptions = load_json(os.path.join(args.work, "exceptions.json"), []) or []
    stats = load_json(os.path.join(args.work, "stats.json"), {}) or {}

    outputs = {}
    for name in ARTIFACTS + ["evidence_map.json"]:
        p = os.path.join(args.out, name)
        if os.path.exists(p) and os.path.getsize(p) > 0:
            outputs[name.rsplit(".", 1)[0]] = name
    if os.path.exists(os.path.join(args.work, "evidence_map.json")) and "evidence_map" not in outputs:
        shutil.copyfile(os.path.join(args.work, "evidence_map.json"),
                        os.path.join(args.out, "evidence_map.json"))
        outputs["evidence_map"] = "evidence_map.json"

    result = {
        "case_id": insp.get("case_id") or "unknown",
        "status": args.status,
        "skill": args.skill,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "task_summary": (insp.get("task_head") or "")[:400] or None,
        "outputs": outputs,
        "evidence_map": evidence,
        "change_log": changes,
        "uncertainty": uncertainty,
        "manual_confirmations": manual,
        "exceptions": exceptions,
        "stats": stats,
        "sources": {"inspection": "work/inspection.json", "structure": "work/structure.json",
                    "findings_scan": "work/findings_scan.json",
                    "findings_engine": "work/findings_engine.json"},
    }

    contract_names = []
    if os.path.exists(args.case):
        case = load_json(args.case, {}) or {}
        oc = case.get("output_contract") or case.get("outputContract") or {}
        if isinstance(oc, dict):
            contract_names = list(oc.keys())
        elif isinstance(oc, list):
            contract_names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in oc]

    # v2.0.1 单点改动：契约逐字段语义对齐回填（优先读 contract_check 产物）
    cmap = load_json(os.path.join(args.work, "contract_map.json"), None)
    cmap_fields = {}
    if isinstance(cmap, dict):
        for f in cmap.get("fields") or []:
            if isinstance(f, dict) and f.get("field"):
                cmap_fields[f["field"]] = f
    alias = {"result": "outputs", "deliverables": "outputs", "main_output": "outputs",
             "report": "outputs", "evidence": "evidence_map", "sources": "sources",
             "changes": "change_log", "uncertainties": "uncertainty",
             "verification": "outputs", "findings": "outputs"}
    for name in contract_names:
        if name in result and result[name]:
            continue
        f = cmap_fields.get(name)
        if f is not None:
            # 语义对齐结构：{"artifact", "summary", "coverage"}
            cov = f.get("coverage") or "missing"
            if cov == "missing":
                need = f.get("required_content") or "所需内容未说明"
                result[name] = {"artifact": None,
                                "summary": f"未产出对应内容：{need}",
                                "coverage": "missing"}
                uncertainty.append({"item": f"output_contract.{name}",
                                    "note": result[name]["summary"]})
                result["uncertainty"] = uncertainty
            else:
                result[name] = {"artifact": f.get("mapped_artifact"),
                                "summary": f.get("artifact_summary") or f.get("justification") or "",
                                "coverage": cov}
        else:
            # 无 contract_map.json 时回退原 alias 逻辑（保持兼容）
            tgt = alias.get(name)
            result[name] = result.get(tgt) if tgt else result.get("outputs")
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
    print(f"[assemble] status={args.status} outputs={list(outputs)} 契约字段={contract_names}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
