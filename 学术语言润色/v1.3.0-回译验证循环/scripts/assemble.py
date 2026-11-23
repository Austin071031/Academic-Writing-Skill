#!/usr/bin/env python3
"""assemble.py — 组装最终产物：改后全文、双语对照、修改清单、审校报告、diff 预览、result.json。

用法: python3 assemble.py [--work-dir /app/work] [--output-dir /app/output] [--bilingual]

读取:
  /app/work/source_segments.json        源文本（extract_text.py）
  /app/work/polish_chunks/*.jsonl       Agent 逐句润色记录（每句一行）
  /app/work/term_table.csv              术语表（terminology.py build）
  /app/work/consistency_report.*        术语回扫（terminology.py check）
  /app/work/guard_report.*              守恒检查（guard_check.py）
  /app/work/resolutions.jsonl           Agent 对 critical 标记的处置（可选，每行
                                        {"flag_id","kind","action":"fixed|justified","note"}）
不改写任何句子内容；只做合并、计数与格式化。未记录的句子在产物中如实标注。
"""
import argparse, csv, glob, html, json, os, re, sys
from collections import Counter, OrderedDict

TYPE_LABELS = {
    "grammar": "语法", "syntax": "句法", "collocation": "搭配", "punctuation": "标点",
    "spelling": "拼写", "long-sentence": "长句切分", "terminology": "术语统一",
    "abbreviation": "缩写与首次出现", "register": "语域语气", "redundancy": "冗余精简",
    "logic": "逻辑连接", "clarity": "表达清晰度", "hedging": "限定强度",
    "formatting": "格式", "other": "其他",
}


def load_chunks(chunks_dir):
    entries = OrderedDict()
    for p in sorted(glob.glob(os.path.join(chunks_dir, "*.jsonl"))):
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("id"):
                    entries[e["id"]] = e
    return entries


def join_sentences(sents, lang):
    if lang == "zh":
        return "".join(sents)
    return " ".join(sents)


