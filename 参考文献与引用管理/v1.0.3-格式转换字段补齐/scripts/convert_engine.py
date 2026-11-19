#!/usr/bin/env python3
"""convert_engine.py — 版本4 专属：声明式格式映射转换 + 字段补齐审计。

职责:
  1. 调用 cite_engine render/convert 生成目标格式 /app/output/converted_refs.txt 与
     /app/output/references.md（bibtex/ris 目标时 references.md 为代码块包装）。
  2. 生成 /app/output/field_audit.json：逐条目 {rid, 缺字段列表, 补齐动作, 来源 rid}。
     补齐动作仅两种: "copied_from_<RID>"（同题重复条目字段互补）或 "not_provided"
     （材料未提供，不得臆造补齐）。
  3. 生成 /app/output/convert_report.md（人读）与 /app/output/report.md（预览用副本）。
  4. 标点规范化：英文条目半角、中文条目全角（DOI 受保护不被改写）。
  5. 作者名转换： "Smith, John" -> GB/T "Smith J"（仅姓氏 + 名首字母，不臆造中间名）。
  6. 文献类型标识表来自 references/format_specs/gbt_type_tags.md（简单解析，不硬编码）；
     目标规范参数来自 references/format_specs/<style>.md 的"机器可读参数"节。
  7. 可选 --try-online：以 5 秒超时探测 Crossref；失败/不可用时诚实记录 unverified，
     任何情况下不臆造字段。

用法:
  python3 convert_engine.py --library work/library.json \
      --to gbt2015_numeric|gbt2015_author|apa7|vancouver|bibtex|ris \
      --outdir /app/output [--work /app/work] [--specs-dir references/format_specs] [--try-online]
"""
import argparse, json, os, re, shutil, socket, subprocess, sys, urllib.request

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CITE_ENGINE = os.path.join(SCRIPT_DIR, "cite_engine.py")

CHECK_FIELDS = ["title", "authors", "year", "venue", "volume", "issue", "pages", "doi"]
FILLABLE_FIELDS = ["volume", "issue", "pages", "doi", "year", "venue"]
CJK_RE = re.compile(r"[一-鿿]")
DOI_RE = re.compile(r"10\.\d{4,9}/\S+")

# ---------- 资源文件解析（声明式映射表，可复用，不硬编码进脚本） ----------

def load_spec_params(specs_dir, style):
    """解析 references/format_specs/<style>.md 的『机器可读参数』节，返回 dict。"""
    path = os.path.join(specs_dir, f"{style}.md")
    params = {}
    if not os.path.exists(path):
        return params, None
    with open(path, encoding="utf-8") as f:
        text = f.read()
    in_block = False
    for line in text.splitlines():
        if re.match(r"^##\s*机器可读参数", line):
            in_block = True
            continue
        if in_block and line.startswith("## "):
            break
        if in_block:
            m = re.match(r"\s*-\s*([a-z_]+)\s*:\s*(.+?)\s*$", line)
            if m:
                params[m.group(1)] = m.group(2)
    return params, path

def load_type_tags(specs_dir):
    """解析 references/format_specs/gbt_type_tags.md 的映射表 -> {entry_type: 标识}。"""
    path = os.path.join(specs_dir, "gbt_type_tags.md")
    table = {}
    if not os.path.exists(path):
        return table, None
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*\|\s*`?([a-z_]+)`?\s*\|\s*`?([A-Z]{1,4})`?\s*\|", line)
            if m and m.group(1) not in ("entry_type",):
                table[m.group(1)] = m.group(2)
    return table, path

# ---------- 作者名转换 ----------

def _split_western(name):
    """'Smith, John Michael' -> ('Smith', 'John Michael'); 'John Smith' -> ('Smith', 'John')。"""
    name = name.strip().strip(".")
    if "," in name:
        last, given = name.split(",", 1)
        return last.strip(), given.strip()
    parts = name.split()
    if len(parts) >= 2:
        return parts[-1], " ".join(parts[:-1])
    return name, ""

