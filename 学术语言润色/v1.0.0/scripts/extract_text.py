#!/usr/bin/env python3
"""extract_text.py — 材料文本提取与分块分句：为逐句润色提供带稳定 ID 的源文本。

用法: python3 extract_text.py [--input-dir /input] [--work-dir /app/work]

输出:
  /app/work/source_segments.json  结构化段落/句子（含 ID、类型、语言）
  /app/work/source_dump.md        带 ID 的人类可读源文本（Agent 润色时对照用）
  /app/work/extract_report.json   每个文件的提取方式与失败原因（诚实记录）

依赖: 仅 Python 3.8+ 标准库；PDF 优先用 poppler 的 pdftotext，其次 PyMuPDF/pypdf（若已安装）。
不做任何润色或内容推断；提取失败的文件如实标注，不编造内容。
"""
import argparse, json, os, re, subprocess, sys, zipfile
import xml.etree.ElementTree as ET

try:
    from inspect_case import detect_encoding  # 同目录复用
except Exception:  # 直接以脚本路径调用时
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from inspect_case import detect_encoding

TEXT_EXT = {".txt", ".md", ".markdown", ".tex", ".rst", ".json", ".csv", ".tsv",
            ".html", ".htm", ".xml", ".bib", ".log", ".yaml", ".yml"}

# ---------- 保护片段：数学、引用、URL 在分句时不被切断 ----------
PROTECT_PATTERNS = [
    r"\$\$.*?\$\$",                          #  display math
    r"\$[^$\n]+?\$",                         #  inline math
    r"\\begin\{[^}]*\}.*?\\end\{[^}]*\}",   #  LaTeX 环境
    r"\\cite[tp]?\*?(?:\[[^\]]*\])?\{[^}]*\}",
    r"\\ref\{[^}]*\}", r"\\eqref\{[^}]*\}", r"\\label\{[^}]*\}",
    r"https?://[^\s)>\]]+",
    r"\[[0-9]+(?:\s*[-–,，]\s*[0-9]+)*\]",   #  数字引用 [1] [1,2] [1-3]
    r"\{[^{}\n]{1,60}\}",                   #  LaTeX 参数（保守）
]
PROTECT_RE = re.compile("(" + "|".join(f"(?:{p})" for p in PROTECT_PATTERNS) + ")", re.S)

ZH_END = "。！？；"
EN_ABBR = {"e.g", "i.e", "et al", "cf", "vs", "viz", "Fig", "Figs", "Tab", "Tabs",
           "Eq", "Eqs", "Sec", "No", "Dr", "Prof", "Mr", "Mrs", "Ms", "St", "Jr",
           "Sr", "approx", "ca", "ed", "eds", "vol", "pp", "par", "resp", "al"}


def mask_protected(text):
    spans = []

    def repl(m):
        spans.append(m.group(0))
        return f"\x00{len(spans)-1}\x00"

    return PROTECT_RE.sub(repl, text), spans


def unmask(text, spans):
    def repl(m):
        return spans[int(m.group(1))]

    return re.sub(r"\x00(\d+)\x00", repl, text)


def split_sentences(text):
    """把一段正文切成句子列表。保护片段不被切断；中英文分别处理。"""
    if not text.strip():
        return []
    masked, spans = mask_protected(text)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", masked))
    latin = len(re.findall(r"[A-Za-z]", masked))
    out, buf = [], []
    i, n = 0, len(masked)

    def flush():
        s = "".join(buf).strip()
        if s:
            out.append(unmask(s, spans))
        buf.clear()

    while i < n:
        ch = masked[i]
        buf.append(ch)
        if ch in ZH_END:
            flush()
        elif ch in ".!?":
            # 拉丁语境断句：后随空格+大写/引号/括号/数字，且非缩写、非小数
            tail = masked[i + 1:i + 8]
            prev = masked[max(0, i - 12):i]
            word_m = re.search(r"([A-Za-z]+)$", prev)
            word = word_m.group(1) if word_m else ""
            is_decimal = ch == "." and word and re.search(r"\d$", word)
            is_abbr = word in EN_ABBR or (word and len(word) == 1 and word.isupper())
            if (not is_decimal and not is_abbr and latin >= cjk
                    and re.match(r"\s+[A-Z0-9\"'(\[\u201c]", tail)):
                flush()
        i += 1
    flush()
    return [s for s in out if s]


