#!/usr/bin/env python3
"""anchor_engine.py — 修改定位主攻引擎：双坐标定位 + 基线↔修订稿行号映射 + 回复信定位声明独立核验。

核心能力（对应评分"对得上/可核验性"）：
1. 双坐标定位：edit_report.json 每个 applied op 同时给出
   - 基线侧坐标：章节标题、para_id、基线行号（在基线文件逐行搜索 anchor_quote 得到；
     找不到记"锚点已由改写消除"，用 method/ratio 说明模糊命中情况）；
   - 修订侧坐标：revised_line、所在段 ID、new_text 前 30 字。
2. 行级 diff 映射：difflib.SequenceMatcher 对基线与修订稿全文做行级对齐，
   输出 change regions（基线行区间→修订稿行区间），并把每个 op 按 revised_line
   反查挂到对应区域；生成 /app/output/location_table.md 与 work/anchor_map.json。
3. 回复信定位声明核验（response_letter.md 存在时执行）：
   (a) 所有 E# 引用必须在 edit_report applied 集合内；
   (b) 所有引号（「」〈〉“” \" \"）包裹且 ≥8 字的引文，必须能在 revised_manuscript.md
       中按空白归一化子串找到（或能在审稿意见原文中找到——视为意见摘录）；
   (c) 所有 P\\d{3}[a-z]? / SEC\\d+ / 第?\\d+行 坐标引用——P/SEC 必须在 structure
       或新增段 ID 集合内，行号必须 ≤ 修订稿总行数。
   任何不可核对的声明列入 unresolvable_claims 并 exit 1。
4. 失效锚点预警：method 以 fuzzy 开头的 op 单独列出，提示"锚点为模糊匹配，人工复核定位"。

用法: python3 anchor_engine.py --work /app/work --out /app/output [--baseline <路径>]
缺省 --baseline 时从 work/structure.json 的 source_file 取得。
exit 0=全部定位可核对；1=存在不可核对声明或输入缺失。
"""
import argparse
import difflib
import json
import os
import re
import sys

# 引号对：中文直角引号、中文弯引号、英文直引号
QUOTE_PAIRS = [("「", "」"), ("〈", "〉"), ("“", "”"), ('"', '"')]
MIN_QUOTE_LEN = 8  # 引文核验的最小长度（字）

RE_EREF = re.compile(r"(?<![A-Za-z0-9])E\d+(?![0-9])")          # E1 / E12
RE_PID = re.compile(r"(?<![A-Za-z0-9])P\d{3}[a-z]?(?![0-9A-Za-z])")  # P003 / P005a
RE_SEC = re.compile(r"(?<![A-Za-z0-9])SEC\d+(?![0-9])")         # SEC5
RE_LINE_NO = re.compile(r"第?\s*(\d+)\s*行")                     # 第17行 / 17行


def norm_ws(s):
    """空白归一化：所有连续空白折叠为单空格，用于跨换行/缩进的稳健匹配。"""
    return re.sub(r"\s+", " ", s).strip()


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def read_text(path):
    """多编码尝试读文本；失败返回 None。"""
    if not path or not os.path.exists(path):
        return None
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    return None


def find_anchor_in_lines(lines, needle):
    """在基线逐行搜索锚点。
    返回 (行号1起, 相似度, 方式)；找不到返回 (None, 最佳相似度, 'missing')。
    方式 ∈ exact / normalized / fuzzy。
    """
    if not needle or not needle.strip():
        return None, 0.0, "missing"
    q = needle.strip()
    for i, ln in enumerate(lines, 1):
        if q in ln:
            return i, 1.0, "exact"
    nq = norm_ws(q)
    for i, ln in enumerate(lines, 1):
        if nq and nq in norm_ws(ln):
            return i, 1.0, "normalized"
    best, bi = 0.0, None
    for i, ln in enumerate(lines, 1):
        r = difflib.SequenceMatcher(None, nq, norm_ws(ln)).ratio()
        if r > best:
            best, bi = r, i
    if best >= 0.60:
        return bi, round(best, 3), "fuzzy"
    return None, round(best, 3), "missing"


