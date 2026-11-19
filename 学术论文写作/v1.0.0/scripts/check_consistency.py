#!/usr/bin/env python3
"""check_consistency.py — 成稿机读一致性核验（本 Skill 的核心关卡）。

五项检查：
  1. numbers   稿件中每个实质数字必须能在材料语料（/app/work/text/* + facts.json）中找到原串
  2. citations 每个引用键/编号存在且被使用；文献表条目均被引用；无悬空引用
  3. sections  brief.required_sections 中的必备章节在稿件中均有对应标题
  4. placeholders 【待确认】等占位符逐条列出（必须同步进 result.json uncertainty）
  5. ref_fields 文献条目缺年份/DOI 提示
输出 consistency_report.json/.md；整体 verdict=PASS/WARN/FAIL。仅用标准库，永不崩溃。
"""
import argparse, json, os, re, sys, datetime

NUM_RE = re.compile(r"(?<![\w.])([-+]?\d+(?:,\d{3})*\.\d+|[-+]?\d+(?:,\d{3})+|\d+(?:\.\d+)?%|\d{2,})(?![\w%])")
PENDING_RE = re.compile(r"【待确认[：:]?[^】]*】|TODO|TBD|XXX|FIXME")
SECTION_KEYWORDS = {
    "title": ["标题", "title"], "abstract": ["摘要", "abstract"],
    "keywords": ["关键词", "关键字", "keywords"],
    "introduction": ["引言", "前言", "introduction"],
    "methods": ["方法", "材料与方法", "methods", "methodology", "materials and methods"],
    "results": ["结果", "results", "findings"],
    "discussion": ["讨论", "discussion"], "conclusion": ["结论", "conclusion"],
    "references": ["参考文献", "references", "bibliography"],
    "acknowledg": ["致谢", "acknowledg"], "data_avail": ["数据可得", "数据可用", "data availab"],
    "figures": ["图", "figure", "caption"], "tables": ["表", "table"],
    "appendix": ["附录", "appendix", "supplement"],
    "declarations": ["声明", "declaration", "利益冲突", "conflict", "funding", "资助"],
}

def norm_num(s):
    s = s.replace(",", "").rstrip("%")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s

def build_corpus(work):
    """材料语料：所有提取文本 + facts 值，用于数字溯源。"""
    corpus, years = [], set()
    tdir = os.path.join(work, "text")
    if os.path.isdir(tdir):
        for fn in os.listdir(tdir):
            if fn.endswith(".txt"):
                try:
                    corpus.append(open(os.path.join(tdir, fn), encoding="utf-8", errors="replace").read())
                except Exception:
                    pass
    fj = os.path.join(work, "facts.json")
    if os.path.isfile(fj):
        try:
            for t in json.load(open(fj, encoding="utf-8")):
                corpus.append(str(t.get("value", "")))
        except Exception:
            pass
    bj = os.path.join(work, "bibliography.json")
    if os.path.isfile(bj):
        try:
            for b in json.load(open(bj, encoding="utf-8")):
                corpus.append(b.get("raw", ""))
                if b.get("year"):
                    years.add(b["year"][:4])
        except Exception:
            pass
    return "\n".join(corpus), years

def strip_refs_section(text):
    """返回 (正文, 文献表段落)。文献表中的数字（卷期页年）不参与数字溯源检查。"""
    m = re.search(r"^#{1,4}\s*(参考文献|参考文献列表|References|Bibliography)\s*$",
                  text, re.M | re.I)
    if m:
        return text[:m.start()], text[m.start():]
    return text, ""

