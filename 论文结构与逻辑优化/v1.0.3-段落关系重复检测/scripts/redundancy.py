#!/usr/bin/env python3
"""redundancy.py — V4 主攻引擎：段落关系与重复内容深度分析。

产出:
  work/redundancy_report.json  重复对表 + 衔接问题表 + 拆分候选表 + 统计
  work/findings_engine.json    深度 findings（dimension ∈ {redundancy, paragraph_relation}，
                               与 six_scan 同 schema，report_builder 合并去重）

方法（可复核，阈值见 scanutil.THRESH）:
  a) 段落重复对: 全部段落两两（n_char>=40）字符 3-gram Jaccard。
       >=0.55 → 重复: 同章相邻 → merge；跨章 → 删除冗余侧 + 交叉引用
       （保留启发式: 角色更核心者优先，平级取先出现者）。
       摘要↔引言、结论↔摘要的高重叠单独标注"结构性呼应 vs 冗余"，confidence<=0.6 人工裁决。
       0.30–0.55 → 近似重复: narrow（差异化改写或合并）。
  b) 句子级跨章节近重复: 句子 3-gram Jaccard>=0.80 且分属不同章节 → merge/删。
  c) 衔接缺失（比 six_scan 更深）:
       同章相邻段 terms Jaccard<0.05 且后段无 CONNECTIVES 开头 → add_transition；
       回指悬空: 段首"如前所述/上文/据此/this shows..."但前 3 段无内容词重叠 → finding。
  d) 该拆分未拆分: 段 n_char>=400 且内部句子两两平均 terms-Jaccard<0.03 → split 候选，
       建议拆分点 = 前后半内部相似度最低的句界。
  e) 统计: 重复对总数、涉及段落数、冗余字符估算（重复对中较短段字符数之和）。

findings 上限 MAX_FINDINGS=15（按 重复 > 句子重复 > 回指悬空 > 衔接缺失 > 拆分 截断）。
"""
import argparse, json, os, re, sys, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scanutil import (shingles, terms, jaccard, classify_role, short, make_finding,
                      load_structure, save_findings, append_change_log,
                      CONNECTIVES, THRESH)

MAX_FINDINGS = 15
MIN_PARA_CHAR = 40        # 参与段落重复对的字数下限
SPLIT_MIN_CHAR = 400      # 拆分候选的字数下限
SPLIT_MAX_SENT = 30       # 内部句子数上限（防爆）
DUP = THRESH["para_dup_jaccard"]    # 0.55
NEAR = THRESH["para_near_jaccard"]  # 0.30
SENT_DUP = THRESH["sent_dup_jaccard"]  # 0.80
GAP = THRESH["gap_lex_jaccard"]     # 0.05

# 角色核心度: 论证主体章节的重复更可能承载信息，呼应类章节重叠多为结构性
ROLE_CORE = {"method": 3, "experiment": 3, "results": 3, "discussion": 3,
             "introduction": 2, "conclusion": 2,
             "abstract": 1, "related_work": 1,
             "keywords": 0, "acknowledgment": 0, "references": 0,
             "appendix": 1, "other": 2}

ECHO_ROLE_PAIRS = {frozenset(("abstract", "introduction")),
                   frozenset(("abstract", "conclusion"))}

ANAPHOR_CUES = re.compile(
    r"^(如前所述|如上所述|如前|上文|如上|据此|由此(可见)?|基于上述|如前节|上节|"
    r"this shows|these results|as shown above|as mentioned above|as noted above|"
    r"as discussed above|the above (results|analysis|discussion)|our results show)", re.I)


def para_role(p):
    return classify_role(p["section"])


def para_pos(model, pid):
    for i, p in enumerate(model["paragraphs"]):
        if p["id"] == pid:
            return i
    return -1


def pick_keeper(a, b, model):
    """保留启发式: 角色核心度高者保留；平级取先出现者。"""
    ra, rb = ROLE_CORE.get(para_role(a), 2), ROLE_CORE.get(para_role(b), 2)
    if ra != rb:
        return a if ra > rb else b
    return a if para_pos(model, a["id"]) < para_pos(model, b["id"]) else b


