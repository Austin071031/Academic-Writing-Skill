#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_preview.py — Export verification ("交得出"):

  render    DOCX -> PDF via LibreOffice (headless), then measure the *actual*
            page size (pdfinfo), check font embedding (pdffonts) and render
            PNG previews of the first pages (pdftoppm).
  toc-insert  Insert a real TOC field (Word F9-refreshable) into the DOCX at
              the correct structural position, with placeholder cached entries.
  toc-fill    Two-pass TOC refresh: locate every Heading1-3 in the rendered
              PDF (pdftotext per page), rewrite the TOC field's cached
              entries with real page numbers, keeping begin/separate/end so
              Word can still refresh with F9.

Usage:
    python3 render_preview.py render in.docx --outdir /app/output [--pages 6]
    python3 render_preview.py toc-insert in.docx [--spec spec.json]
    python3 render_preview.py toc-fill in.docx in.pdf

Stdlib only (LibreOffice + poppler must be on PATH; both degrade honestly).
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ooxml import (  # noqa: E402
    Docx, q, qn, get_attr, get_child, make_el, insert_in_order,
    para_text, para_style_id, mm_to_twips,
)

HAVE_LO = None
HAVE_POPPLER = None


def _which(cmd):
    from shutil import which
    return which(cmd)


def check_env():
    global HAVE_LO, HAVE_POPPLER
    HAVE_LO = bool(_which("libreoffice") or _which("soffice"))
    HAVE_POPPLER = bool(_which("pdftotext") and _which("pdftoppm") and _which("pdfinfo"))
    return {"libreoffice": HAVE_LO, "poppler": HAVE_POPPLER}


def soffice():
    return _which("libreoffice") or _which("soffice")


