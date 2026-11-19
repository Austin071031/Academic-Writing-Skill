#!/usr/bin/env python3
"""parse_manuscript.py — 将稿件解析为结构模型 work/structure.json。

支持: .md / .tex / .txt / .docx(标准库解zip) / .pdf(调 pdftotext，缺失则降级记录)。
输出结构: sections[] / paragraphs[] / sentences[] / stats / issues。
段落与句子带稳定 ID（SEC1, P001, P001-s2），供诊断定位回溯。
只依赖标准库；pdftotext 为可选外部工具。
"""
import argparse, json, os, re, subprocess, sys, zipfile
import xml.etree.ElementTree as ET

HEADING_KEYWORDS = (
    "摘要", "关键词", "关键字", "引言", "前言", "绪论", "背景", "相关工作", "文献综述",
    "研究方法", "研究方法与设计", "材料与方法", "实验方法", "实验设置", "实验", "仿真",
    "结果", "结果与讨论", "结果分析", "讨论", "结论", "结论与展望", "总结", "总结与展望",
    "展望", "致谢", "参考文献", "引用文献", "附录", "声明",
    "abstract", "keywords", "introduction", "background", "related work", "literature review",
    "methods", "methodology", "materials and methods", "experimental setup", "experiments",
    "results", "results and discussion", "discussion", "conclusion", "conclusions",
    "acknowledg", "references", "bibliography", "appendix", "supplement",
)

RE_MD_HEAD = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
RE_TEX_SEC = re.compile(r"\\(section|subsection|subsubsection|chapter)\*?\{([^}]*)\}")
RE_NUM_HEAD = re.compile(r"^(\d+(?:\.\d+){0,3})[、．.\s]\s*(\S.{0,58})$")
RE_CN_HEAD = re.compile(r"^(第[一二三四五六七八九十百\d]+[章节篇部])[、．.\s:：]?\s*(.{0,40})$")
RE_CN_ENUM = re.compile(r"^([一二三四五六七八九十]+)、\s*(.{1,40})$")
RE_SENT = re.compile(r"[^。！？!?；;]+[。！？!?；;]*")
# 英文缩写与保护模式：切句前屏蔽其句点
_ABBR = ["et al", "Fig", "Figs", "Eq", "Eqs", "No", "Nos", "ca", "cf", "vs",
         "e.g", "i.e", "etc", "approx", "Dr", "Prof", "Mr", "Ms", "St", "Jr",
         "vol", "pp", "ed", "eds", "Inc", "Ltd", "Co", "U.S", "U.K", "Ph.D",
         "M.Sc", "B.Sc", "i.v", "i.p", "s.c", "wt", "at", "mol", "vol"]
RE_ABBR_PROTECT = re.compile(
    r"\b(" + "|".join(re.escape(a) for a in _ABBR) + r")\.", re.I)
RE_SENT_BOUNDARY = re.compile(r"(?<=[.!?])\s+(?=[\"'“‘(\[A-Z0-9])")

def split_sentences_mixed(text):
    """中英混排句切分：先按中文标点粗切，再对每段做英文句号切分（带保护）。"""
    out = []
    for chunk in RE_SENT.finditer(text.replace("\n", " ").strip()):
        s = chunk.group(0).strip()
        if not s:
            continue
        # 保护：小数、缩写、姓名首字母、版本号中的句点
        prot = re.sub(r"(\d)\.(\d)", lambda m: m.group(1) + "\x00DOT\x00" + m.group(2), s)
        prot = RE_ABBR_PROTECT.sub(lambda m: m.group(1) + "\x00DOT\x00", prot)
        # 注：不保护单个大写字母+句点（"1.18 V. The ..." 中 V 为单位结尾，
        # 保护会误并句；正文姓名首字母场景由缩写表覆盖常见情形）
        for part in RE_SENT_BOUNDARY.split(prot):
            part = part.replace("\x00DOT\x00", ".").strip()
            if part:
                out.append(part)
    return out

def read_text(path, limit=4_000_000):
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read(limit), enc
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError:
            return None, None
    return None, None

def is_kw_heading(line):
    s = line.strip().rstrip(":：")
    if len(s) > 40:
        return None
    low = s.lower()
    for kw in HEADING_KEYWORDS:
        if low == kw or low.startswith(kw + " "):
            return s
    return None

