#!/usr/bin/env python3
"""parse_source.py — 解析源文/事实材料为结构化段落与事实清单，生成 work/source.json。

用法: python3 parse_source.py <源文文件...> [--work /app/work] [--lang zh|en]
支持 md/txt/tex（docx/pdf 请先用 pdftotext 等转为 txt 后传入）。
输出 source.json:
  paragraphs: [{pid, kind(heading/body/list/figure_note/table_note/quote), text,
                facts:[{type, raw, span}]}]
  fact_index: 全部事实的扁平清单（含 pid 溯源）
  acronyms:   [{raw, count, first_pid, expanded(bool)}]
  term_candidates: [{term, count, kind(zh_term/latin/acronym)}]
  stats: {n_paragraphs, n_facts, n_chars}
事实类型: number(带单位数值) / percent / sample(样本量) / figure_ref / table_ref /
          year / compare(比较表述) / conclusion(结论句标记)
"""
import argparse, json, os, re, sys

UNIT = r"(?:mS/cm|S/cm|mS·cm(?:[-−][0-9])?|g/cm3|g·cm[-−]?3|kg/m3|nm|μm|mm|cm|km|mA|mV|kV|V|mAh/g|mAh·g[-−]?1|Wh/kg|W/kg|MPa|GPa|kPa|Pa|K|℃|°C|mol/L|mM|MΩ|Ω|Hz|kHz|MHz|GHz|ms|s|min|h|mL|μL|L|mg|μg|g|kg|wt%|vol%|at%|ppm|ppb|nmol|μmol|mmol|mol|J|kJ|mJ|eV|keV|mV/s|rpm|MPa·?m½|GPa·?m½|倍|%|‰)"
NUM = r"[-+−]?\d+(?:\.\d+)?(?:\s*[×xX]\s*10(?:\^|[-−])?[0-9]+)?(?:\s*[–~〜-]\s*[-+]?\d+(?:\.\d+)?)?"

RE_NUMBER_UNIT = re.compile(r"(%s)\s*(%s)" % (NUM, UNIT))
RE_PERCENT = re.compile(r"(%s)\s*(?:%%|‰|百分比)" % NUM)
RE_SAMPLE = re.compile(r"(?:n\s*=|N\s*=|样本量[是为：:]?\s*|共\s*)(\d{1,6})\s*(?:例|只|个|篇|组|名|份|株|条|samples?|subjects?|cases?)?", re.I)
RE_FIGREF = re.compile(r"(图\s*\d+(?:[-–.]\d+)*[a-zA-Z]?(?:\s*[-–,，、]\s*\d+)*|Fig\.?\s*\d+(?:[-–.]\d+)*[a-zA-Z]?|Figure\s*\d+(?:[-–.]\d+)*)")
RE_TABREF = re.compile(r"(表\s*\d+(?:[-–.]\d+)*(?:\s*[-–,，、]\s*\d+)*|Table\s*\d+(?:[-–.]\d+)*)")
RE_YEAR = re.compile(r"((?:19|20)\d{2})\s*年?")
RE_COMPARE = re.compile(r"(%s)\s*(%s)?\s*(高于|低于|优于|相当于|是|达|达到|提升|提高|降低|下降|增加|减少|超出|相当于)[^，。；;,.]{0,30}" % (NUM, UNIT))
RE_CONCLUSION = re.compile(r"(表明|证实|证明|显示|发现|实现|首次|突破|解决了|显著提高|显著降低|有望|初步表明|提示|demonstrat\w+|show(?:s|ed|n)?\s+that|achiev\w+|reveal\w+)", re.I)
RE_ACRONYM = re.compile(r"\b[A-Z][A-Z0-9]{1,9}(?:[-/][A-Z0-9]+)*\b")
RE_ZH_TERM = re.compile(r"[一-鿿]{3,10}(?:材料|电池|电解质|电极|模型|算法|蛋白|基因|细胞|体系|结构|界面|机制|器件|催化|合成|表征|性能|效应|通路|网络|光谱|晶体|合金|薄膜|纳米|复合)")
RE_ACR_EXPAND = re.compile(r"([一-鿿A-Za-z][一-鿿A-Za-z /·-]{1,30}?)[（(]\s*([A-Z][A-Z0-9]{1,9})\s*[)）]")

KIND_HEADING = "heading"

