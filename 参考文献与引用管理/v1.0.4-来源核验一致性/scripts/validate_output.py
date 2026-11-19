#!/usr/bin/env python3
"""validate_output.py — 发布前闸门：校验 /app/output 交付完整性。

用法: python3 validate_output.py --out /app/output [--work /app/work] [--expect-status success]
检查: result.json 可解析且含 case_id/status; 主产物存在且非空; 文献编号连续性复检;
诚实性: 不允许 result.json 中出现预制答案痕迹（本脚本只做结构校验，不核查内容真实性）。
exit 0 = 通过; 1 = 有 critical 问题（需修复或如实降级 status）。
"""
import argparse, json, os, re, sys

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
        ok &= fail("outputs 为空：至少交付一个主产物")

    # 主产物非空检查
    for key, rel in list((result.get("outputs") or {}).items()):
        p = os.path.join(args.out, rel)
        if not os.path.exists(p):
            ok &= fail(f"outputs.{key} 指向的文件不存在: {rel}")
        elif os.path.getsize(p) == 0:
            ok &= fail(f"outputs.{key} 文件为空: {rel}")

    # 参考文献编号连续性复检（若存在 references.json）
    rj = os.path.join(args.out, "references.json")
    if os.path.exists(rj):
        try:
            with open(rj, encoding="utf-8") as f:
                refs = json.load(f)
            nums = [e["number"] for e in refs.get("entries", [])]
            if nums and nums != list(range(1, len(nums) + 1)):
                ok &= fail(f"参考文献列表编号不连续: {nums[:10]}...")
        except Exception as e:
            ok &= fail(f"references.json 解析失败: {e}")

    # 一致性复检（若存在 consistency_audit.json 且含 critical）
    ca = os.path.join(args.out, "consistency_audit.json")
    if os.path.exists(ca):
        try:
            with open(ca, encoding="utf-8") as f:
                audit = json.load(f)
            crit = [i for i in audit.get("issues", []) if i.get("type") in ("out_of_range", "gap")]
            if crit and result.get("status") == "success":
                print(f"[validate][WARN] 一致性存在 {len(crit)} 个 critical 但 status=success", file=sys.stderr)
        except Exception:
            pass

    print(f"[validate] {'PASS' if ok else 'FAIL'} (status={result.get('status')})")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
