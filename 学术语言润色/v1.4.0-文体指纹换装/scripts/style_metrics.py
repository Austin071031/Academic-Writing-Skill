#!/usr/bin/env python3
"""style_metrics.py — 文体指纹度量：润色前后的可计算语域画像对比（v1.4.0 核心）。

用法:
  python3 style_metrics.py profile --segments /app/work/source_segments.json \
      --register 期刊论文 --out /app/work            # 生成目标画像 target_profile.json
  python3 style_metrics.py compare --source /app/work/source_segments.json \
      --polished /app/work/polished_segments.json --out /app/work  # 前后对比报告

度量项（中英文通用）：
  句长分布（均值/长句占比）、限定词密度与档位分布、被动语态估计、连接词频次、
  人称使用、口语词/宣传词命中、术语变体数。
目标画像来自 references/register_profiles.md 的五档预设；未指定文体时按 source 画像+微调。
只度量与报告，不改写。
"""
import argparse, json, os, re, sys
from collections import Counter

SPOKEN_ZH = ["但是", "比如", "做了", "搞", "弄", "挺", "蛮", "非常(?!地)好", "的话", "呢", "啊"]
HYPE = ["国际领先", "世界首创", "重大突破", "首次(?!报道|提出)", "革命性", "颠覆性",
        "厉害", "一流", "顶尖", "完美", "very excellent", "amazing", "remarkable",
        "outstanding", "groundbreaking", "unprecedented", "perfect", "best"]
PERSON = {"zh_first": ["我们", "我(?!国|方)"], "en_first": [r"\bwe\b", r"\bI\b"]}
HEDGE_TIERS = {0: ["证明", "证实", "必然", "肯定", "毫无疑问", "prove", "confirms?",
                   "definitively", "establishes?", "must", "undoubtedly"],
               1: ["表明", "显示", "说明", "揭示", "suggests?", "indicates?", "shows?",
                   "demonstrates?", "reveals?", "supports?", "consistent with"],
               2: ["可能", "或许", "有望", "提示", "初步", "约", "大致", "may", "might",
                   "could", "possibly", "potentially", "likely", "appears?", "seems?",
                   "tends?", "preliminary", "approximately", "roughly", "partially"]}
CONNECTIVES_ZH = ["然而", "因此", "此外", "同时", "另外", "并且", "而且", "从而", "进而",
                  "值得(注意的是|一提)"]
CONNECTIVES_EN = [r"\bhowever\b", r"\btherefore\b", r"\bmoreover\b", r"\bfurthermore\b",
                  r"\bin addition\b", r"\badditionally\b", r"\bmeanwhile\b", r"\bhence\b",
                  r"\bthus\b", r"\bconsequently\b"]
PASSIVE_EN = re.compile(r"\b(?:is|are|was|were|be|been|being)\s+(?:\w+ly\s+)?[a-z]+(?:ed|en)\b", re.I)


def sentences_from(segments_path):
    out = []
    for seg in json.load(open(segments_path, encoding="utf-8")):
        if seg.get("kind") in ("math", "fence"):
            continue
        for s in seg.get("sentences") or [seg.get("text", "")]:
            if s.strip():
                out.append(s)
    return out


def hit_count(patterns, text, flags=re.I):
    return sum(len(re.findall(p, text, flags)) for p in patterns)


def fingerprint(sents):
    text = "\n".join(sents)
    n = max(len(sents), 1)
    lens = [len(s) for s in sents]
    zh = len(re.findall(r"[一-鿿]", text)) >= len(re.findall(r"[A-Za-z]", text))
    long_th = 40 if zh else 30
    tiers = {t: hit_count(lex, text, re.I) for t, lex in HEDGE_TIERS.items()}
    fp = {
        "sentences": n,
        "lang": "zh" if zh else "en",
        "avg_len": round(sum(lens) / n, 1),
        "long_ratio": round(sum(1 for L in lens if L > long_th) / n, 3),
        "hedge_density": round(sum(tiers.values()) / n, 3),
        "hedge_tiers": tiers,
        "passive_ratio": round(len(PASSIVE_EN.findall(text)) / n, 3) if not zh else None,
        "connectives": round((hit_count(CONNECTIVES_ZH, text) if zh
                              else hit_count(CONNECTIVES_EN, text)) / n, 3),
        "person_first": hit_count(PERSON["zh_first" if zh else "en_first"], text, re.I),
        "spoken_hits": hit_count(SPOKEN_ZH, text) if zh else None,
        "hype_hits": hit_count(HYPE, text),
    }
    return fp


