#!/usr/bin/env python3
"""repro_gate.py — 可复现闸门（v1.0.2 方向核心引擎）。

对 work/repro_checklist.json 的复现清单逐项检查：代码版本、运行环境（OS/Python/关键库）、
硬件、数据获取方式（URL 或校验和）、可执行命令序列、随机种子、预计开销。
另校验章节"6 可复现清单"小节确实包含每条命令的首个令牌（命令不能只登记不写进正文）。
用法: python3 repro_gate.py --work /app/work --out /app/output
输出: repro_report.json {items:[{key,ok,note}], missing, commands_not_in_chapter, verdict}
"""
import argparse, json, os, re, sys

REQUIRED = ["code_version", "environment", "hardware", "data_acquisition", "commands", "seeds"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    cp = os.path.join(args.work, "repro_checklist.json")
    checklist = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else {}
    if not checklist:  # v3.0.0：回退到单一登记表 registration.json
        rp = os.path.join(args.work, "registration.json")
        if os.path.exists(rp):
            checklist = (json.load(open(rp, encoding="utf-8")) or {}).get("repro_checklist") or {}
    items, missing = [], []
    for k in REQUIRED:
        v = checklist.get(k)
        ok = bool(v) and (not isinstance(v, (list, dict)) or len(v) > 0)
        if not ok:
            missing.append(k)
        items.append({"key": k, "ok": bool(ok)})

    chap_path = os.path.join(args.work, "sections", "06_repro.md")
    chap_txt = open(chap_path, encoding="utf-8").read() if os.path.exists(chap_path) else ""
    not_in = []
    for cmd in checklist.get("commands") or []:
        tok = re.split(r"\s+", cmd.strip())[0] if cmd.strip() else ""
        if tok and tok not in chap_txt:
            not_in.append(cmd[:100])

    env = checklist.get("environment") or {}
    if isinstance(env, dict) and not (env.get("python") or env.get("os")):
        items.append({"key": "environment.python_or_os", "ok": False})
        if "environment" not in missing:
            missing.append("environment.python_or_os")
    da = checklist.get("data_acquisition") or {}
    if isinstance(da, dict) and not (da.get("url") or da.get("hash") or da.get("path")):
        items.append({"key": "data_acquisition.url_or_hash", "ok": False})
        if "data_acquisition" not in missing:
            missing.append("data_acquisition.url_or_hash")

    verdict = "pass" if not missing and not not_in else "fail"
    report = {"items": items, "missing": missing,
              "commands_not_in_chapter": not_in, "est_cost": checklist.get("est_cost"),
              "verdict": verdict}
    rp = os.path.join(args.out, "repro_report.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[repro] 缺 {missing} 命令未入章 {len(not_in)} verdict={verdict} -> {rp}")
    sys.exit(0 if verdict == "pass" else 1)

if __name__ == "__main__":
    sys.exit(main())