def disposition(a, b, model, same_section, adjacent, keeper):
    """重复对的建议处置。"""
    if same_section and adjacent:
        return "merge", (f"{a['id']} 与 {b['id']} 同章相邻且近重复，合并为一段："
                         f"保留 {keeper['id']} 的论证主线，另一段仅保留其增量信息（如有）。")
    if same_section:
        return "merge", (f"{a['id']} 与 {b['id']} 同章重复，合并：保留 {keeper['id']}，"
                         f"删除另一段或将其差异句并入保留段。")
    loser = b if keeper is a else a
    return "merge", (f"跨章重复：保留 {keeper['id']}（{keeper['section']}），"
                     f"删除 {loser['id']}（{loser['section']}）的重复表述，"
                     f"改为一句交叉引用（'详见{keeper['section']}'）。")


PAIR_CAP = 1000  # 两两比较防爆上限：超出时保留文档序前 1000 个达标段落


def analyze_para_pairs(model):
    """段落两两重复/近似重复/结构性呼应。"""
    dup_rows, near_rows, echo_rows = [], [], []
    ps = [p for p in model["paragraphs"] if p["n_char"] >= MIN_PARA_CHAR]
    capped = len(ps) > PAIR_CAP
    if capped:
        ps = ps[:PAIR_CAP]
    sig = {p["id"]: shingles(p["text"]) for p in ps}
    for a, b in itertools.combinations(ps, 2):
        sim = jaccard(sig[a["id"]], sig[b["id"]])
        if sim < NEAR:
            continue
        ra, rb = para_role(a), para_role(b)
        same_section = a["section_id"] == b["section_id"]
        adjacent = same_section and abs(para_pos(model, b["id"]) - para_pos(model, a["id"])) == 1
        row = {
            "a": {"para_id": a["id"], "section": a["section"], "role": ra,
                  "quote": short(a["text"], 90)},
            "b": {"para_id": b["id"], "section": b["section"], "role": rb,
                  "quote": short(b["text"], 90)},
            "similarity": round(sim, 3),
            "same_section": same_section, "adjacent": adjacent,
        }
        if sim >= DUP:
            if frozenset((ra, rb)) in ECHO_ROLE_PAIRS:
                # 摘要↔引言 / 结论↔摘要：结构性呼应 vs 冗余，人工裁决
                row["category"] = "structural_echo"
                row["disposition"] = "human_adjudication"
                row["rationale"] = ("摘要与首尾章节的重叠部分是文体要求（点题/回收），"
                                    "部分是冗余复述；两者词面高度相似无法自动区分，"
                                    "confidence<=0.6，交由人工裁决：保留点题骨架、删除展开性复述。")
                echo_rows.append(row)
            else:
                keeper = pick_keeper(a, b, model)
                op, instr = disposition(a, b, model, same_section, adjacent, keeper)
                row["category"] = "duplicate"
                row["disposition"] = op
                row["keeper"] = keeper["id"]
                row["rationale"] = instr
                dup_rows.append(row)
        else:
            row["category"] = "near_duplicate"
            row["disposition"] = "narrow"
            row["rationale"] = (f"相似度 {sim:.2f} 处于近似重复区间（{NEAR}–{DUP}）："
                                f"两段论述同一内容但措辞不同，建议差异化改写（各段保留不同侧面），"
                                f"或合并为一段消除分叉表述。")
            near_rows.append(row)
    dup_rows.sort(key=lambda r: -r["similarity"])
    near_rows.sort(key=lambda r: -r["similarity"])
    if capped:
        note = (f"段落对比较超上限（>{PAIR_CAP}），仅比较文档序前 {PAIR_CAP} 个"
                f"达标段落，超出的段落未参与重复检测。")
        for rows in (dup_rows, near_rows):
            for r in rows:
                r["rationale"] = note + r["rationale"]
    return dup_rows, near_rows, echo_rows


