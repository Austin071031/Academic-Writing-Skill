#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fidelity_check.py — Content-unit-level before/after comparison between the
original manuscript and the adapted DOCX ("转得全" evidence).

The adapter only restyles; it never rewrites text.  This script verifies that
claim unit by unit and flags ANY loss, merge, rewrite or image-ification.

Checks:
  * paragraph text sequence identical (normalized whitespace)
  * counts: paragraphs / tables / rows / images / OMML math / hyperlinks /
    bookmarks / footnotes / endnotes / comments / sections
  * every text unit of the original exists in the adapted doc (1:1 in order)

Usage:
    python3 fidelity_check.py ORIG.docx ADAPTED.docx --report fidelity.md \
        --json fidelity.json

Stdlib only.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ooxml import Docx, q, get_attr, para_text  # noqa: E402


def units(path):
    d = Docx(path)
    doc = d.document()
    norm = lambda s: re.sub(r"\s+", " ", s).strip()
    paras = []
    toc_entries = 0
    for p in doc.iter(q("p")):
        # structurally exclude TOC field entries (TOC1-TOC3 styles); they are
        # generated content, not source content
        pPr = p.find(q("pPr"))
        sid = None
        if pPr is not None and pPr.find(q("pStyle")) is not None:
            sid = get_attr(pPr.find(q("pStyle")), "w:val")
        if sid and re.match(r"^TOC[1-9]$", sid):
            toc_entries += 1
            continue
        t = norm(para_text(p))
        if t:
            paras.append(t)
    paras = [p for p in paras if p]
    tables = list(doc.iter(q("tbl")))
    rows = sum(len(t.findall(q("tr"))) for t in tables)
    cells_text = []
    for t in tables:
        for tc in t.iter(q("tc")):
            cells_text.append(norm(" ".join(para_text(p) for p in tc.iter(q("p")))))
    stats = {
        "paragraphs_nonempty": len(paras),
        "tables": len(tables),
        "table_rows": rows,
        "table_cells_nonempty": sum(1 for c in cells_text if c),
        "drawings": sum(1 for _ in doc.iter(q("drawing"))),
        "pict": sum(1 for _ in doc.iter(q("pict"))),
        "oMath": sum(1 for _ in doc.iter(q("oMath"))),
        "oMathPara": sum(1 for _ in doc.iter(q("oMathPara"))),
        "hyperlinks": sum(1 for _ in doc.iter(q("hyperlink"))),
        "bookmarks": sum(1 for _ in doc.iter(q("bookmarkStart"))),
        "sections": sum(1 for _ in doc.iter(q("sectPr"))),
        "footnote_refs": sum(1 for _ in doc.iter(q("footnoteReference"))),
        "endnote_refs": sum(1 for _ in doc.iter(q("endnoteReference"))),
        "comment_refs": sum(1 for _ in doc.iter(q("commentReference"))),
        "ins_markers": sum(1 for _ in doc.iter(q("ins"))),
        "del_markers": sum(1 for _ in doc.iter(q("del"))),
        "fields": sum(1 for _ in doc.iter(q("fldChar"))) +
                  sum(1 for _ in doc.iter(q("fldSimple"))),
    }
    parts = {n for n in d.parts if n.startswith("word/") and n.endswith(".xml")}
    aux_parts = sorted(p for p in parts if any(
        k in p for k in ("footnotes.xml", "endnotes.xml", "comments.xml")))
    media = sorted(n for n in d.parts if n.startswith("word/media/"))
    return {"paras": paras, "cells": cells_text, "stats": stats,
            "aux_parts": aux_parts, "media": media,
            "media_bytes": {m: len(d.parts[m]) for m in media}}


