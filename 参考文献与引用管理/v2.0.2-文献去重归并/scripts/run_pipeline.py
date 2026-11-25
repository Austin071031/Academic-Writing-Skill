#!/usr/bin/env python3
"""run_pipeline.py — 文献去重归并编排器（v2.0.2）。

v2.0.2 唯一机制增量（父版 v1.0.2，attempt 89251，57 分）：六阶段压缩为 prep/finish 两步；
prep 生成「裁决工作单」（候选组+信号一屏呈现），Agent 只需逐组写
merge_decisions.jsonl，apply/报告/组装全部脚本化。

用法:
  python3 scripts/run_pipeline.py --stage prep
  # Agent 读工作单 → 写 /app/work/merge_decisions.jsonl
  python3 scripts/run_pipeline.py --stage finish
"""
import argparse, json, os, subprocess, sys

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
    print("== prep [1/2] init_result / inspect_case / parse_library")
    run(["python3", f"{HERE}/init_result.py", "--case", f"{args.input}/case.json", "--out", O])
    run(["python3", f"{HERE}/inspect_case.py", "--case", f"{args.input}/case.json",
         "--task", f"{args.input}/task.md", "--input-dir", args.input, "--work", W])
    insp = load_json(os.path.join(W, "inspection.json"), {}) or {}
    lib_cands = [c["path"] for c in insp.get("library_candidates", [])
                 if c.get("library_format") not in ("pdf", "docx")]
    # 无独立文献库时尝试稿件候选中的列表文件
    if not lib_cands:
        lib_cands = [c["path"] for c in insp.get("manuscript_candidates", [])]
    if lib_cands:
        run(["python3", f"{HERE}/parse_library.py"] + lib_cands + ["--work", W])
    else:
        save_json(os.path.join(W, "library.json"), {"records": [], "issues": ["无文献库"], "count": 0})
    lib_path = os.path.join(W, "library.json")
    print("== prep [2/2] dedup_engine candidates")
    run(["python3", f"{HERE}/dedup_engine.py", "candidates", "--library", lib_path, "--work", W])
    # 裁决工作单
    lib = load_json(lib_path, {}) or {}
    byid = {r["id"]: r for r in lib.get("records", [])}
    cands = load_json(os.path.join(W, "merge_candidates.json"), {}) or {}
    groups = cands.get("groups") or cands.get("candidate_groups") or []
    lines = ["# 去重裁决工作单（Agent 逐组写 merge_decisions.jsonl）", ""]
    for g in groups:
        gid = g.get("group_id") or g.get("id")
        members = g.get("members") or g.get("records") or g.get("rids") or []
        lines.append(f"## {gid}（{len(members)} 条候选）")
        for rid in members:
            r = byid.get(rid, {})
            lines.append(f"- **{rid}** [{r.get('entry_type')}] {r.get('title','')} | "
                         f"{(r.get('authors') or ['?'])[0]} | {r.get('year','?')} | "
                         f"{r.get('venue','')} | DOI:{r.get('doi') or '无'} | 来源:{r.get('source_file')}")
        for pair in (g.get("signals") or g.get("pairs") or []):
            lines.append(f"  信号: {json.dumps(pair, ensure_ascii=False)[:200]}")
        lines.append("")
    prot = cands.get("protected_pairs") or []
    if prot:
        lines.append("## 保护对（禁止合并，疑似同名不同文）")
        for pp in prot:
            lines.append(f"- {json.dumps(pp, ensure_ascii=False)[:180]}")
        lines.append("")
    lines += ["## 决策文件写法（/app/work/merge_decisions.jsonl，每组一行）", "```json",
              '{"group_id":"G1","action":"merge","keep_rid":"R001","drop_rids":["R002","R003"],'
              '"rationale":"<合并依据，引用信号值>"}',
              '{"group_id":"G2","action":"keep_separate","rationale":"<不合并依据>"}', "```"]
    ws = os.path.join(W, "verdict_worksheet.md")
    with open(ws, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    n = len(lib.get("records", []))
    print(f"\n===== 裁决工作单已写 {ws}（{n} 条记录，{len(groups)} 个候选组）=====")
    print("Agent：读工作单 → 写 /app/work/merge_decisions.jsonl → 跑 --stage finish")
    return 0

def stage_finish(args):
    W, O = args.work, args.out
    lib_path = os.path.join(W, "library.json")
    dec = os.path.join(W, "merge_decisions.jsonl")
    if not os.path.exists(dec):
        print("  | merge_decisions.jsonl 缺失——仅交付候选报告（status=partial）")
        save_json(os.path.join(W, "exceptions.json"), ["Agent 未提供裁决，未执行合并"])
    else:
        print("== finish [1/2] dedup_engine apply")
        run(["python3", f"{HERE}/dedup_engine.py", "apply", "--library", lib_path,
             "--decisions", dec, "--work", W, "--out", O])
        # 合并后渲染 GB/T 参考文献表（与父版交付对齐）
        deduped_path = os.path.join(O, "library_deduped.json")
        if os.path.exists(deduped_path):
            run(["python3", f"{HERE}/cite_engine.py", "render", "--records", deduped_path,
                 "--style", "gbt2015_numeric", "--out", os.path.join(O, "references.md")])
    lib = load_json(lib_path, {}) or {}
    deduped = load_json(os.path.join(O, "library_deduped.json"),
                        load_json(os.path.join(W, "library_deduped.json"), {}) or {}) or {}
    n_out = len(deduped.get("records", []))
    decisions = [json.loads(l) for l in open(dec, encoding="utf-8")
                 if l.strip()] if os.path.exists(dec) else []
    if decisions and not os.path.exists(os.path.join(W, "evidence_map.json")):
        save_json(os.path.join(W, "evidence_map.json"),
                  [{"group_id": d.get("group_id"), "location": "verdict_worksheet",
                    "source": f"action={d.get('action')} keep={d.get('keep_rid')}",
                    "support": "信号表见 merge_report", "rationale": d.get("rationale", "")}
                   for d in decisions])
    save_json(os.path.join(W, "stats.json"),
              {"n_records_in": len(lib.get("records", [])), "n_records_out": n_out,
               "n_groups_decided": len(decisions)})
    status = "success" if decisions else "partial"
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
    ap.add_argument("--skill", default="ref-dedup-merge v2.0.2")
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True); os.makedirs(args.out, exist_ok=True)
    rc = stage_prep(args) if args.stage == "prep" else stage_finish(args)
    print(f"[run_pipeline] {args.stage} DONE")
    return rc

if __name__ == "__main__":
    sys.exit(main())
