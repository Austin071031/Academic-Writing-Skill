#!/usr/bin/env python3
r"""check_calibration.py — 趋势与差异表述校准自检脚本。

用法:
  python3 check_calibration.py --text section.md --comparisons comparisons.md --out report.json

判定:
  C1 强断言词(显著/大幅/明显/significantly/markedly/dramatically/substantially)
     所在句必须含统计锚 (p\s*[<=>] 或 n\s*= 或 CI 或 ± 或 数字+%)
  C2 若 comparisons.md 中全部 p 值缺失, 正文不得出现"显著"
  C3 comparisons.md 中标级 2(无显著差异)的比较, 正文不得用方向性结论词
     (高于/低于/增加/降低/increase/decrease/higher/lower) 描述该对比较
  C4 标级 4(单条件现象): 引用其数值的句子须含限定词 (仅/只有/只在/only)
  C5 比较句须有基线: 句中既有方向词又含两组数值, 或含 vs/compared with 结构
退出码: 0 = 全部通过; 1 = 存在 fail。
仅依赖 Python 3 标准库。
"""
import argparse
import json
import re
import sys

STRONG = [r"显著", r"大幅", r"明显", r"急剧", r"明显?高于", r"明显?低于",
          r"significantly", r"markedly", r"dramatically", r"substantially", r"drastically"]
STAT_ANCHOR = re.compile(r"(p\s*[<≤>=]|\bn\s*=|CI|±|\d+(?:\.\d+)?\s*%)", re.I)
DIRECTION = [r"高于", r"低于", r"增加", r"降低", r"升高", r"下降",
             r"increas", r"decreas", r"higher", r"lower", r"elevat", r"rais", r"reduc"]
LIMITING = [r"仅", r"只有", r"只在", r"only"]
COMP_ID = re.compile(r"\bC(\d+)\b")


def sentences(text):
    # 先保护小数点中的 ".", 再按中英文句读切分
    protected = re.sub(r"(\d)\.(\d)", r"\1DOT\2", text)
    parts = re.split(r"(?<=[。！？；.!?;])\s*", protected)
    return [s.replace("DOT", ".").strip() for s in parts if s.strip()]


def parse_comparisons(path):
    """从 comparisons.md 提取: {cid: {'level': int, 'p': float|None}}"""
    out = {}
    try:
        content = open(path, encoding="utf-8").read()
    except OSError:
        return out
    for m in re.finditer(r"C(\d+)\b(.*?)(?:\n|$)", content):
        cid, rest = m.group(1), m.group(2)
        lvl = re.search(r"级\s*(\d)", rest)
        p = re.search(r"p\s*=\s*([0-9.]+)", rest)
        out[cid] = {"level": int(lvl.group(1)) if lvl else None,
                    "p": float(p.group(1)) if p else None}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--comparisons", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    text = open(args.text, encoding="utf-8").read()
    sents = sentences(text)
    comps = parse_comparisons(args.comparisons)
    report = {"checks": []}
    fails = 0

    def add(rule, ok, detail):
        nonlocal fails
        report["checks"].append({"rule": rule, "pass": bool(ok), "detail": detail})
        if not ok:
            fails += 1

    # C1 强断言 + 统计锚
    c1_hits = []
    for i, s in enumerate(sents):
        if re.search("|".join(STRONG), s, re.I) and not STAT_ANCHOR.search(s):
            c1_hits.append({"sentence_index": i, "text": s[:140]})
    add("C1_STRONG_CLAIM_HAS_STAT", not c1_hits, c1_hits[:8])

    # C2 无 p 值材料禁用"显著"
    pvals = [c["p"] for c in comps.values() if c.get("p") is not None]
    if not pvals:
        sig_hits = [{"sentence_index": i, "text": s[:140]} for i, s in enumerate(sents)
                    if re.search(r"显著|significant", s, re.I)]
        add("C2_NO_SIGNIFICANCE_WITHOUT_P", not sig_hits,
            {"note": "comparisons.md 中无任何 p 值", "hits": sig_hits[:8]})
    else:
        add("C2_NO_SIGNIFICANCE_WITHOUT_P", True, "存在 p 值记录，跳过")

    # C3 级2比较禁用方向结论（正文整体扫描: 若正文引用该比较的数值对）
    c3_hits = []
    for cid, c in comps.items():
        if c.get("level") != 2:
            continue
        # 在正文中找同时含该 CID 数值上下文的句子（简化: 用 CID 注释锚 <!-- C1 --> 或句中含该对 p 值）
        pat_p = re.compile(rf"p\s*=\s*{re.escape(str(c['p']))}\b") if c.get("p") is not None else None
        for i, s in enumerate(sents):
            tagged = re.search(rf"<!--\s*C{cid}\s*-->", s) or (pat_p and pat_p.search(s))
            if tagged and re.search("|".join(DIRECTION), s, re.I) and not re.search(r"无显著|无统计|no significant|did not", s, re.I):
                c3_hits.append({"comparison": f"C{cid}", "sentence_index": i, "text": s[:140]})
    add("C3_NONSIG_NOT_DIRECTIONAL", not c3_hits, c3_hits[:8])

    # C4 级4单条件现象须限定
    c4_hits = []
    for cid, c in comps.items():
        if c.get("level") != 4:
            continue
        for i, s in enumerate(sents):
            if re.search(rf"<!--\s*C{cid}\s*-->", s) and not re.search("|".join(LIMITING), s):
                c4_hits.append({"comparison": f"C{cid}", "sentence_index": i, "text": s[:140]})
    add("C4_SINGLE_CONDITION_LIMITED", not c4_hits, c4_hits[:8])

    # C5 比较句基线检查: 方向句须含至少两个数值 或 引用标记
    c5_hits = []
    two_nums = re.compile(r"\d+(?:\.\d+)?.*(?:vs|与|相比|\bversus\b).*\d+(?:\.\d+)?|\d+(?:\.\d+)?\s*[–-]\s*\d+(?:\.\d+)?", re.I)
    for i, s in enumerate(sents):
        if re.search("|".join(DIRECTION), s, re.I) and "<!--" not in s:
            nums = re.findall(r"\d+(?:\.\d+)?", s)
            if len(nums) < 2 and not re.search(r"(图|Fig(?:ure)?\.?|表|Table)\s*\S*\d", s):
                c5_hits.append({"sentence_index": i, "text": s[:140]})
    add("C5_COMPARISON_HAS_BASELINE", not c5_hits, c5_hits[:8])

    report["summary"] = {"total": len(report["checks"]), "failed": fails,
                         "verdict": "PASS" if fails == 0 else "FAIL"}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
