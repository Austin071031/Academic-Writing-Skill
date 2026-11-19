#!/usr/bin/env python3
"""parse_chapters.py — 长文档分章解析：多文件 → 章节树 + 稳定段落 ID + 交叉引用登记。

用法: python3 parse_chapters.py <file1> [<file2> ...] [--work /app/work]
                                [--out-name chapters.json] [--order file1,file2,...]
支持 .md/.txt/.tex/.docx/.pdf（docx/pdf 尽力降级提取纯文本并记录 issues）。
输出 work/chapters.json:
  files: [{key, path, format, n_paragraphs, issues}]
  sections: [{sid, file_key, level, heading_number, title, char_count,
              paragraphs: [{pid, kind, text, cite_marks, xrefs, char_count}]}]
  paragraphs: 全局扁平索引（同对象引用展开），pid 形如 C01-S002-P003
  headings: [{sid, level, number, title}]（目录树材料）
kind ∈ body|heading|figure_note|table_note|equation_note|appendix|footnote|
       reference_list|list|caption
xrefs: 段落内交叉引用 [{kind: figure|table|equation|chapter|section, raw, target}]
引用标记样式同 parse_manuscript：numeric / author_year / latex / footnote_md。
"""
import argparse, json, os, re, subprocess, sys, zipfile

NUM_MARK = re.compile(r"\[(\d+(?:\s*[-–—,，]\s*\d+)*)\]")
AUTHOR_YEAR = re.compile(r"[（(]([^（）()]{1,60}?)[,，]\s*((?:19|20)\d{2}[a-z]?)[)）]")
LATEX_CITE = re.compile(r"\\cite[a-z]*\{([^}]+)\}")
FOOTNOTE_MD = re.compile(r"\[\^([^\]]+)\]")
HEADING_MD = re.compile(r"^(#{1,6})\s+(.+)$")
HEADING_TEX = re.compile(r"\\(chapter|section|subsection|subsubsection)\*?\s*\{")
HEADING_NUM = re.compile(r"^(\d+(?:\.\d+){0,3})[\s\.、](\S.{0,120})$")
HEADING_CH = re.compile(r"^第([一二三四五六七八九十百\d]+)(章|节)\s*(\S.{0,120})$")
HEADING_CHNUM = re.compile(r"^([一二三四五六七八九十]+)、(\S.{0,120})$")
FIG_REF = re.compile(r"(图|Fig(?:ure)?\.?)\s*(\d+(?:[-–.]\d+)?)")
TAB_REF = re.compile(r"(表|Table\.?)\s*(\d+(?:[-–.]\d+)?)")
EQ_REF = re.compile(r"(式|公式|Eq\.?|Equation\.?)\s*[（(]?(\d+(?:[-–.]\d+)?)[)）]?")
CHAP_REF = re.compile(r"第([一二三四五六七八九十百\d]+)(章|节)")

def extract_docx(path):
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        xml = re.sub(r"</w:p>", "\n", xml)
        xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
        import html
        text = html.unescape(re.sub(r"<[^>]+>", "", xml))
        return text, None
    except Exception as e:
        return None, f"docx 解析失败: {e}"

def extract_pdf(path):
    try:
        r = subprocess.run(["pdftotext", "-q", path, "-"], capture_output=True, timeout=60)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.decode("utf-8", "ignore"), None
        return None, "pdftotext 无输出"
    except FileNotFoundError:
        return None, "环境缺少 pdftotext（降级：登记 exceptions）"
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

def find_xrefs(text):
    xrefs = []
    for m in FIG_REF.finditer(text):
        xrefs.append({"kind": "figure", "raw": m.group(0), "target": m.group(2)})
    for m in TAB_REF.finditer(text):
        xrefs.append({"kind": "table", "raw": m.group(0), "target": m.group(2)})
    for m in EQ_REF.finditer(text):
        xrefs.append({"kind": "equation", "raw": m.group(0), "target": m.group(2)})
    for m in CHAP_REF.finditer(text):
        xrefs.append({"kind": "chapter" if m.group(2) == "章" else "section",
                      "raw": m.group(0), "target": m.group(1)})
    return xrefs

def parse_heading(text):
    t = text.strip()
    m = HEADING_MD.match(t)
    if m:
        return len(m.group(1)), None, m.group(2).strip()
    m = HEADING_TEX.search(t)
    if m:
        lv = {"chapter": 1, "section": 2, "subsection": 3, "subsubsection": 4}[m.group(1)]
        title = t[m.end():]
        title = re.sub(r"\}.*$", "", title, count=1) if "}" in title else title
        num = None
        nm = re.match(r"(\d+(?:\.\d+)*)", title)
        if nm:
            num = nm.group(1)
            title = title[nm.end():].strip(" .、")
        return lv, num, title.strip() or t
    m = HEADING_NUM.match(t)
    if m:
        return m.group(1).count(".") + 1, m.group(1), m.group(2).strip()
    m = HEADING_CH.match(t)
    if m:
        return (1 if m.group(2) == "章" else 2), m.group(1), m.group(3).strip()
    m = HEADING_CHNUM.match(t)
    if m:
        return 1, m.group(1), m.group(2).strip()
    return None