def esc(s):
    return html.escape(str(s), quote=False).replace("\n", "<br>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", default="/app/work")
    ap.add_argument("--output-dir", default="/app/output")
    ap.add_argument("--bilingual", action="store_true", help="生成逐句中英/原文-改文对照")
    args = ap.parse_args()
    wd, outdir = args.work_dir, args.output_dir
    os.makedirs(outdir, exist_ok=True)

    segs = json.load(open(os.path.join(wd, "source_segments.json"), encoding="utf-8"))
    chunks = load_chunks(os.path.join(wd, "polish_chunks"))

    polished_segments, polished_lines = [], []
    log_rows, unlogged = [], []
    for seg in segs:
        sents = seg.get("sentences") or []
        kind = seg.get("kind")
        if kind in ("math", "fence"):
            polished_lines.append(seg["text"])
            continue
        if kind == "heading" or not sents:
            # 标题不改写、不进修改清单（Agent 若确需改标题，可在 chunks 中记录并在此放开）
            if not sents:
                polished_lines.append(seg.get("text", ""))
            else:
                e = chunks.get(seg["id"])
                polished_lines.append(e.get("polished", sents[0]) if e else sents[0])
            continue
        out_sents = []
        for i, s in enumerate(sents, 1):
            sid = f"{seg['id']}-S{i}" if len(sents) > 1 else seg["id"]
            e = chunks.get(sid)
            if e is None and len(sents) == 1:
                e = chunks.get(seg["id"])
            if e is None:
                unlogged.append(sid)
                out_sents.append(s)
                log_rows.append({"id": sid, "original": s, "polished": s, "decision": "keep",
                                 "types": [], "reason": "（未记录：按原文保留，需人工确认）",
                                 "logged": False})
            else:
                out_sents.append(e.get("polished", s))
                log_rows.append({**{k: e.get(k) for k in
                                    ("id", "original", "polished", "decision", "types", "reason")},
                                 "logged": True})
        if kind in ("heading", "caption", "list", "table_row") and len(sents) == 1:
            polished_lines.append(out_sents[0])
        else:
            polished_lines.append(join_sentences(out_sents, seg.get("lang", "zh")))
        polished_segments.append({"id": seg["id"], "kind": kind, "doc": seg.get("doc"),
                                  "lang": seg.get("lang"), "sentences": out_sents})

    with open(os.path.join(wd, "polished_segments.json"), "w", encoding="utf-8") as f:
        json.dump(polished_segments, f, ensure_ascii=False, indent=1)

    # ---- polished_full.md ----
    polished_md = "\n\n".join(l for l in polished_lines if l.strip()) + "\n"
    with open(os.path.join(outdir, "polished_full.md"), "w", encoding="utf-8") as f:
        f.write(polished_md)

    # ---- change_log ----
    modified = [r for r in log_rows if r.get("decision") == "modify"]
    kept = [r for r in log_rows if r.get("decision") == "keep"]
    by_type = Counter(t for r in modified for t in (r.get("types") or ["other"]))
    with open(os.path.join(outdir, "change_log.jsonl"), "w", encoding="utf-8") as f:
        for r in log_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(outdir, "change_log.md"), "w", encoding="utf-8") as f:
        f.write("# 逐句修改清单（change log）\n\n")
        f.write(f"句子总数 {len(log_rows)}；修改 {len(modified)}；保留 {len(kept)}；"
                f"未记录 {len(unlogged)}（未记录句已按原文保留并列入人工确认）。\n\n")
        f.write("## 修改类型分布\n\n")
        for t, n in by_type.most_common():
            f.write(f"- {t}（{TYPE_LABELS.get(t, t)}）: {n} 处\n")
        f.write("\n## 逐句对照（仅列出 decision=modify 的句子）\n\n")
        f.write("| ID | 原文 | 改文 | 修改类型 | 理由 |\n|---|---|---|---|---|\n")
        for r in modified:
            types = ", ".join(f"{t}({TYPE_LABELS.get(t, t)})" for t in (r.get("types") or ["other"]))
            cells = [str(r.get("id", "")).replace("|", "\\|"),
                     str(r.get("original", "")).replace("|", "\\|").replace("\n", " "),
                     str(r.get("polished", "")).replace("|", "\\|").replace("\n", " "),
                     types, str(r.get("reason", "")).replace("|", "\\|")]
            f.write("| " + " | ".join(cells) + " |\n")
        if unlogged:
            f.write("\n## 未记录句子（按原文保留，建议人工过一遍）\n\n")
            for sid in unlogged[:100]:
                f.write(f"- {sid}\n")

    # ---- bilingual / sentence alignment ----
    if args.bilingual:
        with open(os.path.join(outdir, "sentence_alignment.md"), "w", encoding="utf-8") as f:
            f.write("# 原文—改文逐句对照（sentence alignment）\n\n")
            f.write("| ID | 原文 | 改文 | 类型 | 理由 |\n|---|---|---|---|---|\n")
            for r in log_rows:
                if not r.get("logged"):
                    continue
                types = ", ".join(r.get("types") or []) or "—"
                cells = [str(r.get("id", "")).replace("|", "\\|"),
                         str(r.get("original", "")).replace("|", "\\|").replace("\n", " "),
                         str(r.get("polished", "")).replace("|", "\\|").replace("\n", " "),
                         types, str(r.get("reason", "")).replace("|", "\\|")]
                f.write("| " + " | ".join(cells) + " |\n")

    # ---- terminology table copy ----
    tt_csv = os.path.join(wd, "term_table.csv")
    if os.path.exists(tt_csv):
        with open(tt_csv, encoding="utf-8") as f:
            rows = list(csv.reader(f))
        with open(os.path.join(outdir, "terminology_table.csv"), "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)
        with open(os.path.join(outdir, "terminology_table.md"), "w", encoding="utf-8") as f:
            f.write("# 术语表（terminology table）\n\n| " + " | ".join(rows[0]) + " |\n")
            f.write("|" + "---|" * len(rows[0]) + "\n")
            for r in rows[1:]:
                f.write("| " + " | ".join(c.replace("|", "\\|") for c in r) + " |\n")

    # ---- review report（术语回扫 + 守恒检查 + 处置记录） ----
    parts = ["# 审校报告（确定性检查 + 处置记录）\n"]
    for name in ("consistency_report.md", "guard_report.md", "claims_report.md"):
        p = os.path.join(wd, name)
        if os.path.exists(p):
            parts.append(open(p, encoding="utf-8").read())
    res_path = os.path.join(wd, "resolutions.jsonl")
    resolutions = []
    if os.path.exists(res_path):
        with open(res_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        resolutions.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    parts.append("\n## Agent 对标记的处置\n\n")
    if resolutions:
        parts.append("| 标记 | 类型 | 处置 | 说明 |\n|---|---|---|---|\n")
        for r in resolutions:
            parts.append(f"| {r.get('flag_id','')} | {r.get('kind','')} | {r.get('action','')} | "
                         f"{str(r.get('note','')).replace('|','\\|')} |\n")
    else:
        parts.append("（无处置记录：critical 标记为 0 时尚不需要；否则需在 resolutions.jsonl 中逐条记录）\n")
    with open(os.path.join(outdir, "review_report.md"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(parts))

    # ---- drift_report.md（回译验证报告：v1.3.0 特有产物） ----
    src_keys = {}
    for seg in segs:
        sents, keys = seg.get("sentences") or [], seg.get("keys") or []
        for i in range(1, len(sents) + 1):
            sid = f"{seg['id']}-S{i}" if len(sents) > 1 else seg["id"]
            if i - 1 < len(keys) and keys[i - 1]:
                src_keys[sid] = True
    with open(os.path.join(outdir, "drift_report.md"), "w", encoding="utf-8") as f:
        f.write("# 回译验证报告（drift report）\n\n")
        f.write("关键句（含数值/引用/限定词/否定/因果）modify 后的回译结论与主张矩阵。\n\n")
        f.write("| 句 ID | 决策 | 回译结论 | 主张矩阵（claims） |\n|---|---|---|---|\n")
        for r in log_rows:
            if r.get("id") in src_keys and r.get("decision") == "modify":
                reason = str(r.get("reason", ""))
                bt = "回译一致" if ("回译一致" in reason or "回译通过" in reason) else (
                    "回退保留原文" if "回退" in reason else "（未标注，见审校报告）")
                e = chunks.get(r["id"], {})
                claims = e.get("claims")
                cs = "；".join(f"{k}={v}" for k, v in claims.items()) if claims else "—"
                cs = cs.replace("|", "\\|")
                f.write(f"| {r['id']} | modify | {bt} | {cs} |\n")
        n_bt = sum(1 for r in log_rows if r.get("id") in src_keys
                   and r.get("decision") == "modify"
                   and ("回译一致" in str(r.get("reason", "")) or "回译通过" in str(r.get("reason", ""))))
        f.write(f"\n关键句 modify 回译通过 {n_bt} 句。\n")

    # ---- diff.html ----
    with open(os.path.join(outdir, "diff.html"), "w", encoding="utf-8") as f:
        f.write("<!doctype html><meta charset='utf-8'><title>原文-改文对照</title>\n"
                "<style>body{font-family:sans-serif;margin:2em}table{border-collapse:collapse;width:100%}"
                "td,th{border:1px solid #ccc;padding:4px;vertical-align:top;font-size:14px}"
                "td.del{color:#a00}td.ins{color:#060}tr.keep{opacity:.55}</style>\n"
                "<h1>原文—改文对照（逐句）</h1><table><tr><th>ID</th><th>原文</th><th>改文</th>"
                "<th>类型</th><th>理由</th></tr>\n")
        for r in log_rows:
            cls = "keep" if r.get("decision") == "keep" else ""
            types = ", ".join(r.get("types") or []) or "—"
            f.write(f"<tr class='{cls}'><td>{esc(r.get('id'))}</td><td class='del'>{esc(r.get('original'))}</td>"
                    f"<td class='ins'>{esc(r.get('polished'))}</td><td>{esc(types)}</td>"
                    f"<td>{esc(r.get('reason'))}</td></tr>\n")
        f.write("</table>\n")
    with open(os.path.join(outdir, "polished_full.html"), "w", encoding="utf-8") as f:
        body = "\n".join(f"<p>{esc(l).replace(chr(10),'<br>')}</p>" for l in polished_lines if l.strip())
        f.write(f"<!doctype html><meta charset='utf-8'><title>润色后全文</title>"
                f"<style>body{{font-family:serif;max-width:46em;margin:2em auto;line-height:1.7}}</style>{body}")

    # ---- result.json 更新 ----
    result_p = os.path.join(outdir, "result.json")
    brief = json.load(open(os.path.join(wd, "brief.json"), encoding="utf-8")) \
        if os.path.exists(os.path.join(wd, "brief.json")) else {}
    result = json.load(open(result_p, encoding="utf-8")) if os.path.exists(result_p) \
        else {"case_id": brief.get("case_id", "unknown"), "output_contract": {}}
    guard = json.load(open(os.path.join(wd, "claims_report.json"), encoding="utf-8")) \
        if os.path.exists(os.path.join(wd, "claims_report.json")) else {}
    resolved_keys = {(r.get("flag_id"), r.get("kind")) for r in resolutions}
    unresolved = [x for x in guard.get("flags", []) if x["level"] == "critical"
                  and (x.get("id"), x["kind"]) not in resolved_keys]

    artifacts = {
        "polished_full": "polished_full.md",
        "sentence_alignment": "sentence_alignment.md" if args.bilingual else None,
        "change_log_md": "change_log.md",
        "change_log_jsonl": "change_log.jsonl",
        "terminology_table_md": "terminology_table.md" if os.path.exists(tt_csv) else None,
        "terminology_table_csv": "terminology_table.csv" if os.path.exists(tt_csv) else None,
        "review_report": "review_report.md",
        "diff_preview": "diff.html",
        "polished_preview": "polished_full.html",
    }
    result.update({
        "case_id": result.get("case_id") or brief.get("case_id", "unknown"),
        "status": "in_progress",
        "artifacts": {k: v for k, v in artifacts.items() if v},
        "change_records": {
            "change_log_jsonl": "change_log.jsonl",
            "change_log_md": "change_log.md",
            "summary": {"sentences_total": len(log_rows), "modified": len(modified),
                        "kept": len(kept), "unlogged": len(unlogged),
                        "by_type": dict(by_type)},
        },
        "fact_preservation": {
            "claims_report": "review_report.md", "drift_report": "drift_report.md",
            "critical_unresolved": len(unresolved),
            "coverage_ratio": guard.get("coverage_ratio"),
        },
    })
    oc = result.setdefault("output_contract", {})
    if isinstance(oc, dict):
        # Agent 可在 /app/work/contract_map.json 中显式指定 {契约键: 产物文件名}，优先级最高
        cmap = {}
        cm_p = os.path.join(wd, "contract_map.json")
        if os.path.exists(cm_p):
            try:
                cmap = json.load(open(cm_p, encoding="utf-8"))
            except Exception:
                pass

        def tokens(s):
            return set(re.findall(r"[a-z0-9]+", str(s).lower()))

        ALIAS = {
            "polished_full.md": {"text", "manuscript", "fulltext", "revised", "final"},
            "sentence_alignment.md": {"bilingual", "parallel", "alignment", "sidebyside", "双语", "对照"},
            "change_log.md": {"changelog", "changes", "修改清单"},
            "terminology_table.md": {"terms", "glossary", "terminology", "术语表"},
            "review_report.md": {"review", "audit", "审校"},
        }
        art_tokens = {fname: tokens(fname) | tokens(art_key) | ALIAS.get(fname, set())
                      for art_key, fname in artifacts.items() if fname}
        for key in oc:
            fname = cmap.get(key)
            if fname and not os.path.exists(os.path.join(outdir, fname)):
                fname = None
            if fname is None:
                kt = tokens(key)
                best, best_score = None, 0.0
                for f, at in art_tokens.items():
                    if not kt & at:
                        continue
                    score = len(kt & at) / max(len(kt), 1)  # 契约键被产物名覆盖的比例
                    if score > best_score:
                        best, best_score = f, score
                fname = best if best_score >= 0.5 else None
            if fname:
                oc[key]["delivered"] = fname
                oc[key]["artifact_path"] = os.path.abspath(os.path.join(outdir, fname))
                oc[key].pop("null_reason", None)
    with open(result_p, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[assemble] sentences={len(log_rows)} modified={len(modified)} kept={len(kept)} "
          f"unlogged={len(unlogged)} critical_unresolved={len(unresolved)}")
    print(f"[assemble] artifacts -> {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
