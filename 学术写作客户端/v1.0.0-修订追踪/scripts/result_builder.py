#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""result_builder — 依据 case.json 的 output_contract 构建诚实的 result.json。

用法：
  python3 result_builder.py /input/case.json /app/output/result.json \
      [--status success|partial|failed] [--set key=value ...]

契约：
  - case_id 原样保留；output_contract 的每个字段都必须出现（缺失值填 null 并
    记入 missing_fields，不得静默丢弃）。
  - status 如实：成功=success；有未解决缺口=partial；无法完成=failed。
  - uncertainty / human_confirmations 单列，绝不把未确认内容当作事实写入。
  - 任何阶段都可重复调用（幂等），先落盘部分结果再增量改进。
"""
import argparse
import json
import os
import sys
import time


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("case_json")
    ap.add_argument("result_path")
    ap.add_argument("--status", default=None)
    ap.add_argument("--set", action="append", default=[],
                    help="key=value 或 key=@file_path")
    args = ap.parse_args()

    case = load_json(args.case_json, {}) or {}
    contract = case.get("output_contract") or {}
    case_id = case.get("case_id") or case.get("id") or "unknown"

    # 读取已有 result（增量改进）
    result = load_json(args.result_path, {}) or {}
    if not isinstance(result, dict):
        result = {}

    result["case_id"] = case_id

    # 契约字段：全部出现，未知为 null
    missing = result.get("missing_fields", [])
    if isinstance(contract, dict):
        for key in contract:
            if key not in result:
                result[key] = None
                if key not in missing:
                    missing.append(key)
    result["missing_fields"] = missing

    for kv in args.set:
        if "=" not in kv:
            continue
        k, v = kv.split("=", 1)
        if v.startswith("@"):
            fp = v[1:]
            if os.path.exists(fp):
                try:
                    with open(fp, encoding="utf-8") as f:
                        v = f.read()
                except Exception:
                    pass
        # 尝试 JSON 解析
        try:
            v = json.loads(v)
        except Exception:
            pass
        result[k] = v
        if k in result.get("missing_fields", []):
            result["missing_fields"].remove(k)

    if args.status:
        result["status"] = args.status
        if "status" in result.get("missing_fields", []):
            result["missing_fields"].remove("status")
    elif "status" not in result:
        result["status"] = "partial"

    for key in ("uncertainty", "human_confirmations", "sources",
                "change_records"):
        if key not in result or not isinstance(result[key], list):
            result[key] = result.get(key) if isinstance(
                result.get(key), list) else []

    result.setdefault("generated_at_epoch", int(time.time()))
    result["schema"] = "academic-writing-client/result@v1"

    os.makedirs(os.path.dirname(os.path.abspath(args.result_path)),
                exist_ok=True)
    with open(args.result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(json.dumps({"ok": True, "result_path": args.result_path,
                      "case_id": case_id, "status": result["status"],
                      "missing_fields": result["missing_fields"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
