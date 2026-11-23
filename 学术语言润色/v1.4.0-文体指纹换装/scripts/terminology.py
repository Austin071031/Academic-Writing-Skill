#!/usr/bin/env python3
"""terminology.py — 术语表构建（build）与全篇一致性回扫（check）。

用法:
  python3 terminology.py build  --segments /app/work/source_segments.json --out /app/work \
      [--provided /input/术语表.csv]
  python3 terminology.py check  --segments /app/work/polished_segments.json \
      --table /app/work/term_table.csv --out /app/work

build: 从源文本抽取候选术语（缩写定义、高频复合词、中文术语），生成 term_table.csv。
check: 对润色后文本做全篇回扫——变体拼写、缩写首次出现形式、跨段漂移，输出
       consistency_report.md/json。只报告，不改写；所有冲突交由 Agent 处置。
"""
import argparse, csv, json, os, re, sys
from collections import defaultdict

# 缩写定义模式: Full Name (ABBR) / 中文全称（ABBR）/ ABBR (中文全称) / 中文全称（English, ABBR）
RE_EN_FULL_ABBR = re.compile(r"([A-Za-z][A-Za-z0-9\-/ ]{2,60}?)\s*\(([A-Z][A-Za-z0-9\-]{1,12})\)")
RE_ZH_FULL_ABBR = re.compile(r"([一-鿿][一-鿿0-9\-]{1,15})（([A-Z][A-Za-z0-9]{1,12})）")
RE_ZH_EN_ABBR = re.compile(
    r"([一-鿿]{2,12})（([A-Za-z][A-Za-z0-9\- ]{2,50}?),\s*([A-Z][A-Za-z0-9\-]{1,12})）")
RE_ABBR_ZH = re.compile(r"([A-Z][A-Za-z0-9\-]{1,12})\s*[（(]([一-鿿][一-鿿0-9\-]{1,15})[）)]")
RE_LEAD_CTX = re.compile(
    r"^(?:随着|基于|通过|采用|利用|使用|在|对|将|把|由|从|和|与|及|以及|关于|对于|由于|"
    r"针对|结合|相比|上述|该|此|其|所述|一种|这种|新的|的)+")


def clean_zh_full(form):
    """去掉抽入术语前缀的语境词与定语：'模型的均方根误差'->'均方根误差'，'随着深度学习'->'深度学习'。"""
    form = RE_LEAD_CTX.sub("", form)
    idx = form.rfind("的", 0, 6)
    if 0 <= idx and len(form[idx + 1:]) >= 2:
        form = form[idx + 1:]
    return form
RE_LEAD_MOD = re.compile(r"^(?:的|该|此|其|上述|这种|一种|新的|所述)+")
RE_CJK = re.compile(r"[一-鿿]")

# 中文术语后缀（领域通用，宁缺毋滥）
ZH_TERM_SUFFIX = ("学|性|率|法|模型|算法|效应|机制|蛋白|细胞|基因|酶|载体|催化剂|"
                  "材料|结构|函数|方程|定理|准则|指标|系数|分布|过程|系统|网络|节点|"
                  "能量|势|场|谱|峰|相|晶|键|分子|离子|电子|光子|声子|激子")
RE_ZH_TERM = re.compile(rf"[一-鿿]{{2,10}}(?:{ZH_TERM_SUFFIX})")
RE_EN_TERM = re.compile(r"\b[A-Z][a-z]+(?:[- ][A-Z]?[a-z0-9]+){1,3}\b")


def load_segments(path):
    with open(path, encoding="utf-8") as f:
        segs = json.load(f)
    rows = []
    for seg in segs:
        if seg.get("kind") in ("math", "fence"):
            continue
        for si, s in enumerate(seg.get("sentences") or [seg.get("text", "")], 1):
            sid = f"{seg['id']}-S{si}" if len(seg.get("sentences") or []) > 1 else seg["id"]
            rows.append({"sid": sid, "text": s})
    return rows


def find_occurrences(rows, surface):
    occ = []
    for r in rows:
        if surface and surface in r["text"]:
            occ.append(r["sid"])
    return occ