def western_to_gbt(name):
    """'Smith, John' -> 'Smith J'；'Smith, John Michael' -> 'Smith JM'（取全部名首字母，不臆造）。"""
    if not name or CJK_RE.search(name):
        return name
    last, given = _split_western(name)
    initials = "".join(t[0].upper() for t in re.split(r"[\s\-]+", given) if t and t[0].isalpha())
    return f"{last} {initials}" if initials else last

def western_to_apa(name):
    """'Smith, John' -> 'Smith, J.'；'Jean-Luc Picard' -> 'Picard, J.-L.'。"""
    if not name or CJK_RE.search(name):
        return name
    last, given = _split_western(name)
    parts = []
    for tok in given.split():
        subs = [s for s in tok.split("-") if s and s[0].isalpha()]
        if subs:
            parts.append("-".join(s[0].upper() + "." for s in subs))
    return f"{last}, {' '.join(parts)}" if parts else last

def normalize_authors(recs, to):
    """按目标规范预处理作者名字形；返回新 records（不修改原对象）。"""
    out = []
    for r in recs:
        r2 = dict(r)
        auth = list(r.get("authors") or [])
        if to in ("gbt2015_numeric", "gbt2015_author", "vancouver"):
            r2["authors"] = [western_to_gbt(a) for a in auth]
        elif to == "apa7":
            r2["authors"] = [western_to_apa(a) for a in auth]
        out.append(r2)
    return out

# ---------- 标点规范化 ----------

def normalize_punct(text, lang, zh_fullwidth=True):
    """GB/T：中文条目全角、英文条目半角；APA/Vancouver：一律半角（zh_fullwidth=False）。
    DOI 子串受保护不被改写。"""
    if lang == "zh" and zh_fullwidth:
        protected = []
        def stash(m):
            protected.append(m.group(0))
            return f"\x00{len(protected)-1}\x00"
        t = DOI_RE.sub(stash, text)
        t = t.replace(", ", "，").replace(",", "，")
        t = t.replace("; ", "；").replace(";", "；")
        t = t.replace(": ", "：").replace(":", "：")
        t = t.replace("(", "（").replace(")", "）")
        t = re.sub(r"\.\s*", "．", t)
        t = re.sub(r"\x00(\d+)\x00", lambda m: protected[int(m.group(1))], t)
        return t
    # 英文条目：全角 -> 半角并恢复空格
    t = text
    for fw, hw in (("，", ", "), ("．", ". "), ("。", ". "), ("：", ": "),
                   ("；", "; "), ("（", " ("), ("）", ")")):
        t = t.replace(fw, hw)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t

# ---------- 字段补齐（仅跨条目推理：同题重复条目字段互补） ----------

def norm_title_key(title):
    return re.sub(r"[^0-9a-z一-鿿]", "", (title or "").lower())

def cross_record_fill(recs):
    """同题（规范化标题相同）且 entry_type 相同或一方为 misc、年份一致或一方缺失时，
    允许字段互补。返回 (filled_recs, fills) ，fills: {rid: [{field, action, source_rid, note}]}"""
    groups = {}
    for r in recs:
        groups.setdefault(norm_title_key(r.get("title")), []).append(r)
    fills = {}
    filled = [dict(r) for r in recs]
    byid = {r["id"]: r for r in filled}
    for key, members in groups.items():
        if not key or len(members) < 2:
            continue
        for r in members:
            for donor in members:
                if donor is r:
                    continue
                same_type = donor.get("entry_type") == r.get("entry_type") or \
                    "misc" in (donor.get("entry_type"), r.get("entry_type"))
                yr_r, yr_d = r.get("year"), donor.get("year")
                year_ok = (not yr_r) or (not yr_d) or (yr_r == yr_d)
                if not (same_type and year_ok):
                    continue
                for field in FILLABLE_FIELDS:
                    if not r.get(field) and donor.get(field):
                        tgt = byid[r["id"]]
                        if not tgt.get(field):
                            tgt[field] = donor[field]
                            fills.setdefault(r["id"], []).append({
                                "field": field, "action": f"copied_from_{donor['id']}",
                                "source_rid": donor["id"],
                                "note": "同题重复条目字段互补（跨条目推理，非臆造）"})
    return filled, fills

