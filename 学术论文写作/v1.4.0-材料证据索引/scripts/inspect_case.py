#!/usr/bin/env python3
"""inspect_case.py — 预检：解析 /input/case.json 与 task.md → brief.json；立即写 result.json 保底骨架。
仅用标准库，任何异常不阻断。"""
import argparse, json, os, re, sys, datetime

MAT_EXT = {".pdf",".csv",".tsv",".txt",".md",".docx",".doc",".json",".png",".jpg",".jpeg",".xlsx",".bib",".ris"}
SECTIONS = [("abstract",r"摘要|abstract"),("introduction",r"引言|introduction"),("methods",r"方法|methods?|methodology"),
 ("results",r"结果|results?"),("discussion",r"讨论|discussion"),("conclusion",r"结论|conclusions?"),
 ("references",r"参考文献|references?"),("figures",r"图注|figures?|caption"),("tables",r"表格|tables?"),
 ("data_avail",r"数据可得|数据可用|data\s+availab"),("declarations",r"声明|declarations?|利益冲突|conflict"),
 ("keywords",r"关键词|keywords?"),("appendix",r"附录|appendix|supplement")]
STYLES = [("gbt7714",r"GB/?T?\s*7714|国标|顺序编码"),("apa",r"\bAPA\b"),("ieee",r"\bIEEE\b"),
 ("author_year",r"著者.?出版年|author.?year"),("numeric",r"数字编号|numbered|numeric|vancouver")]

def rt(p, n=300000):
    try:
        return open(p, encoding="utf-8", errors="replace").read(n)
    except Exception:
        return ""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input"); ap.add_argument("--work", default="/app/work"); ap.add_argument("--out", default="/app/output")
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True); os.makedirs(a.out, exist_ok=True)
    issues, case, cid, contract = [], {}, None, []
    cj = os.path.join(a.input, "case.json")
    if not os.path.isfile(cj):
        for r,_d,fs in os.walk(a.input):
            if "case.json" in fs: cj = os.path.join(r, "case.json"); break
    if os.path.isfile(cj):
        try: case = json.loads(rt(cj, 2_000_000) or "{}")
        except Exception as e: issues.append(f"case.json 解析失败: {e}")
    else:
        issues.append("缺少 case.json")
    if isinstance(case, dict):
        cid = case.get("case_id") or case.get("id")
        oc = case.get("output_contract")
        if isinstance(oc, list): contract = [str(x) for x in oc]
        elif isinstance(oc, dict): contract = list(map(str, oc.keys()))
        elif isinstance(oc, str): contract = [s for s in re.split(r"[,\s]+", oc) if s]
    if not cid: cid, _ = "UNKNOWN-CASE", issues.append("case_id 未找到")
    task = rt(os.path.join(a.input, "task.md"))
    if not task: issues.append("缺少 task.md 或为空")
    blob = task + "\n" + json.dumps(case, ensure_ascii=False)[:15000]
    secs = [s for s,p in SECTIONS if re.search(p, blob, re.I)]
    sty = next((s for s,p in STYLES if re.search(p, blob, re.I)), "gbt7714")
    wm = re.search(r"(\d{3,6})\s*(?:字|词|words?)", blob, re.I)
    mats = []
    for r,_d,fs in os.walk(a.input):
        for fn in sorted(fs):
            if fn.lower() in ("case.json","task.md"): continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in MAT_EXT:
                p = os.path.join(r, fn)
                mats.append({"path": p, "rel": os.path.relpath(p, a.input), "ext": ext,
                             "size": os.path.getsize(p) if os.path.isfile(p) else -1})
    if not mats: issues.append("/input 未发现材料文件")
    brief = {"case_id": cid, "task_excerpt": task[:600], "required_sections": secs or
             ["abstract","introduction","methods","results","discussion","references"],
             "sections_inferred": not secs, "citation_style": sty, "word_target": int(wm.group(1)) if wm else None,
             "language": "en" if re.search(r"英文|in English", blob, re.I) and "中文" not in blob else "zh",
             "output_contract": contract, "materials": mats, "issues": issues,
             "created_utc": datetime.datetime.now(datetime.UTC).isoformat()}
    json.dump(brief, open(os.path.join(a.work, "brief.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    skel = {"case_id": cid, "status": "partial", "stage": "inspect", "deliverables": {},
            "sources": [], "uncertainty": issues + ["保底骨架：写作尚未完成"], "change_log": []}
    for f in contract:
        skel.setdefault(f, "unavailable: 流水线未完成")
    rj = os.path.join(a.out, "result.json")
    if not os.path.isfile(rj):
        json.dump(skel, open(rj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "run_log.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## inspect {brief['created_utc']}\n- case={cid} sections={len(brief['required_sections'])} style={sty} materials={len(mats)} issues={issues}\n")
    print(json.dumps({"ok": True, "case_id": cid, "sections": brief["required_sections"], "style": sty,
                      "materials": len(mats), "contract": contract, "issues": issues}, ensure_ascii=False))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        sys.stderr.write(f"inspect fatal: {e}\n"); sys.exit(1)
