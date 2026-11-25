#!/usr/bin/env python3
"""segment_builder.py — 由 structure.json 构建句段级翻译单元 work/segments.json。

每个句段带稳定 ID（与原文结构模型一致：SEC1-h / P001-s2 / P007），
标注 kind（heading/body/abstract/caption/footnote/formula/reference/list），
并预抽取受保护片段（数字+单位、引用标记、公式、URL/DOI、缩写定义），
供翻译时保持原样、译后机检逐项核对。

同时产出 work/source_for_translation.md：供 Agent 分批翻译的紧凑源文清单
（只列需要翻译的句段，含段 ID 与保护提示），避免 Agent 回读全文浪费预算。

用法: python3 segment_builder.py --work /app/work
只依赖标准库。
"""
import argparse, json, os, re, sys

RE_CAPTION = re.compile(
    r"^\s*(图\s*\d|表\s*\d|式\s*\(|Figure\s*\d|Fig\.\s*\d|TABLE\s*\d|Table\s*\d|"
    r"Scheme\s*\d|Equation\s*\(|Eq\.\s*\()", re.I)
RE_FOOTNOTE = re.compile(r"^\s*(\[\^\d+\]:|注[:：]|Note[:：]|\*\s|†|‡)")
RE_MD_LIST = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
RE_FORMULA_LINE = re.compile(
    r"(\\begin\{(equation|align|eqnarray)|\$\$|\\\[|\\frac|\\sum|\\int|\\alpha|\\beta)")
RE_URL_DOI = re.compile(r"(https?://\S+|doi\s*[:：]\s*\S+|10\.\d{4,9}/\S+)", re.I)
RE_REF_HEAD = re.compile(r"(参考文献|引用文献|references|bibliography)", re.I)

# 数字（含千分位/小数/科学计数/范围）+ 可选单位/百分号
RE_NUMBER = re.compile(
    r"(?<![A-Za-z0-9.])(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)"
    r"(\s*[×xX]\s*10\^?[-+]?\d+|"
    r"\s*(?:%|‰|°C|K|nm|µm|μm|mm|cm|dm|km|mA|cm-2|cm2|cm²|mA\s*/\s*cm[²2]|"
    r"V|mV|kV|W|kW|kWh|Wh|kg|mg|µg|μg|g|mol|mmol|mM|M|ppm|ppb|"
    r"Hz|kHz|MHz|GHz|Pa|kPa|MPa|GPa|bar|atm|Ω|ohm|"
    r"h|hr|hrs|min|s|ms|ns|µs|μs|days?|weeks?|months?|years?|"
    r"million|billion|trillion|thousand|万|亿|千|百|"
    r"eV|keV|MeV|J|kJ|mJ|rpm|wt%|at%|vol%|mol%))?", re.I)
# 引用标记：数字型 [1] [1-3] [1,2] 与 著者-年型 (Zhang et al., 2023) / Zhang et al. (2023)
RE_CITE_NUM = re.compile(r"\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]")
RE_CITE_AY_PAREN = re.compile(
    r"\((?:[A-Z][A-Za-zÀ-ÿ'’-]+(?:\s+(?:and|&|与)\s+[A-Z][A-Za-zÀ-ÿ'’-]+)?"
    r"(?:\s+et\s+al\.)?,?\s+\d{4}[a-z]?(?:\s*;\s*[^)]*\d{4}[a-z]?)*)\)")
RE_CITE_AY_NARR = re.compile(
    r"[A-Z][A-Za-zÀ-ÿ'’-]+(?:\s+et\s+al\.)?\s*\(\d{4}[a-z]?\)")
# 缩写定义：full name (ABBR)
RE_ACRONYM_DEF = re.compile(r"\(([A-Z][A-Za-z0-9]{1,7})\)")
RE_INLINE_MATH = re.compile(r"(\$[^$]+\$|\\\([^)]+\\\)|\\\[[^\]]+\\\])")

MATH_CHARS = set("=+-×÷∑∫√∂∇αβγδεζηθικλμνξπρστυφχψωΑΒΓΔΘΛΞΠΣΦΨΩ()[]{}^_/\\<>|≈≤≥≠±∞")

def classify_para(text, in_refs):
    s = text.strip()
    if in_refs:
        return "reference"
    if RE_FORMULA_LINE.search(s):
        return "formula"
    if RE_CAPTION.search(s):
        return "caption"
    if RE_FOOTNOTE.search(s):
        return "footnote"
    if RE_MD_LIST.search(s):
        return "list"
    mathy = sum(1 for c in s if c in MATH_CHARS)
    if len(s) < 200 and len(s) > 3 and mathy / max(len(s), 1) > 0.35:
        return "formula"
    return "body"

def protected_spans(text):
    """返回 [{kind, text, span}]，kind ∈ number/citation/formula/acronym_def/url。"""
    spans = []
    occupied = []

    def add(kind, m, text_override=None):
        a, b = m.span()
        for (x, y) in occupied:
            if a < y and x < b:
                return
        occupied.append((a, b))
        spans.append({"kind": kind, "text": text_override or m.group(0), "span": [a, b]})

    for m in RE_URL_DOI.finditer(text):
        add("url", m)
    for m in RE_INLINE_MATH.finditer(text):
        add("formula", m)
    for m in RE_CITE_NUM.finditer(text):
        add("citation", m)
    for m in RE_CITE_AY_PAREN.finditer(text):
        add("citation", m)
    for m in RE_CITE_AY_NARR.finditer(text):
        add("citation", m)
    for m in RE_ACRONYM_DEF.finditer(text):
        add("acronym_def", m)
    for m in RE_NUMBER.finditer(text):
        if m.group(1).strip() in ("", "-"):
            continue
        add("number", m)
    spans.sort(key=lambda s: s["span"][0])
    return spans