def analyze_sentence_dups(model):
    """句子级跨章节近重复（3-gram Jaccard >= SENT_DUP 且分属不同章节）。"""
    rows = []
    sents = [s for s in model["sentences"] if len(s["text"]) >= 12]
    sig = {s["id"]: shingles(s["text"]) for s in sents}
    for a, b in itertools.combinations(sents, 2):
        if a["section_id"] == b["section_id"]:
            continue
        sim = jaccard(sig[a["id"]], sig[b["id"]])
        if sim >= SENT_DUP:
            rows.append({
                "a": {"sentence_id": a["id"], "section": a["section"],
                      "para_id": a["para_id"], "quote": short(a["text"], 90)},
                "b": {"sentence_id": b["id"], "section": b["section"],
                      "para_id": b["para_id"], "quote": short(b["text"], 90)},
                "similarity": round(sim, 3),
                "disposition": "merge",
                "rationale": ("跨章近重复句：保留论证位置更合理的一处"
                              "（一般为方法/结果章），另一处删除或改为交叉引用。"),
            })
    rows.sort(key=lambda r: -r["similarity"])
    return rows


def analyze_cohesion(model):
    """衔接缺失 + 回指悬空（比 six_scan 深的段落关系分析）。"""
    by_sec, order = {}, []
    for p in model["paragraphs"]:
        by_sec.setdefault(p["section_id"], []).append(p)
        order.append(p)
    pos = {p["id"]: i for i, p in enumerate(order)}

    gaps = []
    for sec_id, ps in by_sec.items():
        for a, b in zip(ps, ps[1:]):
            if para_role(a) in ("references", "acknowledgment"):
                continue
            sim = jaccard(terms(a["text"]), terms(b["text"]))
            head = b["text"].strip()[:30]
            if sim < GAP and not CONNECTIVES.search(head):
                gaps.append({
                    "from_para": a["id"], "to_para": b["id"], "section": b["section"],
                    "lex_jaccard": round(sim, 3),
                    "to_para_quote": short(b["text"], 90),
                    "disposition": "add_transition",
                    "rationale": (f"同章相邻段 {a['id']}→{b['id']} 内容词重叠 {sim:.2f}"
                                  f"（阈值 {GAP}）且后段无衔接词开头，话题跳变缺过渡。"),
                })

    dangles = []
    for i, p in enumerate(order):
        m = ANAPHOR_CUES.search(p["text"].strip())
        if not m:
            continue
        prev_terms = set()
        for q in order[max(0, i - 3):i]:
            prev_terms |= terms(q["text"])
        overlap = terms(p["text"]) & prev_terms
        if not overlap:
            dangles.append({
                "para_id": p["id"], "section": p["section"],
                "cue": m.group(0), "para_quote": short(p["text"], 90),
                "disposition": "add_transition",
                "rationale": (f"段首以「{m.group(0)}」回指，但前 3 段（"
                              f"{', '.join(q['id'] for q in order[max(0, i-3):i]) or '无'}）"
                              f"与其无内容词重叠，回指悬空：读者找不到所指。"),
            })
    return gaps, dangles


