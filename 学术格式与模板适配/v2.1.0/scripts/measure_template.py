#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
measure_template.py — Reverse-engineer a structured format checklist from a
template DOCX (投稿模板 / 学位论文模板).

Reads the template's styles.xml, numbering.xml and sectPr and emits a
machine-readable `spec` JSON plus a human-readable checklist.  This is the
"认得准" step: every value is *measured from the actual file*, not guessed.

Usage:
    python3 measure_template.py TEMPLATE.docx --out spec_template.json \
        --checklist checklist_template.md

Stdlib only.
"""
import argparse
import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from ooxml import (  # noqa: E402
    Docx, W, q, qn, get_attr, twips_to_mm, para_text, iter_paragraphs,
    para_style_id,
)

HEADING_NAME_RE = __import__("re").compile(r"heading\s*(\d)|标题\s*(\d+)", __import__("re").I)
CAPTION_HINTS = ("caption", "题注")
REF_HINTS = ("reference", "bibliography", "参考文献")


def _sz(rPr):
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
    return {a: get_attr(rF, "w:" + a) for a in ("ascii", "hAnsi", "eastAsia", "cs")}


def _spacing(pPr):
    if pPr is None:
        return {}
    sp = pPr.find(q("spacing"))
    if sp is None:
        return {}
    line = get_attr(sp, "w:line")
    rule = get_attr(sp, "w:lineRule")
    out = {}
    if line:
        if rule == "auto":
            out["line_spacing"] = round(int(line) / 240.0, 3)
            out["line_rule"] = "multiple"
        elif rule in ("exact", "atLeast"):
            out["line_spacing_pt"] = round(int(line) / 20.0, 2)
            out["line_rule"] = rule
    for k, wname in (("before_pt", "before"), ("after_pt", "after")):
        v = get_attr(sp, "w:" + wname)
        if v is not None:
            out[k] = round(int(v) / 20.0, 2)
    return out


def _indent(pPr):
    if pPr is None:
        return {}
    ind = pPr.find(q("ind"))
    if ind is None:
        return {}
    out = {}
    for k, wname in (("first_line_pt", "firstLine"), ("first_line_ch", "firstLineChars"),
                     ("left_pt", "left"), ("left_ch", "leftChars"), ("hanging_pt", "hanging")):
        v = get_attr(ind, "w:" + wname)
        if v is not None:
            out[k] = int(v)
    return out


def _bold(rPr):
    if rPr is None:
        return None
    b = rPr.find(q("b"))
    if b is None:
        return None
    v = get_attr(b, "w:val")
    return v not in ("0", "false", "off")


def _outline(pPr):
    if pPr is None:
        return None
    ol = pPr.find(q("outlineLvl"))
    return int(get_attr(ol, "w:val")) if ol is not None else None


def _numpr(pPr):
    if pPr is None:
        return None
    np = pPr.find(q("numPr"))
    if np is None:
        return None
    numId = np.find(q("numId"))
    return get_attr(numId, "w:val") if numId is not None else None


def measure(path):
    d = Docx(path)
    doc = d.document()
    styles_root = d.styles() or __import__("xml.etree.ElementTree").Element(q("styles"))

    spec = {"source": path, "measured_from": "template_docx",
            "page": {}, "styles": {}, "numbering": {}, "notes": []}

    # --- page setup from the last sectPr in body -----------------------------
    sect = None
    for el in doc.iter(q("sectPr")):
        sect = el
    if sect is None:
        body = d.body()
        if body is not None:
            sect = body.find(q("sectPr"))
    if sect is not None:
        pgSz = sect.find(q("pgSz"))
        if pgSz is not None:
            w = get_attr(pgSz, "w:w")
            h = get_attr(pgSz, "w:h")
            spec["page"]["width_mm"] = twips_to_mm(w)
            spec["page"]["height_mm"] = twips_to_mm(h)
            spec["page"]["orient"] = get_attr(pgSz, "w:orient", "portrait")
        pgMar = sect.find(q("pgMar"))
        if pgMar is not None:
            for k, wname in (("margin_top_mm", "top"), ("margin_bottom_mm", "bottom"),
                             ("margin_left_mm", "left"), ("margin_right_mm", "right"),
                             ("header_mm", "header"), ("footer_mm", "footer"),
                             ("gutter_mm", "gutter")):
                v = get_attr(pgMar, "w:" + wname)
                if v is not None:
                    spec["page"][k] = twips_to_mm(v)
        cols = sect.find(q("cols"))
        if cols is not None:
            spec["page"]["columns"] = int(get_attr(cols, "w:num", "1"))
        # doc grid / line pitch
        grid = sect.find(q("docGrid"))
        if grid is not None:
            spec["page"]["doc_grid"] = get_attr(grid, "w:type")

    # --- styles ---------------------------------------------------------------
    import re as _re
    for st in styles_root.findall(q("style")):
        sid = st.get(q("styleId"))
        stype = st.get(q("type"), "paragraph")
        name_el = st.find(q("name"))
        name = get_attr(name_el, "w:val") if name_el is not None else sid
        pPr = st.find(q("pPr"))
        rPr = st.find(q("rPr"))
        entry = {"name": name, "type": stype}
        f = _fonts(rPr)
        if f:
            entry["fonts"] = f
        sz = _sz(rPr)
        if sz:
            entry["size_pt"] = sz
        b = _bold(rPr)
        if b is not None:
            entry["bold"] = b
        sp = _spacing(pPr)
        if sp:
            entry.update(sp)
        ind = _indent(pPr)
        if ind:
            entry.update(ind)
        ol = _outline(pPr)
        if ol is not None:
            entry["outline_level"] = ol
        nid = _numpr(pPr)
        if nid is not None:
            entry["numId"] = nid
        nxt = st.find(q("next"))
        if nxt is not None:
            entry["next"] = get_attr(nxt, "w:val")
        # classify
        m = HEADING_NAME_RE.search(name or "")
        if stype == "paragraph":
            if m:
                lvl = int(m.group(1) or m.group(2))
                entry["role"] = "heading"
                entry["level"] = lvl
            elif any(h in (name or "").lower() for h in CAPTION_HINTS):
                entry["role"] = "caption"
            elif any(h in (name or "").lower() for h in REF_HINTS):
                entry["role"] = "reference"
            elif (name or "").lower() in ("normal", "正文", "body text", "body"):
                entry["role"] = "body"
        spec["styles"][sid] = entry

    # --- numbering -------------------------------------------------------------
    numbering = d.numbering()
    if numbering is not None:
        abstract = {}
        for an in numbering.findall(q("abstractNum")):
            aid = get_attr(an, "w:abstractNumId")
            levels = {}
            for lvl in an.findall(q("lvl")):
                ilvl = get_attr(lvl, "w:ilvl", "0")
                fmt = lvl.find(q("numFmt"))
                txt = lvl.find(q("lvlText"))
                pstyle = lvl.find(q("pStyle"))
                levels[int(ilvl)] = {
                    "numFmt": get_attr(fmt, "w:val") if fmt is not None else None,
                    "lvlText": get_attr(txt, "w:val") if txt is not None else None,
                    "pStyle": get_attr(pstyle, "w:val") if pstyle is not None else None,
                }
            abstract[aid] = levels
        spec["numbering"]["abstract"] = abstract

    # --- docDefaults -----------------------------------------------------------
    dd = styles_root.find(q("docDefaults"))
    if dd is not None:
        rpd = dd.find(q("rPrDefault"))
        if rpd is not None:
            rprd = rpd.find(q("rPr"))
            f = _fonts(rprd)
            sz = _sz(rprd)
            defaults = {}
            if f:
                defaults["fonts"] = f
            if sz:
                defaults["size_pt"] = sz
            if defaults:
                spec["defaults"] = defaults

    # --- document body census (counts, not content) ----------------------------
    n_par = n_tbl = n_img = n_math = 0
    for p in iter_paragraphs(doc):
        n_par += 1
    for _ in doc.iter(q("tbl")):
        n_tbl += 1
    for _ in doc.iter(q("drawing")):
        n_img += 1
    for _ in doc.iter(q("oMath")):
        n_math += 1
    spec["template_census"] = {"paragraphs": n_par, "tables": n_tbl,
                               "drawings": n_img, "oMath": n_math}
    return spec


def to_checklist(spec):
    """Render a human checklist of measured requirements."""
    L = []
    L.append("# 模板检查项清单（由模板文件实测提取）")
    L.append("")
    L.append("来源：`%s`（measure_template.py 实测，非经验猜测）" % spec.get("source"))
    L.append("")
    pg = spec.get("page", {})
    L.append("## 页面设置")
    for k in ("width_mm", "height_mm", "orient", "margin_top_mm", "margin_bottom_mm",
              "margin_left_mm", "margin_right_mm", "header_mm", "footer_mm",
              "columns", "doc_grid"):
        if k in pg:
            L.append("- [ ] %s = %s" % (k, pg[k]))
    L.append("")
    L.append("## 样式（角色 / 字体 / 字号 / 行距 / 大纲级别）")
    for sid, e in sorted(spec.get("styles", {}).items()):
        if e.get("type") != "paragraph":
            continue
        bits = []
        if e.get("role"):
            bits.append("role=%s" % e["role"])
        if e.get("level") is not None:
            bits.append("level=%s" % e["level"])
        f = e.get("fonts") or {}
        if f.get("ascii"):
            bits.append("ascii=%s" % f["ascii"])
        if f.get("eastAsia"):
            bits.append("eastAsia=%s" % f["eastAsia"])
        if e.get("size_pt"):
            bits.append("size=%spt" % e["size_pt"])
        if e.get("line_spacing"):
            bits.append("line=%sx" % e["line_spacing"])
        if e.get("outline_level") is not None:
            bits.append("outline=%s" % e["outline_level"])
        if e.get("numId"):
            bits.append("numId=%s" % e["numId"])
        L.append("- [ ] `%s`（%s）：%s" % (sid, e.get("name"), "；".join(bits)))
    if spec.get("defaults"):
        L.append("")
        L.append("## 文档默认")
        L.append("- [ ] defaults = %s" % json.dumps(spec["defaults"], ensure_ascii=False))
    L.append("")
    L.append("## 说明")
    L.append("- 清单中所有数值均由模板文件实测；与任务书文本要求冲突时，以任务书为"
             "准并在 spec 的 `conflicts` 中登记。")
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("template")
    ap.add_argument("--out", default="spec_template.json")
    ap.add_argument("--checklist", default=None)
    args = ap.parse_args(argv)
    spec = measure(args.template)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=2)
    if args.checklist:
        with open(args.checklist, "w", encoding="utf-8") as f:
            f.write(to_checklist(spec))
    print(json.dumps({"ok": True, "spec": args.out,
                      "styles": len(spec.get("styles", {})),
                      "page": spec.get("page", {})}, ensure_ascii=False))


if __name__ == "__main__":
    main()
