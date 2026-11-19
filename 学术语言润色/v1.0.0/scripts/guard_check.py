#!/usr/bin/env python3
"""guard_check.py — 限定强度与事实守恒检查：原文 vs 改文逐句对照（只报告，不改写）。

用法: python3 guard_check.py --source /app/work/source_segments.json \
          --chunks /app/work/polish_chunks --out /app/work

对 change log（polish_chunks/*.jsonl）中每个 decision=modify 的句子，抽取五类特征并对照:
  numbers   数值与单位（critical：增/删/改数值或单位）
  citations 引用编号与 \\cite 键（critical）
  pointers  图表/公式/章节指向（critical）
  hedging   限定强度等级（critical：跨档升降；warning：同档提示）
  logic     否定词与因果-相关表述（critical）
输出 guard_report.json / guard_report.md；exit 1 表示存在 critical 待处置。
"""
import argparse, glob, json, os, re, sys
from collections import Counter

UNITS = (r"%|°C|℃|°|K|Pa|kPa|MPa|GPa|atm|bar|mbar|Torr|nm|μm|µm|um|mm|cm|dm|m|km|"
         r"ng|μg|µg|ug|mg|g|kg|t|mL|ml|μL|µL|uL|L|mol|mmol|μmol|s|ms|μs|ns|min|h|d|"
         r"Hz|kHz|MHz|GHz|THz|eV|keV|MeV|GeV|V|mV|kV|MV|W|mW|kW|J|kJ|kcal|N|kN|rpm|"
         r"dB|px|dpi|ppb|ppm|Ω|kΩ|MΩ|S|F|pF|nF|Bq|Gy|Sv|cal|°|′|″")
RE_NUMBER = re.compile(rf"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?(?:\\?\s*(?:{UNITS}))?")
RE_CITE_NUM = re.compile(r"\[[0-9]+(?:\s*[-–,，]\s*[0-9]+)*\]")
RE_CITE_AY = re.compile(r"\(([A-Z][A-Za-z\-]+(?:\s+et\s+al\.?)?(?:\s+and\s+[A-Z][A-Za-z\-]+)?,?\s+(?:19|20)\d{2}[a-z]?(?:;[^)]+)?)\)")
RE_CITE_KEY = re.compile(r"\\cite[tp]?\*?(?:\[[^\]]*\])?\{[^}]*\}")
RE_POINTER = re.compile(r"(?:图|表|插图|算法|式|公式|方程|Figure|Fig\.?|Figs\.?|Table|Tab\.?|"
                        r"Algorithm|Eq\.?|Eqs\.?|Equation|Section|Sec\.?|Chapter)\s*"
                        r"(?:[0-9]+(?:\.[0-9]+)?(?:[-–][0-9]+)?)")

# 限定强度三档
HEDGE_STRONG = ["证明", "证实", "确证", "必然", "肯定", "毫无疑问", "决定性", "首次证明",
                "prove", "proves", "proved", "proven", "confirm", "confirms", "definitively",
                "establish", "establishes", "always", "must", "undoubtedly"]
HEDGE_MID = ["表明", "显示", "说明", "揭示", "反映出", "证实为", "显著", "一致表明",
             "suggest", "suggests", "suggested", "indicate", "indicates", "indicated",
             "show", "shows", "showed", "shown", "demonstrate", "demonstrates", "demonstrated",
             "reveal", "reveals", "revealed", "support", "supports", "supported",
             "consistent with", "in line with", "confirmatory"]
HEDGE_WEAK = ["可能", "或许", "有望", "提示", "倾向于", "初步", "约", "大致", "一定程度上",
              "不完全", "疑似", "或将", "may", "might", "could", "possibly", "potentially",
              "likely", "appears", "appear", "seems", "seem", "tend", "tends", "suggestive",
              "preliminary", "approximately", "roughly", "partially", "in part"]
RE_NEG_ZH = re.compile(r"不|未|无|非|没有|并未|难以|勿|莫|否")
RE_NEG_EN = re.compile(r"\b(not|no|never|neither|nor|without|fails?|failed|absence|absent|lack|lacks|lacking|unable|cannot|can't|don't|doesn't|didn't|won't)\b", re.I)
RE_CAUSAL_ZH = re.compile(r"导致|引起|决定|致使|归因于|造成|使得")
RE_CORR_ZH = re.compile(r"相关|关联|伴随|对应|一致|吻合")
RE_CAUSAL_EN = re.compile(r"\b(cause[sd]?|causing|lead(?:s|ing)? to|led to|result(?:s|ed|ing)? in|due to|owing to|attribut\w+ to|therefore|thus|hence|giving rise to)\b", re.I)
RE_CORR_EN = re.compile(r"\b(correlat\w+|associat\w+|accompan\w+|coincid\w+|consistent with|in line with)\b", re.I)


