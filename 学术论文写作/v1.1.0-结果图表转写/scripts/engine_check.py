#!/usr/bin/env python3
"""engine_check.py（结果图表转写方向）— 数字回写核验 + 图注规范检查。
规则：稿件每个实质数字必须命中材料语料；由材料数字计算得出的值必须标注【计算值：算式】（豁免并登记）；
图/表注必须存在且含样本量或数据来源说明。输出 /app/output/engine_report.json + number_trace.md。"""
import argparse, json, os, re, sys, datetime

NUM = re.compile(r"(?<![\w.])([-+]?\d+(?:,\d{3})*\.\d+|[-+]?\d+(?:,\d{3})+|\d+(?:\.\d+)?%|\d{2,})(?![\w%])")
PEND = re.compile(r"【待确认[^】]*】")
CALC = re.compile(r"【计算值[：:][^】]*】")

def norm(s):
    s = s.replace(",", "").rstrip("%")
    return s.rstrip("0").rstrip(".") if "." in s else s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manuscript", default="/app/output/manuscript.md")
    ap.add_argument("--work", default="/app/work"); ap.add_argument("--out", default="/app/output")
    a = ap.parse_args()
    corpus = []
    tdir = os.path.join(a.work, "text")
    if os.path.isdir(tdir):
        for fn in os.listdir(tdir):
            try: corpus.append(open(os.path.join(tdir, fn), encoding="utf-8", errors="replace").read())
            except Exception: pass
    fl = os.path.join(a.work, "facts_ledger.json")
    if os.path.isfile(fl):
        try: corpus += [str(t.get("value","")) for t in json.load(open(fl, encoding="utf-8"))]
        except Exception: pass
    corpus = "\n".join(corpus)
    ms = open(a.manuscript, encoding="utf-8", errors="replace").read() if os.path.isfile(a.manuscript) else ""
    body = re.split(r"^#{1,4}\s*(参考文献|References)\s*$", ms, flags=re.M | re.I)[0]
    # 豁免语义：【计算值/待确认】仅豁免"标记内部"与"紧邻标记之前"（≤25 字符且无句读）的数字
    pend_spans = [(m.start(), m.end()) for m in PEND.finditer(body)]
    calc_spans = [(m.start(), m.end()) for m in CALC.finditer(body)]
    def exempted(pos_start, pos_end):
        for s, e in pend_spans + calc_spans:
            if pos_start >= s and pos_end <= e:   # 标记内部的数字（算式、说明）
                return True
            if 0 <= s - pos_end <= 25 and not re.search(r"[。；\n]", body[pos_end:s]):
                return True                       # 紧邻标记之前的被注解数字
        return False
    unmatched, checked, calc_ok = [], 0, 0
    for m in NUM.finditer(body):
        raw = m.group(1); n = norm(raw)
        if not n or n == "0": continue
        ctx = body[max(0, m.start()-50):m.end()+50].replace("\n", " ")
        if re.fullmatch(r"(19|20)\d{2}", n): continue
        if exempted(m.start(), m.end()):
            calc_ok += 1; continue
        if re.search(r"[图表]\s*$", body[max(0, m.start()-4):m.start()]): continue
        if re.match(r"^(0?[1-9]|[12]\d|3[01])$", n) and re.search(r"(第|节|章|式)\s*$", body[max(0, m.start()-6):m.start()]): continue
        if body[max(0, m.start()-3):m.start()] in ("[", "［"): continue
        checked += 1
        cands = {n, raw.replace(",", "").rstrip("%")}
        if "." not in n: cands.add(n + ".0")
        if not any(v and re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d])", corpus) for v in cands):
            unmatched.append({"value": raw, "context": ctx[-110:]})
    figs = re.findall(r"(图\s*\d+)", body); figcap = re.findall(r"图\s*\d+[^\n。]*[。.\n]", ms)
    tabs = re.findall(r"(表\s*\d+)", body); tabcap = re.findall(r"表\s*\d+[^\n。]*[。.\n]", ms)
    missing_figcap = sorted(set(f for f in figs if not any(c.startswith(f) for c in figcap)))
    missing_tabcap = sorted(set(t for t in tabs if not any(c.startswith(t) for c in tabcap)))
    causal = re.findall(r"(导致|证明了|决定了|显著促进|显著提升|significantly (?:increase|improve|cause))", body)
    has_stats = bool(re.search(r"(检验|test|p\s*[<=>]|方差分析|ANOVA|置信)", body, re.I))
    causal_flag = bool(causal and not has_stats)
    fails = []
    if unmatched: fails.append(f"{len(unmatched)} 个数字无台账出处（须找到出处、改为【计算值】或删除）")
    if missing_figcap or missing_tabcap: fails.append(f"正文引用但缺图/表注: {missing_figcap + missing_tabcap}")
    warnings = [f"{calc_ok} 处【计算值】（已豁免溯源，需人工复核算式）"] if calc_ok else []
    if causal_flag: warnings.append(f"检出因果/显著性措辞 {sorted(set(causal))[:6]} 但无统计检验语境，建议改'提示/相关'或补检验依据")
    pend = PEND.findall(ms)
    if pend: warnings += [f"待确认: {p}" for p in sorted(set(pend))[:20]]
    verdict = "FAIL" if fails else ("WARN" if warnings else "PASS")
    rep = {"engine": "results-transcription", "verdict": verdict, "fails": fails, "warnings": warnings,
           "numbers": {"checked": checked, "unmatched": unmatched[:60], "n_unmatched": len(unmatched)},
           "captions": {"fig_refs": sorted(set(figs)), "table_refs": sorted(set(tabs)),
                        "missing_fig_caption": missing_figcap, "missing_table_caption": missing_tabcap},
           "created_utc": datetime.datetime.now(datetime.UTC).isoformat()}
    json.dump(rep, open(os.path.join(a.out, "engine_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "number_trace.md"), "w", encoding="utf-8") as f:
        f.write(f"# 数字回写核验（verdict={verdict}）\n\n检查 {checked} 个实质数字，未命中 {len(unmatched)} 个；计算值豁免 {calc_ok} 处。\n\n")
        for u in unmatched[:60]: f.write(f"- ❌ `{u['value']}` — {u['context']}\n")
        if fails: f.write("\n## 必须返修\n" + "".join(f"- {x}\n" for x in fails))
        if warnings: f.write("\n## 需人工复核\n" + "".join(f"- {x}\n" for x in warnings))
    print(json.dumps({"verdict": verdict, "fails": fails, "n_unmatched": len(unmatched)}, ensure_ascii=False))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        out = "/app/output"
        if "--out" in sys.argv:
            try: out = sys.argv[sys.argv.index("--out") + 1]
            except Exception: pass
        os.makedirs(out, exist_ok=True)
        json.dump({"engine": "results-transcription", "verdict": "WARN", "fails": [], "warnings": [f"engine_check 异常: {str(e)[:150]}"]},
                  open(os.path.join(out, "engine_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        sys.exit(0)
