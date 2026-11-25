#!/usr/bin/env python3
"""renumber_plan.py — 「编号连锁更新」引擎（版本2 专属，纯确定性）。

把 Agent 写在 work/edit_ops.json 里的语义化编辑操作编译为 旧号→新号 mapping，
驱动共享 cite_engine 完成正文/图注/表注/附录/脚注的全文编号连锁重排，
重建文末参考文献列表，并做不变量终检（连续、无悬空、无缺口、样式统一）。

用法:
  python3 renumber_plan.py --work /app/work --out /app/output [--style auto]
  [--edit-ops /app/work/edit_ops.json] [--engine scripts/cite_engine.py]

输入:
  work/edit_ops.json       Agent 写的编辑操作列表（见 references/edit_ops_schema.md）
  work/manuscript.json     parse_manuscript.py 产物（必须存在）
  work/library.json        parse_library.py 产物（文献库记录 R001...，顺序=当前列表序）
  work/reference_list.json 可选；稿件自带文末列表 parse 未覆盖时 Agent 手工补写
                           [{num, text}]，优先于 library.json 作为列表文本来源

输出:
  work/mapping.json         旧号→新号（null=删除），喂给 cite_engine renumber
  work/manuscript.renumbered.json  重排后稿件（cite_engine 产出）
  work/library_reordered.json 按新序排列的存活记录（含 source_file/source_index）
  /app/output/references.md + references.json  重建后的文末列表
  /app/output/edited_manuscript.md             重排后的可编辑稿件
  /app/output/renumber_report.md  人读报告（操作清单→映射表→悬空清单→终检结论）
  work/renumber_report.json        机读报告（同内容 + 终检 PASS/FAIL）
stdout 最后一行: INVARIANTS: PASS 或 INVARIANTS: FAIL（exit 0/1）

著者-出版年稿件: 不做数字重排，仅检查列表排序并标注 stale 条目，报告中说明。
"""
import argparse, json, os, re, subprocess, sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ENGINE = os.path.join(SCRIPT_DIR, "cite_engine.py")

VALID_OPS = {"delete", "reorder", "insert_existing", "merge"}


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def ref_to_pos(ref_id, id_to_pos, order_len):
    """ref_id 两种形式:
    - 'R007'（library.json 记录号）→ 按【条目身份】在当前列表中定位（删改后位置可能变动）;
    - 纯数字 '3' → 视为【当前列表序号】（第 3 位）。
    返回 1..order_len 的位置；无法定位返回 None。"""
    if ref_id is None:
        return None
    s = str(ref_id).strip()
    m = re.fullmatch(r"[Rr]0*(\d+)", s)
    if m:
        return id_to_pos.get(f"R{int(m.group(1)):03d}")  # 身份查找，找不到=None
    if s.isdigit():
        pos = int(s)
        return pos if 1 <= pos <= order_len else None
    return id_to_pos.get(s)  # 其他 key（如 bibtex key）在列表中查找


def parse_ref_list_entries(path):
    """work/reference_list.json: [{num, text}, ...] → {pos: text}"""
    data = load_json(path)
    if not isinstance(data, list):
        return {}
    out = {}
    for it in data:
        if isinstance(it, dict) and isinstance(it.get("num"), int) and it.get("text"):
            out[int(it["num"])] = str(it["text"])
    return out


