#!/usr/bin/env python3
"""fidelity_engine.py — 事实数据保真核验与内容取舍台账引擎（v1.0.1 专属）。

子命令:
  check   --source work/source.json --rewrite <改写稿.md> [--work /app/work]
      → work/fidelity_report.json + work/fidelity_report.md：
        正向：源文 fact_index 中每个 number/percent/sample/figure_ref/table_ref 事实在
              改写稿中的核验（verbatim / derived / missing，含换算式）。
        反向：改写稿中每个"数值+单位/百分比"若不能在源文中 verbatim 或 derived 匹配，
              记 unverified（severity=critical）。
        图表引用：改写稿引用的图/表编号必须存在于源文；源文被引图表消失记 warn。
        遮蔽：年份(19xx/20xx)、紧贴字母的数字（化学式/倍率如 LiNi0.8、0.5C）、
              章节号/版本号不当作数据事实。
  ledger  --decisions work/retention_decisions.jsonl [--work /app/work]
      → work/retention_ledger.json + work/retention_ledger.md：
        校验取舍决定（每个含 conclusion/compare/关键数据的段落必须有决定且不得无理由
        删除），并生成人读台账（每段 before 摘要/动作/理由/涉及事实/丢弃事实）。
判据与 references/fidelity_rules.md 的阈值表保持一致。
"""
import argparse, json, os, re, sys

# ============ 判据常量（与 references/fidelity_rules.md 一致） ============
EPS_EXACT = 1e-9          # verbatim：数值严格相等
REL_TOL = 0.01            # derived：±1% 相对容差 / 四舍五入容差
MIN_REASON_CHARS = 4      # ledger：删除/压缩决定的最小理由长度
MASKED_REASONS = {"", "无", "无理由", "不知道", "不详", "略", "删了", "不需要"}
MANDATORY_TYPES = {"number", "percent", "sample", "compare", "conclusion"}
KEY_PID_TYPES = {"compare", "conclusion"}   # 同段含此类事实 → missing/altered 判 critical
CHECK_TYPES = {"number", "percent", "sample", "figure_ref", "table_ref"}
ACTIONS = {"保留", "压缩", "删除"}

# ============ 单位体系：canonical -> (family, factor_to_base, [中文别名]) ============
UNIT_TABLE = {
    "nm": ("length", 1e-9, ["纳米"]),
    "μm": ("length", 1e-6, ["微米"]),
    "mm": ("length", 1e-3, ["毫米"]),
    "cm": ("length", 1e-2, ["厘米"]),
    "km": ("length", 1e3,  ["千米", "公里"]),
    "Ω":  ("resistance", 1.0, ["欧姆"]),
    "kΩ": ("resistance", 1e3, ["千欧"]),
    "MΩ": ("resistance", 1e6, ["兆欧"]),
    "mV": ("voltage", 1e-3, ["毫伏"]),
    "V":  ("voltage", 1.0, ["伏", "伏特"]),
    "kV": ("voltage", 1e3, ["千伏"]),
    "mg": ("mass", 1e-3, ["毫克"]),
    "g":  ("mass", 1.0, ["克"]),
    "kg": ("mass", 1e3,  ["千克", "公斤"]),
    "μL": ("volume", 1e-6, ["微升"]),
    "mL": ("volume", 1e-3, ["毫升"]),
    "L":  ("volume", 1.0, ["升"]),
}
EXTRA_UNITS = ["mS/cm", "S/cm", "g/cm3", "g·cm-3", "kg/m3", "mAh/g", "mAh·g-1",
               "Wh/kg", "W/kg", "MPa", "GPa", "kPa", "Pa", "K", "℃", "°C",
               "mol/L", "mM", "Hz", "kHz", "MHz", "GHz", "ms", "s", "min", "h",
               "μg", "wt%", "vol%", "at%", "ppm", "ppb", "nmol", "μmol", "mmol",
               "mol", "J", "kJ", "mJ", "eV", "keV", "rpm", "倍"]
