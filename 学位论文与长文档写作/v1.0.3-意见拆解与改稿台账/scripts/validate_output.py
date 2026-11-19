#!/usr/bin/env python3
"""validate_output.py — 长文档发布前闸门：校验 /app/output 交付完整性。

用法: python3 validate_output.py --out /app/output [--work /app/work] [--expect-status success]
检查:
  1. result.json 可解析且含 case_id/status/outputs；outputs 指向的文件存在且非空。
  2. 若存在 work/xref_audit.json：交叉引用完整性复检（悬空引用 = critical，缺失定义 = WARN）。
  3. 若存在 references.md：文献编号连续性 + 正文引用与文献表双向一致。
  4. status=success 但 evidence_map 为空 → FAIL（可核验性是硬要求）。
exit 0 = 通过; 1 = 有 critical 问题（修复或如实降级 status）。
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
        fail("result.json 不存在")
        sys.exit(1)
    try:
        with open(rp, encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        fail(f"result.json 不可解析: {e}")
        sys.exit(1)

    for field in ("case_id", "status"):
        if not result.get(field):
            ok &= fail(f"result.json 缺少 {field}")
    if args.expect_status and result.get("status") != args.expect_status:
        ok &= fail(f"status={result.get('status')} 期望 {args.expect_status}")
    if not result.get("outputs"):
        ok &= fail("outputs 为空：至少交付一个主产物")
    for key, rel in list((result.get("outputs") or {}).items()):
        p = os.path.join(args.out, rel)
        if not os.path.exists(p):
            ok &= fail(f"outputs.{key} 指向的文件不存在: {rel}")
        elif os.path.getsize(p) == 0:
            ok &= fail(f"outputs.{key} 文件为空: {rel}")

    # 交叉引用完整性
    xa = os.path.join(args.work, "xref_audit.json")
    if os.path.exists(xa):
        try:
            with open(xa, encoding="utf-8") as f:
                audit = json.load(f)
            dangling = audit.get("dangling") or []
            if dangling:
                ok &= fail(f"存在悬空交叉引用 {len(dangling)} 处: "
                           f"{[d.get('raw') for d in dangling[:8]]}")
            if audit.get("missing_definition"):
                print(f"[validate][WARN] 交叉引用缺少定义: "
                      f"{audit['missing_definition'][:8]}", file=sys.stderr)
        except Exception:
            pass

    # 参考文献编号连续性与双向一致
    refp = os.path.join(args.out, "references.md")
    if os.path.exists(refp):
        with open(refp, encoding="utf-8") as f:
            txt = f.read()
        nums = [int(m.group(1)) for m in re.finditer(r"^\[(\d+)\]", txt, re.M)]
        if nums and nums != list(range(1, len(nums) + 1)):
            ok &= fail(f"参考文献编号不连续: {nums[:10]}")
        cited = set()
        for key, rel in list((result.get("outputs") or {}).items()):
            p = os.path.join(args.out, rel)
            if not (p.endswith(".md") and os.path.exists(p)):
                continue
            with open(p, encoding="utf-8") as f:
                t = f.read()
            for m in re.finditer(r"\[(\d+(?:\s*[-–,，]\s*\d+)*)\]", t):
                for part in re.split(r"[,，]", m.group(1)):
                    rm = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part.strip())
                    if rm:
                        cited.update(range(int(rm.group(1)), int(rm.group(2)) + 1))
                    elif part.strip().isdigit():
                        cited.add(int(part.strip()))
        if cited and nums:
            stray = cited - set(nums)
            if stray:
                ok &= fail(f"正文引用了文献表中不存在的编号: {sorted(stray)[:10]}")

    # 可核验性
    if result.get("status") == "success" and not result.get("evidence_map"):
        ok &= fail("status=success 但 evidence_map 为空（可核验性是评分硬要求）")

    print(f"[validate] {'PASS' if ok else 'FAIL'} (status={result.get('status')})")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
