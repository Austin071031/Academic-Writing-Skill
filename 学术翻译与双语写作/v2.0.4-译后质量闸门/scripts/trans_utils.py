#!/usr/bin/env python3
"""trans_utils.py — 翻译 Skill 共享工具函数（被 assemble/engines import）。

- load_translations(work): 合并 work/translations*.jsonl 与 translations.json，
  后者/后行覆盖先前者（支持增量追加与修订）；返回 {seg_id: {"translation":..., "line": n, "file": name}}
- extract_numbers(text): 提取数字并做跨语言表达归一（万/亿/million/billion 等），
  返回 [{raw, value, unit, span}]
- 语气/否定/量词词表（按语言）供边界与风格引擎使用。
只依赖标准库。
"""
import json, os, re, glob

RE_NUM_CORE = re.compile(
    r"(?<![A-Za-z0-9.])(-?\d{1,3}(?:,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?)"
    r"(\s*[×xX]\s*10\^?(?:\{)?[-+]?\d+(?:\})?|"
    r"\s*(?:%|‰|°C|K\b|nm|µm|μm|mm|cm|dm|km|mA\s*/\s*cm[²2-]|"
    r"mA|cm-2|cm2|cm²|"
    r"V|mV|kV|W|kW|kWh|Wh|kg|mg|µg|μg|g\b|mol|mmol|mM|M\b|ppm|ppb|"
    r"Hz|kHz|MHz|GHz|Pa|kPa|MPa|GPa|bar|atm|Ω|ohm|"
    r"h|hr|hrs|min|s\b|ms|ns|µs|μs|days?|weeks?|months?|years?|"
    r"million|billion|trillion|thousand|万|亿|千|百|"
    r"eV|keV|MeV|J|kJ|mJ|rpm|wt%|at%|vol%|mol%))?", re.I)

# 引用标记（数字型/著者-年型）：数字抽取前屏蔽，避免把 [1]、2023 当年份数字误检
RE_CITE_MASK = [
    re.compile(r"\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]"),
    re.compile(r"[（(](?:[A-Z][A-Za-zÀ-ÿ'’-]+(?:\s+(?:and|&|与)\s+[A-Z][A-Za-zÀ-ÿ'’-]+)?"
               r"(?:\s+et\s+al\.)?,?\s+\d{4}[a-z]?(?:\s*[;；]\s*[^)）]*\d{4}[a-z]?)*"
               r")[)）]"),
    re.compile(r"[A-Z][A-Za-zÀ-ÿ'’-]+(?:\s+et\s+al\.)?\s*[（(]\d{4}[a-z]?[)）]"),
]