ALIAS = {a: canon for canon, (_f, _fac, aliases) in UNIT_TABLE.items() for a in aliases}

NUM = r"[-+−]?\d+(?:\.\d+)?"
_UNITS_SORTED = sorted(set(list(UNIT_TABLE.keys()) + list(ALIAS.keys()) + EXTRA_UNITS),
                       key=len, reverse=True)
UNIT_ALT = "|".join(re.escape(u) for u in _UNITS_SORTED)
UNIT_NO_PCT_ALT = "|".join(re.escape(u) for u in _UNITS_SORTED if u not in ("%",))

# 改写稿数值 token：number + 可选单位/百分号（含 ％ 与 ‰）
TOKEN_RE = re.compile(r"(?P<num>%s)\s*(?P<unit>%%|％|‰|%s)?" % (NUM, UNIT_ALT))
PCT_ZH_RE = re.compile(r"百分之\s*(?P<num>%s)" % NUM)
FIG_RE = re.compile(r"(?<![0-9A-Za-z.])(?:图|Fig\.?|Figure)\s*(\d+(?:[-–.]\d+)*[a-zA-Z]?)")
TAB_RE = re.compile(r"(?<!代)(?<![0-9A-Za-z.])(?:表|Table)\s*(\d+(?:[-–.]\d+)*)")
RE_YEAR = re.compile(r"^(?:19|20)\d{2}$")
RE_DROP = re.compile(r"由\s*(%s)\s*(%s)?\s*降至\s*(%s)\s*(%s)?" % (NUM, UNIT_NO_PCT_ALT, NUM, UNIT_NO_PCT_ALT))

LEVEL_RANK = {"verbatim": 3, "derived": 2}

# ============ 数值与单位工具 ============

def fnum(s):
    return float(s.replace("−", "-").strip())

def rel_close(a, b, tol=REL_TOL):
    if b == 0:
        return abs(a) <= tol
    return abs(a - b) / abs(b) <= tol

def decs(v):
    s = ("%f" % v).rstrip("0")
    return len(s.split(".")[1]) if "." in s else 0

def rounded_eq(a, b):
    """四舍五入等价：a 按 b 的小数位取整后相等，或相对差 ≤ 1%。"""
    if rel_close(a, b):
        return True
    k = min(decs(a), decs(b))
    return round(a, k) == round(b, k)

def canon(unit):
    return ALIAS.get(unit, unit) if unit else None

def unit_info(unit):
    return UNIT_TABLE.get(canon(unit)) if unit else None

def fmt(v):
    s = ("%f" % v).rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"

