#!/usr/bin/env python3
"""check_causal.py — 因果越界与局限完整性审计脚本。

用法:
  python3 check_causal.py --text section.md --design design_notes.md --out report.json

判定:
  A1 因果动词(导致/引起/造成/证明/决定/归因于/leads to/results in/proves/demonstrates that)
     所在句: design_notes.md 中须有对应级B(K编号)登记, 或句内含降级标记
     (推测/可能/提示/有待/待验证/may/might/suggest/speculat/potentially), 否则 fail
  A2 结果部分不得出现机制词汇(机制/通路/介导/通过...起作用/mediate/mechanism/pathway)
  A3 局限部分覆盖四层: 方法/样本/测量/统计(或 method/sample/measurement/statistic),
     每层至少一条
  A4 每条局限须含改进方向(未来|可|有待|下一步|future|further|next)
退出码: 0 = 全部通过; 1 = 存在 fail。
仅依赖 Python 3 标准库。
"""
import argparse
import json
import re
import sys

CAUSAL = [r"导致", r"引起", r"造成", r"证明[了了]?", r"决定[了]?", r"归因于",
          r"leads?\s+to", r"results?\s+in", r"gives?\s+rise\s+to", r"proves?\s+that",
          r"demonstrates?\s+that", r"is responsible for"]
DOWNGRADE = [r"推测", r"可能", r"提示", r"有待", r"待验证", r"尚待", r"或许",
             r"may\b", r"might\b", r"suggest", r"speculat", r"potentially", r"could\b",
             r"plausib", r"cannot rule out"]
MECH = [r"机制", r"通路", r"介导", r"通过.{0,10}(起作用|发挥作用|调控)", r"mediat", r"mechanism", r"pathway"]
LAYERS = {
    "method": [r"方法", r"method", r"设计", r"design", r"流程", r"protocol"],
    "sample": [r"样本", r"sample", r"队列", r"cohort", r"受试者", r"participant", r"subjects?"],
    "measurement": [r"测量", r"measure", r"检测限", r"检出", r"仪器", r"assay", r"observer"],
    "statistics": [r"统计", r"statistic", r"检验效能", r"power", r"多重比较", r"multiple comparison", r"混杂", r"confound"],
}
IMPROVE = re.compile(r"未来|可|有待|下一步|需|应|future|further|next|should|could", re.I)
K_LEVEL_B = re.compile(r"K\d+.*级\s*B|K\d+.*level\s*B", re.I)


def sentences(text):
    # 先保护小数点中的 ".", 再按中英文句读切分
    protected = re.sub(r"(\d)\.(\d)", r"\1DOT\2", text)
    parts = re.split(r"(?<=[。！？；.!?;])\s*", protected)
    return [s.replace("DOT", ".").strip() for s in parts if s.strip()]


def split_sections(text):
    results, discussion, cur = [], [], None
    for line in text.splitlines():
        h = re.match(r"^#{1,4}\s*(.+)$", line)
        if h:
            t = h.group(1)
            if re.search(r"结果|Results?", t, re.I) and not re.search(r"讨论|Discussion", t, re.I):
                cur = results
            elif re.search(r"讨论|Discussion", t, re.I):
                cur = discussion
            continue
        if cur is not None:
            cur.append(line)
    return "\n".join(results).strip(), "\n".join(discussion).strip()


def extract_limitations(discussion: str):
    """从讨论段切出局限小节（'局限'/'limitation' 标题或段落开头词）。"""
    m = re.search(r"(局限|limitation).{0,20}\n(.*?)(?=\n#{1,4}|\Z)", discussion, re.I | re.S)
    if m:
        return m.group(2)
    # 退化: 找到首个含"局限/limitation"的段落块, 取该块至段末
    blocks = re.split(r"\n\s*\n", discussion)
    for i, b in enumerate(blocks):
        if re.search(r"局限|limitation", b, re.I):
            return "\n".join(blocks[i:])
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--design", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    text = open(args.text, encoding="utf-8").read()
    design = open(args.design, encoding="utf-8").read()
    res, disc = split_sections(text)
    has_level_b = bool(K_LEVEL_B.search(design))
    report = {"checks": []}
    fails = 0

    def add(rule, ok, detail):
        nonlocal fails
        report["checks"].append({"rule": rule, "pass": bool(ok), "detail": detail})
        if not ok:
            fails += 1

    # A1 因果动词审计
    a1_hits = []
    for i, s in enumerate(sentences(text)):
        if re.search("|".join(CAUSAL), s, re.I):
            has_down = re.search("|".join(DOWNGRADE), s, re.I)
            has_k = re.search(r"<!--\s*K\d+\s*-->", s)
            if not has_down and not (has_k and has_level_b):
                a1_hits.append({"sentence_index": i, "text": s[:150]})
    add("A1_CAUSAL_VERB_AUDIT", not a1_hits,
        {"hits": a1_hits[:10], "note": "design_notes 含级B登记: %s" % has_level_b})

    # A2 结果段机制词汇
    a2_hits = []
    if res:
        for i, s in enumerate(sentences(res)):
            if re.search("|".join(MECH), s, re.I):
                a2_hits.append({"sentence_index": i, "text": s[:150]})
    add("A2_NO_MECHANISM_IN_RESULTS", not a2_hits, a2_hits[:10])

    # A3 局限四层覆盖
    lim = extract_limitations(disc or text)
    missing_layers = []
    for layer, pats in LAYERS.items():
        if not re.search("|".join(pats), lim, re.I):
            missing_layers.append(layer)
    add("A3_LIMITATION_LAYERS", not missing_layers,
        {"missing": missing_layers, "limitations_excerpt": lim[:300]})

    # A4 改进方向
    lim_sents = sentences(lim) if lim else []
    no_improve = [s[:150] for s in lim_sents
                  if re.search(r"局限|不足|限制", s) and not IMPROVE.search(s)]
    add("A4_LIMITATION_HAS_REMEDY", not no_improve, no_improve[:10])

    report["summary"] = {"total": len(report["checks"]), "failed": fails,
                         "verdict": "PASS" if fails == 0 else "FAIL"}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