def classify_block(line, in_yaml_front):
    s = line.strip()
    if not s:
        return "blank"
    if s.startswith("#") or re.match(r"^(第[一二三四五六七八九十百\d]+[章节部分篇]|[0-9]+(?:\.[0-9]+)*\s+\S|"
                                     r"\\(?:section|subsection|subsubsection|chapter|paragraph)\*?\{|"
                                     r"(Abstract|Introduction|Methods?|Results?|Discussion|Conclusion|References|"
                                     r"摘要|引言|绪论|方法|结果|讨论|结论|参考文献|致谢|附录)[:：]?\s*$)", s, re.I):
        return "heading"
    if re.match(r"^(图|表|插图|算法|Figure|Fig\.?|Table|Tab\.?|Algorithm)\s*\d+", s, re.I):
        return "caption"
    if s.startswith(("- ", "* ", "+ ")) or re.match(r"^\d+[.)]\s", s):
        return "list"
    if s.startswith("$$") or s.startswith("\\begin") or s.startswith("\\["):
        return "math"
    if s.startswith("|") and s.endswith("|"):
        return "table_row"
    if s.startswith("```"):
        return "fence"
    return "para"


def extract_docx(path):
    """标准库提取 docx 正文段落（含表格单元格），失败返回 None。"""
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paras = []
        for p in root.iter(ns + "p"):
            texts = [t.text or "" for t in p.iter(ns + "t")]
            line = "".join(texts).strip()
            if line:
                paras.append(line)
        return "\n".join(paras)
    except Exception:
        return None


def extract_pdf(path):
    """依次尝试 pdftotext / PyMuPDF / pypdf；全部失败返回 None。"""
    try:
        r = subprocess.run(["pdftotext", "-layout", path, "-"],
                           capture_output=True, timeout=120)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.decode("utf-8", errors="replace")
    except Exception:
        pass
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(path)
        txt = "\n".join(page.get_text() for page in doc)
        doc.close()
        if txt.strip():
            return txt
    except Exception:
        pass
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        txt = "\n".join((pg.extract_text() or "") for pg in reader.pages)
        if txt.strip():
            return txt
    except Exception:
        pass
    return None


def doc_language(text):
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if cjk == 0 and latin == 0:
        return "unknown"
    return "zh" if cjk >= latin else "en"