# ---------- Crossref 探测（诚实降级） ----------

def probe_crossref(timeout=5):
    socket.setdefaulttimeout(timeout)
    try:
        req = urllib.request.Request(
            "https://api.crossref.org/works?rows=1",
            headers={"User-Agent": "ref-format-converter/1.0 (mailto:unknown@example.com)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200, None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

# ---------- cite_engine 调用 ----------

def run_cite_engine(argv):
    r = subprocess.run([sys.executable, CITE_ENGINE] + argv,
                       capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout or "") + (r.stderr or "")

# ---------- 字段保留率 ----------

def field_kept(field, value, line):
    if not value:
        return True
    lv = line.lower()
    if field == "title":
        return value[:30].lower().rstrip(".。") in lv
    if field == "authors":
        if isinstance(value, list) and value:
            surname = re.split(r"[,\s]", value[0])[0]
            return bool(surname) and surname.lower() in lv
        return True
    if field == "year":
        return str(value) in line
    if field in ("venue", "pages", "doi"):
        return str(value).lower().rstrip(".。") in lv
    if field in ("volume", "issue"):
        return bool(re.search(rf"(?<!\d){re.escape(str(value))}(?!\d)", line))
    return str(value) in line

# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", required=True)
    ap.add_argument("--to", required=True,
                    choices=["gbt2015_numeric", "gbt2015_author", "apa7",
                             "vancouver", "bibtex", "ris"])
    ap.add_argument("--outdir", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--specs-dir", default=os.path.join(SKILL_DIR, "references", "format_specs"))
    ap.add_argument("--try-online", action="store_true",
                    help="探测 Crossref（5 秒超时）；结果仅记录，不用于自动补齐")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    os.makedirs(args.work, exist_ok=True)
    exceptions, manual_confirmations = [], []

    with open(args.library, encoding="utf-8") as f:
        lib = json.load(f)
    recs = lib.get("records", [])
    if not recs:
        print("[convert_engine] 文献库为空", file=sys.stderr)
        return 1

    # 1. 读取声明式资源
    spec_params, spec_path = load_spec_params(args.specs_dir, args.to)
    type_tags, tags_path = load_type_tags(args.specs_dir)
    if args.to.startswith("gbt2015") and not type_tags:
        exceptions.append({"phase": "convert", "issue": f"类型标识表缺失: {tags_path or args.specs_dir}",
                           "action": "退回 cite_engine 内置映射"})
    if not spec_params:
        exceptions.append({"phase": "convert", "issue": f"规范参数文件缺失: {spec_path or args.to}",
                           "action": "使用 cite_engine 默认模板"})

    # 2. 跨条目字段互补
    filled_recs, fills = cross_record_fill(recs)

    # 3. Crossref 探测（可选；仅记录，不自动补齐）
    online_status = "not_attempted"
    if args.try_online:
        need_doi = [r for r in filled_recs if not r.get("doi")]
        if need_doi:
            ok, err = probe_crossref(timeout=5)
            if ok:
                online_status = "reachable"
                manual_confirmations.append({
                    "item": "online_doi_lookup",
                    "note": "Crossref 可达，但自动联网补齐已禁用；请人工逐条核对后补 DOI。",
                    "rids": [r["id"] for r in need_doi]})
            else:
                online_status = f"unavailable: {err}"
                exceptions.append({"phase": "online_probe",
                                   "issue": f"Crossref 探测失败（5s 超时）: {err}",
                                   "action": "缺失 DOI 一律标记 unverified/not_provided，不得臆造"})

    # 4. 作者名字形归一 + 写归一化库
    norm_recs = normalize_authors(filled_recs, args.to)
    norm_lib = dict(lib)
    norm_lib["records"] = norm_recs
    norm_path = os.path.join(args.work, "library.normalized.json")
    with open(norm_path, "w", encoding="utf-8") as f:
        json.dump(norm_lib, f, ensure_ascii=False, indent=2)

    # 5. 调用 cite_engine 生成目标格式
    byid = {r["id"]: r for r in norm_recs}
    final_lines = {}  # rid -> 最终展示行（含标点规范化）
    engine_log = []
    if args.to in ("gbt2015_numeric", "gbt2015_author", "apa7", "vancouver"):
        refs_md = os.path.join(args.outdir, "references.md")
        rc, log = run_cite_engine(["render", "--records", norm_path,
                                   "--style", args.to, "--out", refs_md])
        engine_log.append(log.strip())
        if rc != 0:
            exceptions.append({"phase": "render", "issue": log.strip()[-300:], "action": "中断"})
            print(f"[convert_engine] cite_engine render 失败: {log}", file=sys.stderr)
            return 2
        with open(refs_md.replace(".md", ".json"), encoding="utf-8") as f:
            rendered = json.load(f)
        zh_fw = args.to.startswith("gbt2015")  # APA/Vancouver 条目内部一律半角
        for e in rendered.get("entries", []):
            rid, text = e["id"], e["text"]
            # 类型标识以资源文件 gbt_type_tags.md 为准（覆盖引擎内置映射）
            if args.to.startswith("gbt2015") and type_tags:
                want = type_tags.get((byid[rid].get("entry_type") or "misc"), "EB")
                text = re.sub(r"\[[A-Z]{1,4}\]", f"[{want}]", text, count=1)
            text = normalize_punct(text, byid[rid].get("language", "en"), zh_fullwidth=zh_fw)
            final_lines[rid] = text
        # converted_refs.txt: 带编号
        order = [e["id"] for e in rendered.get("entries", [])]
        numeric = args.to in ("gbt2015_numeric", "vancouver")
        lines = []
        for i, rid in enumerate(order, 1):
            label = f"[{i}] " if numeric else ""
            lines.append(f"{label}{final_lines[rid]}")
        with open(os.path.join(args.outdir, "converted_refs.txt"), "w", encoding="utf-8") as f:
            f.write("\n\n".join(lines) + "\n")
        # references.md 重写为规范化后的文本
        with open(refs_md, "w", encoding="utf-8") as f:
            f.write(f"## 参考文献（{args.to}）\n\n" + "\n\n".join(lines) + "\n")
    else:  # bibtex / ris 回转
        conv_path = os.path.join(args.outdir, "converted_refs.txt")
        rc, log = run_cite_engine(["convert", "--library", norm_path,
                                   "--to", args.to, "--out", conv_path])
        engine_log.append(log.strip())
        if rc != 0:
            print(f"[convert_engine] cite_engine convert 失败: {log}", file=sys.stderr)
            return 2
        with open(conv_path, encoding="utf-8") as f:
            conv_text = f.read()
        with open(os.path.join(args.outdir, "references.md"), "w", encoding="utf-8") as f:
            f.write(f"## 参考文献（{args.to} 导出）\n\n```\n{conv_text}```\n")
        # cite_engine convert 按记录顺序输出、空行分隔；逐块对应以便字段保留率核对
        chunks = [c for c in conv_text.strip().split("\n\n") if c.strip()]
        for i, r in enumerate(norm_recs):
            final_lines[r["id"]] = chunks[i] if i < len(chunks) else ""

    # 6. 字段审计
    audit_records = []
    kept_total = present_total = 0
    not_provided_list = []
    for r0 in recs:
        rid = r0["id"]
        rf = byid[rid]
        line = final_lines.get(rid, "")
        missing = [k for k in CHECK_FIELDS if not rf.get(k)]
        fill_entries = []
        copied = {x["field"]: x for x in fills.get(rid, [])}
        for k in missing:
            entry = {"field": k, "action": "not_provided", "source_rid": None,
                     "note": "材料未提供，不得臆造补齐"}
            if args.try_online and k == "doi" and online_status.startswith("unavailable"):
                entry["note"] = "材料未提供，不得臆造补齐；Crossref 探测失败，状态 unverified"
            fill_entries.append(entry)
            not_provided_list.append({"rid": rid, "field": k})
        for k, x in copied.items():
            fill_entries.append({"field": k, "action": x["action"],
                                 "source_rid": x["source_rid"], "note": x["note"]})
        # 字段保留率（以补齐后记录为准，对照最终输出行）
        present = [k for k in CHECK_FIELDS if rf.get(k)]
        kept = [k for k in present if field_kept(k, rf.get(k), line)]
        dropped = [k for k in present if k not in kept]
        kept_total += len(kept)
        present_total += len(present)
        audit_records.append({
            "rid": rid,
            "source_file": r0.get("source_file"), "source_index": r0.get("source_index"),
            "raw_format": r0.get("raw_format"), "entry_type": r0.get("entry_type"),
            "language": r0.get("language"),
            "missing_fields": missing,
            "fills": fill_entries,
            "fields_present": present, "fields_kept": kept, "fields_dropped_in_render": dropped,
        })

    retention = (kept_total / present_total) if present_total else 1.0
    audit = {
        "target": args.to,
        "spec_file": spec_path, "type_tag_file": tags_path,
        "spec_params": spec_params,
        "online_lookup": {"attempted": bool(args.try_online), "status": online_status,
                          "policy": "禁止联网臆造；探测失败一律 unverified，字段标 not_provided"},
        "summary": {
            "n_records": len(recs),
            "n_with_missing": sum(1 for a in audit_records if a["missing_fields"]),
            "n_copied_fills": sum(len(fills.get(rid, [])) for rid in fills),
            "n_not_provided": len(not_provided_list),
            "field_retention_rate": round(retention, 4),
        },
        "records": audit_records,
    }
    with open(os.path.join(args.outdir, "field_audit.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)

    # 7. convert_report.md（人读）
    fmt_counts, type_counts, lang_counts = {}, {}, {}
    for r in recs:
        fmt_counts[r.get("raw_format", "?")] = fmt_counts.get(r.get("raw_format", "?"), 0) + 1
        type_counts[r.get("entry_type", "?")] = type_counts.get(r.get("entry_type", "?"), 0) + 1
        lang_counts[r.get("language", "?")] = lang_counts.get(r.get("language", "?"), 0) + 1
    rep = []
    rep.append(f"# 格式转换与字段补齐报告（目标: {args.to}）\n")
    rep.append("## 1. 源格式统计\n")
    rep.append("- 来源格式: " + ", ".join(f"{k}×{v}" for k, v in sorted(fmt_counts.items())))
    rep.append("- 文献类型: " + ", ".join(f"{k}×{v}" for k, v in sorted(type_counts.items())))
    rep.append("- 语种: " + ", ".join(f"{k}×{v}" for k, v in sorted(lang_counts.items())))
    rep.append(f"- 规范参数文件: {spec_path or '缺失（使用引擎默认）'}")
    rep.append(f"- 类型标识表: {tags_path or '缺失（使用引擎默认）'}")
    rep.append(f"- 联网探测: {online_status}（策略：不臆造，失败即 unverified）\n")
    rep.append("## 2. 逐条转换前后对照摘录\n")
    byid_orig = {r["id"]: r for r in recs}
    for a in audit_records:
        r0 = byid_orig[a["rid"]]
        before = (f"[{a['raw_format']}] {r0.get('source_file')}#{r0.get('source_index')} | "
                  f"{r0.get('entry_type')} | {', '.join(r0.get('authors') or []) or '—'}. "
                  f"{r0.get('title') or '—'}. {r0.get('venue') or '—'}, {r0.get('year') or '—'}, "
                  f"{r0.get('volume') or '—'}({r0.get('issue') or '—'}): {r0.get('pages') or '—'}. "
                  f"DOI: {r0.get('doi') or '—'}")
        rep.append(f"### {a['rid']}\n- 转换前: {before}\n- 转换后: {a_line(a, final_lines)}\n")
    rep.append("## 3. 字段保留率\n")
    rep.append(f"- 总体保留率: {retention:.1%}（{kept_total}/{present_total}，以补齐后字段对照最终输出，启发式核对）")
    for a in audit_records:
        if a["fields_dropped_in_render"]:
            rep.append(f"- {a['rid']}: 渲染后疑似丢失 {a['fields_dropped_in_render']}（需人工复核）")
    rep.append("")
    rep.append("## 4. 未提供字段清单（材料未提供，不得臆造补齐）\n")
    if not_provided_list:
        for x in not_provided_list:
            rep.append(f"- {x['rid']}: 缺 `{x['field']}`")
    else:
        rep.append("- 无")
    rep.append("")
    copied_any = [dict(x, rid=rid) for rid in fills for x in fills[rid]]
    rep.append("## 5. 跨条目补齐记录（同题重复条目字段互补）\n")
    if copied_any:
        for x in copied_any:
            rep.append(f"- {x['rid']}.{x['field']} <- {x['source_rid']}（{x['note']}）")
    else:
        rep.append("- 无（未发现满足条件的同题重复条目，或字段已齐全）")
    rep.append("")
    report_text = "\n".join(rep)
    with open(os.path.join(args.outdir, "convert_report.md"), "w", encoding="utf-8") as f:
        f.write(report_text)
    shutil.copyfile(os.path.join(args.outdir, "convert_report.md"),
                    os.path.join(args.outdir, "report.md"))

    # 8. work/ 中间产物（供 assemble_result 汇总）
    change_log = [{"op": "convert", "location": a["rid"],
                   "before": f"{a['raw_format']}:{a['source_file']}#{a['source_index']}",
                   "after": final_lines.get(a["rid"], "")[:200],
                   "reason": f"格式转换为 {args.to}，标点按语种规范化"}
                  for a in audit_records]
    for rid, xs in fills.items():
        for x in xs:
            change_log.append({"op": "fill", "location": f"{rid}.{x['field']}",
                               "before": "", "after": f"<- {x['source_rid']}",
                               "reason": x["note"]})
    evidence = [{"entry_id": a["rid"], "location": f"{a['source_file']}#{a['source_index']}",
                 "source": "条目字段", "support": "converted",
                 "rationale": f"{a['raw_format']} -> {args.to}",
                 "verification": "字段保留启发式核对" + ("（有疑似丢失）" if a["fields_dropped_in_render"] else "")}
                for a in audit_records]
    stats = {"target": args.to, "n_records": len(recs),
             "source_formats": fmt_counts, "entry_types": type_counts, "languages": lang_counts,
             "field_retention_rate": round(retention, 4),
             "n_missing_field_instances": len(not_provided_list),
             "n_copied_fills": len(copied_any), "online_status": online_status}
    for name, obj in (("change_log.json", change_log), ("evidence_map.json", evidence),
                      ("stats.json", stats)):
        with open(os.path.join(args.work, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    for name, obj in (("exceptions.json", exceptions),
                      ("manual_confirmations.json", manual_confirmations)):
        p = os.path.join(args.work, name)
        old = []
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    old = json.load(f)
            except Exception:
                old = []
        with open(p, "w", encoding="utf-8") as f:
            json.dump((old or []) + obj, f, ensure_ascii=False, indent=2)

    print(f"[convert_engine] {len(recs)} 条 -> {args.to}; 保留率 {retention:.1%}; "
          f"缺字段实例 {len(not_provided_list)}; 互补补齐 {len(copied_any)}; "
          f"online={online_status}")
    return 0

def a_line(audit_rec, final_lines):
    return final_lines.get(audit_rec["rid"], "（无输出行）")

if __name__ == "__main__":
    sys.exit(main())