def tier_of(tok):
    t = tok.lower()
    for i, lex in enumerate((HEDGE_STRONG, HEDGE_MID, HEDGE_WEAK)):
        if t in [x.lower() for x in lex]:
            return i  # 0 strong, 1 mid, 2 weak
    return None


def hedge_tokens(text):
    """返回 {档位: 命中词列表}。0 强 / 1 中 / 2 弱。中文词按子串匹配，英文词按词边界匹配。"""
    low = text.lower()
    by_tier = {0: [], 1: [], 2: []}
    for i, lex in enumerate((HEDGE_STRONG, HEDGE_MID, HEDGE_WEAK)):
        for w in lex:
            if re.search(r"[一-鿿]", w):
                if w in low:
                    by_tier[i].append(w)
            elif re.search(r"(?<![A-Za-z])" + re.escape(w.lower()) + r"(?![A-Za-z])", low):
                by_tier[i].append(w)
    return by_tier


def features(text):
    nums = sorted(RE_NUMBER.findall(text))
    cites = sorted(RE_CITE_NUM.findall(text)) + sorted(RE_CITE_AY.findall(text)) + sorted(RE_CITE_KEY.findall(text))
    ptrs = sorted(RE_POINTER.findall(text))
    by_tier = hedge_tokens(text)
    neg = len(RE_NEG_ZH.findall(text)) + len(RE_NEG_EN.findall(text))
    causal = bool(RE_CAUSAL_ZH.search(text) or RE_CAUSAL_EN.search(text))
    corr = bool(RE_CORR_ZH.search(text) or RE_CORR_EN.search(text))
    return {"numbers": nums, "citations": cites, "pointers": ptrs,
            "hedge_by_tier": by_tier, "hedge_tier": (min((t for t, v in by_tier.items() if v),
                                                         default=None)),
            "negations": neg, "causal": causal, "correlational": corr}


