#!/usr/bin/env python3
"""cite_engine.py — 引用标记的解析、重排、渲染与样式转换（纯确定性，可被各版本复用）。

子命令:
  renumber   --manuscript work/manuscript.json --mapping work/mapping.json [--inplace-text file]
               按 old->new 映射重排稿件内数字编号标记，输出重排后稿件与一致性报告。
  render     --records work/library.json --style gbt2015_numeric|gbt2015_author|apa7|vancouver
               生成格式化参考文献表（参考文献.md 与 json）。
  convert    --library work/library.json --to bibtex|ris|gbt2015|apa7  格式转换输出。
  audit      --manuscript work/manuscript.json --nrefs N  一致性体检（悬空/越界/连续/样式混杂）。
mapping.json: {"1": 2, "2": 1, ...}（旧编号 -> 新编号；null/缺失 = 删除）
"""
import argparse, json, os, re, sys

CN_TYPE_TAG = {"journal_article": "J", "conference_paper": "C", "book": "M",
               "book_chapter": "M", "thesis": "D", "patent": "P", "standard": "S",
               "report": "R", "preprint": "EB", "misc": "EB", "dataset": "DS"}

def fmt_names(names, style, lang):
    """GB/T 7714: 姓 名首字母大写; 中文 3 人后 '等'; 英文 3 人后 'et al'。APA7: 20 人后省略。"""
    names = [n.strip() for n in names if n and n.strip()]
    if style == "apa7":
        if len(names) > 21:
            shown = names[:19] + ["… " + names[-1].split(",")[-1].strip()]
        else:
            shown = names
        return ", ".join(shown)
    if lang == "zh":
        shown = names[:3]
        s = ", ".join(shown)
        if len(names) > 3:
            s += ", 等"
        return s
    shown = names[:3]
    s = ", ".join(shown)
    if len(names) > 3:
        s += ", et al"
    return s

def render_entry(rec, style, index=None):
    lang = rec.get("language", "en")
    title = (rec.get("title") or "").rstrip(".。")
    venue = (rec.get("venue") or "").rstrip(".。")
    year = rec.get("year") or ""
    vol = rec.get("volume") or ""
    issue = rec.get("issue") or ""
    pages = (rec.get("pages") or "").rstrip(".。")
    doi = rec.get("doi") or ""
    names = fmt_names(rec.get("authors") or [], style, lang)
    if style in ("gbt2015_numeric", "gbt2015_author"):
        tag = CN_TYPE_TAG.get(rec.get("entry_type", "misc"), "EB")
        core = f"{names}. {title}[{tag}]"
        if venue:
            core += f". {venue}"
        yv = ""
        if year:
            yv += f", {year}"
        if vol:
            yv += f", {vol}"
        if issue:
            yv += f"({issue})"
        core += yv
        if pages:
            core += f": {pages}"
        core += "."
        if doi:
            core += f" DOI: {doi}."
        return core
    if style == "apa7":
        core = ""
        if names:
            core += names + " "
        core += f"({year})." if year else "(n.d.)."
        core += f" {title}."
        if venue:
            core += f" *{venue}*"
            if vol:
                core += f", *{vol}*"
            if issue:
                core += f"({issue})"
            if pages:
                core += f", {pages}"
            core += "."
        if doi:
            core += f" https://doi.org/{doi}"
        return core
    if style == "vancouver":
        core = ""
        if names:
            core += ", ".join(rec.get("authors") or []) + ". "
        core += title + "."
        if venue:
            core += f" {venue}."
        if year:
            core += f" {year}"
            if vol:
                core += f";{vol}"
            if issue:
                core += f"({issue})"
            if pages:
                core += f":{pages}"
            core += "."
        if doi:
            core += f" doi:{doi}"
        return core
    return title

def compress_nums(nums):
    """[1,2,3,5] -> '1-3,5'"""
    nums = sorted(set(nums))
    if not nums:
        return ""
    out, start, prev = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        out.append(f"{start}-{prev}" if prev > start else f"{start}")
        start = prev = n
    out.append(f"{start}-{prev}" if prev > start else f"{start}")
    return ",".join(out)

def expand_raw(raw):
    """'1-3,5' -> [1,2,3,5]"""
    nums = []
    for part in re.split(r"[,，]", raw):
        part = part.strip()
        m = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if b - a <= 200:
                nums.extend(range(a, b + 1))
        elif part.isdigit():
            nums.append(int(part))
    return nums

NUM_MARK_RE = re.compile(r"\[(\d+(?:\s*[-–—,，]\s*\d+)*)\]")

