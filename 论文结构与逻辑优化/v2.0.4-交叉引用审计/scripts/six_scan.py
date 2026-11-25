#!/usr/bin/env python3
"""six_scan.py — 六维度轻量普查（共享基线），产出 work/findings_scan.json。

六维度（与评分细则"结果完整性"一致）:
  D1 研究问题  D2 章节结构  D3 论证链  D4 段落关系  D5 重复内容  D6 结论边界
本脚本给出每维度 Top-N 候选问题（带原文锚点）；深度诊断由各版本专属引擎完成。
所有 finding 遵循统一 schema（见 scanutil.make_finding）。
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scanutil import (RQ_CUES, CLAIM_CUES, EVIDENCE_CITES, EVIDENCE_FIGTAB, EVIDENCE_NUMBER,
                      CAUSAL_CUES, CORRELATION_CUES, ABSOLUTE_CUES, DESIGN_CUES,
                      LIMITATION_CUES, CONNECTIVES, NUM_IN_CONCL, CANONICAL_ORDER,
                      THRESH, terms, shingles, jaccard, classify_role, short,
                      make_finding, load_structure, save_findings, append_change_log,
                      role_of_section)

MAX_PER_DIM = 8

def scan_d1_rq(model):
    out = []
    rq_sents = [s for s in model["sentences"] if RQ_CUES.search(s["text"])]
    intro_roles = {"abstract", "introduction"}
    intro_secs = {s["id"] for s in model["sections"] if classify_role(s["heading"]) in intro_roles}
    intro_rq = [s for s in rq_sents if s["section_id"] in intro_secs]
    if not rq_sents:
        out.append(make_finding(
            "D1-01", "research_question", "研究问题未显式提出",
            next(iter(intro_secs), "SEC?"), None, None,
            "(全文未检出'研究问题/本文旨在/we aim/RQn'等提示语)",
            "六维普查：全文 RQ 提示词零命中；研究问题未被清楚提出时，后文方法与结论缺少对齐锚点。",
            "add", "在引言末尾以 1-2 句显式陈述研究问题（或编号列出 RQ1/RQ2），并在结论逐一回应。",
            "high", 0.75))
    else:
        concl_sents = [s for s in model["sentences"]
                       if role_of_section(model, s["section_id"]) == "conclusion"]
        concl_terms = terms(" ".join(s["text"] for s in concl_sents))
        orphan = []
        for s in (intro_rq or rq_sents)[:4]:
            cov = jaccard(terms(s["text"]), concl_terms)
            if cov < THRESH["rq_cover_overlap"] and concl_sents:
                orphan.append((s, cov))
        for i, (s, cov) in enumerate(orphan[:MAX_PER_DIM - 1], 2):
            out.append(make_finding(
                f"D1-{i:02d}", "research_question", "研究问题在结论中无呼应",
                s["section"], s["para_id"], s["id"], s["text"],
                f"该研究问题/目标句与结论章节的术语覆盖率仅 {cov:.2f}（阈值 {THRESH['rq_cover_overlap']}），"
                "结论未回应此问题，首尾闭环存疑。",
                "add", "在结论中补充对该研究问题的直接回应（回答了什么、证据在哪一节），或收窄引言中的问题表述。",
                "high", 0.65))
    return out

def scan_d2_structure(model):
    out, n = [], 0
    secs = [s for s in model["sections"] if s["level"] > 0]
    roles = [(s, classify_role(s["heading"])) for s in secs]
    present = {r for _, r in roles}
    body = [s for s, r in roles if r not in ("references", "appendix", "acknowledgment")]
    total = sum(s["n_char"] for s in body) or 1
    # 核心章节缺失
    core = {"introduction": "引言", "method": "方法", "conclusion": "结论"}
    for role, name in core.items():
        if role not in present and len(model["sections"]) > 1:
            n += 1
            out.append(make_finding(
                f"D2-{n:02d}", "section_structure", f"核心章节缺失：{name}",
                "(全文)", None, None, f"(未检出'{name}'类章节标题)",
                f"章节角色归类（标题关键词匹配）未发现{name}章节；若为文体所致请人工确认，否则论证链缺环。",
                "add", f"补充独立'{name}'章节，或在现有章节中以显式小标题标出{name}内容。",
                "high", 0.6))
    # 顺序异常
    order_seq = [CANONICAL_ORDER.index(r) for _, r in roles if r in CANONICAL_ORDER]
    for i in range(1, len(order_seq)):
        if order_seq[i] < order_seq[i - 1] and n < MAX_PER_DIM:
            bad = [s for s, r in roles if r in CANONICAL_ORDER and CANONICAL_ORDER.index(r) == order_seq[i]][0]
            n += 1
            out.append(make_finding(
                f"D2-{n:02d}", "section_structure", "章节顺序与论证顺序倒置",
                bad["heading"], None, None, bad["heading"],
                f"章节角色序列 {order_seq} 在第 {i + 1} 处出现回退（如结果先于方法、结论先于结果），"
                "信息释放顺序不服务论证。",
                "move", "按 摘要→引言→相关工作→方法→实验/结果→讨论→结论 的论证顺序调整该章节位置；"
                "若为期刊模板要求请在报告中说明。", "medium", 0.6))
            break
    # 篇幅失衡
    for s in body:
        share = s["n_char"] / total
        if share > THRESH["section_imbalance"] and len(body) >= 4 and n < MAX_PER_DIM:
            n += 1
            out.append(make_finding(
                f"D2-{n:02d}", "section_structure", "篇幅分配失衡",
                s["heading"], None, None, s["heading"],
                f"该章节占正文 {share:.0%}（阈值 {THRESH['section_imbalance']:.0%}），"
                "挤压了其他论证环节；可能混入应拆分/后移的内容。",
                "split", "审读该章节：将细节性内容移入附录，将不同主题段落拆分为独立小节。",
                "medium", 0.65))
    # 标题层级跳变
    prev = None
    for s in secs:
        if prev is not None and s["level"] - prev > 1 and n < MAX_PER_DIM:
            n += 1
            out.append(make_finding(
                f"D2-{n:02d}", "section_structure", "标题层级跳变",
                s["heading"], None, None, s["heading"],
                f"标题层级由 H{prev} 直接跳到 H{s['level']}，中间层级缺失，目录层级关系断裂。",
                "reorder", "补齐中间层级标题，或将该标题调整为 H{}。".format(prev + 1),
                "low", 0.7))
        prev = s["level"]
    return out

def scan_d3_chain(model):
    out, n = [], 0
    unsupported = []
    for p in model["paragraphs"]:
        ptext = p["text"]
        has_anchor = bool(EVIDENCE_CITES.search(ptext) or EVIDENCE_FIGTAB.search(ptext)
                          or EVIDENCE_NUMBER.search(ptext))
        if has_anchor:
            continue
        for s in model["sentences"]:
            if s["para_id"] == p["id"] and CLAIM_CUES.search(s["text"]):
                unsupported.append(s)
    for s in unsupported[:MAX_PER_DIM]:
        n += 1
        out.append(make_finding(
            f"D3-{n:02d}", "argument_chain", "论断无同段论据锚点",
            s["section"], s["para_id"], s["id"], s["text"],
            "该句含论断提示词（表明/证明/显著优于/shows 等），但所在段落无引用、无图表锚点、"
            "无带单位数据；论据支撑位置不明。",
            "narrow", "二选一：(a) 在该句补充具体论据锚点（引用编号/图表号/数据）；(b) 将论断收窄为本段已有数据支持的范围。",
            "high", 0.6))
    return out

def scan_d4_paragraph(model):
    out, n = [], 0
    by_sec = {}
    for p in model["paragraphs"]:
        by_sec.setdefault(p["section_id"], []).append(p)
    for sec_id, ps in by_sec.items():
        for a, b in zip(ps, ps[1:]):
            if n >= MAX_PER_DIM:
                break
            sim = jaccard(terms(a["text"]), terms(b["text"]))
            if sim < THRESH["gap_lex_jaccard"] and not CONNECTIVES.search(b["text"].strip()):
                n += 1
                out.append(make_finding(
                    f"D4-{n:02d}", "paragraph_relation", "段落间缺过渡且话题跳变",
                    a["section"], b["id"], None,
                    short(b["text"], 60),
                    f"相邻段落 {a['id']}→{b['id']} 词面重叠 Jaccard={sim:.2f}"
                    f"（阈值 {THRESH['gap_lex_jaccard']}），且后段无衔接词开头，存在逻辑跳跃风险。",
                    "add_transition", "在 {} 段首补一句过渡（承接 {} 的结论/引出新话题的理由），或调整两段顺序。".format(b["id"], a["id"]),
                    "medium", 0.55))
    return out

def scan_d5_redundancy(model):
    out, n = [], 0
    ps = [p for p in model["paragraphs"] if p["n_char"] >= 40]
    sig = {p["id"]: shingles(p["text"]) for p in ps}
    for i in range(len(ps)):
        for j in range(i + 1, len(ps)):
            a, b = ps[i], ps[j]
            if a["section_id"] == b["section_id"]:
                continue
            sim = jaccard(sig[a["id"]], sig[b["id"]])
            if sim >= THRESH["para_dup_jaccard"] and n < MAX_PER_DIM:
                n += 1
                out.append(make_finding(
                    f"D5-{n:02d}", "redundancy", "跨章节段落重复",
                    f"{a['section']} ⇄ {b['section']}", f"{a['id']}⇄{b['id']}", None,
                    short(a["text"], 60),
                    f"两段字符 3-gram Jaccard={sim:.2f}（阈值 {THRESH['para_dup_jaccard']}），"
                    "分属不同章节，属跨章节重复表述。",
                    "merge", "保留论证位置上更合理的一段，另一段删除或改写为一句交叉引用（'详见X节'）。",
                    "medium", 0.75))
    return out

def scan_d6_boundary(model):
    out, n = [], 0
    concl_sents = [s for s in model["sentences"]
                   if role_of_section(model, s["section_id"]) in ("conclusion", "abstract")]
    body_text = " ".join(s["text"] for s in model["sentences"]
                         if role_of_section(model, s["section_id"])
                         in ("results", "experiment", "method", "discussion"))
    body_nums = set(m.group(0).strip() for m in NUM_IN_CONCL.finditer(body_text))
    has_limit = any(LIMITATION_CUES.search(s["text"]) for s in model["sentences"])
    for s in concl_sents:
        if n >= MAX_PER_DIM:
            break
        t = s["text"]
        if CAUSAL_CUES.search(t) and CORRELATION_CUES.search(body_text) and not DESIGN_CUES.search(body_text):
            n += 1
            out.append(make_finding(
                f"D6-{n:02d}", "conclusion_boundary", "相关性证据支撑因果表述",
                s["section"], s["para_id"], s["id"], t,
                "结论句含因果动词（导致/提高/improve 等），正文证据提示相关性（相关/关联/correlation）"
                "且未检出对照/消融/随机等设计词，因果强度超出证据。",
                "narrow", "将因果表述降级为关联表述（'与…相关''在…条件下观察到'），或补充支持因果的实验设计引用。",
                "high", 0.6))
        elif ABSOLUTE_CUES.search(t):
            n += 1
            out.append(make_finding(
                f"D6-{n:02d}", "conclusion_boundary", "绝对化表述",
                s["section"], s["para_id"], s["id"], t,
                "结论句含绝对化量词（所有/任何/完全/always/never），单研究证据一般不支持全域断言。",
                "qualify", "限定适用范围：补出适用条件（数据规模/体系/工况），或将绝对词改为限定词（'在本文条件下'）。",
                "medium", 0.65))
        else:
            stray = [m.group(0).strip() for m in NUM_IN_CONCL.finditer(t)
                     if m.group(0).strip() and m.group(0).strip() not in body_nums
                     and len(m.group(0).strip()) > 1]
            if stray:
                n += 1
                out.append(make_finding(
                    f"D6-{n:02d}", "conclusion_boundary", "结论数字在正文中无出处",
                    s["section"], s["para_id"], s["id"], t,
                    f"数字 {stray[:3]} 未在方法/结果/讨论章节出现（逐字匹配），结论引入了无源数据。",
                    "narrow", "为该数字补正文出处（指向具体表格/小节），或从结论中删除。",
                    "high", 0.7))
    if not has_limit and n < MAX_PER_DIM:
        n += 1
        out.append(make_finding(
            "D6-%02d" % n, "conclusion_boundary", "缺少局限性说明",
            "(全文)", None, None, "(未检出 局限/不足/未来工作/limitation 等提示语)",
            "全文未检出局限性提示词；结论边界声明缺失，读者无法判断结论的适用条件。",
            "add_limitation", "在结论前或讨论末尾补 1 段局限性说明（样本/方法假设/外推边界）。",
            "medium", 0.7))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    model = load_structure(args.work)

    findings = []
    for fn in (scan_d1_rq, scan_d2_structure, scan_d3_chain,
               scan_d4_paragraph, scan_d5_redundancy, scan_d6_boundary):
        try:
            findings.extend(fn(model))
        except Exception as e:
            print(f"[six_scan][warn] {fn.__name__} 失败: {e}", file=sys.stderr)

    save_findings(args.work, "findings_scan.json", findings)
    append_change_log(args.work, [{
        "step": "six_scan", "action": "六维度轻量普查",
        "detail": f"产出 {len(findings)} 条候选问题（每维度≤{MAX_PER_DIM}）",
        "artifact": "work/findings_scan.json"}])
    by_dim = {}
    for f in findings:
        by_dim[f["dimension"]] = by_dim.get(f["dimension"], 0) + 1
    print(f"[six_scan] findings={len(findings)} 分布={by_dim}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
