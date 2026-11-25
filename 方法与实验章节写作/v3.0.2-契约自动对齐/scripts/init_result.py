#!/usr/bin/env python3
"""init_result.py — 尽早落盘诚实的 result.json 骨架，防止超时空手。

用法: python3 init_result.py [--case /input/case.json] [--out /app/output]
只依赖标准库。幂等：重复运行保留已写入的非骨架结果。
"""
import argparse, json, os, sys, datetime

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default=os.environ.get("WORK_DIR", "/app/work"))
    args = ap.parse_args()

    case_id = None
    contract = []
    if os.path.exists(args.case):
        try:
            with open(args.case, encoding="utf-8") as f:
                case = json.load(f)
            case_id = case.get("case_id") or case.get("id") or case.get("caseId")
            oc = case.get("output_contract") or case.get("outputContract") or {}
            if isinstance(oc, dict):
                contract = list(oc.keys())
            elif isinstance(oc, list):
                contract = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in oc]
        except Exception as e:
            print(f"[init_result] case.json 解析失败（将仅记录异常）: {e}", file=sys.stderr)

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "result.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
            if old.get("status") not in (None, "running"):
                print(f"[init_result] 已有 status={old.get('status')}，保留不覆盖")
                return 0
        except Exception:
            pass

    result = {
        "case_id": case_id or "unknown",
        "status": "running",
        "skill": None,
        "task_summary": None,
        "outputs": {},
        "evidence_map": [],
        "change_log": [],
        "uncertainty": [],
        "manual_confirmations": [],
        "exceptions": [],
        "stats": {},
        "sources": {},
        "output_contract_fields": contract,
        "initialized_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "note": "骨架结果：Skill 正在运行，完成后由 build_deliverables.py 重写。",
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[init_result] 骨架已写入 {path} (case_id={case_id}, contract_fields={len(contract)})")

    # v3.0.2：契约自动推导——按 output_contract 字段名生成 contract_extra 草稿，
    # 供 build_deliverables.py 合并（Agent 手写 contract_extra.json 时优先）
    if contract:
        draft = {}
        for f in contract:
            fl = str(f).lower()
            if any(k in fl for k in ("chapter", "draft", "document", "section", "manuscript", "md")):
                draft[f] = "methods_chapter.md"
            elif any(k in fl for k in ("verif", "audit", "report", "check")):
                draft[f] = "build_report.json"
            elif any(k in fl for k in ("evidence", "source", "provenance", "map")):
                draft[f] = "provenance_map.json"
            else:
                draft[f] = "result.json"  # 兜底：字段在 result.json 内由 status.json 提供
        work = args.work
        try:
            os.makedirs(work, exist_ok=True)
            with open(os.path.join(work, "contract_extra_draft.json"), "w", encoding="utf-8") as f2:
                json.dump(draft, f2, ensure_ascii=False, indent=2)
            print(f"[init_result] 契约草稿已写入 {work}/contract_extra_draft.json（{len(draft)} 字段）")
        except Exception as e:
            print(f"[init_result][WARN] 契约草稿写入失败: {e}")

if __name__ == "__main__":
    sys.exit(main())
