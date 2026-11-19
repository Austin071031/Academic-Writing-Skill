#!/usr/bin/env python3
"""extract_facts.py — 事实底稿与文献库。

产出（--work 下）：
  facts.json        每条事实：fact_id、value（原文数值串）、unit、context、source(material_id#locator)
                    来源：CSV 列统计 + 原始行值、文本材料中含数值/单位的句子
  bibliography.json 解析到的文献条目：ref_key、raw、authors/year/venue/doi（尽力解析）、source
  facts_digest.md   限长事实摘要，供写作时直接取用
写作红线支撑：稿件中的数字必须能在 facts.json 或材料锚点中找到。仅用标准库。
"""
import argparse, json, os, re, sys, csv, datetime, statistics

NUM = r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?(?:[eE][-+]?\d+)?"
NUM_SENT_RE = re.compile(
    r"[^。\n.!?]{0,160}?(?:\d+\.\d+|\d+%|\d+\s*(?:mg|g|kg|μg|ug|mL|ml|L|mm|cm|m|km|nm|μm|um|"
    r"mol|mM|μM|uM|nM|Hz|kHz|MHz|GHz|V|mV|A|mA|W|kW|J|kJ|Pa|kPa|MPa|GPa|K|℃|°C|s|ms|min|h|"
    r"eV|keV|MeV|GeV|GPa|nM|pM|bp|kb|Da|kDa|g/mol|rpm|CFU|cells?|mM|ppm|ppb|"
    r"p\s*[<=>]\s*0?\.\d+|n\s*=\s*\d+|N\s*=\s*\d+|r\s*=\s*0?\.\d+|R[²2]\s*=\s*0?\.\d+|"
    r"SD|SEM|CI|±|±\s*\d))[^。\n]{0,160}?")
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")
YEAR_RE = re.compile(r"\b(19|20)\d{2}[a-z]?\b")

def is_float(s):
    try:
        float(s); return True
    except Exception:
        return False