def build_change_regions(base_lines, rev_lines):
    """行级对齐：基线行区间→修订稿行区间的变更区域（1 起闭区间）。"""
    sm = difflib.SequenceMatcher(None, base_lines, rev_lines, autojunk=False)
    regions = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        regions.append({
            "kind": tag,  # replace / insert / delete
            "baseline_lines": [i1 + 1, i2] if i2 > i1 else None,  # 1 起闭区间
            "revised_lines": [j1 + 1, j2] if j2 > j1 else None,
            "op_ids": [],
        })
    return regions


def region_of(regions, revised_line=None, baseline_line=None):
    """把 op 挂到包含其修订行（优先）或基线行的变更区域；找不到返回 None。"""
    if revised_line is not None:
        for r in regions:
            rl = r.get("revised_lines")
            if rl and rl[0] <= revised_line <= rl[1]:
                return r
    if baseline_line is not None:
        for r in regions:
            bl = r.get("baseline_lines")
            if bl and bl[0] <= baseline_line <= bl[1]:
                return r
    return None


def para_section(structure, para_id):
    """段 ID → 章节标题；新增段（如 P005a）经其锚段推断。"""
    by_id = {p["id"]: p for p in structure.get("paragraphs", [])}
    p = by_id.get(para_id) or by_id.get(re.sub(r"[a-z]+$", "", para_id or ""))
    if not p:
        return None
    for s in structure.get("sections", []):
        if s["id"] == p.get("section_id"):
            return s.get("heading")
    return p.get("section")


def extract_quotes(letter_lines):
    """抽取引号包裹的引文（≥MIN_QUOTE_LEN 字），返回 [{line, quote}]。"""
    out = []
    for ln_no, line in enumerate(letter_lines, 1):
        for open_q, close_q in QUOTE_PAIRS:
            pat = re.escape(open_q) + r"(.*?)" + re.escape(close_q)
            for m in re.finditer(pat, line):
                text = m.group(1).strip()
                if len(text) >= MIN_QUOTE_LEN:
                    out.append({"line": ln_no, "quote": text})
    return out


