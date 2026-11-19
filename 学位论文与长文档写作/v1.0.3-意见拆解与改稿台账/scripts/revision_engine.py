#!/usr/bin/env python3
"""revision_engine.py — 意见拆解与改稿落实台账引擎（纯 Python3 标准库）。

子命令:
  parse   拆解组织方工单/任务文本 → work/workorder_items.json
  locate  为每条意见定位目标段落候选 pid + 冲突检测
  apply   执行 Agent 修改决策 → 修订章节 + 落实台账 + diff 报告
  version 按轮次汇总 → work/version_report.json（含回退说明）

红线: 修改保留作者原意（只动 Agent 指定段落）；无法落实如实标注；
before/after 一律来自真实文本（chapters.json 段落原文 / 文件实读）。
"""
import argparse, difflib, json, os, re, shutil, sys, datetime

TYPES = ["补充", "删除", "改写", "结构调整", "格式", "引用", "其他"]
TYPE_RULES = [
    ("补充", r"(补充|添加|增加|增补|补上|写明|加入)"),
    ("删除", r"(删除|删去|去掉|去除|移除)"),
    ("改写", r"(改写|重写|修改|改为|调整为|表述为|换成)"),
    ("结构调整", r"(结构|顺序|移动|合并|拆分|调至|挪到)"),
    ("格式", r"(格式|排版|统一|字体|编号样式|对齐)"),
    ("引用", r"(引用|文献|注释|出处|参考文献|citation|reference)"),
]
TASK_VERBS = r"(修改|补充|删除|改写|调整|统一|检查|完善|核对|订正|增补)"
OPPOSITE = {("补充", "删除"), ("删除", "补充")}

# ---------------------------------------------------------------- 公共工具

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, obj):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def norm_text(s):
    return re.sub(r"\s+", " ", s or "").strip()

def char_ngrams(s, n=2):
    s = re.sub(r"[^\w一-鿿]+", "", (s or "").lower())
    return {s[i:i + n] for i in range(len(s) - n + 1)} if len(s) >= n else ({s} if s else set())

def classify_type(raw_type, content):
    for t, pat in TYPE_RULES:
        if raw_type and re.search(pat, raw_type):
            return t
    for t, pat in TYPE_RULES:
        if content and re.search(pat, content):
            return t
    return "其他"

def excerpt(s, limit=220):
    s = norm_text(s)
    return s if len(s) <= limit else s[:limit] + "…"

# ---------------------------------------------------------------- parse

def iter_workorder_items(data):
    """兼容多种工单结构，产出 (round_no, raw_item) 序列。"""
    rounds = None
    if isinstance(data, dict):
        for key in ("rounds", "items", "opinions", "comments", "edits"):
            if isinstance(data.get(key), list):
                rounds = data[key] if key == "rounds" else [{"round": 1, "opinions": data[key]}]
                break
        if rounds is None:  # 单条意见形式的 dict
            if any(k in data for k in ("id", "content", "opinion", "target")):
                rounds = [{"round": 1, "opinions": [data]}]
    elif isinstance(data, list):
        rounds = [{"round": 1, "opinions": data}]
    for rd in rounds or []:
        if not isinstance(rd, dict):
            continue
        rno = rd.get("round", rd.get("round_no", rd.get("index", 1)))
        ops = None
        for key in ("opinions", "items", "comments", "edits"):
            if isinstance(rd.get(key), list):
                ops = rd[key]
                break
        if ops is None and any(k in rd for k in ("id", "content", "opinion")):
            ops = [rd]
        for op in ops or []:
            if isinstance(op, dict):
                yield rno, op
            elif isinstance(op, str) and op.strip():
                yield rno, {"content": op.strip()}

def parse_from_workorder(path):
    data = load_json(path)
    if data is None:
        return None, f"工单文件无法解析: {path}"
    items = []
    for i, (rno, op) in enumerate(iter_workorder_items(data), 1):
        content = op.get("content") or op.get("opinion") or op.get("text") or op.get("comment") or ""
        raw_type = op.get("type") or op.get("category") or op.get("kind") or ""
        items.append({
            "rid": str(op.get("id") or op.get("rid") or op.get("no") or f"W{i}"),
            "round": rno,
            "target_file": op.get("target") or op.get("target_file") or op.get("file") or op.get("path"),
            "type": classify_type(str(raw_type), str(content)),
            "content": str(content).strip(),
            "status": "pending",
        })
    return items, None

