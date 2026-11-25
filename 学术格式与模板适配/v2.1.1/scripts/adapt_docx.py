#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
adapt_docx.py — Apply a normalized `spec` (from extract_spec.py) to a manuscript
DOCX, structurally, not cosmetically:

  * page size / margins / columns          (sectPr)
  * bound styles: Normal / Heading1-4 / Caption / ReferenceList
    (styles.xml + numbering.xml abstract binding, so outline & TOC work)
  * heading numbering (decimal multilevel or 第X章 style)
  * body font / size / line-spacing normalization (runs that carry text)
  * three-line tables (三线表) with repeating header row
  * captions restyled (图x / 表x / Figure x), positions preserved
  * references section restyled (hanging indent, GB/T 7714-like numeric)
  * footer page number (PAGE field) when required or assumed
  * existing TOC fields, hyperlinks, bookmarks, revisions: left untouched

All edits are recorded in a change log JSON (unit-level, reviewable).

Usage:
    python3 adapt_docx.py MANUSCRIPT.docx --spec spec.json \
        --out /app/output/manuscript_adapted.docx --changelog changes.json

Stdlib only.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ooxml import (  # noqa: E402
    Docx, W, q, qn, get_attr, set_attr, get_child,
    make_el, set_run_fonts, set_run_size, set_bold, set_spacing, set_indent,
    set_outline_lvl, insert_in_order, sort_children_in_place, para_text,
    para_style_id, set_para_style, mm_to_twips, pt_to_half,
)

A4 = (11906, 16838)
LETTER = (12240, 15840)

H1_CN = re.compile(r"^\s*第[一二三四五六七八九十百千0-9]+章(\s|　|\.|、|$)")
H_NUM = re.compile(r"^\s*(\d+(?:\.\d+){0,4})\s*[、\.．\s]\s*(\S.*)?$")
FRONT_MATTER = re.compile(
    r"^\s*(摘\s*要|abstract|致谢|acknowledg|结论|conclusion|参考文献|references|"
    r"附录|appendix|目录|contents|引\s*言|introduction)\s*$", re.I)
CAPTION = re.compile(
    r"^\s*((?:图|表)\s*[\d一二三四五六七八九]+(?:[-.．—][\d]+)?|"
    r"(?:Figure|Fig\.?|Table)\s*\d+)[\s:：.．、)]*(.*)$", re.I)
REF_HEAD = re.compile(r"^\s*(参考文献|references)\s*$", re.I)
REF_ENTRY = re.compile(r"^\s*(\[\d+\]|\d+[\.、\)])\s*(\S.*)$")


def _ensure_styles(doc):
    """Ensure styles.xml exists."""
    doc.ensure_part("word/styles.xml", "styles", lambda: make_el("w:styles"))
    return doc.styles()


def _find_style(styles_root, style_id):
    for st in styles_root.findall(q("style")):
        if st.get(q("styleId")) == style_id:
            return st
    return None


def _new_style(styles_root, style_id, name, stype="paragraph", based_on=None):
    st = make_el("w:style", {"w:type": stype, "w:styleId": style_id})
    nm = make_el("w:name", {"w:val": name})
    insert_in_order(st, nm)
    if based_on:
        bo = make_el("w:basedOn", {"w:val": based_on})
        insert_in_order(st, bo)
    qf = make_el("w:qFormat")
    insert_in_order(st, qf)
    styles_root.append(st)
    return st


def _style_rpr(st):
    return get_child(st, "w:rPr")


def _style_ppr(st):
    return get_child(st, "w:pPr")


def _font_pair(spec, group="body"):
    body = spec.get("body", {}) or {}
    f = (body.get("fonts") or {})
    ascii_f = f.get("ascii") or "Times New Roman"
    ea_f = f.get("eastAsia") or "宋体"
    return ascii_f, ea_f


