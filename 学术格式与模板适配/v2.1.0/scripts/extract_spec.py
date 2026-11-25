#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_spec.py — Turn free-text format requirements (task.md / case task text /
.cls / .tex / spec .md / spec .pdf) into a normalized, machine-checkable `spec`
JSON, then merge it with the *measured* template spec.

Everything unrecognized is recorded in `unresolved` (for the agent to settle
from the case text) — the pipeline never silently guesses.

Usage:
    python3 extract_spec.py --text task.md --tex template.cls --pdf spec.pdf \
        --measured spec_template.json --out spec.json

Stdlib only (pdftotext from poppler is used for PDFs when present).
"""
import argparse
import json
import os
import re
import subprocess
import sys

# ---------------------------------------------------------------------------
# Chinese font-size name -> pt
# ---------------------------------------------------------------------------
CN_SIZE = {
    "初号": 42, "小初": 36, "一号": 26, "小一": 24, "二号": 22, "小二": 18,
    "三号": 16, "小三": 15, "四号": 14, "小四": 12, "五号": 10.5, "小五": 9,
    "六号": 7.5, "小六": 6.5,
}

FONT_ALIASES = {
    "times new roman": "Times New Roman",
    "times": "Times New Roman",
    "arial": "Arial",
    "calibri": "Calibri",
    "宋体": "宋体", "simsun": "宋体", "宋": "宋体",
    "黑体": "黑体", "simhei": "黑体",
    "楷体": "楷体", "kaiti": "楷体", "楷": "楷体",
    "仿宋": "仿宋", "fangsong": "仿宋",
}

REF_STYLES = {
    "gb/t 7714": "gb_t_7714", "gbt7714": "gb_t_7714", "gb7714": "gb_t_7714",
    "7714": "gb_t_7714",
    "ieee": "ieee", "apa": "apa", "apa7": "apa", "vancouver": "vancouver",
    "nature": "nature", "elsevier": "elsevier", "springer": "springer",
    "harvard": "harvard", "mla": "mla", "chicago": "chicago",
    "author-year": "author_year", "author year": "author_year",
    "numeric": "numeric",
}


def _pt(v):
    return float(v)


def _size_pt(token):
    token = token.strip()
    if token in CN_SIZE:
        return float(CN_SIZE[token])
    m = re.match(r"(\d+(?:\.\d+)?)\s*(?:pt|磅|point)", token, re.I)
    if m:
        return float(m.group(1))
    return None


def _font(token):
    t = token.strip().lower()
    if t in FONT_ALIASES:
        return FONT_ALIASES[t]
    for k, v in FONT_ALIASES.items():
        if k in t:
            return v
    return token.strip()


def extract_from_text(text):
    """Rule-based extraction; returns (spec_dict, unresolved_hints)."""
    spec = {"page": {}, "body": {}, "headings": {}, "captions": {},
            "tables": {}, "references": {}, "header_footer": {}, "toc": {}}
    un = []
    T = text.replace(" ", " ")
    low = T.lower()

    # ---- page size / margins ------------------------------------------------
    m = re.search(r"a4", low)
    if m:
        spec["page"]["paper"] = "A4"
    m = re.search(r"(letter|us letter)", low)
    if m:
        spec["page"]["paper"] = "Letter"
    def _to_mm(val, unit_hint=""):
        v = float(val)
        if "毫米" in unit_hint or re.search(r"\bmm\b", unit_hint):
            return v
        return v * 10.0  # cm / 厘米 (the common Chinese academic unit)

    for label, key in (("上边距|上页边距|top margin", "margin_top_mm"),
                       ("下边距|下页边距|bottom margin", "margin_bottom_mm"),
                       ("左边距|左页边距|inner margin", "margin_left_mm"),
                       ("右边距|右页边距|outer margin", "margin_right_mm"),
                       ("页边距", None)):
        for mm in re.finditer(r"(?:%s)[^0-9]{0,6}(\d+(?:\.\d+)?)\s*(cm|厘米|毫米|mm)" % label, T):
            v = _to_mm(mm.group(1), mm.group(2))
            if key:
                spec["page"][key] = v
            else:
                for kk in ("margin_top_mm", "margin_bottom_mm",
                           "margin_left_mm", "margin_right_mm"):
                    spec["page"].setdefault(kk, v)
    for cm in re.finditer(r"页边距[^。；\n]{0,40}", T):
        seg = cm.group(0)
        # common Chinese pattern: 上下 X cm，左右 Y cm
        vert = re.search(r"(上下|纵向)[^0-9]{0,4}(\d+(?:\.\d+)?)", seg)
        horz = re.search(r"(左右|横向)[^0-9]{0,4}(\d+(?:\.\d+)?)", seg)
        if vert and horz:
            spec["page"]["margin_top_mm"] = spec["page"]["margin_bottom_mm"] = _to_mm(vert.group(2))
            spec["page"]["margin_left_mm"] = spec["page"]["margin_right_mm"] = _to_mm(horz.group(2))
        # pattern: 页边距上2.5cm下2.5cm左3.0cm右2.0cm
        pairs = {"上": "margin_top_mm", "下": "margin_bottom_mm",
                 "左": "margin_left_mm", "右": "margin_right_mm"}
        for side, k in pairs.items():
            for pm in re.finditer(r"%s\s*(\d+(?:\.\d+)?)\s*(cm|厘米|毫米|mm)" % side, seg):
                spec["page"][k] = _to_mm(pm.group(1), pm.group(2))
    m = re.search(r"(\d+)\s*栏|双栏|single column|one column|double column|two column", low)
    if m:
        if re.search(r"双栏|double column|two column", low):
            spec["page"]["columns"] = 2
        elif m.group(1):
            spec["page"]["columns"] = int(m.group(1))

    # ---- body font / size / spacing ------------------------------------------
    seg = None
    m = re.search(r"(正文|body)[^。；\n]{0,80}", low)
    if m:
        seg = T[m.start():m.end()]
    # cut the segment before any heading-related words so that e.g. "正文小四…
    # 一级标题三号黑体…" only describes the body
    if seg:
        cut = re.search(r"(标题|heading|章\s*标|级\s*标)", seg)
        if cut:
            seg = seg[:cut.start()]
    target = seg or T
    # pick the size token that appears FIRST (nearest to 正文)
    best = None
    for name in CN_SIZE:
        i = target.find(name)
        if i >= 0 and (best is None or i < best[0]):
            best = (i, float(CN_SIZE[name]))
    if best:
        spec["body"]["size_pt"] = best[1]
    if "size_pt" not in spec["body"]:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:pt|磅)", target)
        if m:
            spec["body"]["size_pt"] = float(m.group(1))
    for fkey in ("times new roman", "arial", "calibri", "宋体", "黑体", "楷体", "仿宋"):
        if fkey in target.lower():
            spec["body"].setdefault("fonts", {})["ascii" if fkey.isascii() else "eastAsia"] = _font(fkey)
    if "行距" in T:
        m = re.search(r"([\d.]+)\s*倍行距", T)
        if m:
            spec["body"]["line_spacing"] = float(m.group(1))
        elif re.search(r"固定值\s*(\d+(?:\.\d+)?)\s*(?:pt|磅)", T):
            spec["body"]["line_spacing_pt"] = float(re.search(
                r"固定值\s*(\d+(?:\.\d+)?)", T).group(1))
        elif re.search(r"固定行距|exact", low):
            spec["body"]["line_rule"] = "exact"
        if re.search(r"单倍行距", T):
            spec["body"]["line_spacing"] = 1.0

    # ---- headings -------------------------------------------------------------
    for hm in re.finditer(r"(第?[一二三四五六七八九十0-9]+[级章]标题|heading\s?\d|h1|h2|h3)[^。；\n]{0,80}", low):
        seg = T[hm.start():hm.end()]
        lvl_m = re.search(r"(\d)", hm.group(1))
        lvl = int(lvl_m.group(1)) if lvl_m else None
        if lvl is None:
            continue
        entry = spec["headings"].setdefault("h%d" % lvl, {})
        cn = re.findall(r"(初号|小初|一号|小一|二号|小二|三号|小三|四号|小四|五号|小五|六号)", seg)
        if cn:
            entry["size_pt"] = float(CN_SIZE[cn[0]])
        else:
            pm = re.search(r"(\d+(?:\.\d+)?)\s*(?:pt|磅)", seg)
            if pm:
                entry["size_pt"] = float(pm.group(1))
        if "黑体" in seg:
            entry["fonts"] = {"eastAsia": "黑体"}
        elif "宋体" in seg:
            entry["fonts"] = {"eastAsia": "宋体"}
        elif "楷体" in seg:
            entry["fonts"] = {"eastAsia": "楷体"}
        for fk in ("times new roman", "arial"):
            if fk in seg:
                entry.setdefault("fonts", {})["ascii"] = _font(fk)
        if "加粗" in seg or "bold" in seg:
            entry["bold"] = True
        if re.search(r"居中", seg):
            entry["align"] = "center"
        elif re.search(r"左对齐", seg):
            entry["align"] = "left"
    if re.search(r"章节按\s*([\d.]+|第.+章)", T):
        m = re.search(r"章节按\s*([\d.]+|第.+章)", T)
        spec["headings"]["numbering"] = (
            "chinese_chapter" if "第" in m.group(1) else "decimal_multilevel")

    # ---- captions ---------------------------------------------------------------
    if re.search(r"图题[在位于]{1,3}(下|下方|下面)|图注[在位于]{1,3}(下|下方)|caption\s*below", low):
        spec["captions"]["figure_position"] = "below"
    if re.search(r"表题[在位于]{1,3}(上|上方|上面)|表注[在位于]{1,3}(上|上方)|caption\s*above", low):
        spec["captions"]["table_position"] = "above"
    m = re.search(r"图\s*(\d+)[-—.](\d+)", T)
    if m:
        spec["captions"]["figure_numbering"] = "chapter_seq"
    if re.search(r"三线表|three[- ]line", low):
        spec["tables"]["three_line"] = True
        spec["tables"]["top_border_pt"] = 1.5
        spec["tables"]["bottom_border_pt"] = 1.5
        spec["tables"]["header_border_pt"] = 0.75
    m = re.search(r"题注[^。；\n]{0,30}(小五|五号|小四|六号|\d+(?:\.\d+)?\s*(?:pt|磅))", T)
    if m:
        spec["captions"]["size_pt"] = _size_pt(m.group(1))

    # ---- references ---------------------------------------------------------------
    for k, v in REF_STYLES.items():
        if k in low:
            spec["references"]["style"] = v
            break
    if re.search(r"参考文献悬挂缩进|hanging indent", low):
        spec["references"]["hanging_indent"] = True
    m = re.search(r"(?:参考文献|references)[^。；\n]{0,40}(小五|五号|小四|四号|\d+(?:\.\d+)?\s*(?:pt|磅))", low)
    if m:
        spec["references"]["size_pt"] = _size_pt(m.group(1))
    if re.search(r"按作者字母|alphabetical|按出现顺序|order of appearance", low):
        spec["references"]["order"] = (
            "alphabetical" if re.search(r"字母|alphabet", low) else "appearance")

    # ---- header/footer / page numbers --------------------------------------------
    if re.search(r"页码|page number", low):
        spec["header_footer"]["page_number"] = True
        if re.search(r"页脚|footer", low):
            spec["header_footer"]["page_number_position"] = "footer"
        elif re.search(r"页眉|header", low):
            spec["header_footer"]["page_number_position"] = "header"
        if re.search(r"居中", low):
            spec["header_footer"]["page_number_align"] = "center"
        if re.search(r"罗马数字|roman", low):
            spec["header_footer"]["front_matter_numbering"] = "roman"

    # ---- TOC -----------------------------------------------------------------------
    if re.search(r"目录|table of contents|\btoc\b", low):
        spec["toc"]["required"] = True

    # unresolved hints: sentences that look like requirements we could not parse
    for rm in re.finditer(r"[^。；\n]{0,60}(须|必须|应当|要求|一律|均为)[^。；\n]{0,60}", T):
        seg = rm.group(0).strip()
        if seg and not any(k in seg for k in ("不得", "禁止")):
            un.append(seg)
    spec["_unresolved_hints"] = un[:50]
    return spec


def extract_from_cls(text):
    """Parse a LaTeX .cls / .tex preamble for geometry / font / spacing."""
    spec = {"page": {}, "body": {}, "_unresolved_hints": []}
    g = re.search(r"\\geometry\{([^}]*)\}", text)
    if g:
        for kv in g.group(1).split(","):
            if "=" in kv:
                k, v = kv.split("=", 1)
                k, v = k.strip(), v.strip()
                m = re.match(r"(\d+(?:\.\d+)?)(cm|mm|in|pt)", v)
                if not m:
                    continue
                val = float(m.group(1))
                unit = m.group(2)
                if unit == "mm":
                    val /= 10.0
                elif unit == "in":
                    val *= 25.4
                elif unit == "pt":
                    val *= 25.4 / 72.0
                keymap = {"top": "margin_top_mm", "bottom": "margin_bottom_mm",
                          "left": "margin_left_mm", "right": "margin_right_mm",
                          "inner": "margin_left_mm", "outer": "margin_right_mm"}
                if k in keymap:
                    spec["page"][keymap[k]] = round(val, 2)
                if k == "twocolumn":
                    spec["page"]["columns"] = 2
    m = re.search(r"\\documentclass\[([^\]]*)\]", text)
    if m:
        om = re.search(r"(\d+(?:\d+)?)pt", m.group(1))
        if om:
            spec["body"]["size_pt"] = float(om.group(1))
        if "twocolumn" in m.group(1):
            spec["page"]["columns"] = 2
    if re.search(r"\\linespread\{([\d.]+)\}", text):
        spec["body"]["line_spacing"] = round(
            float(re.search(r"\\linespread\{([\d.]+)\}", text).group(1)) * 1.2, 3)
    for cmd, style in (("IEEEtran", "ieee"), ("elsarticle", "elsevier"),
                       ("springer", "springer"), ("apa", "apa")):
        if cmd in text:
            spec.setdefault("references", {})["style"] = style
    return spec


def read_pdf_text(path):
    try:
        out = subprocess.run(["pdftotext", "-layout", path, "-"],
                             capture_output=True, timeout=120)
        return out.stdout.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return ""


def project_measured_styles(measured):
    """Project template style measurements onto the normalized spec groups the
    adapter actually consumes (body / headings / captions / references).

    measure_template.py records every style under 'styles', but the adapter
    reads only the normalized groups; without this projection a template-only
    requirement (task text silent on body font/size/spacing) silently falls
    back to built-in defaults and the adapted file contradicts the template.
    Only missing keys are filled here; textual extraction still wins later via
    deep_merge(measured, textual) with conflicts recorded.
    """
    styles = (measured or {}).get("styles") or {}
    if not styles:
        return measured
    KEYS = ("size_pt", "fonts", "bold", "line_spacing", "line_spacing_pt",
            "line_rule", "before_pt", "after_pt")
    body = measured.setdefault("body", {})
    heads = measured.setdefault("headings", {})
    caps = measured.setdefault("captions", {})
    refs = measured.setdefault("references", {})
    for _sid, entry in styles.items():
        if entry.get("type") != "paragraph":
            continue
        role = entry.get("role")
        if role == "body":
            dst = body
        elif role == "heading" and entry.get("level") in (1, 2, 3, 4):
            dst = heads.setdefault("h%d" % entry["level"], {})
        elif role == "caption":
            dst = caps
        elif role == "reference":
            dst = refs
        else:
            continue
        for k in KEYS:
            if k in entry and k not in dst:
                dst[k] = entry[k]
        # first-line indent: measured raw units are 1/100-char / twips, rename
        # explicitly so downstream readers are not misled by a "_pt" suffix
        if entry.get("first_line_ch") and "first_line_chars" not in dst:
            dst["first_line_chars"] = round(entry["first_line_ch"] / 100.0, 1)
        if entry.get("first_line_pt") and "first_line_twips" not in dst:
            dst["first_line_twips"] = entry["first_line_pt"]
    defaults = (measured or {}).get("defaults") or {}
    for k in ("size_pt", "fonts"):
        if k in defaults and k not in body:
            body[k] = defaults[k]
    for g in ("body", "headings", "captions", "references"):
        if not measured.get(g):
            measured.pop(g, None)
    return measured


def deep_merge(base, extra):
    """extra wins; conflicts recorded under 'conflicts'."""
    conflicts = []
    out = json.loads(json.dumps(base)) if base else {}
    _merge_into(out, extra or {}, "", conflicts)
    return out, conflicts


def _merge_into(dst, src, path, conflicts):
    for k, v in src.items():
        if k.startswith("_"):
            continue
        p = "%s.%s" % (path, k) if path else k
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _merge_into(dst[k], v, p, conflicts)
        elif k in dst and dst[k] not in (None, {}, "") and dst[k] != v:
            conflicts.append({"path": p, "measured": dst[k], "textual": v,
                              "resolution": "textual_wins"})
            dst[k] = v
        else:
            dst[k] = v


def finalize(spec, conflicts):
    spec["conflicts"] = conflicts
    # collect unresolved: leaf values still missing from key groups
    unresolved = []
    for group, keys in (("page", ("margin_top_mm", "margin_bottom_mm",
                                  "margin_left_mm", "margin_right_mm")),
                        ("body", ("size_pt",))):
        for kk in keys:
            if kk not in spec.get(group, {}):
                unresolved.append("%s.%s" % (group, kk))
    spec["unresolved"] = unresolved
    return spec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=None, help="task.md / requirements txt")
    ap.add_argument("--tex", default=None, help=".cls or .tex preamble")
    ap.add_argument("--pdf", default=None, help="spec PDF")
    ap.add_argument("--measured", default=None, help="spec JSON from measure_template.py")
    ap.add_argument("--out", default="spec.json")
    args = ap.parse_args(argv)

    textual = {"page": {}, "body": {}, "headings": {}, "captions": {},
               "tables": {}, "references": {}, "header_footer": {}, "toc": {}}
    un = []
    for kind, path in (("text", args.text), ("tex", args.tex), ("pdf", args.pdf)):
        if not path:
            continue
        if kind == "pdf":
            text = read_pdf_text(path)
            if not text.strip():
                un.append("PDF 规格文件无法抽取文本（可能为扫描件）：%s" % path)
                continue
        else:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        part = extract_from_cls(text) if kind == "tex" else extract_from_text(text)
        _merge_into(textual, part, "", [])
        un.extend(part.get("_unresolved_hints", []))

    measured = {}
    if args.measured and os.path.exists(args.measured):
        with open(args.measured, encoding="utf-8") as f:
            measured = json.load(f)
        measured.pop("_unresolved_hints", None)
        # v2.1.0: wire measured template styles into body/headings/captions/
        # references groups so template-only requirements reach the adapter
        measured = project_measured_styles(measured)

    merged, conflicts = deep_merge(measured, textual)
    merged["_unresolved_hints"] = un
    finalize(merged, conflicts)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "out": args.out,
                      "conflicts": len(conflicts),
                      "unresolved": merged["unresolved"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
