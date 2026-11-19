#!/usr/bin/env python3
"""claim_engine.py — 论断强度校准引擎（v1.0.2 专属，方向「说得准」）。

子命令:
  extract --source work/source.json [--work /app/work]
      → work/source_claims.json：从源文段落抽取论断句（含结论标记的句子），
        每条 {claim_id, pid, sentence, level, level_name, causality, markers}。
  check   --rewrite <改写稿.md> [--work /app/work]
      → work/claim_report.json + work/claim_report.md + work/claim_verdicts.jsonl：
        源文论断经 alignment.json（若存在）映射到改写稿段落，逐条判定
        kept / downgraded / upgraded / negation_flip / missing；
        反向检测改写稿中源外新结论（new_claim）。critical 时 exit=2。

强度阶梯（数值越小越强，与 references/claim_rules.md 判据表一致）：
  L0 绝对化：完全解决/彻底解决/从根本上/100%/唯一/首次（+泛化量词 所有/任何）
  L1 确立：  证实/证明/表明/显示/demonstrate/show
  L2 初步：  初步表明/提示/暗示/suggest/indicate
  L3 展望：  有望/可能/预计/potentially/may
因果标记：导致/促使/取决于/因而/cause/due to；相关标记：相关/伴随/关联/correlate/associate。
"""
import argparse, json, os, re, sys

LEVEL_NAMES = {0: "L0 绝对化", 1: "L1 确立", 2: "L2 初步", 3: "L3 展望"}

# 中文强度标记：(marker, level)。L0 分两组：强绝对化措辞触发抽取并定级；
# 泛化量词（所有/任何）不单独触发论断、不单独定级，仅在改写稿新增时判升格。
L1_ZH = ["证实", "证明", "表明", "显示"]
L2_ZH = ["初步表明", "初步显示", "初步证实", "初步", "提示", "暗示"]
L3_ZH = ["有望", "可能", "预计"]
L0_STRONG_ZH = ["完全解决", "彻底解决", "从根本上", "100%", "唯一", "首次"]
L0_WEAK_ZH = ["所有", "任何"]

EN_STRENGTH = [
    (re.compile(r"\bdemonstrat\w*", re.I), 1),
    (re.compile(r"\bshow(?:s|ed|n)?\b", re.I), 1),
    (re.compile(r"\bsuggest\w*", re.I), 2),
    (re.compile(r"\bindicat\w*", re.I), 2),
    (re.compile(r"\bpotentially\b", re.I), 3),
    (re.compile(r"\bmay\b", re.I), 3),
]
CAUSE_ZH = ["导致", "促使", "取决于", "因而"]
CORR_ZH = ["相关", "伴随", "关联"]
EN_CAUSE = re.compile(r"\bcause\w*|\bdue\s+to\b", re.I)
EN_CORR = re.compile(r"\bcorrelat\w*|\bassociat\w*", re.I)

NEG_ZH = ["不", "未", "无", "没有", "并非", "并未", "无法", "不能", "难以"]
EN_NEG = re.compile(r"\b(?:not|no|never|cannot|can't|fail(?:s|ed)?\s+to)\b", re.I)

SENT_SPLIT = re.compile(r"[。！？!?；;\n]+")
MATCH_TH = 0.15   # 2-gram Dice 阈值；低于此值判 missing / new_claim
# 修改建议用的同级措辞
LEVEL_FALLBACK = {1: "「表明/显示」", 2: "「初步表明/提示」", 3: "「有望/可能」", 0: "（源文本身即绝对化措辞，需人工确认）"}


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

def find_strength(sent):
    """返回 (level 或 None, markers list)。level=None 表示无强度标记。
    长标记优先：已命中 span 内部的短标记跳过（如「初步表明」中的「表明」）。"""
    zh = ([(m, 0, "strong") for m in L0_STRONG_ZH]
          + [(m, 2, "strong") for m in L2_ZH]
          + [(m, 3, "strong") for m in L3_ZH]
          + [(m, 1, "strong") for m in L1_ZH]
          + [(m, 0, "weak") for m in L0_WEAK_ZH])
    zh.sort(key=lambda x: -len(x[0]))
    hits = []  # (start, end, marker, level, group)
    for marker, level, group in zh:
        start = 0
        while True:
            i = sent.find(marker, start)
            if i < 0:
                break
            span = (i, i + len(marker))
            if not any(span[0] >= h[0] and span[1] <= h[1] and (span[0], span[1]) != (h[0], h[1])
                       for h in hits):
                hits.append((span[0], span[1], marker, level, group))
            start = i + 1
    for pat, level in EN_STRENGTH:
        for m in pat.finditer(sent):
            hits.append((m.start(), m.end(), m.group(0), level, "strong"))
    strong = [h for h in hits if h[4] == "strong"]
    level = min(h[3] for h in strong) if strong else None
    markers = sorted({h[2] for h in hits})
    # 保守规则：「初步」与 L1 动词同句（如"初步结果表明/显示"）时按 L2 定级——
    # 初步是明确的限定语，丢掉它即构成升格。
    if level == 1 and "初步" in markers:
        level = 2
    return level, markers

