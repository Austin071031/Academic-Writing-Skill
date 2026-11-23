#!/usr/bin/env python3
"""engine_pre.py（结果图表转写方向）— 数值台账：把数据文件与含数值句子提取为带锚点的台账，
是结果节写作的唯一数字来源。产出 /app/work/facts_ledger.json + facts_ledger.md（限长）。"""
import argparse, csv, json, os, re, statistics, subprocess, sys

NUM_SENT = re.compile(r"[^。\n.!?]{0,160}?(?:\d+\.\d+|\d+%|\d+\s*(?:mg|g|kg|μg|ug|mL|ml|L|mm|cm|m|nm|μm|um|mol|mM|μM|uM|nM|pM|Hz|kHz|MHz|V|mV|A|mA|W|kW|J|kJ|Pa|kPa|MPa|GPa|K|℃|°C|s|ms|min|h|eV|keV|MeV|bp|kb|Da|kDa|rpm|CFU|ppm|ppb|cells?|±)|p\s*[<=>]\s*0?\.\d+|n\s*=\s*\d+|N\s*=\s*\d+|r\s*=\s*0?\.\d+|R[²2]\s*=\s*0?\.\d+)[^。\n]{0,160}?")
DOI = re.compile(r"10\.\d{4,9}/\S+")

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
    facts, notes = [], []
    def add(kind, value, unit, src, ctx=""):
        facts.append({"fact_id": f"F{len(facts)+1:04d}", "kind": kind, "value": str(value)[:400],
                      "unit": unit, "context": ctx[:160], "source": src})
    for i, m in enumerate(brief.get("materials", [])):
        mid, ext, path = f"M{i+1:02d}", m.get("ext",""), m.get("path","")
        try:
            if ext in (".csv", ".tsv"):
                rows = []
                with open(path, encoding="utf-8", errors="replace", newline="") as f:
                    for r in csv.reader(f, delimiter="\t" if ext == ".tsv" else ","):
                        if any(c.strip() for c in r): rows.append(r)
                        if len(rows) > 20000: break
                if not rows: continue
                hdr, data = rows[0], rows[1:]
                with open(os.path.join(tdir, f"{mid}.txt"), "w", encoding="utf-8") as f:
                    for j, r in enumerate(rows, 1): f.write(f"row{j}: " + " | ".join(r) + "\n")
                for j, r in enumerate(data[:80], 2):
                    add("table_row", " | ".join(f"{hdr[k] if k<len(hdr) else k}={c}" for k, c in enumerate(r)), "", f"{mid}#row{j}")
                for k in range(len(hdr)):
                    vals = [r[k].strip() for r in data if k < len(r)]
                    xs = []
                    for v in vals:
                        try: xs.append(float(v))
                        except Exception: pass
                    if len(xs) >= 2:
                        st = {"n": len(xs), "mean": round(statistics.fmean(xs), 6), "min": min(xs), "max": max(xs)}
                        if len(xs) >= 2: st["sd"] = round(statistics.stdev(xs), 6)
                        add("column_stats", json.dumps(st, ensure_ascii=False), "", f"{mid}#col:{hdr[k]}", f"列 {hdr[k]} 描述统计（仅供参考，正文引用原始行值）")
            elif ext in (".txt", ".md", ".json", ".bib"):
                lines = open(path, encoding="utf-8", errors="replace").read(400000).splitlines()
                with open(os.path.join(tdir, f"{mid}.txt"), "w", encoding="utf-8") as f: f.write("\n".join(lines))
                for ln, line in enumerate(lines, 1):
                    if not re.search(r"\d", line) or DOI.search(line): continue
                    mm = NUM_SENT.search(line)
                    if mm and len(mm.group(0).strip()) >= 12:
                        add("text_sentence", mm.group(0).strip(), "", f"{mid}#l{ln}")
                        if sum(1 for x in facts if x["source"].startswith(mid)) > 200: break
            elif ext == ".pdf":
                tp = os.path.join(tdir, f"{mid}.txt")
                if pdf_text(path, tp):
                    lines = open(tp, encoding="utf-8", errors="replace").read().splitlines()
                    for ln, line in enumerate(lines, 1):
                        if not re.search(r"\d", line) or DOI.search(line): continue
                        mm = NUM_SENT.search(line)
                        if mm and len(mm.group(0).strip()) >= 12:
                            add("text_sentence", mm.group(0).strip(), "", f"{mid}#l{ln}")
                            if sum(1 for x in facts if x["source"].startswith(mid)) > 250: break
                else:
                    notes.append(f"{mid} {m.get('rel')}: PDF 文本提取失败，相关数值不得写入")
            elif ext in (".docx", ".doc"):
                lines = docx_lines(path)
                with open(os.path.join(tdir, f"{mid}.txt"), "w", encoding="utf-8") as f: f.write("\n".join(lines))
                for ln, line in enumerate(lines, 1):
                    if not re.search(r"\d", line): continue
                    mm = NUM_SENT.search(line)
                    if mm and len(mm.group(0).strip()) >= 12: add("text_sentence", mm.group(0).strip(), "", f"{mid}#l{ln}")
            elif ext in (".png", ".jpg", ".jpeg"):
                notes.append(f"{mid} {m.get('rel')}: 图片材料，图中数值需人工/OCR 确认，不得凭视觉估计写入")
        except Exception as e:
            notes.append(f"{mid} {m.get('rel')}: 处理失败 {str(e)[:120]}")
    facts = facts[:1500]
    json.dump(facts, open(os.path.join(a.work, "facts_ledger.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(a.work, "facts_ledger.md"), "w", encoding="utf-8") as f:
        f.write(f"# 数值台账（{len(facts)} 条，写作唯一数字来源）\n\n**红线：稿件每个数字必须来自本台账（记 fact_id）或标注【计算值：算式】/【待确认】。**\n\n")
        for t in facts[:400]:
            f.write(f"- [{t['fact_id']}] ({t['source']}) {t['context']} {t['value']}\n")
        if len(facts) > 400: f.write(f"\n…其余 {len(facts)-400} 条见 facts_ledger.json\n")
        for n in notes: f.write(f"\n> 注意: {n}\n")
    with open(os.path.join(a.out, "run_log.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## engine_pre ledger facts={len(facts)} notes={len(notes)}\n")
    print(json.dumps({"ok": True, "facts": len(facts), "notes": notes}, ensure_ascii=False))

if __name__ == "__main__":
    sys.exit(main())
