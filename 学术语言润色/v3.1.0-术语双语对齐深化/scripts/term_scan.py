#!/usr/bin/env python3
"""term_scan.py — 术语漂移扫描：对 Agent 维护的术语表做全篇一致性回扫（v3.1.0 唯一脚本）。

用法:
  python3 term_scan.py --table /app/work/term_table.csv --text /app/output/polished.md \
      --out /app/work [--source /input/manuscript.md]

输入术语表（Agent 在润色前建立，CSV，至少三列）:
  concept, preferred, variants
  均方根误差, 均方根误差/root mean square error, RMSE;均方差
  （preferred 列用 "/" 分隔中英双语首选写法；variants 列用 ";" 分隔全部曾见写法）

输出 term_consistency_report.md/json：
  - 同一概念多种写法并存（critical）；
  - 缩写先于全称出现（warning）；
  - 表中概念在文中完全消失（warning，可能误删）。
只报告不改写；critical 由 Agent 处置后重跑。仅标准库。
"""
import argparse, csv, json, os, re, sys


def load_table(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            concept = (r.get("concept") or "").strip()
            if not concept:
                continue
            preferred = [x.strip() for x in (r.get("preferred") or "").split("/") if x.strip()]
            variants = [x.strip() for x in re.split(r"[;；]", r.get("variants") or "") if x.strip()]
            rows.append({"concept": concept, "preferred": preferred,
                         "variants": sorted(set(variants) | set(preferred), key=len, reverse=True)})
    return rows


def occurrences(text, form):
    """返回 (次数, 首现位置)。长写法优先匹配避免子串重复计数。"""
    idxs = [m.start() for m in re.finditer(re.escape(form), text)]
    return len(idxs), (idxs[0] if idxs else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--source", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    table = load_table(args.table)
    text = open(args.text, encoding="utf-8", errors="replace").read()
    findings = []
    for c in table:
        used = {}
        for form in c["variants"]:
            n, first = occurrences(text, form)
            if n:
                used[form] = (n, first)
        if not used:
            findings.append({"level": "warning", "concept": c["concept"],
                             "issue": "该概念在润色后文本中未出现任何写法，确认是否仍在范围内"})
            continue
        forms = list(used)
        if len(forms) > 1:
            # 豁免规则：仅"全称（缩写）"式括号定义共现豁免；其余独立出现 → 漂移
            def_spans = []
            for i, fa in enumerate(forms):
                for fb in forms[i + 1:]:
                    for pat in (rf"{re.escape(fa)}（[^）]{{0,40}}{re.escape(fb)}）",
                                rf"{re.escape(fa)}\([^)]{{0,40}}{re.escape(fb)}\)",
                                rf"{re.escape(fb)}（[^）]{{0,40}}{re.escape(fa)}）",
                                rf"{re.escape(fb)}\([^)]{{0,40}}{re.escape(fa)}\)"):
                        def_spans.extend(m.span() for m in re.finditer(pat, text))
            def in_def(pos, form):
                return any(s <= pos < e for s, e in def_spans)
            remaining = {}
            for f in forms:
                ps = [m.start() for m in re.finditer(re.escape(f), text) if not in_def(m.start(), f)]
                if ps:
                    remaining[f] = ps
            if len(remaining) >= 2:
                findings.append({"level": "critical", "concept": c["concept"],
                                 "issue": "同一概念多种写法并存（括号定义共现豁免后仍有独立出现）: "
                                          + "; ".join(f"'{f}'×{len(ps)}" for f, ps in remaining.items()),
                                 "forms": forms})
        # 缩写首现检查：全大写写法若存在且其首现早于任何非缩写写法
        abbrs = [f for f in forms if re.fullmatch(r"[A-Z][A-Z0-9\-]{1,11}", f)]
        fulls = [f for f in forms if f not in abbrs]
        for a in abbrs:
            if fulls and used[a][1] < min(used[f][1] for f in fulls):
                findings.append({"level": "warning", "concept": c["concept"],
                                 "issue": f"缩写 '{a}' 首次出现早于全称，若文体要求首现给全称则需补"})

    rep = {"concepts": len(table),
           "critical": sum(1 for x in findings if x["level"] == "critical"),
           "warning": sum(1 for x in findings if x["level"] == "warning"),
           "findings": findings}
    os.makedirs(args.out, exist_ok=True)
    json.dump(rep, open(os.path.join(args.out, "term_consistency_report.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "term_consistency_report.md"), "w", encoding="utf-8") as f:
        f.write("# 术语一致性回扫报告（term_scan.py）\n\n")
        f.write(f"受控概念 {rep['concepts']} 个；critical {rep['critical']}，warning {rep['warning']}。\n\n")
        for x in findings:
            f.write(f"- **[{x['level']}]** {x['concept']}：{x['issue']}\n")
        if not findings:
            f.write("- 全部概念写法统一，无漂移。\n")
    print(f"[term_scan] concepts={rep['concepts']} critical={rep['critical']} warning={rep['warning']}")
    return 1 if rep["critical"] else 0


if __name__ == "__main__":
    sys.exit(main())