def detect_causality(sent):
    cm = [m for m in CAUSE_ZH if m in sent] + [m.group(0) for m in EN_CAUSE.finditer(sent)]
    rm = [m for m in CORR_ZH if m in sent] + [m.group(0) for m in EN_CORR.finditer(sent)]
    if cm:
        return "因果", sorted(set(cm))
    if rm:
        return "相关", sorted(set(rm))
    return "无", []

def has_negation(sent):
    return any(m in sent for m in NEG_ZH) or bool(EN_NEG.search(sent))

def ngrams(text, n=2):
    t = re.sub(r"\s+", "", text)
    t = re.sub(r"[-+−]?\d+(?:\.\d+)?%?", "#", t)  # 数字遮蔽，对齐看语义骨架
    return {t[i:i + n] for i in range(len(t) - n + 1)} if len(t) >= n else {t}

def dice(a, b):
    """2-gram Dice 系数：句级匹配用（containment 对短句/标题有偏）。"""
    if not a or not b:
        return 0.0
    return 2.0 * len(a & b) / (len(a) + len(b))


def cmd_extract(args):
    src = load(args.source)
    if src is None:
        print(f"[claim:extract] source.json 读取失败: {args.source}", file=sys.stderr)
        return 1
    claims = []
    n = 0
    for p in src.get("paragraphs", []):
        for sent in split_sentences(p.get("text", "")):
            level, markers = find_strength(sent)
            if level is None:
                continue
            causality, cmarkers = detect_causality(sent)
            n += 1
            claims.append({"claim_id": f"C{n:03d}", "pid": p["pid"],
                           "sentence": sent, "level": level,
                           "level_name": LEVEL_NAMES[level],
                           "causality": causality, "causal_markers": cmarkers,
                           "markers": markers,
                           "negated": has_negation(sent)})
    out = {"claims": claims,
           "stats": {"n_claims": len(claims),
                     "by_level": {LEVEL_NAMES[l]: sum(1 for c in claims if c["level"] == l)
                                  for l in (0, 1, 2, 3)},
                     "by_causality": {k: sum(1 for c in claims if c["causality"] == k)
                                      for k in ("因果", "相关", "无")}}}
    op = os.path.join(args.work, "source_claims.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[claim:extract] 论断句={len(claims)} "
          f"分级={out['stats']['by_level']} 因果性={out['stats']['by_causality']}")
    return 0


