#!/usr/bin/env python3
"""build_ledger.py — 数值台账(evidence ledger)格式校验器。

用法:
  python3 build_ledger.py evidence_ledger.json

校验:
  - 顶层为 list 或含 "entries" 的 dict
  - 每条必填: source(图/表/统计输出来源), quantity(物理量), value(数值)
  - 可选: id, panel, unit, error{type,value}, n, stat{...}, quote, confidence
  - confidence ∈ {high, medium, low}
退出码: 0 = 通过; 1 = 存在错误; 2 = 文件/JSON 错误。
仅依赖 Python 3 标准库。
"""
import json
import sys

REQUIRED = ["source", "quantity", "value"]
OPTIONAL = ["id", "panel", "unit", "error", "n", "stat", "quote", "confidence"]
CONFIDENCE = {"high", "medium", "low"}
ERR_TYPES = {"SD", "SEM", "CI95", "IQR", "range", "unknown"}


def check(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"FATAL: 无法读取台账: {e}", file=sys.stderr)
        return 2
    entries = raw.get("entries") if isinstance(raw, dict) else raw
    if not isinstance(entries, list) or not entries:
        print("ERROR: 台账为空或格式错误（应为非空 list 或 {'entries': [...]}）")
        return 1
    errors = 0
    ids = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            print(f"ERROR [{i}]: 条目不是 dict")
            errors += 1
            continue
        for k in REQUIRED:
            if k not in e or e[k] in (None, ""):
                print(f"ERROR [{i}]: 缺少必填字段 {k}")
                errors += 1
        for k in e:
            if k not in REQUIRED + OPTIONAL:
                print(f"WARN  [{i}]: 未知字段 {k}")
        if "value" in e:
            try:
                float(e["value"])
            except (TypeError, ValueError):
                print(f"ERROR [{i}]: value 不是数值: {e['value']!r}")
                errors += 1
        if "confidence" in e and e["confidence"] not in CONFIDENCE:
            print(f"ERROR [{i}]: confidence 应为 {sorted(CONFIDENCE)} 之一")
            errors += 1
        err = e.get("error")
        if err is not None:
            if not isinstance(err, dict) or "value" not in err:
                print(f"ERROR [{i}]: error 应为 {{'type': ..., 'value': ...}}")
                errors += 1
            elif err.get("type", "unknown") not in ERR_TYPES:
                print(f"WARN  [{i}]: error.type 建议为 {sorted(ERR_TYPES)}")
        if "id" in e:
            if e["id"] in ids:
                print(f"ERROR [{i}]: id 重复: {e['id']}")
                errors += 1
            ids.add(e["id"])
    print(f"CHECKED {len(entries)} entries, {errors} error(s)")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(check(sys.argv[1]))