def classify(v_tok, u_tok, v_fac, u_fac):
    """判定改写 token (v_tok,u_tok) 是否等价于源文事实值 (v_fac,u_fac)。
    返回 (level, formula)；不匹配返回 None。u 为 "%" 表示百分数，None 表示裸数。"""
    if u_fac == "%":
        if u_tok == "%":
            if abs(v_tok - v_fac) <= EPS_EXACT:
                return ("verbatim", None)
            if rounded_eq(v_tok, v_fac):
                return ("derived", f"{fmt(v_fac)}% ≈ {fmt(v_tok)}%（四舍五入/±1% 容差）")
            return None
        if u_tok == "‰" and abs(v_tok / 10.0 - v_fac) <= max(REL_TOL, 0):
            if rounded_eq(v_tok / 10.0, v_fac):
                return ("derived", f"{fmt(v_fac)}% = {fmt(v_tok)}‰")
            return None
        if u_tok is None and 0 < abs(v_tok) < 1:
            dec = v_fac / 100.0
            if abs(v_tok - dec) <= EPS_EXACT:
                return ("derived", f"{fmt(v_fac)}% = {fmt(v_tok)}（百分比↔小数）")
            if rounded_eq(v_tok, dec):
                return ("derived", f"{fmt(v_fac)}% ≈ {fmt(v_tok)}（百分比↔小数，±1% 容差）")
        return None
    if u_fac is None:  # 源文裸数（sample/年份）只对裸 token
        if u_tok is None and (abs(v_tok - v_fac) <= EPS_EXACT or rounded_eq(v_tok, v_fac)):
            return ("verbatim", None) if abs(v_tok - v_fac) <= EPS_EXACT else \
                   ("derived", f"{fmt(v_fac)} ≈ {fmt(v_tok)}（四舍五入）")
        return None
    # number 事实（带单位）
    if not u_tok or u_tok == "%":
        return None
    i_tok, i_fac = unit_info(u_tok), unit_info(u_fac)
    if i_tok and i_fac and i_tok[0] == i_fac[0]:
        same_mag = abs(i_tok[1] - i_fac[1]) <= EPS_EXACT
        if same_mag:
            if abs(v_tok - v_fac) <= EPS_EXACT:
                if u_tok != u_fac and canon(u_tok) == canon(u_fac):
                    return ("verbatim", f"单位等价：{fmt(v_fac)} {u_fac} ≡ {fmt(v_tok)} {u_tok}")
                return ("verbatim", None)
            if rounded_eq(v_tok, v_fac):
                return ("derived", f"{fmt(v_fac)} {u_fac} ≈ {fmt(v_tok)} {u_tok}（四舍五入/±1% 容差）")
            return None
        base_tok, base_fac = v_tok * i_tok[1], v_fac * i_fac[1]
        if rel_close(base_tok, base_fac, REL_TOL / 10):
            return ("derived", f"{fmt(v_fac)} {u_fac} = {fmt(v_tok)} {u_tok}（单位换算）")
        return None
    if canon(u_tok) == canon(u_fac):
        if abs(v_tok - v_fac) <= EPS_EXACT:
            return ("verbatim", None)
        if rounded_eq(v_tok, v_fac):
            return ("derived", f"{fmt(v_fac)} {u_fac} ≈ {fmt(v_tok)} {u_tok}（四舍五入/±1% 容差）")
    return None

# ============ 改写稿 token 化（含遮蔽） ============

def tokenize_rewrite(text):
    """抽取改写稿中的数值 token；遮蔽年份、紧贴字母的数字（化学式/倍率）、章节号。"""
    tokens = []
    occupied = set()
    for m in PCT_ZH_RE.finditer(text):  # 百分之X
        tokens.append({"value": fnum(m.group("num")), "unit": "%", "raw": m.group(0),
                       "span": list(m.span()), "masked": False})
        occupied.add((m.start(), m.end()))
    for m in TOKEN_RE.finditer(text):
        if any(not (m.end() <= a or m.start() >= b) for a, b in occupied):
            continue
        num_s, unit = m.group("num"), m.group("unit")
        if unit in ("%", "％"):
            unit = "%"
        v = fnum(num_s)
        prev = text[m.start() - 1] if m.start() > 0 else ""
        nxt = text[m.end()] if m.end() < len(text) else ""
        masked = False
        note = None
        if unit is None:
            if RE_YEAR.match(num_s.lstrip("+-")):
                masked, note = True, "年份遮蔽"
            elif (prev.isalpha() or nxt.isalpha()):
                masked, note = True, "紧贴字母遮蔽（化学式/倍率/章节号）"
            elif prev in "vV第" :
                masked, note = True, "章节/版本号遮蔽"
        tokens.append({"value": v, "unit": unit, "raw": m.group(0).strip(),
                       "span": list(m.span()), "masked": masked, "mask_note": note})
    tokens.sort(key=lambda t: t["span"][0])
    return tokens

def parse_fact_groups(raw, ftype):
    """把 fact raw 解析为 [(value, unit)]；percent 的 unit 记为 "%"，sample 记 None。"""
    if ftype == "percent":
        m = re.match(r"\s*(%s)" % NUM, raw)
        return [(fnum(m.group(1)), "%")] if m else []
    if ftype == "sample":
        m = re.search(r"\d+", raw)
        return [(float(m.group(0)), None)] if m else []
    if ftype == "number":
        groups = []
        for m in re.finditer(r"(%s)\s*(%s)" % (NUM, UNIT_NO_PCT_ALT), raw):
            groups.append((fnum(m.group(1)), m.group(2)))
        return groups
    return []

