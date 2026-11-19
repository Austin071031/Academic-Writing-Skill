#!/usr/bin/env python3
"""validate_output.py — 发布前闸门：校验 /app/output 思维导图交付完整性。

用法: python3 validate_output.py --out /app/output [--work /app/work] [--expect-status success]
检查: result.json 可解析且含 case_id/status; 主导图产物（.md/.mm/.opml/.mmd 至少其一 + 一种预览）
存在且非空; .mm/.opml 为良构 XML; audit critical=0 才可 status=success（否则如实降级）。
exit 0 = 通过; 1 = 有 critical 问题。
"""
import argparse, json, os, sys, xml.etree.ElementTree as ET

def fail(msg):
    print(f"[validate][FAIL] {msg}", file=sys.stderr)
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--expect-status", default=None)
    args = ap.parse_args()
    ok = True

    rp = os.path.join(args.out, "result.json")
    if not os.path.exists(rp):
        sys.exit(fail("result.json 不存在") and 1)
    try:
        with open(rp, encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        sys.exit(fail(f"result.json 不可解析: {e}") and 1)

    for field in ("case_id", "status"):
        if not result.get(field):
            ok &= fail(f"result.json 缺少 {field}")
    if args.expect_status and result.get("status") != args.expect_status:
        ok &= fail(f"status={result.get('status')} 期望 {args.expect_status}")
    if not result.get("outputs"):
        ok &= fail("outputs 为空：至少交付一个产物")

    for key, rel in list((result.get("outputs") or {}).items()):
        p = os.path.join(args.out, rel)
        if not os.path.exists(p):
            ok &= fail(f"outputs.{key} 指向的文件不存在: {rel}")
        elif os.path.getsize(p) == 0:
            ok &= fail(f"outputs.{key} 文件为空: {rel}")

    files = set(os.listdir(args.out)) if os.path.isdir(args.out) else set()
    editable = [f for f in files if os.path.splitext(f)[1] in (".md", ".mm", ".opml", ".mmd")]
    if not editable:
        ok &= fail("缺少可编辑导图产物（.md/.mm/.opml/.mmd 至少其一）")
    previews = [f for f in files if os.path.splitext(f)[1] in (".svg", ".png", ".html", ".pdf")]
    if not previews:
        ok &= fail("缺少预览产物（.svg/.png/.html/.pdf 至少其一）")

    for f in files:
        if f.endswith((".mm", ".opml")):
            try:
                ET.parse(os.path.join(args.out, f))
            except Exception as e:
                ok &= fail(f"{f} 不是良构 XML: {e}")

    audit = None
    for cand in (os.path.join(args.out, "audit_report.json"), os.path.join(args.work, "audit.json")):
        if os.path.exists(cand):
            try:
                audit = json.load(open(cand, encoding="utf-8"))
            except Exception:
                audit = None
            break
    if audit:
        ncrit = (audit.get("stats") or {}).get("n_critical", 0)
        if ncrit and result.get("status") == "success":
            ok &= fail(f"audit 存在 {ncrit} 个 critical 但 status=success，应修复或降级为 partial")
        cov = (audit.get("stats") or {}).get("coverage")
        print(f"[validate] audit: critical={ncrit} coverage={cov}")

    print(f"[validate] {'PASS' if ok else 'FAIL'} (status={result.get('status')})")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