def split_sentences(text):
    return split_sentences_mixed(text)

def parse_markdown(text):
    blocks, in_code = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        blocks.append(line)
    return blocks

def tex_to_lines(text):
    text = re.sub(r"(?<!\\)%.*", "", text)
    return text.splitlines()

def docx_to_blocks(path):
    """返回 [(kind, level, text)]，kind ∈ {heading, para}。标准库解析。"""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    blocks = []
    with zipfile.ZipFile(path) as z:
        with z.open("word/document.xml") as f:
            tree = ET.parse(f)
    for p in tree.getroot().iter("{%s}p" % ns["w"]):
        style = None
        ppr = p.find("w:pPr", ns)
        if ppr is not None:
            ps = ppr.find("w:pStyle", ns)
            if ps is not None:
                style = ps.get("{%s}val" % ns["w"], "")
        txt = "".join(t.text or "" for t in p.iter("{%s}t" % ns["w"])).strip()
        if not txt:
            continue
        lvl = None
        if style:
            m = re.search(r"(?:Heading|标题)\s*(\d+)", style, re.I)
            if m:
                lvl = int(m.group(1))
            elif re.search(r"^(Heading|标题|Title)", style, re.I):
                lvl = 1
        blocks.append(("heading", lvl, txt) if lvl else ("para", None, txt))
    return blocks

def build_model(blocks, source, fmt, issues):
    """blocks: [(kind, level, text)] → structure model"""
    sections, paragraphs, sentences = [], [], []
    cur = {"id": "SEC0", "level": 0, "heading": "(文首/无标题部分)", "order": 0,
           "start_para": None, "end_para": None, "n_char": 0}
    pno = 0

    def close_section():
        cur["end_para"] = pno if cur["start_para"] is not None else None
        sections.append(dict(cur))

    def new_section(level, heading):
        nonlocal cur
        if cur["start_para"] is not None or cur["heading"] != "(文首/无标题部分)":
            close_section()
        cur = {"id": f"SEC{len(sections) + 1}", "level": level, "heading": heading.strip(),
               "order": len(sections) + 1, "start_para": None, "end_para": None, "n_char": 0}

    for kind, level, text in blocks:
        if kind == "heading":
            new_section(level or 1, text)
            continue
        pno += 1
        pid = f"P{pno:03d}"
        if cur["start_para"] is None:
            cur["start_para"] = pno
        cur["n_char"] += len(text)
        sents = split_sentences(text)
        paragraphs.append({"id": pid, "section_id": cur["id"], "section": cur["heading"],
                           "index_in_section": (pno - cur["start_para"] + 1),
                           "text": text, "n_char": len(text), "n_sent": len(sents)})
        for si, s in enumerate(sents, 1):
            sentences.append({"id": f"{pid}-s{si}", "para_id": pid, "section_id": cur["id"],
                              "section": cur["heading"], "text": s})
    close_section()
    for s in sections:
        s["n_para"] = (s["end_para"] - s["start_para"] + 1) if s["start_para"] else 0

    body_chars = sum(s["n_char"] for s in sections)
    if not any(p["text"].strip() for p in paragraphs):
        issues.append("稿件解析后无任何正文段落")
    if len(sections) <= 1 and body_chars > 3000:
        issues.append("未识别到任何章节标题（按无标题平铺文本处理，结构类判断置信度下调）")

    model = {"source_file": source, "format": fmt, "sections": sections,
             "paragraphs": paragraphs, "sentences": sentences,
             "stats": {"n_sections": len([s for s in sections if s["level"] > 0]),
                       "n_paragraphs": len(paragraphs), "n_sentences": len(sentences),
                       "n_chars": body_chars},
             "issues": issues}
    return model