def build_segments(struct):
    segments = []
    sections = {s["id"]: s for s in struct["sections"]}
    ref_sec_ids = set()
    for s in struct["sections"]:
        if RE_REF_HEAD.search(s["heading"] or ""):
            ref_sec_ids.add(s["id"])

    # 标题段
    for s in struct["sections"]:
        if s["level"] > 0 and s["heading"]:
            segments.append({
                "seg_id": s["id"] + "-h", "para_id": None, "section_id": s["id"],
                "section": s["heading"], "kind": "heading", "level": s["level"],
                "source": s["heading"], "protected": protected_spans(s["heading"]),
                "needs_translation": True,
            })

    for p in struct["paragraphs"]:
        sec = sections.get(p["section_id"], {})
        in_refs = p["section_id"] in ref_sec_ids
        kind = classify_para(p["text"], in_refs)
        if kind == "reference":
            # 多条目合并段按 [n] 前缀拆分为逐条 segment，保证逐条完整性可机检
            entries = [e.strip() for e in re.split(r"(?=\[\d+\]\s)", p["text"]) if e.strip()]
            if len(entries) <= 1:
                entries = [p["text"]]
            for ri, entry in enumerate(entries, 1):
                segments.append({
                    "seg_id": f"{p['id']}-r{ri}" if len(entries) > 1 else p["id"],
                    "para_id": p["id"], "section_id": p["section_id"],
                    "section": sec.get("heading"), "kind": "reference",
                    "source": entry, "protected": protected_spans(entry),
                    "needs_translation": False,
                    "note": "参考文献条目原样保留"})
            continue
        if kind == "formula":
            segments.append({
                "seg_id": p["id"], "para_id": p["id"], "section_id": p["section_id"],
                "section": sec.get("heading"), "kind": kind,
                "source": p["text"], "protected": protected_spans(p["text"]),
                "needs_translation": False,
                "note": "公式原样保留"})
            continue
        if kind in ("caption", "footnote", "list"):
            segments.append({
                "seg_id": p["id"], "para_id": p["id"], "section_id": p["section_id"],
                "section": sec.get("heading"), "kind": kind,
                "source": p["text"], "protected": protected_spans(p["text"]),
                "needs_translation": True,
                "note": "整体翻译，保持编号/标记原位",
            })
            continue
        # body：句子级
        sents = [s for s in struct["sentences"] if s["para_id"] == p["id"]]
        if not sents:
            segments.append({
                "seg_id": p["id"], "para_id": p["id"], "section_id": p["section_id"],
                "section": sec.get("heading"), "kind": "body",
                "source": p["text"], "protected": protected_spans(p["text"]),
                "needs_translation": True})
            continue
        for sn in sents:
            segments.append({
                "seg_id": sn["id"], "para_id": p["id"], "section_id": p["section_id"],
                "section": sec.get("heading"), "kind": "body",
                "source": sn["text"], "protected": protected_spans(sn["text"]),
                "needs_translation": True})

    order = {sid: i for i, sid in enumerate(
        [s["id"] for s in sorted(struct["sections"], key=lambda x: x["order"])])}
    def sort_key(seg):
        sid = seg["section_id"]
        if seg["kind"] == "heading":
            return (order.get(sid, 999), -1, 0)
        m = re.match(r"P(\d+)(?:-s(\d+))?", seg["seg_id"])
        pno = int(m.group(1)) if m else 9999
        sno = int(m.group(2)) if m and m.group(2) else 0
        return (order.get(sid, 999), pno, sno)
    segments.sort(key=sort_key)
    return segments

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    sp = os.path.join(args.work, "structure.json")
    if not os.path.exists(sp):
        print("[segment_builder][FATAL] 缺少 work/structure.json，先运行 parse_manuscript.py",
              file=sys.stderr)
        return 1
    with open(sp, encoding="utf-8") as f:
        struct = json.load(f)

    segments = build_segments(struct)
    with open(os.path.join(args.work, "segments.json"), "w", encoding="utf-8") as f:
        json.dump({"source_file": struct["source_file"], "segments": segments},
                  f, ensure_ascii=False, indent=1)

    # 紧凑源文清单（供 Agent 分批翻译）
    lines = ["# 待译句段清单（每行格式：<seg_id> TAB <源文>；括号内为须原样保留的受保护片段）",
             ""]
    cur_sec = None
    for seg in segments:
        if seg["section_id"] != cur_sec:
            cur_sec = seg["section_id"]
            lines.append(f"\n## [{cur_sec}] {seg.get('section') or ''}")
        if not seg["needs_translation"]:
            lines.append(f"{seg['seg_id']}\t〔不译·原样保留：{seg.get('note','')}〕"
                         f"{seg['source'][:80]}")
            continue
        prot = "、".join(s["text"] for s in seg["protected"][:8])
        hint = f"  〔保留: {prot}〕" if prot else ""
        lines.append(f"{seg['seg_id']}\t{seg['source']}{hint}")
    with open(os.path.join(args.work, "source_for_translation.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    n_tr = sum(1 for s in segments if s["needs_translation"])
    n_prot = sum(len(s["protected"]) for s in segments)
    kinds = {}
    for s in segments:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    print(f"[segment_builder] 句段={len(segments)} 待译={n_tr} 保护片段={n_prot} 类型={kinds}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
