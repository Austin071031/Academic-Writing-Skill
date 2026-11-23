#!/usr/bin/env python3
"""annotate.py — 编辑批注制产物组装（v1.5.0 核心）：批注式手稿、编辑卡、验收清单、result.json。

用法: python3 annotate.py [--work-dir /app/work] [--output-dir /app/output]

读取 /app/work/edit_records/*.jsonl（每句一条编辑记录）:
  {"id","original","action":"apply|confirm|keep","diagnosis":"…","prescription":"…",
   "reason":"…","types":["grammar"],"confidence":"high|medium|low","note":"…"}
  action=apply   有把握，直接改（改文=prescription）
  action=confirm 拿不准，保留原文并开人工确认卡（改文=original）
  action=keep    原文保留（附保留依据）

产物（/app/output）:
  annotated_manuscript.md   批注式手稿：行内 [E#] 锚点 + ~~原文~~ → **改文**（apply 时）
  edit_cards.md/.jsonl      每张编辑卡：诊断→处方→理由→置信度→人工确认项
  polished_full.md          采纳版全文（apply 生效，confirm/keep 保持原文）
  acceptance_checklist.md   作者验收清单（confirm 卡逐条 + 验收勾选项）
  change_log.jsonl          与姊妹版兼容的逐句记录
  result.json               契约字段闭环
"""
import argparse, datetime, glob, html, json, os, re, sys
from collections import Counter, OrderedDict

VALID_TYPES = {"grammar", "syntax", "collocation", "punctuation", "spelling", "long-sentence",
               "terminology", "abbreviation", "register", "redundancy", "logic", "clarity",
               "hedging", "formatting", "other"}
TYPE_ZH = {"grammar": "语法", "syntax": "句法", "collocation": "搭配", "punctuation": "标点",
           "spelling": "拼写", "long-sentence": "长句切分", "terminology": "术语统一",
           "abbreviation": "缩写首现", "register": "语域语气", "redundancy": "冗余精简",
           "logic": "逻辑连接", "clarity": "表达清晰度", "hedging": "限定强度",
           "formatting": "格式", "other": "其他"}