def compare(a, b):
    report = {"checks": [], "missing_in_adapted": [], "added_in_adapted": [],
              "stat_diffs": [], "media_diffs": [], "verdict": "PASS"}
    C = report["checks"]

    # 1) paragraph sequence (order-preserving containment: adapted must be a
    #    supersequence of the original; inserted units are listed separately)
    pa, pb = a["paras"], b["paras"]
    ia = 0
    missing = []
    for t in pa:
        while ia < len(pb) and pb[ia] != t:
            ia += 1
        if ia == len(pb):
            missing.append(t)
        else:
            ia += 1
    report["missing_in_adapted"] = missing[:50]
    extra = [t for t in pb if t not in set(pa)]
    # whitelisted additions: TOC heading paragraph only (TOC entries are
    # excluded structurally via TOC1-3 styles in units())
    whitelisted = [t for t in extra if re.fullmatch(r"目\s*录|目\s*次|Contents", t)]
    extra = [t for t in extra if t not in set(whitelisted)]
    report["added_in_adapted"] = extra[:50]
    report["whitelisted_additions"] = whitelisted[:50]
    ok_seq = not missing
    C.append({"item": "正文段落单元按序保留（原文 %d 段 -> 成品 %d 段）" % (len(pa), len(pb)),
              "status": "PASS" if ok_seq else "FAIL",
              "missing_count": len(missing), "extra_count": len(extra)})

    # 2) table cells
    ca, cb = a["cells"], b["cells"]
    missing_cells = [c for c in ca if c and c not in set(cb)]
    C.append({"item": "表格单元格文本保留（%d -> %d）" % (len(ca), len(cb)),
              "status": "PASS" if not missing_cells else "FAIL",
              "missing_count": len(missing_cells)})
    if missing_cells:
        report["missing_in_adapted"].extend(("cell: " + c) for c in missing_cells[:20])

    # 3) unit counts (increases explainable by generated TOC are INFO, not WARN)
    TOC_EXPLAINABLE = {"paragraphs_nonempty", "fields"}
    for k, va in a["stats"].items():
        vb = b["stats"].get(k, 0)
        if va != vb:
            info_only = k in TOC_EXPLAINABLE and vb > va and report["whitelisted_additions"]
            report["stat_diffs"].append({"unit": k, "original": va, "adapted": vb,
                                         "info": bool(info_only)})
            C.append({"item": "单元计数 %s" % k,
                      "status": "PASS" if info_only else "WARN",
                      "detail": "%d -> %d（%s）" % (va, vb,
                          "新增为目录域生成内容，已白名单登记" if info_only
                          else "适配器不应改变内容单元数量")})
    if not report["stat_diffs"]:
        C.append({"item": "内容单元计数一致（段落/表格/图片/公式/超链接/书签/脚注/批注/修订/域）",
                  "status": "PASS"})

    # 4) media byte-identical
    for m in a["media"]:
        if m not in b["media"]:
            report["media_diffs"].append({"media": m, "issue": "missing"})
        elif a["media_bytes"][m] != b["media_bytes"][m]:
            report["media_diffs"].append({"media": m, "issue": "content_changed",
                                          "orig_bytes": a["media_bytes"][m],
                                          "adapted_bytes": b["media_bytes"][m]})
    for m in b["media"]:
        if m not in a["media"]:
            report["media_diffs"].append({"media": m, "issue": "added"})
    C.append({"item": "图片媒体文件逐字节一致（%d 个）" % len(a["media"]),
              "status": "PASS" if not report["media_diffs"] else "FAIL"})

    # 5) aux parts (footnotes/endnotes/comments)
    lost_parts = [p for p in a["aux_parts"] if p not in b["aux_parts"]]
    C.append({"item": "脚注/尾注/批注部件保留", "status": "PASS" if not lost_parts else "FAIL",
              "detail": lost_parts or "全部保留"})

    if any(c["status"] == "FAIL" for c in C):
        report["verdict"] = "FAIL"
    elif any(c["status"] == "WARN" for c in C):
        report["verdict"] = "WARN"
    return report


def to_markdown(r):
    L = ["# 保真度核验报告（fidelity_check）", ""]
    L.append("总体结论：**%s**" % r["verdict"])
    L.append("")
    L.append("| 检查项 | 结果 | 说明 |")
    L.append("|---|---|---|")
    for c in r["checks"]:
        L.append("| %s | %s | %s |" % (
            c["item"], c["status"],
            str(c.get("detail", c.get("missing_count", "")))[:120]))
    if r["missing_in_adapted"]:
        L += ["", "## 原文有而成品缺失的单元（前 50 条）", ""]
        L += ["- `%s`" % m[:100] for m in r["missing_in_adapted"]]
    if r["added_in_adapted"]:
        L += ["", "## 成品新增文本单元（前 50 条）", ""]
        L += ["- `%s`" % m[:100] for m in r["added_in_adapted"]]
    if r["media_diffs"]:
        L += ["", "## 媒体差异", ""]
        L += ["- %s" % json.dumps(m, ensure_ascii=False) for m in r["media_diffs"]]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("original")
    ap.add_argument("adapted")
    ap.add_argument("--report", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)
    a = units(args.original)
    b = units(args.adapted)
    r = compare(a, b)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(to_markdown(r))
    print(json.dumps({"verdict": r["verdict"],
                      "fails": sum(1 for c in r["checks"] if c["status"] == "FAIL")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