UNIT_SCALE = {"万": 1e4, "亿": 1e8, "千": 1e3, "百": 1e2,
              "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
PURE_UNITS = {"%", "‰", "°c", "k", "nm", "µm", "μm", "mm", "cm", "dm", "km", "ma",
              "cm-2", "cm2", "cm²", "ma / cm²", "v", "mv", "kv", "w", "kw", "kwh",
              "wh", "kg", "mg", "µg", "μg", "g", "mol", "mmol", "mm", "m", "ppm",
              "ppb", "hz", "khz", "mhz", "ghz", "pa", "kpa", "mpa", "gpa", "bar",
              "atm", "ω", "ohm", "h", "hr", "hrs", "min", "s", "ms", "ns", "µs",
              "μs", "day", "days", "week", "weeks", "month", "months", "year",
              "years", "ev", "kev", "mev", "j", "kj", "mj", "rpm", "wt%", "at%",
              "vol%", "mol%"}

def parse_number_token(raw_num, suffix):
    """返回 (value, unit)。单位词（万/亿/million…）参与数值；物理单位归一为小写串。"""
    try:
        base = float(raw_num.replace(",", ""))
    except ValueError:
        return None, None
    unit = None
    if suffix:
        s = suffix.strip()
        m = re.match(r"[×xX]\s*10\^?(?:\{)?([-+]?\d+)", s)
        if m:
            base *= 10 ** int(m.group(1))
        else:
            low = s.lower().strip()
            if low in UNIT_SCALE:
                base *= UNIT_SCALE[low]
            elif low in PURE_UNITS or re.fullmatch(r"ma\s*/\s*cm[²2]", low):
                unit = low
            else:
                unit = low
    return base, unit

def extract_numbers(text):
    """提取 [{raw, value, unit, span}]；value 为跨语言归一后的浮点（含万/亿/million）。
    引用标记（[1]、(Zhang, 2023)）内部数字先屏蔽，避免把引用当年份/数据误检。"""
    masked = text
    for pat in RE_CITE_MASK:
        masked = pat.sub(lambda m: " " * (m.end() - m.start()), masked)
    out = []
    for m in RE_NUM_CORE.finditer(masked):
        raw_num, suffix = m.group(1), m.group(2)
        if raw_num.strip() in ("", "-"):
            continue
        val, unit = parse_number_token(raw_num, suffix)
        if val is None:
            continue
        out.append({"raw": m.group(0).strip(), "value": val,
                    "unit": unit, "span": list(m.span())})
    return out

# 语气/限定/否定词表：category → {lang: [词]}
HEDGE_LEXICON = {
    "possibility": {
        "en": ["may", "might", "could", "possibly", "perhaps", "likely",
               "unlikely", "potential", "potentially"],
        "zh": ["可能", "也许", "或许", "有望", "潜在", "大概", "或"],
    },
    "suggestion": {
        "en": ["suggest", "suggests", "suggested", "indicate", "indicates",
               "indicated", "imply", "implies", "appear", "appears", "seem",
               "seems", "tentatively"],
        "zh": ["表明", "提示", "显示", "暗示", "初步", "似乎"],
    },
    "approximation": {
        "en": ["approximately", "approx.", "about", "around", "roughly",
               "nearly", "almost", "ca.", "circa", "~"],
        "zh": ["约", "大约", "近", "接近", "左右", "上下", "余"],
    },
    "limitation": {
        "en": ["only", "solely", "exclusively", "just", "merely", "limited to",
               "at most", "at least", "up to", "no more than"],
        "zh": ["仅", "只", "只有", "仅有", "至多", "至少", "最多", "限于"],
    },
    "negation": {
        "en": ["no", "not", "none", "never", "neither", "nor", "without",
               "absence", "absent", "fail", "fails", "failed", "lack", "lacks",
               "insignificant", "not significant", "no significant"],
        "zh": ["不", "无", "没有", "未", "并非", "并无", "缺乏", "未见", "不能",
               "不再", "毫无"],
    },
    "certainty": {
        "en": ["prove", "proves", "proven", "demonstrate", "demonstrates",
               "demonstrated", "confirm", "confirms", "confirmed", "must",
               "certainly", "definitely", "always", "all", "every", "any",
               "completely", "entirely"],
        "zh": ["证明", "证实", "必然", "一定", "所有", "任何", "每个",
               "完全", "彻底", "总是"],
    },
}
# “确定”易误命中“不确定度/决定”等复合词，不列入词表

def find_markers(text, lang, categories=None):
    """返回 [{category, token, span}]；lang ∈ en/zh。"""
    hits = []
    cats = categories or list(HEDGE_LEXICON)
    for cat in cats:
        for tok in HEDGE_LEXICON.get(cat, {}).get(lang, []):
            if lang == "en":
                pat = re.compile(r"(?<![A-Za-z])" + re.escape(tok) + r"(?![A-Za-z])", re.I)
            else:
                pat = re.compile(re.escape(tok))
            for m in pat.finditer(text):
                # "No. 123" / "No 123"（基金号、编号）不是否定词
                if tok.lower() == "no" and re.match(r"^[\s.]*\d", text[m.end():]):
                    continue
                hits.append({"category": cat, "token": m.group(0), "span": list(m.span())})
    hits.sort(key=lambda h: h["span"][0])
    return hits

def load_translations(work):
    """合并 translations*.jsonl（按文件名排序，后写覆盖先写）与 translations.json。
    返回 (merged, sources)，merged: {seg_id: translation_text}。"""
    merged, sources = {}, []
    files = sorted(glob.glob(os.path.join(work, "translations*.jsonl")))
    for fp in files:
        n = 0
        with open(fp, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sid = rec.get("seg_id") or rec.get("id")
                tr = rec.get("translation")
                if sid and isinstance(tr, str) and tr.strip():
                    merged[sid] = tr.strip()
                    n += 1
        sources.append({"file": os.path.basename(fp), "records": n})
    fp = os.path.join(work, "translations.json")
    if os.path.exists(fp):
        try:
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            items = data.items() if isinstance(data, dict) else \
                [(r.get("seg_id"), r.get("translation")) for r in data]
            n = 0
            for sid, tr in items:
                if sid and isinstance(tr, str) and tr.strip():
                    merged[sid] = tr.strip()
                    n += 1
            sources.append({"file": "translations.json", "records": n})
        except Exception:
            pass
    return merged, sources

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

def lang_of(text):
    cn = len(re.findall(r"[一-鿿]", text or ""))
    en = len(re.findall(r"[A-Za-z]", text or ""))
    if cn + en == 0:
        return "unknown"
    return "zh" if cn >= en * 0.3 else "en"
