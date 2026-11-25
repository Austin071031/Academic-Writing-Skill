#!/usr/bin/env python3
"""self_compare.py — 基线对照自证：把"无 Skill 风格的基线段"与 Skill 成稿做同口径量化对照。

用法: python3 self_compare.py --work /app/work --out /app/output [--patterns references/anti_fluff_patterns.txt]
输入: work/baseline_intro.md（Agent 按 SKILL.md 3.7 写的基线段，150–250 字，无锚点、无引用编号要求）、
      work/draft_intro.md + work/draft_rl.md（Skill 工作稿）、work/evidence_map.json、
      work/claim_bindings.jsonl（可有可无数）。
输出: output/comparison_report.md + work/self_compare.json。
指标（同一套引擎规则在两边各算一遍）: 空转铺垫命中数、证据锚定句比例、未解决问题信号数、
论断-引用绑定覆盖率（Skill 侧）、篇幅。
"""
import argparse, json, os, re, sys

FLUFF = [
    r"近年来[^。；]{0,30}(受到|得到|引起)?(广泛|越来越多)?(关注|重视|研究热)",
    r"随着[^。；]{2,40}(的)?(快速|飞速)?发展",
    r"(已经成为|俨然成为|逐渐成为)[^。；]{0,25}(研究)?热点",
    r"具有(重要|重大|深远)的?(理论|现实|应用|科学)?(意义|价值)",
    r"(不可或缺|不可替代|至关重要|举足轻重)",
    r"(如火如荼|方兴未艾|蓬勃开展|迅猛发展)",
    r"众所周知",
]
PROBLEM = re.compile(r"尚未|仍(然)?(缺乏|存在|未)|有待|原因不明|争议|瓶颈|缺口|无法(有效)?(解决|兼顾)")

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def read(path):
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()

def sentences(text):
    parts = re.split(r"(?<=[。！？；;.!?])\s*", re.sub(r"^#+.*$", "", text, flags=re.M))
    return [p.strip() for p in parts if len(p.strip()) >= 10]

def analyze(text, patterns):
    sents = sentences(text)
    fluff = 0
    for s in sents:
        if any(re.search(p, s) for p in patterns):
            fluff += 1
    anchored = sum(1 for s in sents if re.search(r"〔E\d+〕", s))
    return {"sentences": len(sents), "fluff_hits": fluff,
            "anchored": anchored, "anchor_ratio": round(anchored / len(sents), 3) if sents else 0.0,
            "problem_signals": len(PROBLEM.findall(text)),
            "chars": len(re.sub(r"\s", "", text))}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--patterns", default=None)
    args = ap.parse_args()

    patterns = list(FLUFF)
    if args.patterns and os.path.exists(args.patterns):
        with open(args.patterns, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line.split("\t")[0])

    baseline = read(os.path.join(args.work, "baseline_intro.md"))
    skilled = (read(os.path.join(args.work, "draft_intro.md")) + "\n" +
               read(os.path.join(args.work, "draft_rl.md"))).strip()
    ev = load_json(os.path.join(args.work, "evidence_map.json"), []) or []
    n_bindings = 0
    bp = os.path.join(args.work, "claim_bindings.jsonl")
    if os.path.exists(bp):
        with open(bp, encoding="utf-8") as f:
            n_bindings = sum(1 for ln in f if ln.strip() and not ln.strip().startswith("#"))

    issues = []
    if not baseline.strip():
        issues.append("baseline_intro.md 缺失：无法生成对照，跳过本报告")
    if not skilled:
        issues.append("工作稿缺失")

    base_stats = analyze(baseline, patterns) if baseline.strip() else None
    skill_stats = analyze(skilled, patterns) if skilled else None

    result = {"version": "v2.0.3-基线对照自证",
              "baseline": base_stats, "skilled": skill_stats,
              "evidence_entries": len(ev), "claim_bindings": n_bindings,
              "issues": issues}
    os.makedirs(args.work, exist_ok=True)
    with open(os.path.join(args.work, "self_compare.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    lines = ['# Skill 增益自证对照（同口径量化）', '',
             '> 基线段由 Agent 按「无方法指引的常见风格」撰写（baseline_intro.md），成稿为本 Skill 产出。',
             '> 同一套确定性规则在两侧各算一遍，供评审验证使用增益。',
             '']
    if base_stats and skill_stats:
        lines += ["| 指标 | 基线段（无 Skill 风格） | Skill 成稿 |",
                  "|---|---|---|",
                  f"| 空转铺垫命中（句） | {base_stats['fluff_hits']} | {skill_stats['fluff_hits']} |",
                  f"| 证据锚定句数/总句数 | {base_stats['anchored']}/{base_stats['sentences']}（{base_stats['anchor_ratio']:.0%}） | {skill_stats['anchored']}/{skill_stats['sentences']}（{skill_stats['anchor_ratio']:.0%}） |",
                  f"| 未解决问题信号 | {base_stats['problem_signals']} | {skill_stats['problem_signals']} |",
                  f"| 登记证据条目（evidence_map） | 0 | {len(ev)} |",
                  f"| 论断-引用绑定 | 0 | {n_bindings} |",
                  f"| 篇幅（字） | {base_stats['chars']} | {skill_stats['chars']} |",
                  ""]
        gain = []
        if skill_stats["fluff_hits"] < base_stats["fluff_hits"]:
            gain.append(f"空转铺垫 {base_stats['fluff_hits']}→{skill_stats['fluff_hits']}")
        if skill_stats["anchor_ratio"] > base_stats["anchor_ratio"]:
            gain.append(f"锚定比例 {base_stats['anchor_ratio']:.0%}→{skill_stats['anchor_ratio']:.0%}")
        if skill_stats["problem_signals"] > base_stats["problem_signals"]:
            gain.append("未解决问题更明确")
        lines.append("**改善摘要**：" + ("；".join(gain) if gain else "本案例差异不显著，如实记录。"))
        lines.append("")
    else:
        lines.append("（对照材料不全，未生成对照表；见 issues）")
        lines.append("")
        for i in issues:
            lines.append(f"- {i}")
        lines.append("")

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "comparison_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[self_compare] 基线={'有' if base_stats else '无'} 成稿={'有' if skill_stats else '无'} issues={len(issues)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
