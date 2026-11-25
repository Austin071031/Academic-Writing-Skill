#!/usr/bin/env python3
"""validate_output.py — 发布前闸门：校验 /app/output 交付完整性与一致性。

用法: python3 validate_output.py --out /app/output [--work /app/work] [--expect-status success]
exit 0 = 通过; 1 = 有 critical 问题（需修复或如实降级 status）。
"""
import argparse, json, os, re, sys

def fail(msg):
    print(f"[validate][FAIL] {msg}", file=sys.stderr)
    return False

def warn(msg):
    print(f"[validate][WARN] {msg}", file=sys.stderr)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--expect-status", default=None)
    args = ap.parse_args()

    ok = True
    rp = os.path.join(args.out, "result.json")
    if not os.path.exists(rp):
        fail("result.json 不存在")
        sys.exit(1)
    try:
        with open(rp, encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        fail(f"result.json 不可解析: {e}")
        sys.exit(1)

    for field in ("case_id", "status", "outputs"):
        if not result.get(field):
            ok &= fail(f"result.json 缺少 {field}")
    if args.expect_status and result.get("status") != args.expect_status:
        ok &= fail(f"status={result.get('status')} 期望 {args.expect_status}")
    for key, rel in list((result.get("outputs") or {}).items()):
        p = os.path.join(args.out, rel)
        if not os.path.exists(p):
            ok &= fail(f"outputs.{key} 指向的文件不存在: {rel}")
        elif os.path.getsize(p) == 0:
            ok &= fail(f"outputs.{key} 文件为空: {rel}")

    # output_contract 字段核对
    contract = result.get("output_contract_fields") or []
    missing_contract = [c for c in contract if c not in result]
    if missing_contract:
        ok &= fail(f"output_contract 字段未覆盖: {missing_contract}（请在 work/contract_extra.json 或 status.json 补齐）")

    # build_report 复检
    brp = os.path.join(args.out, "build_report.json")
    if os.path.exists(brp):
        with open(brp, encoding="utf-8") as f:
            br = json.load(f)
        cov = br.get("coverage", {})
        missing = [k for k, v in cov.items() if not v]
        if missing and result.get("status") == "success":
            warn(f"六要素缺 {missing} 但 status=success（应降级为 partial 或补齐）")
            ok = False
        if br.get("anchors", {}).get("missing"):
            ok &= fail(f"存在未解析证据锚点: {br['anchors']['missing']}")
        if br.get("table_rows", 0) == 0:
            warn("参数表为空：若材料含参数，应填写 table_rows.json")
    else:
        ok &= fail("build_report.json 缺失：请先运行 build_deliverables.py")

    # 章节泄漏抽检：正文数值不得出现"TODO/待补/xxx"占位
    chap = os.path.join(args.out, "methods_chapter.md")
    if os.path.exists(chap):
        with open(chap, encoding="utf-8") as f:
            txt = f.read()
        for bad in ("TODO", "待补", "TBD", "xxx", "XXX", "【补", "（补", "(补"):
            if bad in txt:
                warn(f"章节含占位符 {bad!r}")
    print("[validate] 完成: " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    sys.exit(main())
