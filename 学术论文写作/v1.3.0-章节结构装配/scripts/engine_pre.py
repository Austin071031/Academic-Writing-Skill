#!/usr/bin/env python3
"""engine_pre.py（章节结构方向）— 章节-材料支撑骨架：扫描材料文本，按章节关键词命中生成
outline.md（必备章节 × 支撑材料 × 材料缺口）。Agent 按骨架写稿，缺支撑的章节标【待补】。"""
import argparse, json, os, re, subprocess, sys

SEC_KW = {"title": ["研究", "基于", "分析", "评价"],
 "abstract": ["摘要", "abstract"], "keywords": ["关键词", "keyword"],
 "introduction": ["引言", "背景", "研究意义", "introduction", "background"],
 "methods": ["方法", "材料与方法", "实验", "步骤", "protocol", "method", "制备", "测定"],
 "results": ["结果", "表明", "显示", "result", "测得", "达到"],
 "discussion": ["讨论", "机制", "归因", "discussion", "局限"],
 "conclusion": ["结论", "总结", "conclusion"],
 "references": ["参考文献", "references", "[1]", "DOI", "doi"],
 "figures": ["图", "figure", "fig"], "tables": ["表", "table"],
 "data_avail": ["数据可得", "数据可用", "原始数据", "data availab"],
 "declarations": ["利益冲突", "基金", "资助", "致谢", "funding", "conflict", "acknowledg"]}

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
        if ext in (".txt", ".md", ".json", ".csv", ".tsv", ".bib"):
            open(dst, "w", encoding="utf-8").write(open(path, encoding="utf-8", errors="replace").read(500000)); return True
    except Exception:
        return False
    return False

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
    support = {s: [] for s in brief.get("required_sections", [])}
    unreadable = []
    for i, m in enumerate(brief.get("materials", [])):
        mid, ext, path = f"M{i+1:02d}", m.get("ext", ""), m.get("path", "")
        tp = os.path.join(tdir, f"{mid}.txt")
        ok = extract(path, ext, tp)
        if not ok:
            unreadable.append(f"{mid} {m.get('rel')}")
            if ext in (".png", ".jpg", ".jpeg"):
                support.setdefault("figures", []).append(f"{mid}(图片需人工看图)")
            continue
        text = open(tp, encoding="utf-8", errors="replace").read(300000).lower()
        for sec in support:
            kws = SEC_KW.get(sec, [sec])
            hits = sum(text.count(k.lower()) for k in kws)
            if hits >= 1:
                support[sec].append(f"{mid}({m.get('rel','')[:40]}, 命中{hits})")
        # 类型先验：数据文件必支撑结果与方法；含数字记录的文本同理
        if ext in (".csv", ".tsv", ".xlsx"):
            for sec in ("results", "methods", "tables"):
                if sec in support and not any(x.startswith(mid) for x in support[sec]):
                    support[sec].append(f"{mid}({m.get('rel','')[:40]}, 数据文件先验)")
        elif re.search(r"\d+\.\d+|n\s*=\s*\d+|p\s*[<=>]", text):
            for sec in ("results", "methods"):
                if sec in support and not any(x.startswith(mid) for x in support[sec]):
                    support[sec].append(f"{mid}({m.get('rel','')[:40]}, 含数值记录)")
    wt = brief.get("word_target") or 3000
    ratios = {"abstract": 0.05, "introduction": 0.15, "methods": 0.25, "results": 0.3, "discussion": 0.2, "conclusion": 0.05}
    with open(os.path.join(a.work, "outline.md"), "w", encoding="utf-8") as f:
        f.write(f"# 章节装配骨架（case={brief.get('case_id')}，目标字数≈{wt}）\n\n")
        f.write("按本骨架逐节写作；支撑材料为空 = 材料缺口，该节写【待补：缺材料】并列入 uncertainty。\n\n")
        for sec in brief.get("required_sections", []):
            mats = support.get(sec) or []
            quota = f"，建议篇幅≈{int(wt*ratios[sec])} 字" if sec in ratios else ""
            f.write(f"## {sec}{quota}\n")
            if mats:
                for x in mats: f.write(f"- 支撑: {x}\n")
            else:
                f.write("- ⚠ 无材料支撑（缺口，标【待补】）\n")
            f.write("\n")
        if unreadable:
            f.write("## 不可读材料\n" + "".join(f"- {u}\n" for u in unreadable))
    json.dump({"support": support, "unreadable": unreadable},
              open(os.path.join(a.work, "outline.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "run_log.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## engine_pre outline sections={len(support)} unreadable={len(unreadable)}\n")
    print(json.dumps({"ok": True, "sections": len(support),
                      "gaps": [s for s, v in support.items() if not v], "unreadable": unreadable}, ensure_ascii=False))

if __name__ == "__main__":
    sys.exit(main())