def cmd_build(args):
    rows = load_segments(args.segments)
    corpus = "\n".join(r["text"] for r in rows)
    concepts = {}  # key -> {preferred, abbreviation, variants:{form:[sids]}, source, note}

    def add_concept(key, full, abbr, sid, source):
        c = concepts.setdefault(key, {"preferred": full, "abbreviation": abbr or "",
                                      "variants": defaultdict(list), "source": source, "note": ""})
        c["variants"][full].append(sid)
        if abbr:
            c["variants"][abbr].append(sid)
        return c

    for r in rows:
        t = r["text"]
        for m in RE_EN_FULL_ABBR.finditer(t):
            full, abbr = m.group(1).strip(), m.group(2)
            if RE_CJK.search(full) or len(full.split()) > 6:
                continue
            add_concept(full.lower(), full, abbr, r["sid"], "英文全称(缩写)定义")
        for m in RE_ZH_FULL_ABBR.finditer(t):
            full = clean_zh_full(m.group(1))
            add_concept(f"zh:{full}", full, m.group(2), r["sid"], "中文全称（缩写）定义")
        for m in RE_ZH_EN_ABBR.finditer(t):
            full = clean_zh_full(m.group(1))
            c = add_concept(f"zh:{full}", full, m.group(3), r["sid"], "中文全称（English, 缩写）定义")
            if c is not None:
                c["variants"][m.group(2)].append(r["sid"])
        for m in RE_ABBR_ZH.finditer(t):
            add_concept(f"zh:{m.group(2)}", m.group(2), m.group(1), r["sid"], "缩写（中文全称）定义")

    # 高频复合词候选（出现 >=2 次），仅作候选，交由 Agent 审阅
    for pat, kind in ((RE_ZH_TERM, "zh_term"), (RE_EN_TERM, "en_term")):
        counts = defaultdict(list)
        for r in rows:
            for m in pat.finditer(r["text"]):
                counts[m.group(0)].append(r["sid"])
        for form, sids in counts.items():
            if len(sids) >= 2 and form.lower() not in concepts:
                key = f"cand:{form.lower()}"
                concepts[key] = {"preferred": form, "abbreviation": "",
                                 "variants": {form: sids}, "source": f"高频候选({kind},出现{len(sids)}次)",
                                 "note": "候选术语，需 Agent 确认是否为受控概念"}

    # 无显式定义的裸缩写（首次出现需补全称时报告）
    defined = {c["abbreviation"].lower() for c in concepts.values() if c["abbreviation"]}
    abbr_counts = defaultdict(list)
    for r in rows:
        for m in re.finditer(r"\b([A-Z][A-Z0-9]{1,9})\b", r["text"]):
            w = m.group(1)
            if w in ("ID", "RE", "PDF", "URL", "JSON", "NOTE", "TBD", "OK"):
                continue
            abbr_counts[w].append(r["sid"])
    for w, sids in abbr_counts.items():
        if w.lower() not in defined and len(sids) >= 2:
            concepts.setdefault(f"undef:{w.lower()}", {
                "preferred": w, "abbreviation": w,
                "variants": {w: sids}, "source": "未定义缩写(出现%d次)" % len(sids),
                "note": "未见全称定义；若目标文体要求首次出现给全称，应补或确认"})

    # 案例自带术语表合并
    provided_rows = []
    if args.provided and os.path.exists(args.provided):
        with open(args.provided, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip().strip("|")
                cells = [c.strip() for c in re.split(r"[,，\t|]", line) if c.strip()]
                if len(cells) >= 2 and not line.startswith("#"):
                    provided_rows.append(cells)
        for cells in provided_rows:
            key = f"provided:{cells[0].lower()}"
            c = concepts.setdefault(key, {"preferred": cells[0], "abbreviation": cells[1] if len(cells) > 2 else "",
                                          "variants": defaultdict(list),
                                          "source": "案例自带术语表", "note": ""})
            c["preferred"] = cells[0]
            if len(cells) > 2:
                c["abbreviation"] = cells[2] if cells[2].isupper() or re.match(r"^[A-Z]", cells[2]) else cells[1]
            for form in cells[:3]:
                if form:
                    c["variants"][form].extend(find_occurrences(rows, form))

    out_csv = os.path.join(args.out, "term_table.csv")
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["concept_key", "preferred_form", "abbreviation", "variant_forms", "occurrences",
                    "source", "status", "note"])
        for key in sorted(concepts):
            c = concepts[key]
            variants = dict(c["variants"])
            occ = sorted({s for v in variants.values() for s in v})
            status = "case_provided" if key.startswith("provided:") else (
                "defined" if "定义" in c["source"] else "candidate")
            w.writerow([key, c["preferred"], c["abbreviation"],
                        "; ".join(f"{k}×{len(v)}" for k, v in sorted(variants.items())),
                        f"{len(occ)}处:{' '.join(occ[:8])}{'…' if len(occ) > 8 else ''}",
                        c["source"], status, c["note"]])
    n_def = sum(1 for k, c in concepts.items() if "定义" in c["source"] or k.startswith("provided:"))
    print(f"[terminology build] concepts={len(concepts)} defined={n_def} candidates="
          f"{len(concepts) - n_def} -> {out_csv}")
    if provided_rows:
        print(f"[terminology build] 合并案例自带术语表 {len(provided_rows)} 条: {args.provided}")


