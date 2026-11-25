#!/usr/bin/env python3
"""contract_audit.py — 契约与任务指令自动对齐引擎（v3.0.2 方向核心）。

--phase requirements：把 /input/task.md 拆成原子指令清单（work/task_requirements.json），
  供 Agent 写作前逐条对照。
--phase verify：装配后校验：① output_contract 字段在 result.json 中非空；
  ② task.md 原子指令的关键要素在章节正文中出现（关键词命中）；
  ③ status 与未闭合缺口一致。输出 contract_report.json，verdict=pass/fail。
用法: python3 contract_audit.py --phase requirements|verify [--task /input/task.md]
      [--work /app/work] [--out /app/output]
"""
import argparse, json, os, re, sys

REQ_HINT = re.compile(r"(必须|需要|要求|撰写|补写|改写|输出|包含|覆盖|格式|受众|语言|篇幅|不得|禁止|must|shall|include|write|format|cover|deliver)", re.I)
STOP = set("the and for with from this that are was were been have has had not you your our their its his her they them she him into about over under between within without".split())

def keywords(text):
    """从指令句提取检索关键词：中文取 2-4 字实义词组，英文取 ≥4 字母实词。"""
    kws = []
    for m in re.finditer(r"[A-Za-z][a-z]{3,}", text):
        w = m.group(0).lower()
        if w not in STOP:
            kws.append(w)
    for m in re.finditer(r"[\u4e00-\u9fff]{2,6}", text):
        kws.append(m.group(0))
    return kws[:6]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["requirements", "verify"], required=True)
    ap.add_argument("--task", default="/input/task.md")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    if args.phase == "requirements":
        reqs = []
        if os.path.exists(args.task):
            txt = open(args.task, encoding="utf-8", errors="ignore").read()
            for i, line in enumerate(txt.splitlines(), 1):
                line = line.strip().lstrip("#*>-•·0123456789.、)） ")
                if 8 <= len(line) <= 300 and REQ_HINT.search(line):
                    reqs.append({"rid": f"T{len(reqs)+1:02d}", "text": line, "source_line": i,
                                 "keywords": keywords(line)})
        outp = os.path.join(args.work, "task_requirements.json")
        json.dump(reqs, open(outp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(f"[contract] 原子指令 {len(reqs)} 条 -> {outp}（写作时逐条对照）")
        return 0

    # verify
    issues = []
    rp = os.path.join(args.out, "result.json")
    result = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else {}
    contract = result.get("output_contract_fields") or []
    for f in contract:
        v = result.get(f)
        if v in (None, "", [], {}):
            issues.append({"kind": "contract_field_empty", "field": f})

    chap_p = os.path.join(args.out, "methods_chapter.md")
    chap = open(chap_p, encoding="utf-8").read() if os.path.exists(chap_p) else ""
    chap_l = chap.lower()
    req_p = os.path.join(args.work, "task_requirements.json")
    reqs = json.load(open(req_p, encoding="utf-8")) if os.path.exists(req_p) else []
    uncovered = []
    for r in reqs:
        kws = r.get("keywords") or keywords(r.get("text", ""))
        hit = any(k.lower() in chap_l for k in kws) if kws else True
        if not hit:
            uncovered.append({"rid": r["rid"], "text": r["text"][:80], "keywords": kws})
    for u in uncovered:
        issues.append({"kind": "requirement_uncovered", **u})

    unresolved = [g for g in (result.get("uncertainty") or []) if g.get("status") == "unresolved"]
    if unresolved and result.get("status") == "success":
        issues.append({"kind": "status_inconsistent", "note": "有未解决缺口但 status=success"})

    verdict = "pass" if not issues else "fail"
    rep = {"contract_fields_checked": len(contract), "requirements_total": len(reqs),
           "requirements_uncovered": len(uncovered), "issues": issues, "verdict": verdict}
    json.dump(rep, open(os.path.join(args.out, "contract_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"[contract] 契约字段 {len(contract)} 指令 {len(reqs)} 未覆盖 {len(uncovered)} verdict={verdict}")
    sys.exit(0 if verdict == "pass" else 1)

if __name__ == "__main__":
    sys.exit(main())