def csv_facts(mat_id, abs_path, ext, facts, cap):
    delim = "\t" if ext == ".tsv" else ","
    rows = []
    with open(abs_path, encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.reader(f, delimiter=delim):
            if any(c.strip() for c in r):
                rows.append(r)
            if len(rows) > 20000:
                break
    if not rows:
        return
    header, data = rows[0], rows[1:]
    ncol = len(header)
    # 原始行值（小表全量，大表前 60 行）
    for j, r in enumerate(data[:60], start=2):
        if len(facts) >= cap: return
        facts.append({"fact_id": f"F{len(facts)+1:04d}", "kind": "table_row",
                      "value": " | ".join(f"{header[k] if k < ncol else f'col{k+1}'}={c}" for k, c in enumerate(r))[:400],
                      "unit": "", "context": f"{os.path.basename(abs_path)} 第 {j} 行",
                      "source": f"{mat_id}#row{j}"})
    # 数值列统计
    for k in range(ncol):
        if len(facts) >= cap: break
        vals = [r[k].strip() for r in data if k < len(r) and is_float(r[k].strip())]
        if len(vals) >= 2:
            xs = [float(v) for v in vals]
            stat = {"n": len(xs), "mean": round(statistics.fmean(xs), 6),
                    "min": min(xs), "max": max(xs)}
            if len(xs) >= 2:
                stat["sd"] = round(statistics.stdev(xs), 6)
            facts.append({"fact_id": f"F{len(facts)+1:04d}", "kind": "column_stats",
                          "value": json.dumps(stat, ensure_ascii=False),
                          "unit": "", "context": f"{os.path.basename(abs_path)} 列 `{header[k]}`（基于 n={len(xs)}）",
                          "source": f"{mat_id}#col:{header[k]}"})

def text_facts(mat_id, work, facts, cap, per_material_cap=250):
    txt_path = os.path.join(work, "text", f"{mat_id}.txt")
    if not os.path.isfile(txt_path):
        return
    lines = open(txt_path, encoding="utf-8", errors="replace").read().splitlines()
    kept = 0
    for ln, line in enumerate(lines, 1):
        if kept >= per_material_cap or len(facts) >= cap:
            return
        if not re.search(r"\d", line):
            continue
        for m in NUM_SENT_RE.finditer(line):
            s = m.group(0).strip()
            if len(s) < 12 or not re.search(r"\d", s):
                continue
            # 过滤纯参考文献行（含 DOI 或 年+期刊样式）——文献进 bibliography
            if DOI_RE.search(s):
                continue
            facts.append({"fact_id": f"F{len(facts)+1:04d}", "kind": "text_sentence",
                          "value": s[:400], "unit": "", "context": "",
                          "source": f"{mat_id}#l{ln}"})
            kept += 1
            break  # 每行最多取一条，避免爆炸

REF_LINE_RE = re.compile(
    r"^(\s*\[?\d{1,3}\]?[.\)、]?\s+)?\S.*" + r"(19|20)\d{2}" + r".*", )

def parse_bibliography(work, materials):
    """从全部文本材料中识别文献条目：DOI 行或 [n] 作者. 题名. 期刊. 年 样式行。"""
    entries, seen = [], set()
    for m in materials:
        mid = m.get("material_id")
        txt_path = os.path.join(work, "text", f"{mid}.txt")
        if not os.path.isfile(txt_path):
            continue
        try:
            lines = open(txt_path, encoding="utf-8", errors="replace").read().splitlines()
        except Exception:
            continue
        buf = ""
        def emit(raw, ln):
            raw = raw.strip().strip(";")
            if len(raw) < 25 or not YEAR_RE.search(raw):
                return
            key = raw[:120]
            if key in seen:
                return
            seen.add(key)
            doi = DOI_RE.search(raw)
            year = YEAR_RE.search(raw)
            # 作者：年份前的第一段；去掉前导 [n]
            pre = re.sub(r"^\s*\[?\d{1,3}\]?[.\)、]?\s*", "", raw)
            authors = pre.split("(")[0] if "(" in pre[:120] else pre
            authors = authors.split(".")[0][:200]
            entries.append({
                "ref_key": f"R{len(entries)+1:03d}",
                "raw": raw[:600],
                "authors": authors.strip(" ,"),
                "year": year.group(0) if year else "",
                "doi": doi.group(0).rstrip(".") if doi else "",
                "venue": "",
                "fields_complete": bool(doi and year and authors.strip()),
                "source": f"{mid}#l{ln}",
            })
        for ln, line in enumerate(lines, 1):
            s = line.strip()
            cont = buf and not re.match(r"^\s*\[?\d{1,3}\]?[.\)、]?\s+\S", s) and not DOI_RE.search(s) and len(buf) < 500
            if DOI_RE.search(s) or re.match(r"^\s*\[?\d{1,3}\]?[.\)、]?\s*\S.*(19|20)\d{2}", s):
                if buf:
                    emit(buf, ln)
                buf = s
                if DOI_RE.search(s) or len(s) > 60:
                    emit(buf, ln); buf = ""
            elif cont:
                buf += " " + s
            else:
                if buf:
                    emit(buf, ln); buf = ""
        if buf:
            emit(buf, len(lines))
    return entries

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--cap", type=int, default=1500)
    args = ap.parse_args()

    idx_path = os.path.join(args.work, "material_index.json")
    materials = []
    if os.path.isfile(idx_path):
        try:
            materials = json.load(open(idx_path, encoding="utf-8"))
        except Exception:
            materials = []

    facts = []
    for m in materials:
        if len(facts) >= args.cap:
            break
        if m.get("status") != "ok":
            continue
        ext = m.get("ext", "")
        if ext in (".csv", ".tsv"):
            try:
                csv_facts(m["material_id"], m["abs_path"], ext, facts, args.cap)
            except Exception:
                pass
        elif ext in (".pdf", ".txt", ".md", ".docx", ".doc"):
            try:
                text_facts(m["material_id"], args.work, facts, args.cap)
            except Exception:
                pass

    biblio = parse_bibliography(args.work, materials)

    with open(os.path.join(args.work, "facts.json"), "w", encoding="utf-8") as f:
        json.dump(facts, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.work, "bibliography.json"), "w", encoding="utf-8") as f:
        json.dump(biblio, f, ensure_ascii=False, indent=1)

    # facts_digest.md（限长，写作时读它）
    with open(os.path.join(args.work, "facts_digest.md"), "w", encoding="utf-8") as f:
        f.write(f"# 事实底稿摘要（自动生成 {datetime.datetime.utcnow().isoformat()}Z）\n")
        f.write(f"共 {len(facts)} 条事实、{len(biblio)} 条文献。全量见 facts.json / bibliography.json。\n")
        f.write("**红线：稿件中的数字必须逐条对应本表或材料锚点；找不到出处的数字不得写入稿件。**\n\n")
        budget, used = 36000, 0
        for t in facts:
            line = f"- [{t['fact_id']}] ({t['source']}) {t['context']} {t['value']}\n"
            if used + len(line) > budget:
                f.write(f"\n…（其余 {len(facts)} 条见 facts.json）\n"); break
            f.write(line); used += len(line)
        f.write("\n## 文献条目\n")
        for b in biblio[:120]:
            f.write(f"- [{b['ref_key']}] ({b['source']}) {b['raw'][:240]}"
                    + (f" DOI:{b['doi']}" if b["doi"] else "（无DOI）") + "\n")

    try:
        with open(os.path.join(args.out, "run_log.md"), "a", encoding="utf-8") as f:
            f.write(f"\n## extract_facts {datetime.datetime.utcnow().isoformat()}Z\n")
            f.write(f"- facts={len(facts)}, references={len(biblio)}\n")
    except Exception:
        pass
    print(json.dumps({"ok": True, "facts": len(facts), "references": len(biblio)}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
