#!/usr/bin/env python3
"""rq_engine.py — V1 主攻引擎：研究问题（RQ）与贡献主张对齐深度分析。

产出:
  work/rq_map.json          RQ×章节覆盖矩阵 + 贡献主张×证据映射 + 首尾呼应矩阵
  work/findings_engine.json 深度 findings（与 six_scan 同 schema，report_builder 合并去重）

方法（可复核）:
  1) RQ 抽取: 提示词正则 + 编号 RQ 归组（RQ1/问题一…）。
  2) 覆盖判定: RQ 内容词集合与各角色章节（方法/实验/结果/讨论/结论）的 Jaccard 覆盖率，
     阈值见 scanutil.THRESH；低于下限 → 断裂候选。
  3) 贡献核验: 贡献句术语与结果/实验段落的重叠 + 该段是否含数据/图表锚点 →
     "主张有证据 / 证据弱 / 无证据" 三档。
  4) 首尾呼应: 摘要+引言的论断句 与 结论句 两两相似度，无呼应论断列出。
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scanutil import (RQ_CUES, CONTRIBUTION_CUES, CLAIM_CUES, EVIDENCE_CITES,
                      EVIDENCE_FIGTAB, EVIDENCE_NUMBER, RQ_NUMBERED, THRESH,
                      terms, jaccard, classify_role, short, make_finding,
                      load_structure, save_findings, append_change_log)

COVER = THRESH["rq_cover_overlap"]

def role_terms(model):
    by_role = {}
    for s in model["sentences"]:
        r = classify_role(next((x["heading"] for x in model["sections"]
                                if x["id"] == s["section_id"]), ""))
        by_role.setdefault(r, []).append(s["text"])
    return {r: terms(" ".join(ts)) for r, ts in by_role.items()}

def extract_rq(model):
    rqs = []
    for s in model["sentences"]:
        if RQ_CUES.search(s["text"]):
            tag = None
            m = RQ_NUMBERED.search(s["text"])
            if m:
                tag = m.group(1).rstrip(":：")
            rqs.append({"tag": tag, "sentence_id": s["id"], "para_id": s["para_id"],
                        "section": s["section"], "text": s["text"],
                        "terms": sorted(terms(s["text"]))[:200]})
    return rqs

def extract_contributions(model):
    out = []
    for s in model["sentences"]:
        if CONTRIBUTION_CUES.search(s["text"]):
            out.append({"sentence_id": s["id"], "para_id": s["para_id"],
                        "section": s["section"], "text": s["text"]})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    model = load_structure(args.work)
    rt = role_terms(model)
    findings, n = [], 0

    rqs = extract_rq(model)
    contribs = extract_contributions(model)

    # ---- RQ × 角色章节覆盖矩阵 ----
    rq_rows = []
    for rq in rqs:
        tset = set(rq["terms"])
        cover = {r: round(jaccard(tset, tt), 3) for r, tt in rt.items()
                 if r in ("method", "experiment", "results", "discussion", "conclusion")}
        best = max(cover, key=cover.get) if cover else None
        row = {"rq": short(rq["text"], 100), "tag": rq["tag"],
               "location": {"section": rq["section"], "para_id": rq["para_id"],
                            "sentence_id": rq["sentence_id"]},
               "coverage_by_role": cover, "best_matched_role": best}
        rq_rows.append(row)
        if cover.get("method", 0) < COVER and cover.get("experiment", 0) < COVER:
            n += 1
            findings.append(make_finding(
                f"E-{n:02d}", "research_question", "研究问题无方法/实验承接",
                rq["section"], rq["para_id"], rq["sentence_id"], rq["text"],
                f"该 RQ 内容词在方法章覆盖率 {cover.get('method', 0):.2f}、实验章 "
                f"{cover.get('experiment', 0):.2f}（阈值 {COVER}），问题与方法各说各话。",
                "add", "在方法章显式说明哪一部分设计回答此 RQ（可用相同术语回扣），或收窄 RQ 至方法实际覆盖范围。",
                "high", 0.7))
        elif cover.get("results", 0) < COVER and cover.get("conclusion", 0) < COVER:
            n += 1
            findings.append(make_finding(
                f"E-{n:02d}", "research_question", "研究问题无结果/结论回应",
                rq["section"], rq["para_id"], rq["sentence_id"], rq["text"],
                f"该 RQ 内容词在结果章覆盖率 {cover.get('results', 0):.2f}、结论章 "
                f"{cover.get('conclusion', 0):.2f}（阈值 {COVER}），问题提出后无人回答。",
                "add", "在结果/结论中以相同术语显式回应此 RQ（回答了没有、证据在哪），或在引言删除该问题。",
                "high", 0.7))

    # ---- 贡献主张 × 证据映射 ----
    contrib_rows = []
    ev_paras = [p for p in model["paragraphs"]
                if classify_role(p["section"]) in ("results", "experiment", "discussion")
                and (EVIDENCE_NUMBER.search(p["text"]) or EVIDENCE_FIGTAB.search(p["text"]))]
    if not contribs:
        n += 1
        findings.append(make_finding(
            f"E-{n:02d}", "research_question", "贡献主张缺失",
            "(全文)", None, None, "(未检出'贡献/contribution/首次提出'等提示语)",
            "全文未显式陈述贡献主张；读者需自行从方法/结果中归纳本文做了什么。",
            "add", "在引言末尾以条目列出 2-4 条贡献主张，每条与后文章节一一对应。",
            "medium", 0.65))
    for c in contribs:
        ct = terms(c["text"])
        best_p, best_sim = None, 0.0
        for p in ev_paras:
            sim = jaccard(ct, terms(p["text"]))
            if sim > best_sim:
                best_p, best_sim = p, sim
        verdict = ("supported" if best_sim >= 0.25 else
                   "weak" if best_sim >= 0.12 else "unsupported")
        contrib_rows.append({"claim": short(c["text"], 100),
                             "location": {"section": c["section"], "para_id": c["para_id"],
                                          "sentence_id": c["sentence_id"]},
                             "best_evidence_para": best_p["id"] if best_p else None,
                             "best_evidence_section": best_p["section"] if best_p else None,
                             "overlap": round(best_sim, 3), "verdict": verdict})
        if verdict == "unsupported":
            n += 1
            findings.append(make_finding(
                f"E-{n:02d}", "research_question", "贡献主张无对应证据段落",
                c["section"], c["para_id"], c["sentence_id"], c["text"],
                f"与结果/实验中含数据或图表锚点段落的最大术语重叠仅 {best_sim:.2f}（<0.12），"
                "该贡献主张在已完成工作中找不到对应证据。",
                "narrow", "核实该贡献是否确已完成后删除或降级（'尝试/初步探索'），或在结果章补齐对应证据段落。",
                "high", 0.65))
        elif verdict == "weak":
            n += 1
            findings.append(make_finding(
                f"E-{n:02d}", "research_question", "贡献主张证据偏弱",
                c["section"], c["para_id"], c["sentence_id"], c["text"],
                f"最佳证据段落为 {best_p['id']}（{best_p['section']}），重叠 {best_sim:.2f}，"
                "主张与证据的对应关系不直接。",
                "narrow", "在该贡献句或证据段落处补交叉引用（'见表X/第Y节'），使主张—证据一一对应。",
                "medium", 0.6))

    # ---- 首尾呼应：摘要/引言论断 × 结论 ----
    head_claims = [s for s in model["sentences"]
                   if classify_role(s["section"]) in ("abstract", "introduction")
                   and CLAIM_CUES.search(s["text"])]
    concl = [s for s in model["sentences"] if classify_role(s["section"]) == "conclusion"]
    concl_terms = [terms(s["text"]) for s in concl]
    echo_rows, no_echo = [], []
    for s in head_claims:
        sims = [jaccard(terms(s["text"]), ct) for ct in concl_terms] or [0.0]
        best = max(sims)
        echo_rows.append({"head_claim": short(s["text"], 100),
                          "location": {"section": s["section"], "sentence_id": s["id"]},
                          "best_conclusion_echo": round(best, 3)})
        if best < THRESH["claim_echo_jaccard"] and concl:
            no_echo.append((s, best))
    for s, best in no_echo[:6]:
        n += 1
        findings.append(make_finding(
            f"E-{n:02d}", "research_question", "摘要/引言论断在结论中无呼应",
            s["section"], s["para_id"], s["id"], s["text"],
            f"该论断与结论各句最大相似度 {best:.2f}（阈值 {THRESH['claim_echo_jaccard']}），"
            "前文承诺后文未兑现，首尾闭环断裂。",
            "add", "在结论补一句对该论断的回应（兑现/修正/说明未覆盖原因），或从前文删改该承诺。",
            "medium", 0.6))

    rq_map = {
        "method_note": "RQ/贡献句由提示词正则抽取；覆盖率为内容词 Jaccard；阈值见 scanutil.THRESH，全部可复核。",
        "research_questions": rq_rows, "contributions": contrib_rows,
        "head_conclusion_echo": echo_rows,
        "summary": {"n_rq": len(rqs), "n_contribution": len(contribs),
                    "n_head_claims": len(head_claims), "n_no_echo": len(no_echo)},
    }
    with open(os.path.join(args.work, "rq_map.json"), "w", encoding="utf-8") as f:
        json.dump(rq_map, f, ensure_ascii=False, indent=1)
    save_findings(args.work, "findings_engine.json", findings)
    append_change_log(args.work, [{
        "step": "rq_engine", "action": "研究问题与贡献主张对齐深度分析",
        "detail": f"RQ={len(rqs)} 贡献={len(contribs)} 首尾论断={len(head_claims)}，深度问题 {len(findings)} 条",
        "artifact": "work/rq_map.json + work/findings_engine.json"}])
    print(f"[rq_engine] RQ={len(rqs)} 贡献={len(contribs)} 无呼应={len(no_echo)} 深度findings={len(findings)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
