#!/usr/bin/env python3
"""style_engine.py — 学术风格控制引擎（v1.0.3 学术风格方向）。

仅 audit 子命令（译后运行）：对 translations.jsonl 中译文做语域与句式机检，
区分两类问题：
  A. 直译痕迹（translationese）：中文目标——动词名词化（进行/做出+研究）、
     被动滥用（被字句密度）、超长前置定语（20+字+的）、英式连接（对于…来说/
     在…的情况下/由于…的原因/作为…的）、长句（>90字）；
     英文目标——It is well known that / with the development of /
     more and more / 感叹号。
  B. 语域越界：宣传口吻（革命性/颠覆性/突破性/完美/极大地/世界一流；
     英文 revolutionary/perfect/amazing）、口语化（东西/搞/挺/蛮；
     英文 a lot of/big thing）、第一人称单数（我/你；英文 I/we 之外语境的 you）。
输出 work/style_report.json（指标+逐句段问题）与 work/findings.json（学术风格维度）。
用法: python3 style_engine.py audit --work /app/work
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trans_utils as tu

ZH_PATTERNS = [
    ("直译-动词名词化", re.compile(r"(进行|做出|作出|给予|加以|实现)[一-鿿]{0,4}的?"
     r"(研究|实验|分析|处理|测试|测量|计算|表征|优化|制备|讨论|比较|合成|改性)"),
     "改为动词直接谓语，如「研究了/表征了」", "低"),
    ("直译-被动滥用", re.compile(r"被[一-鿿]{1,12}(?:为|所)?"),
     "中文优先主动或「由/经/通过」；仅在被动的施事不明或习惯被动时保留", "低"),
    ("直译-超长前置定语", re.compile(r"[一-鿿]{15,}的[一-鿿]{1,12}"),
     "拆为短句或后置从句，避免 15 字以上连续定语链", "中"),
    ("直译-英式连接", re.compile(r"(对于[一-鿿]{2,20}来说|在[一-鿿]{2,20}的情况下|"
     r"由于[一-鿿]{2,20}的原因|作为[一-鿿]{1,15}的[一-鿿]{1,8}|"
     r"值得指出的是|众所周知)"),
     "改为中文惯用衔接或直接陈述", "低"),
    ("语域-宣传口吻", re.compile(r"(革命性|颠覆性|突破性|完美|完美地|极大地|空前的|"
     r"世界一流|遥遥领先|巨大贡献|重大意义)"),
     "学术语域要求克制表述，改为中性陈述或删除", "高"),
    ("语域-口语化", re.compile(r"(东西|搞[一-鿿]{0,3}|挺[一-鿿]{1,3}|蛮[一-鿿]{1,3}|"
     r"啥|咱们|好吧|对吧)"),
     "改为书面学术用语", "中"),
    ("语域-第一人称单数", re.compile(r"(?<![一-鿿])(我|我的|你|你的)(?![一-鿿])"),
     "学术文本用无人称或「本文/本研究」", "中"),
]
EN_PATTERNS = [
    ("直译-中式套话", re.compile(r"\b(It is well known that|With the (rapid )?development of|"
     r"more and more|plays an? (important|key) role|As we all know)\b", re.I),
     "改为具体陈述或删除空转套话", "低"),
    ("语域-宣传口吻", re.compile(r"\b(revolutionary|groundbreaking|perfect|perfectly|"
     r"amazing|remarkable breakthrough|world-class)\b", re.I),
     "学术语域要求克制表述", "高"),
    ("语域-口语化", re.compile(r"\b(a lot of|lots of|big deal|stuff|kind of|sort of)\b", re.I),
     "改为书面学术用语", "中"),
    ("语域-感叹号", re.compile(r"!"), "学术正文避免感叹号", "中"),
]

def audit_text(sid, section, tr, target_lang):
    pats = ZH_PATTERNS if target_lang == "zh" else EN_PATTERNS
    issues = []
    for name, pat, advice, sev in pats:
        for m in pat.finditer(tr):
            issues.append({"type": name, "span": list(m.span()),
                           "excerpt": m.group(0)[:60], "advice": advice, "severity": sev})
    # 长句（中文 >90 字；英文 >45 词）
    if target_lang == "zh":
        for sent in re.split(r"(?<=[。！？；])", tr):
            if len(sent) > 90:
                issues.append({"type": "句式-超长句", "span": None,
                               "excerpt": sent[:60] + "…",
                               "advice": f"该句 {len(sent)} 字，建议按逻辑拆为 2-3 句",
                               "severity": "低"})
    else:
        for sent in re.split(r"(?<=[.!?])\s+", tr):
            w = len(sent.split())
            if w > 45:
                issues.append({"type": "句式-超长句", "span": None,
                               "excerpt": sent[:60] + "…",
                               "advice": f"该句 {w} 词，建议拆分",
                               "severity": "低"})
    return issues

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["audit"])
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    segdata = tu.load_json(os.path.join(args.work, "segments.json"))
    if not segdata:
        print("[style_engine][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    insp = tu.load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    target_lang = (insp.get("translation_task") or {}).get("target_lang") or "zh"
    merged, _ = tu.load_translations(args.work)

    findings = []
    per_seg = []
    n_find = 0
    tot_chars = tot_issues = 0
    passive_cnt = de_cnt = 0
    for s in segdata["segments"]:
        if not s["needs_translation"]:
            continue
        tr = merged.get(s["seg_id"])
        if not tr:
            continue
        tot_chars += len(tr)
        if target_lang == "zh":
            passive_cnt += len(re.findall(r"被", tr))
            de_cnt += len(re.findall(r"的", tr))
        issues = audit_text(s["seg_id"], s.get("section"), tr, target_lang)
        # 每个句段同类问题只报一次（取首个实例），避免刷屏
        seen_types = set()
        uniq = []
        for it in issues:
            if it["type"] in seen_types:
                continue
            seen_types.add(it["type"])
            uniq.append(it)
        tot_issues += len(uniq)
        if uniq:
            per_seg.append({"seg_id": s["seg_id"], "section": s.get("section"),
                            "translation": tr[:200], "issues": uniq})
        for it in uniq:
            n_find += 1
            findings.append({
                "id": f"STY-{n_find:03d}", "dimension": "学术风格", "type": it["type"],
                "location": {"seg_id": s["seg_id"], "section": s.get("section")},
                "quote": s["source"][:120],
                "evidence": f"译文片段「{it['excerpt']}」命中规则：{it['type']}。"
                            f"译文：{tr[:150]}",
                "action": {"op": "de_literalize", "instruction": it["advice"]},
                "severity": it["severity"], "confidence": 0.7,
                "status": "脚本候选"})

    metrics = {"target_lang": target_lang, "chars": tot_chars,
               "issue_segments": len(per_seg), "issues_total": tot_issues}
    if target_lang == "zh" and tot_chars:
        metrics["de_per_100_chars"] = round(de_cnt / tot_chars * 100, 2)
        metrics["passive_per_100_chars"] = round(passive_cnt / tot_chars * 100, 2)
        metrics["note"] = "的密度>4.5/百字 或 被字>0.6/百字 通常提示直译腔"
    tu.save_json(os.path.join(args.work, "style_report.json"),
                 {"metrics": metrics, "segments": per_seg})
    old = tu.load_json(os.path.join(args.work, "findings.json"), []) or []
    old = [f for f in old if f.get("dimension") != "学术风格"]
    tu.save_json(os.path.join(args.work, "findings.json"), old + findings)
    print(f"[style_engine audit] 句段问题={len(per_seg)} findings+{len(findings)} "
          f"指标={metrics}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