def build_styles(doc, spec, changes):
    styles_root = _ensure_styles(doc)
    ascii_f, ea_f = _font_pair(spec)
    body = spec.get("body", {}) or {}
    body_size = body.get("size_pt") or 12.0
    line = body.get("line_spacing")
    line_pt = body.get("line_spacing_pt")
    line_rule = body.get("line_rule") or ("atLeast" if line_pt else "auto")

    # --- Normal ---------------------------------------------------------------
    st = _find_style(styles_root, "Normal") or _new_style(styles_root, "Normal", "Normal")
    rPr = _style_rpr(st)
    set_run_fonts(rPr, ascii_f, ea_f)
    set_run_size(rPr, pt_to_half(body_size))
    set_bold(rPr, False)
    pPr = _style_ppr(st)
    if line:
        set_spacing(pPr, line=int(round(line * 240)), line_rule="auto")
    elif line_pt:
        set_spacing(pPr, line=pt_to_half(line_pt), line_rule=line_rule)
    if body.get("align"):
        jc = get_child(pPr, "w:jc")
        set_attr(jc, "w:val", body["align"])
    changes.append({"unit": "style:Normal",
                    "action": "bound",
                    "detail": {"ascii": ascii_f, "eastAsia": ea_f,
                               "size_pt": body_size, "line_spacing": line}})

    # --- headings ---------------------------------------------------------------
    heads = spec.get("headings", {}) or {}
    numbering = heads.get("numbering", "decimal_multilevel")
    hdefs = {
        1: dict(size=16.0, bold=True, align="center", before=13, after=13),
        2: dict(size=14.0, bold=True, align="left", before=13, after=6),
        3: dict(size=13.0, bold=True, align="left", before=6, after=6),
        4: dict(size=12.0, bold=True, align="left", before=6, after=6),
    }
    for lvl in (1, 2, 3, 4):
        hd = hdefs[lvl]
        ov = heads.get("h%d" % lvl) or {}
        size = ov.get("size_pt") or hd["size"]
        bold = ov.get("bold", hd["bold"])
        align = ov.get("align") or hd["align"]
        hfonts = ov.get("fonts") or {}
        h_ascii = hfonts.get("ascii") or ascii_f
        h_ea = hfonts.get("eastAsia") or ("黑体" if lvl <= 2 else ea_f)
        sid = "Heading%d" % lvl
        st = _find_style(styles_root, sid) or _new_style(
            styles_root, sid, "heading %d" % lvl, based_on="Normal")
        # keep built-in name so Word/LO map outline correctly
        nm = st.find(q("name"))
        if nm is None:
            nm = make_el("w:name", {"w:val": "heading %d" % lvl})
            insert_in_order(st, nm)
        else:
            set_attr(nm, "w:val", "heading %d" % lvl)
        rPr = _style_rpr(st)
        set_run_fonts(rPr, h_ascii, h_ea)
        set_run_size(rPr, pt_to_half(size))
        set_bold(rPr, bold)
        # academic headings are black, not themed blue; never italic
        col = get_child(rPr, "w:color")
        set_attr(col, "w:val", "auto")
        it = get_child(rPr, "w:i")
        set_attr(it, "w:val", 0)
        pPr = _style_ppr(st)
        get_child(pPr, "w:keepNext")
        set_spacing(pPr, before=hd["before"] * 20, after=hd["after"] * 20)
        jc = get_child(pPr, "w:jc")
        set_attr(jc, "w:val", align)
        set_outline_lvl(pPr, lvl - 1)
        changes.append({"unit": "style:%s" % sid, "action": "bound",
                        "detail": {"size_pt": size, "bold": bold, "align": align,
                                   "ascii": h_ascii, "eastAsia": h_ea}})

    # --- Caption -------------------------------------------------------------------
    cap = spec.get("captions", {}) or {}
    cap_size = cap.get("size_pt") or 10.5
    st = _find_style(styles_root, "Caption") or _new_style(
        styles_root, "Caption", "caption", based_on="Normal")
    rPr = _style_rpr(st)
    set_run_fonts(rPr, ascii_f, ea_f)
    set_run_size(rPr, pt_to_half(cap_size))
    set_bold(rPr, False)
    col = get_child(rPr, "w:color")
    set_attr(col, "w:val", "auto")
    it = get_child(rPr, "w:i")
    set_attr(it, "w:val", 0)
    pPr = _style_ppr(st)
    jc = get_child(pPr, "w:jc")
    set_attr(jc, "w:val", "center")
    set_spacing(pPr, before=60, after=120)
    changes.append({"unit": "style:Caption", "action": "bound",
                    "detail": {"size_pt": cap_size, "align": "center"}})

    # --- ReferenceList ---------------------------------------------------------------
    ref = spec.get("references", {}) or {}
    ref_size = ref.get("size_pt") or body_size
    st = _find_style(styles_root, "ReferenceList") or _new_style(
        styles_root, "ReferenceList", "Reference List", based_on="Normal")
    rPr = _style_rpr(st)
    set_run_fonts(rPr, ascii_f, ea_f)
    set_run_size(rPr, pt_to_half(ref_size))
    set_bold(rPr, False)
    pPr = _style_ppr(st)
    hang = 420
    set_indent(pPr, left=hang, hanging=hang)
    set_spacing(pPr, line=360, line_rule="auto")
    changes.append({"unit": "style:ReferenceList", "action": "bound",
                    "detail": {"size_pt": ref_size, "hanging_pt": hang / 20.0}})
    return numbering


