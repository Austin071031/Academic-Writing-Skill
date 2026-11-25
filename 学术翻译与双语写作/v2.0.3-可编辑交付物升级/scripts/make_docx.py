#!/usr/bin/env python3
"""make_docx.py — 可编辑交付物升级（v2.0.3 方向）：纯标准库生成 .docx。

把 translation_full.md 与 bilingual.md 转成可编辑 Word 文档
（translation.docx / bilingual.docx），并尽力用 LibreOffice 渲染 PDF 预览；
工具缺失时在 preview_status.json 如实记录降级。

docx 生成：最小 OOXML（document.xml + styles + content types），
标题层级映射 md 的 # 级别，双语对照段保留 〔PID〕 坐标。

用法: python3 make_docx.py --out /app/output [--work /app/work]
"""
import argparse, html, json, os, re, shutil, subprocess, sys, zipfile

CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""
RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""
STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:pPr><w:outlineLvl w:val="0"/></w:pPr><w:rPr><w:b/><w:sz w:val="32"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:pPr><w:outlineLvl w:val="1"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:pPr><w:outlineLvl w:val="2"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
</w:styles>"""

def md_to_docx_xml(md_text):
    paras = []
    for line in md_text.splitlines():
        s = line.rstrip()
        if not s.strip():
            continue
        style = None
        m = re.match(r"^(#{1,3})\s+(.*)$", s)
        if m:
            style = f"Heading{len(m.group(1))}"
            s = m.group(2)
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)  # 去 md 加粗标记
        esc = html.escape(s)
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        paras.append(f"<w:p>{ppr}<w:r><w:t xml:space=\"preserve\">{esc}</w:t></w:r></w:p>")
    body = "".join(paras)
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body>{body}<w:sectPr/></w:body></w:document>")

def write_docx(md_path, docx_path):
    with open(md_path, encoding="utf-8") as f:
        xml = md_to_docx_xml(f.read())
    with zipfile.ZipFile(docx_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/document.xml", xml)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    status = tu_status = {"docx": [], "pdf": [], "notes": []}
    made = []
    for md, docx in (("translation_full.md", "translation.docx"),
                     ("bilingual.md", "bilingual.docx")):
        p = os.path.join(args.out, md)
        if not os.path.exists(p):
            continue
        try:
            write_docx(p, os.path.join(args.out, docx))
            made.append(docx)
            status["docx"].append(docx)
        except Exception as e:
            status["notes"].append(f"{docx} 生成失败: {e}")

    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if soffice and made:
        for docx in made:
            try:
                r = subprocess.run(
                    [soffice, "--headless", "--convert-to", "pdf",
                     "--outdir", args.out, os.path.join(args.out, docx)],
                    capture_output=True, timeout=180)
                pdf = docx.rsplit(".", 1)[0] + ".pdf"
                if r.returncode == 0 and os.path.exists(os.path.join(args.out, pdf)):
                    status["pdf"].append(pdf)
                else:
                    status["notes"].append(f"{docx}→PDF 转换失败（{r.returncode}），已跳过")
            except Exception as e:
                status["notes"].append(f"{docx}→PDF 异常: {e}")
    elif made:
        status["notes"].append("环境无 LibreOffice：docx 已交付，PDF 预览降级为 preview.html")

    ps_path = os.path.join(args.out, "preview_status.json")
    old = {}
    if os.path.exists(ps_path):
        try:
            with open(ps_path, encoding="utf-8") as f:
                old = json.load(f)
        except Exception:
            pass
    old.update(status)
    with open(ps_path, "w", encoding="utf-8") as f:
        json.dump(old, f, ensure_ascii=False, indent=2)
    print(f"[make_docx] docx={made} pdf={status['pdf']}"
          + ("" if status["pdf"] else "（无 PDF 工具，如实记录降级）"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
