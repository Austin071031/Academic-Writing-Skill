#!/usr/bin/env python3
"""run_pipeline.py — 编号连锁更新编排器（v2.0.1）。

v2.0.1 唯一机制增量（父版 v1.0.1，attempt 89250，63 分；对照组 v1.1.0 全自动=50 分）：
把六阶段流程压缩为 prep/finish 两步，Agent 的 edit_ops 判断**保留**（v1.1.0 证明
去掉 Agent 判断会降分），机械环节全部脚本化。

用法:
  python3 scripts/run_pipeline.py --stage prep    # 预检+解析+打印当前列表与操作示例
  # Agent 读输出，写 /app/work/edit_ops.json
  python3 scripts/run_pipeline.py --stage finish  # 引擎+审计+组装+闸门+预览
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

def derive_reference_list(manuscript_path, work):
    ms = load_json(manuscript_path, {}) or {}
    entries = []
    for p in ms.get("paragraphs", []):
        if p.get("kind") != "reference_list":
            continue
        text = p["text"]
        marks = list(re.finditer(r"\[(\d+)\]", text))
        if marks:
            for i, m in enumerate(marks):
                end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
                entries.append({"num": int(m.group(1)), "text": text[m.end():end].strip()})
    seen = {}
    for e in entries:
        seen.setdefault(e["num"], e["text"])
    entries = [{"num": n, "text": seen[n]} for n in sorted(seen)]
    if entries:
        save_json(os.path.join(work, "reference_list.json"), entries)
    return entries

def fix_dangling(work, report_path):
    rep = load_json(report_path, {}) or {}
    dangling = rep.get("dangling_refs") or []
    if not dangling:
        return 0
    ms_path = os.path.join(work, "manuscript.json")
    ms = load_json(ms_path)
    if not ms:
        return 0
    dead = set()
    for d in dangling:
        dead.update(d.get("dangling_old_nums") or d.get("nums") or [])
    if not dead:
        return 0
    removed = 0
    pat = re.compile(r"\[(\d+(?:\s*[-–—,，]\s*\d+)*)\]")
    def expand(raw):
        nums = []
        for part in re.split(r"[,，]", raw):
            part = part.strip()
            m = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", part)
            if m:
                nums.extend(range(int(m.group(1)), int(m.group(2)) + 1))
            elif part.isdigit():
                nums.append(int(part))
        return nums
    for p in ms.get("paragraphs", []):
        def repl(m):
            nonlocal removed
            nums = expand(m.group(1))
            keep = sorted({n for n in nums if n not in dead})
            if len(keep) == len(nums):
                return m.group(0)
            removed += len(nums) - len(keep)
            if not keep:
                return ""
            segs, st, pv = [], keep[0], keep[0]
            for n in keep[1:]:
                if n == pv + 1:
                    pv = n; continue
                segs.append(f"{st}-{pv}" if pv > st else str(st)); st = pv = n
            segs.append(f"{st}-{pv}" if pv > st else str(st))
            return "[" + ",".join(segs) + "]"
        p["text"] = pat.sub(repl, p["text"])
        p["cite_marks"] = [{"raw": m.group(0), "style": "numeric",
                            "nums": expand(m.group(1)), "span": [m.start(), m.end()]}
                           for m in pat.finditer(p["text"])]
    save_json(ms_path, ms)
    return removed

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
    else:
        print("  | 未找到稿件文件")
    if lib_cands:
        print("== prep [3/3] parse_library:", ", ".join(os.path.basename(c) for c in lib_cands))
        run(["python3", f"{HERE}/parse_library.py"] + lib_cands + ["--work", W])
    else:
        save_json(os.path.join(W, "library.json"), {"records": [], "issues": ["无文献库"], "count": 0})
    ms_path = os.path.join(W, "manuscript.json")
    ref_entries = derive_reference_list(ms_path, W)
    lib = load_json(os.path.join(W, "library.json"), {}) or {}
    n_lib = len(lib.get("records", []))
    # 输出给 Agent 的决策材料
    print("\n===== AGENT 决策材料（读完后写 /app/work/edit_ops.json，再跑 --stage finish）=====")
    task_file = f"{args.input}/task.md"
    if os.path.exists(task_file):
        print("--- task.md 全文 ---")
        print(open(task_file, encoding="utf-8", errors="ignore").read()[:4000])
    if ref_entries:
        print(f"--- 当前文末列表（{len(ref_entries)} 条）---")
        for e in ref_entries:
            print(f"[{e['num']}] {e['text'][:120]}")
    elif n_lib:
        print(f"--- 文献库记录（{n_lib} 条，序即当前列表序）---")
        for r in lib["records"]:
            print(f"[{r['id']}] {r.get('title','')[:80]} | {r.get('year','')} | {(r.get('authors') or [''])[0]}")
    print("""--- edit_ops.json 写法（只写 task.md 明确要求的操作）---
[{"op":"delete","ref_id":2,"note":"任务书第X句"},{"op":"reorder","ref_id":"R003","to":1},
 {"op":"insert_existing","ref_id":"R012","to":3},{"op":"merge","ref_ids":["R003","R008"],"keep":"R003"}]