def detect_truncation(full_text, issues):
    tail = re.sub(r"\s+", "", full_text or "")[-30:]
    if tail and not re.search(r"[。！？!?.\]）)】\"'”’]$", tail):
        issues.append("稿件末尾无终结标点，疑似被截断（结论边界类判断需人工复核）")
        return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None, help="稿件路径；缺省取 inspection.json 第一候选")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    issues = []
    insp_path = os.path.join(args.work, "inspection.json")
    src, ext = args.file, None
    if not src:
        insp = {}
        if os.path.exists(insp_path):
            with open(insp_path, encoding="utf-8") as f:
                insp = json.load(f)
        cands = insp.get("manuscript_candidates") or []
        if not cands:
            print("[parse_manuscript][FATAL] 无稿件候选", file=sys.stderr)
            return 1
        src = cands[0]["path"]
    ext = os.path.splitext(src)[1].lower()

    blocks = []
    if ext == ".docx":
        try:
            blocks = docx_to_blocks(src)
        except Exception as e:
            issues.append(f"docx 解析失败: {e}（降级为纯文本抽取）")
            try:
                with zipfile.ZipFile(src) as z:
                    with z.open("word/document.xml") as f:
                        raw = f.read().decode("utf-8", "ignore")
                text = re.sub(r"<[^>]+>", "", raw)
                blocks = [("para", None, ln.strip()) for ln in text.splitlines() if ln.strip()]
            except Exception as e2:
                print(f"[parse_manuscript][FATAL] docx 无法读取: {e2}", file=sys.stderr)
                return 1
        full_text = "\n".join(b[2] for b in blocks)
    elif ext == ".pdf":
        try:
            r = subprocess.run(["pdftotext", "-layout", src, "-"],
                               capture_output=True, timeout=120)
            if r.returncode != 0 or not r.stdout.strip():
                raise RuntimeError(r.stderr.decode("utf-8", "ignore")[:200] or "空输出")
            full_text = r.stdout.decode("utf-8", "ignore")
            issues.append("PDF 经 pdftotext 抽取：版式、图表与公式可能丢失，相关判断按文本层进行")
        except Exception as e:
            print(f"[parse_manuscript][FATAL] PDF 抽取失败（pdftotext 不可用或文件损坏）: {e}",
                  file=sys.stderr)
            return 1
        blocks = None
    else:
        full_text, enc = read_text(src)
        if full_text is None:
            print(f"[parse_manuscript][FATAL] 无法读取 {src}", file=sys.stderr)
            return 1
        if enc != "utf-8":
            issues.append(f"稿件编码为 {enc}，已自动转码读取")
        blocks = None

    if blocks is None:  # md / tex / txt / pdf-text 统一走行级标题识别
        lines = full_text.splitlines()
        if ext == ".tex":
            lines = tex_to_lines(full_text)
        if ext == ".md":
            lines = parse_markdown(full_text)
        blocks, buf = [], []

        def flush():
            nonlocal buf
            para = " ".join(x.strip() for x in buf).strip()
            buf = []
            if para:
                blocks.append(("para", None, para))

        for line in lines:
            raw = line.rstrip()
            s = raw.strip()
            if ext == ".tex":
                m = RE_TEX_SEC.search(s)
                if m:
                    flush()
                    lvl = {"chapter": 1, "section": 1, "subsection": 2, "subsubsection": 3}[m.group(1)]
                    blocks.append(("heading", lvl, m.group(2)))
                    continue
            if ext == ".md":
                m = RE_MD_HEAD.match(s)
                if m:
                    flush()
                    blocks.append(("heading", len(m.group(1)), m.group(2)))
                    continue
            if not s:
                flush()
                continue
            kw = is_kw_heading(s)
            mnum = RE_NUM_HEAD.match(s)
            mcn = RE_CN_HEAD.match(s)
            menum = RE_CN_ENUM.match(s)
            if kw:
                flush()
                blocks.append(("heading", 1, kw))
            elif mnum and not s.endswith(("。", "！", "？", ".", "!", "?")):
                flush()
                lvl = mnum.group(1).count(".") + 1
                blocks.append(("heading", lvl, s))
            elif mcn and len(s) < 50:
                flush()
                blocks.append(("heading", 1, s))
            elif menum and len(s) < 45:
                flush()
                blocks.append(("heading", 1, s))
            else:
                buf.append(raw)
        flush()

    detect_truncation(full_text, issues)
    model = build_model(blocks, src, ext.lstrip("."), issues)

    os.makedirs(args.work, exist_ok=True)
    out = os.path.join(args.work, "structure.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)
    st = model["stats"]
    print(f"[parse_manuscript] {os.path.basename(src)} fmt={model['format']} "
          f"章节={st['n_sections']} 段落={st['n_paragraphs']} 句子={st['n_sentences']} 字符={st['n_chars']}")
    for iss in issues:
        print(f"[parse_manuscript][issue] {iss}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
