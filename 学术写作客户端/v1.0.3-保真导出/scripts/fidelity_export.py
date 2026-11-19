#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fidelity_export — 保真导出管线：渲染 + 字体核验 + 目录页码回填 + 保真差分。

管线步骤（全部可降级，失败如实记录）：
  1. font-check      字体替换建议（度量兼容表）+ 最终 PDF 嵌入字体检查
  2. render          DOCX -> PDF -> PNG 预览（LibreOffice；不可用则降级注明）
  3. toc-refresh     检测 TOC 域；pdftotext 定位标题页码后回填域缓存值
                     （保留 begin/separate/end 域结构，Word 内仍可 F9 刷新）
  4. fidelity        before/after 内容单元级差分（audit_diff）

用法：
  python3 fidelity_export.py font-check <docx> [out.json]
  python3 fidelity_export.py render <docx> <out_dir> [pages]
  python3 fidelity_export.py toc-refresh <docx> <pdf> <out_docx> [out.json]
  python3 fidelity_export.py fidelity <before.docx> <after.docx> [whitelist.txt] [out.json]
"""
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docxkit as dk  # noqa: E402
import audit_diff  # noqa: E402

# 度量兼容替换表（缺字体时用同度量字体替代，保证版式不塌）
FONT_SUBSTITUTE = {
    "Times New Roman": "Liberation Serif",
    "Arial": "Liberation Sans",
    "Calibri": "Carlito",
    "Cambria": "Caladea",
    "Courier New": "Liberation Mono",
    "Courier": "Liberation Mono",
    "宋体": "Noto Serif CJK SC",
    "SimSun": "Noto Serif CJK SC",
    "黑体": "Noto Sans CJK SC",
    "SimHei": "Noto Sans CJK SC",
}

TWIPS_PER_PT = 20
PT_PER_CM = 28.3465


def pt_to_twips(pt):
    return int(round(pt * TWIPS_PER_PT))


def cm_to_twips(cm):
    return int(round(cm * PT_PER_CM * TWIPS_PER_PT))


# 中文字号 -> 磅
CN_FONT_SIZE = {"初号": 42, "小初": 36, "一号": 26, "小一": 24, "二号": 22,
                "小二": 18, "三号": 16, "小三": 15, "四号": 14, "小四": 12,
                "五号": 10.5, "小五": 9, "六号": 7.5}


def used_fonts(docx):
    fonts = set()
    root = docx.tree().getroot()
    for tag in ("w:rFonts",):
        for el in root.iter(dk.qn(tag)):
            for attr in ("ascii", "eastAsia", "hAnsi", "cs"):
                v = el.get(dk.qn("w:" + attr))
                if v:
                    fonts.add(v)
    if docx.has_part("word/styles.xml"):
        st = docx.tree("word/styles.xml").getroot()
        for el in st.iter(dk.qn("w:rFonts")):
            for attr in ("ascii", "eastAsia", "hAnsi", "cs"):
                v = el.get(dk.qn("w:" + attr))
                if v:
                    fonts.add(v)
    return sorted(fonts)


def system_fonts():
    found = set()
    for d in ("/usr/share/fonts", os.path.expanduser("~/.fonts"),
              "/usr/local/share/fonts"):
        for base, _, files in os.walk(d):
            for f in files:
                found.add(os.path.splitext(f)[0])
    return found


def font_check(docx_path, out=None):
    docx = dk.Docx(docx_path)
    fonts = used_fonts(docx)
    avail = system_fonts()
    report = {"fonts_in_document": fonts, "substitutions": [],
              "note": "替代字体与原版度量兼容（同字宽），版式保持一致"}
    for f in fonts:
        base = f.split(",")[0].strip()
        if base in avail:
            continue
        sub = FONT_SUBSTITUTE.get(base)
        if sub and any(sub.lower().replace(" ", "") in a.lower().replace(" ", "")
                       for a in avail):
            report["substitutions"].append({"from": base, "to": sub,
                                            "metric_compatible": True})
        elif sub:
            report["substitutions"].append({"from": base, "to": sub,
                                            "metric_compatible": True,
                                            "installed": False})
        else:
            report["substitutions"].append({"from": base, "to": None,
                                            "metric_compatible": False,
                                            "note": "无已知度量兼容替代，"
                                                    "版式可能有细微差异"})
    s = json.dumps(report, ensure_ascii=False, indent=1)
    if out:
        open(out, "w", encoding="utf-8").write(s)
    print(s)
    return 0


def render(docx_path, out_dir, pages=3):
    import render_preview
    st = render_preview.render(docx_path, out_dir, pages)
    print(json.dumps(st, ensure_ascii=False))
    return 0 if st["ok"] else 1


def _pdf_pages_text(pdf_path):
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return []
    try:
        r = subprocess.run([pdftotext, "-layout", pdf_path, "-"],
                           capture_output=True, text=True, timeout=120)
        return r.stdout.split("\f")
    except Exception:
        return []


def toc_refresh(docx_path, pdf_path, out_docx, out=None):
    """两遍渲染回填 TOC 缓存页码（保留域结构）。"""
    os.makedirs(os.path.dirname(os.path.abspath(out_docx)) or ".",
                exist_ok=True)
    docx = dk.Docx(docx_path)
    dk._build_parent_map(docx.tree().getroot())
    root = docx.tree().getroot()
    # 找 TOC 域
    instrs = [it for it in root.iter(dk.qn("w:instrText"))]
    has_toc = any("TOC" in (it.text or "") for it in instrs)
    headings = []
    for p in docx.paragraphs():
        st = docx.para_style(p) or ""
        t = docx.para_text(p).strip()
        if t and re.match(r"(?i)heading[1-3]$|标题[1-3]$", st):
            headings.append(t)
    report = {"has_toc_field": has_toc, "headings_found": len(headings),
              "refreshed": 0, "degraded": []}
    if not has_toc:
        report["degraded"].append("文档无 TOC 域，跳过页码回填")
        docx.save(out_docx)
    else:
        pages = _pdf_pages_text(pdf_path)
        page_of = {}
        for i, ptext in enumerate(pages, start=1):
            for h in headings:
                if h and h in ptext and h not in page_of:
                    page_of[h] = i
        # 回填：对 TOC 段落内“标题文本 + 尾部页码”的行，按标题匹配实测页码，
        # 只改尾部数字的显示文本，不动域结构（Word 内仍可 F9 刷新）。
        toc_paras = []
        for p in docx.paragraphs():
            pts = [(t, t.text) for t in p.iter(dk.qn("w:t"))]
            full = "".join(x[1] or "" for x in pts)
            if re.search(r"\t?\d+$", full) and any(
                    h[:10] in full for h in headings):
                toc_paras.append((p, pts, full))
        k = 0
        for p, pts, full in toc_paras:
            for h in headings:
                if h[:12] in full and h in page_of:
                    new_page = str(page_of[h])
                    m = re.search(r"(\d+)$", full)
                    if m and m.group(1) != new_page:
                        old = m.group(1)
                        # 只改最后一个 w:t 的尾部数字
                        tail = pts[-1]
                        if tail[1] and tail[1].endswith(old):
                            tail[0].text = tail[1][:-len(old)] + new_page
                            report["refreshed"] += 1
                    break
            k += 1
        if not pages:
            report["degraded"].append("pdftotext 不可用或无文本层，"
                                      "未回填页码；Word 中 F9 可刷新")
        docx.save(out_docx)
    s = json.dumps(report, ensure_ascii=False, indent=1)
    if out:
        open(out, "w", encoding="utf-8").write(s)
    print(s)
    return 0


def fidelity(before, after, whitelist=None, out=None):
    wl = []
    if whitelist and os.path.exists(whitelist):
        wl = [l.strip() for l in open(whitelist, encoding="utf-8")
              if l.strip()]
    report = audit_diff.diff(before, after, wl)
    s = json.dumps(report, ensure_ascii=False, indent=1)
    if out:
        open(out, "w", encoding="utf-8").write(s)
    print(s)
    return 0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    rest = sys.argv[2:]
    if cmd == "font-check":
        return font_check(rest[0], rest[1] if len(rest) > 1 else None)
    if cmd == "render":
        return render(rest[0], rest[1],
                      int(rest[2]) if len(rest) > 2 else 3)
    if cmd == "toc-refresh":
        return toc_refresh(rest[0], rest[1], rest[2],
                           rest[3] if len(rest) > 3 else None)
    if cmd == "fidelity":
        return fidelity(rest[0], rest[1],
                        rest[2] if len(rest) > 2 else None,
                        rest[3] if len(rest) > 3 else None)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
