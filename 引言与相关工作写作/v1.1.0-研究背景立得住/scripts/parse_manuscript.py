#!/usr/bin/env python3
"""parse_manuscript.py — 提取稿件文本、分段并定位引用标记。

支持 .md/.txt/.tex/.docx(.pdf 通过 pdftotext 降级)。输出 work/manuscript.json:
  paragraphs: [{pid, kind, text, cite_marks:[{raw,style,nums,span}]}]
kind ∈ body|heading|figure_note|table_note|appendix|footnote|reference_list|list
引用样式识别: numeric([1] [1-3] [1,2]) | latex(\\cite) | author_year | footnote(¹/[^1])
"""
import argparse, json, os, re, subprocess, sys, zipfile

NUM_MARK = re.compile(r"\[(\d+(?:\s*[-–—,，]\s*\d+)*)\]")
AUTHOR_YEAR = re.compile(r"[（(]([^（）()]{1,60}?)[,，]\s*((?:19|20)\d{2}[a-z]?)[)）]")
LATEX_CITE = re.compile(r"\\cite[a-z]*\{([^}]+)\}")
FOOTNOTE_MD = re.compile(r"\[\^([^\]]+)\]")
HEADING_MD = re.compile(r"^#{1,6}\s+")
HEADING_TEX = re.compile(r"\\(section|subsection|subsubsection|chapter)\*?\{")

def extract_docx(path):
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        xml = re.sub(r"</w:p>", "\n", xml)
        xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
        text = re.sub(r"<[^>]+>", "", xml)
        import html
        return html.unescape(text), None
    except Exception as e:
        return None, f"docx 解析失败: {e}"

def extract_pdf(path):
    try:
        r = subprocess.run(["pdftotext", "-q", path, "-"], capture_output=True, timeout=60)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.decode("utf-8", "ignore"), None
        return None, "pdftotext 无输出"
    except FileNotFoundError:
        return None, "环境缺少 pdftotext"
    except Exception as e:
        return None, f"pdf 解析失败: {e}"

def read_any(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return extract_docx(path)
    if ext == ".pdf":
        return extract_pdf(path)
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read(), None
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError as e:
            return None, str(e)
    return None, "无法解码"

def classify_para(text, in_refs):
    t = text.strip()
    if not t:
        return "empty"
    if in_refs:
        return "reference_list"
    if HEADING_MD.match(t) or HEADING_TEX.match(t):
        return "heading"
    if re.match(r"^(图|表|Fig\.?|Table|Chart)\s*\d+", t, re.I):
        return "figure_note" if re.match(r"^(图|Fig)", t, re.I) else "table_note"
    if re.match(r"^(附录|Appendix)\b", t, re.I):
        return "appendix"
    if re.match(r"^([-*•]|\d+[.)、])\s", t):
        return "list"
    return "body"

def find_marks(text):
    marks = []
    for m in NUM_MARK.finditer(text):
        nums = []
        for part in re.split(r"[,，]", m.group(1)):
            part = part.strip()
            rm = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", part)
            if rm:
                nums.extend(range(int(rm.group(1)), int(rm.group(2)) + 1))
            elif part.isdigit():
                nums.append(int(part))
        if nums:
            marks.append({"raw": m.group(0), "style": "numeric", "nums": nums,
                          "span": [m.start(), m.end()]})
    for m in AUTHOR_YEAR.finditer(text):
        author = m.group(1).strip()
        if re.search(r"(19|20)\d{2}", author) or len(author) > 50:
            continue
        marks.append({"raw": m.group(0), "style": "author_year",
                      "author": author, "year": m.group(2), "span": [m.start(), m.end()]})
    for m in LATEX_CITE.finditer(text):
        keys = [k.strip() for k in m.group(1).split(",") if k.strip()]
        marks.append({"raw": m.group(0), "style": "latex", "keys": keys,
                      "span": [m.start(), m.end()]})
    for m in FOOTNOTE_MD.finditer(text):
        marks.append({"raw": m.group(0), "style": "footnote_md", "label": m.group(1),
                      "span": [m.start(), m.end()]})
    marks.sort(key=lambda x: x["span"][0])
    return marks

def split_paragraphs(text):
    """按空行分段；保留行内结构。"""
    paras = re.split(r"\n\s*\n", text)
    return [re.sub(r"\s*\n\s*", " ", p).strip() for p in paras if p.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out-name", default="manuscript.json")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    text, err = read_any(args.file)
    issues = []
    if err:
        issues.append(err)
    if text is None:
        out = {"file": args.file, "paragraphs": [], "issues": issues + ["无法提取文本"]}
        with open(os.path.join(args.work, args.out_name), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"[parse_manuscript] 失败: {issues}")
        return 1

    paras = split_paragraphs(text)
    out_paras, in_refs = [], False
    for i, p in enumerate(paras):
        kind = classify_para(p, in_refs)
        if re.search(r"(参考文献|References|Bibliography|Works Cited)\s*$", p, re.I) and kind == "heading":
            in_refs = True
        pid = f"P{i+1:03d}"
        marks = find_marks(p)
        out_paras.append({"pid": pid, "kind": kind, "text": p, "cite_marks": marks})
    n_marks = sum(len(p["cite_marks"]) for p in out_paras)
    styles = sorted({m["style"] for p in out_paras for m in p["cite_marks"]})
    out = {"file": args.file, "format": os.path.splitext(args.file)[1].lower().lstrip("."),
           "paragraphs": out_paras, "styles_detected": styles,
           "n_paragraphs": len(out_paras), "n_cite_marks": n_marks, "issues": issues}
    with open(os.path.join(args.work, args.out_name), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[parse_manuscript] {len(out_paras)} 段, {n_marks} 个引用标记, 样式={styles}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
