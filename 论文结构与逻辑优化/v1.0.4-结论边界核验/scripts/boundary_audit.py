#!/usr/bin/env python3
"""boundary_audit.py — V5 主攻引擎：结论边界与表述尺度深度核验。

产出:
  work/boundary_audit.json   数字溯源表（逐条 verdict）+ 因果三档表 + 范围比对表 + 限制审计
  work/findings_engine.json  深度 findings（dimension=conclusion_boundary，report_builder 合并去重）

分析对象: 角色为 abstract / conclusion 的句子 + discussion 章末段句子（目标句）。
方法（可复核，判据详见 references/boundary_rules.md）:
  a) 数字溯源三层匹配：逐字命中 ok → 数值相等格式不同 format_diff（提示人工）→
     相对差≤5% 且可由四舍五入得到 approx（疑似四舍五入/笔误）→ 完全无匹配 stray（无源数字）。
     年份(19xx/20xx)与编号(图1/表2/[3]/式4)不计入。
  b) 摘要-结论一致性：内容词 Jaccard≥0.4 的摘要-结论句对，数字集合不一致 → finding。
  c) 因果三档：方法/实验章有 DESIGN_CUES → supported；正文仅 CORRELATION_CUES →
     overreach（降级为关联表述）；两者都无 → unverifiable（人工确认）。
  d) 绝对化表述：ABSOLUTE_CUES 句 → qualify（限定适用范围）。
  e) 推广超界：结论出现范围词（所有体系/任何/通用/universal…）而方法/实验章只测有限条件
     → qualify（枚举已测条件作证据）。
  f) 限制说明审计：LIMITATION_CUES 完全缺失 → add_limitation；仅在致谢/附录 → move；
     仅一句且无量化边界 → add（不充分）。
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scanutil import (CAUSAL_CUES, CORRELATION_CUES, ABSOLUTE_CUES, DESIGN_CUES,
                      LIMITATION_CUES, NUM_IN_CONCL, terms, jaccard, classify_role,
                      short, make_finding, load_structure, save_findings,
                      append_change_log)

TARGET_ROLES = ("abstract", "conclusion")          # + discussion 末段
SOURCE_ROLES = ("method", "experiment", "results", "discussion")  # 数字溯源源章
MAX_FINDINGS = 15
APPROX_TOL = 0.05        # 相对差容差（另须满足舍入一致性，见 boundary_rules.md §1）
ECHO_JACCARD = 0.4       # 摘要-结论同语境句对判定

SCOPE_CUES = re.compile(
    r"(所有体系|各类体系|各种体系|任何体系|任意体系|所有材料|任何材料|通用的?|普适|"
    r"广泛适用|普遍适用|适用面广|universal(ly)?|generally applicable|"
    r"applicable to all|all (systems|materials|datasets)|any (system|material|dataset))", re.I)
YEAR_RE = re.compile(r"^(19|20)\d{2}$")
REFCTX_RE = re.compile(r"(图|表|附图|附表|式|公式|节|章|第|Fig\.?|Figure|Table|Tab\.?|"
                       r"Eq\.?|Equation|Section|\[)\s*$", re.I)
ENTITY_RE = re.compile(r"([一-鿿A-Za-z0-9\-]{2,8}?)(?:体系|材料|电池|负极|正极|数据集|模型|催化剂|合金)")


def decimals(token):
    m = re.search(r"\.(\d+)", token)
    return len(m.group(1)) if m else 0


def unit_of(token):
    if re.search(r"[%％]", token):
        return "%"
    if re.search(r"[倍×]", token):
        return "x"
    return ""


def extract_numbers(text):
    """返回 [{'token','value','unit'}]，剔除年份与图表/公式/章节编号。"""
    out = []
    for m in NUM_IN_CONCL.finditer(text):
        tok = m.group(0).strip()
        if not tok:
            continue
        core = re.match(r"\d+(?:\.\d+)?", tok).group(0)
        if YEAR_RE.match(core) and unit_of(tok) == "":
            continue
        if REFCTX_RE.search(text[:m.start()]):
            continue
        out.append({"token": tok, "value": float(core), "unit": unit_of(tok)})
    return out


def scaled_equal(a, ua, b, ub):
    """数值相等判定：含 % 与无量纲的 ×100 换算。"""
    if abs(a - b) < 1e-9 and ua == ub:
        return True
    if ua != ub:
        if abs(a * 100 - b) < 1e-6 or abs(a - b * 100) < 1e-6:
            return True
    return False


def rounding_consistent(src, tgt):
    """tgt 是否可由 src 经四舍五入（按对方小数位）得到。"""
    return (abs(round(src["value"], decimals(tgt["token"])) - tgt["value"]) < 1e-9
            or abs(round(tgt["value"], decimals(src["token"])) - src["value"]) < 1e-9)


def sent_role(model, sent):
    h = next((x["heading"] for x in model["sections"] if x["id"] == sent["section_id"]), "")
    return classify_role(h)


def target_sentences(model):
    """abstract / conclusion 全部句 + discussion 章末段句。"""
    out, disc = [], {}
    for s in model["sentences"]:
        r = sent_role(model, s)
        if r in TARGET_ROLES:
            out.append(s)
        elif r == "discussion":
            disc.setdefault(s["section_id"], []).append(s)
    for ss in disc.values():
        last_para = max(x["para_id"] for x in ss)
        out.extend(x for x in ss if x["para_id"] == last_para)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    model = load_structure(args.work)
    findings, n = [], 0

    def add(dimension, ftype, section, para_id, sent_id, quote, evidence,
            op, instruction, severity, confidence, status="待作者复核"):
        nonlocal n
        n += 1
        findings.append(make_finding(f"E-{n:02d}", dimension, ftype, section,
                                     para_id, sent_id, quote, evidence,
                                     op, instruction, severity, confidence, status))

    targets = target_sentences(model)
    sources = [s for s in model["sentences"] if sent_role(model, s) in SOURCE_ROLES]
    src_text_norm = re.sub(r"\s+", "", " ".join(s["text"] for s in sources))
    src_nums = []
    for s in sources:
        for num in extract_numbers(s["text"]):
            src_nums.append({**num, "section": s["section"], "sentence_id": s["id"],
                             "sentence": short(s["text"], 90)})

    # ---------- a) 数字溯源（三层匹配） ----------
    prov_rows, seen = [], set()
    cnt = {"ok": 0, "format_diff": 0, "approx": 0, "stray": 0}
    for s in targets:
        for num in extract_numbers(s["text"]):
            key = (s["id"], num["token"])
            if key in seen:
                continue
            seen.add(key)
            row = {"number": num["token"], "location": {
                       "section": s["section"], "para_id": s["para_id"], "sentence_id": s["id"]},
                   "sentence": short(s["text"], 90), "verdict": None,
                   "matched_source": None, "rel_diff": None}
            if re.sub(r"\s+", "", num["token"]) in src_text_norm:
                row["verdict"] = "ok"
            else:
                eq = next((x for x in src_nums
                           if scaled_equal(num["value"], num["unit"], x["value"], x["unit"])), None)
                if eq:
                    row["verdict"], row["matched_source"] = "format_diff", eq
                    add("conclusion_boundary", "数字与正文数值相等但表述格式不同",
                        s["section"], s["para_id"], s["id"], s["text"],
                        f"数字 {num['token']} 与 {eq['section']} 的 {eq['token']} 数值相等"
                        "（如小数/百分数换算），但表述格式不一致，读者无法直接对号。",
                        "qualify", "统一数字表述格式（全文同用百分数或同用小数），或在该处注明与正文数据的对应关系。",
                        "low", 0.55, "需人工确认")
                else:
                    cands = [x for x in src_nums if x["unit"] == num["unit"] and x["value"] != 0]
                    best = min(cands, key=lambda x: abs(x["value"] - num["value"])
                               / max(abs(x["value"]), abs(num["value"])), default=None)
                    if best is not None:
                        row["rel_diff"] = round(abs(best["value"] - num["value"])
                                                / max(abs(best["value"]), abs(num["value"])), 4)
                    if best is not None and row["rel_diff"] <= APPROX_TOL \
                            and rounding_consistent(best, num):
                        row["verdict"], row["matched_source"] = "approx", best
                        add("conclusion_boundary", "结论数字疑似四舍五入或笔误",
                            s["section"], s["para_id"], s["id"], s["text"],
                            f"数字 {num['token']} 与 {best['section']} 的 {best['token']} 相对差 "
                            f"{row['rel_diff']:.2%}（容差 {APPROX_TOL:.0%}），可由其舍入得到，"
                            "疑似四舍五入或笔误。",
                            "qualify", "核对该数字与正文出处：四舍五入则统一精度并注明，笔误则改正为正文数值。",
                            "medium", 0.65)
                    else:
                        row["verdict"], row["matched_source"] = "stray", best
                        add("conclusion_boundary", "结论/摘要数字无正文出处（无源数字）",
                            s["section"], s["para_id"], s["id"], s["text"],
                            f"数字 {num['token']} 在方法/实验/结果/讨论章无逐字命中、无数值相等、"
                            + (f"最近源数字为 {best['token']}（{best['section']}），相对差 "
                               f"{row['rel_diff']:.2%}"
                               + ("超出容差。" if row["rel_diff"] > APPROX_TOL
                                  else "在容差内但无法由舍入得到（非四舍五入，疑似篡改）。")
                               if best else "源章未检出任何可比对数字。"),
                            "narrow", "为该数字补正文出处（指向具体表格/小节），或从结论/摘要中删除或改为正文已有数值。",
                            "high", 0.75)
            cnt[row["verdict"]] += 1
            prov_rows.append(row)

    # ---------- b) 摘要-结论数字一致性 ----------
    echo_rows = []
    abs_s = [s for s in model["sentences"] if sent_role(model, s) == "abstract"]
    con_s = [s for s in model["sentences"] if sent_role(model, s) == "conclusion"]
    done_pair = set()
    for a in abs_s:
        na = extract_numbers(a["text"])
        if not na:
            continue
        for c in con_s:
            nc = extract_numbers(c["text"])
            if not nc:
                continue
            sim = jaccard(terms(a["text"]), terms(c["text"]))
            if sim < ECHO_JACCARD:
                continue
            unmatched_a = [x for x in na if not any(
                scaled_equal(x["value"], x["unit"], y["value"], y["unit"]) for y in nc)]
            unmatched_c = [y for y in nc if not any(
                scaled_equal(y["value"], y["unit"], x["value"], x["unit"]) for x in na)]
            echo_rows.append({"abstract_sentence": short(a["text"], 90),
                              "conclusion_sentence": short(c["text"], 90),
                              "jaccard": round(sim, 3),
                              "abstract_numbers": [x["token"] for x in na],
                              "conclusion_numbers": [y["token"] for y in nc],
                              "consistent": not (unmatched_a or unmatched_c)})
            if (unmatched_a or unmatched_c) and c["id"] not in done_pair:
                done_pair.add(c["id"])
                add("conclusion_boundary", "摘要与结论同语境数字不一致",
                    c["section"], c["para_id"], c["id"], c["text"],
                    f"与摘要句（Jaccard={sim:.2f}≥{ECHO_JACCARD}）同语境，但摘要数字 "
                    f"{[x['token'] for x in na]} 与结论数字 {[y['token'] for y in nc]} 对不上"
                    f"（摘要有 {[x['token'] for x in unmatched_a]}，结论有 {[y['token'] for y in unmatched_c]}）。",
                    "narrow", "以正文数据为准统一摘要与结论数字；两处必须逐字一致，任何舍入须在两处同步。",
                    "high", 0.75)

    # ---------- c) 因果表述三档 ----------
    design_text = " ".join(s["text"] for s in model["sentences"]
                           if sent_role(model, s) in ("method", "experiment"))
    body_text = " ".join(s["text"] for s in model["sentences"])
    has_design = bool(DESIGN_CUES.search(design_text))
    has_corr = bool(CORRELATION_CUES.search(body_text))
    causal_rows, n_over = [], 0
    for s in targets:
        if not CAUSAL_CUES.search(s["text"]):
            continue
        if has_design:
            verdict = "supported"
        elif has_corr:
            verdict = "overreach"
        else:
            verdict = "unverifiable"
        causal_rows.append({"sentence": short(s["text"], 90),
                            "location": {"section": s["section"], "para_id": s["para_id"],
                                         "sentence_id": s["id"]},
                            "verdict": verdict})
        if verdict == "overreach":
            n_over += 1
            add("conclusion_boundary", "因果表述超出证据强度（正文仅支持相关）",
                s["section"], s["para_id"], s["id"], s["text"],
                "该句含因果动词（导致/提升/improve 等），但方法/实验章未检出对照/随机/消融等"
                "因果设计词，正文仅出现相关性提示词（相关/关联/correlation），因果强度超出证据。",
                "narrow", "将因果表述降级为关联表述（'与…相关''在…条件下观察到'），或在方法章补充支持因果的实验设计。",
                "high", 0.7)
        elif verdict == "unverifiable":
            add("conclusion_boundary", "因果表述无法核验（无设计词亦无相关性说明）",
                s["section"], s["para_id"], s["id"], s["text"],
                "该句含因果动词，但方法/实验章无对照/随机/消融设计词，正文也无相关性表述，"
                "因果主张的证据基础无法从文本核验。",
                "qualify", "人工确认因果证据：补实验设计引用，或改写为'本文条件下观察到'类限定表述。",
                "medium", 0.55, "需人工确认")

    # ---------- d) 绝对化表述 / e) 推广超界 ----------
    me_text = " ".join(s["text"] for s in model["sentences"]
                       if sent_role(model, s) in ("method", "experiment"))
    entities = []
    for e in ENTITY_RE.findall(me_text):
        e = e.strip("，。、的在用对为与及")
        if e and e not in entities:
            entities.append(e)
    scope_rows = []
    for s in targets:
        m = SCOPE_CUES.search(s["text"])
        if m:
            scope_rows.append({"sentence": short(s["text"], 90), "scope_word": m.group(0),
                               "location": {"section": s["section"], "para_id": s["para_id"],
                                            "sentence_id": s["id"]},
                               "tested_entities": entities[:8],
                               "verdict": "overgeneralized"})
            ev = (f"结论使用范围词「{m.group(0)}」，但方法/实验章"
                  + (f"仅检出有限测试条件（体系/材料/数据集线索：{'、'.join(entities[:6])}），"
                     "无支撑全域推广的证据。" if me_text.strip() else
                     "未检出（无法核验推广范围）。"))
            add("conclusion_boundary", "结论推广范围超出实验条件",
                s["section"], s["para_id"], s["id"], s["text"], ev,
                "qualify", "将范围词限定为已测条件（'在本文测试的X体系中'），或在实验章补充多体系验证数据。",
                "high", 0.7 if me_text.strip() else 0.6)
        elif ABSOLUTE_CUES.search(s["text"]):
            add("conclusion_boundary", "绝对化表述",
                s["section"], s["para_id"], s["id"], s["text"],
                "结论/摘要句含绝对化量词（所有/任何/完全/always/never），单研究证据一般不支持全域断言。",
                "qualify", "限定适用范围：补出适用条件（数据规模/体系/工况），或将绝对词改为限定词（'在本文条件下'）。",
                "medium", 0.65)

    # ---------- f) 限制说明审计 ----------
    lim_hits = [{"sentence": short(s["text"], 90), "section": s["section"],
                 "role": sent_role(model, s), "sentence_id": s["id"],
                 "has_number": bool(extract_numbers(s["text"]))}
                for s in model["sentences"] if LIMITATION_CUES.search(s["text"])]
    good_roles = [h for h in lim_hits if h["role"] in ("discussion", "conclusion")]
    if not lim_hits:
        lim_verdict = "missing"
        add("conclusion_boundary", "缺少局限性说明",
            "(全文)", None, None, "(未检出 局限/不足/未来工作/limitation 等提示语)",
            "全文未检出局限性提示词；结论边界声明缺失，读者无法判断结论的适用条件与失效边界。",
            "add_limitation", "在讨论末尾或结论前补 1 段局限性说明（样本/方法假设/外推边界），最好含量化边界。",
            "medium", 0.7)
    elif not good_roles:
        lim_verdict = "misplaced"
        h0 = lim_hits[0]
        add("conclusion_boundary", "局限性说明位置不当",
            h0["section"], None, h0["sentence_id"], h0["sentence"],
            f"局限性提示词仅出现在 {h0['section']}（角色 {h0['role']}），"
            "不在讨论/结论主线中，读者在结论处看不到边界声明。",
            "move", "将局限性说明移至讨论章末尾或结论章首段，使其与结论同视野出现。",
            "medium", 0.65)
    elif len(good_roles) == 1 and not good_roles[0]["has_number"]:
        lim_verdict = "insufficient"
        h0 = good_roles[0]
        add("conclusion_boundary", "局限性说明不充分（仅一句且无量化边界）",
            h0["section"], None, h0["sentence_id"], h0["sentence"],
            "全文仅一句局限性表述且不含任何数字边界（样本量/适用范围/误差区间），"
            "不足以支撑读者判断结论尺度。",
            "add", "扩充局限性说明：补量化边界（如样本量、测试工况区间、误差范围）与失效条件。",
            "low", 0.6)
    else:
        lim_verdict = "adequate"
    lim_audit = {"hits": lim_hits, "verdict": lim_verdict}

    # ---------- 汇总 ----------
    sev_rank = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: sev_rank.get(f["severity"], 3))
    findings = findings[:MAX_FINDINGS]
    audit = {
        "method_note": "数字溯源=三层匹配（逐字/等值换算/舍入容差5%）；年份与图表编号不计入；"
                       "因果三档依据方法实验章设计词与正文相关性词；范围比对枚举方法实验章体系名词；"
                       "目标句=摘要/结论全部句+讨论末段。全部中间值见本文件，可复核。",
        "number_provenance": prov_rows,
        "abstract_conclusion_consistency": echo_rows,
        "causal_audit": causal_rows,
        "scope_audit": scope_rows,
        "limitation_audit": lim_audit,
        "summary": {"n_numbers": len(prov_rows), **cnt,
                    "n_causal": len(causal_rows), "n_overreach": n_over,
                    "n_scope": len(scope_rows), "limitation_verdict": lim_verdict,
                    "n_findings": len(findings)},
    }
    with open(os.path.join(args.work, "boundary_audit.json"), "w", encoding="utf-8") as f:
        json.dump(audit, f, ensure_ascii=False, indent=1)
    save_findings(args.work, "findings_engine.json", findings)
    append_change_log(args.work, [{
        "step": "boundary_audit", "action": "结论边界与表述尺度深度核验",
        "detail": f"数字={len(prov_rows)}（ok={cnt['ok']} approx={cnt['approx']} stray={cnt['stray']}）"
                  f" 因果句={len(causal_rows)}（overreach={n_over}） 范围词={len(scope_rows)}"
                  f" 限制={lim_verdict}，深度问题 {len(findings)} 条",
        "artifact": "work/boundary_audit.json + work/findings_engine.json"}])
    print(f"[boundary_audit] nums={len(prov_rows)} ok={cnt['ok']} approx={cnt['approx']} "
          f"stray={cnt['stray']} causal={len(causal_rows)} over={n_over} findings={len(findings)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
