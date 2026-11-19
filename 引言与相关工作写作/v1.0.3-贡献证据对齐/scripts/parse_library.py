#!/usr/bin/env python3
"""parse_library.py — 把多种格式的文献库统一解析为规范化记录。

支持: BibTeX(.bib) / RIS(.ris) / EndNote Export(.enw) / ISI(.ciw,.nbib) /
CNKI 或 GB/T 编号纯文本 / CSV / JSON。输出 work/library.json。

用法: python3 parse_library.py <library文件...> [--work /app/work] [--out-name library.json]
每条记录字段: id, source_file, source_index, raw_format, entry_type, title, authors[],
year, venue, volume, issue, pages, doi, language, raw, field_presence{}
"""
import argparse, json, os, re, sys, csv, io

# ---------- 通用工具 ----------

def detect_cjk(s):
    return bool(re.search(r"[\u4e00-\u9fff]", s or ""))

def split_authors(s):
    """拆分作者字符串。优先 'and' (BibTeX)、分号；中文按 ',' '，' 但避开 '等'。"""
    if not s:
        return []
    s = s.strip().rstrip(".")
    parts = re.split(r"\s+and\s+|[;；]", s, flags=re.I)
    out = []
    for p in parts:
        p = p.strip()
        if not p or p.lower() in ("et al", "et al."):
            continue
        # 中文逗号分隔的多作者: 张三, 李四, 王五
        if detect_cjk(p) and "，" in p:
            out.extend([x.strip() for x in p.split("，") if x.strip()])
        else:
            out.append(p)
    return [a for a in out if a]

def norm_type(raw, fmt):
    t = (raw or "").lower().strip()
    m = {
        "article|journal|j|jour|jfull": "journal_article",
        "conference|proceedings|inproceedings|c|conf|cpaper|confproc": "conference_paper",
        "preprint|arxiv": "preprint",
        "book|monograph|m|b": "book",
        "inbook|incollection|chapter|chap": "book_chapter",
        "thesis|dissertation|d|thes|phdthesis|mastersthesis": "thesis",
        "patent|p|pat": "patent",
        "standard|s": "standard",
        "report|r|rprt|techreport": "report",
        "misc|generic|web|online|eb|gen": "misc",
        "dataset": "dataset",
    }
    for pat, val in m.items():
        if re.fullmatch(rf"({pat})", t):
            return val
    return "misc"

# ---------- BibTeX ----------

def parse_bibtex(text):
    entries = []
    # 去掉注释
    text = re.sub(r"(?m)^%.*$", "", text)
    for m in re.finditer(r"@([A-Za-z]+)\s*\{", text):
        etype = m.group(1)
        depth, i = 1, m.end()
        while i < len(text) and depth:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[m.end():i - 1]
        entries.append((etype, body))
    recs = []
    for etype, body in entries:
        key = body.split(",", 1)[0].strip() if "," in body else body.strip()
        fields = {}
        rest = body.split(",", 1)[1] if "," in body else ""
        for fm in re.finditer(r"([A-Za-z][A-Za-z0-9_\-]*)\s*=\s*", rest):
            name = fm.group(1).lower()
            start = fm.end()
            if start < len(rest) and rest[start] == "{":
                depth, j = 1, start + 1
                while j < len(rest) and depth:
                    if rest[j] == "{":
                        depth += 1
                    elif rest[j] == "}":
                        depth -= 1
                    j += 1
                val = rest[start + 1:j - 1]
            else:
                jm = re.search(r"[,\n]", rest[start:])
                j = start + (jm.start() if jm else len(rest[start:]))
                val = rest[start:j].strip().strip('"')
            fields[name] = re.sub(r"\s+", " ", val).strip()
        ym = re.search(r"(19|20)\d{2}", fields.get("year", ""))
        recs.append({
            "entry_type": norm_type(etype, "bibtex"),
            "title": fields.get("title", ""),
            "authors": split_authors(fields.get("author", "")),
            "year": ym.group(0) if ym else None,
            "venue": fields.get("journal") or fields.get("booktitle") or fields.get("publisher", ""),
            "volume": fields.get("volume", ""), "issue": fields.get("number") or fields.get("issue", ""),
            "pages": (fields.get("pages", "") or "").replace("--", "-"),
            "doi": (fields.get("doi", "") or "").replace("https://doi.org/", "").strip(),
            "key": key, "extra_fields": {k: v for k, v in fields.items() if k not in
                ("title", "author", "year", "journal", "booktitle", "publisher", "volume",
                 "number", "issue", "pages", "doi")},
        })
    return recs

