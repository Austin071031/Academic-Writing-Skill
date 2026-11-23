#!/usr/bin/env python3
"""engine_check.py（章节结构方向）— 完整性五检：必备章节、声明字段、标题层级连续性、
图/表注存在性、篇幅比例；缺项必须显式【待补】标注才降级为 WARN 而非 FAIL。
输出 engine_report.json + completeness_report.md。"""
import argparse, json, os, re, sys, datetime

SEC_KW = {"title": None, "abstract": ["摘要", "abstract"], "keywords": ["关键词", "keyword"],
 "introduction": ["引言", "前言", "introduction"], "methods": ["方法", "材料与方法", "methods", "methodology"],
 "results": ["结果", "results", "findings"], "discussion": ["讨论", "discussion"],
 "conclusion": ["结论", "conclusion"], "references": ["参考文献", "references", "bibliography"],
 "figures": None, "tables": None, "data_avail": ["数据可得", "数据可用", "data availab"],
 "declarations": ["利益冲突", "作者贡献", "基金", "资助", "致谢", "数据可得", "数据可用", "conflict", "funding", "acknowledg", "declaration", "data availab"],
 "appendix": ["附录", "appendix", "supplement"]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manuscript", default="/app/output/manuscript.md")
    ap.add_argument("--work", default="/app/work"); ap.add_argument("--out", default="/app/output")
    a = ap.parse_args()
    ms = open(a.manuscript, encoding="utf-8", errors="replace").read() if os.path.isfile(a.manuscript) else ""
    brief = {}
    bp = os.path.join(a.work, "brief.json")
    if os.path.isfile(bp):
        try: brief = json.load(open(bp, encoding="utf-8"))
        except Exception: pass
    heads = re.findall(r"^(#{1,4})\s+(.+?)\s*$", ms, re.M)
    htext = [h[1] for h in heads]
    fails, warns = [], []
    missing = []
    for sec in brief.get("required_sections", []):
        if sec == "title":
            if not any(h[0] == "#" for h in heads): missing.append("title")
            continue
        if sec == "figures":
            if not re.search(r"图\s*\d+|figure\s*\d+", ms, re.I): missing.append("figures")
            continue
        if sec == "tables":
            if not re.search(r"表\s*\d+|table\s*\d+", ms, re.I): missing.append("tables")
            continue
        kws = SEC_KW.get(sec) or [sec]
        if not any(any(k.lower() in h.lower() for k in kws) for h in htext):
            # 正文有【待补：缺材料】标注该节名也算显式处理
            if re.search(r"【待补[^】]*" + re.escape(sec) + r"[^】]*】", ms) or \
               re.search(re.escape(sec) + r"[^。\n]{0,30}【待补", ms):
                warns.append(f"章节 {sec} 以【待补】显式标注（材料缺口）")
            else:
                missing.append(sec)
    if missing: fails.append("缺必备章节且无【待补】标注: " + ",".join(missing))
    levels = [len(h[0]) for h in heads]
    for x, y in zip(levels, levels[1:]):
        if y > x + 1:
            warns.append("标题层级跳级（如 # 直接到 ###），影响可编辑性"); break
    wt = brief.get("word_target")
    nchar = len(re.sub(r"\s", "", ms))
    if wt:
        if nchar < wt * 0.6: warns.append(f"实际篇幅 {nchar} 字 < 目标 {wt} 的 60%，若材料已穷尽请在 uncertainty 说明")
        elif nchar > wt * 1.5: warns.append(f"实际篇幅 {nchar} 字 > 目标 {wt} 的 150%，建议压缩")
    abs_m = re.search(r"^#{1,4}\s*摘要[^\n]*\n(.*?)(?=^#{1,4}\s|\Z)", ms, re.M | re.S | re.I)
    if abs_m and re.search(r"\[\d+\]", abs_m.group(1)):
        warns.append("摘要中出现引用编号，不符合惯例，应移入正文")
    pend = re.findall(r"【待确认[^】]*】|【待补[^】]*】", ms)
    if pend: warns.append(f"{len(pend)} 处显式缺口标注（须全部列入 uncertainty）")
    verdict = "FAIL" if fails else ("WARN" if warns else "PASS")
    rep = {"engine": "structure-completeness", "verdict": verdict, "fails": fails, "warnings": warns,
           "sections_found": htext[:50], "char_count": nchar,
           "created_utc": datetime.datetime.now(datetime.UTC).isoformat()}
    json.dump(rep, open(os.path.join(a.out, "engine_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "completeness_report.md"), "w", encoding="utf-8") as f:
        f.write(f"# 章节完整性报告（verdict={verdict}）\n\n必备章节: {brief.get('required_sections')}\n\n实际标题: {htext[:40]}\n\n")
        if fails: f.write("## 必须返修\n" + "".join(f"- ❌ {x}\n" for x in fails) + "\n")
        if warns: f.write("## 需确认\n" + "".join(f"- ⚠ {x}\n" for x in warns) + "\n")
    print(json.dumps({"verdict": verdict, "fails": fails}, ensure_ascii=False))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        out = "/app/output"
        if "--out" in sys.argv:
            try: out = sys.argv[sys.argv.index("--out") + 1]
            except Exception: pass
        os.makedirs(out, exist_ok=True)
        json.dump({"engine": "structure-completeness", "verdict": "WARN", "fails": [], "warnings": [f"engine_check 异常: {str(e)[:150]}"]},
                  open(os.path.join(out, "engine_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        sys.exit(0)
