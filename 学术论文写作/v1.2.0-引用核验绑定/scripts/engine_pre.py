#!/usr/bin/env python3
"""engine_pre.py（引用核验方向）— 文献库构建：从全部材料解析参考文献条目 → library.json/md。
条目带 ref_key、作者/年份/刊名/DOI 尽力解析、字段完整性标记、材料锚点。纯标准库。"""
import argparse, json, os, re, subprocess, sys

DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
YEAR = re.compile(r"\b(19|20)\d{2}[a-z]?\b")

def pdf_text(path, dst):
    try:
        r = subprocess.run(["pdftotext", "-layout", path, dst], capture_output=True, timeout=120)
        return r.returncode == 0 and os.path.isfile(dst)
    except Exception:
        return False

def docx_lines(path):
    try:
        r = subprocess.run(["pandoc", "-t", "plain", "--wrap=none", path], capture_output=True, timeout=60)
        if r.returncode == 0: return r.stdout.decode("utf-8", "replace").splitlines()
    except Exception: pass
    try:
        import zipfile
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", "replace")
        return [t for t in ("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)) for p in xml.split("</w:p>")) if t.strip()]
    except Exception:
        return []

def parse_entries(lines, mid):
    """识别文献条目：含 DOI 的行，或 [n] 开头含年份的行，或 '作者. 题名. 刊名, 年' 样式的行；处理跨行续行。"""
    entries, seen = [], set()
    buf, buf_ln = "", 0
    def emit(raw, ln):
        raw = " ".join(raw.split()).strip(";")
        if len(raw) < 25 or not YEAR.search(raw): return
        key = raw[:120]
        if key in seen: return
        seen.add(key)
        doi = DOI.search(raw); yr = YEAR.search(raw)
        pre = re.sub(r"^\s*\[?\d{1,3}\]?[.\)、]?\s*", "", raw)
        authors = (pre.split("(")[0] if "(" in pre[:120] else pre).split(".")[0][:200].strip(" ,")
        vol = re.search(r"(19|20)\d{2}[,，]?\s*(\d+)\s*[（(]?(\d+)?[）)]?\s*[:：]\s*(\d+[-–—]\d+)?", raw)
        entries.append({"ref_key": f"R{len(entries)+1:03d}", "raw": raw[:600], "authors": authors,
                        "year": (yr.group(0) if yr else ""), "doi": (doi.group(0).rstrip(".") if doi else ""),
                        "venue_pages": (vol.group(0)[:60] if vol else ""),
                        "fields_complete": bool(doi and yr and authors),
                        "missing_fields": [x for x, ok in (("DOI", bool(doi)), ("年份", bool(yr)), ("作者", bool(authors)),
                                                            ("卷期页", bool(vol))) if not ok],
                        "source": f"{mid}#l{ln}"})
    for ln, line in enumerate(lines, 1):
        s = line.strip()
        if not s: continue
        starts_new = bool(re.match(r"^\s*\[?\d{1,3}\]?[.\)、]?\s*\S", s) and YEAR.search(s)) or bool(DOI.search(s))
        if starts_new:
            if buf: emit(buf, buf_ln)
            buf, buf_ln = s, ln
            if DOI.search(s) or len(s) > 80: emit(buf, ln); buf = ""
        elif buf and len(buf) < 480 and not re.match(r"^\s*\[?\d{1,3}\]?[.\)、]", s):
            buf += " " + s
        else:
            if buf: emit(buf, buf_ln); buf = ""
            # 无编号条目：作者起始 + 含年份 + 较长
            if YEAR.search(s) and len(s) > 60 and re.match(r"^[A-ZÀ-Þ一-鿿][\w\-一-鿿., ]{3,80}", s) and not DOI.search(s):
                emit(s, ln)
    if buf: emit(buf, buf_ln)
    return entries

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input"); ap.add_argument("--work", default="/app/work"); ap.add_argument("--out", default="/app/output")
    a = ap.parse_args()
    brief = {}
    bp = os.path.join(a.work, "brief.json")
    if os.path.isfile(bp):
        try: brief = json.load(open(bp, encoding="utf-8"))
        except Exception: pass
    tdir = os.path.join(a.work, "text"); os.makedirs(tdir, exist_ok=True)
    lib, notes = [], []
    for i, m in enumerate(brief.get("materials", [])):
        mid, ext, path = f"M{i+1:02d}", m.get("ext",""), m.get("path","")
        lines = []
        try:
            if ext == ".pdf":
                tp = os.path.join(tdir, f"{mid}.txt")
                if pdf_text(path, tp): lines = open(tp, encoding="utf-8", errors="replace").read().splitlines()
                else: notes.append(f"{mid} {m.get('rel')}: PDF 提取失败")
            elif ext in (".txt", ".md", ".bib", ".ris", ".json"):
                lines = open(path, encoding="utf-8", errors="replace").read(400000).splitlines()
                open(os.path.join(tdir, f"{mid}.txt"), "w", encoding="utf-8").write("\n".join(lines))
            elif ext in (".docx", ".doc"):
                lines = docx_lines(path)
                open(os.path.join(tdir, f"{mid}.txt"), "w", encoding="utf-8").write("\n".join(lines))
            elif ext in (".csv", ".tsv"):
                lines = open(path, encoding="utf-8", errors="replace").read(200000).splitlines()
                open(os.path.join(tdir, f"{mid}.txt"), "w", encoding="utf-8").write("\n".join(lines))
            elif ext in (".png", ".jpg", ".jpeg"):
                notes.append(f"{mid} {m.get('rel')}: 图片材料，无法解析文献条目")
        except Exception as e:
            notes.append(f"{mid}: 处理失败 {str(e)[:100]}")
        if lines: lib += parse_entries(lines, mid)
    for j, e in enumerate(lib): e["ref_key"] = f"R{j+1:03d}"
    json.dump(lib, open(os.path.join(a.work, "library.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(a.work, "library.md"), "w", encoding="utf-8") as f:
        f.write(f"# 文献库（{len(lib)} 条，引用的唯一来源）\n\n**红线：稿件引用只可使用本表条目；字段照抄 raw，缺失字段不补造。**\n\n")
        for e in lib[:150]:
            miss = f"　⚠缺:{'/'.join(e['missing_fields'])}" if e["missing_fields"] else ""
            f.write(f"- [{e['ref_key']}] ({e['source']}) {e['raw'][:260]}{miss}\n")
        if not lib: f.write("\n> 材料中未解析到文献条目：若任务要求引用，写入 uncertainty，不得虚构文献。\n")
        for n in notes: f.write(f"\n> 注意: {n}\n")
    with open(os.path.join(a.out, "run_log.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## engine_pre library refs={len(lib)} notes={len(notes)}\n")
    print(json.dumps({"ok": True, "references": len(lib), "notes": notes}, ensure_ascii=False))

if __name__ == "__main__":
    sys.exit(main())