# ---------- RIS ----------

RIS_MAP = {"TI": "title", "T1": "title", "CT": "title",
           "AU": "authors", "A1": "authors", "A2": "authors",
           "PY": "year", "Y1": "year", "DA": "year",
           "JO": "venue", "JF": "venue", "JA": "venue", "T2": "venue", "BT": "venue",
           "VL": "volume", "IS": "issue", "SP": "pages", "EP": "pages_end",
           "DO": "doi", "SN": "issn", "UR": "url", "AB": "abstract", "KW": "keywords",
           "N1": "note", "PB": "publisher", "ET": "edition", "ID": "ref_id"}

def parse_ris(text):
    recs, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])  -\s?(.*)$", line.rstrip())
        if m:
            tag, val = m.group(1), m.group(2).strip()
            if tag == "TY":
                cur = {"entry_type_raw": val, "_authors": [], "_kw": [], "_pages_start": ""}
                continue
            if tag == "ER":
                if cur:
                    recs.append(cur); cur = None
                continue
            if cur is None:
                continue
            field = RIS_MAP.get(tag)
            if field == "authors":
                cur["_authors"].append(val)
            elif field == "keywords":
                cur["_kw"].append(val)
            elif field == "pages":
                cur["_pages_start"] = val
            elif field == "pages_end":
                cur["_pages_end"] = val
            elif field:
                cur[field] = val
        elif cur is not None and line.strip() and "  - " not in line[:6]:
            # 续行
            for k in ("title", "abstract", "venue"):
                if k in cur:
                    cur[k] += " " + line.strip()
    out = []
    for r in recs:
        ps = r.pop("_pages_start", "")
        pe = r.pop("_pages_end", "")
        pages = f"{ps}-{pe}".strip("-") if pe else ps
        yr = r.get("year", "")
        ym = re.search(r"(19|20)\d{2}", yr)
        out.append({
            "entry_type": norm_type(r.pop("entry_type_raw", ""), "ris"),
            "title": r.pop("title", ""), "authors": r.pop("_authors", []),
            "year": ym.group(0) if ym else None,
            "venue": r.pop("venue", ""), "volume": r.pop("volume", ""),
            "issue": r.pop("issue", ""), "pages": pages,
            "doi": (r.pop("doi", "") or "").replace("https://doi.org/", ""),
            "extra_fields": {k: v for k, v in r.items() if not k.startswith("_") and k not in ("year",)},
        })
    return out

# ---------- EndNote (%X) / ISI ----------

def parse_endnote(text):
    recs, cur = [], {}
    for line in text.splitlines():
        m = re.match(r"^%([A-Z0-9])\s?(.*)$", line.rstrip())
        if m:
            tag, val = m.group(1), m.group(2).strip()
            if tag == "0" and cur:
                recs.append(cur); cur = {}
            cur.setdefault(tag, []).append(val)
        elif cur and line.strip():
            cur[list(cur.keys())[-1]][-1] += " " + line.strip()
    if cur:
        recs.append(cur)
    def g(rec, *tags):
        for t in tags:
            if t in rec:
                return "; ".join(rec[t])
        return ""
    out = []
    for r in recs:
        ym = re.search(r"(19|20)\d{2}", g(r, "D"))
        out.append({
            "entry_type": norm_type(g(r, "0"), "endnote"),
            "title": g(r, "T"), "authors": split_authors(g(r, "A")),
            "year": ym.group(0) if ym else None,
            "venue": g(r, "J", "B", "S"), "volume": g(r, "V"), "issue": g(r, "N"),
            "pages": (g(r, "P") or "").replace("--", "-"),
            "doi": (g(r, "R") or "").replace("https://doi.org/", ""),
            "url": g(r, "U"), "extra_fields": {"note": g(r, "Z", "X"), "keywords": g(r, "K")},
        })
    return out

