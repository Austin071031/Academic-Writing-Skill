#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""init_result.py — 写 result.json 骨架（幂等，骨架先行）。

无命令行参数：读 INPUT/case.json（不存在则 case_id="unknown"），
写 OUTPUT/result.json。INPUT/OUTPUT 默认 /input 与 /app/output，
可用环境变量 GRANT_INPUT_DIR / GRANT_OUTPUT_DIR 覆盖（本地测试用）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu


def contract_fields(contract):
    """从 case.json 的 output_contract 抽取字段名列表。"""
    if isinstance(contract, dict):
        return list(contract.keys())
    if isinstance(contract, list):
        out = []
        for item in contract:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                for k in ("field", "name", "key", "artifact"):
                    if k in item and isinstance(item[k], str):
                        out.append(item[k])
                        break
        return out
    return []


def main():
    input_dir = gu.env_input_dir()
    output_dir = gu.env_output_dir()
    gu.ensure_dir(output_dir)

    case = gu.read_json(os.path.join(input_dir, "case.json"), None)
    case_id = "unknown"
    fields = []
    if isinstance(case, dict):
        case_id = case.get("case_id") or "unknown"
        fields = contract_fields(case.get("output_contract"))
    elif isinstance(case, list):
        # 宽容解析：list 中找第一个带 case_id 的 dict
        for item in case:
            if isinstance(item, dict) and item.get("case_id"):
                case_id = item["case_id"]
                fields = contract_fields(item.get("output_contract"))
                break

    result = {
        "case_id": case_id,
        "status": "initialized",
        "skill": None,
        "outputs": {},
        "evidence_map": [],
        "change_log": [],
        "uncertainty": {"placeholder": "待后续阶段回填"},
        "manual_confirmations": [],
        "exceptions": [],
        "stats": {},
    }
    if fields:
        result["output_contract"] = {k: None for k in fields}

    out_path = os.path.join(output_dir, "result.json")
    gu.write_json(out_path, result)
    print(f"[init_result] wrote {out_path} (case_id={case_id}, "
          f"contract_fields={len(fields)})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        # init 阶段无 work 目录可用，尽力而为地把异常写到输出目录
        try:
            gu.record_exception(os.path.join(gu.env_output_dir(), "work"),
                                "init_result", "case.json", e, "写空骨架后退出 1")
        except Exception:
            pass
        print(f"[init_result] ERROR: {e}")
        raise SystemExit(1)