def verify_letter_claims(letter_text, revised_text, comments_text, applied_ids,
                         known_pids, known_secs, revised_total_lines):
    """核验回复信三类定位声明，返回 (claims 明细, unresolvable 列表)。"""
    claims = {"e_refs": [], "quotes": [], "coords": []}
    unresolvable = []

    # (a) E# 引用必须落在 applied 集合内
    for m in RE_EREF.finditer(letter_text):
        ref = m.group(0)
        entry = {"ref": ref, "line": letter_text[:m.start()].count("\n") + 1,
                 "ok": ref in applied_ids}
        claims["e_refs"].append(entry)
        if not entry["ok"]:
            unresolvable.append({"type": "E引用悬空", "line": entry["line"],
                                 "claim": ref,
                                 "detail": f"{ref} 不在 edit_report applied 集合内"})

    # (b) 引号引文必须能在修订稿中找到（空白归一化子串），或在审稿意见原文中（意见摘录）
    rev_norm = norm_ws(revised_text)
    com_norm = norm_ws(comments_text or "")
    for q in extract_quotes(letter_text.splitlines()):
        nq = norm_ws(q["quote"])
        ok_rev = bool(nq) and nq in rev_norm
        ok_com = bool(nq) and nq in com_norm
        entry = {"line": q["line"], "quote": q["quote"][:120],
                 "found_in": "revised" if ok_rev else ("comments" if ok_com else None)}
        claims["quotes"].append(entry)
        if not (ok_rev or ok_com):
            unresolvable.append({"type": "引文未找到", "line": q["line"],
                                 "claim": q["quote"][:120],
                                 "detail": "引文既不在 revised_manuscript.md 也不在意见原文中"
                                           "（引文须逐字引用修订稿现存文字）"})

    # (c) 坐标引用：P/SEC 合法性 + 行号 ≤ 修订稿总行数
    for m in RE_PID.finditer(letter_text):
        ref = m.group(0)
        line_no = letter_text[:m.start()].count("\n") + 1
        ok = ref in known_pids
        claims["coords"].append({"kind": "para", "ref": ref, "line": line_no, "ok": ok})
        if not ok:
            unresolvable.append({"type": "段坐标不存在", "line": line_no, "claim": ref,
                                 "detail": f"{ref} 不在 structure 或新增段 ID 集合内"})
    for m in RE_SEC.finditer(letter_text):
        ref = m.group(0)
        line_no = letter_text[:m.start()].count("\n") + 1
        ok = ref in known_secs
        claims["coords"].append({"kind": "section", "ref": ref, "line": line_no, "ok": ok})
        if not ok:
            unresolvable.append({"type": "章节坐标不存在", "line": line_no, "claim": ref,
                                 "detail": f"{ref} 不在 structure 章节集合内"})
    for m in RE_LINE_NO.finditer(letter_text):
        n = int(m.group(1))
        line_no = letter_text[:m.start()].count("\n") + 1
        ok = 1 <= n <= revised_total_lines
        claims["coords"].append({"kind": "line", "ref": m.group(0), "line": line_no, "ok": ok})
        if not ok:
            unresolvable.append({"type": "行号越界", "line": line_no, "claim": m.group(0),
                                 "detail": f"行号 {n} 超出修订稿总行数 {revised_total_lines}"})
    return claims, unresolvable


def fmt_span(span):
    if not span:
        return "—"
    return f"L{span[0]}" if span[0] == span[1] else f"L{span[0]}–{span[1]}"


