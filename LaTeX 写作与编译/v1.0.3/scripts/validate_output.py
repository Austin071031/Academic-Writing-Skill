#!/usr/bin/env python3
"""validate_output.py — 交付闸门：核对 /app/output 是否满足运行时契约。

用法: python3 validate_output.py [--out /app/output] [--case /input/case.json]
检查项:
  1. result.json 存在且为合法 JSON；
  2. 含 case_id（与 case.json 一致，若可得）；
  3. output_contract 全部字段在顶层存在；
  4. status ∈ {success, partial, failed}，failed 时必须有 exceptions 说明；
  5. 至少存在一个可编辑交付物（latex_project/*.tex 或 outputs 非空）；
  6. status=success 但 build.success=false 时给出矛盾警告（不阻断）。
退出码 0=通过，1=未通过（打印缺口清单）。
"""
import argparse, json, os, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--case", default="/input/case.json")
    args = ap.parse_args()

    problems, warnings = [], []
    rp = os.path.join(args.out, "result.json")
    if not os.path.exists(rp):
        print("[validate] FAIL: result.json 不存在")
        return 1
    try:
        with open(rp, encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        print(f"[validate] FAIL: result.json 非法 JSON: {e}")
        return 1

    cid = result.get("case_id")
    if not cid or cid == "unknown":
        problems.append("case_id 缺失或为 unknown")
    if os.path.exists(args.case):
        try:
            case = json.load(open(args.case, encoding="utf-8"))
            real = case.get("case_id") or case.get("id")
            if real and cid and cid != real:
                problems.append(f"case_id 与 case.json 不一致: {cid} != {real}")
            oc = case.get("output_contract") or case.get("outputContract") or {}
            names = list(oc.keys()) if isinstance(oc, dict) else \
                [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in oc]
            for n in names:
                if n not in result:
                    problems.append(f"output_contract 字段缺失: {n}")
        except Exception as e:
            warnings.append(f"case.json 读取失败（跳过契约核对）: {e}")

    status = result.get("status")
    if status not in ("success", "partial", "failed"):
        problems.append(f"status 非法: {status!r}（应为 success/partial/failed）")
    if status == "failed" and not result.get("exceptions"):
        problems.append("status=failed 但 exceptions 为空，无法复核失败原因")

    tex_found = []
    lp = os.path.join(args.out, "latex_project")
    if os.path.isdir(lp):
        for dirpath, _, filenames in os.walk(lp):
            tex_found.extend(f for f in filenames if f.endswith((".tex", ".bib", ".sty", ".cls")))
    if not tex_found and not result.get("outputs"):
        problems.append("无可编辑交付物（latex_project/ 为空且 outputs 为空）")

    if status == "success":
        b = result.get("build") or {}
        if b.get("success") is False:
            warnings.append("status=success 但 build.success=false，请核实是否应降级 partial")

    for w in warnings:
        print(f"[validate] 警告: {w}")
    if problems:
        for p in problems:
            print(f"[validate] FAIL: {p}")
        return 1
    print(f"[validate] PASS: case_id={cid} status={status} 可编辑文件={len(tex_found)} "
          f"PDF={'有' if os.path.exists(os.path.join(args.out, 'preview.pdf')) else '无'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
