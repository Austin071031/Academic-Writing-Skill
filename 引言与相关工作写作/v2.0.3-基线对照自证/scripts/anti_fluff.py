#!/usr/bin/env python3
"""anti_fluff.py — V1 研究背景立得住：空转铺垫审计 + 背景锚定统计。

用法: python3 anti_fluff.py --work /app/work --out /app/output [--patterns references/anti_fluff_patterns.txt]
读 work/draft_intro.md（引言工作稿）与 evidence_map.json：
  1) 空转铺垫检测：命中 patterns 清单的句子 → 建议改写类别，写入 version_report 与 anti_fluff_audit.md；
  2) 锚定统计：研究背景小节（"研究空白/不足/挑战"标题之前）中含 〔E#〕 锚点的句子占比；
  3) 具体问题信号：背景段须出现"尚未/仍缺乏/有待/原因不明/争议/瓶颈"等指向未解决问题的表述。
verdict ∈ {pass, warn, fail}，仅作审计结论，不中断流程。
"""
import argparse, json, os, re, sys

DEFAULT_PATTERNS = [
    (r"近年来[^。；]{0,30}(受到|得到|引起)?(广泛|越来越多)?(关注|重视|研究热)", "空转铺垫", "删去流行度叙述，改述具体研究脉络或量化需求"),
    (r"随着[^。；]{2,40}(的)?(快速|飞速)?发展", "套话起始", "以领域具体矛盾或技术约束起笔"),
    (r"(已经成为|俨然成为|逐渐成为)[^。；]{0,25}(研究)?热点", "空转铺垫", "说明该方向要解决的具体问题"),
    (r"具有(重要|重大|深远)的?(理论|现实|应用|科学)?(意义|价值)", "泛泛意义", "改为该问题不解决会导致的具体后果"),
    (r"(不可或缺|不可替代|至关重要|举足轻重)", "泛化强调", "给出依赖关系的具体证据或删去"),
    (r"(如火如荼|方兴未艾|蓬勃开展|迅猛发展)", "修辞堆砌", "删除修辞，保留可核验事实"),
    (r"(引起了学术界|受到学界)(的)?(广泛)?(关注|兴趣)", "空转铺垫", "改为指出仍未解决的具体问题"),
    (r"众所周知", "套话起始", "删除；背景应从领域共识的可核验事实写起"),
]

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def split_sentences(text):
    parts = re.split(r"(?<=[。！？；;.!?])\s*", text)
    return [p.strip() for p in parts if p.strip()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--patterns", default=None)
    args = ap.parse_args()

    patterns = list(DEFAULT_PATTERNS)
    if args.patterns and os.path.exists(args.patterns):
        with open(args.patterns, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    patterns.append((parts[0], parts[1], parts[2] if len(parts) > 2 else "改写为空转句"))

    intro_path = os.path.join(args.work, "draft_intro.md")
    draft = ""
    if os.path.exists(intro_path):
        with open(intro_path, encoding="utf-8") as f:
            draft = f.read()
    else:
        print("[anti_fluff][issue] draft_intro.md 缺失", file=sys.stderr)

    ev = load_json(os.path.join(args.work, "evidence_map.json"), []) or []
    eids = {e.get("eid") for e in ev if isinstance(e, dict)}

    # 背景小节 = 第一个"空白/不足/挑战/缺口"标题之前的部分
    cut = re.search(r"^#{2,3}\s*.*(空白|不足|挑战|缺口|局限)", draft, re.M)
    bg = draft[:cut.start()] if cut else draft

    sents = split_sentences(re.sub(r"^#+.*$", "", bg, flags=re.M))
    total = len([s for s in sents if len(s) >= 10])
    anchored = 0
    fluff_hits = []
    for s in sents:
        if len(s) < 10:
            continue
        anchors = re.findall(r"〔(E\d+)〕", s)
        resolved = [a for a in anchors if a in eids]
        if anchors and len(resolved) == len(anchors):
            anchored += 1
        for pat, cat, sug in patterns:
            if re.search(pat, s):
                fluff_hits.append({"sentence": s[:120], "category": cat,
                                   "pattern": pat, "suggestion": sug})
                break

    problem_signals = len(re.findall(r"尚未|仍(然)?(缺乏|存在|未)|有待|原因不明|争议|瓶颈|缺口|无法(有效)?(解决|兼顾)", bg))
    signal_ok = problem_signals >= 1
    anchor_ratio = anchored / total if total else 0.0

    if fluff_hits or not signal_ok or anchor_ratio < 0.5:
        verdict = "fail" if (not signal_ok and anchor_ratio < 0.3) else "warn"
    else:
        verdict = "pass"

    report = {"version": "v1.0.0-研究背景立得住",
              "fluff_hits": fluff_hits,
              "grounding": {"background_sentences": total, "anchored_sentences": anchored,
                            "anchor_ratio": round(anchor_ratio, 3),
                            "problem_signals": problem_signals,
                            "problem_signal_ok": signal_ok},
              "verdict": verdict}
    os.makedirs(args.work, exist_ok=True)
    with open(os.path.join(args.work, "version_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    lines = ["# 研究背景空转铺垫审计", "",
             f"- 背景句总数：{total}；带可解析证据锚点句数：{anchored}（比例 {anchor_ratio:.0%}）",
             f"- 未解决问题信号数：{problem_signals}（要求 ≥1）：{'满足' if signal_ok else '缺失'}",
             f"- 审计结论：**{verdict}**", ""]
    if fluff_hits:
        lines.append("## 命中句与改写建议")
        lines.append("")
        for i, h in enumerate(fluff_hits, 1):
            lines.append(f"{i}. 【{h['category']}】{h['sentence']}")
            lines.append(f"   - 建议：{h['suggestion']}")
        lines.append("")
    else:
        lines.append("未检出空转铺垫句式。")
        lines.append("")
    if not signal_ok:
        lines.append("> ⚠ 背景段缺少指向具体未解决问题的表述，请补入由材料可支撑的问题句。")
    if anchor_ratio < 0.5 and total > 0:
        lines.append("> ⚠ 背景句证据锚定比例低于 50%，请为具体事实句补 〔E#〕 锚点或在 "
                     "evidence_map.json 中登记判断类条目（type=judgment）。")

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "anti_fluff_audit.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[anti_fluff] 句={total} 锚定={anchored} 空转={len(fluff_hits)} 问题信号={problem_signals} verdict={verdict}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
