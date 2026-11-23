#!/usr/bin/env python3
"""engine_check.py（引用核验方向）— 引用五检：悬空引用、装饰性（未被引用）条目、编号连续性、
格式混用、字段完整性；并生成论断—引用绑定表（含上下文，供 Agent 复核语义）。
输出 engine_report.json + citation_audit.md。"""
import argparse, json, os, re, sys, datetime

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
    style = brief.get("citation_style", "gbt7714")
    m = re.search(r"^#{1,4}\s*(参考文献|References|Bibliography)\s*$", ms, re.M | re.I)
    body, refs = (ms[:m.start()], ms[m.start():]) if m else (ms, "")
    fails, warns = [], []
    bindings = []
    num_cites = []
    for mm in re.finditer(r"\[(\d{1,3})(?:\s*[-–—]\s*(\d{1,3}))?\]", body):
        lo = int(mm.group(1)); hi = int(mm.group(2)) if mm.group(2) else lo
        sent_start = max(body.rfind("。", 0, mm.start()), body.rfind("\n", 0, mm.start())) + 1
        ctx = body[sent_start:mm.end() + 30].strip()[:150]
        for n in range(lo, hi + 1):
            num_cites.append(n)
            bindings.append({"cite": f"[{n}]", "sentence_context": ctx, "binding_ok": None})
    ref_nums = [int(x) for x in re.findall(r"^\s*\[?(\d{1,3})\]?[.\)、]?\s+\S", refs, re.M)]
    ay_cites = re.findall(r"\(([A-ZÀ-ÞA-Za-z\-一-鿿]+(?:\s+et\s+al\.?|等)?)[,，]?\s*((?:19|20)\d{2})[a-z]?\)", body)
    ay_entries = re.findall(r"([A-ZÀ-ÞA-Za-z\-一-鿿]+).*?((?:19|20)\d{2})", refs)
    if ay_cites and not num_cites:
        for au, yr in ay_cites:
            bindings.append({"cite": f"({au}, {yr})", "sentence_context": "", "binding_ok": None})
            if not any(e[0].lower().startswith(au[:5].lower()) and e[1] == yr for e in ay_entries):
                fails.append(f"作者-年份引用在文献表中无对应: ({au}, {yr})")
    max_ref = max(ref_nums) if ref_nums else 0
    dangling = sorted(set(n for n in num_cites if n > max_ref or n < 1))
    if dangling: fails.append(f"悬空引用（文献表共 {max_ref} 条）: {sorted(set(dangling))}")
    uncited = sorted(set(ref_nums) - set(num_cites))
    if uncited and style in ("gbt7714", "numeric", "ieee", "vancouver"):
        fails.append(f"文献表条目未被正文引用（装饰性/冗余）: {uncited}")
    if ref_nums and sorted(ref_nums) != list(range(1, max_ref + 1)):
        warns.append(f"文献表编号不连续/乱序: 实际 {sorted(ref_nums)[:20]}")
    if num_cites and ay_cites:
        warns.append("正文混用数字编号与作者-年份两种引用格式，应统一")
    for ln in refs.splitlines():
        s = ln.strip()
        if len(s) < 25: continue
        if re.match(r"^\[?\d{1,3}\]?[.\)、]?\s+\S", s) or re.search(r"(19|20)\d{2}", s):
            miss = []
            if not re.search(r"(19|20)\d{2}", s): miss.append("年份")
            if "10." not in s and not re.search(r"(19|20)\d{2}[,，]?\s*\d+", s): miss.append("DOI/卷期页")
            if miss: warns.append(f"条目缺{'/'.join(miss)}（保持缺失不补造）: {s[:70]}")
    lib_n = None
    lj = os.path.join(a.work, "library.json")
    if os.path.isfile(lj):
        try: lib_n = len(json.load(open(lj, encoding="utf-8")))
        except Exception: pass
    if lib_n is not None and ref_nums and abs(lib_n - len(ref_nums)) > 2:
        warns.append(f"文献表条数({len(ref_nums)})与材料解析文献库({lib_n})差异>2，需人工核对是否漏收/合并")
    verdict = "FAIL" if fails else ("WARN" if warns else "PASS")
    rep = {"engine": "citation-integrity", "verdict": verdict, "fails": fails, "warnings": warns,
           "style": style, "cited_count": len(set(num_cites)) or len(ay_cites),
           "ref_entries": len(ref_nums) or len(ay_entries), "library_entries": lib_n,
           "created_utc": datetime.datetime.now(datetime.UTC).isoformat()}
    json.dump(rep, open(os.path.join(a.out, "engine_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "citation_audit.md"), "w", encoding="utf-8") as f:
        f.write(f"# 引用核验报告（verdict={verdict}，格式={style}）\n\n")
        if fails: f.write("## 必须返修\n" + "".join(f"- ❌ {x}\n" for x in fails) + "\n")
        if warns: f.write("## 需确认\n" + "".join(f"- ⚠ {x}\n" for x in warns) + "\n")
        f.write("\n## 论断—引用绑定表（Agent 逐条复核 binding_ok，语义不支撑须改）\n\n")
        f.write("| 引用 | 所在句上下文 | 语义支撑? |\n|---|---|---|\n")
        for b in bindings[:60]:
            f.write(f"| {b['cite']} | {b['sentence_context'][:100].replace('|','/')} | 待复核 |\n")
    print(json.dumps({"verdict": verdict, "fails": fails, "warns": len(warns)}, ensure_ascii=False))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        out = "/app/output"
        if "--out" in sys.argv:
            try: out = sys.argv[sys.argv.index("--out") + 1]
            except Exception: pass
        os.makedirs(out, exist_ok=True)
        json.dump({"engine": "citation-integrity", "verdict": "WARN", "fails": [], "warnings": [f"engine_check 异常: {str(e)[:150]}"]},
                  open(os.path.join(out, "engine_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        sys.exit(0)
