#!/usr/bin/env python3
"""validate_output.py — 发布前闸门：校验 /app/output 交付完整性。

用法: python3 validate_output.py --out /app/output [--work /app/work]
检查: result.json 可解析且含 case_id/status；译文主产物存在且非空；
findings schema 抽检；诚实性（有未处置异常却 status=success 时告警）；
缺译句段存在时 status 应为 partial。
exit 0 = PASS; 1 = FAIL（修复或如实降级 status）。
"""
import argparse, json, os, sys

def fail(msg):
    print(f"[validate][FAIL] {msg}", file=sys.stderr)
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
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
    if not result.get("outputs"):
        ok &= fail("outputs 为空：至少交付一个主产物")

    main_products = [k for k in (result.get("outputs") or {})
                     if k in ("translation_full", "bilingual", "revised_translation",
                              "audit_annotated", "report")]
    if not main_products:
        ok &= fail("缺少译文/对照/报告类主产物")

    for key, rel in list((result.get("outputs") or {}).items()):
        p = os.path.join(args.out, rel)
        if not os.path.exists(p):
            ok &= fail(f"outputs.{key} 指向的文件不存在: {rel}")
        elif os.path.getsize(p) == 0:
            ok &= fail(f"outputs.{key} 文件为空: {rel}")

    fp = os.path.join(args.out, "findings.json")
    if os.path.exists(fp):
        try:
            with open(fp, encoding="utf-8") as f:
                findings = json.load(f)
            ids = [x.get("id") for x in findings]
            if len(ids) != len(set(ids)):
                ok &= fail("findings.json 存在重复 id")
            for x in findings[:60]:
                for req in ("dimension", "type", "location", "quote",
                            "evidence", "action"):
                    if req not in x:
                        ok &= fail(f"finding {x.get('id')} 缺字段 {req}")
                        break
        except Exception as e:
            ok &= fail(f"findings.json 解析失败: {e}")

    stats = result.get("stats") or {}
    missing = stats.get("segments_missing", 0)
    if missing and result.get("status") == "success":
        print(f"[validate][WARN] 存在 {missing} 个缺译句段但 status=success，"
              "建议降为 partial 或补齐译文", file=sys.stderr)
    if result.get("exceptions") and result.get("status") == "success":
        print("[validate][WARN] 存在 exceptions 但 status=success，请确认异常已处置",
              file=sys.stderr)
    if not result.get("evidence_map"):
        print("[validate][WARN] evidence_map 为空，可核验性将受损", file=sys.stderr)

    print(f"[validate] {'PASS' if ok else 'FAIL'} (status={result.get('status')}, "
          f"outputs={len(result.get('outputs') or {})})")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
