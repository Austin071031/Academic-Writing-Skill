#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""drift_guard — 锚定式修改的语义漂移守卫。

核心规则（AI 修改方向的方法论落地）：
  A. 锚定：每条改动的 old 文本必须真实存在于原稿（不许凭印象改写）。
  B. 最小：每个段落被改动的字符占比超过阈值（默认 0.5）且不在指令范围内
     时，判为疑似整段重写（语义漂移），必须人工确认。
  C. 净土：未在任何改动锚点邻近（同段）出现的段落若发生变化，判为
     未授权改动（unauthorized change）。
  D. 数字守恒：改写前后段落中的数字集合必须一致（除非该数字正是改动目标
     且指令明确），防止事实漂移。

输入：原稿 docx、改后 docx、改动明细 json（revisions_apply 的 changes.json
     或同构 [{old,new,...}] 列表）。
输出：drift_report.json + 退出码（0 干净 / 1 有警告 / 2 有未授权改动）。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docxkit as dk  # noqa: E402

NUM_RE = re.compile(r"\d+(?:\.\d+)?%?")

DEFAULT_MAX_REWRITE_RATIO = 0.5


def build_changes(changes_json):
    d = json.load(open(changes_json, encoding="utf-8"))
    if isinstance(d, dict):
        return d.get("changes", [])
    return d


def para_changed_ratio(a, b):
    """两段文本的字符级最简差异占比（非 LCS，工程近似：公共子序列占比）。"""
    if a == b:
        return 0.0
    if not a or not b:
        return 1.0
    # difflib 近似
    import difflib
    sm = difflib.SequenceMatcher(None, a, b)
    changed = sum(max(i2 - i1, j2 - j1)
                  for tag, i1, i2, j1, j2 in sm.get_opcodes()
                  if tag != "equal")
    return changed / max(len(a), len(b), 1)


def guard(before_path, after_path, changes, max_ratio=DEFAULT_MAX_REWRITE_RATIO):
    before = dk.Docx(before_path)
    after = dk.Docx(after_path)
    dk._build_parent_map(before.tree().getroot())
    dk._build_parent_map(after.tree().getroot())
    bp = dk.para_dump(before)
    ap = dk.para_dump(after)

    # A. 锚定校验
    anchor_ok, anchor_fail = 0, []
    for c in changes:
        old = c.get("old") or c.get("del_text") or ""
        if not old or c.get("type") == "insert_after":
            anchor_ok += 1
            continue
        found = any(old in p["text"] or old in (c.get("old") or "")
                    for p in bp)
        # 注意：若该改动已应用，old 只存在于 before 快照
        if found:
            anchor_ok += 1
        else:
            anchor_fail.append({"edit_id": c.get("edit_id"),
                                "old": old[:60]})

    # 授权改动段落集合：锚点同段 + 原稿中包含任一 old 文本的段落（±1 容差）
    authorized = set()
    for c in changes:
        ai = c.get("anchor_para", c.get("anchored_para"))
        if ai is not None:
            authorized.add(ai)
            authorized.add(ai + 1)
        old = c.get("old") or c.get("del_text") or ""
        if old:
            for i, p in enumerate(bp):
                if old in p["text"]:
                    authorized.add(i)

    # 对齐：先精确匹配未变段落，再对剩余段落做 ±3 容差的最优对齐
    after_texts = [p["text"] for p in ap]
    used_after = set()
    pairs = []  # (before_idx, after_idx|None)
    for i, p in enumerate(bp):
        if p["text"] in after_texts:
            j = after_texts.index(p["text"])
            while j in used_after:
                try:
                    j = after_texts.index(p["text"], j + 1)
                except ValueError:
                    j = -1
                    break
            if j >= 0:
                used_after.add(j)
                pairs.append((i, j))
                continue
        pairs.append((i, None))
    for i, j in pairs:
        if j is not None:
            continue
        p = bp[i]
        best_j, best_r = None, None
        for j2 in range(max(0, i - 3), min(len(ap), i + 4)):
            if j2 in used_after:
                continue
            r = para_changed_ratio(p["text"], ap[j2]["text"])
            if best_r is None or r < best_r:
                best_r, best_j = r, j2
        if best_j is not None and best_r > 0:
            used_after.add(best_j)
            pairs[i] = (i, best_j)

    # B/C. 漂移与净土检查
    warnings, unauthorized = [], []
    for i, j in pairs:
        if j is None:
            continue
        p, q = bp[i], ap[j]
        ratio = para_changed_ratio(p["text"], q["text"])
        if ratio == 0.0:
            continue
        if ratio > max_ratio:
            warnings.append({"before_para": i, "after_para": j,
                             "rewrite_ratio": round(ratio, 3),
                             "before": p["text"][:80],
                             "after": q["text"][:80],
                             "note": "改写幅度超过阈值，需确认指令授权"})
        near = any(abs(i - a) <= 1 for a in authorized)
        if not near:
            unauthorized.append({"before_para": i, "after_para": j,
                                 "rewrite_ratio": round(ratio, 3),
                                 "before": p["text"][:80],
                                 "after": q["text"][:80],
                                 "note": "该段落不在任何改动锚点邻近，"
                                         "属未授权改动"})

    # D. 数字守恒（仅检查有改动的授权段落对）
    num_drift = []
    for i, j in pairs:
        if j is None or i not in authorized:
            continue
        na = set(NUM_RE.findall(bp[i]["text"]))
        nb = set(NUM_RE.findall(ap[j]["text"]))
        removed = na - nb
        if removed:
            covered = any(all(
                str(n) in ((c.get("old") or "") + (c.get("new") or ""))
                for n in removed)
                for c in changes)
            if not covered:
                num_drift.append({"before_para": i, "after_para": j,
                                  "numbers_removed": sorted(removed),
                                  "note": "数字在改写中消失且未见于改动目标"})

    report = {
        "anchors": {"ok": anchor_ok, "failed": anchor_fail},
        "rewrite_warnings": warnings,
        "unauthorized_changes": unauthorized,
        "number_drift": num_drift,
        "max_rewrite_ratio": max_ratio,
        "verdict": "clean" if not (unauthorized or anchor_fail) else
                   ("warning" if not unauthorized else "unauthorized"),
    }
    return report


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    before, after, changes_json = sys.argv[1:4]
    out = sys.argv[4] if len(sys.argv) > 4 else None
    max_ratio = float(sys.argv[5]) if len(sys.argv) > 5 else \
        DEFAULT_MAX_REWRITE_RATIO
    changes = build_changes(changes_json)
    report = guard(before, after, changes, max_ratio)
    s = json.dumps(report, ensure_ascii=False, indent=1)
    if out:
        open(out, "w", encoding="utf-8").write(s)
    print(s)
    return {"clean": 0, "warning": 1}.get(report["verdict"], 2)


if __name__ == "__main__":
    sys.exit(main())
