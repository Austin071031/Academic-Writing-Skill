#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compliance_check.py — Verify the adapted DOCX against every requirement in the
`spec` ("排得对" evidence).  Emits a per-item PASS/FAIL/SKIP checklist with the
*measured* values from the output file.

Usage:
    python3 compliance_check.py ADAPTED.docx --spec spec.json \
        --report compliance.md --json compliance.json

Stdlib only.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ooxml import (  # noqa: E402
    Docx, q, qn, get_attr, get_child, twips_to_mm, para_text, half_to_pt,
)

TOL_MM = 1.0
TOL_PT = 0.6


def _sz_pt(rPr):
    if rPr is None:
        return None
    sz = rPr.find(q("sz"))
    return float(get_attr(sz, "w:val")) / 2.0 if sz is not None else None


def _fonts(rPr):
    if rPr is None:
        return {}
    rF = rPr.find(q("rFonts"))
    if rF is None:
        return {}
    return {a: get_attr(rF, "w:" + a) for a in ("ascii", "eastAsia")}


def _line(pPr):
    if pPr is None:
        return None
    sp = pPr.find(q("spacing"))
    if sp is None:
        return None
    line = get_attr(sp, "w:line")
    rule = get_attr(sp, "w:lineRule", "auto")
    if line is None:
        return None
    if rule == "auto":
        return {"multiple": round(int(line) / 240.0, 3)}
    return {rule: int(line) / 20.0}


def _style(doc, sid):
    st = None
    for s in (doc.styles() or []).findall(q("style")):
        if s.get(q("styleId")) == sid:
            st = s
            break
    if st is None:
        return None
    return {
        "rPr": st.find(q("rPr")),
        "pPr": st.find(q("pPr")),
        "outline": (int(get_attr(st.find(q("pPr")).find(q("outlineLvl")), "w:val"))
                    if st.find(q("pPr")) is not None and
                    st.find(q("pPr")).find(q("outlineLvl")) is not None else None),
    }