def renumber_text(text, mapping, stats):
    def repl(m):
        old_nums = expand_raw(m.group(1))
        new_nums = []
        dropped = []
        for n in old_nums:
            v = mapping.get(str(n))
            if v is None:
                dropped.append(n)
                stats["dropped_marks"] += 1
            else:
                new_nums.append(int(v))
        if dropped:
            stats["paras_with_dropped"].add(stats.get("_cur_pid", "?"))
        if not new_nums:
            stats["empty_marks"] += 1
            return ""  # 全部删除则移除标记，留待审校
        stats["marks_renumbered"] += 1
        return f"[{compress_nums(new_nums)}]"
    return NUM_MARK_RE.sub(repl, text)

def cmd_renumber(args):
    with open(args.manuscript, encoding="utf-8") as f:
        ms = json.load(f)
    with open(args.mapping, encoding="utf-8") as f:
        mapping = json.load(f)
    stats = {"marks_renumbered": 0, "dropped_marks": 0, "empty_marks": 0,
             "paras_with_dropped": set(), "_cur_pid": None}
    for p in ms.get("paragraphs", []):
        stats["_cur_pid"] = p["pid"]
        p["text"] = renumber_text(p["text"], mapping, stats)
        # 更新 cite_marks
        marks = []
        for m in NUM_MARK_RE.finditer(p["text"]):
            marks.append({"raw": m.group(0), "style": "numeric",
                          "nums": expand_raw(m.group(1)), "span": [m.start(), m.end()]})
        p["cite_marks"] = marks
    # 连续性检查
    all_nums = [n for p in ms["paragraphs"] for m in p["cite_marks"] for n in m["nums"]]
    maxn = max(all_nums) if all_nums else 0
    missing = [n for n in range(1, maxn + 1) if n not in set(all_nums)]
    report = {"mapping": mapping, "marks_renumbered": stats["marks_renumbered"],
              "dropped_mark_count": stats["dropped_marks"],
              "empty_marks_removed": stats["empty_marks"],
              "paras_with_dropped_refs": sorted(stats["paras_with_dropped"]),
              "max_inline_number": maxn,
              "gaps_in_sequence": missing,
              "sequential": not missing}
    out_ms = args.manuscript if args.inplace else args.manuscript.replace(".json", ".renumbered.json")
    with open(out_ms, "w", encoding="utf-8") as f:
        json.dump(ms, f, ensure_ascii=False, indent=2)
    rep_path = os.path.join(os.path.dirname(args.manuscript) or ".", "renumber_report.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    if args.inplace_text:
        with open(args.inplace_text, encoding="utf-8") as f:
            raw = f.read()
        with open(args.inplace_text + ".renumbered", "w", encoding="utf-8") as f:
            f.write(renumber_text(raw, mapping, stats))
    print(f"[renumber] 重排 {stats['marks_renumbered']} 处, 悬空 {stats['dropped_marks']} 处, "
          f"连续={'是' if not missing else '否 缺' + str(missing)}")
    return 0

def cmd_render(args):
    with open(args.records, encoding="utf-8") as f:
        lib = json.load(f)
    recs = lib.get("records", [])
    if args.order:
        with open(args.order, encoding="utf-8") as f:
            order = json.load(f)  # [rid,...] 按引用顺序
        byid = {r["id"]: r for r in recs}
        recs = [byid[r] for r in order if r in byid]
    lines, entries = [], []
    for i, r in enumerate(recs, 1):
        text = render_entry(r, args.style, i)
        label = f"[{i}]" if "numeric" in args.style or args.style == "vancouver" else ""
        lines.append(f"{label} {text}".strip())
        entries.append({"number": i, "id": r["id"], "text": text})
    outdir = os.path.dirname(args.out) or "."
    os.makedirs(outdir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("## 参考文献\n\n" + "\n\n".join(lines) + "\n")
    with open(args.out.replace(".md", ".json"), "w", encoding="utf-8") as f:
        json.dump({"style": args.style, "entries": entries}, f, ensure_ascii=False, indent=2)
    print(f"[render] {len(entries)} 条, 样式 {args.style} -> {args.out}")
    return 0

def cmd_convert(args):
    with open(args.library, encoding="utf-8") as f:
        lib = json.load(f)
    recs = lib.get("records", [])
    out = []
    if args.to == "bibtex":
        for r in recs:
            bt = {"journal_article": "article", "conference_paper": "inproceedings",
                  "book": "book", "thesis": "phdthesis", "misc": "misc",
                  "preprint": "misc", "report": "techreport", "patent": "misc"}.get(r["entry_type"], "misc")
            fields = [f"  title = {{{r.get('title','')}}}"]
            if r.get("authors"):
                fields.append(f"  author = {{{' and '.join(r['authors'])}}}")
            if r.get("year"):
                fields.append(f"  year = {{{r['year']}}}")
            if r.get("venue"):
                key = "journal" if bt == "article" else ("booktitle" if bt == "inproceedings" else "publisher")
                fields.append(f"  {key} = {{{r['venue']}}}")
            for k in ("volume", "issue", "pages", "doi"):
                if r.get(k):
                    fields.append(f"  {k} = {{{r[k]}}}")
            out.append(f"@{bt}{{{r['id']},\n" + ",\n".join(fields) + "\n}")
    elif args.to == "ris":
        ty = {"journal_article": "JOUR", "conference_paper": "CONF", "book": "BOOK",
              "thesis": "THES", "report": "RPRT", "patent": "PAT", "misc": "GEN"}.get
        for r in recs:
            lines = [f"TY  - {ty(r['entry_type'], 'GEN')}"]
            for a in r.get("authors", []):
                lines.append(f"AU  - {a}")
            if r.get("title"): lines.append(f"TI  - {r['title']}")
            if r.get("venue"): lines.append(f"JO  - {r['venue']}")
            if r.get("year"): lines.append(f"PY  - {r['year']}")
            if r.get("volume"): lines.append(f"VL  - {r['volume']}")
            if r.get("issue"): lines.append(f"IS  - {r['issue']}")
            if r.get("pages"): lines.append(f"SP  - {r['pages']}")
            if r.get("doi"): lines.append(f"DO  - {r['doi']}")
            lines.append("ER  - ")
            out.append("\n".join(lines))
    elif args.to in ("gbt2015", "apa7"):
        style = "gbt2015_numeric" if args.to == "gbt2015" else "apa7"
        for i, r in enumerate(recs, 1):
            out.append(f"[{i}] {render_entry(r, style, i)}")
    else:
        print(f"不支持的目标格式: {args.to}", file=sys.stderr)
        return 2
    dest = args.out or f"converted.{args.to.split('_')[0]}"
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n\n".join(out) + "\n")
    print(f"[convert] {len(recs)} 条 -> {dest} ({args.to})")
    return 0

def cmd_audit(args):
    with open(args.manuscript, encoding="utf-8") as f:
        ms = json.load(f)
    issues = []
    all_nums = []
    style_mix = set()
    for p in ms.get("paragraphs", []):
        for m in p.get("cite_marks", []):
            style_mix.add(m["style"])
            if m["style"] == "numeric":
                all_nums.extend(m["nums"])
                for n in m["nums"]:
                    if n > args.nrefs:
                        issues.append({"type": "out_of_range", "pid": p["pid"],
                                       "raw": m["raw"], "detail": f"编号 {n} 超过文献表数量 {args.nrefs}"})
    cnt = {}
    for n in all_nums:
        cnt[n] = cnt.get(n, 0) + 1
    dangling = [n for n in sorted(cnt) if n > args.nrefs]
    maxn = max(all_nums) if all_nums else 0
    missing = [n for n in range(1, maxn + 1) if n not in cnt]
    if missing:
        issues.append({"type": "gap", "detail": f"1..{maxn} 中未引用编号: {missing}"})
    if len(style_mix) > 1:
        issues.append({"type": "style_mix", "detail": f"正文引用样式混杂: {sorted(style_mix)}"})
    first = ms["paragraphs"][0]["text"][:60] if ms.get("paragraphs") else ""
    report = {"n_refs": args.nrefs, "n_inline_marks": len(all_nums),
              "distinct_numbers": len(cnt), "out_of_range": dangling,
              "gaps": missing, "sequential": not missing,
              "styles": sorted(style_mix), "style_consistent": len(style_mix) <= 1,
              "issues": issues}
    rp = os.path.join(os.path.dirname(args.manuscript) or ".", "consistency_audit.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[audit] 标记 {len(all_nums)} 处, 越界 {len(dangling)}, 缺口 {len(missing)}, "
          f"样式一致={report['style_consistent']}")
    return 1 if any(i["type"] in ("out_of_range", "gap") for i in issues) else 0

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("renumber"); p.add_argument("--manuscript", required=True)
    p.add_argument("--mapping", required=True); p.add_argument("--inplace", action="store_true")
    p.add_argument("--inplace-text"); p.set_defaults(fn=cmd_renumber)
    p = sub.add_parser("render"); p.add_argument("--records", required=True)
    p.add_argument("--style", required=True); p.add_argument("--order")
    p.add_argument("--out", default="references/references.md"); p.set_defaults(fn=cmd_render)
    p = sub.add_parser("convert"); p.add_argument("--library", required=True)
    p.add_argument("--to", required=True); p.add_argument("--out"); p.set_defaults(fn=cmd_convert)
    p = sub.add_parser("audit"); p.add_argument("--manuscript", required=True)
    p.add_argument("--nrefs", type=int, required=True); p.set_defaults(fn=cmd_audit)
    args = ap.parse_args()
    return args.fn(args)

if __name__ == "__main__":
    sys.exit(main())
