#!/usr/bin/env python3
"""run_pipeline.py — 来源核验与一致性检查编排器（v2.0.4）。

v2.0.4 唯一机制增量（父版 v1.0.4，attempt 89253，57 分）：六阶段压缩为 prep/finish 两步；
prep 生成「匹配裁决工作单」（每个带引用段落 + 所引条目元数据并排呈现），Agent 只需
逐段写 match_verdicts.jsonl，条目体检/标注稿/报告全部脚本化。

用法:
  python3 scripts/run_pipeline.py --stage prep
  # Agent 读工作单 → 写 /app/work/match_verdicts.jsonl
  python3 scripts/run_pipeline.py --stage finish
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    for line in ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-3:]:
        print("  |", line)
    return r

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def stage_prep(args):
    W, O = args.work, args.out
    print("== prep [1/2] init_result / inspect_case / parse")
    run(["python3", f"{HERE}/init_result.py", "--case", f"{args.input}/case.json", "--out", O])
    run(["python3", f"{HERE}/inspect_case.py", "--case", f"{args.input}/case.json",
         "--task", f"{args.input}/task.md", "--input-dir", args.input, "--work", W])
    insp = load_json(os.path.join(W, "inspection.json"), {}) or {}
    ms_cands = [c["path"] for c in insp.get("manuscript_candidates", [])]
    lib_cands = [c["path"] for c in insp.get("library_candidates", [])
                 if c.get("library_format") not in ("pdf", "docx")]
    if ms_cands:
        run(["python3", f"{HERE}/parse_manuscript.py", ms_cands[0], "--work", W])
    if lib_cands:
        run(["python3", f"{HERE}/parse_library.py"] + lib_cands + ["--work", W])
    else:
        save_json(os.path.join(W, "library.json"), {"records": [], "issues": ["无文献库"], "count": 0})
    print("== prep [2/2] 生成匹配裁决工作单")
    ms = load_json(os.path.join(W, "manuscript.json"), {}) or {}
    lib = load_json(os.path.join(W, "library.json"), {}) or {}
    records = lib.get("records", [])
    lines = ["# 引用匹配裁决工作单（Agent 逐段写 match_verdicts.jsonl）", "",
             "## A. 文献库条目", ""]
    for i, r in enumerate(records, 1):
        lines.append(f"- **编号{i} / {r['id']}** [{r.get('entry_type')}] {r.get('title','')} | "
                     f"{(r.get('authors') or ['?'])[0]} | {r.get('year','?')} | "
                     f"{r.get('venue','')} | DOI:{r.get('doi') or '无'}")
    # 稿件自带文末列表（编号→条目原文），优先于按库位次猜测
    own_list = {}
    for p in ms.get("paragraphs", []):
        if p.get("kind") != "reference_list":
            continue
        marks = list(re.finditer(r"\[(\d+)\]", p["text"]))
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else len(p["text"])
            own_list.setdefault(int(m.group(1)), p["text"][m.end():end].strip())
    lines += ["", "## B. 带引用标记的正文段落（逐段裁决：论断与所引文献是否对得上）", "",
              f"（编号→条目依据：{'稿件自带文末列表' if own_list else '文献库位次（无自带列表，请人工核对）'}）", ""]
    n_cited = 0
    for p in ms.get("paragraphs", []):
        if p.get("kind") == "reference_list":
            continue
        cited = [m for m in p.get("cite_marks", []) if m.get("style") == "numeric"]
        if not cited:
            continue
        n_cited += 1
        nums = sorted({n for m in cited for n in m.get("nums", [])})
        lines.append(f"### {p['pid']}（引用编号 {nums}）")
        lines.append(p["text"])
        for n in nums:
            if n in own_list:
                lines.append(f"  ↳ [{n}] {own_list[n][:110]}")
            elif 1 <= n <= len(records):
                r = records[n - 1]
                lines.append(f"  ↳ [{n}] {r.get('title','')[:90]} | {r.get('venue','')} {r.get('year','')}")
            else:
                lines.append(f"  ↳ [{n}] ⚠ 编号超出文献库范围（{len(records)} 条）")
        lines.append("")
    lines += ["## C. 裁决文件写法（/app/work/match_verdicts.jsonl，每段至少一行）", "```json",
              '{"pid":"P002","sentence":"<论断句原文>","entry_ids":["R001"],'
              '"verdict":"supports","rationale":"<双方原文短语对照>"}',
              "verdict 四档: supports / partially / unrelated / insufficient_evidence", "```"]
    ws = os.path.join(W, "match_worksheet.md")
    with open(ws, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n===== 工作单已写 {ws}（{n_cited} 个待裁决段落 / {len(records)} 条文献）=====")
    print("Agent：读工作单 → 写 /app/work/match_verdicts.jsonl → 跑 --stage finish")
    return 0

def stage_finish(args):
    W, O = args.work, args.out
    vd = os.path.join(W, "match_verdicts.jsonl")
    if not os.path.exists(vd):
        print("  | match_verdicts.jsonl 缺失——仅交付条目体检（status=partial）")
        save_json(os.path.join(W, "exceptions.json"), ["Agent 未提供裁决，缺论断级匹配结论"])
    print("== finish [1/2] verify_engine")
    run(["python3", f"{HERE}/verify_engine.py",
         "--library", os.path.join(W, "library.json"),
         "--manuscript", os.path.join(W, "manuscript.json"),
         "--verdicts", vd, "--work", W, "--out", O])
    rep = load_json(os.path.join(O, "verification_report.json"),
                    load_json(os.path.join(W, "verification_report.json"), {}) or {}) or {}
    n_v = sum(1 for l in open(vd, encoding="utf-8") if l.strip()) if os.path.exists(vd) else 0
    save_json(os.path.join(W, "stats.json"),
              {"n_verdicts": n_v,
               "n_suspicious_entries": len(rep.get("suspicious_entries", []) or []),
               "conclusion": rep.get("conclusion")})
    status = "success" if n_v else "partial"
    print(f"== finish [2/2] assemble / validate / preview（status={status}）")
    run(["python3", f"{HERE}/assemble_result.py", "--work", W, "--out", O,
         "--case", f"{args.input}/case.json", "--skill", args.skill, "--status", status])
    rv = run(["python3", f"{HERE}/validate_output.py", "--out", O])
    run(["python3", f"{HERE}/render_previews.py", "--out", O])
    return 0 if rv.returncode == 0 else 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--stage", required=True, choices=["prep", "finish"])
    ap.add_argument("--skill", default="citation-verification-audit v2.0.4")
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True); os.makedirs(args.out, exist_ok=True)
    rc = stage_prep(args) if args.stage == "prep" else stage_finish(args)
    print(f"[run_pipeline] {args.stage} DONE")
    return rc

if __name__ == "__main__":
    sys.exit(main())
