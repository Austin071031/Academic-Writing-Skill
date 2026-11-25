#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fact_ledger.py --work W

从 work/materials.json 抽取事实台账 → work/fact_ledger.json + fact_ledger.md。
类型：number / citation / pub_mention / term / abbrev / year。
去重键 = type + value + unit。F0001.. 顺序编号，幂等可重跑。
"""
import argparse
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "fact_ledger"
CTX = 60  # context ±60 字

DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'）)，。；]+")
GRANT_NO_RE = re.compile(
    r"(?:批准号|项目号|课题号|Grant\s*No\.?|No\.?)\s*[:：]?\s*[A-Za-z]{0,4}\d{5,}", re.I)
PATENT_RE = re.compile(r"(?:ZL\s*[\d.]+|[一二三四五六七八九十\d]+年[\w]{0,6}专利|发明专利|实用新型专利)")
JOURNAL_HINT_RE = re.compile(
    r"\b(?:Vol\.?\s*\d|pp?\.?\s*\d)|卷|第\d+期|页|"
    r"\b(?:J\.|Acta|Science|Nature|Joule|Cell|Advanced|Energy|Materials|Nano|Phys|Chem)\w*", re.I)
YEAR_RE = re.compile(r"(?<![\w.])(?:19|20)\d{2}(?![\w.])")
TERM_ABBR_FULL = re.compile(r"([A-Za-z][A-Za-z0-9-]{1,20})\s*[（(]([^（）()]{2,40})[）)]")
TERM_FULL_ABBR = re.compile(r"([一-鿿][一-鿿\w·（）()、/\s-]{1,30}?)\s*[（(]([A-Za-z][A-Za-z0-9-]{1,20})[）)]")
ABBR_RE = re.compile(r"(?<![A-Za-z])[A-Z][A-Z0-9]{2,}(?![A-Za-z])")


def ctx(text, start, end):
    a = max(0, start - CTX)
    b = min(len(text), end + CTX)
    return text[a:b].replace("\n", " ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    work = args.work
    gu.ensure_dir(work)

    materials = gu.read_json(os.path.join(work, "materials.json"), None)
    if not isinstance(materials, dict) or "files" not in materials:
        gu.record_exception(work, STAGE, "materials.json",
                            "缺失或结构不符", "写空台账")
        gu.write_json(os.path.join(work, "fact_ledger.json"), {"entries": []})
        return 0

    entries = []
    seen = set()  # type+value+unit

    def add(type_, value, unit, context, file_id, pid, sec):
        key = (type_, str(value).strip(), gu.norm_unit(unit))
        if key in seen or not str(value).strip():
            return
        seen.add(key)
        entries.append({
            "fid": f"F{len(entries) + 1:04d}",
            "type": type_, "value": str(value).strip(),
            "unit": gu.norm_unit(unit), "context": context[:2 * CTX + 80],
            "source": {"file_id": file_id, "pid": pid}, "sec": sec})

    abbrev_counter = Counter()
    abbrev_first = {}  # abbr -> (file_id, pid, sec, context)

    for fentry in materials["files"]:
        file_id = fentry.get("file_id", "F?")
        for p in fentry.get("paragraphs", []):
            text = p.get("text", "")
            pid, sec = p.get("pid", ""), p.get("sec", "")
            # 1) 数字（含单位/百分数/万、亿/科学计数）
            for n in gu.extract_numbers(text):
                pos = text.find(n["raw"])
                add("number", n["value"], n["unit"],
                    ctx(text, pos, pos + len(n["raw"])), file_id, pid, sec)
            # 2) 年份
            for m in YEAR_RE.finditer(text):
                add("year", m.group(0), "年", ctx(text, m.start(), m.end()),
                    file_id, pid, sec)
            # 3) 引用标记
            for c in gu.extract_citations(text):
                pos = text.find(c)
                add("citation", c, "", ctx(text, max(pos, 0), max(pos, 0) + len(c)),
                    file_id, pid, sec)
            # 4) 论文/成果线索 pub_mention
            for m in DOI_RE.finditer(text):
                add("pub_mention", m.group(0).rstrip(".,;:："), "DOI",
                    ctx(text, m.start(), m.end()), file_id, pid, sec)
            for m in GRANT_NO_RE.finditer(text):
                add("pub_mention", m.group(0).strip(), "基金号",
                    ctx(text, m.start(), m.end()), file_id, pid, sec)
            for m in PATENT_RE.finditer(text):
                add("pub_mention", m.group(0).strip(), "专利",
                    ctx(text, m.start(), m.end()), file_id, pid, sec)
            for m in JOURNAL_HINT_RE.finditer(text):
                # 期刊论文线索：宽松匹配到的词
                add("pub_mention", m.group(0).strip(), "期刊线索",
                    ctx(text, m.start(), m.end()), file_id, pid, sec)
            # 5) 术语定义对：缩写（全称）/ 全称（缩写）
            for m in TERM_ABBR_FULL.finditer(text):
                add("term", f"{m.group(1)}（{m.group(2)}）", "",
                    ctx(text, m.start(), m.end()), file_id, pid, sec)
            for m in TERM_FULL_ABBR.finditer(text):
                add("term", f"{m.group(1).strip()}（{m.group(2)}）", "",
                    ctx(text, m.start(), m.end()), file_id, pid, sec)
            # 6) 大写缩写计数（≥3 字母，全文出现 ≥2 次才收录）
            for m in ABBR_RE.finditer(text):
                a = m.group(0)
                abbrev_counter[a] += 1
                if a not in abbrev_first:
                    abbrev_first[a] = (file_id, pid, sec,
                                       ctx(text, m.start(), m.end()))

    for abbr, cnt in sorted(abbrev_counter.items()):
        if cnt >= 2:
            file_id, pid, sec, context = abbrev_first[abbr]
            add("abbrev", abbr, f"x{cnt}", context, file_id, pid, sec)

    gu.write_json(os.path.join(work, "fact_ledger.json"), {"entries": entries})

    # fact_ledger.md：按文件分组
    lines = ["# 事实台账（fact_ledger）", "",
             "> Agent 写作时用〔F0001〕标记引用以下条目；未在台账的事实禁止写入稿件。", ""]
    by_file = {}
    for e in entries:
        by_file.setdefault(e["source"]["file_id"], []).append(e)
    for fid, es in sorted(by_file.items()):
        path = next((f.get("path") for f in materials["files"]
                     if f.get("file_id") == fid), fid)
        lines += [f"## {fid} {path}", ""]
        for e in es:
            unit = f" {e['unit']}" if e["unit"] else ""
            lines.append(f"- **{e['fid']}** ({e['type']}{unit}) `{e['value']}` — {e['context']}")
        lines.append("")
    with open(os.path.join(work, "fact_ledger.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[fact_ledger] entries={len(entries)} "
          f"types={dict(Counter(e['type'] for e in entries))}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[fact_ledger] ERROR: {e}")
        raise SystemExit(1)