def apply_ops(order, n_list, n_lib, ops):
    """order: 当前列表序（元素为旧编号）。返回 (新 order, 操作日志, 错误)。
    每个元素 = 旧编号；被删除的不再出现。insert_existing 从文献库拉入新编号。
    n_list=旧列表大小（mapping 覆盖 1..n_list）；n_lib=文献库记录数（insert 上限）。"""
    log, errors = [], []
    order = list(order)
    for i, op in enumerate(ops):
        if not isinstance(op, dict) or op.get("op") not in VALID_OPS:
            errors.append(f"op#{i}: 未知或非法操作 {op!r}，已跳过")
            continue
        kind = op["op"]
        note = op.get("note", "")
        id_to_pos = {f"R{old:03d}": idx + 1 for idx, old in enumerate(order)}

        if kind == "delete":
            pos = ref_to_pos(op.get("ref_id"), id_to_pos, len(order))
            if pos is None:
                errors.append(f"op#{i} delete: ref_id={op.get('ref_id')} 无法定位（可能已被删），已跳过")
                continue
            old = order.pop(pos - 1)
            log.append({"op": "delete", "old": old, "note": note})

        elif kind == "insert_existing":
            rid = str(op.get("ref_id", "")).strip()
            m = re.fullmatch(r"[Rr]0*(\d+)", rid)
            if not m:
                errors.append(f"op#{i} insert_existing: ref_id={rid} 不是 R00X 形式，已跳过")
                continue
            old = int(m.group(1))
            if old in order:
                errors.append(f"op#{i} insert_existing: {rid} 已在列表中，已跳过（如需调序用 reorder）")
                continue
            if not (1 <= old <= n_lib):
                errors.append(f"op#{i} insert_existing: {rid} 超出文献库范围 1..{n_lib}，已跳过")
                continue
            to = op.get("to")
            if to is None:
                order.append(old)
            else:
                try:
                    to = max(0, min(int(to) - 1, len(order)))
                except (TypeError, ValueError):
                    to = len(order)
                order.insert(to, old)
            log.append({"op": "insert_existing", "old": old, "to": op.get("to"), "note": note})

        elif kind == "reorder":
            if op.get("ref_ids"):  # 子集全序：给出的条目按此相对顺序排列，其余保持相对序
                wanted, new_order, used = [], [], set()
                for rid in op["ref_ids"]:
                    p = ref_to_pos(rid, id_to_pos, len(order))
                    if p is None:
                        errors.append(f"op#{i} reorder: ref_id={rid} 无法定位，已忽略该项")
                        continue
                    wanted.append(order[p - 1])
                ws = set(wanted)
                wit = iter(wanted)
                for old in order:
                    if old in ws:
                        new_order.append(next(wit))
                        used.add(old)
                    else:
                        new_order.append(old)
                order = new_order
                log.append({"op": "reorder", "ref_ids": [f"R{x:03d}" for x in wanted],
                            "note": note})
            else:  # 单条移动: ref_id -> to（1..len，语义=插入到第 to 位）
                pos = ref_to_pos(op.get("ref_id"), id_to_pos, len(order))
                if pos is None:
                    errors.append(f"op#{i} reorder: ref_id={op.get('ref_id')} 无法定位，已跳过")
                    continue
                old = order.pop(pos - 1)
                to = op.get("to")
                try:
                    to = max(0, min(int(to) - 1, len(order))) if to is not None else len(order)
                except (TypeError, ValueError):
                    to = len(order)
                order.insert(to, old)
                log.append({"op": "reorder", "old": old, "to": op.get("to"), "note": note})

        elif kind == "merge":
            keep = ref_to_pos(op.get("keep") or op.get("ref_id"), id_to_pos, len(order))
            merged = [ref_to_pos(r, id_to_pos, len(order)) for r in (op.get("ref_ids") or [])]
            merged = [order[p - 1] for p in merged if p]
            if keep is None:
                errors.append(f"op#{i} merge: keep={op.get('keep') or op.get('ref_id')} 无法定位，已跳过")
                continue
            keep_old = order[keep - 1]
            dropped = [x for x in merged if x != keep_old and x in order]
            for x in dropped:
                order.remove(x)
            log.append({"op": "merge", "keep": keep_old, "dropped": dropped, "note": note})
    return order, log, errors


def build_mapping(order, n):
    """order 元素为旧编号（insert_existing 拉入的库编号可能 > n）。
    每个存活条目（含新插入）获得新号；1..n 中未存活者 = null（删除）。
    新插入条目保留 旧库号->新号 的恒等映射，使 Agent 可在正文直接引用其库编号 [k]。"""
    mapping = {}
    for newpos, old in enumerate(order, 1):
        mapping[str(old)] = newpos
    for old in range(1, n + 1):
        mapping.setdefault(str(old), None)
    return mapping