def cmd_check(args):
    work = args.work
    claims_doc = load(os.path.join(work, "source_claims.json"))
    if claims_doc is None:
        print("[claim:check] source_claims.json 不存在：请先运行 "
              "claim_engine.py extract --source work/source.json", file=sys.stderr)
        return 1
    if not os.path.exists(args.rewrite):
        print(f"[claim:check] 改写稿不存在: {args.rewrite}", file=sys.stderr)
        return 1
    claims = claims_doc.get("claims", [])
    align = load(os.path.join(work, "alignment.json"), {}) or {}
    with open(args.rewrite, encoding="utf-8") as f:
        rtext = f.read()

    # 改写句清单（带 rpid）
    rsents = []  # {rpid, sent, grams, level, markers, causality, negated}
    for i, para in enumerate(split_paragraphs(rtext), 1):
        rpid = f"R{i:03d}"
        for s in split_sentences(para):
            level, markers = find_strength(s)
            causality, cm = detect_causality(s)
            rsents.append({"rpid": rpid, "sent": s, "grams": ngrams(s),
                           "level": level, "markers": markers,
                           "causality": causality, "causal_markers": cm,
                           "negated": has_negation(s)})

    # alignment: source_pid → [rpid 按 sim 降序]
    pid2rpid = {}
    for l in align.get("links", []):
        pid2rpid.setdefault(l["source_pid"], []).append((l["sim"], l["rpid"]))
    for k in pid2rpid:
        pid2rpid[k] = [rpid for _sim, rpid in sorted(pid2rpid[k], key=lambda x: -x[0])]

    issues = []
    verdicts = []

    def add_issue(severity, itype, claim, r, detail, suggestion):
        issues.append({
            "severity": severity, "type": itype,
            "claim_id": claim.get("claim_id"), "pid": claim.get("pid"),
            "rpid": (r or {}).get("rpid"),
            "source_sentence": (claim.get("sentence") or "")[:120],
            "rewrite_sentence": ((r or {}).get("sent") or "")[:120],
            "source_level": (LEVEL_NAMES[claim["level"]] if claim.get("level") is not None else None),
            "rewrite_level": (LEVEL_NAMES[r["level"]] if r and r.get("level") is not None
                              else ("L1 断言(无强度标记)" if r else None)),
            "detail": detail, "suggestion": suggestion})

    # 正向：逐条源文论断 → 改写句
    for c in claims:
        sg = ngrams(c["sentence"])
        cand = [r for r in rsents if r["rpid"] in pid2rpid.get(c["pid"], [])]
        pool = cand + [r for r in rsents if r not in cand]  # 对齐段落优先，全局兜底
        best, best_sim = None, 0.0
        for r in pool:
            sim = dice(sg, r["grams"])
            if sim > best_sim:
                best, best_sim = r, sim
        if best is None or best_sim < MATCH_TH:
            verdicts.append({"claim_id": c["claim_id"], "pid": c["pid"], "verdict": "missing",
                             "sim": round(best_sim, 3)})
            add_issue("warn", "missing", c, None,
                      f"源文论断（{c['level_name']}）在改写稿中找不到对应句（最佳相似度 {best_sim:.2f}）",
                      "若为关键论断请补回，且措辞强度保持源文同级；若为有意删除请在 change_log 写明理由")
            continue

        r = best
        r_level = r["level"] if r["level"] is not None else 1  # 无强度标记按 L1 断言处理
        s_level = c["level"]
        c_issues = []

        # 1) 否定翻转
        if r["negated"] != c["negated"]:
            c_issues.append(("negation_flip", "critical",
                             f"否定极性翻转：源文{'含' if c['negated'] else '不含'}否定，"
                             f"改写句{'含' if r['negated'] else '不含'}否定",
                             "恢复源文极性：逐字核对「不/未/无/未能」等否定词是否与源文一致"))
        # 2) L0 绝对化新增
        s_set = set(c["markers"])
        new_l0 = [m for m in r["markers"]
                  if m in L0_STRONG_ZH + L0_WEAK_ZH and m not in s_set]
        if new_l0:
            c_issues.append(("absolute_upgrade", "critical",
                             f"改写稿新增绝对化措辞：{'、'.join(new_l0)}（源文对应句无同等措辞）",
                             f"删除绝对化措辞，回退到源文同级 {LEVEL_FALLBACK.get(s_level, '')}"))
        # 3) 强度升格（数值越小越强）
        if r_level < s_level:
            c_issues.append(("upgraded", "critical",
                             f"强度升格：源文 {LEVEL_NAMES[s_level]} → 改写稿 {LEVEL_NAMES[r_level]}",
                             f"把强措辞回退到源文同级，如 {LEVEL_FALLBACK[s_level]}"))
        # 4) 相关→因果
        if c["causality"] == "相关" and r["causality"] == "因果":
            c_issues.append(("causality_upgrade", "critical",
                             f"相关被写成因果：源文「{'、'.join(c['causal_markers'])}」→ "
                             f"改写稿「{'、'.join(r['causal_markers'])}」",
                             "恢复相关性措辞（相关/伴随/关联），不得使用导致/促使/取决于/因而"))
        elif c["causality"] == "无" and r["causality"] == "因果":
            c_issues.append(("causality_added", "warn",
                             f"源文无因果表述，改写稿新增因果标记「{'、'.join(r['causal_markers'])}」",
                             "删除因果措辞或回溯源文依据"))
        # 5) 降格（允许但提示）
        if r_level > s_level:
            c_issues.append(("downgraded", "info",
                             f"强度降格：源文 {LEVEL_NAMES[s_level]} → 改写稿 {LEVEL_NAMES[r_level]}（更保守，允许）",
                             "若降格导致关键结论失真，可恢复源文同级措辞"))

        if c_issues:
            worst = "kept"
            for itype, sev, _d, _s in c_issues:
                if sev == "critical":
                    worst = itype
                    break
                if itype == "downgraded" and worst == "kept":
                    worst = "downgraded"
            for itype, sev, d, s in c_issues:
                add_issue(sev, itype, c, r, d, s)
            verdicts.append({"claim_id": c["claim_id"], "pid": c["pid"], "rpid": r["rpid"],
                             "verdict": worst, "sim": round(best_sim, 3)})
        else:
            verdicts.append({"claim_id": c["claim_id"], "pid": c["pid"], "rpid": r["rpid"],
                             "verdict": "kept", "sim": round(best_sim, 3)})

    # 反向：改写稿含结论标记的句子若无源文对应 → new_claim
    claim_grams = [(c, ngrams(c["sentence"])) for c in claims]
    for r in rsents:
        if r["level"] is None and not any(m in L0_WEAK_ZH for m in r["markers"]):
            continue  # 无结论标记
        best_sim = max((dice(r["grams"], cg) for _c, cg in claim_grams), default=0.0)
        if best_sim < MATCH_TH:
            add_issue("critical", "new_claim",
                      {"claim_id": None, "pid": None, "sentence": "", "level": None, "markers": []},
                      r,
                      f"改写稿论断句在源文中无对应论断（最佳相似度 {best_sim:.2f}），疑似源外新结论",
                      "删除该句，或回溯源文找到依据并以同级措辞改写；源文没有结论不得新造")
            verdicts.append({"claim_id": None, "rpid": r["rpid"], "verdict": "new_claim",
                             "sim": round(best_sim, 3)})

    n_by = {}
    for v in verdicts:
        n_by[v["verdict"]] = n_by.get(v["verdict"], 0) + 1
    n_critical = sum(1 for i in issues if i["severity"] == "critical")
    n_warn = sum(1 for i in issues if i["severity"] == "warn")
    verdict = "PASS" if n_critical == 0 else "FAIL"
    stats = {"n_claims": len(claims), "verdicts": n_by,
             "n_critical": n_critical, "n_warn": n_warn,
             "n_info": sum(1 for i in issues if i["severity"] == "info")}
    report = {"verdict": verdict, "stats": stats, "issues": issues,
              "claim_verdicts": verdicts,
              "alignment_stats": (align.get("stats") if align else None)}
    with open(os.path.join(work, "claim_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(os.path.join(work, "claim_verdicts.jsonl"), "w", encoding="utf-8") as f:
        for v in verdicts:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")

    lines = ["# 论断强度校准报告", "",
             f"- 判定：**{verdict}**　源文论断 {len(claims)} 条，"
             f"critical {n_critical} / warn {n_warn} / 提示 {stats['n_info']}",
             f"- 逐条判定："
             + "、".join(f"{k} {n_by[k]}" for k in
                         ("kept", "downgraded", "upgraded", "negation_flip", "missing", "new_claim")
                         if k in n_by), ""]
    if issues:
        lines += ["## 问题清单", ""]
        for i, it in enumerate(issues, 1):
            loc = it["rpid"] or it["pid"] or "全文"
            lines.append(f"### {i}. [{it['severity']}] {it['type']}（{loc}）")
            if it["source_sentence"]:
                lines.append(f"- 源文（{it['pid']}，{it['source_level']}）：{it['source_sentence']}")
            if it["rewrite_sentence"]:
                lines.append(f"- 改写（{it['rpid']}，{it['rewrite_level']}）：{it['rewrite_sentence']}")
            lines.append(f"- 问题：{it['detail']}")
            lines.append(f"- 建议：{it['suggestion']}")
            lines.append("")
    else:
        lines.append("全部论断强度与源文一致，未发现升格/否定翻转/源外新结论。")
    with open(os.path.join(work, "claim_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[claim:check] verdict={verdict} critical={n_critical} warn={n_warn} "
          f"kept={n_by.get('kept', 0)} upgraded={n_by.get('upgraded', 0)} "
          f"missing={n_by.get('missing', 0)} new_claim={n_by.get('new_claim', 0)}")
    return 0 if verdict == "PASS" else 2


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("extract")
    p1.add_argument("--source", required=True)
    p1.add_argument("--work", default="/app/work")
    p2 = sub.add_parser("check")
    p2.add_argument("--rewrite", required=True)
    p2.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    if args.cmd == "extract":
        return cmd_extract(args)
    return cmd_check(args)


if __name__ == "__main__":
    sys.exit(main())
