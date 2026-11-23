#!/usr/bin/env python3
"""init_result.py — 尽早生成 /app/output/result.json 诚实骨架（部分结果也有有效交付物）。

用法: python3 init_result.py [--work-dir /app/work] [--output-dir /app/output]

保留 case_id 与 output_contract 全部原始键；未完成的字段以 null_reason 如实标注，
Agent 后续用 assemble.py 填充。
"""
import argparse, datetime, json, os, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", default="/app/work")
    ap.add_argument("--output-dir", default="/app/output")
    args = ap.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    brief_p = os.path.join(args.work_dir, "brief.json")
    brief = json.load(open(brief_p, encoding="utf-8")) if os.path.exists(brief_p) else {}
    contract = brief.get("output_contract") or {}
    if isinstance(contract, dict):
        oc = {k: {"spec": v, "delivered": None, "null_reason": "处理中，尚未填充"}
              for k, v in contract.items()}
    elif isinstance(contract, list):
        oc = {k: {"spec": None, "delivered": None, "null_reason": "处理中，尚未填充"}
              for k in contract}
    else:
        oc = {}

    result = {
        "case_id": brief.get("case_id", "unknown"),
        "status": "in_progress",
        "generated_by": "academic-language-polisher (weekly-skill)",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "output_contract": oc,
        "artifacts": {},
        "change_records": {"change_log_jsonl": None, "change_log_md": None,
                           "summary": {"sentences_total": None, "modified": None,
                                       "kept": None, "by_type": {}}},
        "sources": [m.get("rel_path") for m in brief.get("material_files", [])],
        "assumptions": [],
        "uncertainty": list(brief.get("issues", [])),
        "manual_review_required": [],
        "runtime": {"model_requests_used": None, "notes": "由 SKILL.md 流程驱动，脚本调用见 /app/work"},
    }
    out = os.path.join(args.output_dir, "result.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[init_result] skeleton -> {out} (contract keys: {list(oc)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
