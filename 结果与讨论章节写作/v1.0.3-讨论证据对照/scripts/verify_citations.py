#!/usr/bin/env python3
"""verify_citations.py — 讨论段引用真实性与论断锚点核验脚本。

用法:
  python3 verify_citations.py --text section.md --matrix matrix.md \
      --refs reference_keys.json --out citation_report.json

判定:
  V1 正文引用匹配: (Author, Year) / Author et al. (Year) / Author (Year) / [n]
     逐条匹配 reference_keys.json（key 为姓氏, year 为年份）; 无匹配 → 疑似虚构引用
  V2 讨论部分论断句锚点: 每句须含 【数据:...】/【文献:...】/数据锚/文献锚 之一
     （观察性过渡句除外: 不含论断动词的句子自动豁免, 见 CITATION_RULES）
  V3 矩阵中类型为"文献"的行, 关系列（一致/不一致/部分一致）非空
  V4 矩阵中类型为"推测"的行, 正文相应句须含 "推测, 尚待验证" 或 "speculation" 标注
退出码: 0 = 全部通过; 1 = 存在 fail。
仅依赖 Python 3 标准库。
"""
import argparse
import json
import re
import sys

CITE_PATTERNS = [
    re.compile(r"([A-Z][A-Za-zÀ-ÿ'\-]+)(?:\s+et\s+al\.?|\s+and\s+[A-Z][A-Za-zÀ-ÿ'\-]+|\s+等)?\s*[（(]((?:19|20)\d{2})[）)]"),
    re.compile(r"([A-Z][A-Za-zÀ-ÿ'\-]+)\s*\[(\d{1,3})\]"),
    re.compile(r"[（(]([A-Z][A-Za-zÀ-ÿ'\-]+)(?:\s+et\s+al\.?)?,?\s*((?:19|20)\d{2})[）)]"),
]
CLAIM_VERBS = re.compile(
    r"表明|说明|显示|证实|提示|支持|与.{0,8}(一致|相反)|差异可能|可能源|推测|我们(认为|提出)|表明|demonstrat|"
    r"suggest|indicat|show|support|consistent with|contrary|in contrast|we speculat|we propose", re.I)
ANCHOR = re.compile(r"【(数据|文献)[:：][^】]+】|\[(数据|文献)\]")
SPEC_MARK = re.compile(r"推测.{0,6}待验证|speculation.{0,25}test|尚待验证|to be (tested|confirmed|validated)")


def extract_citations(text):
    cites = []
    for pat in CITE_PATTERNS:
        for m in pat.finditer(text):
            key = m.group(1)
            year_or_num = m.group(2)
            cites.append({"key": key, "ref": year_or_num, "pos": m.start()})
    # 去重（同位置）
    seen, out = set(), []
    for c in cites:
        if (c["key"], c["ref"]) not in seen:
            seen.add((c["key"], c["ref"]))
            out.append(c)
    return out


def split_sections(text):
    results, discussion, cur = [], [], None
    for line in text.splitlines():
        h = re.match(r"^#{1,4}\s*(.+)$", line)
        if h:
            t = h.group(1)
            if re.search(r"讨论|Discussion", t, re.I):
                cur = discussion
            elif re.search(r"结果|Results?", t, re.I):
                cur = results
            continue
        if cur is not None:
            cur.append(line)
    return "\n".join(results).strip(), "\n".join(discussion).strip()


def sentences(text):
    # 先保护小数点中的 ".", 再按中英文句读切分
    protected = re.sub(r"(\d)\.(\d)", r"\1DOT\2", text)
    parts = re.split(r"(?<=[。！？；.!?;])\s*", protected)
    return [s.replace("DOT", ".").strip() for s in parts if s.strip()]


def parse_matrix(path):
    lit_rows, spec_rows = [], []
    try:
        content = open(path, encoding="utf-8").read()
    except OSError:
        return lit_rows, spec_rows
    for line in content.splitlines():
        if not line.strip().startswith("|") or re.search(r"\|[-\s|]+\|", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        mid = cells[0].strip("*# ")
        if not re.match(r"M?\d+", mid):
            continue
        row_type, relation = cells[2], cells[4] if len(cells) > 4 else ""
        if "文献" in row_type and not re.search(r"一致|相反|不符|不适用|N/?A", relation):
            lit_rows.append({"id": mid, "relation": relation})
        if "推测" in row_type:
            spec_rows.append({"id": mid})
    return lit_rows, spec_rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True)
    ap.add_argument("--matrix", required=True)
    ap.add_argument("--refs", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    text = open(args.text, encoding="utf-8").read()
    try:
        refs = json.load(open(args.refs, encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"FATAL: 无法读取 reference_keys.json: {e}", file=sys.stderr)
        return 2

    ref_keys = {(r.get("key", "").lower(), str(r.get("year", ""))) for r in refs}
    ref_nums = {str(i + 1) for i in range(len(refs))}
    report = {"checks": []}
    fails = 0

    def add(rule, ok, detail):
        nonlocal fails
        report["checks"].append({"rule": rule, "pass": bool(ok), "detail": detail})
        if not ok:
            fails += 1

    # V1 引用匹配
    bad_cites = []
    for c in extract_citations(text):
        if c["ref"].isdigit() and len(c["ref"]) <= 3 and (c["key"], c["ref"]) not in ref_keys:
            # [n] 编号制
            if c["ref"] not in ref_nums:
                bad_cites.append(c)
        elif (c["key"].lower(), c["ref"]) not in ref_keys:
            bad_cites.append(c)
    add("V1_CITATIONS_RESOLVE", not bad_cites, bad_cites[:10])

    # V2 讨论段论断句锚点
    _, disc = split_sections(text)
    no_anchor = []
    if disc:
        for i, s in enumerate(sentences(disc)):
            if CLAIM_VERBS.search(s) and not ANCHOR.search(s):
                no_anchor.append({"sentence_index": i, "text": s[:140]})
    add("V2_CLAIMS_HAVE_ANCHORS", not no_anchor, no_anchor[:10])

    # V3/V4 矩阵检查
    lit_rows, spec_rows = parse_matrix(args.matrix)
    add("V3_LITERATURE_ROWS_HAVE_RELATION", not lit_rows, lit_rows[:10])
    missing_spec = []
    for r in spec_rows:
        if not SPEC_MARK.search(text):
            missing_spec.append(r)
            break
    add("V4_SPECULATION_MARKED", not missing_spec, missing_spec)

    report["summary"] = {"total": len(report["checks"]), "failed": fails,
                         "citations_checked": len(extract_citations(text)),
                         "verdict": "PASS" if fails == 0 else "FAIL"}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
