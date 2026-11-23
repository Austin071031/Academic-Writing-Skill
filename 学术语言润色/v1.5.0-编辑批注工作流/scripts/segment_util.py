#!/usr/bin/env python3
"""segment_util.py — 一站式预检：解析输入、提取文本、分句、标注关键句、落盘 result.json 骨架。

用法: python3 segment_util.py [--input-dir /input] [--work-dir /app/work] [--output-dir /app/output]

关键句（写入 source_dump.md 的 【K】 标记与 segments 的 key=true）：
含数值/单位、引用编号、图表指向、限定词、否定词或因果词的句子——回译验证的对象。
"""
import argparse, datetime, json, os, re, subprocess, sys, zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from inspect_case import detect_encoding  # noqa: E402

TEXT_EXT = {".txt", ".md", ".markdown", ".tex", ".rst", ".json", ".csv", ".tsv",
            ".html", ".htm", ".xml", ".bib", ".log", ".yaml", ".yml"}

UNITS = r"%|°C|℃|nm|μm|µm|um|mm|cm|m|km|mg|g|kg|mL|L|mol|s|ms|μs|min|h|Hz|kHz|MHz|eV|keV|MeV|V|mV|kV|W|J|kJ|rpm|dB|ppb|ppm"
RE_NUM = re.compile(rf"\d+(?:\.\d+)?(?:\\?\s*(?:{UNITS}))")
RE_CITE = re.compile(r"\[[0-9]+(?:\s*[-–,，]\s*[0-9]+)*\]|\\cite[tp]?\*?(?:\[[^\]]*\])?\{[^}]*\}|"
                     r"\([A-Z][A-Za-z\-]+(?:\s+et\s+al\.?)?,?\s+(?:19|20)\d{2}[a-z]?\)")
RE_PTR = re.compile(r"(?:图|表|插图|算法|式|公式|Figure|Fig\.?|Table|Tab\.?|Algorithm|Eq\.?|"
                    r"Equation|Section|Sec\.?)\s*(?:[0-9]+(?:\.[0-9]+)?)")
HEDGES = ["证明", "证实", "必然", "肯定", "毫无疑问", "表明", "显示", "说明", "揭示", "显著",
          "可能", "或许", "有望", "提示", "初步", "约", "大致", "一定程度上",
          "prove", "confirm", "definitively", "establish", "must", "suggest", "indicate",
          "show", "demonstrate", "reveal", "support", "consistent with", "may", "might",
          "could", "possibly", "potentially", "likely", "appear", "seem", "tend",
          "preliminary", "approximately", "roughly", "partially"]
RE_NEG = re.compile(r"不|未|无|非(?!常|凡|洲)|没有|难以|\b(?:not|no|never|neither|without|fails?|absence|cannot|unable)\b", re.I)
RE_CAUS = re.compile(r"导致|引起|决定|致使|归因于|使得|相关|关联|伴随|"
                     r"\b(?:cause[sd]?|lead(?:s|ing)? to|led to|result\w+ in|due to|owing to|attribut\w+ to|"
                     r"correlat\w+|associat\w+|consistent with)\b", re.I)


def is_key(s):
    low = s.lower()
    return bool(RE_NUM.search(s) or RE_CITE.search(s) or RE_PTR.search(s)
                or any(h in low for h in HEDGES) or RE_NEG.search(s) or RE_CAUS.search(s))


PROTECT_RE = re.compile(r"(\$\$.*?\$\$|\$[^$\n]+?\$|\\begin\{[^}]*\}.*?\\end\{[^}]*\}|"
                        r"\\cite[tp]?\*?(?:\[[^\]]*\])?\{[^}]*\}|\\ref\{[^}]*\}|\\eqref\{[^}]*\}|"
                        r"https?://[^\s)>\]]+|\[[0-9]+(?:\s*[-–,，]\s*[0-9]+)*\])", re.S)
ZH_END = "。！？；"
EN_ABBR = {"e.g", "i.e", "et al", "cf", "vs", "Fig", "Figs", "Tab", "Eq", "Eqs", "Sec",
           "No", "Dr", "Prof", "Mr", "Mrs", "Ms", "St", "Jr", "approx", "al"}


