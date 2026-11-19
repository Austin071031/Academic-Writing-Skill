#!/usr/bin/env python3
"""audience_engine.py — 受众画像与可读性引擎（v1.0.0 专属）。

子命令:
  profile  --inspection work/inspection.json --source work/source.json [--work /app/work]
      → work/audience_profile.json：受众画像、篇幅约束、术语处置计划（jargon_plan）、
        可读性目标（句长上限/术语密度上限/缩写展开要求）。
  check    --rewrite <改写稿.md> [--work /app/work]
      → work/readability_report.json + work/readability_report.md：
        逐指标达标判定、未展开缩写、未解释术语、超长句、篇幅超限，均带 rpid 定位。
判据与 references/audience_rules.md 的阈值表保持一致。
"""
import argparse, json, os, re, sys

# 受众 → 可读性目标（与 references/audience_rules.md 一致）
AUDIENCE_RULES = {
    "公众/科普读者":      {"max_sent_chars": 45, "avg_sent_chars": 30, "jargon_density_max": 0.03,
                           "acronym_policy": "expand_first", "explain_terms": True},
    "学生读者":           {"max_sent_chars": 55, "avg_sent_chars": 35, "jargon_density_max": 0.05,
                           "acronym_policy": "expand_first", "explain_terms": True},
    "投资人/产业界":      {"max_sent_chars": 55, "avg_sent_chars": 35, "jargon_density_max": 0.05,
                           "acronym_policy": "expand_first", "explain_terms": True},
    "政策制定者/管理者":  {"max_sent_chars": 55, "avg_sent_chars": 35, "jargon_density_max": 0.04,
                           "acronym_policy": "expand_first", "explain_terms": True},
    "项目评审专家":       {"max_sent_chars": 70, "avg_sent_chars": 45, "jargon_density_max": 0.08,
                           "acronym_policy": "expand_first", "explain_terms": False},
    "跨学科同行":         {"max_sent_chars": 65, "avg_sent_chars": 40, "jargon_density_max": 0.06,
                           "acronym_policy": "expand_first", "explain_terms": True},
    "本领域同行":         {"max_sent_chars": 80, "avg_sent_chars": 50, "jargon_density_max": 0.10,
                           "acronym_policy": "allow", "explain_terms": False},
    "unspecified":        {"max_sent_chars": 55, "avg_sent_chars": 35, "jargon_density_max": 0.05,
                           "acronym_policy": "expand_first", "explain_terms": True},
}
EXPLAIN_HINT = re.compile(r"(即|也就是|也就是说|指的是|通俗地说|简单来说|所谓|是一种|指的是|"
                          r"[（(][^（）()]{2,40}[)）]|——|：)", )
SENT_SPLIT = re.compile(r"[。！？!?；;]+")

def split_sentences(text):
    return [s.strip() for s in SENT_SPLIT.split(text) if s.strip()]

def split_paragraphs(text):
    out = []
    for b in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        b = re.sub(r"^#{1,6}\s*", "", b.strip())
        if b:
            out.append(b)
    return out