# ---------- CNKI / GB/T / 编号纯文本 ----------

CNKI_TYPE_TAG = re.compile(r"\[([JCMDSNRP])\]")

def parse_numbered_text(text):
    """解析 '[1] 作者. 题名[J]. 刊名, 2020, 12(3): 45-50.' 风格条目（CNKI/GB/T 导出）。"""
    # 切分条目起始: 行首 [n] 或 [n] 紧跟内容
    chunks = re.split(r"(?m)(?=^\s*\[\d+\]\s*)", text)
    out = []
    for ch in chunks:
        ch = ch.strip()
        if not ch:
            continue
        ch = re.sub(r"^\[\d+\]\s*", "", ch)
        ch = re.sub(r"\s+", " ", ch)
        tmatch = CNKI_TYPE_TAG.search(ch)
        etype = {"J": "journal_article", "C": "conference_paper", "M": "book",
                 "D": "thesis", "S": "standard", "N": "misc", "R": "report",
                 "P": "patent"}.get(tmatch.group(1), "misc") if tmatch else "misc"
        # 题名: 第一个类型标记前的最后一个 '. ' 之后
        title = ""
        if tmatch:
            before = ch[:tmatch.start()]
            segs = re.split(r"[.．]\s*", before)
            title = segs[-1].strip() if segs else ""
        else:
            segs = re.split(r"[.．]\s*", ch)
            title = segs[1].strip() if len(segs) > 1 else segs[0].strip()
        # 作者: 题名前的段
        authors = []
        if tmatch:
            before = ch[:tmatch.start()]
            segs = re.split(r"[.．]\s*", before)
            if len(segs) >= 2:
                authors = split_authors(segs[-2])
        ym = re.search(r"(19|20)\d{2}", ch)
        doi_m = re.search(r"(?:doi[:：]?\s*)?(10\.\d{4,9}/\S+)", ch, re.I)
        venue = ""
        if tmatch:
            after = ch[tmatch.end():].lstrip(".．,， ")
            vsegs = re.split(r"[,，]", after, 1)
            venue = vsegs[0].strip() if vsegs else ""
        vol_m = re.search(r"(\d+)\s*\((\d+)\)", ch)
        pages_m = re.search(r"[:：]\s*([A-Za-z]?\d+(?:[-–—][A-Za-z]?\d+)?)\s*[.。]?\s*$", ch)
        out.append({
            "entry_type": etype, "title": title.strip("[JCMDSNRP] .，,"),
            "authors": authors, "year": ym.group(0) if ym else None,
            "venue": venue, "volume": vol_m.group(1) if vol_m else "",
            "issue": vol_m.group(2) if vol_m else "",
            "pages": (pages_m.group(1).replace("–", "-").replace("—", "-") if pages_m else ""),
            "doi": doi_m.group(1).rstrip(".。") if doi_m else "",
            "extra_fields": {},
        })
    return out

# ---------- CSV / JSON ----------

def parse_csv(text):
    out = []
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        low = {k.lower().strip(): (v or "").strip() for k, v in row.items() if k}
        title = low.get("title") or low.get("题名") or low.get("ti") or ""
        if not title:
            continue
        ym = re.search(r"(19|20)\d{2}", low.get("year", "") + low.get("年份", "") + low.get("date", ""))
        out.append({
            "entry_type": norm_type(low.get("type") or low.get("文献类型") or "", "csv"),
            "title": title,
            "authors": split_authors(low.get("authors") or low.get("作者") or low.get("author") or ""),
            "year": ym.group(0) if ym else None,
            "venue": low.get("venue") or low.get("journal") or low.get("刊名") or low.get("source") or "",
            "volume": low.get("volume") or low.get("卷") or "",
            "issue": low.get("issue") or low.get("number") or low.get("期") or "",
            "pages": (low.get("pages") or low.get("页码") or "").replace("–", "-"),
            "doi": (low.get("doi") or "").replace("https://doi.org/", ""),
            "extra_fields": {k: v for k, v in low.items() if k not in
                ("title", "题名", "authors", "作者", "author", "year", "年份", "date",
                 "venue", "journal", "刊名", "source", "volume", "卷", "issue", "number",
                 "期", "pages", "页码", "doi", "type", "文献类型")},
        })
    return out

