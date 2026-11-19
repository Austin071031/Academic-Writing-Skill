#!/usr/bin/env python3
"""validate_output.py — 返修交付发布前闸门。

用法: python3 validate_output.py --out /app/output [--work /app/work] [--expect-status success]
检查:
- result.json 可解析且含 case_id/status，outputs 指向的文件存在非空；
- 三大主产物齐备: revised_manuscript.md / response_letter.md / edit_locations.md(或 location_table.md)；
- 修订稿与基线确实存在差异（防止"声称修改实为原样"）；
- verification.json overall_pass 与 result.json status 一致（FAIL 不得报 success）；
- dispositions 覆盖率复核。
exit 0 = PASS; 1 = FAIL（修复或如实降级 status）。
"""
import argparse, json, os, sys

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
        print("[validate][FAIL] result.json 不存在", file=sys.stderr)
        return 1
    try:
        with open(rp, encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        print(f"[validate][FAIL] result.json 不可解析: {e}", file=sys.stderr)
        return 1

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

    # 三大主产物
    for name in ("revised_manuscript.md", "response_letter.md"):
        if not os.path.exists(os.path.join(args.out, name)):
            ok &= fail(f"主产物缺失: {name}")
    if not (os.path.exists(os.path.join(args.out, "edit_locations.md"))
            or os.path.exists(os.path.join(args.out, "location_table.md"))):
        ok &= fail("修改定位产物缺失: edit_locations.md 或 location_table.md")

    # 修订稿与基线存在差异
    struct_p = os.path.join(args.work, "structure.json")
    rev_p = os.path.join(args.out, "revised_manuscript.md")
    if os.path.exists(struct_p) and os.path.exists(rev_p):
        try:
            with open(struct_p, encoding="utf-8") as f:
                struct = json.load(f)
            src = struct.get("source_file")
            if src and os.path.exists(src):
                base_txt = open(src, encoding="utf-8", errors="ignore").read()
                rev_txt = open(rev_p, encoding="utf-8").read()
                if base_txt.strip() == rev_txt.strip():
                    ok &= fail("修订稿与基线完全相同：不存在任何真实修改")
        except Exception as e:
            warn(f"差异检查跳过: {e}")

    # verification 与 status 一致
    vp = os.path.join(args.out, "verification.json")
    if os.path.exists(vp):
        try:
            with open(vp, encoding="utf-8") as f:
                ver = json.load(f)
            if ver.get("overall_pass") is False and result.get("status") == "success":
                ok &= fail("verification FAIL 但 status=success：修复或降级为 partial")
            for cname, c in (ver.get("checks") or {}).items():
                if c.get("pass") is False:
                    warn(f"verification.{cname} 未通过")
        except Exception as e:
            warn(f"verification.json 解析失败: {e}")
    else:
        warn("缺 verification.json：可核验性得分将受损")

    # 覆盖率复核
    comments_p = os.path.join(args.work, "comments.json")
    disp_p = os.path.join(args.work, "dispositions.json")
    if os.path.exists(comments_p) and os.path.exists(disp_p):
        try:
            comments = json.load(open(comments_p, encoding="utf-8"))
            disps = json.load(open(disp_p, encoding="utf-8"))
            n_sub = sum(len(c["sub_requests"]) for c in comments.get("comments", []))
            if len(disps) < n_sub:
                warn(f"dispositions ({len(disps)}) 少于子要求数 ({n_sub})：答得全存疑")
        except Exception:
            pass

    if result.get("exceptions") and result.get("status") == "success":
        warn("存在 exceptions 但 status=success，请确认异常已处置")
    if not result.get("change_log"):
        warn("change_log 为空：修改记录缺失将损害可核验性")

    print(f"[validate] {'PASS' if ok else 'FAIL'} (status={result.get('status')}, "
          f"outputs={len(result.get('outputs') or {})})")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