def render_pdf(docx_path, outdir):
    os.makedirs(outdir, exist_ok=True)
    pdf = os.path.join(outdir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
    if os.path.exists(pdf):
        os.remove(pdf)
    if not HAVE_LO:
        return None, "libreoffice 不可用，无法渲染 PDF 预览"
    # dedicated user profile: survives read-only HOME / concurrent harness runs
    profile = "/tmp/lo_profile_%d" % os.getpid()
    r = subprocess.run(
        [soffice(), "--headless", "--norestore",
         "-env:UserInstallation=file://%s" % profile,
         "--convert-to", "pdf", "--outdir", outdir, docx_path],
        capture_output=True, timeout=300)
    if not os.path.exists(pdf):
        return None, "LibreOffice 转换失败: %s" % (r.stderr or r.stdout).decode("utf-8", "replace")[:300]
    return pdf, None


def pdf_page_size(pdf):
    try:
        out = subprocess.run(["pdfinfo", pdf], capture_output=True, timeout=60)
        txt = out.stdout.decode("utf-8", "replace")
        m = re.search(r"Page size:\s*([\d.]+)\s*x\s*([\d.]+)\s*pts", txt)
        if not m:
            return None
        w = float(m.group(1)) * 25.4 / 72.0
        h = float(m.group(2)) * 25.4 / 72.0
        pages = re.search(r"Pages:\s*(\d+)", txt)
        return {"width_mm": round(w, 2), "height_mm": round(h, 2),
                "pages": int(pages.group(1)) if pages else None}
    except Exception as e:  # noqa: BLE001
        return None


def pdf_fonts(pdf):
    try:
        out = subprocess.run(["pdffonts", pdf], capture_output=True, timeout=60)
        lines = out.stdout.decode("utf-8", "replace").splitlines()
        fonts = []
        for ln in lines[2:]:
            parts = ln.split()
            # v2.1.2: pdffonts columns are "name type encoding emb sub uni
            # object ID", and type/encoding may themselves contain spaces
            # ("Type 1", "CID Type 0", "Identity-H").  Left-indexing the row
            # therefore misreads "Builtin"/"0" as the emb flag and reports
            # embedded CID fonts as NOT embedded.  The yes/no flags are the
            # three tokens immediately before the object-ID pair, so parse
            # them from the RIGHT side of the row.
            if len(parts) >= 7:
                fonts.append({
                    "name": parts[0], "type": parts[1],
                    "embedded": parts[-5].lower() == "yes",
                    "subset": parts[-4].lower() == "yes",
                })
        return fonts
    except Exception:  # noqa: BLE001
        return []


def make_previews(pdf, outdir, n_pages=6):
    if not HAVE_POPPLER:
        return []
    os.makedirs(outdir, exist_ok=True)
    base = os.path.join(outdir, "preview")
    subprocess.run(["pdftoppm", "-png", "-r", "90", "-f", "1", "-l", str(n_pages),
                    pdf, base], capture_output=True, timeout=180)
    return sorted(
        os.path.join(outdir, f) for f in os.listdir(outdir)
        if f.startswith("preview") and f.endswith(".png"))


# ---------------------------------------------------------------------------
# TOC tooling
# ---------------------------------------------------------------------------

def _body_paras(doc):
    body = doc.body()
    out = []
    for child in body:
        if child.tag == q("p"):
            out.append(child)
    return out


def _heading_level(p):
    sid = para_style_id(p)
    if not sid:
        return None
    m = re.match(r"Heading([1-4])$", sid)
    return int(m.group(1)) if m else None


def _content_width_twips(doc):
    sect = None
    for el in doc.document().iter(q("sectPr")):
        sect = el
    if sect is None:
        return 9016
    pgSz = sect.find(q("pgSz"))
    pgMar = sect.find(q("pgMar"))
    w = int(get_attr(pgSz, "w:w", "11906"))
    l = int(get_attr(pgMar, "w:left", "1800")) if pgMar is not None else 1800
    r = int(get_attr(pgMar, "w:right", "1800")) if pgMar is not None else 1800
    return w - l - r


def _toc_entry_para(text, page, level, width, first=False, last=False):
    p = make_el("w:p")
    pPr = make_el("w:pPr")
    st = make_el("w:pStyle", {"w:val": "TOC%d" % level})
    insert_in_order(pPr, st)
    ind = make_el("w:ind", {"w:left": str(240 * (level - 1))})
    insert_in_order(pPr, ind)
    tabs = make_el("w:tabs")
    tab = make_el("w:tab", {"w:val": "right", "w:leader": "dot",
                            "w:pos": str(width)})
    tabs.append(tab)
    insert_in_order(pPr, tabs)
    insert_in_order(p, pPr)
    if first:
        for fc, txt in (("begin", None), (None, ' TOC \\o "1-3" \\z \\u '), ("separate", None)):
            r = make_el("w:r")
            if fc:
                r.append(make_el("w:fldChar", {"w:fldCharType": fc}))
            else:
                it = make_el("w:instrText", {"xml:space": "preserve"})
                it.text = txt
                r.append(it)
            p.append(r)
    def _run(text):
        r = make_el("w:r")
        t = make_el("w:t")
        t.text = text
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        r.append(t)
        return r
    p.append(_run(text))
    rtab = make_el("w:r")
    rtab.append(make_el("w:tab"))
    p.append(rtab)
    p.append(_run(str(page)))
    if last:
        r = make_el("w:r")
        r.append(make_el("w:fldChar", {"w:fldCharType": "end"}))
        p.append(r)
    return p


def collect_headings(doc):
    """(level, text, counters, embedded) for every Heading1-3 in body order.

    `embedded` is True when the paragraph's style numbering is suppressed
    because the text already carries its own number.
    """
    counters = [0, 0, 0]
    out = []
    for p in _body_paras(doc):
        lvl = _heading_level(p)
        if lvl is None or lvl > 3:
            continue
        text = re.sub(r"\s+", " ", para_text(p)).strip()
        if not text or re.sub(r"\s+", "", text) in ("目录", "目次", "Contents", "CONTENTS"):
            continue
        counters[lvl - 1] += 1
        for j in range(lvl, 3):
            counters[j] = 0
        embedded = False
        pPr = p.find(q("pPr"))
        if pPr is not None:
            numPr = pPr.find(q("numPr"))
            if numPr is not None:
                nid = numPr.find(q("numId"))
                if nid is not None and get_attr(nid, "w:val") == "0":
                    embedded = True
        out.append((lvl, text, tuple(counters), embedded))
    return out


def toc_insert(docx_path, spec_path=None):
    doc = Docx(docx_path)
    body = doc.body()
    paras = _body_paras(doc)
    headings = collect_headings(doc)
    if not headings:
        return {"ok": False, "reason": "文档中没有 Heading1-3 标题，未插入目录"}
    # duplicate guard: a TOC field already present?
    for n in doc.parts:
        if n.startswith("word/") and n.endswith(".xml") and b'TOC \\o' in doc.parts[n]:
            return {"ok": False, "reason": "已存在 TOC 域，跳过插入"}

    width = _content_width_twips(doc)
    width = width - 240  # right padding inside the tab stop

    # locate insert position
    insert_before = None
    toc_heading_para = None
    for p in paras:
        t = re.sub(r"\s+", "", para_text(p))
        if t in ("目录", "目次", "Contents", "CONTENTS"):
            toc_heading_para = p
            break
    if toc_heading_para is None:
        # before first numbered chapter-like heading
        for p in paras:
            lvl = _heading_level(p)
            if lvl == 1:
                t = re.sub(r"\s+", " ", para_text(p)).strip()
                if re.match(r"^(第[一二三四五六七八九十百千0-9]+章|\d+(\s|\.|、))", t):
                    insert_before = p
                    break
    # build TOC block
    block = []
    if toc_heading_para is None:
        h = make_el("w:p")
        pPr = make_el("w:pPr")
        st = make_el("w:pStyle", {"w:val": "Heading1"})
        insert_in_order(pPr, st)
        numPr = make_el("w:numPr")
        ilvl = make_el("w:ilvl", {"w:val": "0"})
        insert_in_order(numPr, ilvl)
        nid = make_el("w:numId", {"w:val": "0"})
        insert_in_order(numPr, nid)
        insert_in_order(pPr, numPr)
        insert_in_order(h, pPr)
        r = make_el("w:r")
        t = make_el("w:t")
        t.text = "目  录"
        r.append(t)
        h.append(r)
        block.append(h)
    labels = {0: "%d", 1: "%d.%d", 2: "%d.%d.%d"}
    for i, (lvl, text, c, embedded) in enumerate(headings):
        label = None if embedded else labels[lvl - 1] % c[:lvl]
        entry_text = ("%s  %s" % (label, text)) if label else text
        block.append(_toc_entry_para(
            entry_text, "?", lvl, width,
            first=(i == 0), last=(i == len(headings) - 1)))
    # insert
    if toc_heading_para is not None:
        idx = list(body).index(toc_heading_para)
        for j, el in enumerate(block):
            body.insert(idx + 1 + j, el)
    elif insert_before is not None:
        idx = list(body).index(insert_before)
        for j, el in enumerate(block):
            body.insert(idx + j, el)
    else:
        sect = body.find(q("sectPr"))
        idx = list(body).index(sect) if sect is not None else len(list(body))
        for j, el in enumerate(block):
            body.insert(idx + j, el)
    doc.save(docx_path)
    return {"ok": True, "entries": len(headings)}


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


def _page_texts(pdf):
    """Per-page text via ONE pdftotext call (pages separated by form feeds).

    Falls back to per-page calls (bounded) when the form-feed split is absent.
    """
    try:
        out = subprocess.run(["pdftotext", pdf, "-"],
                             capture_output=True, timeout=120)
        text = out.stdout.decode("utf-8", "replace")
        pages = text.split("\f")
        if len(pages) > 1:
            return [_norm(p) for p in pages]
    except Exception:  # noqa: BLE001
        pass
    info = pdf_page_size(pdf) or {}
    n = min(info.get("pages") or 1, 200)  # budget guard: never >200 subprocesses
    pages = []
    for i in range(1, n + 1):
        try:
            out = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i),
                                  pdf, "-"], capture_output=True, timeout=20)
            pages.append(_norm(out.stdout.decode("utf-8", "replace")))
        except Exception:  # noqa: BLE001
            pages.append("")
    return pages