def parse_json(text):
    data = json.loads(text)
    items = data if isinstance(data, list) else data.get("records") or data.get("references") or data.get("items") or []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        low = {k.lower(): v for k, v in it.items()}
        title = low.get("title") or low.get("题名") or ""
        if not title:
            continue
        auth = low.get("authors") or low.get("author") or low.get("作者") or []
        if isinstance(auth, str):
            auth = split_authors(auth)
        ym = re.search(r"(19|20)\d{2}", str(low.get("year") or low.get("年份") or ""))
        out.append({
            "entry_type": norm_type(str(low.get("type") or low.get("entry_type") or ""), "json"),
            "title": title, "authors": [str(a) for a in auth],
            "year": ym.group(0) if ym else None,
            "venue": str(low.get("venue") or low.get("journal") or low.get("刊名") or ""),
            "volume": str(low.get("volume") or ""), "issue": str(low.get("issue") or low.get("number") or ""),
            "pages": str(low.get("pages") or "").replace("–", "-"),
            "doi": str(low.get("doi") or "").replace("https://doi.org/", ""),
            "extra_fields": {k: str(v) for k, v in low.items() if k not in
                ("title", "题名", "authors", "author", "作者", "year", "年份", "type",
                 "entry_type", "venue", "journal", "刊名", "volume", "issue", "number",
                 "pages", "doi")},
        })
    return out

PARSERS = {"bibtex": parse_bibtex, "ris": parse_ris, "endnote": parse_endnote,
           "cnki_or_gbt": parse_numbered_text, "numbered_plain": parse_numbered_text,
           "csv": parse_csv, "json": parse_json, "isi": parse_ris, "plain": parse_numbered_text}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out-name", default="library.json")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    all_records, issues = [], []
    for path in args.files:
        if not os.path.exists(path):
            issues.append(f"文献库文件不存在: {path}")
            continue
        raw = None
        for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
            try:
                with open(path, encoding=enc) as f:
                    raw = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue
        if raw is None:
            issues.append(f"无法解码: {path}")
            continue
        head = raw[:4000]
        if "@" in head[:200] and re.search(r"@\w+\s*\{", head):
            fmt = "bibtex"
        elif re.search(r"^TY  -", head, re.M):
            fmt = "ris"
        elif re.search(r"^%[A-Z0-9] ", head, re.M):
            fmt = "endnote"
        elif re.search(r"\[[JCMDSNRP]\]", head):
            fmt = "cnki_or_gbt"
        elif path.lower().endswith(".csv"):
            fmt = "csv"
        elif path.lower().endswith(".json") or head.lstrip().startswith(("[", "{")):
            fmt = "json"
        else:
            fmt = "numbered_plain"
        try:
            recs = PARSERS.get(fmt, parse_numbered_text)(raw)
        except Exception as e:
            issues.append(f"{path} 解析异常({fmt}): {e}")
            recs = []
        for i, r in enumerate(recs):
            r["id"] = f"R{len(all_records)+1:03d}"
            r["source_file"] = os.path.basename(path)
            r["source_index"] = i + 1
            r["raw_format"] = fmt
            r["language"] = "zh" if detect_cjk((r.get("title") or "") + (r.get("venue") or "")) else "en"
            r["year"] = r.get("year") or None
            r["raw"] = ""
            fp = {k: bool(r.get(k)) for k in ("title", "authors", "year", "venue",
                                              "volume", "issue", "pages", "doi")}
            fp["n_authors"] = len(r.get("authors") or [])
            r["field_presence"] = fp
            all_records.append(r)
        print(f"[parse_library] {os.path.basename(path)}: {len(recs)} 条 ({fmt})")

    lib = {"records": all_records, "issues": issues,
           "count": len(all_records)}
    out = os.path.join(args.work, args.out_name)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)
    print(f"[parse_library] 共 {len(all_records)} 条 -> {out}")
    for iss in issues:
        print(f"[parse_library][issue] {iss}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
