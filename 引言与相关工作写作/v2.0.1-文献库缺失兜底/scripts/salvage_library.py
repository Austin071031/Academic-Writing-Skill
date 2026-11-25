#!/usr/bin/env python3
"""salvage_library.py — 文献库兜底：当 parse_library 未得到任何条目时，
从稿件参考文献段（reference_list 段落）与笔记文本中抢救文献记录，写入 work/library.json。

用法: python3 salvage_library.py --work /app/work
幂等：library.json 已有非空 records 时直接跳过（no-op）。
支持的条目形态（尽力而为，解析置信度写入 salvage_confidence）：
  [1] 张三, 李四. 题名[J]. 刊名, 2023, 10(2): 100-108.   （GB/T 7714 / CNKI）
  [1] Author A, Author B. Title. Journal, 2023, 10: 100-108.（编号英文）
  1. Author. Title. Venue. 2023.                          （数字加点）
  Author, A. (2023). Title. Journal, 10(2), 100-108.      （APA 近似）
"""
import argparse, json, os, re, sys

NUM_PREFIX = re.compile(r"^\s*(?:\[(\d+)\]|(\d+)[.)、])\s*(.+)$", re.S)
TYPE_MARK = re.compile(r"\[(J|C|M|D|P|S|R|EB/OL|Z)\]")
YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def parse_entry(text, idx):
    t = re.sub(r"\s+", " ", text).strip()
    mark = TYPE_MARK.search(t)
    entry_type = {"J": "journal_article", "C": "conference_paper", "M": "book",
                  "D": "thesis", "P": "patent", "S": "standard", "R": "report",
                  "EB/OL": "preprint"}.get(mark.group(1) if mark else None, "misc")
    years = YEAR.findall(t)
    year = int(years[-1]) if years else None
    # 拆分作者. 题名. 其余
    segs = [s.strip() for s in re.split(r"(?<=[.。])\s+", t) if s.strip()]
    authors, title, venue = [], "", ""
    if len(segs) >= 2:
        first = segs[0].rstrip(".。")
        # 作者段判定：含逗号分隔的人名片段，且不含年份
        if not YEAR.search(first) and len(first) <= 200:
            authors = [a.strip() for a in re.split(r"[,，;；]", first) if a.strip()][:8]
            segs = segs[1:]
    if segs:
        title = segs[0].rstrip(".。")
        if mark:
            title = title.split("[")[0].strip().rstrip(".。")
        segs = segs[1:]
    if segs:
        rest = ". ".join(segs)
        venue = rest.split(",")[0].split("，")[0].strip().rstrip(".。")
        venue = re.sub(r"^(见[:：]|In[:：])\s*", "", venue)[:120]
    vol = issue = pages = ""
    m = re.search(r"(\d+)\s*\((\d+(?:[-–]\d+)?)\)\s*[:：]\s*([\d\-–]+)", t)
    if m:
        vol, issue, pages = m.group(1), m.group(2), m.group(3)
    else:
        m2 = re.search(r",\s*(\d+)\s*[:：]\s*([\d\-–]+)", t)
        if m2:
            vol, pages = m2.group(1), m2.group(2)
    conf = "high" if (authors and title and year and venue) else \
           "medium" if (title and (year or venue)) else "low"
    return {"id": f"R{idx:03d}", "source_file": "salvaged", "source_index": idx,
            "raw_format": "salvaged_reference_list", "entry_type": entry_type,
            "title": title, "authors": authors, "year": year, "venue": venue,
            "volume": vol, "issue": issue, "pages": pages, "doi": "",
            "language": "zh" if re.search(r"[\u4e00-\u9fff]", t) else "en",
            "salvage_confidence": conf, "raw": t[:400]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    lib_path = os.path.join(args.work, "library.json")
    lib = load_json(lib_path, {}) or {}
    if lib.get("records"):
        print(f"[salvage] 已有文献记录 {len(lib['records'])} 条，跳过（no-op）")
        return 0

    texts = []
    ms = load_json(os.path.join(args.work, "manuscript.json"), {}) or {}
    for p in ms.get("paragraphs", []):
        if p.get("kind") == "reference_list":
            texts.append(p.get("text", ""))
    if not texts:
        nt = load_json(os.path.join(args.work, "notes.json"), {}) or {}
        for src in nt.get("sources", []):
            for p in src.get("paragraphs", []):
                if NUM_PREFIX.match(p.get("text", "")[:200]):
                    texts.append(p.get("text", ""))
    if not texts:
        print("[salvage] 稿件无参考文献段、笔记无编号条目，无法抢救", file=sys.stderr)
        return 0

    records = []
    for t in texts:
        # 单段含多条时按 [n] 或换行切分
        chunks = re.split(r"(?=\[\d+\]\s*\S)", t) if t.count("[") > 1 and re.search(r"\[\d+\]", t) else [t]
        for c in chunks:
            m = NUM_PREFIX.match(c.strip())
            body = m.group(3) if m else c.strip()
            if len(body) < 15:
                continue
            rec = parse_entry(body, len(records) + 1)
            if rec["salvage_confidence"] == "low" and not rec["title"]:
                continue
            records.append(rec)

    out = {"records": records, "n_records": len(records),
           "salvaged": True, "note": "由 salvage_library.py 从稿件/笔记参考文献段抢救，字段置信度见 salvage_confidence"}
    with open(lib_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    hi = sum(1 for r in records if r["salvage_confidence"] == "high")
    print(f"[salvage] 抢救文献 {len(records)} 条（高置信 {hi}）-> {lib_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