def check_numbers(body, corpus, bib_years):
    bad, checked = [], 0
    for m in NUM_RE.finditer(body):
        raw = m.group(1)
        ctx_start = max(0, m.start() - 60)
        ctx = body[ctx_start:m.end() + 60].replace("\n", " ")
        n = norm_num(raw)
        if not n or n == "0":
            continue
        # 排除：年份(且在文献年份集合或 19xx/20xx)、图/表/节编号、待确认占位内
        if re.fullmatch(r"(19|20)\d{2}", n) and (n in bib_years or re.search(r"(©|\b20\d\d\s*年)", ctx)):
            continue
        if re.fullmatch(r"(19|20)\d{2}", n):
            continue  # 年份一律豁免（文献与常识年份不属实验数据）
        if re.search(r"[图表]\s*$", body[max(0, m.start()-4):m.start()]):
            continue
        if re.match(r"^(0?[1-9]|[12]\d|3[01])$", n) and re.search(r"(图|表|第|节|章|式|方程)\s*$", body[max(0, m.start()-6):m.start()]):
            continue
        if PENDING_RE.search(ctx):
            continue
        if int(m.start()) >= 0 and body[max(0, m.start()-3):m.start()] in ("[", "［"):
            continue  # 引用编号
        checked += 1
        variants = {n, raw.replace(",", "").rstrip("%")}
        if "." not in n:
            variants.add(n + ".0")
        ok = False
        for v in variants:
            if v and re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d])", corpus):
                ok = True; break
        if not ok:
            bad.append({"value": raw, "context": ctx[-120:]})
    return {"checked": checked, "unmatched": bad[:80], "n_unmatched": len(bad)}

def check_citations(body, refs_text, brief, work):
    style = (brief or {}).get("citation_style", "gbt7714")
    issues, cited_keys = [], set()
    # 文献表条目
    ref_entries = re.findall(r"^\s*\[?(\d{1,3})\]?[.\)、]?\s+\S", refs_text, re.M)
    author_year_entries = re.findall(r"^[-*\s]*([A-ZÀ-Þ一-鿿][\w\-一-鿿]*(?:\s+(?:et\s+al\.?|等))?).*?((?:19|20)\d{2})",
                                     refs_text, re.M)
    if style in ("apa", "author_year"):
        for m in re.finditer(r"\(([A-ZÀ-Þ一-鿿][\w\-一-鿿]*(?:\s+et\s+al\.?|等)?)[,，]?\s*((?:19|20)\d{2})[a-z]?\)", body):
            key = (m.group(1), m.group(2))
            cited_keys.add(key)
            if not any(a.startswith(m.group(1)[:6]) and y == m.group(2) for a, y in author_year_entries):
                issues.append(f"作者-年份引用在文献表中无对应条目: ({m.group(1)}, {m.group(2)})")
    else:  # 数字顺序制
        max_ref = max([int(x) for x in ref_entries], default=0)
        for m in re.finditer(r"\[(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\]", body):
            a = int(m.group(1)); b = int(m.group(2)) if m.group(2) else a
            for n in range(a, b + 1):
                cited_keys.add(n)
                if n > max_ref:
                    issues.append(f"引用 [{n}] 超出文献表范围（共 {max_ref} 条）")
        for n in [int(x) for x in ref_entries]:
            if n not in cited_keys:
                issues.append(f"文献表第 [{n}] 条未被正文引用（疑似装饰性/冗余引用）")
    # 与 bibliography.json 对账（信息项）
    bj = os.path.join(work, "bibliography.json")
    src_count = None
    if os.path.isfile(bj):
        try:
            src_count = len(json.load(open(bj, encoding="utf-8")))
        except Exception:
            pass
    return {"style": style, "issues": issues[:60], "n_issues": len(issues),
            "n_ref_entries_in_ms": len(ref_entries) or len(author_year_entries),
            "n_source_bibliography": src_count}

def check_sections(text, required):
    heads = re.findall(r"^#{1,4}\s+(.+?)\s*$", text, re.M)
    found, missing = [], []
    for sec in required:
        kws = SECTION_KEYWORDS.get(sec, [sec])
        hit = any(any(k.lower() in h.lower() for k in kws) for h in heads)
        if not hit and sec in ("figures", "tables"):
            # 图注/表注通常内联而非独立章节：接受正文中的"图 N"/"表 N"编号或独立图注行
            pat = r"(图\s*\d+|figure\s*\d+|fig\.\s*\d+)" if sec == "figures" else r"(表\s*\d+|table\s*\d+)"
            hit = bool(re.search(pat, text, re.I))
        (found if hit else missing).append(sec)
    return {"required": required, "found": found, "missing": missing, "headings": heads[:60]}