def segment_document(doc_id, text):
    """切成 blocks -> paragraphs -> sentences，分配稳定 ID。"""
    segments = []
    blocks, cur, in_fence, in_yaml = [], [], False, False
    lines = text.split("\n")
    for idx, line in enumerate(lines):
        if idx == 0 and line.strip() == "---":
            in_yaml = True
            continue
        if in_yaml:
            if line.strip() == "---":
                in_yaml = False
            continue
        if line.strip().startswith("```"):
            in_fence = not in_fence
            cur.append(line)
            continue
        if not in_fence and not line.strip():
            if cur:
                blocks.append("\n".join(cur))
                cur = []
        else:
            cur.append(line)
    if cur:
        blocks.append("\n".join(cur))

    for bi, block in enumerate(blocks, 1):
        lines_b = block.split("\n")
        kind = classify_block(lines_b[0].strip(), False)
        if kind in ("math", "fence"):
            seg = {"id": f"{doc_id}-B{bi}", "kind": kind, "doc": doc_id,
                   "text": block, "lang": doc_language(block),
                   "sentences": []}
            segments.append(seg)
            continue
        pi = 0
        for line in lines_b:
            s = line.rstrip()
            if not s.strip():
                continue
            pi += 1
            k = classify_block(s, False)
            if k in ("heading", "caption", "list", "table_row"):
                # 标题/图注/表格行/列表项作为整体句子
                seg = {"id": f"{doc_id}-B{bi}-P{pi}", "kind": k, "doc": doc_id,
                       "text": s.strip(), "lang": doc_language(s), "sentences": [s.strip()]}
                segments.append(seg)
            else:
                sents = split_sentences(s)
                seg = {"id": f"{doc_id}-B{bi}-P{pi}", "kind": k, "doc": doc_id,
                       "text": s.strip(), "lang": doc_language(s), "sentences": sents}
                segments.append(seg)
    return segments


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--work-dir", default="/app/work")
    args = ap.parse_args()

    brief_path = os.path.join(args.work_dir, "brief.json")
    brief = json.load(open(brief_path, encoding="utf-8")) if os.path.exists(brief_path) else {}

    report, all_segments = {}, []
    for m in brief.get("material_files", []):
        rel, path, ext = m["rel_path"], m["path"], m["ext"]
        if m.get("kind") != "text":
            report[rel] = {"status": "skipped", "reason": f"非文本类材料（{ext or '无扩展名'}）"}
            continue
        text, how = None, None
        if ext in TEXT_EXT:
            enc, note = detect_encoding(path)
            try:
                with open(path, "r", encoding=enc, errors="replace") as f:
                    text = f.read()
                how = f"纯文本({enc})"
                if note:
                    report.setdefault(rel, {})["encoding_note"] = note
            except Exception as e:
                report[rel] = {"status": "failed", "reason": f"读取失败: {e}"}
                continue
        elif ext == ".docx":
            text = extract_docx(path)
            how = "docx XML 解析(标准库)"
        elif ext == ".pdf":
            text = extract_pdf(path)
            how = "pdftotext/PyMuPDF/pypdf"
        if text is None:
            report[rel] = {"status": "failed",
                           "reason": "提取失败（工具链不可用或文件损坏），该材料如实标注为未处理"}
            continue
        doc_id = re.sub(r"[^A-Za-z0-9]+", "_", os.path.splitext(os.path.basename(rel))[0]) or "doc"
        segs = segment_document(doc_id, text)
        all_segments.extend(segs)
        n_sents = sum(len(s["sentences"]) for s in segs)
        report[rel] = {"status": "ok", "method": how, "blocks": len(segs),
                       "sentences": n_sents, "chars": len(text)}

    with open(os.path.join(args.work_dir, "source_segments.json"), "w", encoding="utf-8") as f:
        json.dump(all_segments, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.work_dir, "extract_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    with open(os.path.join(args.work_dir, "source_dump.md"), "w", encoding="utf-8") as f:
        f.write("# 源文本分句转写（带稳定 ID，供逐句润色对照）\n\n")
        f.write("> 本文件由 extract_text.py 机械转写，未经任何润色；ID 在全流程中保持稳定。\n\n")
        for seg in all_segments:
            if seg["kind"] in ("math", "fence"):
                f.write(f"## [{seg['id']}] ({seg['kind']})\n\n{seg['text']}\n\n")
            elif len(seg["sentences"]) <= 1:
                f.write(f"## [{seg['id']}] ({seg['kind']})\n\n{seg['text']}\n\n")
            else:
                f.write(f"## [{seg['id']}] ({seg['kind']})\n\n")
                for si, s in enumerate(seg["sentences"], 1):
                    f.write(f"- {seg['id']}-S{si}: {s}\n")
                f.write("\n")

    n_ok = sum(1 for v in report.values() if v.get("status") == "ok")
    n_fail = sum(1 for v in report.values() if v.get("status") == "failed")
    print(f"[extract_text] docs_ok={n_ok} docs_failed={n_fail} segments={len(all_segments)} "
          f"sentences={sum(len(s['sentences']) for s in all_segments)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
