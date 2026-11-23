#!/usr/bin/env python3
"""engine_pre.py（材料组织方向）— 材料索引 + 三登记（冗余/冲突/缺失）。
材料 → 带锚点文本段索引与限长摘要；跨材料同参数不同值冲突检测；近重复段落冗余检测；
材料×章节支撑矩阵。产出 material_index.md、register.json/md。"""
import argparse, hashlib, json, os, re, subprocess, sys

def extract(path, ext, dst):
    try:
        if ext == ".pdf":
            r = subprocess.run(["pdftotext", "-layout", path, dst], capture_output=True, timeout=120)
            return r.returncode == 0 and os.path.isfile(dst)
        if ext in (".docx", ".doc"):
            r = subprocess.run(["pandoc", "-t", "plain", "--wrap=none", path], capture_output=True, timeout=60)
            if r.returncode == 0:
                open(dst, "w", encoding="utf-8").write(r.stdout.decode("utf-8", "replace")); return True
            import zipfile
            xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", "replace")
            ls = [t for t in ("".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)) for p in xml.split("</w:p>")) if t.strip()]
            open(dst, "w", encoding="utf-8").write("\n".join(ls)); return bool(ls)
        if ext in (".txt", ".md", ".json", ".bib", ".csv", ".tsv"):
            open(dst, "w", encoding="utf-8").write(open(path, encoding="utf-8", errors="replace").read(500000)); return True
    except Exception:
        return False
    return False

KV = re.compile(r"([\w一-鿿（）()·\- ]{2,24}?)\s*(?:=|为|是|[:：])\s*([-+]?\d+(?:\.\d+)?\s*(?:%|mg|g|kg|mL|ml|L|mm|cm|m|nm|mol|mM|μM|uM|nM|h|min|s|℃|°C|rpm|V|W|Pa|K|eV)?)")
STOP_KEYS = {"row", "http", "https", "doi", "isbn", "issn", "图", "表", "第", "eq", "fig"}

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
    index, unreadable = [], []
    para_seen, redundant = {}, []
    kv_map = {}
    for i, m in enumerate(brief.get("materials", [])):
        mid, ext, path = f"M{i+1:02d}", m.get("ext", ""), m.get("path", "")
        tp = os.path.join(tdir, f"{mid}.txt")
        ok = extract(path, ext, tp)
        entry = {"material_id": mid, "rel": m.get("rel"), "ext": ext, "status": "ok" if ok else "unreadable",
                 "n_lines": 0, "kv_count": 0}
        if not ok:
            unreadable.append(f"{mid} {m.get('rel')}（{'图片需人工看图' if ext in ('.png','.jpg','.jpeg') else '提取失败'}）")
            index.append(entry); continue
        lines = open(tp, encoding="utf-8", errors="replace").read().splitlines()
        entry["n_lines"] = len(lines)
        for ln, line in enumerate(lines, 1):
            s = line.strip()
            if len(s) >= 40:
                h = hashlib.md5(re.sub(r"\s+", "", s).encode()).hexdigest()
                if h in para_seen and para_seen[h][0] != mid:
                    redundant.append({"type": "redundant", "between": [para_seen[h][0], f"{mid}#l{ln}"],
                                      "text": s[:100]})
                else:
                    para_seen.setdefault(h, (f"{mid}#l{ln}",))
            for km in KV.finditer(s):
                key = re.sub(r"\s+", " ", km.group(1).strip(" ,，.。:：")).lower()
                val = km.group(2).strip()
                if len(key) < 2 or key in STOP_KEYS or re.fullmatch(r"\d+", key): continue
                kv_map.setdefault(key, []).append({"value": val, "source": f"{mid}#l{ln}"})
                entry["kv_count"] += 1
        index.append(entry)
    conflicts = []
    for key, vals in kv_map.items():
        uniq = {}
        for v in vals: uniq.setdefault(v["value"], []).append(v["source"])
        if len(uniq) >= 2:
            srcs = {s.split("#")[0] for ss in uniq.values() for s in ss}
            if len(srcs) >= 2:
                conflicts.append({"type": "conflict", "parameter": key[:60],
                                  "values": [{"value": v, "sources": s[:4]} for v, s in list(uniq.items())[:6]]})
    register = {"conflicts": conflicts[:60], "redundant": redundant[:40], "unreadable": unreadable}
    json.dump(register, open(os.path.join(a.work, "register.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    budget = 36000
    with open(os.path.join(a.work, "material_index.md"), "w", encoding="utf-8") as f:
        f.write("# 材料索引与三登记（冗余/冲突/缺失）\n\n## 材料清单\n")
        for e in index:
            f.write(f"- {e['material_id']} `{e['rel']}` — {e['status']}，{e['n_lines']} 行，参数 {e['kv_count']} 个\n")
        f.write("\n## 冲突登记（跨材料同参数不同值——正文采用前必须裁决或标【待确认】）\n")
        for c in register["conflicts"][:25]:
            vs = "；".join(f"`{v['value']}`({','.join(v['sources'][:2])})" for v in c["values"])
            f.write(f"- 参数 `{c['parameter']}`: {vs}\n")
        if not register["conflicts"]: f.write("- 未检出\n")
        f.write("\n## 冗余登记（跨材料近重复内容，引用一处即可）\n")
        for r in register["redundant"][:15]:
            f.write(f"- {' ↔ '.join(r['between'])}: {r['text'][:80]}\n")
        if not register["redundant"]: f.write("- 未检出\n")
        f.write("\n## 缺失/不可读登记\n")
        for u in unreadable: f.write(f"- {u}\n")
        if not unreadable: f.write("- 无\n")
        f.write("\n## 材料摘要（锚点 Mxx#l行号，全文 /app/work/text/Mxx.txt）\n")
        used = 0
        for e in index:
            if e["status"] != "ok": continue
            tp = os.path.join(tdir, f"{e['material_id']}.txt")
            lines = open(tp, encoding="utf-8", errors="replace").read().splitlines()
            head = f"\n### {e['material_id']} `{e['rel']}`\n"
            body = "".join(f"[{e['material_id']}#l{j+1}] {l[:160]}\n" for j, l in enumerate(lines[:40]) if l.strip())
            part = head + body[:2500]
            if used + len(part) > budget:
                part = head + "（摘要预算耗尽，见全文文件）\n"
            f.write(part); used += len(part)
    with open(os.path.join(a.out, "run_log.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## engine_pre matindex materials={len(index)} conflicts={len(conflicts)} redundant={len(redundant)} unreadable={len(unreadable)}\n")
    print(json.dumps({"ok": True, "materials": len(index), "conflicts": len(conflicts),
                      "redundant": len(redundant), "unreadable": unreadable}, ensure_ascii=False))

if __name__ == "__main__":
    sys.exit(main())