def classify(text, kind_hint):
    t = text.strip()
    if kind_hint == "heading":
        return "heading"
    if re.match(r"^(图\s*\d|Fig)", t, re.I):
        return "figure_note" if not re.search(r"(见图|如图|Figure \d+ shows)", t, re.I) else "body"
    if re.match(r"^(表\s*\d|Table\s+\d)", t, re.I) and len(t) < 400:
        return "table_note"
    if re.match(r"^(式|公式|Eq)", t, re.I) and len(t) < 300:
        return "equation_note"
    if re.match(r"^(附录|Appendix)\b", t, re.I):
        return "appendix"
    if re.match(r"^[>\s]*(\[.?\]|\d+)[.、)]?\s*[^:：]{0,80}[:：]\s", t) and len(t) < 200:
        return "caption"
    if re.match(r"^([-*•]|\d+[.)、]\s)", t):
        return "list"
    return "body"

def parse_file(fkey, path):
    text, err = read_any(path)
    issues = [err] if err else []
    if text is None:
        return {"key": fkey, "path": path, "format": os.path.splitext(path)[1].lower().lstrip("."),
                "sections": [], "issues": issues + ["无法提取文本"]}
    raw_paras = [re.sub(r"\s*\n\s*", " ", p).strip()
                 for p in re.split(r"\n\s*\n", text) if p.strip()]
    # 纯文本换行分段兜底
    if len(raw_paras) <= 1 and "\n" in text:
        raw_paras = [p.strip() for p in text.splitlines() if p.strip()]
    sections = []
    cur = {"sid": f"{fkey}-S000", "file_key": fkey, "level": 0, "heading_number": None,
           "title": "(文件开头)", "paragraphs": []}
    sections.append(cur)
    sid_seq = 0
    in_refs = False
    for p in raw_paras:
        if re.search(r"^(#{1,6}\s*)?(参考文献|References|Bibliography|Works Cited)\s*$", p, re.I):
            in_refs = True
        hp = parse_heading(p)
        if hp and not in_refs:
            lv, num, title = hp
            sid_seq += 1
            cur = {"sid": f"{fkey}-S{sid_seq:03d}", "file_key": fkey, "level": lv,
                   "heading_number": num, "title": title, "paragraphs": []}
            sections.append(cur)
            continue
        kind = "reference_list" if in_refs else classify(p, None)
        pid = f"{cur['sid']}-P{len(cur['paragraphs']) + 1:03d}"
        cur["paragraphs"].append({"pid": pid, "kind": kind, "text": p,
                                  "cite_marks": find_marks(p), "xrefs": find_xrefs(p),
                                  "char_count": len(p)})
    for s in sections:
        s["char_count"] = sum(p["char_count"] for p in s["paragraphs"])
    return {"key": fkey, "path": path,
            "format": os.path.splitext(path)[1].lower().lstrip("."),
            "sections": sections, "issues": issues}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out-name", default="chapters.json")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    files, sections, flat, headings = [], [], [], []
    for i, path in enumerate(args.files, 1):
        fkey = f"C{i:02d}"
        fr = parse_file(fkey, path)
        files.append({k: fr[k] for k in ("key", "path", "format", "issues")})
        files[-1]["n_paragraphs"] = sum(len(s["paragraphs"]) for s in fr["sections"])
        files[-1]["n_sections"] = len(fr["sections"]) - (1 if fr["sections"] and fr["sections"][0]["level"] == 0 else 0)
        for s in fr["sections"]:
            sections.append(s)
            for p in s["paragraphs"]:
                flat.append(p)
            if s["level"] > 0:
                headings.append({"sid": s["sid"], "file_key": s["file_key"], "level": s["level"],
                                 "number": s["heading_number"], "title": s["title"]})
    styles = sorted({m["style"] for p in flat for m in p["cite_marks"]})
    out = {"files": files, "sections": sections, "paragraphs": flat,
           "headings": headings, "styles_detected": styles,
           "n_paragraphs": len(flat), "n_cite_marks": sum(len(p["cite_marks"]) for p in flat),
           "n_xrefs": sum(len(p["xrefs"]) for p in flat),
           "total_chars": sum(p["char_count"] for p in flat)}
    with open(os.path.join(args.work, args.out_name), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[parse_chapters] {len(files)} 文件 / {len(headings)} 标题 / {len(flat)} 段 / "
          f"{out['n_cite_marks']} 引用标记 / {out['n_xrefs']} 交叉引用 / {out['total_chars']} 字")
    return 0

if __name__ == "__main__":
    sys.exit(main())