def analyze_splits(model):
    """该拆分未拆分: 长段 + 多话题混杂（内部句子两两平均相似度极低）。"""
    rows = []
    by_para = {}
    for s in model["sentences"]:
        by_para.setdefault(s["para_id"], []).append(s)
    for p in model["paragraphs"]:
        if p["n_char"] < SPLIT_MIN_CHAR:
            continue
        sents = by_para.get(p["id"], [])
        if not (2 <= len(sents) <= SPLIT_MAX_SENT):
            continue
        tsets = [terms(s["text"]) for s in sents]
        pairs = [(jaccard(tsets[i], tsets[j]), i, j)
                 for i in range(len(sents)) for j in range(i + 1, len(sents))]
        avg = sum(x[0] for x in pairs) / len(pairs)
        if avg >= 0.03:
            continue
        # 建议拆分点: 前半/后半内部相似度最低的句界
        best_k, best_sim = 1, 2.0
        for k in range(1, len(sents)):
            left = terms(" ".join(s["text"] for s in sents[:k]))
            right = terms(" ".join(s["text"] for s in sents[k:]))
            sim = jaccard(left, right)
            if sim < best_sim:
                best_k, best_sim = k, sim
        rows.append({
            "para_id": p["id"], "section": p["section"], "n_char": p["n_char"],
            "n_sent": len(sents), "avg_internal_jaccard": round(avg, 3),
            "suggested_split_after": sents[best_k - 1]["id"],
            "split_point_quote": short(sents[best_k - 1]["text"], 60),
            "disposition": "split",
            "rationale": (f"段落 {p['n_char']} 字符，内部 {len(sents)} 句两两平均相似度 "
                          f"{avg:.3f}（<0.03），多话题混杂：建议在 "
                          f"{sents[best_k-1]['id']} 之后拆为两段，各段一个话题并补过渡句。"),
        })
    rows.sort(key=lambda r: r["avg_internal_jaccard"])
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    model = load_structure(args.work)

    dup_rows, near_rows, echo_rows = analyze_para_pairs(model)
    sent_rows = analyze_sentence_dups(model)
    gap_rows, dangle_rows = analyze_cohesion(model)
    split_rows = analyze_splits(model)

    # ---- findings（上限 15，按信息价值排序截断）----
    findings, n = [], 0

    def add(f):
        nonlocal n
        if len(findings) >= MAX_FINDINGS:
            return
        findings.append(f)

    for r in dup_rows:
        n += 1
        add(make_finding(
            f"E-{n:02d}", "redundancy", "段落重复" + ("（同章相邻）" if r["adjacent"] else "（跨章）"),
            f"{r['a']['section']} ⇄ {r['b']['section']}", f"{r['a']['para_id']}⇄{r['b']['para_id']}", None,
            r["a"]["quote"],
            f"两段字符 3-gram Jaccard={r['similarity']:.2f}（重复阈值 {DUP}）。{r['rationale']}",
            "merge", r["rationale"],
            "high" if r["similarity"] >= 0.75 else "medium",
            min(0.6 + (r["similarity"] - DUP), 0.9)))
    for r in echo_rows:
        n += 1
        add(make_finding(
            f"E-{n:02d}", "redundancy", "结构性呼应 vs 冗余（人工裁决）",
            f"{r['a']['section']} ⇄ {r['b']['section']}", f"{r['a']['para_id']}⇄{r['b']['para_id']}", None,
            r["a"]["quote"],
            f"摘要与首尾章节重叠 Jaccard={r['similarity']:.2f}：点题性呼应是文体要求，"
            f"展开性复述是冗余，二者词面不可分，需人工裁决。",
            "narrow", "保留点题骨架句（研究对象+主要结论各一句），删除展开性复述句；"
                      "若摘要/结论本身已极简则驳回本条。",
            "low", 0.5))
    for r in sent_rows:
        n += 1
        add(make_finding(
            f"E-{n:02d}", "redundancy", "跨章节句子级近重复",
            f"{r['a']['section']} ⇄ {r['b']['section']}",
            f"{r['a']['para_id']}⇄{r['b']['para_id']}",
            f"{r['a']['sentence_id']}⇄{r['b']['sentence_id']}", r["a"]["quote"],
            f"两句字符 3-gram Jaccard={r['similarity']:.2f}（阈值 {SENT_DUP}），分属不同章节。",
            "merge", r["rationale"], "medium", 0.7))
    for r in near_rows:
        n += 1
        add(make_finding(
            f"E-{n:02d}", "redundancy", "段落近似重复",
            f"{r['a']['section']} ⇄ {r['b']['section']}", f"{r['a']['para_id']}⇄{r['b']['para_id']}", None,
            r["a"]["quote"],
            f"两段 Jaccard={r['similarity']:.2f}，处近似重复区间（{NEAR}–{DUP}）：{r['rationale']}",
            "narrow", r["rationale"], "medium", 0.55))
    for r in dangle_rows:
        n += 1
        add(make_finding(
            f"E-{n:02d}", "paragraph_relation", "回指悬空",
            r["section"], r["para_id"], None, r["para_quote"], r["rationale"],
            "add_transition", "在段首补出所指内容（重述关键结论/显式引用小节号），"
                              "或删除该回指短语改为直接陈述。", "medium", 0.65))
    for r in gap_rows:
        n += 1
        add(make_finding(
            f"E-{n:02d}", "paragraph_relation", "段落间缺过渡且话题跳变",
            r["section"], r["to_para"], None, r["to_para_quote"], r["rationale"],
            "add_transition",
            f"在 {r['to_para']} 段首补一句过渡（承接 {r['from_para']} 的结论/引出新话题的理由），"
            f"或调整两段顺序。", "medium", 0.55))
    for r in split_rows:
        n += 1
        add(make_finding(
            f"E-{n:02d}", "paragraph_relation", "多话题段落（该拆分未拆分）",
            r["section"], r["para_id"], None, r["split_point_quote"], r["rationale"],
            "split", f"在 {r['suggested_split_after']} 之后拆分本段，拆后两段各设主题句并补衔接。",
            "medium", 0.6))

    # ---- 统计 ----
    involved = set()
    for r in dup_rows:
        involved.add(r["a"]["para_id"])
        involved.add(r["b"]["para_id"])
    redundant_chars = sum(min(next(p["n_char"] for p in model["paragraphs"]
                                   if p["id"] == r["a"]["para_id"]),
                              next(p["n_char"] for p in model["paragraphs"]
                                   if p["id"] == r["b"]["para_id"]))
                          for r in dup_rows) if dup_rows else 0
    stats = {
        "n_duplicate_pairs": len(dup_rows),
        "n_near_pairs": len(near_rows),
        "n_structural_echo": len(echo_rows),
        "n_sentence_dups": len(sent_rows),
        "n_cohesion_gaps": len(gap_rows),
        "n_dangling_refs": len(dangle_rows),
        "n_split_candidates": len(split_rows),
        "paragraphs_involved_in_duplicates": sorted(involved),
        "n_paragraphs_involved": len(involved),
        "estimated_redundant_chars": redundant_chars,
    }

    report = {
        "method_note": ("段落重复: 字符 3-gram Jaccard，重复阈值 "
                        f"{DUP}、近似重复 {NEAR}–{DUP}、句子级跨章 {SENT_DUP}；"
                        f"衔接缺失: 同章相邻段内容词 Jaccard<{GAP} 且后段无衔接词；"
                        "回指悬空: 段首回指词但前 3 段无内容词重叠；"
                        "拆分候选: 段落>=400 字符且内部句子两两平均相似度<0.03。"
                        "阈值集中于 scanutil.THRESH，全部可复核。"),
        "thresholds": {"para_duplicate": DUP, "para_near": NEAR,
                       "sentence_dup": SENT_DUP, "gap_lex": GAP,
                       "split_min_char": SPLIT_MIN_CHAR, "split_avg_sim": 0.03},
        "duplicate_pairs": dup_rows,
        "near_duplicate_pairs": near_rows,
        "structural_echo_pairs": echo_rows,
        "sentence_duplicates": sent_rows,
        "cohesion_gaps": gap_rows,
        "dangling_references": dangle_rows,
        "split_candidates": split_rows,
        "statistics": stats,
    }
    with open(os.path.join(args.work, "redundancy_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    save_findings(args.work, "findings_engine.json", findings)
    append_change_log(args.work, [{
        "step": "redundancy", "action": "段落关系与重复内容深度分析",
        "detail": (f"重复对={len(dup_rows)} 近似={len(near_rows)} 结构性呼应={len(echo_rows)} "
                   f"句子重复={len(sent_rows)} 衔接缺失={len(gap_rows)} 回指悬空={len(dangle_rows)} "
                   f"拆分候选={len(split_rows)}，深度 findings {len(findings)} 条"
                   f"（冗余字符估算 {redundant_chars}）"),
        "artifact": "work/redundancy_report.json + work/findings_engine.json"}])
    print(f"[redundancy] pairs={len(dup_rows)} near={len(near_rows)} "
          f"sentdup={len(sent_rows)} gaps={len(gap_rows)} splits={len(split_rows)} "
          f"findings={len(findings)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
