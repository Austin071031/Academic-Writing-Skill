#!/usr/bin/env python3
"""run_pipeline.py — 引用插入定位编排器（v2.0.0）。

v2.0.0 唯一机制增量（父版 v1.0.0，attempt 89249，53 分）：六阶段压缩为 prep/finish 两步；
prep 直接生成「论断工作单」（段落+文献目录一屏呈现），Agent 只需读工作单写
citation_decisions.jsonl，finish 全部脚本化。rubric 核心已内联进 SKILL.md。

用法:
  python3 scripts/run_pipeline.py --stage prep
  # Agent 读工作单 → 写 /app/work/citation_decisions.jsonl
  python3 scripts/run_pipeline.py --stage finish
"""
import argparse, json, os, re, subprocess, sys, shutil

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
    print("== prep [1/3] init_result / inspect_case")
    run(["python3", f"{HERE}/init_result.py", "--case", f"{args.input}/case.json", "--out", O])
    run(["python3", f"{HERE}/inspect_case.py", "--case", f"{args.input}/case.json",
         "--task", f"{args.input}/task.md", "--input-dir", args.input, "--work", W])
    insp = load_json(os.path.join(W, "inspection.json"), {}) or {}
    ms_cands = [c["path"] for c in insp.get("manuscript_candidates", [])]
    lib_cands = [c["path"] for c in insp.get("library_candidates", [])
                 if c.get("library_format") not in ("pdf", "docx")]
    if ms_cands:
        print("== prep [2/3] parse_manuscript:", os.path.basename(ms_cands[0]))
        run(["python3", f"{HERE}/parse_manuscript.py", ms_cands[0], "--work", W])
    if lib_cands:
        print("== prep [3/3] parse_library:", ", ".join(os.path.basename(c) for c in lib_cands))
        run(["python3", f"{HERE}/parse_library.py"] + lib_cands + ["--work", W])
    else:
        save_json(os.path.join(W, "library.json"), {"records": [], "issues": ["无文献库"], "count": 0})
    # 论断工作单
    ms = load_json(os.path.join(W, "manuscript.json"), {}) or {}
    lib = load_json(os.path.join(W, "library.json"), {}) or {}
    lines = ["# 论断工作单（Agent 依据本单写 citation_decisions.jsonl）", "",
             "## A. 稿件正文段落（需要判断哪些句子需要引用支撑）", ""]
    for p in ms.get("paragraphs", []):
        if p.get("kind") in ("body", "figure_note", "table_note", "appendix", "list"):
            marks = ", ".join(m["raw"] for m in p.get("cite_marks", [])) or "无标记"
            lines.append(f"### {p['pid']}（{p['kind']}，现有标记: {marks}）")
            lines.append(p["text"])
            lines.append("")
    lines += ["## B. 文献库目录（引用只能从这里选 id）", ""]
    for r in lib.get("records", []):
        auth = (r.get("authors") or ["?"])[0]
        lines.append(f"- **{r['id']}** [{r.get('entry_type')}] {r.get('title','')} | "
                     f"{auth} | {r.get('year','?')} | {r.get('venue','')}")
    lines += ["", "## C. 决策文件写法（/app/work/citation_decisions.jsonl，每行一条）",
              '```json',
              '{"claim_id":"C1","pid":"P002","sentence":"<从段落原文逐字复制的论断句>",'
              '"claim_type":"量化事实","entry_ids":["R001"],"rationale":"<为何该条目支撑>",'
              '"position":"after_sentence","form":"numeric"}',
              '```']
    ws = os.path.join(W, "claims_worksheet.md")
    with open(ws, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n===== 论断工作单已写 {ws}（{len(ms.get('paragraphs', []))} 段 / "
          f"{len(lib.get('records', []))} 条文献）=====")
    print("Agent：读工作单 → 写 /app/work/citation_decisions.jsonl → 跑 --stage finish")
    return 0

def stage_finish(args):
    W, O = args.work, args.out
    dec = os.path.join(W, "citation_decisions.jsonl")
    if not os.path.exists(dec):
        print("  | citation_decisions.jsonl 缺失——以空决策交付审计基线（status=partial）")
        open(dec, "w").close()
        save_json(os.path.join(W, "exceptions.json"),
                  ["Agent 未提供 citation_decisions.jsonl，仅交付原稿与文献表"])
    ms_path = os.path.join(W, "manuscript.json")
    lib_path = os.path.join(W, "library.json")
    print("== finish [1/3] place_citations（引擎）")
    run(["python3", f"{HERE}/place_citations.py", "--decisions", dec,
         "--manuscript", ms_path, "--library", lib_path, "--out", O, "--work", W])
    audit = load_json(os.path.join(W, "placement_audit.json"), {}) or {}
    lib = load_json(lib_path, {}) or {}
    nrefs = len(lib.get("records", []))
    ms_rn = os.path.join(W, "manuscript.renumbered.json")
    audit_src = ms_rn if os.path.exists(ms_rn) else ms_path
    if os.path.exists(audit_src) and nrefs:
        print("== finish [2/3] 一致性 audit")
        run(["python3", f"{HERE}/cite_engine.py", "audit", "--manuscript", audit_src,
             "--nrefs", str(nrefs)])
        src = os.path.join(W, "consistency_audit.json")
        if os.path.exists(src):
            shutil.copy(src, os.path.join(O, "consistency_audit.json"))
    # evidence/change/stats 汇总
    n_dec = sum(1 for l in open(dec, encoding="utf-8") if l.strip()) if os.path.exists(dec) else 0
    decisions = [json.loads(l) for l in open(dec, encoding="utf-8")
                 if l.strip()] if os.path.exists(dec) else []
    if decisions and not os.path.exists(os.path.join(W, "evidence_map.json")):
        save_json(os.path.join(W, "evidence_map.json"),
                  [{"claim_id": d.get("claim_id"), "location": d.get("pid"),
                    "source": d.get("sentence", "")[:150],
                    "support": f"引用条目 {d.get('entry_ids')}",
                    "rationale": d.get("rationale", "")} for d in decisions])
    save_json(os.path.join(W, "stats.json"),
              {"n_decisions": n_dec, "n_refs": nrefs,
               "misplaced_after": audit.get("misplaced_after_insert", audit.get("inserted_misplaced"))})
    status = "success" if n_dec else "partial"
    print(f"== finish [3/3] assemble / validate / preview（status={status}）")
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
    ap.add_argument("--skill", default="citation-placement-skill v2.0.0")
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True); os.makedirs(args.out, exist_ok=True)
    rc = stage_prep(args) if args.stage == "prep" else stage_finish(args)
    print(f"[run_pipeline] {args.stage} DONE")
    return rc

if __name__ == "__main__":
    sys.exit(main())
