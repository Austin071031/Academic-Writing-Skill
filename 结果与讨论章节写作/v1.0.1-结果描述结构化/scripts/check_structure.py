#!/usr/bin/env python3
"""check_structure.py — 结果/讨论章节结构自检脚本。

用法:
  python3 check_structure.py --text section.md --outline outline.md --out report.json

判定（report 中每条给出 pass/fail 与定位）:
  R1 结果部分解释性词汇扫描: suggests that / indicates that / 表明 / 由于 / 因为 / 提示……机制 等
  R2 结果部分因果性词汇扫描: 导致 / 引起 / leads to / results in / due to
  R3 结果部分评价性词汇扫描: 令人惊讶 / 有趣 / remarkably / interestingly / importantly
  R4 结果部分每个段落须含 ≥1 图表锚点 (图N / Fig. N / 表N / Table N)
  R5 结果部分段落长度均衡: max/min 字数比 ≤ 5
  R6 讨论部分机制推测标注: 出现 推测|可能机制|speculat 时, 句内或相邻句须有标注
  R7 outline 发现编号在正文中全部出现
退出码: 0 = 全部通过; 1 = 存在 fail。
仅依赖 Python 3 标准库。
"""
import argparse
import json
import re
import sys

INTERPRETIVE = [
    r"表明", r"说明", r"暗示", r"提示.{0,6}机制", r"这意味着", r"由此可见",
    r"suggests?\s+that", r"indicates?\s+that", r"implies?\s+that", r"demonstrates?\s+that",
    r"is consistent with the notion", r"reflects?",
]
CAUSAL = [
    r"导致", r"引起", r"造成", r"归因于", r"由于.{0,12}(导致|引起)",
    r"leads?\s+to", r"results?\s+in", r"gives?\s+rise\s+to", r"owing\s+to", r"due\s+to",
]
NEGATION = re.compile(r"未|没有|无|不再|no\s+|not\s+|did\s+not|without", re.I)
EVALUATIVE = [
    r"令人惊讶", r"出人意料", r"有趣的是", r"值得注意的是", r" importantly,? ",
    r"interestingly,? ", r"remarkably,? ", r"surprisingly,? ", r"notably,? ",
]
SPECULATION = [r"推测", r"可能机制", r"speculat", r"we believe", r"可能解释"]
SPECULATION_MARK = [r"推测.{0,4}待验证", r"speculation.{0,20}test", r"待验证", r"有待", r"to be (tested|confirmed|validated)"]
ANCHOR = re.compile(r"(图\s?\d|Fig(?:ure)?\.?\s*\d|表\s?\d|Table\s+\d|图S\d|Table\s*S\d)")
F_REF = re.compile(r"\bF(\d+)\b")


def split_sentences(text: str):
    protected = re.sub(r"(\d)\.(\d)", r"\1DOT\2", text)
    parts = re.split(r"(?<=[。！？；.!?;])\s*", protected)
    return [p.replace("DOT", ".").strip() for p in parts if p.strip()]


def split_sections(text: str):
    """按常见小节标题切分结果/讨论。"""
    results, discussion = [], []
    cur = None
    for line in text.splitlines():
        h = re.match(r"^#{1,4}\s*(.+)$", line)
        if h:
            title = h.group(1)
            if re.search(r"结果|Results?", title, re.I) and not re.search(r"讨论|Discussion", title, re.I):
                cur = results
            elif re.search(r"讨论|Discussion", title, re.I):
                cur = discussion
            continue
        if cur is not None:
            cur.append(line)
    if not results and not discussion:
        return None, None
    return "\n".join(results).strip(), "\n".join(discussion).strip()


def scan(patterns, sentences, label):
    hits = []
    for i, s in enumerate(sentences):
        for p in patterns:
            if re.search(p, s, re.I):
                hits.append({"rule": label, "sentence_index": i, "pattern": p, "text": s[:120]})
                break
    return hits


def paras(block: str):
    return [p.strip() for p in re.split(r"\n\s*\n", block) if p.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--outline", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    text = open(args.text, encoding="utf-8").read()
    outline = open(args.outline, encoding="utf-8").read()
    res, disc = split_sections(text)
    report = {"checks": []}
    fails = 0

    def add(rule, ok, detail):
        nonlocal fails
        report["checks"].append({"rule": rule, "pass": bool(ok), "detail": detail})
        if not ok:
            fails += 1

    if res is None and disc is None:
        add("SECTION_SPLIT", False, "未识别到'结果'/'讨论'小节标题，无法自检；请使用 ## 结果 / ## Discussion 形式标注")
    else:
        add("SECTION_SPLIT", True, "已识别结果与讨论小节")
        res_sents = split_sentences(res)
        add("R1_INTERPRETIVE_IN_RESULTS", not scan(INTERPRETIVE, res_sents, "interpretive"),
            scan(INTERPRETIVE, res_sents, "interpretive")[:5])
        causal_hits = [h for h in scan(CAUSAL, res_sents, "causal")
                       if not NEGATION.search(h["text"])]
        add("R2_CAUSAL_IN_RESULTS", not causal_hits, causal_hits[:5])
        add("R3_EVALUATIVE_IN_RESULTS", not scan(EVALUATIVE, res_sents, "evaluative"),
            scan(EVALUATIVE, res_sents, "evaluative")[:5])
        ps = paras(res)
        no_anchor = [i for i, p in enumerate(ps) if not ANCHOR.search(p)]
        add("R4_PARAGRAPH_ANCHOR", not no_anchor, {"paragraphs_without_anchor": no_anchor})
        if len(ps) >= 2:
            lens = [len(p) for p in ps]
            ratio = max(lens) / max(1, min(lens))
            add("R5_PARAGRAPH_BALANCE", ratio <= 5.0, {"lengths": lens, "ratio": round(ratio, 2)})

        if disc:
            disc_sents = split_sentences(disc)
            spec_hits = []
            for i, s in enumerate(disc_sents):
                if re.search("|".join(SPECULATION), s, re.I):
                    window = s + (disc_sents[i + 1] if i + 1 < len(disc_sents) else "")
                    if not re.search("|".join(SPECULATION_MARK), window):
                        spec_hits.append({"sentence_index": i, "text": s[:120]})
            add("R6_SPECULATION_MARKED", not spec_hits, spec_hits[:5])
        else:
            add("R6_SPECULATION_MARKED", False, "未找到讨论部分")

    f_ids = set(F_REF.findall(outline))
    if f_ids:
        missing = [fid for fid in sorted(f_ids, key=int) if not re.search(rf"\bF{fid}\b", text)]
        add("R7_FINDINGS_COVERAGE", not missing, {"missing_findings": missing})
    else:
        add("R7_FINDINGS_COVERAGE", True, "outline 中未发现 F 编号发现条目，跳过")

    report["summary"] = {"total": len(report["checks"]), "failed": fails,
                         "verdict": "PASS" if fails == 0 else "FAIL"}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