def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def cmd_profile(args):
    insp = load(args.inspection, {})
    src = load(args.source, {})
    audience = insp.get("audience", "unspecified")
    rules = AUDIENCE_RULES.get(audience, AUDIENCE_RULES["unspecified"])
    genre = insp.get("genre") or ["科普文章"]
    length_limit = insp.get("length_limit")

    jargon_plan = []
    for a in src.get("acronyms", []):
        if a["count"] < 1:
            continue
        if rules["acronym_policy"] == "allow":
            action = "保留"
            hint = "本领域同行受众可直接使用缩写"
        elif a.get("expanded") and a.get("expansion"):
            action = "首次展开后使用"
            hint = f"首次出现写全称：{a['expansion']}（{a['raw']}），之后可用缩写"
        else:
            action = "展开或替换"
            hint = "源文未给全称：用中文描述性说法替换，或在术语表标注待作者确认全称"
        jargon_plan.append({"term": a["raw"], "kind": "acronym", "count": a["count"],
                            "action": action, "hint": hint})
    for t in src.get("term_candidates", []):
        if t["kind"] != "zh_term" or t["count"] < 2:
            continue
        action = "解释后使用" if rules["explain_terms"] else "保留"
        hint = ("首次出现处用一句话或类比解释其含义" if rules["explain_terms"]
                else "评审/同行受众可直接使用")
        jargon_plan.append({"term": t["term"], "kind": "zh_term", "count": t["count"],
                            "action": action, "hint": hint})

    profile = {"audience": audience, "genre": genre, "length_limit": length_limit,
               "rules": rules, "jargon_plan": jargon_plan,
               "writing_targets": {
                   "max_sent_chars": rules["max_sent_chars"],
                   "avg_sent_chars": rules["avg_sent_chars"],
                   "jargon_density_max": rules["jargon_density_max"],
                   "length_note": (f"篇幅上限 {length_limit['value']}{length_limit['unit']}"
                                   if length_limit else "未指定篇幅上限，建议不超过源文 60%")},
               "notes": insp.get("issues", [])}
    op = os.path.join(args.work, "audience_profile.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
    print(f"[audience:profile] 受众={audience} 文体={genre} 术语计划={len(jargon_plan)} 条 "
          f"句长目标≤{rules['max_sent_chars']} 篇幅={length_limit}")
    return 0

def cmd_check(args):
    work = args.work
    profile = load(os.path.join(work, "audience_profile.json"), {})
    align = load(os.path.join(work, "alignment.json"), {})
    rules = profile.get("rules") or AUDIENCE_RULES["unspecified"]
    if not os.path.exists(args.rewrite):
        print(f"[audience:check] 改写稿不存在: {args.rewrite}", file=sys.stderr)
        return 1
    with open(args.rewrite, encoding="utf-8") as f:
        rtext = f.read()

    issues = []
    rparas = split_paragraphs(rtext)
    n_chars = len(re.sub(r"\s", "", rtext))

    # 1. 篇幅
    ll = profile.get("length_limit")
    if ll and ll.get("unit", "字").startswith("字"):
        if n_chars > ll["value"] * 1.05:
            issues.append({"severity": "critical", "type": "length_exceeded",
                           "detail": f"篇幅 {n_chars} 字超过上限 {ll['value']} 字（含 5% 容差）",
                           "location": "全文"})
    length_stat = {"n_chars": n_chars,
                   "limit": ll["value"] if ll else None,
                   "within": (n_chars <= ll["value"] * 1.05) if ll else None}

    # 2. 句长
    sents = []
    for i, p in enumerate(rparas, 1):
        for s in split_sentences(p):
            sents.append((f"R{i:03d}", s, len(re.sub(r"\s", "", s))))
    long_sents = [{"rpid": rpid, "text": s[:60], "n_chars": n}
                  for rpid, s, n in sents if n > rules["max_sent_chars"]]
    avg_len = round(sum(n for _, _, n in sents) / max(1, len(sents)), 1)
    if long_sents:
        issues.append({"severity": "warn", "type": "long_sentence",
                       "detail": f"{len(long_sents)} 句超过 {rules['max_sent_chars']} 字",
                       "location": ",".join(x["rpid"] for x in long_sents[:5])})
    if avg_len > rules["avg_sent_chars"] * 1.3:
        issues.append({"severity": "warn", "type": "avg_sentence_long",
                       "detail": f"平均句长 {avg_len} 字，高于目标 {rules['avg_sent_chars']} 字的 130%",
                       "location": "全文"})

    # 3. 缩写与术语
    plan = {j["term"]: j for j in profile.get("jargon_plan", [])}
    unexplained_acr = []
    for term, j in plan.items():
        if j["kind"] == "acronym" and rules["acronym_policy"] == "expand_first":
            if re.search(r"\b%s\b" % re.escape(term), rtext):
                # 有展开形式？（全称（缩写）或 缩写（全称）或 解释性动词 nearby）
                pat1 = re.search(r"[（(]\s*%s\s*[)）]" % re.escape(term), rtext)
                pat2 = re.search(r"%s\s*[（(][^（）()]{2,40}[)）]" % re.escape(term), rtext)
                if not (pat1 or pat2):
                    unexplained_acr.append(term)
                    issues.append({"severity": "critical", "type": "acronym_not_expanded",
                                   "detail": f"缩写 {term} 在改写稿中未展开/未解释",
                                   "location": "首次出现处"})
    unexplained_terms = []
    if rules["explain_terms"]:
        for term, j in plan.items():
            if j["kind"] != "zh_term":
                continue
            for m in re.finditer(re.escape(term), rtext):
                ctx = rtext[max(0, m.start() - 60): m.end() + 60]
                if not EXPLAIN_HINT.search(ctx):
                    unexplained_terms.append(term)
                    issues.append({"severity": "warn", "type": "term_not_explained",
                                   "detail": f"术语「{term}」上下文未见解释（即/也就是/括号注/类比）",
                                   "location": "首次出现处"})
                    break

    # 4. 术语密度（源文术语在改写稿中的出现占比）
    term_hits = 0
    for term in plan:
        term_hits += len(re.findall(re.escape(term), rtext))
    density = round(term_hits / max(1, n_chars) * 100, 3) / 100
    if density > rules["jargon_density_max"]:
        issues.append({"severity": "warn", "type": "jargon_density_high",
                       "detail": f"术语密度 {density:.1%} 高于目标 {rules['jargon_density_max']:.1%}",
                       "location": "全文"})

    stats = {"length": length_stat, "n_sentences": len(sents),
             "avg_sent_chars": avg_len, "long_sentences": long_sents,
             "unexplained_acronyms": unexplained_acr,
             "unexplained_terms": unexplained_terms,
             "jargon_density": density,
             "n_critical": sum(1 for i in issues if i["severity"] == "critical"),
             "n_warn": sum(1 for i in issues if i["severity"] == "warn")}
    verdict = "PASS" if stats["n_critical"] == 0 else "FAIL"
    report = {"verdict": verdict, "audience": profile.get("audience", "unspecified"),
              "issues": issues, "stats": stats,
              "alignment_stats": align.get("stats")}
    with open(os.path.join(work, "readability_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    lines = ["# 可读性核查报告", "",
             f"- 受众：{report['audience']}　判定：**{verdict}**",
             f"- 篇幅：{n_chars} 字" + (f" / 上限 {ll['value']} 字" if ll else ""),
             f"- 句子 {len(sents)} 句，平均句长 {avg_len} 字（目标 ≤{rules['avg_sent_chars']}），"
             f"超长句 {len(long_sents)} 句（上限 {rules['max_sent_chars']}）",
             f"- 术语密度 {density:.1%}（目标 ≤{rules['jargon_density_max']:.1%}）",
             f"- 未展开缩写 {len(unexplained_acr)} 个：{'、'.join(unexplained_acr) or '无'}",
             f"- 未解释术语 {len(unexplained_terms)} 个：{'、'.join(unexplained_terms[:10]) or '无'}", ""]
    if issues:
        lines += ["## 问题清单", ""]
        for i, it in enumerate(issues, 1):
            lines.append(f"{i}. [{it['severity']}] {it['type']}：{it['detail']}（{it['location']}）")
    else:
        lines.append("全部指标达标。")
    with open(os.path.join(work, "readability_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[audience:check] verdict={verdict} critical={stats['n_critical']} "
          f"warn={stats['n_warn']} avg句长={avg_len} 篇幅={n_chars}")
    return 0 if verdict == "PASS" else 2

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("profile")
    p1.add_argument("--inspection", required=True)
    p1.add_argument("--source", required=True)
    p1.add_argument("--work", default="/app/work")
    p2 = sub.add_parser("check")
    p2.add_argument("--rewrite", required=True)
    p2.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    if args.cmd == "profile":
        return cmd_profile(args)
    return cmd_check(args)

if __name__ == "__main__":
    sys.exit(main())
