r"""pdf_extract.py — PDF 材料直通：文本抽取与 LaTeX 骨架重建（v2.0.2 增量，本版唯一机制改动）。

契约场景："PDF parsing receives the actual PDF without a pre-extracted answer layer"。
当材料只有论文 PDF（无 .tex 源）时，本脚本：
  1. 调系统 pdftotext（-layout）抽取全文 → work/pdf_text.txt；
     pdftotext 缺失则诚实记 exceptions 并退出（不伪造抽取结果）；
  2. 启发式重建章节骨架（标题/章节/参考文献条目）→ work/project/main.tex，
     公式、图片、作者信息等不可靠内容一律 TODO 占位并登记 manual_confirmations；
  3. 出 work/rebuild_map.json（章节→PDF 文本行号锚点）与 work/pdf_report.json。
重建原则是"可编译骨架 + 原文文本锚点"，不是逐字排版复原；数字与公式以 PDF 为唯一
事实来源，Agent 对照 pdf_text.txt 人工回填。

用法:
  python3 pdf_extract.py [--pdf <path>] [--work /app/work] [--project /app/work/project]
                         [--dir <skill根目录>]
参数读自 direction.json 的 pdf_extract 节（真被读取）。仅标准库 + 系统 pdftotext。
"""
import argparse, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))

HEAD_NUM = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+([A-Z\u4e00-\u9fff][^\n]{2,60})$")
HEAD_ROMAN = re.compile(r"^\s*([IVX]+)\.?\s+([A-Z][A-Za-z ]{3,60})$")
REF_HEAD = re.compile(r"^\s*(References|REFERENCES|Bibliography|参考文献)\s*$")
REF_ITEM = re.compile(r"^\s*\[?(\d{1,2})\]?\s*[.、]?\s*(.{10,})$")
CJK = re.compile(r"[一-鿿]")


def load_params(skill_dir):
    d = {"max_pdf_mb": 60, "min_heading_len": 3, "engine_hint": "auto",
         "class_zh": "ctexart", "class_en": "article"}
    try:
        user = (json.load(open(os.path.join(skill_dir, "direction.json"),
                               encoding="utf-8")).get("pdf_extract") or {})
        d.update({k: v for k, v in user.items() if k in d})
    except Exception:
        pass
    return d


def find_pdfs(project, work):
    pdfs = []
    for root in (project, work):
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [x for x in dirnames if not x.startswith(".")]
            for fn in filenames:
                if fn.lower().endswith(".pdf"):
                    pdfs.append(os.path.join(dirpath, fn))
    return sorted(set(pdfs))


def pdftotext(pdf, out_txt):
    if not shutil.which("pdftotext"):
        return False, "pdftotext 不可用"
    try:
        p = subprocess.run(["pdftotext", "-layout", pdf, out_txt], timeout=120,
                           stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT)
        if p.returncode == 0 and os.path.exists(out_txt) and os.path.getsize(out_txt) > 0:
            return True, "ok"
        return False, f"pdftotext rc={p.returncode}: {p.stdout.decode('utf-8','replace')[:200]}"
    except (subprocess.TimeoutExpired, OSError) as e:
        return False, str(e)


def parse_structure(text):
    lines = text.splitlines()
    sections, refs = [], []
    in_refs = False
    title = None
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue
        if title is None and len(line) > 4 and not HEAD_NUM.match(line):
            title = line
            continue
        if REF_HEAD.match(line):
            in_refs = True
            sections.append({"kind": "references_head", "line": i + 1, "text": line})
            continue
        if in_refs:
            m = REF_ITEM.match(line)
            if m:
                refs.append({"n": int(m.group(1)), "line": i + 1, "text": m.group(2)[:200]})
            continue
        m = HEAD_NUM.match(line) or HEAD_ROMAN.match(line)
        if m and len(m.group(2)) >= 3:
            sections.append({"kind": "section", "line": i + 1,
                             "num": m.group(1), "title": m.group(2).strip()})
    return title, sections, refs


def tex_escape(s):
    """抽取文本转义 LaTeX 特殊字符（骨架内联文本必须可编译）。"""
    s = s.replace("\\", r"\textbackslash{}")
    for a, b in (("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                 ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")):
        s = s.replace(a, b)
    return s


