#!/usr/bin/env python3
"""validate_output.py — 交付前终检：result.json 契约字段齐全、产物真实存在、状态自洽。

打印逐项 PASS/FAIL 并写 /app/output/validation.md；整体 PASS 才允许 status=success。
"""
import argparse, json, os, sys, datetime

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()
    out = args.out
    checks = []

    def add(name, ok, detail=""):
        checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})
        return ok

    brief = {}
    bp = os.path.join(args.work, "brief.json")
    if os.path.isfile(bp):
        try:
            brief = json.load(open(bp, encoding="utf-8"))
        except Exception:
            pass

    rj_path = os.path.join(out, "result.json")
    result = None
    if add("result.json 存在", os.path.isfile(rj_path)):
        try:
            result = json.load(open(rj_path, encoding="utf-8"))
            add("result.json 可解析", True)
        except Exception as e:
            add("result.json 可解析", False, str(e)[:120])
            result = {}

    if result is not None:
        cid = result.get("case_id")
        add("case_id 存在且与 brief 一致",
            bool(cid) and (not brief.get("case_id") or cid == brief.get("case_id")),
            f"result={cid} brief={brief.get('case_id')}")
        add("status 取值合法", result.get("status") in ("success", "partial", "failed"),
            str(result.get("status")))
        missing = [f for f in (brief.get("output_contract") or []) if f not in result]
        add("output_contract 字段齐全", not missing,
            "缺: " + ",".join(missing) if missing else f"{len(brief.get('output_contract') or [])} 字段全在")
        # 声明的产物真实存在（/app/output 前缀路径映射回实际 out 目录校验）
        dl = result.get("deliverables") or {}
        for k, v in (dl.items() if isinstance(dl, dict) else []):
            vals = v if isinstance(v, list) else [v]
            for p in vals:
                if isinstance(p, str) and p.startswith("/app/output/"):
                    local = os.path.join(out, os.path.relpath(p, "/app/output"))
                    add(f"产物存在: {k}", os.path.isfile(p) or os.path.isfile(local),
                        p if os.path.isfile(p) else local)
        for u in (result.get("uncertainty") or [])[:0]:
            pass
        add("uncertainty 为列表", isinstance(result.get("uncertainty"), list))

    ms = os.path.join(out, "manuscript.md")
    ms_ok = os.path.isfile(ms) and os.path.getsize(ms) > 200
    add("manuscript.md 非空", ms_ok,
        f"{os.path.getsize(ms) if os.path.isfile(ms) else 0} bytes")

    cr = os.path.join(out, "consistency_report.json")
    if add("consistency_report.json 存在", os.path.isfile(cr)):
        try:
            rep = json.load(open(cr, encoding="utf-8"))
            v = rep.get("verdict")
            add("一致性 verdict 非 FAIL", v in ("PASS", "WARN"), f"verdict={v}")
            if result and result.get("status") == "success":
                add("success 与一致性一致", v in ("PASS", "WARN"),
                    "status=success 但一致性 FAIL，必须降级 partial")
        except Exception as e:
            add("consistency_report 可解析", False, str(e)[:120])

    add("run_log.md 存在", os.path.isfile(os.path.join(out, "run_log.md")))

    n_fail = sum(1 for c in checks if c["result"] == "FAIL")
    overall = "PASS" if n_fail == 0 else "FAIL"
    with open(os.path.join(out, "validation.md"), "w", encoding="utf-8") as f:
        f.write(f"# 交付终检（{datetime.datetime.utcnow().isoformat()}Z）\n\n**overall: {overall}**\n\n")
        for c in checks:
            f.write(f"- [{c['result']}] {c['check']} {('— ' + c['detail']) if c['detail'] else ''}\n")
    try:
        with open(os.path.join(out, "run_log.md"), "a", encoding="utf-8") as f:
            f.write(f"\n## validate_output overall={overall} fails={n_fail}\n")
    except Exception:
        pass
    for c in checks:
        print(f"[{c['result']}] {c['check']} {c['detail']}")
    print(json.dumps({"overall": overall, "fails": n_fail}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