def build_numbering(doc, spec, numbering, changes):
    if numbering == "none":
        return
    doc.ensure_part("word/numbering.xml", "numbering", lambda: make_el("w:numbering"))
    numroot = doc.numbering()
    existing_aids = {get_attr(an, "w:abstractNumId")
                     for an in numroot.findall(q("abstractNum"))}
    aid = "901"
    while aid in existing_aids:
        aid = str(int(aid) + 1)
    an = make_el("w:abstractNum", {"w:abstractNumId": aid})
    lvl_tmpls = {
        "decimal_multilevel": {0: "%1.", 1: "%1.%2", 2: "%1.%2.%3", 3: "%1.%2.%3.%4"},
        "chinese_chapter": {0: "第%1章", 1: "%1.%2", 2: "%1.%2.%3", 3: "%1.%2.%3.%4"},
    }
    tmpls = lvl_tmpls.get(numbering, lvl_tmpls["decimal_multilevel"])
    for lvl in range(4):
        lv = make_el("w:lvl", {"w:ilvl": str(lvl)})
        start = make_el("w:start", {"w:val": "1"})
        insert_in_order(lv, start)
        fmt = make_el("w:numFmt", {"w:val": "decimal"})
        insert_in_order(lv, fmt)
        txt = make_el("w:lvlText", {"w:val": tmpls[lvl]})
        insert_in_order(lv, txt)
        ps = make_el("w:pStyle", {"w:val": "Heading%d" % (lvl + 1)})
        insert_in_order(lv, ps)
        an.append(lv)
    numroot.insert(0, an)
    # concrete num
    nid = "901"
    existing = {get_attr(n, "w:numId") for n in numroot.findall(q("num"))}
    while nid in existing:
        nid = str(int(nid) + 1)
    num = make_el("w:num", {"w:numId": nid})
    ref = make_el("w:abstractNumId", {"w:val": aid})
    insert_in_order(num, ref)
    numroot.append(num)
    changes.append({"unit": "numbering:heading", "action": "bound",
                    "detail": {"pattern": numbering, "numId": nid}})
    return nid