def esc(s):
    return html.escape(str(s), quote=False).replace("\n", "<br>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", default="/app/work")
    ap.add_argument("--output-dir", default="/app/output")
    args = ap.parse_args()
    wd, outdir = args.work_dir, args.output_dir
    os.makedirs(outdir, exist_ok=True)

    segs = json.load(open(os.path.join(wd, "source_segments.json"), encoding="utf-8"))
    records = OrderedDict()
    problems = []
    for p in sorted(glob.glob(os.path.join(wd, "edit_records", "*.jsonl"))):
        for ln, line in enumerate(open(p, encoding="utf-8"), 1):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                problems.append(f"{os.path.basename(p)}:{ln} 非法 JSON")
                continue
            if e.get("id"):
                records[e["id"]] = e
            else:
                problems.append(f"{os.path.basename(p)}:{ln} 缺 id")

    annotated, polished_lines, cards, log_rows, confirm_items = [], [], [], [], []
    polished_segments = []
    e_no = 0
    for seg in segs:
        sents = seg.get("sentences") or []
        kind = seg.get("kind")
        if kind in ("math", "fence"):
            annotated.append(seg["text"])
            polished_lines.append(seg["text"])
            polished_segments.append(seg)
            continue
        if kind == "heading" or not sents:
            annotated.append(seg.get("text", ""))
            polished_lines.append(seg.get("text", ""))
            continue
        out_sents, ann_sents = [], []
        for i, s in enumerate(sents, 1):
            sid = f"{seg['id']}-S{i}" if len(sents) > 1 else seg["id"]
            e = records.get(sid)
            if e is None:
                out_sents.append(s)
                ann_sents.append(s)
                log_rows.append({"id": sid, "original": s, "polished": s, "decision": "keep",
                                 "types": [], "reason": "（未记录：按原文保留，需人工确认）",
                                 "logged": False})
                confirm_items.append({"id": sid, "issue": "无编辑记录，按原文保留，建议作者通读确认"})
                continue
            action = e.get("action", "keep")
            pres = e.get("prescription", s)
            if action == "apply":
                e_no += 1
                out_sents.append(pres)
                ann_sents.append(f"[E{e_no}]~~{s}~~ → **{pres}**[/E{e_no}]")
                cards.append({"no": e_no, "id": sid, "action": "apply", "original": s,
                              "prescription": pres, "diagnosis": e.get("diagnosis", ""),
                              "reason": e.get("reason", ""), "types": e.get("types") or [],
                              "confidence": e.get("confidence", "medium"),
                              "note": e.get("note", "")})
                log_rows.append({"id": sid, "original": s, "polished": pres,
                                 "decision": "modify", "types": e.get("types") or [],
                                 "reason": e.get("reason", ""), "logged": True})
            elif action == "confirm":
                e_no += 1
                out_sents.append(s)
                ann_sents.append(f"[E{e_no}]{s}[/E{e_no}]〔待确认：{e.get('diagnosis','')}〕")
                cards.append({"no": e_no, "id": sid, "action": "confirm", "original": s,
                              "prescription": pres, "diagnosis": e.get("diagnosis", ""),
                              "reason": e.get("reason", ""), "types": e.get("types") or [],
                              "confidence": e.get("confidence", "low"),
                              "note": e.get("note", "")})
                confirm_items.append({"id": sid, "issue": e.get("diagnosis", ""),
                                      "suggestion": pres, "reason": e.get("reason", "")})
                log_rows.append({"id": sid, "original": s, "polished": s,
                                 "decision": "keep", "types": e.get("types") or [],
                                 "reason": f"存疑：{e.get('reason','')}", "logged": True})
            else:
                out_sents.append(s)
                ann_sents.append(s)
                log_rows.append({"id": sid, "original": s, "polished": s,
                                 "decision": "keep", "types": e.get("types") or [],
                                 "reason": e.get("reason", ""), "logged": True})
        joiner = "" if seg.get("lang", "zh") == "zh" else " "
        polished_lines.append(joiner.join(out_sents))
        annotated.append(joiner.join(ann_sents))
        polished_segments.append({"id": seg["id"], "kind": kind, "doc": seg.get("doc"),
                                  "lang": seg.get("lang"), "sentences": out_sents})

    json.dump(polished_segments, open(os.path.join(wd, "polished_segments.json"), "w",
                                      encoding="utf-8"), ensure_ascii=False, indent=1)

    # 产物 1：批注式手稿
    with open(os.path.join(outdir, "annotated_manuscript.md"), "w", encoding="utf-8") as f:
        f.write("# 批注式手稿（annotated manuscript）\n\n")
        f.write("标记约定：`[E#]~~原文~~ → **改文**[/E#]` 为已采纳修改；"
                "`[E#]原文[/E#]〔待确认：…〕` 为需作者裁决处。\n\n")
        f.write("\n\n".join(x for x in annotated if x.strip()) + "\n")

    # 产物 2：采纳版全文
    with open(os.path.join(outdir, "polished_full.md"), "w", encoding="utf-8") as f:
        f.write("\n\n".join(x for x in polished_lines if x.strip()) + "\n")

    # 产物 3：编辑卡
    with open(os.path.join(outdir, "edit_cards.jsonl"), "w", encoding="utf-8") as f:
        for c in cards:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(os.path.join(outdir, "edit_cards.md"), "w", encoding="utf-8") as f:
        f.write("# 编辑卡（edit cards）：诊断 → 处方 → 理由 → 置信度\n\n")
        for c in cards:
            types = ", ".join(f"{t}({TYPE_ZH.get(t,t)})" for t in c["types"]) or "—"
            f.write(f"## [E{c['no']}] {c['id']} ｜ {c['action']} ｜ 置信度 {c['confidence']}\n\n")
            f.write(f"- 诊断：{c['diagnosis']}\n- 原文：{c['original']}\n- 处方：{c['prescription']}\n"
                    f"- 理由：{c['reason']}\n- 类型：{types}\n")
            if c["note"]:
                f.write(f"- 备注：{c['note']}\n")
            f.write("\n")

    # 产物 4：作者验收清单
    with open(os.path.join(outdir, "acceptance_checklist.md"), "w", encoding="utf-8") as f:
        f.write("# 作者验收清单（acceptance checklist）\n\n")
        f.write(f"编辑卡 {len(cards)} 张：apply {sum(1 for c in cards if c['action']=='apply')}、"
                f"confirm {sum(1 for c in cards if c['action']=='confirm')}。\n\n")
        f.write("## 需作者裁决（confirm 卡与未记录句）\n\n")
        for it in confirm_items:
            f.write(f"- [ ] `{it['id']}` {it['issue']}")
            if it.get("suggestion"):
                f.write(f"；建议：{it['suggestion']}（理由：{it.get('reason','')}）")
            f.write("\n")
        if not confirm_items:
            f.write("- 无待裁决项。\n")
        f.write("\n## 通用验收勾选\n\n"
                "- [ ] 数值、单位、统计量与原文一致\n- [ ] 引用编号与图表指向一致\n"
                "- [ ] 限定强度（可能/有望/约）未被改动\n- [ ] 术语全篇统一\n"
                "- [ ] 语域符合目标文体\n")

    # 产物 5：change_log + diff.html（与姊妹版兼容）
    with open(os.path.join(outdir, "change_log.jsonl"), "w", encoding="utf-8") as f:
        for r in log_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    modified = [r for r in log_rows if r["decision"] == "modify"]
    by_type = Counter(t for r in modified for t in (r.get("types") or ["other"]))
    with open(os.path.join(outdir, "change_log.md"), "w", encoding="utf-8") as f:
        f.write("# 逐句修改清单\n\n")
        f.write(f"句子总数 {len(log_rows)}；采纳修改 {len(modified)}；待确认 {len(confirm_items)}。\n\n")
        for t, n in by_type.most_common():
            f.write(f"- {t}（{TYPE_ZH.get(t,t)}）: {n} 处\n")
    with open(os.path.join(outdir, "diff.html"), "w", encoding="utf-8") as f:
        f.write("<!doctype html><meta charset='utf-8'><style>body{font-family:sans-serif;margin:2em}"
                "table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:4px;"
                "font-size:14px;vertical-align:top}td.del{color:#a00}td.ins{color:#060}</style>"
                "<h1>原文—改文对照</h1><table><tr><th>ID</th><th>原文</th><th>改文</th><th>类型</th>"
                "<th>理由</th></tr>\n")
        for r in log_rows:
            types = ", ".join(r.get("types") or []) or "—"
            f.write(f"<tr><td>{esc(r['id'])}</td><td class='del'>{esc(r['original'])}</td>"
                    f"<td class='ins'>{esc(r['polished'])}</td><td>{esc(types)}</td>"
                    f"<td>{esc(r.get('reason',''))}</td></tr>\n")
        f.write("</table>")

    # 产物 6：result.json 闭环
    rp = os.path.join(outdir, "result.json")
    brief = json.load(open(os.path.join(wd, "brief.json"), encoding="utf-8")) \
        if os.path.exists(os.path.join(wd, "brief.json")) else {}
    result = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else \
        {"case_id": brief.get("case_id", "unknown"), "output_contract": {}}
    artifacts = {"annotated_manuscript": "annotated_manuscript.md",
                 "polished_full": "polished_full.md", "edit_cards_md": "edit_cards.md",
                 "edit_cards_jsonl": "edit_cards.jsonl",
                 "acceptance_checklist": "acceptance_checklist.md",
                 "change_log_md": "change_log.md", "change_log_jsonl": "change_log.jsonl",
                 "diff_preview": "diff.html"}

    def tokens(s):
        return set(re.findall(r"[a-z0-9]+", str(s).lower()))

    ALIAS = {"annotated_manuscript.md": {"annotated", "manuscript", "批注"},
             "polished_full.md": {"polished", "text", "fulltext", "revised"},
             "edit_cards.md": {"cards", "edit", "编辑卡"},
             "acceptance_checklist.md": {"acceptance", "checklist", "验收", "review"},
             "change_log.md": {"changelog", "changes", "log"},
             "edit_cards.jsonl": {"cards", "edit"}}
    art_tokens = {fname: tokens(fname) | tokens(ak) | ALIAS.get(fname, set())
                  for ak, fname in artifacts.items()}
    oc = result.setdefault("output_contract", {})
    if isinstance(oc, dict):
        for key in oc:
            kt = tokens(key)
            best, bs = None, 0.0
            for fname, at in art_tokens.items():
                if not kt & at:
                    continue
                sc = len(kt & at) / max(len(kt), 1)
                if sc > bs:
                    best, bs = fname, sc
            if best and bs >= 0.5:
                oc[key]["delivered"] = best
                oc[key]["artifact_path"] = os.path.abspath(os.path.join(outdir, best))
                oc[key].pop("null_reason", None)
    result.update({
        "case_id": result.get("case_id") or brief.get("case_id", "unknown"),
        "status": "in_progress",
        "artifacts": artifacts,
        "change_records": {"change_log_jsonl": "change_log.jsonl",
                           "summary": {"sentences_total": len(log_rows),
                                       "applied": sum(1 for c in cards if c["action"] == "apply"),
                                       "confirm": sum(1 for c in cards if c["action"] == "confirm"),
                                       "kept": sum(1 for r in log_rows if r["decision"] == "keep"),
                                       "by_type": dict(by_type)}},
        "manual_review_required": confirm_items,
    })
    json.dump(result, open(rp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    n_apply = sum(1 for c in cards if c["action"] == "apply")
    n_conf = sum(1 for c in cards if c["action"] == "confirm")
    print(f"[annotate] sentences={len(log_rows)} apply={n_apply} confirm={n_conf} "
          f"problems={len(problems)}")
    for p in problems:
        print("  PROBLEM:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
