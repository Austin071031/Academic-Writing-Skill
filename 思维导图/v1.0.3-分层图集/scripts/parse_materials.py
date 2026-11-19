#!/usr/bin/env python3
"""parse_materials.py — 把 /input 下全部材料解析为带稳定编号的单元索引。

用法: python3 parse_materials.py [--work /app/work] [--inspection /app/work/inspection.json]
输出:
  work/materials.json      — {materials:[{mid,rel,format,pages,units:[{uid,sid,kind,text,page}]}]}
  work/materials_digest.md — 给 Agent 用的压缩目录（标题树 + 每段首句 + 单元号）
单元号稳定: M01-S01-P003。kind ∈ heading/paragraph/list/table/code/caption。
PDF 经 pdftotext（按 \\f 分页保留页码）; docx 经 zipfile 解 XML；其余按文本处理。
只依赖标准库；任何失败材料记入 exceptions 并继续。
"""
import argparse, json, os, re, subprocess, sys, zipfile, html as _html

MAX_UNIT = 2000       # 单元字符上限（超出截断并标记）
MAX_MATERIAL_CHARS = 600_000

H_ATX = re.compile(r"^(#{1,6})\s+(.*)$")
H_NUM = re.compile(r"^(\d+(?:\.\d+){0,3})[\.、\s]\s*(\S.{0,80})$")
H_CN = re.compile(r"^(第[一二三四五六七八九十百\d]+[章节篇部分]|[一二三四五六七八九十]+、)\s*(.{0,80})$")
H_KW = re.compile(r"^(摘要|关键词|关键字|引言|结论|参考文献|附录|Abstract|Keywords?|Introduction|Conclusion|References|Appendix|Acknowledg\w*)\s*[:：]?\s*$", re.I)
LIST_LINE = re.compile(r"^\s*([-*•·]|\d+[\.、\)])\s+")
TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")

def read_text(path):
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read(MAX_MATERIAL_CHARS), enc, None
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError as e:
            return None, None, str(e)
    return None, None, "所有候选编码均解码失败"

def extract_pdf(path):
    """返回 [(page_no, text), ...]；失败返回 (None, err)。"""
    try:
        r = subprocess.run(["pdftotext", "-enc", "UTF-8", path, "-"],
                           capture_output=True, timeout=120)
        if r.returncode != 0:
            return None, f"pdftotext 退出码 {r.returncode}: {r.stderr.decode('utf-8','replace')[:200]}"
        text = r.stdout.decode("utf-8", "replace")
    except FileNotFoundError:
        return None, "环境无 pdftotext"
    except Exception as e:
        return None, f"pdftotext 异常: {e}"
    pages = text.split("\f")
    out = []
    for i, p in enumerate(pages, 1):
        p = p.strip()
        if p:
            out.append((i, p))
    if not out:
        return None, "pdftotext 输出为空（可能为扫描件，需 OCR）"
    return out, None

def extract_docx(path):
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except Exception as e:
        return None, f"docx 解析失败: {e}"
    xml = re.sub(r"</w:p>", "\n\n", xml)
    xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    return html_unescape(xml), None

def html_unescape(t):
    return _html.unescape(t)

def strip_tex(t):
    t = re.sub(r"\\(section|subsection|subsubsection)\*?\{([^{}]*)\}",
               lambda m: "\n" + "#" * {"section": 1, "subsection": 2, "subsubsection": 3}[m.group(1)]
               + " " + m.group(2) + "\n", t)
    t = re.sub(r"\\(begin|end)\{[^{}]*\}", "\n", t)
    t = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{[^{}]*\})?", " ", t)
    return t