# 五档目标画像（references/register_profiles.md 的机读版）
TARGETS = {
    "期刊论文": {"avg_len_zh": (28, 48), "avg_len_en": (18, 28), "long_ratio_max": 0.35,
                 "hedge_density": (0.15, 0.6), "connectives_max": 0.8, "person_first_max": 2,
                 "hype_max": 0, "spoken_max": 0},
    "学位论文": {"avg_len_zh": (25, 50), "avg_len_en": (16, 30), "long_ratio_max": 0.45,
                 "hedge_density": (0.15, 0.7), "connectives_max": 1.0, "person_first_max": 4,
                 "hype_max": 0, "spoken_max": 0},
    "基金申请书": {"avg_len_zh": (25, 45), "avg_len_en": (16, 26), "long_ratio_max": 0.3,
                   "hedge_density": (0.2, 0.8), "connectives_max": 0.7, "person_first_max": 6,
                   "hype_max": 0, "spoken_max": 0},
    "审稿回复": {"avg_len_zh": (22, 42), "avg_len_en": (14, 24), "long_ratio_max": 0.25,
                 "hedge_density": (0.1, 0.5), "connectives_max": 0.7, "person_first_max": 8,
                 "hype_max": 0, "spoken_max": 0},
    "英文摘要": {"avg_len_zh": (25, 45), "avg_len_en": (15, 25), "long_ratio_max": 0.25,
                 "hedge_density": (0.1, 0.5), "connectives_max": 0.6, "person_first_max": 1,
                 "hype_max": 0, "spoken_max": 0},
}


def check_against(fp, tgt):
    issues = []
    lang = fp["lang"]
    lo, hi = tgt[f"avg_len_{lang}"]
    if not lo <= fp["avg_len"] <= hi:
        issues.append(f"平均句长 {fp['avg_len']} 超出 [{lo},{hi}]")
    if fp["long_ratio"] > tgt["long_ratio_max"]:
        issues.append(f"长句占比 {fp['long_ratio']:.0%} 超过 {tgt['long_ratio_max']:.0%}")
    lo, hi = tgt["hedge_density"]
    if not lo <= fp["hedge_density"] <= hi:
        issues.append(f"限定词密度 {fp['hedge_density']} 超出 [{lo},{hi}]")
    if fp["connectives"] > tgt["connectives_max"]:
        issues.append(f"连接词密度 {fp['connectives']} 超过 {tgt['connectives_max']}")
    if fp["person_first"] > tgt["person_first_max"]:
        issues.append(f"第一人称出现 {fp['person_first']} 次，超过 {tgt['person_first_max']}")
    if fp["hype_hits"] > tgt["hype_max"]:
        issues.append(f"宣传/绝对化词命中 {fp['hype_hits']} 处")
    if fp.get("spoken_hits") and fp["spoken_hits"] > tgt["spoken_max"]:
        issues.append(f"口语词命中 {fp['spoken_hits']} 处")
    return issues


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("profile")
    p.add_argument("--segments", required=True)
    p.add_argument("--register", default="期刊论文")
    p.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--source", required=True)
    c.add_argument("--polished", required=True)
    c.add_argument("--out", required=True)
    args = ap.parse_args()

    if args.cmd == "profile":
        src_fp = fingerprint(sentences_from(args.segments))
        tgt = TARGETS.get(args.register, TARGETS["期刊论文"])
        prof = {"register": args.register, "source_fingerprint": src_fp,
                "target": tgt, "register_known": args.register in TARGETS}
        json.dump(prof, open(os.path.join(args.out, "target_profile.json"), "w",
                             encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[style_metrics profile] register={args.register} "
              f"known={args.register in TARGETS} -> target_profile.json")
        return 0

    src_fp = fingerprint(sentences_from(args.source))
    pol_fp = fingerprint(sentences_from(args.polished))
    tp = os.path.join(args.out, "target_profile.json")
    tgt = TARGETS["期刊论文"]
    register = "期刊论文"
    if os.path.exists(tp):
        prof = json.load(open(tp, encoding="utf-8"))
        tgt = prof["target"]
        register = prof["register"]
    issues = check_against(pol_fp, tgt)
    rep = {"register": register, "source": src_fp, "polished": pol_fp,
           "target": tgt, "conformance_issues": issues,
           "conformant": not issues}
    json.dump(rep, open(os.path.join(args.out, "style_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "style_report.md"), "w", encoding="utf-8") as f:
        f.write(f"# 文体指纹对比报告（目标文体：{register}）\n\n")
        f.write("| 指标 | 润色前 | 润色后 | 目标区间 |\n|---|---|---|---|\n")
        lang = pol_fp["lang"]
        rows = [
            ("平均句长", "avg_len", tgt[f"avg_len_{lang}"]),
            ("长句占比", "long_ratio", f"≤{tgt['long_ratio_max']}"),
            ("限定词密度", "hedge_density", tgt["hedge_density"]),
            ("连接词密度", "connectives", f"≤{tgt['connectives_max']}"),
            ("第一人称次数", "person_first", f"≤{tgt['person_first_max']}"),
            ("宣传/绝对化词", "hype_hits", f"≤{tgt['hype_max']}"),
        ]
        if lang == "zh":
            rows.append(("口语词", "spoken_hits", f"≤{tgt['spoken_max']}"))
        else:
            rows.append(("被动语态估计", "passive_ratio", "—"))
        for name, key, band in rows:
            f.write(f"| {name} | {src_fp.get(key)} | {pol_fp.get(key)} | {band} |\n")
        f.write(f"\n档位分布（强/中/弱）：润色前 {src_fp['hedge_tiers']} → 润色后 {pol_fp['hedge_tiers']}\n\n")
        if issues:
            f.write("## 未达标项\n\n")
            for i in issues:
                f.write(f"- {i}\n")
        else:
            f.write("## 全部指标达标 ✓\n")
    print(f"[style_metrics compare] register={register} issues={len(issues)} "
          f"conformant={not issues}")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