def split_sentences(text):
    if not text.strip():
        return []
    spans = []

    def repl(m):
        spans.append(m.group(0))
        return f"\x00{len(spans)-1}\x00"

    masked = PROTECT_RE.sub(repl, text)
    cjk = len(re.findall(r"[一-鿿]", masked))
    latin = len(re.findall(r"[A-Za-z]", masked))
    out, buf = [], []
    i = 0

    def flush():
        s = "".join(buf).strip()
        if s:
            out.append(re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], s))
        buf.clear()

    while i < len(masked):
        ch = masked[i]
        buf.append(ch)
        if ch in ZH_END:
            flush()
        elif ch in ".!?":
            tail = masked[i + 1:i + 8]
            prev = masked[max(0, i - 12):i]
            m = re.search(r"([A-Za-z]+)$", prev)
            word = m.group(1) if m else ""
            if (word not in EN_ABBR and not (ch == "." and word.isdigit())
                    and not (word and len(word) == 1 and word.isupper())
                    and latin >= cjk and re.match(r"\s+[A-Z0-9\"'(\[\u201c]", tail)):
                flush()
        i += 1
    flush()
    return out


def classify(line):
    s = line.strip()
    if not s:
        return "blank"
    if s.startswith("#") or re.match(r"^(第[一二三四五六七八九十百\d]+[章节部分篇]|[0-9]+(?:\.[0-9]+)*\s+\S|"
                                     r"\\(?:section|subsection|subsubsection|chapter)\*?\{|"
                                     r"(Abstract|Introduction|Methods?|Results?|Discussion|Conclusion|References|"
                                     r"摘要|引言|绪论|方法|结果|讨论|结论|参考文献|致谢|附录)[:：]?\s*$)", s, re.I):
        return "heading"
    if re.match(r"^(图|表|插图|算法|Figure|Fig\.?|Table|Tab\.?|Algorithm)\s*\d+", s, re.I):
        return "caption"
    if s.startswith(("- ", "* ", "+ ")) or re.match(r"^\d+[.)]\s", s):
        return "list"
    if s.startswith("$$") or s.startswith("\\begin") or s.startswith("\\["):
        return "math"
    if s.startswith("|"):
        return "table_row"
    if s.startswith("```"):
        return "fence"
    return "para"


def doc_language(t):
    cjk = len(re.findall(r"[一-鿿]", t))
    return "zh" if cjk >= len(re.findall(r"[A-Za-z]", t)) else "en"


def extract_docx(path):
    try:
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("word/document.xml"))
        ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        return "\n".join("".join(t.text or "" for t in p.iter(ns + "t")).strip()
                         for p in root.iter(ns + "p") if "".join(t.text or "" for t in p.iter(ns + "t")).strip())
    except Exception:
        return None


def extract_pdf(path):
    try:
        r = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, timeout=120)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.decode("utf-8", errors="replace")
    except Exception:
        pass
    for mod in ("fitz", "pypdf"):
        try:
            if mod == "fitz":
                import fitz
                doc = fitz.open(path)
                txt = "\n".join(pg.get_text() for pg in doc)
                doc.close()
            else:
                from pypdf import PdfReader
                txt = "\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages)
            if txt.strip():
                return txt
        except Exception:
            continue
    return None


