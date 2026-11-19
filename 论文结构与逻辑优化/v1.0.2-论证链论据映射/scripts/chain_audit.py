#!/usr/bin/env python3
"""chain_audit.py — V3 主攻引擎：论证链与论据对应深度分析。

产出:
  work/chain_audit.json      论断抽取结果 + 论据锚点 + 论断—论据映射表（支撑三档，可复核）
  work/findings_engine.json  深度 findings（dimension=argument_chain，与 six_scan 同 schema）

方法（可复核，规则详见 references/chain_rules.md）:
  a) 论断抽取: 提示词正则 CLAIM_CUES 逐句命中，按线索词分类（比较/因果/概括/绝对）。
  b) 论据锚点: 每句/每段记录锚点类型（引用 [n]/作者年、图表/公式/章节交叉引用、带单位数字）。
  c) 支撑分档: 同句或同段有锚点=strong；相邻段有锚点=weak；窗口内无锚点=none → 断裂(high)。
  d) 逻辑跳跃: 论断句内容词在前 3 段内从未出现（新词比例≥0.6 且无论据）→ add_transition。
  e) 循环论证近似: 两条论断句 3-gram Jaccard≥0.7 且两处都无锚点 → 疑似循环(medium, 需人工确认)。
  f) 强度不足: 因果/绝对论断所在段落只有相关性词或单点数据、无对照/消融/基线 → qualify(high)。
  g) 比较无对象: 比较论断句无 [n] 引用、无专名、无"基线/baseline" → medium。
findings 总数 ≤15。
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scanutil import (CLAIM_CUES, EVIDENCE_CITES, EVIDENCE_FIGTAB, EVIDENCE_NUMBER,
                      CAUSAL_CUES, CORRELATION_CUES, ABSOLUTE_CUES, DESIGN_CUES,
                      terms, jaccard, shingles, classify_role, short, make_finding,
                      load_structure, save_findings, append_change_log)

# ---- 本引擎专用线索词（阈值与正则集中于此，便于复核调参） ----
COMPARE_CUES = re.compile(
    r"(优于|超过|高于|好于|显著(优于|提高|提升|降低|改善)|"
    r"higher than|better than|outperform\w*|superior to|significantly (better|higher|lower|improve))", re.I)
COMPARE_OBJ_CUES = re.compile(   # 必须带比较对象的显性比较
    r"(优于|超过|高于|好于|higher than|better than|outperform\w*|superior to)", re.I)
GENERALIZE_CUES = re.compile(
    r"(表明|说明|可见|意味着|indicate\w*|suggest\w*|show\w* that|reveal\w*)", re.I)
BASELINE_CUES = re.compile(r"(基线|baseline)", re.I)
PROPER_NOUN = re.compile(r"[A-Z][A-Za-z0-9]{2,}")   # 拉丁字母专名近似（BERT/LiFePO4…）

TH = {"jump_new_ratio": 0.6,   # 新内容词比例下限（逻辑跳跃）
      "jump_min_new": 4,       # 新内容词最少个数
      "circ_jaccard": 0.7}     # 循环论证 3-gram 相似度下限

SKIP_ROLES = ("references", "acknowledgment")
MAX_FINDINGS = 15


def anchors_in(text):
    """返回该文本含有的锚点类型集合。"""
    a = set()
    if EVIDENCE_CITES.search(text):
        a.add("cite")
    if EVIDENCE_FIGTAB.search(text):
        a.add("figtab_xref")
    if EVIDENCE_NUMBER.search(text):
        a.add("number")
    return a


def claim_types(text):
    t = []
    if COMPARE_CUES.search(text):
        t.append("比较论断")
    if CAUSAL_CUES.search(text):
        t.append("因果论断")
    if GENERALIZE_CUES.search(text):
        t.append("概括论断")
    if ABSOLUTE_CUES.search(text):
        t.append("绝对论断")
    return t or ["一般论断"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    model = load_structure(args.work)

    paras = model["paragraphs"]
    pidx = {p["id"]: i for i, p in enumerate(paras)}
    para_anchors = {p["id"]: anchors_in(p["text"]) for p in paras}
    para_texts = [p["text"] for p in paras]
    para_terms = [terms(t) for t in para_texts]

    # ---- a) 论断抽取（跳过参考文献/致谢章节） ----
    claims = []
    for s in model["sentences"]:
        if classify_role(s["section"]) in SKIP_ROLES:
            continue
        if not CLAIM_CUES.search(s["text"]):
            continue
        i = pidx.get(s["para_id"], 0)
        s_anchor = anchors_in(s["text"])
        same = s_anchor | para_anchors.get(s["para_id"], set())
        adj = set()
        for j in (i - 1, i + 1):
            if 0 <= j < len(paras):
                adj |= para_anchors[paras[j]["id"]]
        tier = "strong" if same else ("weak" if adj else "none")
        claims.append({"sentence_id": s["id"], "para_id": s["para_id"],
                       "section": s["section"], "text": s["text"],
                       "types": claim_types(s["text"]),
                       "sentence_anchors": sorted(s_anchor),
                       "para_anchors": sorted(para_anchors.get(s["para_id"], set())),
                       "adjacent_anchors": sorted(adj),
                       "support": tier})

    n_strong = sum(1 for c in claims if c["support"] == "strong")
    n_weak = sum(1 for c in claims if c["support"] == "weak")
    n_none = sum(1 for c in claims if c["support"] == "none")

    findings, n = [], 0

    def add_finding(ftype, c, evidence, op, instruction, severity, confidence):
        nonlocal n
        n += 1
        findings.append(make_finding(
            f"E-{n:02d}", "argument_chain", ftype,
            c["section"], c["para_id"], c["sentence_id"], c["text"],
            evidence, op, instruction, severity, confidence))

    # ---- c) 论证链断裂（支撑档 none） ----
    for c in claims:
        if c["support"] == "none":
            add_finding("论证链断裂：论断窗口内无论据锚点", c,
                        f"该论断句（{'/'.join(c['types'])}）所在句、所在段及相邻段均无引用、"
                        "图表/交叉引用或带单位数字锚点，论断悬空。",
                        "narrow",
                        "删除或降级该论断（改述为假设/预期），或在其所在段补可核验证据"
                        "（数据、图表或引用）并显式指回（'见表X/图Y/[n]'）。",
                        "high", 0.7)
            if sum(1 for f in findings if f["type"].startswith("论证链断裂")) >= 8:
                break

    # ---- d) 逻辑跳跃：新术语突现且无论据 ----
    n_jump = 0
    for c in claims:
        if n_jump >= 4:
            break
        i = pidx.get(c["para_id"], 0)
        if i < 2:                      # 前文不足 2 段，不构成"突现"
            continue
        if c["sentence_anchors"] or c["para_anchors"]:
            continue
        prev = set()
        for j in range(max(0, i - 3), i):
            prev |= para_terms[j]
        ct = terms(c["text"])
        new = ct - prev
        if len(ct) >= 4 and len(new) >= TH["jump_min_new"] \
                and len(new) / len(ct) >= TH["jump_new_ratio"]:
            n_jump += 1
            add_finding("逻辑跳跃：论断引入前文未出现的新内容且无论据", c,
                        f"该论断 {len(new)}/{len(ct)} 个内容词在前 3 段内从未出现"
                        f"（如 {'、'.join(sorted(new)[:5])}），且句/段无论据锚点，"
                        "读者无法追溯其来源。",
                        "add_transition",
                        "在该论断前补过渡句交代新概念的定义与出处（引文或前文章节），"
                        "或将论断移至已建立该概念的段落之后。",
                        "medium", 0.6)

    # ---- e) 循环论证近似：论断句两两 3-gram 相似且均无锚点 ----
    bare = [c for c in claims
            if not c["sentence_anchors"] and not c["para_anchors"]]
    sh = {c["sentence_id"]: shingles(c["text"], 3) for c in bare}
    n_circ = 0
    for x in range(len(bare)):
        if n_circ >= 4:
            break
        for y in range(x + 1, len(bare)):
            a, b = bare[x], bare[y]
            if a["para_id"] == b["para_id"]:
                continue
            sim = jaccard(sh[a["sentence_id"]], sh[b["sentence_id"]])
            if sim >= TH["circ_jaccard"]:
                n_circ += 1
                add_finding("疑似循环论证：两处无锚点论断互为复述", b,
                            f"该论断与 {a['sentence_id']}（{a['section']}）3-gram 相似度 "
                            f"{sim:.2f}（阈值 {TH['circ_jaccard']}），两处均无论据锚点，"
                            "疑似以复述充当论证（近似判定，需人工确认）。",
                            "narrow",
                            "核实两处论断是否互为依据：若是，保留一处并为其补独立证据，"
                            "删除另一处复述；若各有所指，分别补锚点。",
                            "medium", 0.55)
                break

    # ---- f) 论据强度不足：因果/绝对论断只有相关性词或单点数据 ----
    n_str = 0
    for c in claims:
        if n_str >= 5:
            break
        strong_claim = ("因果论断" in c["types"]) or ("绝对论断" in c["types"])
        if not strong_claim:
            continue
        p = paras[pidx[c["para_id"]]]
        ptext = p["text"]
        if DESIGN_CUES.search(ptext):
            continue
        only_corr = bool(CORRELATION_CUES.search(ptext))
        nums = EVIDENCE_NUMBER.findall(ptext)
        single_point = bool(nums) and len(nums) == 1 \
            and not set(c["para_anchors"]) - {"number"}
        if only_corr or single_point:
            n_str += 1
            kind = "仅见相关性描述，无对照/消融/基线设计" if only_corr \
                else f"段落仅有单点数据（{len(nums)} 处带单位数字），无对照/消融/基线设计"
            add_finding("论据强度不足：因果/绝对论断缺实验设计支撑", c,
                        f"该{'/'.join(t for t in c['types'] if t in ('因果论断', '绝对论断'))}"
                        f"所在段落{kind}，相关性与单点数据不能支撑因果或绝对化结论。",
                        "qualify",
                        "将论断限定为相关性表述（'与…相关/提示'），或补对照组/消融/基线"
                        "实验后再恢复因果表述。",
                        "high", 0.65)

    # ---- g) 比较无对象：显性比较句找不到比较对象出处 ----
    n_cmp = 0
    for c in claims:
        if n_cmp >= 4:
            break
        if not COMPARE_OBJ_CUES.search(c["text"]):
            continue
        has_obj = (EVIDENCE_CITES.search(c["text"]) or
                   BASELINE_CUES.search(c["text"]) or
                   PROPER_NOUN.search(c["text"]))
        if has_obj:
            continue
        n_cmp += 1
        add_finding("比较论断缺少比较对象或对象无出处", c,
                    "该句含显性比较词（优于/超过/better than 等），但句中无 [n] 引用、"
                    "无拉丁字母专名、无'基线/baseline'，比较对象无法核验。",
                    "add",
                    "补出比较对象的名称与出处（引用编号或'相对于基线X'），"
                    "或删除比较表述改为绝对值陈述。",
                    "medium", 0.6)

    findings = findings[:MAX_FINDINGS]

    chain_audit = {
        "method_note": "论断由 CLAIM_CUES 正则逐句抽取并分类；锚点=引用/图表与交叉引用/带单位数字；"
                       "支撑档: 同句同段=strong, 相邻段=weak, 否则 none；跳跃阈值 new_ratio≥0.6；"
                       "循环阈值 3-gram Jaccard≥0.7（近似，需人工确认）。全部中间值在本文件可复核。",
        "summary": {"n_claims": len(claims), "strong": n_strong, "weak": n_weak,
                    "none": n_none, "n_findings": len(findings),
                    "by_type": {t: sum(1 for c in claims if t in c["types"])
                                for t in ("比较论断", "因果论断", "概括论断", "绝对论断", "一般论断")}},
        "claims": [{"sentence_id": c["sentence_id"], "para_id": c["para_id"],
                    "section": c["section"], "text": short(c["text"], 120),
                    "types": c["types"], "support": c["support"],
                    "sentence_anchors": c["sentence_anchors"],
                    "para_anchors": c["para_anchors"],
                    "adjacent_anchors": c["adjacent_anchors"]} for c in claims],
    }
    with open(os.path.join(args.work, "chain_audit.json"), "w", encoding="utf-8") as f:
        json.dump(chain_audit, f, ensure_ascii=False, indent=1)
    save_findings(args.work, "findings_engine.json", findings)
    append_change_log(args.work, [{
        "step": "chain_audit", "action": "论证链与论据对应深度分析",
        "detail": f"论断={len(claims)} strong={n_strong} weak={n_weak} none={n_none}，"
                  f"深度问题 {len(findings)} 条",
        "artifact": "work/chain_audit.json + work/findings_engine.json"}])
    print(f"[chain_audit] claims={len(claims)} strong={n_strong} weak={n_weak} "
          f"none={n_none} findings={len(findings)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