def set_page(doc, spec, changes):
    pg = spec.get("page", {}) or {}
    body = doc.body()
    if body is None:
        return
    sect = body.find(q("sectPr"))
    if sect is None:
        sect = make_el("w:sectPr")
        insert_in_order(body, sect)
    paper = pg.get("paper")
    pgSz = get_child(sect, "w:pgSz")
    if paper == "Letter":
        set_attr(pgSz, "w:w", LETTER[0]); set_attr(pgSz, "w:h", LETTER[1])
    else:
        set_attr(pgSz, "w:w", A4[0]); set_attr(pgSz, "w:h", A4[1])
    set_attr(pgSz, "w:orient", pg.get("orient", "portrait"))
    pgMar = get_child(sect, "w:pgMar")
    for key, wname in (("margin_top_mm", "top"), ("margin_bottom_mm", "bottom"),
                       ("margin_left_mm", "left"), ("margin_right_mm", "right")):
        if pg.get(key) is not None:
            set_attr(pgMar, "w:" + wname, mm_to_twips(pg[key]))
    set_attr(pgMar, "w:header", mm_to_twips(pg.get("header_mm", 15)))
    set_attr(pgMar, "w:footer", mm_to_twips(pg.get("footer_mm", 17.5)))
    set_attr(pgMar, "w:gutter", 0)
    cols = get_child(sect, "w:cols")
    set_attr(cols, "w:num", int(pg.get("columns", 1)))
    set_attr(cols, "w:space", 720)
    changes.append({"unit": "sectPr:page", "action": "set",
                    "detail": {k: pg.get(k) for k in
                               ("paper", "margin_top_mm", "margin_bottom_mm",
                                "margin_left_mm", "margin_right_mm", "columns")
                               if pg.get(k) is not None}})


def classify(p, style_names):
    """Return (kind, level) for a paragraph: heading/caption/refentry/front/other."""
    sid = para_style_id(p)
    sname = (style_names.get(sid) or "").lower() if sid else ""
    if sid:
        mh = re.match(r"(?:heading|标题)\s*([1-9])", sname)
        if mh:
            return "heading", int(mh.group(1))
    if sid and sname in ("toc 1", "toc 2", "toc 3", "toc1", "toc2", "toc3"):
        return "toc", None
    if sid and "caption" in sname:
        return "caption", None
    # skip paragraphs containing fields (TOC etc.)
    text = para_text(p).strip()
    if not text:
        return "empty", None
    if p.find(q("pPr")) is not None and p.find(q("pPr")).find(q("sectPr")) is not None:
        return "other", None
    m = CAPTION.match(text)
    if m:
        return "caption", None
    if REF_HEAD.match(text):
        return "refhead", None
    if FRONT_MATTER.match(text):
        return "front", None
    if H1_CN.match(text):
        return "heading", 1
    m = H_NUM.match(text)
    if m and m.group(1):
        num, tail = m.group(1), (m.group(2) or "").strip()
        depth = num.count(".")
        # guards: headings are short and do not end with sentence punctuation;
        # a bare 4-digit year ("2020 年...") is not a heading; decimals with
        # unit-like tails ("5.0 GHz ...") are not headings
        if tail and depth <= 3 and len(text) <= 60 and \
                not text.rstrip().endswith(("。", ".", "，", ",", "；", ";")):
            if depth > 0 or len(num) <= 2:
                return "heading", min(depth + 1, 4)
    return "other", None


def body_paragraphs(doc):
    """Top-level block paragraphs (not inside tables/textboxes)."""
    body = doc.body()
    if body is None:
        return []
    out = []
    for child in body:
        if child.tag == q("p"):
            out.append(child)
        elif child.tag == q("sdt"):
            content = child.find(q("sdtContent"))
            if content is not None:
                out.extend(c for c in content if c.tag == q("p"))
    return out


def sid_name_map(styles_root):
    m = {}
    for st in styles_root.findall(q("style")):
        sid = st.get(q("styleId"))
        nm = st.find(q("name"))
        m[sid] = get_attr(nm, "w:val") if nm is not None else sid
    return m


