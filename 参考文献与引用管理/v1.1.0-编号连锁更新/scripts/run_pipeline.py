#!/usr/bin/env python3
"""run_pipeline.py — 编号连锁更新「一命令全流水线」编排器（v1.1.0 新增）。

对 v1.0.1 的唯一机制增量：把 Phase 0-5 的六条命令编排为一条命令，自动完成
初始化→案例侦察→稿件/文献库解析→文末列表基准抽取→任务书编辑指令自动派生（保守启发式，
逐条留痕）→引擎连锁更新（悬空自动处置：仅删除被删条目的正文标记并全程留痕）→
evidence_map/change_log 自动生成→result.json 契约组装→发布闸门→预览渲染。
Agent 只需跑这一条命令；如需人工介入，见 SKILL.md 的「人工覆盖」两阶段用法。

用法: python3 scripts/run_pipeline.py [--input /input] [--out /app/output] [--work /app/work]
                                      [--stage all|prep|finish] [--skill "name vX"]
exit 0 = 交付完成（validate PASS），exit 1 = 有 critical（已以 partial 降级交付）。
"""
import argparse, json, os, re, subprocess, sys, shutil

HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    out = (r.stdout or "") + (r.stderr or "")
    for line in out.strip().splitlines()[-3:]:
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

# ---------- 文末列表基准抽取 ----------
def derive_reference_list(manuscript_path, work):
    """从 reference_list 段抽取条目；同段内多个 [n] 条目按标记切分。"""
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
        else:
            marks2 = list(re.finditer(r"(?:^|\s)(\d{1,3})[.)、]\s+", text))
            for i, m in enumerate(marks2):
                end = marks2[i + 1].start() if i + 1 < len(marks2) else len(text)
                entries.append({"num": int(m.group(1)), "text": text[m.end():end].strip()})
    # 按 num 去重（首见为准）并按编号排序
    seen = {}
    for e in entries:
        seen.setdefault(e["num"], e["text"])
    entries = [{"num": n, "text": seen[n]} for n in sorted(seen)]
    if entries:
        save_json(os.path.join(work, "reference_list.json"), entries)
    return entries

# ---------- 任务书编辑指令自动派生（保守启发式） ----------
DELETE_CUE = re.compile(r"(删除|移除|去掉|不再引用|撤稿|retract|remove|drop|delete)", re.I)
INSERT_CUE = re.compile(r"(插入|补充|加入|新增|补引|insert|add)\s*(文献|引用|reference)?", re.I)
NUM_AFTER = re.compile(r"\[?(\d{1,3})\]?")

def derive_edit_ops(task_text, ref_entries, library, work):
    """只从任务书明确句子派生；定位失败一律进 manual_confirmations，不猜。"""
    ops, evidence, manual = [], [], []
    ref_by_num = {e["num"]: e["text"] for e in ref_entries}
    records = (library or {}).get("records", [])

    def add_ev(op, sentence, matched):
        ops.append(op)
        evidence.append({"op": op["op"], "ref_id": op.get("ref_id"),
                         "location": "task.md", "source": sentence.strip()[:200],
                         "support": f"任务书指令自动派生；命中片段「{matched}」",
                         "rationale": "保守启发式：仅处理带编号/唯一题名定位的明确指令"})

    for sentence in re.split(r"[。；;\n]", task_text):
        s = sentence.strip()
        if not s:
            continue
        if DELETE_CUE.search(s):
            nums = sorted({int(n) for n in NUM_AFTER.findall(s)})
            if not nums:
                # 尝试按题名短语唯一定位
                hits = [e for e in ref_entries
                        if any(k in e["text"] for k in re.findall(r"[一-龥]{4,}|[A-Za-z][A-Za-z ]{6,}", s))]
                if len(hits) == 1:
                    add_ev({"op": "delete", "ref_id": hits[0]["num"],
                            "note": f"task.md 自动派生（题名定位）: {s[:80]}"}, s, hits[0]["text"][:40])
                else:
                    manual.append({"item": s[:200], "reason": "删除指令无编号且题名定位不唯一，需人工确认",
                                   "auto_action": "未执行删除，按恒等映射交付"})
                continue
            for n in nums:
                if n in ref_by_num or not ref_entries:
                    add_ev({"op": "delete", "ref_id": n,
                            "note": f"task.md 自动派生: {s[:80]}"}, s, f"[{n}]")
                else:
                    manual.append({"item": s[:200], "reason": f"编号 {n} 超出当前列表范围",
                                   "auto_action": "跳过该删除"})
        elif INSERT_CUE.search(s):
            hits = [r for r in records
                    if r.get("title") and any(k.lower() in r["title"].lower()
                        for k in re.findall(r"[A-Za-z][A-Za-z ]{6,}|[一-龥]{4,}", s))]
            if len(hits) == 1:
                add_ev({"op": "insert_existing", "ref_id": hits[0]["id"], "to": len(ref_entries) + 1,
                        "note": f"task.md 自动派生（题名定位）: {s[:80]}"}, s, hits[0]["title"][:40])
            else:
                manual.append({"item": s[:200], "reason": "插入指令未能唯一定位库内条目，需人工确认",
                               "auto_action": "未执行插入"})
    if ops:
        save_json(os.path.join(work, "edit_ops.json"), ops)
    return ops, evidence, manual

