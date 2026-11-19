#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_output.py --out O --work W

发布闸门：逐项检查并打印 PASS/FAIL；任一 FAIL exit 1。
检查项：result.json 合法且含 case_id/status；draft/mapping/report 存在
非空（status=failed 除外）；evidence_map 非空；骨架占位 uncertainty 已清。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    work, out = args.work, gu.env_output_dir(args.out)

    results = []
    result = gu.read_json(os.path.join(out, "result.json"), None)
    results.append(("result.json 存在且为合法 JSON", result is not None))
    if not result:
        result = {}
    results.append(("result.json 含 case_id",
                    bool(result.get("case_id"))))
    results.append(("result.json 含 status ∈ success/partial/failed",
                    result.get("status") in ("success", "partial", "failed")))

    failed = result.get("status") == "failed"
    for name in ("proposal_draft.md", "element_mapping.md", "report.md"):
        if failed:
            results.append((f"{name} 存在（status=failed 时豁免）", True))
            continue
        path = os.path.join(out, name)
        ok = os.path.isfile(path) and os.path.getsize(path) > 0
        results.append((f"{name} 存在且非空", ok))

    ev = result.get("evidence_map")
    results.append(("evidence_map 非空",
                    isinstance(ev, list) and len(ev) > 0))

    unc = result.get("uncertainty")
    placeholder = isinstance(unc, dict) and (
        "placeholder" in unc or "待补充" in str(unc.get("placeholder", ""))
        or "TBD" in str(unc) or "TODO" in str(unc))
    results.append(("骨架占位 uncertainty 已清（无 placeholder/TBD）",
                    not placeholder))

    all_ok = True
    for name, ok in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        all_ok = all_ok and ok
    print(f"[validate_output] {'ALL PASS' if all_ok else 'FAILED'} "
          f"({sum(1 for _, ok in results if ok)}/{len(results)})")
    return 0 if all_ok else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[validate_output] ERROR: {e}")
        raise SystemExit(1)