def cmd_check(args):
    rows = load_segments(args.segments)
    with open(args.table, encoding="utf-8") as f:
        table = list(csv.DictReader(f))
    findings = []
    for c in table:
        variants = [v.split("×")[0].strip() for v in (c["variant_forms"] or "").split(";") if v.strip()]
        preferred = c["preferred_form"]
        used = {}
        for v in set(variants) | ({preferred} if preferred else set()):
            occ = find_occurrences(rows, v)
            if occ:
                used[v] = occ
        if not used:
            if c["status"] in ("defined", "case_provided"):
                findings.append({"level": "warning", "concept": preferred,
                                 "issue": "润色后文本中未出现该术语的任何变体，确认是否仍在范围内",
                                 "forms": variants})
            continue
        forms = list(used)
        if len(forms) > 1:
            all_sids = {s for f in forms for s in used[f]}
            # 仅首次定义处共现（全部出现集中在 <=2 个句子、且至多一种形式复现）属正常缩写定义，不报冲突
            if len(all_sids) > 2 or sum(1 for f in forms if len(used[f]) > 1) >= 2:
                first_sids = {f: min(used[f]) for f in forms}
                findings.append({"level": "critical", "concept": preferred,
                                 "issue": "同一概念多种写法并存: " +
                                          "; ".join(f"{f}({len(used[f])}处,首见{first_sids[f]})"
                                                    for f in forms),
                                 "forms": forms})
        elif forms[0] != preferred:
            findings.append({"level": "warning", "concept": preferred,
                             "issue": f"仅出现非首选写法 '{forms[0]}'（首选 '{preferred}'），需确认是否统一",
                             "forms": forms})
        # 缩写首次出现形式
        abbr = c["abbreviation"]
        if abbr and abbr in used:
            first_abbr = min(used[abbr])
            full_forms = [v for v in variants if v != abbr and v in used]
            first_full = min((min(used[v]) for v in full_forms), default=None)
            if first_full is None or first_abbr < first_full:
                findings.append({"level": "warning", "concept": preferred,
                                 "issue": f"缩写 '{abbr}' 的首次出现（{first_abbr}）未见全称同现，"
                                          f"若文体要求首次出现给全称则需补", "forms": forms})
    rep = {"checked_concepts": len(table), "findings": findings,
           "critical": sum(1 for x in findings if x["level"] == "critical"),
           "warning": sum(1 for x in findings if x["level"] == "warning")}
    with open(os.path.join(args.out, "consistency_report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "consistency_report.md"), "w", encoding="utf-8") as f:
        f.write("# 术语一致性回扫报告（terminology.py check，机械扫描）\n\n")
        f.write(f"受控概念 {rep['checked_concepts']} 个；critical {rep['critical']} 条，warning {rep['warning']} 条。\n\n")
        for x in findings:
            f.write(f"- **[{x['level']}]** {x['concept']}：{x['issue']}\n")
        if not findings:
            f.write("- 未发现术语变体冲突或缩写首次出现形式问题。\n")
    print(f"[terminology check] concepts={rep['checked_concepts']} critical={rep['critical']} "
          f"warning={rep['warning']}")
    return 1 if rep["critical"] else 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--segments", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--provided", default=None, help="案例自带的术语表文件（csv/md 表格）")
    c = sub.add_parser("check")
    c.add_argument("--segments", required=True)
    c.add_argument("--table", required=True)
    c.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "build":
        cmd_build(args)
        return 0
    return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