def restyle_body(doc, spec, num_id, changes):
    """Bind paragraphs to styles + normalize run fonts on body text."""
    ascii_f, ea_f = _font_pair(spec)
    body_size = (spec.get("body", {}) or {}).get("size_pt") or 12.0
    styles_root = doc.styles()
    names_by_id = sid_name_map(styles_root) if styles_root is not None else {}

    # parent map to detect runs inside hyperlinks / fields / tracked changes
    root = doc.document()
    parent = {c: p for p in root.iter() for c in p}

    counts = {"heading": 0, "caption": 0, "refentry": 0, "front": 0, "normalized_runs": 0}
    in_refs = False
    for p in body_paragraphs(doc):
        kind, lvl = classify(p, names_by_id)
        if kind == "toc":
            continue
        if kind == "heading":
            in_refs = False
            sid = para_style_id(p)
            sname = (names_by_id.get(sid) or "").lower() if sid else ""
            if not re.match(r"heading\s*%d" % lvl, sname or ""):
                set_para_style(p, "Heading%d" % lvl)
                counts["heading"] += 1
                changes.append({"unit": "para:%s" % para_text(p)[:40],
                                "action": "style->Heading%d" % lvl})
            # if the heading TEXT already carries its own number (第X章 / 1.2),
            # suppress style numbering for this paragraph to avoid duplication
            txt = para_text(p).strip()
            if re.match(r"^(第[一二三四五六七八九十百千0-9]+章|\d+(?:\.\d+){0,3}\s*[\s、\.．])", txt):
                pPr = get_child(p, "w:pPr")
                numPr = get_child(pPr, "w:numPr")
                ilvl = get_child(numPr, "w:ilvl"); set_attr(ilvl, "w:val", 0)
                nid = get_child(numPr, "w:numId"); set_attr(nid, "w:val", 0)
                changes.append({"unit": "para:%s" % txt[:40],
                                "action": "suppress_autonum(embedded)"})
            continue
        if kind == "front":
            in_refs = (REF_HEAD.match(para_text(p).strip()) is not None)
            sid = para_style_id(p)
            sname = (names_by_id.get(sid) or "").lower() if sid else ""
            if not re.match(r"heading\s*1", sname or ""):
                set_para_style(p, "Heading1")
                # unnumbered front-matter heading: disable inherited numbering
                pPr = get_child(p, "w:pPr")
                numPr = get_child(pPr, "w:numPr")
                ilvl = get_child(numPr, "w:ilvl"); set_attr(ilvl, "w:val", 0)
                nid = get_child(numPr, "w:numId"); set_attr(nid, "w:val", 0)
                counts["front"] += 1
                changes.append({"unit": "para:%s" % para_text(p)[:40],
                                "action": "style->Heading1(unnumbered)"})
            continue
        if kind == "refhead":
            in_refs = True
            continue
        if kind == "caption":
            sid = para_style_id(p)
            sname = (names_by_id.get(sid) or "").lower() if sid else ""
            if "caption" not in (sname or ""):
                set_para_style(p, "Caption")
                counts["caption"] += 1
                changes.append({"unit": "para:%s" % para_text(p)[:40],
                                "action": "style->Caption"})
            continue
        if in_refs and kind == "other":
            m = REF_ENTRY.match(para_text(p).strip())
            if m:
                set_para_style(p, "ReferenceList")
                counts["refentry"] += 1
                continue
        # body paragraphs: normalize run-level fonts/sizes only where they
        # carry text; never touch runs inside hyperlinks, fields or revisions
        if kind == "other":
            # v2.1.1: direct w:line / w:lineRule overrides silently defeat the
            # style-bound line spacing at render time (Word/LO give direct
            # paragraph formatting precedence over the style).  Clear only the
            # line-spacing attributes — before/after spacing is intentional
            # and stays.  Paragraphs whose spacing is structural (own
            # numbering, section break, floating objects, math) are skipped.
            pPr = p.find(q("pPr"))
            sp = pPr.find(q("spacing")) if pPr is not None else None
            if sp is not None and (get_attr(sp, "w:line") is not None
                                   or get_attr(sp, "w:lineRule") is not None):
                guarded = pPr.find(q("numPr")) is not None or \
                    pPr.find(q("sectPr")) is not None
                if not guarded:
                    for t in ("drawing", "pict", "object", "oMath"):
                        if any(True for _ in p.iter(q(t))):
                            guarded = True
                            break
                if not guarded:
                    detail = {a: get_attr(sp, "w:" + a)
                              for a in ("line", "lineRule")
                              if get_attr(sp, "w:" + a) is not None}
                    for a in ("line", "lineRule"):
                        sp.attrib.pop(q(a), None)
                    if not sp.attrib:
                        pPr.remove(sp)
                    counts["spacing_overrides_cleared"] = \
                        counts.get("spacing_overrides_cleared", 0) + 1
                    changes.append({"unit": "para:%s" % para_text(p)[:40],
                                    "action": "clear_direct_line_spacing",
                                    "detail": detail})
            for r in p.findall(q("r")):
                if r.find(q("t")) is None:
                    continue
                anc, skip = parent.get(r), False
                while anc is not None:
                    if anc.tag in (q("hyperlink"), q("fldSimple")) or \
                            _local(anc.tag) in ("ins", "del"):
                        skip = True
                        break
                    anc = parent.get(anc)
                if skip:
                    continue
                rPr = r.find(q("rPr"))
                if rPr is None:
                    rPr = make_el("w:rPr")
                    r.insert(0, rPr)
                rF = rPr.find(q("rFonts"))
                cur_ascii = get_attr(rF, "w:ascii") if rF is not None else None
                sz = rPr.find(q("sz"))
                cur_sz = float(get_attr(sz, "w:val")) / 2.0 if sz is not None else None
                if cur_ascii != ascii_f or cur_sz != body_size:
                    set_run_fonts(rPr, ascii_f, ea_f)
                    set_run_size(rPr, pt_to_half(body_size))
                    counts["normalized_runs"] += 1
    changes.append({"unit": "body", "action": "restyle_summary", "detail": counts})
    return counts