# ---------- 悬空自动处置 ----------
def fix_dangling(work, report_path):
    rep = load_json(report_path, {}) or {}
    dangling = rep.get("dangling_refs") or []
    if not dangling:
        return 0
    ms_path = os.path.join(work, "manuscript.json")
    ms = load_json(ms_path)
    if not ms:
        return 0
    removed = 0
    dead = set()
    for d in dangling:
        dead.update(d.get("dangling_old_nums") or d.get("nums")
                    or ([d.get("num")] if d.get("num") else []))
    if not dead:
        return 0
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
            keep = [n for n in nums if n not in dead]
            if len(keep) == len(nums):
                return m.group(0)
            removed += len(nums) - len(keep)
            if not keep:
                return ""
            ks = sorted(set(keep))
            segs, st, pv = [], ks[0], ks[0]
            for n in ks[1:]:
                if n == pv + 1:
                    pv = n; continue
                segs.append(f"{st}-{pv}" if pv > st else str(st)); st = pv = n
            segs.append(f"{st}-{pv}" if pv > st else str(st))
            return "[" + ",".join(segs) + "]"
        p["text"] = pat.sub(repl, p["text"])
        # 同步刷新 cite_marks（引擎悬空检测会读取）
        p["cite_marks"] = [{"raw": m.group(0), "style": "numeric",
                            "nums": expand(m.group(1)), "span": [m.start(), m.end()]}
                           for m in pat.finditer(p["text"])]
    save_json(ms_path, ms)
    return removed

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--stage", default="all", choices=["all", "prep", "finish"])
    ap.add_argument("--skill", default="citation-renumber-chain v1.1.0")
    args = ap.parse_args()
    W, O = args.work, args.out
    os.makedirs(W, exist_ok=True); os.makedirs(O, exist_ok=True)
    exceptions, uncertainty = [], []

    # ---- prep: 初始化 + 侦察 + 解析 + 派生 ----
    if args.stage in ("all", "prep"):
        print("== [1/5] init_result / inspect_case")
        run(["python3", f"{HERE}/init_result.py", "--case", f"{args.input}/case.json", "--out", O])
        run(["python3", f"{HERE}/inspect_case.py", "--case", f"{args.input}/case.json",
             "--task", f"{args.input}/task.md", "--input-dir", args.input, "--work", W])
        insp = load_json(os.path.join(W, "inspection.json"), {}) or {}
        ms_cands = [c["path"] for c in insp.get("manuscript_candidates", [])]
        lib_cands = [c["path"] for c in insp.get("library_candidates", [])
                     if c.get("library_format") not in ("pdf", "docx")]
        if not ms_cands:
            ms_cands = [c["path"] for c in insp.get("manuscript_candidates", [])]
        if not ms_cands:
            exceptions.append("未找到稿件文件，仅交付案例侦察结果")
        else:
            print("== [2/5] parse_manuscript")
            run(["python3", f"{HERE}/parse_manuscript.py", ms_cands[0], "--work", W])
        if lib_cands:
            print("== [3/5] parse_library")
            run(["python3", f"{HERE}/parse_library.py"] + lib_cands + ["--work", W])
        else:
            save_json(os.path.join(W, "library.json"), {"records": [], "issues": ["无文献库"], "count": 0})
            uncertainty.append("无独立文献库文件；文末列表基准仅依赖稿件自带列表")
        ms_path = os.path.join(W, "manuscript.json")
        ref_entries = derive_reference_list(ms_path, W)
        print(f"  | 文末列表基准: {len(ref_entries)} 条")
        # 一致性保护：抽取的列表最大编号 < 正文最大引用编号时，抽取多半有误，
        # 放弃列表基准，改用文献库顺序，并记 uncertainty（宁保守不误删）。
        if ref_entries and os.path.exists(ms_path):
            ms_obj = load_json(ms_path, {}) or {}
            max_inline = max([n for p in ms_obj.get("paragraphs", [])
                              for m in p.get("cite_marks", []) for n in m.get("nums", [])],
                             default=0)
            lib = load_json(os.path.join(W, "library.json"), {}) or {}
            if max_inline > max(e["num"] for e in ref_entries) \
                    and len(lib.get("records", [])) >= max_inline:
                os.remove(os.path.join(W, "reference_list.json"))
                ref_entries = []
                uncertainty.append(
                    f"文末列表抽取异常（列表最大编号 < 正文最大引用编号 {max_inline}），"
                    "已改用文献库顺序作为列表基准；请人工核对")
                print("  | 保护: 列表抽取异常，改用文献库基准")
        # 任务书指令派生（仅当人工 edit_ops.json 不存在时）
        if not os.path.exists(os.path.join(W, "edit_ops.json")):
            task = ""
            for c in (f"{args.input}/task.md",):
                if os.path.exists(c):
                    task = open(c, encoding="utf-8", errors="ignore").read()
            lib = load_json(os.path.join(W, "library.json"), {}) or {}
            ops, evidence, manual = derive_edit_ops(task, ref_entries, lib, W)
            if ops:
                save_json(os.path.join(W, "evidence_map.json"), evidence)
            if manual:
                save_json(os.path.join(W, "manual_confirmations.json"), manual)
            print(f"  | 任务书编辑指令自动派生: {len(ops)} 条操作, {len(manual)} 条待人工确认")
        else:
            print("  | 检测到人工 work/edit_ops.json，跳过自动派生")

    # ---- finish: 引擎 → 悬空处置 → 审计 → 汇总 → 闸门 → 预览 ----
    if args.stage in ("all", "finish"):
        print("== [4/5] renumber_plan（连锁更新引擎）")
        ms_path = os.path.join(W, "manuscript.json")
        if os.path.exists(ms_path):
            r = run(["python3", f"{HERE}/renumber_plan.py", "--work", W, "--out", O,
                     "--engine", f"{HERE}/cite_engine.py"])
            if r.returncode != 0:
                rep_path = os.path.join(W, "renumber_report.json")
                n_removed = fix_dangling(W, rep_path)
                if n_removed:
                    print(f"  | 悬空处置: 自动移除 {n_removed} 个指向被删条目的正文标记（留痕）")
                    chg = load_json(os.path.join(W, "change_log.json"), []) or []
                    chg.append({"op": "auto_remove_dangling_marks", "location": "正文/图表注段落",
                                "before": f"{n_removed} 个悬空标记", "after": "已移除",
                                "reason": "删除条目后正文标记悬空，按引擎报告自动清理；如需保留请人工改写"})
                    save_json(os.path.join(W, "change_log.json"), chg)
                    uncertainty.append(f"悬空处置为自动清理（{n_removed} 处），语义润色需人工复核")
                    r = run(["python3", f"{HERE}/renumber_plan.py", "--work", W, "--out", O,
                             "--engine", f"{HERE}/cite_engine.py"])
        else:
            print("  | manuscript.json 缺失，跳过引擎（仅侦察交付）")
            save_json(os.path.join(W, "exceptions.json"), (load_json(os.path.join(W, "exceptions.json"), []) or []) + exceptions)
        # 终检 audit
        rep = load_json(os.path.join(W, "renumber_report.json"), {}) or {}
        nrefs = (rep.get("invariants") or {}).get("list_entries") or len(ref_entries) or 0
        ms_rn = os.path.join(W, "manuscript.renumbered.json")
        if nrefs and os.path.exists(ms_rn):
            run(["python3", f"{HERE}/cite_engine.py", "audit", "--manuscript", ms_rn,
                 "--nrefs", str(nrefs)])
            src = os.path.join(W, "consistency_audit.json")
            if os.path.exists(src):
                shutil.copy(src, os.path.join(O, "consistency_audit.json"))
        # change_log 从 mapping 自动生成
        chg = load_json(os.path.join(W, "change_log.json"), []) or []
        for old, new in (rep.get("mapping") or {}).items():
            chg.append({"op": "renumber", "location": "正文+文末列表",
                        "before": f"[{old}]", "after": "删除" if new is None else f"[{new}]",
                        "reason": "edit_ops 驱动的连锁重排（引擎 mapping）"})
        save_json(os.path.join(W, "change_log.json"), chg)
        stats = {"n_ops": rep.get("n_ops", 0), "style": rep.get("style"),
                 "invariants_pass": rep.get("PASS"), "n_refs": nrefs}
        save_json(os.path.join(W, "stats.json"), stats)
        if uncertainty and not os.path.exists(os.path.join(W, "uncertainty.json")):
            save_json(os.path.join(W, "uncertainty.json"), uncertainty)
        if exceptions and not os.path.exists(os.path.join(W, "exceptions.json")):
            save_json(os.path.join(W, "exceptions.json"), exceptions)
        # edited manuscript 落盘（若引擎未产出）
        if not os.path.exists(os.path.join(O, "edited_manuscript.md")) and os.path.exists(ms_path):
            ms = load_json(ms_path, {}) or {}
            if ms.get("paragraphs"):
                with open(os.path.join(O, "edited_manuscript.md"), "w", encoding="utf-8") as f:
                    for p in ms["paragraphs"]:
                        f.write(p["text"] + "\n\n")
        passed = bool(rep.get("PASS", True))
        status = "success" if passed else "partial"
        print(f"== [5/5] assemble / validate / preview（status={status}）")
        run(["python3", f"{HERE}/assemble_result.py", "--work", W, "--out", O,
             "--case", f"{args.input}/case.json", "--skill", args.skill, "--status", status])
        rv = run(["python3", f"{HERE}/validate_output.py", "--out", O])
        run(["python3", f"{HERE}/render_previews.py", "--out", O])
        if rv.returncode != 0:
            print("[run_pipeline] validate 有 critical，已以 partial 交付并记录")
            return 1
    print("[run_pipeline] DONE")
    return 0

if __name__ == "__main__":
    sys.exit(main())
