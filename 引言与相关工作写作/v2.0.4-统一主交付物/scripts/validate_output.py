#!/usr/bin/env python3
"""validate_output.py — 发布前闸门：校验 /app/output 交付完整性。

用法: python3 validate_output.py --out /app/output [--work /app/work] [--expect-status success]
检查: result.json 可解析且含 case_id/status/outputs; 主产物 introduction.md 与 related_work.md
存在且非空; 四要素完整性复检（读 build_report.json）; 引用编号连续性复检。
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

    # 四要素复检
    brp = os.path.join(args.out, "build_report.json")
    if os.path.exists(brp):
        try:
            with open(brp, encoding="utf-8") as f:
                br = json.load(f)
            sec = br.get("sections", {})
            missing = [k for k, v in (("intro_background", sec.get("intro_background")),
                                      ("intro_gap", sec.get("intro_gap")),
                                      ("intro_contributions", sec.get("intro_contributions")))
                       if not v]
            if sec.get("rl_groups", 0) < 1:
                missing.append("rl_groups")
            if missing and result.get("status") == "success":
                print(f"[validate][WARN] 四要素缺 {missing} 但 status=success", file=sys.stderr)
            if br.get("agent_pre_numbered"):
                print(f"[validate][WARN] 工作稿中出现 {len(br['agent_pre_numbered'])} 处手写编号", file=sys.stderr)
            if br.get("anchors", {}).get("missing") and result.get("status") == "success":
                print(f"[validate][WARN] 存在未解析锚点但 status=success", file=sys.stderr)
        except Exception:
            pass
    else:
        ok &= fail("build_report.json 缺失：请先运行 build_deliverables.py")

    # 参考文献编号连续性
    refp = os.path.join(args.out, "references.md")
    if os.path.exists(refp):
        with open(refp, encoding="utf-8") as f:
            txt = f.read()
        nums = [int(m.group(1)) for m in re.finditer(r"^\[(\d+)\]", txt, re.M)]
        if nums and nums != list(range(1, len(nums) + 1)):
            ok &= fail(f"参考文献编号不连续: {nums[:10]}")

    # 正文引用与文献表双向一致
    if os.path.exists(os.path.join(args.out, "introduction.md")):
        cited = set()
        for name in ("introduction.md", "related_work.md"):
            p = os.path.join(args.out, name)
            if not os.path.exists(p):
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
        if cited and os.path.exists(refp):
            with open(refp, encoding="utf-8") as f:
                have = {int(m.group(1)) for m in re.finditer(r"^\[(\d+)\]", f.read(), re.M)}
            stray = cited - have
            unused = have - cited
            if stray:
                ok &= fail(f"正文引用了文献表中不存在的编号: {sorted(stray)[:10]}")
            if unused:
                print(f"[validate][WARN] 文献表中有未被正文引用的条目: {sorted(unused)[:10]}", file=sys.stderr)

    print(f"[validate] {'PASS' if ok else 'FAIL'} (status={result.get('status')})")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