def toc_fill(docx_path, pdf_path):
    doc = Docx(docx_path)
    pages = _page_texts(pdf_path)
    # PDF text inserts stray spaces around numbering/CJK; strip all spaces for matching
    pages_ns = [re.sub(r"\s+", "", p) for p in pages]
    headings = collect_headings(doc)
    if not headings:
        return {"ok": False, "reason": "no headings"}
    toc_page = None
    for i, pt in enumerate(pages_ns):
        if re.search(r"目录|目次|Contents", pt):
            toc_page = i + 1
            break
    labels = {0: "%d", 1: "%d.%d", 2: "%d.%d.%d"}
    width = _content_width_twips(doc) - 240
    results = []
    cur = 0  # zero-based page index of the previous heading
    toc_block = []
    for i, (lvl, text, c, embedded) in enumerate(headings):
        label = None if embedded else labels[lvl - 1] % c[:lvl]
        entry_text = ("%s  %s" % (label, text)) if label else text
        probe = re.sub(r"\s+", "", text)[:24]
        page_no = "?"
        if probe:
            hits = [pi for pi in range(cur, len(pages_ns)) if probe in pages_ns[pi]]
            # prefer a hit that is not the TOC page (TOC entries repeat the text)
            pick = next((pi for pi in hits if pi + 1 != toc_page),
                        hits[0] if hits else None)
            if pick is not None:
                page_no = pick + 1
                cur = pick
        results.append({"heading": text, "page": page_no})
        toc_block.append(_toc_entry_para(
            entry_text, page_no, lvl, width,
            first=(i == 0), last=(i == len(headings) - 1)))
    # replace old TOC block: find paragraphs between fldChar begin(TOC) and end
    body = doc.body()
    kids = list(body)
    begin_i = end_i = None
    depth = 0
    for i, el in enumerate(kids):
        if el.tag != q("p"):
            continue
        has_begin = any(
            get_attr(f, "w:fldCharType") == "begin" for f in el.iter(q("fldChar")))
        # check instrText
        instr = "".join(t.text or "" for t in el.iter(q("instrText")))
        if begin_i is None and "TOC" in instr and has_begin:
            begin_i = i
        if begin_i is not None:
            for f in el.iter(q("fldChar")):
                ft = get_attr(f, "w:fldCharType")
                if ft == "begin":
                    depth += 1
                elif ft == "end":
                    depth -= 1
            if depth == 0:
                end_i = i
                break
    if begin_i is None or end_i is None:
        return {"ok": False, "reason": "未找到 TOC 域，无法回填页码"}
    for el in kids[begin_i:end_i + 1]:
        body.remove(el)
    for j, el in enumerate(toc_block):
        body.insert(begin_i + j, el)
    doc.save(docx_path)
    return {"ok": True, "entries": results}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_render(args):
    env = check_env()
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)
    report = {"environment": env}
    pdf, err = render_pdf(args.docx, outdir)
    if err:
        report["error"] = err
        report["status"] = "partial"
        _write(os.path.join(outdir, "render_report.json"), report)
        print(json.dumps(report, ensure_ascii=False))
        return
    report["pdf"] = pdf
    report["page_size"] = pdf_page_size(pdf)
    report["fonts"] = pdf_fonts(pdf)
    report["all_fonts_embedded"] = all(f["embedded"] for f in report["fonts"]) if report["fonts"] else None
    report["previews"] = make_previews(pdf, outdir, args.pages)
    report["status"] = "success"
    _write(os.path.join(outdir, "render_report.json"), report)
    print(json.dumps({k: report[k] for k in ("status", "pdf", "page_size",
                                             "all_fonts_embedded")}, ensure_ascii=False))


def _write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("docx")
    r.add_argument("--outdir", required=True)
    r.add_argument("--pages", type=int, default=6)
    ti = sub.add_parser("toc-insert")
    ti.add_argument("docx")
    ti.add_argument("--spec", default=None)
    tf = sub.add_parser("toc-fill")
    tf.add_argument("docx")
    tf.add_argument("pdf")
    args = ap.parse_args(argv)
    if args.cmd == "render":
        cmd_render(args)
    elif args.cmd == "toc-insert":
        print(json.dumps(toc_insert(args.docx, args.spec), ensure_ascii=False))
    elif args.cmd == "toc-fill":
        print(json.dumps(toc_fill(args.docx, args.pdf), ensure_ascii=False))


if __name__ == "__main__":
    main()