def run_engine(engine, work, mapping_path):
    """调共享 cite_engine renumber（子进程，接口不改）。返回 (report, err)。"""
    ms = os.path.join(work, "manuscript.json")
    cmd = [sys.executable, engine, "renumber", "--manuscript", ms,
           "--mapping", mapping_path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            return None, f"cite_engine renumber 失败: {r.stderr.strip()[:300]}"
        return load_json(os.path.join(work, "renumber_report.json"), {}), None
    except Exception as e:
        return None, f"cite_engine renumber 异常: {e}"


def run_render(engine, lib_path, order_ids, style, out_md):
    """调共享 cite_engine render 生成列表，再回填 source_file/source_index。"""
    cmd = [sys.executable, engine, "render", "--records", lib_path,
           "--style", style]
    if order_ids:
        cmd += ["--order", order_ids]
    cmd += ["--out", out_md]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        return f"cite_engine render 失败: {r.stderr.strip()[:300]}"


def write_outputs(work, out, mapping, order, lib, ref_list_text, style, report,
                  engine=None):
    """重建文末列表（references.md/json）与 edited_manuscript.md。
    列表文本优先取 Agent 手工提供的 work/reference_list.json（保留原措辞），
    否则调共享 cite_engine render 按目标样式格式化（完整字段）。
    每条保留原始出处 source_file + source_index。"""
    os.makedirs(out, exist_ok=True)
    records_by_id = {r["id"]: r for r in lib.get("records", [])}
    # 按新序的存活记录（含出处），供追溯与渲染
    reordered = [records_by_id[f"R{old:03d}"] for old in order
                 if f"R{old:03d}" in records_by_id]
    with open(os.path.join(work, "library_reordered.json"), "w", encoding="utf-8") as f:
        json.dump({"records": reordered, "count": len(reordered)}, f, ensure_ascii=False, indent=2)

    # 引擎渲染完整格式化文本（若可用）；手工 reference_list.json 的原文优先于渲染结果
    rendered = {}
    if engine and reordered:
        lib_sub = os.path.join(work, "library_reordered.json")
        out_md = os.path.join(out, "references.md")
        err = run_render(engine, lib_sub, None, style, out_md)
        if not err:
            rj = load_json(out_md.replace(".md", ".json"), {}) or {}
            for e in rj.get("entries", []):
                rendered[e["number"]] = e["text"]

    entries, lines = [], []
    numeric = ("numeric" in style) or style == "vancouver"
    for newpos, old in enumerate(order, 1):
        rid = f"R{old:03d}"
        rec = records_by_id.get(rid, {})
        text = ref_list_text.get(old) or rendered.get(newpos)
        if text is None:
            auth = ", ".join((rec.get("authors") or [])[:3])
            text = f"{auth}. {rec.get('title') or '(无题名记录)'}" if auth else (rec.get("title") or "(无题名记录)")
        entries.append({"number": newpos, "id": rid, "text": text,
                        "source_file": rec.get("source_file"),
                        "source_index": rec.get("source_index")})
        lines.append(f"[{newpos}] {text}" if numeric else text)
    with open(os.path.join(out, "references.md"), "w", encoding="utf-8") as f:
        f.write("## 参考文献\n\n" + "\n\n".join(lines) + "\n")
    with open(os.path.join(out, "references.json"), "w", encoding="utf-8") as f:
        json.dump({"style": style, "entries": entries}, f, ensure_ascii=False, indent=2)

    # edited_manuscript.md：重排后全文（跳过旧 reference_list 段，避免残留旧编号；
    # 文末统一换成重建后的 references.md 内容）
    ms = load_json(os.path.join(work, "manuscript.renumbered.json"), {}) or {}
    parts = []
    for p in ms.get("paragraphs", []):
        t = p.get("text", "").strip()
        if not t or p.get("kind") == "reference_list":
            continue
        if p.get("kind") == "heading":
            # 跳过原"参考文献"节标题（文末统一换成重建列表）；其余标题保留并防重复 '#'
            if re.match(r"^#{1,6}\s*(参考文献|References|Bibliography|Works Cited)", t, re.I):
                continue
            parts.append(t if t.startswith("#") else f"## {t}")
        else:
            parts.append(t)
    parts.append("## 参考文献\n\n" + "\n\n".join(lines))
    with open(os.path.join(out, "edited_manuscript.md"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(parts) + "\n")
    return entries


def invariants_check(ms_path, list_count):
    """不变量终检：正文最大编号==列表条数；1..N 无缺口；样式不混杂。返回 (ok, detail)。"""
    ms = load_json(ms_path, {}) or {}
    all_nums, styles = [], set()
    for p in ms.get("paragraphs", []):
        if p.get("kind") == "reference_list":
            continue  # 文末列表段落不参与正文不变量
        for m in p.get("cite_marks", []):
            styles.add(m.get("style"))
            if m.get("style") == "numeric":
                all_nums.extend(m.get("nums", []))
    maxn = max(all_nums) if all_nums else 0
    missing = [x for x in range(1, maxn + 1) if x not in set(all_nums)]
    ok = (maxn == list_count) and not missing and len(styles) <= 1
    detail = {"max_inline_number": maxn, "list_entries": list_count,
              "max_equals_list": maxn == list_count,
              "gaps": missing, "no_gaps": not missing,
              "styles_in_text": sorted(styles), "style_consistent": len(styles) <= 1}
    return ok, detail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--edit-ops", default=None)
    ap.add_argument("--style", default="auto",
                    help="auto|numeric|gbt2015_numeric|gbt2015_author|apa7|vancouver")
    ap.add_argument("--engine", default=DEFAULT_ENGINE)
    args = ap.parse_args()

    edit_ops_path = args.edit_ops or os.path.join(args.work, "edit_ops.json")
    ops = load_json(edit_ops_path, []) or []
    ms = load_json(os.path.join(args.work, "manuscript.json"))
    lib = load_json(os.path.join(args.work, "library.json"), {"records": []}) or {"records": []}
    ref_list_text = parse_ref_list_entries(os.path.join(args.work, "reference_list.json"))
    if ms is None or not ms.get("paragraphs"):
        print("INVARIANTS: FAIL (manuscript.json 缺失或无段落，先运行 parse_manuscript.py)",
              file=sys.stderr)
        return 1

    # 样式判定
    style = args.style
    if style == "auto":
        styles = set(ms.get("styles_detected") or [])
        hint = "numeric" if any(p.get("kind") != "reference_list" and
                                any(m["style"] == "numeric" for m in p.get("cite_marks", []))
                                for p in ms["paragraphs"]) else "author_year"
        style = "gbt2015_numeric" if "numeric" in styles or hint == "numeric" else "gbt2015_author"
    author_year = style in ("gbt2015_author", "apa7") and "numeric" not in style

    records = lib.get("records", [])
    n_lib = len(records)
    # 当前列表基准序：Agent 提供 work/reference_list.json 时以其中条目为准
    # （稿件自带列表可能少于文献库记录，insert_existing 从库中拉入）；
    # 否则默认列表 = 文献库全部记录，序为 1..n_lib。
    if ref_list_text:
        base_order = sorted(ref_list_text)
        n = max(ref_list_text)
    else:
        base_order = list(range(1, n_lib + 1))
        n = n_lib

    report = {"style": style, "n_library_records": len(records),
              "n_ops": len(ops), "ops_applied": [], "ops_errors": [],
              "author_year_mode": author_year, "mapping": {}, "deleted": [],
              "dangling_refs": [], "invariants": {}, "PASS": False}

    # ---------- 著者-出版年：不做数字重排 ----------
    if author_year:
        stale = []
        for r in records:
            fp = r.get("field_presence", {})
            if not r.get("year") or not r.get("authors"):
                stale.append({"id": r["id"], "reason": "缺 year 或 authors，排序键不可靠",
                              "source_file": r.get("source_file"),
                              "source_index": r.get("source_index")})
        first_authors = [(r.get("authors") or [""])[0].lower() for r in records]
        sorted_ok = first_authors == sorted(first_authors) if first_authors else True
        report["author_year_check"] = {
            "note": "著者-出版年稿件不做数字重排；仅检查列表排序并标注 stale 条目",
            "list_sorted_by_first_author": sorted_ok, "stale_entries": stale}
        entries = write_outputs(args.work, args.out, {}, list(base_order), lib,
                                ref_list_text, style, report, engine=args.engine)
        ok, detail = True, {"author_year": True, "list_sorted_by_first_author": sorted_ok,
                            "stale_count": len(stale)}
        report["invariants"] = detail
        report["PASS"] = ok and not report["ops_errors"]
        write_reports(report, args.work, args.out, None, entries)
        print("INVARIANTS: PASS (author-year 模式: 未重排, 仅排序检查)" if report["PASS"]
              else "INVARIANTS: FAIL (author-year 模式)")
        return 0 if report["PASS"] else 1

    # ---------- 数字编号：编译 mapping → 引擎连锁更新 ----------
    base_order = list(range(1, n + 1))
    new_order, op_log, op_errors = apply_ops(base_order, n, n_lib, ops)
    mapping = build_mapping(new_order, n)
    report["ops_applied"] = op_log
    report["ops_errors"] = op_errors
    report["mapping"] = {k: v for k, v in sorted(mapping.items(), key=lambda kv: int(kv[0]))}
    report["deleted"] = [x for x in base_order if mapping.get(str(x)) is None]

    mapping_path = os.path.join(args.work, "mapping.json")
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    eng, eng_err = run_engine(args.engine, args.work, mapping_path)
    if eng_err:
        report["ops_errors"].append(eng_err)
        write_reports(report, args.work, args.out, None, [])
        print("INVARIANTS: FAIL (引擎执行失败，见 renumber_report)", file=sys.stderr)
        return 1
    report["engine"] = eng

    # 悬空引用：在【原始】稿件上按旧编号检测——删除号仍被正文/图注/表注/附录/脚注引用处。
    # （必须在重排前检测：重排后新编号可能与旧删除号数值相同，无法直接比对。）
    ms_re = os.path.join(args.work, "manuscript.renumbered.json")
    deleted = set(report["deleted"])
    dangling = []
    for p in ms.get("paragraphs", []):
        if p.get("kind") == "reference_list":
            continue  # 文末列表段落的 [n] 是条目标签，不是正文引用
        for m in p.get("cite_marks", []):
            if m.get("style") == "numeric":
                hit = sorted(set(m.get("nums", [])) & deleted)
                if hit:
                    dangling.append({"pid": p["pid"], "kind": p.get("kind"),
                                     "raw": m["raw"], "dangling_old_nums": hit,
                                     "text_head": p["text"][:80],
                                     "action": "Agent 必须改写该句（删该引或改引存活条目）后重跑引擎"})
    report["dangling_refs"] = dangling

    # 重建列表与稿件
    entries = write_outputs(args.work, args.out, mapping, new_order, lib,
                            ref_list_text, style, report, engine=args.engine)

    ok, detail = invariants_check(ms_re, len(entries))
    report["invariants"] = detail
    report["PASS"] = ok and not dangling and not op_errors
    write_reports(report, args.work, args.out, mapping, entries)
    print(f"[renumber_plan] 映射 {sum(1 for v in mapping.values() if v)} 条, "
          f"删除 {len(report['deleted'])} 条, 悬空段落 {len(dangling)} 处")
    print("INVARIANTS: PASS" if report["PASS"] else "INVARIANTS: FAIL")
    return 0 if report["PASS"] else 1


def write_reports(report, work, out, mapping, entries):
    """写人读 renumber_report.md 与机读 work/renumber_report.json。"""
    os.makedirs(out, exist_ok=True)
    lines = ["# 编号连锁更新报告（renumber_report）", "",
             f"- 引用样式: {report['style']}" +
             ("（著者-出版年模式，未做数字重排）" if report.get("author_year_mode") else ""),
             f"- 文献库记录: {report['n_library_records']} 条; 编辑操作: {report['n_ops']} 个", ""]
    if report.get("author_year_mode"):
        c = report.get("author_year_check", {})
        lines += ["## 著者-出版年检查", "",
                  f"- 列表按第一作者排序: {'是' if c.get('list_sorted_by_first_author') else '否（建议人工确认排序）'}",
                  f"- stale 条目: {len(c.get('stale_entries', []))} 条"]
        for s in c.get("stale_entries", []):
            lines.append(f"  - {s['id']} ({s.get('source_file')}#{s.get('source_index')}): {s['reason']}")
        lines += ["", "> 说明: 著者-出版年稿件的引用不携带编号，删除/调序只需维护文末列表；", ""]
    else:
        lines += ["## 1. 操作清单（edit_ops → 执行结果）", ""]
        if report["ops_applied"]:
            for l in report["ops_applied"]:
                if l["op"] == "delete":
                    lines.append(f"- delete R{l['old']:03d}（新列表中移除）{('— ' + l['note']) if l.get('note') else ''}")
                elif l["op"] == "reorder":
                    lines.append(f"- reorder {l.get('ref_ids') or ('R%03d' % l['old'])} -> to={l.get('to')}")
                elif l["op"] == "insert_existing":
                    lines.append(f"- insert_existing R{l['old']:03d} -> 位置 {l.get('to')}")
                elif l["op"] == "merge":
                    lines.append(f"- merge 保留 R{l['keep']:03d}, 合并掉 " +
                                 ", ".join(f"R{x:03d}" for x in l["dropped"]))
        else:
            lines.append("- （无操作 / edit_ops.json 为空：保持恒等映射）")
        if report["ops_errors"]:
            lines += ["", "### 操作异常", ""] + [f"- {e}" for e in report["ops_errors"]]
        lines += ["", "## 2. 旧号 → 新号映射表", "", "| 旧号 | 新号 |", "|---|---|"]
        for old, new in (mapping or {}).items():
            lines.append(f"| {old} | {'删除' if new is None else new} |")
        lines += ["", f"删除条目: {report['deleted'] or '无'}", ""]
        lines += ["## 3. 悬空引用清单（删除后仍被引用，须 Agent 处置）", ""]
        if report["dangling_refs"]:
            for d in report["dangling_refs"]:
                lines.append(f"- 段落 {d['pid']}（{d.get('kind')}）标记 {d.get('raw')} "
                             f"涉及已删除旧号 {d.get('dangling_old_nums') or '（整段标记被移除）'}")
                lines.append(f"  - 处置: {d['action']}")
        else:
            lines.append("- 无。所有正文引用均落在存活条目上。")
        lines += ["", "## 4. 不变量终检", ""]
        iv = report["invariants"]
        lines += [f"- 正文最大编号 == 列表条数: {iv.get('max_inline_number')} == {iv.get('list_entries')} → "
                  f"{'✓' if iv.get('max_equals_list') else '✗'}",
                  f"- 1..N 无缺口: {'✓' if iv.get('no_gaps') else '✗ 缺 ' + str(iv.get('gaps'))}",
                  f"- 样式统一: {'✓ ' + str(iv.get('styles_in_text')) if iv.get('style_consistent') else '✗ ' + str(iv.get('styles_in_text'))}",
                  "", f"## 结论: **{'PASS' if report['PASS'] else 'FAIL'}**"]
        if not report["PASS"] and report["dangling_refs"]:
            lines += ["", "> FAIL 原因含悬空引用：请先改写对应句子（删除该引或改引存活条目），",
                      "> 更新 edit_ops.json 后重跑 renumber_plan.py，直至 PASS。"]
    with open(os.path.join(out, "renumber_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(work, "renumber_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sys.exit(main())