def diff_counter(a, b):
    """返回 a->b 的增减列表。"""
    ca, cb = Counter(a), Counter(b)
    removed = sorted((ca - cb).elements())
    added = sorted((cb - ca).elements())
    return removed, added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--chunks", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    source = {seg["id"]: seg for seg in json.load(open(args.source, encoding="utf-8"))}
    src_sent = {}
    for seg in source.values():
        if seg.get("kind") in ("heading", "math", "fence"):
            continue  # 标题/公式/代码块不要求逐句记录（记录了也会审校）
        sents = seg.get("sentences") or []
        for i, s in enumerate(sents, 1):
            sid = f"{seg['id']}-S{i}" if len(sents) > 1 else seg["id"]
            src_sent[sid] = s

    entries, seen = [], set()
    for p in sorted(glob.glob(os.path.join(args.chunks, "*.jsonl"))):
        with open(p, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    entries.append({"_parse_error": f"{os.path.basename(p)}:{ln}"})
                    continue
                e["_file"] = os.path.basename(p)
                entries.append(e)
                seen.add(e.get("id"))

    flags = []
    n_modify = n_keep = 0
    for e in entries:
        if "_parse_error" in e:
            flags.append({"level": "critical", "kind": "parse_error", "id": e["_parse_error"],
                          "issue": "change log 行不是合法 JSON，无法审校，需修复"})
            continue
        if e.get("decision") not in ("modify", "keep"):
            flags.append({"level": "warning", "kind": "schema", "id": e.get("id"),
                          "issue": f"decision 字段异常: {e.get('decision')!r}"})
        if e.get("decision") == "modify":
            n_modify += 1
        else:
            n_keep += 1
        sid = e.get("id")
        orig = e.get("original", "")
        rev = e.get("polished", "")
        if not rev.strip():
            flags.append({"level": "critical", "kind": "empty", "id": sid,
                          "issue": "改文为空，句子丢失"})
            continue
        # 与源句对齐核对（允许 Agent 记录的 original 与源句有空白差异）
        src = src_sent.get(sid)
        if src is not None and src.strip() and src.strip() != orig.strip():
            norm = lambda s: re.sub(r"\s+", "", s)
            if norm(src) != norm(orig):
                flags.append({"level": "warning", "kind": "alignment", "id": sid,
                              "issue": "log 中的 original 与源文本不一致，ID 对齐可能错位"})
        fo, fr = features(orig), features(rev)
        r, a = diff_counter(fo["numbers"], fr["numbers"])
        if r or a:
            flags.append({"level": "critical", "kind": "numbers", "id": sid,
                          "issue": f"数值/单位变动: 删除{r} 新增{a}",
                          "original": orig[:120], "polished": rev[:120]})
        r, a = diff_counter(fo["citations"], fr["citations"])
        if r or a:
            flags.append({"level": "critical", "kind": "citations", "id": sid,
                          "issue": f"引用变动: 删除{r} 新增{a}",
                          "original": orig[:120], "polished": rev[:120]})
        r, a = diff_counter(fo["pointers"], fr["pointers"])
        if r or a:
            flags.append({"level": "critical", "kind": "pointers", "id": sid,
                          "issue": f"图表/公式指向变动: 删除{r} 新增{a}",
                          "original": orig[:120], "polished": rev[:120]})
        # 限定强度：按档位核对增删。同档替换（may→might）放行；某档被抽空或新增更强档即 critical。
        bo, br = fo["hedge_by_tier"], fr["hedge_by_tier"]
        orig_strongest = min((t for t, v in bo.items() if v), default=3)
        for t in (0, 1, 2):
            rem, add = diff_counter(bo[t], br[t])
            if rem and not add:
                flags.append({"level": "critical", "kind": "hedging", "id": sid,
                              "issue": f"限定强度变化（档位{t}限定词被删除且无同档替换）: -{rem}",
                              "original": orig[:120], "polished": rev[:120]})
            elif add and not rem and t < orig_strongest:
                flags.append({"level": "critical", "kind": "hedging", "id": sid,
                              "issue": f"限定强度变化（新增强于原文表述的档位{t}词）: +{add}",
                              "original": orig[:120], "polished": rev[:120]})
        if fo["negations"] != fr["negations"]:
            flags.append({"level": "critical", "kind": "negation", "id": sid,
                          "issue": f"否定标记数变化: {fo['negations']}->{fr['negations']}（否定范围可能被改动）",
                          "original": orig[:120], "polished": rev[:120]})
        if fo["causal"] != fr["causal"] or fo["correlational"] != fr["correlational"]:
            flags.append({"level": "critical", "kind": "causality", "id": sid,
                          "issue": f"因果/相关表述性质变化: 原(因果={fo['causal']},相关={fo['correlational']}) "
                                    f"新(因果={fr['causal']},相关={fr['correlational']})",
                          "original": orig[:120], "polished": rev[:120]})

    coverage = sorted(set(src_sent) - seen)
    cov_pct = (len(src_sent) - len(coverage)) / max(len(src_sent), 1)
    rep = {
        "source_sentences": len(src_sent), "logged": len(seen),
        "coverage_ratio": round(cov_pct, 4), "unlogged_ids": coverage[:200],
        "modify": n_modify, "keep": n_keep,
        "flags": flags,
        "critical": sum(1 for x in flags if x["level"] == "critical"),
        "warning": sum(1 for x in flags if x["level"] == "warning"),
    }
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "guard_report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.out, "guard_report.md"), "w", encoding="utf-8") as f:
        f.write("# 事实与限定强度守恒检查（guard_check.py，机械对照）\n\n")
        f.write(f"源句 {rep['source_sentences']}，已记录 {rep['logged']}，覆盖率 "
                f"{rep['coverage_ratio']:.1%}（modify {n_modify} / keep {n_keep}）。\n")
        if coverage:
            f.write(f"\n未记录 ID（前 200）: {', '.join(coverage[:200])}\n")
        f.write(f"\ncritical {rep['critical']} 条，warning {rep['warning']} 条。\n\n")
        for x in flags:
            f.write(f"- **[{x['level']}/{x['kind']}]** `{x.get('id')}` {x['issue']}\n")
        if not flags:
            f.write("- 未发现数值、引用、指向、限定强度、否定范围或因果性质变动。\n")
    print(f"[guard_check] sentences={rep['source_sentences']} logged={rep['logged']} "
          f"coverage={rep['coverage_ratio']:.1%} critical={rep['critical']} warning={rep['warning']}")
    return 1 if rep["critical"] else 0


if __name__ == "__main__":
    sys.exit(main())