def _local(tag):
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def three_line_tables(doc, spec, changes):
    tbl_spec = spec.get("tables", {}) or {}
    if not tbl_spec.get("three_line", True):
        return 0
    top_sz = int(round((tbl_spec.get("top_border_pt") or 1.5) * 8))
    bot_sz = int(round((tbl_spec.get("bottom_border_pt") or 1.5) * 8))
    hdr_sz = int(round((tbl_spec.get("header_border_pt") or 0.75) * 8))
    n = 0
    for tbl in doc.document().iter(q("tbl")):
        tblPr = tbl.find(q("tblPr"))
        if tblPr is None:
            tblPr = make_el("w:tblPr")
            tbl.insert(0, tblPr)
        borders = get_child(tblPr, "w:tblBorders")
        for side, sz in (("top", top_sz), ("bottom", bot_sz)):
            b = get_child(borders, "w:" + side)
            set_attr(b, "w:val", "single")
            set_attr(b, "w:sz", sz)
            set_attr(b, "w:space", 0)
            set_attr(b, "w:color", "000000")
        for side in ("left", "right", "insideH", "insideV"):
            b = get_child(borders, "w:" + side)
            set_attr(b, "w:val", "nil")
        jc = get_child(tblPr, "w:jc")
        set_attr(jc, "w:val", "center")
        rows = tbl.findall(q("tr"))
        if rows:
            # first row: bottom border 0.75pt + repeat header
            trPr = rows[0].find(q("trPr"))
            if trPr is None:
                trPr = make_el("w:trPr")
                rows[0].insert(0, trPr)
            get_child(trPr, "w:tblHeader")
            for tc in rows[0].findall(q("tc")):
                tcPr = tc.find(q("tcPr"))
                if tcPr is None:
                    tcPr = make_el("w:tcPr")
                    tc.insert(0, tcPr)
                tcb = get_child(tcPr, "w:tcBorders")
                b = get_child(tcb, "w:bottom")
                set_attr(b, "w:val", "single")
                set_attr(b, "w:sz", hdr_sz)
                set_attr(b, "w:space", 0)
                set_attr(b, "w:color", "000000")
            # other rows: no top border lines
            for tr in rows[1:]:
                for tc in tr.findall(q("tc")):
                    tcPr = tc.find(q("tcPr"))
                    if tcPr is None:
                        tcPr = make_el("w:tcPr")
                        tc.insert(0, tcPr)
                    tcb = get_child(tcPr, "w:tcBorders")
                    for side in ("top", "bottom", "left", "right"):
                        b = get_child(tcb, "w:" + side)
                        set_attr(b, "w:val", "nil")
        n += 1
    if n:
        changes.append({"unit": "tables", "action": "three_line_format", "count": n,
                        "detail": {"top_pt": top_sz / 8, "bottom_pt": bot_sz / 8,
                                   "header_pt": hdr_sz / 8}})
    return n