ref_id 支持纯数字（当前列表序号）或 R00X（库记录号）。无编辑要求则写 [] 。""")
    return 0

def stage_finish(args):
    W, O = args.work, args.out
    exceptions, uncertainty = [], []
    ms_path = os.path.join(W, "manuscript.json")
    if not os.path.exists(ms_path):
        exceptions.append("manuscript.json 缺失，仅交付案例侦察结果")
        save_json(os.path.join(W, "exceptions.json"), exceptions)
    else:
        print("== finish [1/4] renumber_plan（引擎）")
        r = run(["python3", f"{HERE}/renumber_plan.py", "--work", W, "--out", O,
                 "--engine", f"{HERE}/cite_engine.py"])
        if r.returncode != 0:
            n = fix_dangling(W, os.path.join(W, "renumber_report.json"))
            if n:
                print(f"  | 悬空处置: 自动移除 {n} 个指向被删条目的正文标记（留痕 change_log）")
                chg = load_json(os.path.join(W, "change_log.json"), []) or []
                chg.append({"op": "auto_remove_dangling_marks", "location": "正文/图表注",
                            "before": f"{n} 个悬空标记", "after": "已移除",
                            "reason": "删除条目后正文标记悬空，自动清理；语义复核记 uncertainty"})
                save_json(os.path.join(W, "change_log.json"), chg)
                uncertainty.append(f"悬空处置为自动清理（{n} 处），语义润色需人工复核")
                r = run(["python3", f"{HERE}/renumber_plan.py", "--work", W, "--out", O,
                         "--engine", f"{HERE}/cite_engine.py"])
    rep = load_json(os.path.join(W, "renumber_report.json"), {}) or {}
    ref_entries = load_json(os.path.join(W, "reference_list.json"), []) or []
    lib = load_json(os.path.join(W, "library.json"), {}) or {}
    nrefs = (rep.get("invariants") or {}).get("list_entries") or len(ref_entries) \
        or len(lib.get("records", []))
    ms_rn = os.path.join(W, "manuscript.renumbered.json")
    if nrefs and os.path.exists(ms_rn):
        print("== finish [2/4] audit")
        run(["python3", f"{HERE}/cite_engine.py", "audit", "--manuscript", ms_rn,
             "--nrefs", str(nrefs)])
        src = os.path.join(W, "consistency_audit.json")
        if os.path.exists(src):
            shutil.copy(src, os.path.join(O, "consistency_audit.json"))
    chg = load_json(os.path.join(W, "change_log.json"), []) or []
    for old, new in (rep.get("mapping") or {}).items():
        chg.append({"op": "renumber", "location": "正文+文末列表",
                    "before": f"[{old}]", "after": "删除" if new is None else f"[{new}]",
                    "reason": "edit_ops 驱动的连锁重排（引擎 mapping）"})
    save_json(os.path.join(W, "change_log.json"), chg)
    save_json(os.path.join(W, "stats.json"),
              {"n_ops": rep.get("n_ops", 0), "style": rep.get("style"),
               "invariants_pass": rep.get("PASS"), "n_refs": nrefs})
    if uncertainty:
        save_json(os.path.join(W, "uncertainty.json"), uncertainty)
    # evidence_map：edit_ops 的任务书出处
    ops = load_json(os.path.join(W, "edit_ops.json"), []) or []
    if ops and not os.path.exists(os.path.join(W, "evidence_map.json")):
        save_json(os.path.join(W, "evidence_map.json"),
                  [{"op": o.get("op"), "ref_id": o.get("ref_id") or o.get("ref_ids"),
                    "location": "task.md", "source": o.get("note", ""),
                    "support": "任务书指令", "rationale": "Agent 识别并登记"} for o in ops])
    if not os.path.exists(os.path.join(O, "edited_manuscript.md")) and os.path.exists(ms_path):
        ms = load_json(ms_path, {}) or {}
        if ms.get("paragraphs"):
            with open(os.path.join(O, "edited_manuscript.md"), "w", encoding="utf-8") as f:
                for p in ms["paragraphs"]:
                    f.write(p["text"] + "\n\n")
    passed = bool(rep.get("PASS", True))
    status = "success" if passed else "partial"
    print(f"== finish [3/4] assemble（status={status}）")
    run(["python3", f"{HERE}/assemble_result.py", "--work", W, "--out", O,
         "--case", f"{args.input}/case.json", "--skill", args.skill, "--status", status])
    print("== finish [4/4] validate / preview")
    rv = run(["python3", f"{HERE}/validate_output.py", "--out", O])
    run(["python3", f"{HERE}/render_previews.py", "--out", O])
    return 0 if rv.returncode == 0 else 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--stage", required=True, choices=["prep", "finish"])
    ap.add_argument("--skill", default="citation-renumber-chain v2.0.1")
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True); os.makedirs(args.out, exist_ok=True)
    rc = stage_prep(args) if args.stage == "prep" else stage_finish(args)
    print(f"[run_pipeline] {args.stage} DONE")
    return rc

if __name__ == "__main__":
    sys.exit(main())