def near(a, b, tol):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def check(doc_path, spec):
    doc = Docx(doc_path)
    checks = []

    def add(item, required, status, measured="", expected=""):
        checks.append({"item": item, "required": required, "status": status,
                       "measured": measured, "expected": expected})

    pg = spec.get("page", {}) or {}
    sect = None
    for el in doc.document().iter(q("sectPr")):
        sect = el
    if sect is None:
        add("文档可解析且存在节属性", True, "FAIL", "未找到 sectPr")
        return {"checks": checks, "summary": _summarize(checks)}

    # ---- page -----------------------------------------------------------------
    pgSz = sect.find(q("pgSz"))
    w_mm = twips_to_mm(get_attr(pgSz, "w:w")) if pgSz is not None else None
    h_mm = twips_to_mm(get_attr(pgSz, "w:h")) if pgSz is not None else None
    paper = pg.get("paper")
    if paper:
        exp = {"A4": (210.0, 297.0), "Letter": (215.9, 279.4)}.get(paper)
        ok = exp and near(w_mm, exp[0], TOL_MM) and near(h_mm, exp[1], TOL_MM)
        add("页面尺寸 %s" % paper, True, "PASS" if ok else "FAIL",
            "%sx%s mm" % (w_mm, h_mm), "%sx%s mm" % tuple(exp or ("?", "?")))
    else:
        add("页面尺寸", False, "SKIP", "%sx%s mm" % (w_mm, h_mm), "未指定")
    pgMar = sect.find(q("pgMar"))
    for key, wname, label in (("margin_top_mm", "top", "上边距"),
                              ("margin_bottom_mm", "bottom", "下边距"),
                              ("margin_left_mm", "left", "左边距"),
                              ("margin_right_mm", "right", "右边距")):
        expv = pg.get(key)
        mv = twips_to_mm(get_attr(pgMar, "w:" + wname)) if pgMar is not None else None
        if expv is not None:
            add(label, True, "PASS" if near(mv, expv, TOL_MM) else "FAIL",
                "%s mm" % mv, "%s mm" % expv)
        else:
            add(label, False, "SKIP", "%s mm" % mv, "未指定")
    cols = sect.find(q("cols"))
    ncol = int(get_attr(cols, "w:num", "1")) if cols is not None else 1
    expc = pg.get("columns")
    if expc:
        add("分栏数", True, "PASS" if ncol == int(expc) else "FAIL",
            "%d 栏" % ncol, "%s 栏" % expc)
    else:
        add("分栏数", False, "SKIP", "%d 栏" % ncol, "未指定")

    # ---- Normal ----------------------------------------------------------------
    body = spec.get("body", {}) or {}
    n = _style(doc, "Normal")
    if body.get("size_pt") and n:
        msz = _sz_pt(n["rPr"])
        add("正文字号", True, "PASS" if near(msz, body["size_pt"], TOL_PT) else "FAIL",
            "%s pt" % msz, "%s pt" % body["size_pt"])
    elif body.get("size_pt"):
        add("正文字号", True, "FAIL", "Normal 样式缺失")
    else:
        add("正文字号", False, "SKIP", str(_sz_pt(n["rPr"]) if n else "?"), "未指定")
    if (body.get("fonts") or {}).get("ascii") and n:
        mf = _fonts(n["rPr"]).get("ascii")
        expf = body["fonts"]["ascii"]
        add("正文西文字体", True, "PASS" if mf == expf else "FAIL", mf, expf)
    if (body.get("fonts") or {}).get("eastAsia") and n:
        mf = _fonts(n["rPr"]).get("eastAsia")
        expf = body["fonts"]["eastAsia"]
        add("正文中文字体", True, "PASS" if mf == expf else "FAIL", mf, expf)
    if body.get("line_spacing") and n:
        ml = _line(n["pPr"]) or {}
        mv = ml.get("multiple")
        add("正文行距（%s 倍）" % body["line_spacing"], True,
            "PASS" if near(mv, body["line_spacing"], 0.06) else "FAIL",
            str(mv), str(body["line_spacing"]))
    elif body.get("line_spacing_pt") and n:
        ml = _line(n["pPr"]) or {}
        mv = ml.get("exact") or ml.get("atLeast")
        add("正文行距（固定值）", True,
            "PASS" if near(mv, body["line_spacing_pt"], 1.0) else "FAIL",
            str(mv), str(body["line_spacing_pt"]))

    # ---- headings ----------------------------------------------------------------
    heads = spec.get("headings", {}) or {}
    for lvl in (1, 2, 3, 4):
        h = _style(doc, "Heading%d" % lvl)
        ov = heads.get("h%d" % lvl) or {}
        if h is None:
            if ov:
                add("标题 %d 样式绑定" % lvl, True, "FAIL", "样式缺失")
            continue
        add("标题 %d 大纲级别绑定" % lvl, True,
            "PASS" if h["outline"] == lvl - 1 else "FAIL",
            "outlineLvl=%s" % h["outline"], str(lvl - 1))
        if ov.get("size_pt"):
            msz = _sz_pt(h["rPr"])
            add("标题 %d 字号" % lvl, True,
                "PASS" if near(msz, ov["size_pt"], TOL_PT) else "FAIL",
                "%s pt" % msz, "%s pt" % ov["size_pt"])
        if ov.get("bold") is not None:
            b = h["rPr"].find(q("b")) if h["rPr"] is not None else None
            mv = b is not None and get_attr(b, "w:val", "1") not in ("0", "false")
            add("标题 %d 加粗" % lvl, True,
                "PASS" if mv == bool(ov["bold"]) else "FAIL", str(mv), str(ov["bold"]))
    # numbering binding
    numbering = doc.numbering()
    bound = False
    if numbering is not None:
        for an in numbering.findall(q("abstractNum")):
            for lv in an.findall(q("lvl")):
                ps = lv.find(q("pStyle"))
                if ps is not None and (get_attr(ps, "w:val") or "").startswith("Heading"):
                    bound = True
    add("标题编号与样式绑定（numbering.xml）", heads.get("numbering", "decimal_multilevel") != "none",
        "PASS" if bound else "FAIL", "已绑定" if bound else "未绑定")

    # ---- captions ----------------------------------------------------------------
    cap = spec.get("captions", {}) or {}
    c = _style(doc, "Caption")
    if cap.get("size_pt"):
        msz = _sz_pt(c["rPr"]) if c else None
        add("题注字号", True, "PASS" if near(msz, cap["size_pt"], TOL_PT) else "FAIL",
            "%s pt" % msz, "%s pt" % cap["size_pt"])
    # caption positions: 图题在下 / 表题在上 structural check
    if cap.get("figure_position") == "below" or cap.get("table_position") == "above":
        body_el = doc.body()
        seq = []
        for child in body_el:
            if child.tag == q("p"):
                txt = para_text(child).strip()
                sid = None
                pPr = child.find(q("pPr"))
                if pPr is not None and pPr.find(q("pStyle")) is not None:
                    sid = get_attr(pPr.find(q("pStyle")), "w:val")
                if re.match(r"^\s*图\s*\d+|^\s*(Figure|Fig\.?)\s*\d+", txt, re.I):
                    seq.append(("figcap", sid))
                elif re.match(r"^\s*表\s*\d+|^\s*Table\s*\d+", txt, re.I):
                    seq.append(("tabcap", sid))
                elif child.find(q("pPr")) is not None or txt:
                    seq.append(("other", sid))
            elif child.tag == q("tbl"):
                seq.append(("tbl", None))
        fig_bad = tab_bad = 0
        for i, (k, _) in enumerate(seq):
            if k == "figcap" and cap.get("figure_position") == "below":
                # figure caption should follow a figure/table? heuristic: previous
                # block should be an image-containing para or table
                pass
            if k == "tabcap" and cap.get("table_position") == "above":
                if i + 1 < len(seq) and seq[i + 1][0] != "tbl":
                    tab_bad += 1
        add("表题位于表上方（结构）", cap.get("table_position") == "above",
            "PASS" if tab_bad == 0 else "FAIL",
            "错位 %d 处" % tab_bad, "表题在表上方")

    # ---- tables: three-line --------------------------------------------------------
    tbl_spec = spec.get("tables", {}) or {}
    n_tbl = three = 0
    for tbl in doc.document().iter(q("tbl")):
        n_tbl += 1
        tblPr = tbl.find(q("tblPr"))
        if tblPr is None:
            continue
        borders = tblPr.find(q("tblBorders"))
        if borders is None:
            continue
        def _v(side):
            b = borders.find(q(side))
            if b is None:
                return None
            return (get_attr(b, "w:val"), get_attr(b, "w:sz"))
        top, bot = _v("top"), _v("bottom")
        inside = [_v("insideH"), _v("insideV")]
        hdr_ok = False
        rows = tbl.findall(q("tr"))
        if rows:
            trPr = rows[0].find(q("trPr"))
            hdr_ok = trPr is not None and trPr.find(q("tblHeader")) is not None
        if (top and top[0] == "single" and bot and bot[0] == "single"
                and all(i and i[0] == "nil" for i in inside) and hdr_ok):
            three += 1
    if n_tbl and tbl_spec.get("three_line", True):
        add("三线表格式（顶/底框线 + 表头重复 + 无竖线）", True,
            "PASS" if three == n_tbl else "WARN",
            "%d/%d 张符合" % (three, n_tbl), "全部 %d 张" % n_tbl)
    elif n_tbl:
        add("三线表格式", False, "SKIP", "%d 张表" % n_tbl, "未要求")
    else:
        add("三线表格式", False, "SKIP", "文档中无表格", "")

    # ---- references ------------------------------------------------------------------
    ref = spec.get("references", {}) or {}
    rl = _style(doc, "ReferenceList")
    if ref.get("style") or ref.get("hanging_indent"):
        add("参考文献样式（悬挂缩进）", True, "PASS" if rl else "FAIL",
            "ReferenceList 样式%s" % ("存在" if rl else "缺失"))
        if rl and ref.get("size_pt"):
            msz = _sz_pt(rl["rPr"])
            add("参考文献字号", True,
                "PASS" if near(msz, ref["size_pt"], TOL_PT) else "FAIL",
                "%s pt" % msz, "%s pt" % ref["size_pt"])
    else:
        add("参考文献样式", False, "SKIP", "", "未指定")

    # ---- header/footer page numbers ------------------------------------------------------
    hf = spec.get("header_footer", {}) or {}
    has_field = False
    for part in doc.parts:
        if re.match(r"word/(header|footer)\d+\.xml$", part):
            data = doc.parts[part]
            if b"PAGE" in data or b"fldChar" in data:
                has_field = True
    if hf.get("page_number"):
        add("页码（PAGE 域）", True, "PASS" if has_field else "FAIL",
            "已插入" if has_field else "缺失")
    else:
        add("页码（PAGE 域）", False, "SKIP",
            "已插入" if has_field else "未插入", "未指定")

    # ---- body run spot check --------------------------------------------------------------
    if body.get("size_pt"):
        ascii_f = (body.get("fonts") or {}).get("ascii")
        checked = ok_sz = ok_f = 0
        for p in doc.document().iter(q("p")):
            if checked >= 30:
                break
            # v2.1.0: the spot check verifies BODY text only — heading /
            # caption / reference / TOC runs legitimately differ from the
            # body size and must not be counted as violations
            pPr = p.find(q("pPr"))
            if pPr is not None and pPr.find(q("pStyle")) is not None:
                _sid = get_attr(pPr.find(q("pStyle")), "w:val") or ""
                if _sid.startswith("Heading") or _sid in ("Caption", "ReferenceList") \
                        or _sid.lower().startswith("toc"):
                    continue
            for r in p.findall(q("r")):
                if checked >= 30:
                    break
                if r.find(q("t")) is None or not (r.find(q("t")).text or "").strip():
                    continue
                rPr = r.find(q("rPr"))
                sz = _sz_pt(rPr)
                f = _fonts(rPr).get("ascii")
                if sz:
                    checked += 1
                    if near(sz, body["size_pt"], TOL_PT):
                        ok_sz += 1
                    if not ascii_f or f == ascii_f:
                        ok_f += 1
        if checked:
            add("正文 run 字号抽查（%d 个）" % checked, True,
                "PASS" if ok_sz == checked else "WARN",
                "%d/%d 合规" % (ok_sz, checked))
            if ascii_f:
                add("正文 run 西文字体抽查", True,
                    "PASS" if ok_f == checked else "WARN",
                    "%d/%d 合规" % (ok_f, checked), ascii_f)

    return {"checks": checks, "summary": _summarize(checks)}


def _summarize(checks):
    s = {"PASS": 0, "FAIL": 0, "WARN": 0, "SKIP": 0}
    for c in checks:
        s[c["status"]] = s.get(c["status"], 0) + 1
    return s


def to_markdown(result, spec_src=""):
    L = ["# 合规检查报告（compliance_check）", ""]
    if spec_src:
        L.append("核对依据：`%s`" % spec_src)
        L.append("")
    L.append("汇总：PASS %d / FAIL %d / WARN %d / SKIP %d" % tuple(
        result["summary"].get(k, 0) for k in ("PASS", "FAIL", "WARN", "SKIP")))
    L.append("")
    L.append("| 检查项 | 要求 | 结果 | 实测值 | 期望值 |")
    L.append("|---|---|---|---|---|")
    for c in result["checks"]:
        L.append("| %s | %s | %s | %s | %s |" % (
            c["item"], "必需" if c["required"] else "可选", c["status"],
            str(c.get("measured", ""))[:60], str(c.get("expected", ""))[:60]))
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("adapted")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--report", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    result = check(args.adapted, spec)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(to_markdown(result, args.spec))
    print(json.dumps(result["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