def parse_from_task(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    items = []
    for line in text.splitlines():
        line = line.strip().lstrip("#-*•>0123456789.、)） ").strip()
        if len(line) >= 6 and re.search(TASK_VERBS, line):
            items.append({
                "rid": f"T{len(items) + 1}",
                "round": 0,
                "target_file": None,
                "type": classify_type(None, line),
                "content": line,
                "status": "pending",
                "source": "task.md 规则抽取（非组织方工单，需人工确认）",
            })
    return items

def cmd_parse(args):
    items, note = None, None
    if args.workorder and os.path.exists(args.workorder):
        items, err = parse_from_workorder(args.workorder)
        if err:
            note = err
        elif not items:
            note = f"工单 {args.workorder} 中未解析到任何意见条目"
    elif args.workorder:
        note = f"工单文件不存在: {args.workorder}"
    if not items and args.task and os.path.exists(args.task):
        items = parse_from_task(args.task)
        if items:
            note = (note or "无可用工单") + "；已从 task.md 规则抽取意见行"
    items = items or []
    out = {"source": args.workorder if (items and not any("source" in it for it in items))
           else (args.task if items else None),
           "note": note, "n_items": len(items), "items": items}
    path = os.path.join(args.work, "workorder_items.json")
    save_json(path, out)
    print(f"[parse] {len(items)} 条修改意见 -> {path}" + (f"（{note}）" if note else ""))
    for it in items:
        print(f"  {it['rid']} [轮{it['round']}] [{it['type']}] "
              f"target={it['target_file'] or '-'} :: {excerpt(it['content'], 60)}")
    return 0

# ---------------------------------------------------------------- locate

def match_file_key(target, files):
    """按 basename / rel 路径 / key 匹配 chapters.json 的 files 条目。"""
    if not target:
        return None
    base = os.path.basename(str(target))
    for f in files:
        if os.path.basename(f.get("path", "")) == base:
            return f["key"]
    for f in files:
        if f.get("key") == target or str(target) in f.get("path", ""):
            return f["key"]
    return None

def locate_item(item, sections, files):
    grams = char_ngrams(item.get("content", ""))
    restrict = match_file_key(item.get("target_file"), files)
    if item.get("target_file") and restrict is None:
        item["locate_error"] = f"目标文件缺失: {item['target_file']}"
        item["target_pids"] = []
        return
    scored = []
    for s in sections:
        if restrict and s["file_key"] != restrict:
            continue
        for p in s["paragraphs"]:
            if p["kind"] in ("heading", "reference_list"):
                continue
            ov = len(grams & char_ngrams(p["text"]))
            if ov:
                scored.append((ov, p["pid"], excerpt(p["text"], 80)))
    scored.sort(key=lambda x: -x[0])
    item["target_pids"] = [pid for _sc, pid, _ex in scored[:3]]
    item["locate_top"] = [{"pid": pid, "overlap": sc, "excerpt": ex}
                          for sc, pid, ex in scored[:3]]
    if not scored:
        item["locate_error"] = "未定位到内容相关段落（关键词无重叠）"

def detect_conflicts(items):
    by_pid = {}
    for it in items:
        pids = it.get("target_pids") or []
        if pids:
            by_pid.setdefault(pids[0], []).append(it)
    conflicts = []
    for pid, group in by_pid.items():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if (a["type"], b["type"]) in OPPOSITE:
                    c = {"pid": pid, "rids": [a["rid"], b["rid"]],
                         "types": [a["type"], b["type"]],
                         "reason": f"两条意见定位同一段落 {pid} 且类型相反（{a['type']} vs {b['type']}），需 Agent 裁决"}
                    conflicts.append(c)
                    for it in (a, b):
                        it.setdefault("conflict", []).append(
                            {"with": b["rid"] if it is a else a["rid"], "pid": pid})
    return conflicts

def cmd_locate(args):
    chapters = load_json(args.chapters)
    if not chapters:
        print(f"[locate][FAIL] chapters.json 不存在或不可解析: {args.chapters}", file=sys.stderr)
        return 1
    data = load_json(args.items)
    if not data:
        print(f"[locate][FAIL] workorder_items.json 不存在: {args.items}", file=sys.stderr)
        return 1
    items = data["items"]
    sections, files = chapters.get("sections", []), chapters.get("files", [])
    for it in items:
        it.pop("locate_error", None)
        locate_item(it, sections, files)
    conflicts = detect_conflicts(items)
    data["conflicts"] = conflicts
    save_json(args.items, data)
    n_loc = sum(1 for it in items if it.get("target_pids"))
    print(f"[locate] {n_loc}/{len(items)} 条意见已定位；冲突 {len(conflicts)} 组")
    for it in items:
        flag = " ⚠冲突" if it.get("conflict") else ""
        err = f" ✗{it['locate_error']}" if it.get("locate_error") else ""
        print(f"  {it['rid']}: pids={it.get('target_pids') or []}{flag}{err}")
    for c in conflicts:
        print(f"  [conflict] {c['reason']}")
    return 0

# ---------------------------------------------------------------- apply

def split_blocks(text):
    """与 parse_chapters 一致的分段（空行分段），保留原始块文本。"""
    return [b for b in re.split(r"\n\s*\n", text) if b.strip()]

def find_pid_text(chapters, pid):
    for p in chapters.get("paragraphs", []):
        if p["pid"] == pid:
            return p["text"]
    return None

def replace_block(file_text, old_norm, new_text, mode):
    """在文件文本中替换/插入。返回 (新文本, ok)。"""
    blocks = split_blocks(file_text)
    for idx, b in enumerate(blocks):
        if norm_text(b) == old_norm:
            if mode == "append_after":
                blocks[idx] = b.rstrip() + "\n\n" + new_text.strip()
            else:
                blocks[idx] = new_text.strip()
            return "\n\n".join(blocks) + "\n", True
    return file_text, False

def cmd_apply(args):
    data = load_json(args.items)
    edits = load_json(args.edits, [])
    chapters = load_json(args.chapters)
    if data is None or edits is None:
        print("[apply][FAIL] 缺少 workorder_items.json 或 agent_edits.json", file=sys.stderr)
        return 1
    items = {it["rid"]: it for it in data["items"]}
    edits = {e["rid"]: e for e in edits if isinstance(e, dict) and e.get("rid")}
    orig_dir = os.path.join(args.work, "original")
    rev_dir = os.path.join(args.work, "revised")
    os.makedirs(orig_dir, exist_ok=True)
    os.makedirs(rev_dir, exist_ok=True)

    # 源文件路径映射：basename -> path（优先 chapters.json）
    path_by_base = {}
    if chapters:
        for f in chapters.get("files", []):
            path_by_base[os.path.basename(f["path"])] = f["path"]
    for it in data["items"]:
        tf = it.get("target_file")
        if tf and os.path.exists(str(tf)):
            path_by_base.setdefault(os.path.basename(str(tf)), str(tf))

    def working_copy(base):
        """确保原件已备份、修订副本已建立；返回 (rev_path, ok)。"""
        src = path_by_base.get(base)
        if not src or not os.path.exists(src):
            return None, False
        bak = os.path.join(orig_dir, base)
        if not os.path.exists(bak):
            shutil.copy2(src, bak)
        rev = os.path.join(rev_dir, base)
        if not os.path.exists(rev):
            shutil.copy2(src, rev)
        return rev, True

    ledger = []
    for rid, it in items.items():
        e = edits.get(rid)
        entry = {"rid": rid, "round": it.get("round"), "target_file": it.get("target_file"),
                 "type": it.get("type"), "content": it.get("content"),
                 "target_pids": it.get("target_pids") or []}
        if not e:
            entry.update(status="待人工确认", action=None,
                         reason="Agent 未给出修改决策（agent_edits.json 无此 rid）",
                         before=None, after=None, evidence_pid=None)
            it["status"] = "待人工确认"
            ledger.append(entry)
            continue
        action = e.get("action", "")
        reason = e.get("reason", "")
        entry["action"] = action
        entry["reason"] = reason
        if action == "skip":
            entry.update(status="无法落实", before=None, after=None, evidence_pid=None)
            it["status"] = "无法落实"
            it["status_reason"] = reason
            ledger.append(entry)
            continue
        if action == "defer":
            entry.update(status="待人工确认", before=None, after=None, evidence_pid=None)
            it["status"] = "待人工确认"
            it["status_reason"] = reason
            ledger.append(entry)
            continue
        if action != "edit":
            entry.update(status="待人工确认",
                         reason=f"未知 action={action!r}；" + reason,
                         before=None, after=None, evidence_pid=None)
            it["status"] = "待人工确认"
            ledger.append(entry)
            continue
        # action == edit
        base = os.path.basename(str(it.get("target_file") or ""))
        rev, ok = working_copy(base)
        if not ok:
            entry.update(status="无法落实",
                         reason=f"目标文件缺失，无法执行修改: {it.get('target_file')}；" + reason,
                         before=None, after=None, evidence_pid=None)
            it["status"] = "无法落实"
            it["status_reason"] = entry["reason"]
            ledger.append(entry)
            continue
        pid = e.get("target_pid") or (it.get("target_pids") or [None])[0]
        new_text = (e.get("new_text") or "").strip()
        mode = e.get("mode", "replace")
        if not new_text:
            entry.update(status="无法落实", reason="edit 决策缺少 new_text；" + reason,
                         before=None, after=None, evidence_pid=pid)
            it["status"] = "无法落实"
            it["status_reason"] = entry["reason"]
            ledger.append(entry)
            continue
        with open(rev, encoding="utf-8") as f:
            cur = f.read()
        before = None
        if pid and chapters:
            before = find_pid_text(chapters, pid)
        if before is None and mode != "append_end":
            # pid 未给或找不到原文：尝试在文件中模糊定位 content 关键词最高重叠段
            grams = char_ngrams(it.get("content", ""))
            best, best_b = 0, None
            for b in split_blocks(cur):
                ov = len(grams & char_ngrams(b))
                if ov > best:
                    best, best_b = ov, b
            before = best_b
        if before is None and mode != "append_end":
            entry.update(status="无法落实",
                         reason="无法在目标文件中找到与意见对应的原文段落（before 为空，拒绝臆改）；" + reason,
                         before=None, after=None, evidence_pid=pid)
            it["status"] = "无法落实"
            it["status_reason"] = entry["reason"]
            ledger.append(entry)
            continue
        if mode == "append_end":
            new_cur = cur.rstrip() + "\n\n" + new_text + "\n"
            replaced = True
            before_show = before or "(文末追加，无直接原文段)"
        else:
            new_cur, replaced = replace_block(cur, norm_text(before), new_text, mode)
            before_show = before
        if not replaced:
            entry.update(status="部分落实",
                         reason="原文段落已解析但文本匹配失败（文件可能被并发修改），未改动；" + reason,
                         before=excerpt(before), after=None, evidence_pid=pid)
            it["status"] = "部分落实"
            it["status_reason"] = entry["reason"]
            ledger.append(entry)
            continue
        with open(rev, "w", encoding="utf-8") as f:
            f.write(new_cur)
        entry.update(status="已落实", before=excerpt(before_show),
                     after=excerpt(new_text), evidence_pid=pid, mode=mode)
        it["status"] = "已落实"
        it["applied_pid"] = pid
        ledger.append(entry)

    # 台账 JSON + MD
    n_done = sum(1 for l in ledger if l["status"] == "已落实")
    ledger_obj = {"generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "n_items": len(ledger), "n_done": n_done,
                  "n_partial": sum(1 for l in ledger if l["status"] == "部分落实"),
                  "n_unable": sum(1 for l in ledger if l["status"] == "无法落实"),
                  "n_manual": sum(1 for l in ledger if l["status"] == "待人工确认"),
                  "entries": ledger}
    save_json(os.path.join(args.work, "revision_ledger.json"), ledger_obj)
    lines = ["# 改稿落实台账", "",
             f"共 {len(ledger)} 条意见：已落实 {n_done} / 部分落实 {ledger_obj['n_partial']} / "
             f"无法落实 {ledger_obj['n_unable']} / 待人工确认 {ledger_obj['n_manual']}", ""]
    for l in ledger:
        lines += [f"## {l['rid']}（第 {l.get('round')} 轮 · {l.get('type')} · {l['status']}）",
                  f"- 意见：{l.get('content')}",
                  f"- 目标文件：{l.get('target_file') or '-'}；证据段落：{l.get('evidence_pid') or '-'}",
                  f"- 决策：{l.get('action') or '-'}（{l.get('mode') or '-'}）；理由：{l.get('reason') or '-'}",
                  f"- before：{l.get('before') or '（无）'}",
                  f"- after：{l.get('after') or '（无）'}", ""]
    with open(os.path.join(args.work, "revision_ledger.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # diff 报告（原件备份 vs 修订稿）
    diff_lines = ["# 改稿差异报告（diff）", "",
                  "对照：work/original/（修改前备份）→ work/revised/（修改后）。", ""]
    for base in sorted(os.listdir(rev_dir)):
        bak = os.path.join(orig_dir, base)
        rev = os.path.join(rev_dir, base)
        if not os.path.exists(bak):
            continue
        with open(bak, encoding="utf-8") as f:
            old = f.read().splitlines()
        with open(rev, encoding="utf-8") as f:
            new = f.read().splitlines()
        if old == new:
            diff_lines.append(f"## {base}：无变化\n")
            continue
        diff_lines.append(f"## {base}\n\n```diff")
        diff_lines.extend(difflib.unified_diff(
            old, new, fromfile=f"original/{base}", tofile=f"revised/{base}", lineterm=""))
        diff_lines.append("```\n")
    with open(os.path.join(args.work, "diff_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(diff_lines))

    save_json(args.items, data)
    print(f"[apply] 已落实 {n_done}/{len(ledger)}；修订稿 -> {rev_dir}；"
          f"原件备份 -> {orig_dir}；台账 revision_ledger.json/.md；差异 diff_report.md")
    return 0

# ---------------------------------------------------------------- version

def cmd_version(args):
    data = load_json(args.items)
    if not data:
        print(f"[version][FAIL] 缺少 {args.items}", file=sys.stderr)
        return 1
    items = data["items"]
    rounds = {}
    for it in items:
        r = str(it.get("round", "?"))
        rd = rounds.setdefault(r, {"round": it.get("round"), "n_opinions": 0,
                                   "n_done": 0, "n_partial": 0, "n_unable": 0,
                                   "n_manual": 0, "n_pending": 0,
                                   "unresolved": []})
        rd["n_opinions"] += 1
        st = it.get("status", "pending")
        key = {"已落实": "n_done", "部分落实": "n_partial", "无法落实": "n_unable",
               "待人工确认": "n_manual"}.get(st, "n_pending")
        rd[key] += 1
        if st != "已落实":
            rd["unresolved"].append({"rid": it["rid"], "status": st,
                                     "reason": it.get("status_reason") or it.get("locate_error") or "",
                                     "content": excerpt(it.get("content", ""), 80)})
    orig_dir = os.path.join(args.work, "original")
    backups = sorted(os.listdir(orig_dir)) if os.path.isdir(orig_dir) else []
    report = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "n_opinions": len(items),
        "rounds": [rounds[k] for k in sorted(rounds, key=lambda x: (len(x), x))],
        "conflicts": data.get("conflicts") or [],
        "rollback": {
            "backup_dir": "work/original/",
            "backed_up_files": backups,
            "how_to": "回退：用 work/original/<文件> 覆盖 work/revised/ 同名文件或原始章节文件；"
                      "diff_report.md 可逐行核对改动后再决定。",
        },
        "ledger": "work/revision_ledger.json",
        "diff_report": "work/diff_report.md",
    }
    save_json(os.path.join(args.work, "version_report.json"), report)

    # change_log 追加
    clog_path = os.path.join(args.work, "change_log.json")
    clog = load_json(clog_path, []) or []
    for it in items:
        if it.get("status") in ("已落实", "部分落实"):
            clog.append({"rid": it["rid"], "kind": "revision",
                         "target_file": it.get("target_file"),
                         "pid": it.get("applied_pid"),
                         "status": it["status"],
                         "summary": excerpt(it.get("content", ""), 80)})
    save_json(clog_path, clog)
    print(f"[version] 轮次汇总 {len(report['rounds'])} 轮 / 意见 {len(items)} 条；"
          f"备份 {len(backups)} 个文件 -> work/version_report.json")
    return 0

# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse", help="拆解工单/task.md → workorder_items.json")
    p.add_argument("--workorder", default="/input/organizer-edit-workorder.json")
    p.add_argument("--task", default="/input/task.md")
    p.add_argument("--work", default="/app/work")
    p.set_defaults(func=cmd_parse)

    p = sub.add_parser("locate", help="定位目标段落候选 pid + 冲突检测")
    p.add_argument("--chapters", default=None)
    p.add_argument("--items", default=None)
    p.add_argument("--work", default="/app/work")
    p.set_defaults(func=cmd_locate)

    p = sub.add_parser("apply", help="执行 agent_edits.json 修改决策")
    p.add_argument("--items", default=None)
    p.add_argument("--edits", default=None)
    p.add_argument("--chapters", default=None)
    p.add_argument("--work", default="/app/work")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("version", help="按轮次汇总 → version_report.json")
    p.add_argument("--items", default=None)
    p.add_argument("--work", default="/app/work")
    p.set_defaults(func=cmd_version)

    args = ap.parse_args()
    w = args.work
    if getattr(args, "chapters", None) is None and hasattr(args, "chapters"):
        args.chapters = os.path.join(w, "chapters.json")
    if getattr(args, "items", None) is None:
        args.items = os.path.join(w, "workorder_items.json")
    if getattr(args, "edits", None) is None and args.cmd == "apply":
        args.edits = os.path.join(w, "agent_edits.json")
    os.makedirs(w, exist_ok=True)
    return args.func(args)

if __name__ == "__main__":
    sys.exit(main())