def strip_html(t):
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|section|article)>", "\n", t)
    t = re.sub(r"(?i)<h([1-6])[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return html_unescape(t)

def heading_level(line):
    m = H_ATX.match(line)
    if m:
        return min(len(m.group(1)), 6), m.group(2).strip()
    m = H_NUM.match(line)
    if m and len(line) < 90:
        return min(m.group(1).count(".") + 1, 6), line.strip()
    m = H_CN.match(line)
    if m and len(line) < 90:
        return 1, line.strip()
    m = H_KW.match(line.strip())
    if m:
        return 1, line.strip()
    return None, None

def segment(text, mid, page_of_line=None):
    """把纯文本切分为单元。page_of_line: 可选，函数（行索引->页码）。"""
    units = []
    sid = 0
    pi = 0
    buf = []

    def flush(page):
        nonlocal pi, buf
        para = " ".join(x.strip() for x in buf).strip()
        buf = []
        if not para:
            return
        pi += 1
        kind = "paragraph"
        if LIST_LINE.match(para):
            kind = "list"
        elif TABLE_LINE.match(para):
            kind = "table"
        truncated = len(para) > MAX_UNIT
        if truncated:
            para = para[:MAX_UNIT] + " …[截断]"
        units.append({"uid": f"{mid}-S{sid:02d}-P{pi:03d}", "sid": sid,
                      "kind": kind, "text": para, "page": page,
                      "truncated": truncated})

    lines = text.splitlines()
    cur_page = 1
    for li, raw in enumerate(lines):
        if page_of_line is not None:
            cur_page = page_of_line(li)
        line = raw.rstrip()
        if not line.strip():
            flush(cur_page)
            continue
        lv, title = heading_level(line.strip())
        if lv is not None and not buf:
            sid += 1
            pi = 0
            units.append({"uid": f"{mid}-S{sid:02d}-H", "sid": sid, "kind": "heading",
                          "level": lv, "text": title[:200], "page": cur_page})
            continue
        if lv is not None and buf:
            flush(cur_page)
            sid += 1
            pi = 0
            units.append({"uid": f"{mid}-S{sid:02d}-H", "sid": sid, "kind": "heading",
                          "level": lv, "text": title[:200], "page": cur_page})
            continue
        buf.append(line)
    flush(cur_page)
    if sid == 0 and units:  # 无标题材料：归入 S01
        for u in units:
            u["sid"] = 1
            u["uid"] = u["uid"].replace("-S00-", "-S01-")
    return units

def parse_one(entry, mid):
    path, rel, ext = entry["path"], entry["rel"], entry["ext"]
    mat = {"mid": mid, "rel": rel, "format": ext.lstrip(".") or "txt",
           "pages": None, "units": [], "error": None}
    if ext == ".pdf":
        pages, err = extract_pdf(path)
        if err:
            mat["error"] = err
            return mat
        mat["pages"] = len(pages)
        for pno, ptext in pages:
            for u in segment(ptext, mid):
                u["page"] = pno
                u["uid"] = u["uid"]  # uid 在 segment 内按页生成会重复，下面统一重编
                mat["units"].append(u)
        # 统一重编 sid/pi（跨页连续）
        new_units, sid, pi = [], 0, 0
        for u in mat["units"]:
            if u["kind"] == "heading":
                sid += 1
                pi = 0
            else:
                if sid == 0:
                    sid = 1
                pi = pi + 1
            u["sid"] = sid
            if u["kind"] == "heading":
                u["uid"] = f"{mid}-S{sid:02d}-H"
            else:
                u["uid"] = f"{mid}-S{sid:02d}-P{pi:03d}"
            new_units.append(u)
        mat["units"] = new_units
        return mat
    if ext == ".docx":
        text, err = extract_docx(path)
        if err:
            mat["error"] = err
            return mat
    else:
        text, enc, err = read_text(path)
        if err:
            mat["error"] = err
            return mat
        mat["encoding"] = enc
        if ext == ".tex":
            text = strip_tex(text)
        elif ext in (".html", ".htm"):
            text = strip_html(text)
    mat["units"] = segment(text, mid)
    return mat

def first_sentence(t, n=60):
    t = re.sub(r"\s+", " ", t).strip()
    m = re.split(r"(?<=[。！？.!?])\s*", t, maxsplit=1)
    s = m[0]
    return s[:n] + ("…" if len(s) > n else "")

def make_digest(materials):
    lines = ["# 材料目录（单元号为溯源锚点）", ""]
    for mat in materials:
        head = f"## {mat['mid']}  {mat['rel']}  ({mat['format']}"
        if mat.get("pages"):
            head += f", {mat['pages']} 页"
        head += ")"
        lines.append(head)
        if mat.get("error"):
            lines.append(f"- ⚠ 解析失败: {mat['error']}")
            lines.append("")
            continue
        for u in mat["units"]:
            if u["kind"] == "heading":
                indent = "  " * (u.get("level", 1) - 1)
                pg = f"(p{u['page']})" if u.get("page") else ""
                lines.append(f"{indent}- **{u['uid']}** {u['text']} {pg}")
            else:
                pg = f"(p{u['page']})" if u.get("page") else ""
                lines.append(f"  - {u['uid']}[{u['kind']}]{pg} {first_sentence(u['text'])}")
        lines.append("")
    return "\n".join(lines)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--inspection", default=None)
    args = ap.parse_args()
    insp_path = args.inspection or os.path.join(args.work, "inspection.json")
    try:
        with open(insp_path, encoding="utf-8") as f:
            insp = json.load(f)
    except Exception as e:
        sys.exit(f"[parse_materials] 读取 inspection.json 失败: {e}")

    materials = []
    exceptions = []
    for i, entry in enumerate(insp.get("material_files", []), 1):
        mid = f"M{i:02d}"
        mat = parse_one(entry, mid)
        if mat.get("error"):
            exceptions.append({"stage": "parse_materials", "material": entry["rel"],
                               "error": mat["error"], "action": "跳过该材料，继续处理其余材料"})
        materials.append(mat)

    out = {"materials": materials,
           "stats": {"n_materials": len(materials),
                     "n_units": sum(len(m["units"]) for m in materials),
                     "n_failed": sum(1 for m in materials if m.get("error"))}}
    with open(os.path.join(args.work, "materials.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.work, "materials_digest.md"), "w", encoding="utf-8") as f:
        f.write(make_digest(materials))
    if exceptions:
        ep = os.path.join(args.work, "exceptions.json")
        old = []
        if os.path.exists(ep):
            try:
                old = json.load(open(ep, encoding="utf-8"))
            except Exception:
                old = []
        with open(ep, "w", encoding="utf-8") as f:
            json.dump(old + exceptions, f, ensure_ascii=False, indent=2)
    s = out["stats"]
    print(f"[parse_materials] 材料={s['n_materials']} 单元={s['n_units']} "
          f"失败={s['n_failed']} -> materials.json / materials_digest.md")
    return 0

if __name__ == "__main__":
    sys.exit(main())