def add_footer_pagenum(doc, spec, changes):
    hf = spec.get("header_footer", {}) or {}
    if hf.get("page_number") is False:
        return False
    pos = hf.get("page_number_position", "footer")
    align = hf.get("page_number_align", "center")
    sect = doc.body().find(q("sectPr"))
    if sect is None:
        return False
    part_name = "word/%s1.xml" % pos
    rtype = ("http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
             + pos)
    ckey = pos
    if not doc.has_part(part_name):
        root = make_el("w:%s" % pos)
        p = make_el("w:p")
        pPr = make_el("w:pPr")
        jc = make_el("w:jc", {"w:val": align})
        insert_in_order(pPr, jc)
        insert_in_order(p, pPr)
        r1 = make_el("w:r"); f1 = make_el("w:fldChar", {"w:fldCharType": "begin"})
        r1.append(f1)
        r2 = make_el("w:r"); it = make_el("w:instrText", {"xml:space": "preserve"})
        it.text = " PAGE "
        r2.append(it)
        r3 = make_el("w:r"); f3 = make_el("w:fldChar", {"w:fldCharType": "separate"})
        r3.append(f3)
        r4 = make_el("w:r"); t4 = make_el("w:t"); t4.text = "1"
        r4.append(t4)
        r5 = make_el("w:r"); f5 = make_el("w:fldChar", {"w:fldCharType": "end"})
        r5.append(f5)
        for r in (r1, r2, r3, r4, r5):
            p.append(r)
        root.append(p)
        doc.set_xml(part_name, root, ckey)
    rid = doc.ensure_rel(part_name, rtype)
    ref_tag = "w:%sReference" % pos
    existing = sect.find(q(ref_tag))
    if existing is None:
        ref = make_el(ref_tag, {"w:type": "default", qn("r:id"): rid})
        insert_in_order(sect, ref)
    assumed = "page_number" not in hf or not hf.get("page_number")
    changes.append({"unit": "%s:page_number" % pos, "action": "added_field",
                    "assumption": assumed,
                    "detail": {"align": align, "field": "PAGE"}})
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("manuscript")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--changelog", default="changes.json")
    args = ap.parse_args(argv)

    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    doc = Docx(args.manuscript)
    changes = []

    set_page(doc, spec, changes)
    numbering = build_styles(doc, spec, changes)
    num_id = build_numbering(doc, spec, numbering, changes)
    restyle_body(doc, spec, num_id, changes)
    n_tbl = three_line_tables(doc, spec, changes)
    add_footer_pagenum(doc, spec, changes)

    sort_children_in_place(doc.document())
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    doc.save(args.out)
    with open(args.changelog, "w", encoding="utf-8") as f:
        json.dump(changes, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "out": args.out, "changes": len(changes),
                      "tables_formatted": n_tbl}, ensure_ascii=False))


if __name__ == "__main__":
    main()
