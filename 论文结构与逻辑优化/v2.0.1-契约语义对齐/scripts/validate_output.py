#!/usr/bin/env python3
"""validate_output.py — 发布前闸门：校验 /app/output 交付完整性。

用法: python3 validate_output.py --out /app/output [--work /app/work] [--expect-status success]
检查: result.json 可解析且含 case_id/status；主产物存在且非空；
findings/edit_plan schema 抽检（id 唯一、含 location/quote/action）；
诚实性: 有未处理异常却 status=success 时告警。
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

    # findings schema 抽检
    fp = os.path.join(args.out, "findings.json")
    if os.path.exists(fp):
        try:
            with open(fp, encoding="utf-8") as f:
                findings = json.load(f)
            ids = [x.get("id") for x in findings]
            if len(ids) != len(set(ids)):
                ok &= fail("findings.json 存在重复 id")
            for x in findings[:50]:
                for req in ("dimension", "type", "location", "quote", "evidence", "action"):
                    if req not in x:
                        ok &= fail(f"finding {x.get('id')} 缺字段 {req}")
                        break
            dims = {x.get("dimension") for x in findings}
            if len(dims) < 6:
                print(f"[validate][WARN] 六维度未全覆盖（当前 {len(dims)} 维），"
                      "如系稿件本身无此类问题请在报告中说明", file=sys.stderr)
        except Exception as e:
            ok &= fail(f"findings.json 解析失败: {e}")

    if result.get("exceptions") and result.get("status") == "success":
        print("[validate][WARN] 存在 exceptions 但 status=success，请确认异常已处置", file=sys.stderr)
    if not result.get("evidence_map"):
        print("[validate][WARN] evidence_map 为空，可核验性将受损", file=sys.stderr)

    # v2.0.1 单点改动：契约字段语义对齐校验（contract_check 回填结构）
    contract_fields = result.get("output_contract_fields") or []
    for name in contract_fields:
        v = result.get(name)
        if v is None:
            ok &= fail(f"契约字段 {name} 为 null：请先运行 contract_check.py 做语义对齐回填")
            continue
        if isinstance(v, dict) and "coverage" in v:
            if v.get("coverage") == "missing":
                print(f"[validate][WARN] 契约字段 {name} coverage=missing："
                      "请补交对应产物，或确认已在 uncertainty 中说明", file=sys.stderr)
        else:
            print(f"[validate][WARN] 契约字段 {name} 缺 coverage 标记（旧式 alias 回填）："
                  "建议先运行 contract_check.py 生成 contract_map.json 后重新 assemble",
                  file=sys.stderr)

    print(f"[validate] {'PASS' if ok else 'FAIL'} (status={result.get('status')}, "
          f"outputs={len(result.get('outputs') or {})})")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