def main():
    ap = argparse.ArgumentParser(description="双坐标定位 + 行号映射 + 回复信定位声明核验")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--baseline", default=None,
                    help="基线稿件路径；缺省从 structure.json 的 source_file 取")
    args = ap.parse_args()

    # ---- 输入装载 ----
    structure = load_json(os.path.join(args.work, "structure.json"))
    if not structure:
        print("[anchor_engine][FATAL] 缺少 work/structure.json", file=sys.stderr)
        return 1
    edit_report = load_json(os.path.join(args.work, "edit_report.json"))
    if not edit_report:
        print("[anchor_engine][FATAL] 缺少 work/edit_report.json（先跑 revision_engine）",
              file=sys.stderr)
        return 1
    revised_path = os.path.join(args.out, "revised_manuscript.md")
    revised_text = read_text(revised_path)
    if revised_text is None:
        print(f"[anchor_engine][FATAL] 缺少 {revised_path}", file=sys.stderr)
        return 1
    rev_lines = revised_text.splitlines()

    baseline_path = args.baseline or structure.get("source_file")
    baseline_text = read_text(baseline_path)
    baseline_mode = "file"
    if baseline_text is None:
        # 降级：以 structure 段落每段一行的伪基线继续，保证坐标/映射仍可产出
        baseline_mode = "structure-fallback"
        baseline_text = "\n\n".join(p["text"] for p in structure.get("paragraphs", []))
        print(f"[anchor_engine][WARN] 基线文件不可读（{baseline_path}），"
              f"降级为 structure 段落模式，基线行号为结构伪行号", file=sys.stderr)
    base_lines = baseline_text.splitlines()

    comments = load_json(os.path.join(args.work, "comments.json"), {}) or {}
    comments_text = " ".join(c.get("raw_text", "")
                             for c in comments.get("comments", []))

    # 已知 ID 集合
    known_pids = {p["id"] for p in structure.get("paragraphs", [])}
    known_secs = {s["id"] for s in structure.get("sections", [])}
    for o in edit_report.get("ops", []):
        for k in ("para_id", "anchor_para"):
            if o.get(k):
                known_pids.add(o[k])
    applied_ids = {o["op_id"] for o in edit_report.get("ops", [])
                   if o.get("status") == "applied"}

    # ---- 1+2：双坐标 + 行级 diff 映射 ----
    regions = build_change_regions(base_lines, rev_lines)
    dual = []
    fuzzy_warnings = []
    for o in edit_report.get("ops", []):
        if o.get("status") != "applied":
            continue
        op_id = o.get("op_id")
        quote = o.get("anchor_quote") or ""
        b_line, b_ratio, b_how = find_anchor_in_lines(base_lines, quote)
        # 基线侧段落：insert_* 的 para_id 是新增段，基线坐标应落到其锚段
        b_para_id = o.get("anchor_para") or o.get("para_id")
        section = para_section(structure, b_para_id) or o.get("section") or "—"
        b_coord = {"section": section, "para_id": b_para_id or "—",
                   "line": b_line, "match": b_how, "ratio": b_ratio}
        if b_line is None:
            # 锚点找不到：记"锚点已由改写消除"，用 method/ratio 说明
            b_coord["note"] = (f"锚点已由改写消除（edit method={o.get('method')}, "
                               f"ratio={o.get('ratio')}；基线最佳相似度 {b_ratio}）")
        r_line = o.get("revised_line")
        head30 = (o.get("new_text_head") or "")[:30]
        region = region_of(regions, revised_line=r_line, baseline_line=b_line)
        if region is not None:
            region["op_ids"].append(op_id)
        method = str(o.get("method", ""))
        status = "applied"
        if method.startswith("fuzzy"):
            status = "锚点模糊-需人工复核"
            fuzzy_warnings.append({
                "op_id": op_id,
                "method": method, "ratio": o.get("ratio"),
                "warning": "锚点为模糊匹配，人工复核定位",
                "baseline_coord": b_coord,
                "revised_line": r_line, "para_id": o.get("para_id"),
                "anchor_quote": quote[:120], "new_text_head": head30,
            })
        dual.append({
            "op_id": op_id, "comment_ref": o.get("comment_ref"), "action": o.get("action"),
            "method": method, "ratio": o.get("ratio"),
            "baseline": b_coord,
            "revised": {"line": r_line, "para_id": o.get("para_id"),
                        "section": section, "new_text_head30": head30},
            "change_region": None if region is None else {
                "kind": region["kind"], "baseline_lines": region["baseline_lines"],
                "revised_lines": region["revised_lines"]},
            "status": status, "has_placeholder": o.get("has_placeholder", False),
            "anchor_quote": quote,
        })

    # ---- 3：回复信定位声明核验（信存在才执行）----
    letter_path = os.path.join(args.out, "response_letter.md")
    letter_text = read_text(letter_path)
    letter_checked = letter_text is not None
    claims, unresolvable = {}, []
    if letter_checked:
        claims, unresolvable = verify_letter_claims(
            letter_text, revised_text, comments_text, applied_ids,
            known_pids, known_secs, len(rev_lines))

    # ---- location_table.md ----
    lines = ["# 修改定位表（location_table.md）", "",
             f"生成：anchor_engine（双坐标定位 + 基线↔修订稿行级映射）。",
             f"基线：`{baseline_path}`（{baseline_mode}，共 {len(base_lines)} 行）；"
             f"修订稿：`revised_manuscript.md`（共 {len(rev_lines)} 行）。", "",
             "| op_id | 意见 | 动作 | 基线坐标 | 修订稿坐标 | 锚点原文摘录 | 状态 |",
             "|-|-|-|-|-|-|-|-|"]
    for d in dual:
        b = d["baseline"]
        if b["line"] is not None:
            b_txt = f"§{b['section']} {b['para_id']} 行{b['line']}"
        else:
            b_txt = f"§{b['section']} {b['para_id']}（锚点已由改写消除）"
        r = d["revised"]
        r_txt = (f"行{r['line']} / {r['para_id']}"
                 if r["line"] is not None else f"{r['para_id']}（见 change_region）")
        if r["new_text_head30"]:
            r_txt += f"<br>新文本：{r['new_text_head30']}"
        anchor_show = (d.get("anchor_quote") or "")
        lines.append(f"| {d['op_id']} | {d['comment_ref'] or '—'} | {d['action'] or '—'} "
                     f"| {b_txt} | {r_txt} | {anchor_show} | {d['status']} |")
    lines += ["", "## 变更区域（基线行 → 修订稿行，difflib 行级对齐）", "",
              "| 类型 | 基线行 | 修订稿行 | 关联 op |", "|-|-|-|-|"]
    for rg in regions:
        lines.append(f"| {rg['kind']} | {fmt_span(rg['baseline_lines'])} "
                     f"| {fmt_span(rg['revised_lines'])} "
                     f"| {', '.join(rg['op_ids']) or '—'} |")
    if fuzzy_warnings:
        lines += ["", "## ⚠ 模糊锚点预警（method 以 fuzzy 开头，须人工复核定位）", ""]
        for w in fuzzy_warnings:
            lines.append(f"- {w['op_id']}（{w['method']}, ratio={w['ratio']}）："
                         f"锚点为模糊匹配，人工复核定位。"
                         f"锚点摘录：{w['anchor_quote']}；修订稿行 {w['revised_line']} / "
                         f"{w['para_id']}；新文本：{w['new_text_head']}")
    if letter_checked:
        lines += ["", "## 回复信定位声明核验", ""]
        if unresolvable:
            lines.append(f"**存在 {len(unresolvable)} 处不可核对声明（引擎 exit 1）：**")
            for u in unresolvable:
                lines.append(f"- [{u['type']}] 第{u['line']}行 `{u['claim']}`：{u['detail']}")
        else:
            n_e = len(claims["e_refs"]); n_q = len(claims["quotes"])
            n_c = len(claims["coords"])
            lines.append(f"全部声明可核对：E# 引用 {n_e} 处、引文 {n_q} 处、"
                         f"坐标引用 {n_c} 处。")
    else:
        lines += ["", "## 回复信定位声明核验", "",
                  "未检测到 response_letter.md，跳过（回信写好后重跑本引擎执行核验）。"]
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "location_table.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # ---- anchor_map.json ----
    anchor_map = {
        "baseline_file": baseline_path, "baseline_mode": baseline_mode,
        "revised_file": revised_path,
        "n_baseline_lines": len(base_lines), "n_revised_lines": len(rev_lines),
        "summary": {
            "n_applied": len(dual),
            "n_fuzzy_warnings": len(fuzzy_warnings),
            "n_change_regions": len(regions),
            "letter_checked": letter_checked,
            "n_unresolvable_claims": len(unresolvable),
        },
        "dual_coordinates": dual,
        "change_regions": regions,
        "fuzzy_warnings": fuzzy_warnings,
        "letter_claims": {"checked": letter_checked, "claims": claims,
                          "unresolvable_claims": unresolvable},
    }
    with open(os.path.join(args.work, "anchor_map.json"), "w", encoding="utf-8") as f:
        json.dump(anchor_map, f, ensure_ascii=False, indent=1)

    # ---- 汇总输出 ----
    print(f"[anchor_engine] 双坐标 {len(dual)} 处；变更区域 {len(regions)} 个；"
          f"模糊锚预警 {len(fuzzy_warnings)} 处；回复信核验={'已执行' if letter_checked else '跳过'}"
          f"；不可核对声明 {len(unresolvable)} 处")
    if unresolvable:
        for u in unresolvable:
            print(f"[anchor_engine][FAIL] {u['type']} 第{u['line']}行: {u['detail']}",
                  file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