# ============ check 子命令 ============

def cmd_check(args):
    src = {}
    try:
        with open(args.source, encoding="utf-8") as f:
            src = json.load(f)
    except Exception as e:
        print(f"[fidelity:check] source.json 读取失败: {e}", file=sys.stderr)
        return 1
    if not os.path.exists(args.rewrite):
        print(f"[fidelity:check] 改写稿不存在: {args.rewrite}", file=sys.stderr)
        return 1
    with open(args.rewrite, encoding="utf-8") as f:
        rtext = f.read()

    paragraphs = src.get("paragraphs", [])
    fact_index = src.get("fact_index", [])
    source_text = "\n".join(p["text"] for p in paragraphs)
    pid_key = {p["pid"]: any(f["type"] in KEY_PID_TYPES for f in p.get("facts", []))
               for p in paragraphs}
    para_text = {p["pid"]: p["text"] for p in paragraphs}
    # 源文"由 A 降至 B"端点（用于 73.4%=(320-85)/320 重算判定）
    drop_endpoints = {}
    for p in paragraphs:
        m = RE_DROP.search(p["text"])
        if m:
            a, ua, b, ub = fnum(m.group(1)), m.group(2), fnum(m.group(3)), m.group(4)
            drop_endpoints[p["pid"]] = {"a": a, "ua": ua, "b": b, "ub": ub}

    rtokens = tokenize_rewrite(rtext)
    live_tokens = [t for t in rtokens if not t["masked"]]

    # ---- 源文图表引用集合 ----
    src_figs = {m.group(1) for f in fact_index if f["type"] == "figure_ref"
                for m in FIG_RE.finditer(f["raw"])}
    src_tabs = {m.group(1) for f in fact_index if f["type"] == "table_ref"
                for m in TAB_RE.finditer(f["raw"])}
    rw_figs = {m.group(1): m.group(0) for m in FIG_RE.finditer(rtext)}
    rw_tabs = {m.group(1): m.group(0) for m in TAB_RE.finditer(rtext)}

    issues, fact_rows = [], []
    n_verbatim = n_derived = n_missing = n_altered = 0

    # ---- 正向：源文事实 → 改写稿（先全量匹配，再统一判定，避免顺序误报） ----
    check_facts = []
    seen = set()
    for f in fact_index:
        ftype = f["type"]
        if ftype not in CHECK_TYPES or ftype in ("figure_ref", "table_ref"):
            continue  # 图表引用在专门小节处理
        key = (f["pid"], ftype, f["raw"])
        if key in seen:
            continue
        seen.add(key)
        groups = parse_fact_groups(f["raw"], ftype)
        if groups:
            check_facts.append((f, ftype, groups))

    results = []   # (f, ftype, sev_base, [(level, formula, token)], missing_groups)
    matched_spans = set()
    for f, ftype, groups in check_facts:
        sev_base = "critical" if pid_key.get(f["pid"]) else "warn"
        matched, missing_groups = [], []
        for (gv, gu) in groups:
            best = None
            for t in live_tokens:
                r = classify(t["value"], t["unit"], gv, gu)
                if r and (best is None or LEVEL_RANK[r[0]] > LEVEL_RANK[best[0]]):
                    best = (r[0], r[1], t)
            if best is None and ftype == "percent" and f["pid"] in drop_endpoints:
                # 重算判定：73.4% = (320-85)/320
                ep = drop_endpoints[f["pid"]]
                if ep["ua"] and ep["ub"] and canon(ep["ua"]) == canon(ep["ub"]):
                    recomputed = (ep["a"] - ep["b"]) / ep["a"] * 100.0
                    if rounded_eq(gv, recomputed):
                        has_a = any(classify(t["value"], t["unit"], ep["a"], ep["ua"])
                                    for t in live_tokens)
                        has_b = any(classify(t["value"], t["unit"], ep["b"], ep["ub"])
                                    for t in live_tokens)
                        if has_a and has_b:
                            best = ("derived",
                                    f"{fmt(gv)}% = ({fmt(ep['a'])}-{fmt(ep['b'])})/{fmt(ep['a'])}"
                                    f"（由端点重算）", None)
            if best:
                matched.append(best)
                if best[2] is not None:
                    matched_spans.add(tuple(best[2]["span"]))
            else:
                missing_groups.append((gv, gu))
        results.append((f, ftype, sev_base, matched, missing_groups))

    for f, ftype, sev_base, matched, missing_groups in results:
        if not missing_groups:
            all_levels = [m[0] for m in matched]
            formulas = [m[1] for m in matched if m[1]]
            level = "verbatim" if all(l == "verbatim" for l in all_levels) else "derived"
            if level == "verbatim":
                n_verbatim += 1
            else:
                n_derived += 1
            fact_rows.append({"pid": f["pid"], "type": ftype, "raw": f["raw"],
                              "status": level, "formula": "；".join(formulas) or None,
                              "severity": "info"})
        else:
            # 同量纲不同值 → altered；否则 missing
            altered_hit = None
            for (gv, gu) in missing_groups:
                for t in live_tokens:
                    same_dim = (gu == "%" and t["unit"] == "%") or (
                        gu and t["unit"] and t["unit"] != "%" and
                        unit_info(t["unit"]) and unit_info(gu) and
                        unit_info(t["unit"])[0] == unit_info(gu)[0])
                    if same_dim and tuple(t["span"]) not in matched_spans and \
                            classify(t["value"], t["unit"], gv, gu) is None:
                        altered_hit = t
                        break
                if altered_hit:
                    break
            if altered_hit:
                n_altered += 1
                issues.append({"severity": sev_base, "type": "altered",
                               "pid": f["pid"], "raw": f["raw"],
                               "detail": f"源文「{f['raw']}」，改写稿出现同量纲不同值"
                                         f"「{altered_hit['raw']}」（疑似篡改，必须改回或删去）"})
                fact_rows.append({"pid": f["pid"], "type": ftype, "raw": f["raw"],
                                  "status": "altered",
                                  "rewrite_value": altered_hit["raw"],
                                  "severity": sev_base,
                                  "note": f"改写稿出现 {altered_hit['raw']}，与源文不符"})
            else:
                n_missing += 1
                issues.append({"severity": sev_base, "type": "missing",
                               "pid": f["pid"], "raw": f["raw"],
                               "detail": (f"源文事实「{f['raw']}」未在改写稿中出现"
                                          + ("（该段含比较/结论表述，属关键数据）"
                                             if sev_base == "critical" else ""))})
                fact_rows.append({"pid": f["pid"], "type": ftype, "raw": f["raw"],
                                  "status": "missing", "severity": sev_base,
                                  "note": "关键数据缺失" if sev_base == "critical"
                                          else "非关键数据缺失（可接受，需在台账说明）"})

    # ---- 图表引用双向检查 ----
    fig_rows = []
    for num, raw in rw_figs.items():
        if num not in src_figs:
            issues.append({"severity": "critical", "type": "figure_ref_unknown",
                           "pid": None, "raw": raw,
                           "detail": f"改写稿引用了源文不存在的图编号「{raw}」"})
            fig_rows.append({"ref": raw, "status": "unknown", "severity": "critical"})
    for num in src_figs:
        if num not in rw_figs:
            issues.append({"severity": "warn", "type": "figure_ref_dropped",
                           "pid": None, "raw": f"图{num}",
                           "detail": f"源文图{num}的引用在改写稿中消失"})
            fig_rows.append({"ref": f"图{num}", "status": "dropped", "severity": "warn"})
    for num, raw in rw_tabs.items():
        if num not in src_tabs:
            issues.append({"severity": "critical", "type": "table_ref_unknown",
                           "pid": None, "raw": raw,
                           "detail": f"改写稿引用了源文不存在的表编号「{raw}」"})
            fig_rows.append({"ref": raw, "status": "unknown", "severity": "critical"})
    for num in src_tabs:
        if num not in rw_tabs:
            issues.append({"severity": "warn", "type": "table_ref_dropped",
                           "pid": None, "raw": f"表{num}",
                           "detail": f"源文表{num}的引用在改写稿中消失"})
            fig_rows.append({"ref": f"表{num}", "status": "dropped", "severity": "warn"})

    # ---- 反向：改写稿 token → 源文 ----
    n_unverified = 0
    unverified_rows = []
    src_bare_values = set()
    for f in fact_index:
        for gv, gu in parse_fact_groups(f["raw"], f["type"]):
            if gu == "%":
                src_bare_values.add(round(gv / 100.0, 6))
            src_bare_values.add(round(gv, 6))
    for y in re.finditer(r"(?:19|20)\d{2}", source_text):
        src_bare_values.add(float(y.group(0)))
    src_fig_nums = {float(n) for n in src_figs | src_tabs}

    for t in rtokens:
        if t["masked"]:
            continue
        ok = False
        for f in fact_index:
            for gv, gu in parse_fact_groups(f["raw"], f["type"]):
                if classify(t["value"], t["unit"], gv, gu):
                    ok = True
                    break
            if ok:
                break
        if not ok and t["unit"] is None:
            if (round(t["value"], 6) in src_bare_values or
                    t["value"] in src_fig_nums or
                    re.search(re.escape(t["raw"].split()[0]) if t["raw"] else r"$^",
                              source_text)):
                ok = True
        if not ok:
            n_unverified += 1
            issues.append({"severity": "critical", "type": "unverified",
                           "pid": None, "raw": t["raw"],
                           "detail": f"改写稿数值「{t['raw']}」在源文中无对应"
                                     f"（疑似源外新事实，必须删除或由作者确认）"})
            unverified_rows.append({"raw": t["raw"], "span": t["span"],
                                    "severity": "critical"})

    n_critical = sum(1 for i in issues if i["severity"] == "critical")
    n_warn = sum(1 for i in issues if i["severity"] == "warn")
    verdict = "PASS" if n_critical == 0 else "FAIL"
    report = {
        "verdict": verdict,
        "rewrite": os.path.basename(args.rewrite),
        "summary": {"n_facts_checked": len(fact_rows), "verbatim": n_verbatim,
                    "derived": n_derived, "missing": n_missing, "altered": n_altered,
                    "unverified": n_unverified,
                    "figure_refs": {"source": sorted(src_figs), "rewrite": sorted(rw_figs),
                                    "unknown": sum(1 for r in fig_rows if r["status"] == "unknown"),
                                    "dropped": sum(1 for r in fig_rows if r["status"] == "dropped")},
                    "masked_tokens": sum(1 for t in rtokens if t["masked"]),
                    "n_critical": n_critical, "n_warn": n_warn},
        "facts": fact_rows,
        "unverified": unverified_rows,
        "figure_table_refs": fig_rows,
        "issues": issues,
        "tolerances": {"eps_exact": EPS_EXACT, "rel_tol": REL_TOL,
                       "masking": "年份/紧贴字母数字（化学式、倍率如0.5C）/章节号/版本号不作数据事实"},
    }
    with open(os.path.join(args.work, "fidelity_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    lines = ["# 事实数据保真核验报告", "",
             f"- 判定：**{verdict}**（critical {n_critical}，warn {n_warn}）",
             f"- 事实核验：verbatim {n_verbatim}，derived {n_derived}，"
             f"missing {n_missing}，altered {n_altered}，unverified {n_unverified}",
             f"- 遮蔽 token（年份/化学式/章节号，未参与判定）：{report['summary']['masked_tokens']}",
             ""]
    derived_rows = [r for r in fact_rows if r["status"] == "derived"]
    if derived_rows:
        lines += ["## 换算式（derived）", ""]
        for r in derived_rows:
            lines.append(f"- {r['pid']} `{r['raw']}` → {r['formula']}")
        lines.append("")
    bad = [r for r in fact_rows if r["status"] in ("missing", "altered")]
    if bad:
        lines += ["## 源文事实未保真（missing / altered）", ""]
        for r in bad:
            lines.append(f"- [{r['severity']}] {r['pid']} `{r['raw']}`：{r['status']}"
                         + (f"（改写稿写作 {r.get('rewrite_value')}）" if r.get("rewrite_value") else ""))
        lines.append("")
    if unverified_rows:
        lines += ["## 改写稿源外数值（unverified）", ""]
        for r in unverified_rows:
            lines.append(f"- [critical] `{r['raw']}`：源文中 verbatim/derived 均无对应")
        lines.append("")
    lines += ["## 图表引用", ""]
    if fig_rows:
        for r in fig_rows:
            lines.append(f"- [{r['severity']}] {r['ref']}：{r['status']}")
    else:
        lines.append("- 源文与改写稿图表引用一致（或双方均无）。")
    if issues:
        lines += ["", "## 问题清单（含 warn）", ""]
        for i, it in enumerate(issues, 1):
            lines.append(f"{i}. [{it['severity']}] {it['type']}：{it['detail']}")
    with open(os.path.join(args.work, "fidelity_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[fidelity:check] verdict={verdict} verbatim={n_verbatim} derived={n_derived} "
          f"missing={n_missing} altered={n_altered} unverified={n_unverified} "
          f"critical={n_critical} warn={n_warn}")
    return 0 if verdict == "PASS" else 2

# ============ ledger 子命令 ============

def cmd_ledger(args):
    try:
        with open(os.path.join(args.work, "source.json"), encoding="utf-8") as f:
            src = json.load(f)
    except Exception as e:
        print(f"[fidelity:ledger] source.json 读取失败: {e}", file=sys.stderr)
        return 1
    paragraphs = src.get("paragraphs", [])
    fact_by_pid = {}
    for p in paragraphs:
        fact_by_pid[p["pid"]] = p.get("facts", [])
    mandatory = [p["pid"] for p in paragraphs
                 if any(f["type"] in MANDATORY_TYPES for f in p.get("facts", []))]

    errors, warnings, decisions = [], [], {}
    if not os.path.exists(args.decisions):
        errors.append({"type": "decisions_file_missing",
                       "detail": f"决定文件不存在: {args.decisions}",
                       "missing_pids": mandatory})
    else:
        with open(args.decisions, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError as e:
                    errors.append({"type": "jsonl_parse_error", "line": ln,
                                   "detail": f"第 {ln} 行非合法 JSON：{e}"})
                    continue
                pid = d.get("source_pid")
                action = d.get("action")
                reason = (d.get("reason") or "").strip()
                if not pid or not isinstance(pid, str):
                    errors.append({"type": "missing_pid", "line": ln,
                                   "detail": f"第 {ln} 行缺少 source_pid 字段"})
                    continue
                if pid in decisions:
                    errors.append({"type": "duplicate_decision", "line": ln,
                                   "detail": f"{pid} 出现重复决定"})
                    continue
                if action not in ACTIONS:
                    errors.append({"type": "invalid_action", "line": ln, "pid": pid,
                                   "detail": f"action 必须是 保留|压缩|删除，实为 {action!r}"})
                    continue
                if (not reason or reason in MASKED_REASONS or
                        (action == "删除" and len(reason) < MIN_REASON_CHARS)):
                    errors.append({"type": "unreasoned_action", "line": ln, "pid": pid,
                                   "detail": (f"action={action} 但 reason 缺失/无效"
                                              f"（删除须 ≥{MIN_REASON_CHARS} 字且不得为敷衍理由）")})
                    continue
                if pid not in fact_by_pid:
                    warnings.append({"type": "unknown_pid", "line": ln, "pid": pid,
                                     "detail": "source_pid 不在源文段落中，忽略"})
                    continue
                decisions[pid] = {"source_pid": pid, "action": action, "reason": reason}
        missing = [pid for pid in mandatory if pid not in decisions]
        if missing:
            errors.append({"type": "missing_decision", "detail": "关键段落缺取舍决定",
                           "missing_pids": missing})

    entries = []
    for p in paragraphs:
        pid = p["pid"]
        facts = fact_by_pid[pid]
        key_facts = [f"{f['type']}:{f['raw']}" for f in facts
                     if f["type"] in MANDATORY_TYPES]
        d = decisions.get(pid)
        entries.append({
            "pid": pid, "kind": p["kind"],
            "before": p["text"][:80],
            "n_facts": len(facts),
            "is_mandatory": any(f["type"] in MANDATORY_TYPES for f in facts),
            "action": d["action"] if d else None,
            "reason": d["reason"] if d else None,
            "involved_facts": key_facts,
            "discarded_facts": key_facts if (d and d["action"] == "删除") else [],
            "decided": d is not None,
        })

    ledger = {"summary": {"n_paragraphs": len(paragraphs),
                          "n_mandatory": len(mandatory),
                          "n_decided": len(decisions),
                          "n_deleted": sum(1 for d in decisions.values() if d["action"] == "删除"),
                          "n_errors": len(errors), "n_warnings": len(warnings)},
              "entries": entries, "errors": errors, "warnings": warnings}
    with open(os.path.join(args.work, "retention_ledger.json"), "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)

    L = ["# 内容取舍台账（retention ledger）", "",
         f"- 段落 {len(paragraphs)}，需决定的关键段落 {len(mandatory)}，已决定 {len(decisions)}，"
         f"删除 {ledger['summary']['n_deleted']}", ""]
    L += ["| 段落 | before（摘要） | 动作 | 理由 | 涉及事实 |", "|-|-|-|-|-|"]
    for e in entries:
        facts_s = "；".join(e["involved_facts"][:6]) or "—"
        act = e["action"] or ("**缺决定**" if e["is_mandatory"] else "—")
        L.append(f"| {e['pid']} | {e['before'][:50].replace('|', '｜')} | {act} "
                 f"| {(e['reason'] or '—')[:40].replace('|', '｜')} | {facts_s.replace('|', '｜')} |")
    deleted = [e for e in entries if e["action"] == "删除"]
    if deleted:
        L += ["", "## 删除段落丢弃的事实清单", ""]
        for e in deleted:
            L.append(f"- {e['pid']}：丢弃 " + ("；".join(e["discarded_facts"]) or "无事实"))
    if errors:
        L += ["", "## 校验错误（必须先修复）", ""]
        for er in errors:
            miss = f"，缺失 pid：{er.get('missing_pids')}" if er.get("missing_pids") else ""
            L.append(f"- [{er['type']}] {er['detail']}{miss}")
    with open(os.path.join(args.work, "retention_ledger.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    if errors:
        for er in errors:
            miss = f" 缺失pid={er.get('missing_pids')}" if er.get("missing_pids") else ""
            print(f"[fidelity:ledger][ERROR] {er['type']}: {er['detail']}{miss}",
                  file=sys.stderr)
        print(f"[fidelity:ledger] FAIL errors={len(errors)} decided={len(decisions)}/{len(mandatory)}")
        return 2
    print(f"[fidelity:ledger] OK 决定={len(decisions)} 覆盖关键段落={len(mandatory)} "
          f"删除={ledger['summary']['n_deleted']} warn={len(warnings)}")
    return 0

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("check")
    p1.add_argument("--source", default="/app/work/source.json")
    p1.add_argument("--rewrite", required=True)
    p1.add_argument("--work", default="/app/work")
    p2 = sub.add_parser("ledger")
    p2.add_argument("--decisions", default="/app/work/retention_decisions.jsonl")
    p2.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    if args.cmd == "check":
        return cmd_check(args)
    return cmd_ledger(args)

if __name__ == "__main__":
    sys.exit(main())