def segment_document(doc_id, text):
    segments, blocks, cur, in_fence, in_yaml = [], [], [], False, False
    for idx, line in enumerate(text.split("\n")):
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
        kind = classify(lines_b[0].strip())
        if kind in ("math", "fence"):
            segments.append({"id": f"{doc_id}-B{bi}", "kind": kind, "doc": doc_id,
                             "text": block, "lang": doc_language(block), "sentences": []})
            continue
        for pi, line in enumerate(lines_b, 1):
            s = line.rstrip()
            if not s.strip():
                continue
            k = classify(s)
            if k in ("heading", "caption", "list", "table_row"):
                sents = [s.strip()]
            else:
                sents = split_sentences(s)
            segments.append({"id": f"{doc_id}-B{bi}-P{pi}", "kind": k, "doc": doc_id,
                             "text": s.strip(), "lang": doc_language(s),
                             "sentences": sents, "keys": [is_key(x) for x in sents]})
    return segments


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--work-dir", default="/app/work")
    ap.add_argument("--output-dir", default="/app/output")
    args = ap.parse_args()
    os.makedirs(args.work_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)

    # case 解析
    case, issues = {}, []
    try:
        case = json.load(open(os.path.join(args.input_dir, "case.json"), encoding="utf-8"))
    except Exception as e:
        issues.append(f"case.json 读取失败: {e}")
    case_id = case.get("case_id") or case.get("id") or "unknown"
    contract = case.get("output_contract") or case.get("outputContract") or case.get("outputs") or {}
    task_text = ""
    tp = os.path.join(args.input_dir, "task.md")
    if os.path.exists(tp):
        task_text = open(tp, encoding="utf-8", errors="replace").read()
    else:
        issues.append("task.md 不存在")

    materials, segments, report = [], [], {}
    for root, dirs, files in os.walk(args.input_dir):
        dirs.sort()
        for fn in sorted(files):
            if fn in ("case.json", "task.md"):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, args.input_dir)
            ext = os.path.splitext(fn)[1].lower()
            text, how = None, None
            if ext in TEXT_EXT:
                enc, note = detect_encoding(p)
                try:
                    text = open(p, encoding=enc, errors="replace").read()
                    how = f"纯文本({enc})"
                    if note:
                        issues.append(f"{rel}: {note}")
                except Exception as e:
                    report[rel] = {"status": "failed", "reason": str(e)}
                    continue
            elif ext == ".docx":
                text, how = extract_docx(p), "docx XML(标准库)"
            elif ext == ".pdf":
                text, how = extract_pdf(p), "pdftotext/PyMuPDF/pypdf"
            else:
                report[rel] = {"status": "skipped", "reason": f"不支持格式 {ext}"}
                issues.append(f"{rel}: 格式 {ext or '(无扩展名)'} 无法提取，已标注为未处理")
                continue
            if text is None:
                report[rel] = {"status": "failed", "reason": "提取失败（工具链不可用或文件损坏）"}
                issues.append(f"{rel}: 文本提取失败，标注为未处理")
                continue
            doc_id = re.sub(r"[^A-Za-z0-9]+", "_", os.path.splitext(os.path.basename(rel))[0]) or "doc"
            segs = segment_document(doc_id, text)
            segments.extend(segs)
            materials.append(rel)
            report[rel] = {"status": "ok", "method": how,
                           "sentences": sum(len(s["sentences"]) for s in segs)}
    if not materials:
        issues.append("未发现可提取文本的材料文件")

    json.dump(segments, open(os.path.join(args.work_dir, "source_segments.json"), "w",
                             encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(report, open(os.path.join(args.work_dir, "extract_report.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(args.work_dir, "source_dump.md"), "w", encoding="utf-8") as f:
        f.write("# 源文本分句转写（带稳定 ID；【K】=关键句，modify 后必须回译验证）\n\n")
        for seg in segments:
            if seg["kind"] in ("math", "fence") or not seg["sentences"]:
                f.write(f"## [{seg['id']}] ({seg['kind']})\n\n{seg['text']}\n\n")
            elif len(seg["sentences"]) == 1:
                k = " 【K】" if seg["keys"][0] else ""
                f.write(f"## [{seg['id']}]{k} ({seg['kind']})\n\n{seg['sentences'][0]}\n\n")
            else:
                f.write(f"## [{seg['id']}] ({seg['kind']})\n\n")
                for i, (s, k) in enumerate(zip(seg["sentences"], seg["keys"]), 1):
                    f.write(f"- {seg['id']}-S{i}{' 【K】' if k else ''}: {s}\n")
                f.write("\n")

    brief = {"case_id": case_id, "output_contract": contract,
             "output_contract_keys": list(contract.keys()) if isinstance(contract, dict) else contract,
             "materials": materials, "task_length_chars": len(task_text), "issues": issues}
    json.dump(brief, open(os.path.join(args.work_dir, "brief.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    oc = ({k: {"spec": v, "delivered": None, "null_reason": "处理中，尚未填充"}
           for k, v in contract.items()} if isinstance(contract, dict) else {})
    result = {"case_id": case_id, "status": "in_progress",
              "generated_by": "academic-polish-backtranslation (weekly-skill)",
              "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "output_contract": oc, "artifacts": {}, "sources": materials,
              "assumptions": [], "uncertainty": issues, "manual_review_required": []}
    json.dump(result, open(os.path.join(args.output_dir, "result.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)

    n_key = sum(1 for s in segments for k in s.get("keys", []) if k)
    n_s = sum(len(s["sentences"]) for s in segments)
    print(f"[segment_util] case_id={case_id} sentences={n_s} key={n_key} "
          f"materials={len(materials)} issues={len(issues)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