def check_ref_fields(refs_text):
    warns = []
    for ln in refs_text.splitlines():
        s = ln.strip()
        if len(s) < 25:
            continue
        if re.match(r"^\[?\d{1,3}\]?[.\)、]?\s+\S", s) or re.match(r"^[-*]\s+\S.*(19|20)\d{2}", s):
            if not re.search(r"(19|20)\d{2}", s):
                warns.append(f"文献条目缺年份: {s[:80]}")
            if "10." not in s and not re.search(r"(19|20)\d{2}[,，]?\s*\d+", s):
                warns.append(f"文献条目缺 DOI/卷期页（仅提示）: {s[:80]}")
    return warns[:40]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manuscript", default="/app/output/manuscript.md")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    ms = ""
    if os.path.isfile(args.manuscript):
        ms = open(args.manuscript, encoding="utf-8", errors="replace").read()
    brief = {}
    bp = os.path.join(args.work, "brief.json")
    if os.path.isfile(bp):
        try:
            brief = json.load(open(bp, encoding="utf-8"))
        except Exception:
            pass

    report = {"created_utc": datetime.datetime.utcnow().isoformat() + "Z",
              "manuscript": args.manuscript, "manuscript_chars": len(ms), "checks": {}}
    if not ms.strip():
        report["verdict"] = "FAIL"
        report["checks"]["manuscript"] = {"error": "manuscript 为空或不存在"}
    else:
        corpus, bib_years = build_corpus(args.work)
        body, refs_text = strip_refs_section(ms)
        report["checks"]["numbers"] = check_numbers(body, corpus, bib_years)
        report["checks"]["citations"] = check_citations(body, refs_text, brief, args.work)
        report["checks"]["sections"] = check_sections(ms, brief.get("required_sections", []))
        ph = PENDING_RE.findall(ms)
        report["checks"]["placeholders"] = {"count": len(ph), "items": sorted(set(ph))[:60]}
        report["checks"]["ref_fields"] = {"warnings": check_ref_fields(refs_text)}

        fails = []
        if report["checks"]["numbers"]["n_unmatched"]:
            fails.append(f"{report['checks']['numbers']['n_unmatched']} 个数字无材料出处")
        if report["checks"]["citations"]["n_issues"]:
            fails.append(f"{report['checks']['citations']['n_issues']} 个引用问题")
        if report["checks"]["sections"]["missing"]:
            fails.append("缺必备章节: " + ",".join(report["checks"]["sections"]["missing"]))
        warns = []
        if report["checks"]["placeholders"]["count"]:
            warns.append(f"{report['checks']['placeholders']['count']} 处待确认占位（须列入 uncertainty）")
        warns.extend(report["checks"]["ref_fields"]["warnings"])
        report["verdict"] = "FAIL" if fails else ("WARN" if warns else "PASS")
        report["fail_summary"] = fails
        report["warn_summary"] = warns

    with open(os.path.join(args.out, "consistency_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "consistency_report.md"), "w", encoding="utf-8") as f:
        f.write(f"# 一致性核验报告（{report['created_utc']}）\n\n**verdict: {report['verdict']}**\n\n")
        for name, c in report["checks"].items():
            f.write(f"## {name}\n```json\n{json.dumps(c, ensure_ascii=False, indent=1)[:4000]}\n```\n\n")
        if report.get("fail_summary"):
            f.write("## 必须返修\n" + "".join(f"- {x}\n" for x in report["fail_summary"]))
        if report.get("warn_summary"):
            f.write("## 需确认\n" + "".join(f"- {x}\n" for x in report["warn_summary"]))
    try:
        with open(os.path.join(args.out, "run_log.md"), "a", encoding="utf-8") as f:
            f.write(f"\n## check_consistency {report['created_utc']} verdict={report['verdict']}\n")
    except Exception:
        pass
    print(json.dumps({"verdict": report["verdict"],
                      "fails": report.get("fail_summary", []),
                      "warns": len(report.get("warn_summary", []))}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
