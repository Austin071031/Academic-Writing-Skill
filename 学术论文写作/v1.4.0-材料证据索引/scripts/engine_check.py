#!/usr/bin/env python3
"""engine_check.py（材料组织方向）— 三闭环检查：
1. 冲突闭环：register 中每个冲突必须在稿件中有【待确认：冲突】标注或 change_log 有裁决记录；
2. 覆盖闭环：每份材料要么被稿件/证据映射使用，要么在 unused 清单中说明不用原因；
3. 数字溯源：稿件实质数字命中材料语料（轻量版）。
另检查 evidence_map 文件存在。输出 engine_report.json + material_audit.md。"""
import argparse, json, os, re, sys, datetime

NUM = re.compile(r"(?<![\w.])([-+]?\d+(?:,\d{3})*\.\d+|\d+(?:\.\d+)?%)(?![\w%])")
PEND = re.compile(r"【待确认[^】]*】")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manuscript", default="/app/output/manuscript.md")
    ap.add_argument("--work", default="/app/work"); ap.add_argument("--out", default="/app/output")
    a = ap.parse_args()
    ms = open(a.manuscript, encoding="utf-8", errors="replace").read() if os.path.isfile(a.manuscript) else ""
    chlog = ""
    cl = os.path.join(a.out, "change_log.md")
    if os.path.isfile(cl): chlog = open(cl, encoding="utf-8", errors="replace").read()
    brief = {}
    bp = os.path.join(a.work, "brief.json")
    if os.path.isfile(bp):
        try: brief = json.load(open(bp, encoding="utf-8"))
        except Exception: pass
    reg = {}
    rp = os.path.join(a.work, "register.json")
    if os.path.isfile(rp):
        try: reg = json.load(open(rp, encoding="utf-8"))
        except Exception: pass
    fails, warns = [], []
    # 1. 冲突闭环
    open_conflicts = []
    for c in reg.get("conflicts", [])[:30]:
        key = c["parameter"][:12]
        hit = re.search(r"【待确认[^】]*冲突[^】]*】", ms) and key.split()[0] in ms if key.split() else False
        adjudicated = key.split()[0] in chlog if key.split() else False
        if not (hit or adjudicated):
            open_conflicts.append(c["parameter"])
    if open_conflicts:
        warns.append(f"{len(open_conflicts)} 个材料冲突未见闭环（稿件无【待确认：冲突】且 change_log 无裁决）: {open_conflicts[:5]}")
    # 2. 覆盖闭环（语料：稿件 + change_log + evidence_map；匹配文件名或材料编号）
    em_text = ""
    for p in (os.path.join(a.out, "evidence_map.md"), os.path.join(a.work, "evidence_map.json")):
        if os.path.isfile(p):
            try: em_text += open(p, encoding="utf-8", errors="replace").read()
            except Exception: pass
    hay = ms + "\n" + chlog + "\n" + em_text
    unused = []
    for i, m in enumerate(brief.get("materials", [])):
        rel = m.get("rel", "")
        base = os.path.splitext(os.path.basename(rel))[0]
        mid = f"M{i+1:02d}"
        if (base and base in hay) or rel in hay or mid in hay:
            continue
        unused.append(rel)
    if unused:
        warns.append(f"{len(unused)} 份材料未在稿件/记录中出现（若非故意弃用请说明原因）: {unused[:5]}")
    # 3. 数字溯源（轻量）
    corpus = []
    tdir = os.path.join(a.work, "text")
    if os.path.isdir(tdir):
        for fn in os.listdir(tdir):
            try: corpus.append(open(os.path.join(tdir, fn), encoding="utf-8", errors="replace").read())
            except Exception: pass
    corpus = "\n".join(corpus)
    body = re.split(r"^#{1,4}\s*(参考文献|References)\s*$", ms, flags=re.M | re.I)[0]
    pend_spans = [(m.start(), m.end()) for m in PEND.finditer(body)]
    unmatched, checked = [], 0
    for m in NUM.finditer(body):
        n = m.group(1).replace(",", "").rstrip("%")
        n = n.rstrip("0").rstrip(".") if "." in n else n
        ctx = body[max(0, m.start()-40):m.end()+40]
        if any(0 <= s - m.end() <= 25 for s, _e in pend_spans) or any(ps <= m.start() and m.end() <= pe for ps, pe in pend_spans):
            continue
        checked += 1
        cands = {n, n + ".0"} if "." not in n else {n}
        if not any(re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d])", corpus) for v in cands):
            unmatched.append({"value": m.group(1), "context": ctx[-100:].replace("\n", " ")})
    if unmatched: fails.append(f"{len(unmatched)} 个数字无材料出处")
    em = os.path.join(a.out, "evidence_map.md")
    emw = os.path.join(a.work, "evidence_map.json")
    if not (os.path.isfile(em) or os.path.isfile(emw)):
        warns.append("缺证据映射（evidence_map.md/json）——关键论断→材料锚点的映射是本方向核心交付物")
    verdict = "FAIL" if fails else ("WARN" if warns else "PASS")
    rep = {"engine": "material-evidence-index", "verdict": verdict, "fails": fails, "warnings": warns,
           "conflicts_total": len(reg.get("conflicts", [])), "open_conflicts": open_conflicts[:20],
           "unused_materials": unused[:20], "numbers": {"checked": checked, "unmatched": unmatched[:40]},
           "created_utc": datetime.datetime.now(datetime.UTC).isoformat()}
    json.dump(rep, open(os.path.join(a.out, "engine_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "material_audit.md"), "w", encoding="utf-8") as f:
        f.write(f"# 材料组织审计（verdict={verdict}）\n\n")
        f.write(f"冲突登记 {len(reg.get('conflicts', []))} 个，未闭环 {len(open_conflicts)} 个；未使用材料 {len(unused)} 份；数字检查 {checked} 个/未命中 {len(unmatched)} 个。\n\n")
        if fails: f.write("## 必须返修\n" + "".join(f"- ❌ {x}\n" for x in fails) + "\n")
        if warns: f.write("## 需确认\n" + "".join(f"- ⚠ {x}\n" for x in warns) + "\n")
        for u in unmatched[:30]: f.write(f"- 无出处数字 `{u['value']}` — {u['context']}\n")
    print(json.dumps({"verdict": verdict, "fails": fails}, ensure_ascii=False))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        out = "/app/output"
        if "--out" in sys.argv:
            try: out = sys.argv[sys.argv.index("--out") + 1]
            except Exception: pass
        os.makedirs(out, exist_ok=True)
        json.dump({"engine": "material-evidence-index", "verdict": "WARN", "fails": [], "warnings": [f"engine_check 异常: {str(e)[:150]}"]},
                  open(os.path.join(out, "engine_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        sys.exit(0)