def build_skeleton(title, sections, refs, text, params, pdf_name):
    zh = bool(CJK.search(text[:3000]))
    docclass = params["class_zh"] if zh else params["class_en"]
    lines = text.splitlines()
    out = [f"% 由 pdf_extract.py 从 {pdf_name} 重建的骨架（TODO 处需人工对照 pdf_text.txt 回填）",
           f"\\documentclass{{{docclass}}}",
           "\\usepackage{amsmath}", "\\usepackage{graphicx}", "\\usepackage{booktabs}",
           ""]
    if zh and docclass == "article":
        out.insert(2, "\\usepackage{ctex}")
    out += [f"\\title{{{tex_escape(title) if title else 'TODO-Title'}}}",
            "% TODO(人工确认): 作者信息见 PDF 首页，回填下行",
            "\\author{TODO-Author}",
            "\\date{}", "\\begin{document}", "\\maketitle", ""]
    # 摘要段（标题后首个长段落）
    body_start = 0
    for i, raw in enumerate(lines[:60]):
        if len(raw.strip()) > 80:
            body_start = i
            break
    if body_start:
        out += ["\\begin{abstract}", "% TODO(人工确认): 以下摘要为 PDF 文本抽取，需核对",
                tex_escape(lines[body_start].strip()[:500]), "\\end{abstract}", ""]
    sec_idx = 0
    for s in sections:
        if s["kind"] == "references_head":
            continue
        sec_idx += 1
        out.append(f"\\section{{{tex_escape(s['title'])}}}  % 锚点: pdf_text.txt 第{s['line']}行")
        # 抽取该节首段作为锚点文本（至多 400 字符）
        l0 = s["line"]
        grabbed = []
        for raw in lines[l0:l0 + 12]:
            t = raw.strip()
            if not t:
                break
            if HEAD_NUM.match(t) or HEAD_ROMAN.match(t):
                break
            grabbed.append(t)
            if sum(len(g) for g in grabbed) > 400:
                break
        if grabbed:
            out.append("% TODO(人工确认): 本节以下为抽取文本锚点，公式/图/表需按 PDF 重建")
            out.append(tex_escape(" ".join(grabbed)[:400]))
        else:
            out.append("% TODO(人工确认): 本节内容见 pdf_text.txt 对应锚点")
        out.append("")
    if refs:
        out += ["\\begin{thebibliography}{99}",
                "% TODO(人工确认): 参考文献条目为 PDF 抽取文本，著录字段需逐条核对"]
        for r in refs[:30]:
            out.append(f"\\bibitem{{ref{r['n']:02d}}} {tex_escape(r['text'])}  % 锚点: 第{r['line']}行")
        out += ["\\end{thebibliography}", ""]
    out.append("\\end{document}")
    return "\n".join(out), zh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", default=None)
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--project", default=None)
    ap.add_argument("--dir", default=os.path.dirname(HERE))
    args = ap.parse_args()

    params = load_params(args.dir)
    project = args.project or os.path.join(args.work, "project")
    os.makedirs(args.work, exist_ok=True)
    os.makedirs(project, exist_ok=True)
    exceptions, manuals = [], []

    pdfs = [args.pdf] if args.pdf else find_pdfs(project, args.work)
    report = {"pdfs_found": pdfs, "status": "no_pdf", "skeleton": None,
              "exceptions": exceptions}
    if not pdfs:
        report["status"] = "no_pdf"
        json.dump(report, open(os.path.join(args.work, "pdf_report.json"), "w",
                               encoding="utf-8"), ensure_ascii=False, indent=2)
        print("[pdf_extract] 未发现 PDF 材料；若工程含 .tex 源，本步骤可跳过")
        return 0

    pdf = pdfs[0]
    if os.path.getsize(pdf) > params["max_pdf_mb"] * 1024 * 1024:
        exceptions.append({"where": "pdf_extract", "error": f"PDF 超过 {params['max_pdf_mb']}MB 上限"})
        report["status"] = "too_large"
    else:
        out_txt = os.path.join(args.work, "pdf_text.txt")
        ok, msg = pdftotext(pdf, out_txt)
        if not ok:
            exceptions.append({"where": "pdf_extract", "error": f"PDF 文本抽取失败: {msg}"})
            report["status"] = "extract_failed"
        else:
            text = open(out_txt, encoding="utf-8", errors="replace").read()
            title, sections, refs = parse_structure(text)
            skeleton, zh = build_skeleton(title, sections, refs, text, params,
                                          os.path.basename(pdf))
            main_path = os.path.join(project, "main.tex")
            existed = os.path.exists(main_path)
            if not existed:
                open(main_path, "w", encoding="utf-8").write(skeleton + "\n")
            rebuild = {"pdf": pdf, "text": "work/pdf_text.txt", "title": title,
                       "sections": sections, "references": refs,
                       "skeleton_written": not existed,
                       "skeleton_path": "project/main.tex"}
            json.dump(rebuild, open(os.path.join(args.work, "rebuild_map.json"), "w",
                                    encoding="utf-8"), ensure_ascii=False, indent=2)
            manuals.append({"item": "main.tex 骨架由 PDF 抽取重建：作者/公式/图表为 TODO 占位，"
                                    "须对照 work/pdf_text.txt 人工回填", "severity": "high",
                            "blocking": True})
            report.update({"status": "skeleton_built" if not existed else "kept_existing",
                           "skeleton": main_path, "title": title,
                           "sections": len(sections), "references": len(refs), "cjk": zh})
            print(f"[pdf_extract] 骨架{'已生成' if not existed else '未覆盖(已存在)'}: "
                  f"章节={len(sections)} 参考文献={len(refs)} 中文={zh}")

    json.dump(report, open(os.path.join(args.work, "pdf_report.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)
    # 异常与人工确认登记（与既有产物合并）
    for name, entries in (("exceptions.json", exceptions), ("manual_confirmations.json", manuals)):
        if not entries:
            continue
        p = os.path.join(args.work, name)
        old = []
        if os.path.exists(p):
            try:
                old = json.load(open(p, encoding="utf-8"))
            except Exception:
                old = []
        json.dump(old + entries, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    if report["status"] != "skeleton_built" and report["status"] != "kept_existing":
        print(f"[pdf_extract] 状态={report['status']}（已记 exceptions）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
