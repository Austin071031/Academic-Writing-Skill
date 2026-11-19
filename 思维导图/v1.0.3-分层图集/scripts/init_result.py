#!/usr/bin/env python3
"""init_result.py — 尽早落盘诚实的 result.json 骨架，防止超时空手。

用法: python3 init_result.py [--case /input/case.json] [--out /app/output]
只依赖标准库。幂等：重复运行保留已写入的 status（若已存在且非 running）。
"""
import argparse, json, os, sys, datetime

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--out", default="/app/output")
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
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "outputs": {},
        "evidence_map": [],
        "change_log": [],
        "uncertainty": [],
        "manual_confirmations": [],
        "exceptions": [],
        "notes": "骨架文件：任务开始时落盘，结束时由 assemble_result.py 汇总覆盖。",
    }
    for name in contract:
        result.setdefault(name, None)
    if contract:
        result["output_contract_fields"] = contract

    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[init_result] 骨架 result.json 已写入 {path} (case_id={result['case_id']})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