def classify_para(text):
    s = text.strip()
    if re.match(r"^#{1,6}\s", s) or re.match(r"^(第[一二三四五六七八九十0-9]+[章节部分]|[0-9]+(\.[0-9]+)*[、.．\s])", s):
        return KIND_HEADING
    if re.match(r"^\s*[-*•▪◦]\s", s) or re.match(r"^\s*\d+[、.）)]\s*\S", s):
        return "list"
    if re.match(r"^(图|Fig\.?|Figure)\s*\d+", s):
        return "figure_note"
    if re.match(r"^(表|Table)\s*\d+", s):
        return "table_note"
    if s.startswith(">"):
        return "quote"
    return "body"

def extract_facts(text):
    facts = []
    def add(ftype, m, raw=None):
        facts.append({"type": ftype, "raw": raw if raw is not None else m.group(0).strip(),
                      "span": [m.start(), m.end()]})
    for m in RE_NUMBER_UNIT.finditer(text):
        add("number", m)
    for m in RE_PERCENT.finditer(text):
        add("percent", m)
    for m in RE_SAMPLE.finditer(text):
        add("sample", m)
    for m in RE_FIGREF.finditer(text):
        add("figure_ref", m)
    for m in RE_TABREF.finditer(text):
        add("table_ref", m)
    for m in RE_COMPARE.finditer(text):
        add("compare", m)
    for m in RE_CONCLUSION.finditer(text):
        add("conclusion", m)
    # 年份去重（与 number 重叠的年份不算 number）
    for m in RE_YEAR.finditer(text):
        span = (m.start(1), m.end(1))
        facts.append({"type": "year", "raw": m.group(1), "span": list(span)})
    facts.sort(key=lambda f: f["span"])
    return facts

def split_paragraphs(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", text)
    paras = []
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        # 去掉 markdown 标题符号但保留文本
        clean = re.sub(r"^#{1,6}\s*", "", b)
        paras.append(clean)
    return paras

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--lang", default=None)
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    paragraphs = []
    issues = []
    total_chars = 0
    pcount = 0
    for si, path in enumerate(args.files, 1):
        if not os.path.exists(path):
            issues.append(f"源文文件不存在: {path}")
            continue
        text = None
        for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
            try:
                with open(path, encoding=enc) as f:
                    text = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue
            except OSError as e:
                issues.append(f"无法读取 {path}: {e}")
                text = None
                break
        if text is None:
            continue
        total_chars += len(text)
        for p in split_paragraphs(text):
            pcount += 1
            pid = f"S{si:03d}-P{pcount:03d}"
            paragraphs.append({"pid": pid, "source_file": os.path.basename(path),
                               "kind": classify_para(p), "text": p,
                               "facts": extract_facts(p)})

    fact_index = []
    for p in paragraphs:
        for f in p["facts"]:
            fact_index.append({"pid": p["pid"], "type": f["type"], "raw": f["raw"]})

    full_text = "\n".join(p["text"] for p in paragraphs)
    expanded = {m.group(2): m.group(1).strip() for m in RE_ACR_EXPAND.finditer(full_text)}
    acr_count = {}
    acr_first = {}
    for p in paragraphs:
        for m in RE_ACRONYM.finditer(p["text"]):
            a = m.group(0)
            if a in ("I", "A", "II", "III", "IV", "V", "X"):
                continue
            acr_count[a] = acr_count.get(a, 0) + 1
            acr_first.setdefault(a, p["pid"])
    acronyms = [{"raw": a, "count": c, "first_pid": acr_first[a],
                 "expanded": a in expanded, "expansion": expanded.get(a)}
                for a, c in sorted(acr_count.items(), key=lambda kv: -kv[1])]

    zh_count = {}
    for p in paragraphs:
        for m in RE_ZH_TERM.finditer(p["text"]):
            t = m.group(0)
            zh_count[t] = zh_count.get(t, 0) + 1
    term_candidates = [{"term": t, "count": c, "kind": "zh_term"}
                       for t, c in sorted(zh_count.items(), key=lambda kv: -kv[1]) if c >= 2][:60]
    for a in acronyms[:40]:
        term_candidates.append({"term": a["raw"], "count": a["count"], "kind": "acronym"})

    out = {"paragraphs": paragraphs, "fact_index": fact_index,
           "acronyms": acronyms, "term_candidates": term_candidates,
           "stats": {"n_paragraphs": len(paragraphs), "n_facts": len(fact_index),
                     "n_chars": total_chars},
           "issues": issues}
    op = os.path.join(args.work, "source.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[parse_source] 段落={len(paragraphs)} 事实={len(fact_index)} "
          f"缩写={len(acronyms)} 术语候选={len(term_candidates)} 字符={total_chars}")
    for i in issues:
        print(f"[parse_source][issue] {i}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
