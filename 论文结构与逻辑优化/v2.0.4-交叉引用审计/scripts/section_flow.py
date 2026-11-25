#!/usr/bin/env python3
"""section_flow.py — V2 主攻引擎：章节结构与叙事顺序深度分析（v2.0.4 交叉引用审计）。

产出:
  work/section_map.json          角色序列表 + 篇幅表 + 缩写表 + 逆序对 + xref_audit（可复核中间产物）
  work/findings_engine.json      深度 findings（与 six_scan 同 schema，report_builder 合并去重）
  work/restructured_outline.md   重组大纲草稿（各节去向 + move/merge/split/add 汇总，非改写稿）

方法（可复核）:
  a) 章节角色序列: 逐节 classify_role，与 CANONICAL_ORDER 比对，列出全部逆序对
     （结果先于方法、结论先于结果、参考文献不在末尾等）→ move 候选。
  b) 核心章节缺失: introduction / method / results|experiment / conclusion；
     全文仅 1-2 节时降级为提示（low，注明"短文档降级"）。
  c) 篇幅分析: 单节 >55% → split 候选；方法章 <8% 且存在结果章 → "方法过薄"（add）；
     引言 >35% → "铺垫过长"（move 细节后移）。
  d) 标题层级: H1→H3 跳变（reorder）；同级重复标题名（merge 候选）；空章节（add）。
  e) 信息释放顺序: 缩写首现未定义（正则 [A-Z][A-Z0-9]{1,7}s?，查首现句及邻句的
     "全称（ABBR）/ABBR（全称）"定义模式）→ add 补定义；"如前所述/aforementioned"
     类回指在前 200 词内无内容词重叠 → add_transition 候选。
  f) 该后移的细节: 结果/讨论/结论章的大段方法性描述（含"采用/步骤/配置为"等）
     → move 到方法章候选。
  g) 交叉引用完整性审计（v2.0.4 新增，dimension=argument_chain）: 图/表/公式/章节/
     文献编号的"引用侧—定义侧"双向核对。引用编号无对应定义锚点 → 悬空（high）；
     文献条目从未被正文引用 → medium；被引图表编号跳号（无悬空时）→ low 提示。
     引用侧取自正文句子（排除参考文献章），定义侧取自独立图注段/标题数字编号/
     参考文献条目，全部统计写入 section_map.json 的 "xref_audit" 键供复核。

所有阈值见 scanutil.THRESH；启发式置信度 0.55-0.75；findings ≤15 条
（xref 类与原有类合并后按 severity 稳定截断，同严重度保持生成顺序）。
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scanutil import (CANONICAL_ORDER, THRESH, terms, jaccard, classify_role,
                      short, make_finding, load_structure, save_findings,
                      append_change_log)

MAX_FINDINGS = 15
IMBALANCE = THRESH["section_imbalance"]          # 0.55 单节占比上限
METHOD_THIN = 0.08                                # 方法章占比下限
INTRO_MAX = 0.35                                  # 引言占比上限
BACKMATTER = ("references", "appendix", "acknowledgment")

BACKREF_CUES = re.compile(
    r"(如前所述|如前所言|如前|如上所述|如上|上述|前已述及|前文|前述|"
    r"as mentioned above|as noted above|as described above|as shown above|"
    r"aforementioned)", re.I)
METHOD_LEAK = re.compile(
    r"(采用|步骤|配置为|参数设置|流程如下|具体操作|实验步骤|实验条件|制备方法|"
    r"球磨|烧结|压制|球料比|升温速率|保温|we use[sd]?|we adopt|we employ|"
    r"experimental setup|the setup|configured as|procedure)", re.I)
# 边界用 (?<![A-Za-z0-9])/(?![A-Za-z0-9]) 而非 \b，避免 Li2CO3/ZrO2 等化学式
# 内部的 "CO3"/"O2" 被当作缩写。
ABBR_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z][A-Z0-9]{1,7}s?(?![A-Za-z0-9])")
MAX_UNDEF_ABBR = 5   # 未定义缩写 finding 上限（其余仅入 abbrev_table）
# 常见非缩写/勿报白名单（罗马数字、国别机构、出版标识）
ABBR_STOP = {"II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII",
             "US", "USA", "UK", "UN", "EU", "DOI", "ISBN", "ISSN", "HTTP", "HTTPS",
             "WWW", "ET", "AL", "VS", "NO", "FIG", "TAB", "EQ", "SEC", "APP",
             "PHD", "MSc".upper(), "DR"}


def load_inspection(work):
    p = os.path.join(work, "inspection.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def is_review_genre(insp):
    c = insp.get("constraints") or {}
    g = str(c.get("genre") or c.get("requirements") or "").lower()
    return ("综述" in g or "review" in g or "survey" in g)


def abbrev_defined(abbr, window):
    """window: 首现句及相邻句拼接文本。检查 全称（ABBR）/ 中文全称（ABBR）/ ABBR（全称）。"""
    esc = re.escape(abbr)
    pats = [
        r"[A-Za-z][A-Za-z\-]{2,}[\s\-]*[（(]\s*" + esc + r"\s*[）)]",   # full name (ABBR)
        r"[一-鿿][一-鿿A-Za-z0-9]{1,20}\s*[（(]\s*" + esc + r"\s*[）)]",  # 中文全称（ABBR）
        esc + r"\s*[（(](?=[^）)]*[a-z一-鿿])[^）)]{2,50}[）)]",          # ABBR（全称）
    ]
    return any(re.search(p, window) for p in pats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    model = load_structure(args.work)
    insp = load_inspection(args.work)
    findings, n = [], 0

    def add(ftype, section, para_id, sent_id, quote, evidence, op, instr,
            sev="medium", conf=0.65, dim="section_structure"):
        nonlocal n
        # v2.0.4: 不再在 add 内截断；全部候选生成完毕后在写出前按 severity 稳定
        # 截断到 MAX_FINDINGS 并重编号（xref 类 high 不会被先到的 low 挤掉）。
        n += 1
        findings.append(make_finding(
            f"E-{n:02d}", dim, ftype, section, para_id, sent_id,
            quote, evidence, op, instr, sev, conf))

    secs = [s for s in model["sections"] if s["level"] > 0]
    leveled = [(s, classify_role(s["heading"])) for s in secs]
    # 共享 structure.json 的 n_para 由 parse_manuscript 计算；此处从段落表
    # 自行统计，规避共享脚本 end_para 的已知 off-by-one（见 V2 交付说明）。
    para_counts = {}
    for p in model["paragraphs"]:
        para_counts[p["section_id"]] = para_counts.get(p["section_id"], 0) + 1
    n_para = lambda s: para_counts.get(s["id"], 0)  # noqa: E731
    body = [(s, r) for s, r in leveled if r not in BACKMATTER]
    total_char = sum(s["n_char"] for s, _ in body) or 1
    review = is_review_genre(insp)
    short_doc = len(leveled) <= 2

    # ---- a) 章节角色序列与逆序对 ----
    canon = [(s, r) for s, r in leveled if r in CANONICAL_ORDER]
    role_rows = [{"section_id": s["id"], "heading": s["heading"], "level": s["level"],
                  "role": r, "order": s["order"], "n_para": n_para(s),
                  "n_char": s["n_char"],
                  "share": round(s["n_char"] / total_char, 3) if r not in BACKMATTER else None}
                 for s, r in leveled]
    inversions = []
    for i in range(len(canon)):
        for j in range(i + 1, len(canon)):
            oi, oj = CANONICAL_ORDER.index(canon[i][1]), CANONICAL_ORDER.index(canon[j][1])
            if oj < oi:
                inversions.append({"before": {"heading": canon[i][0]["heading"], "role": canon[i][1]},
                                   "after": {"heading": canon[j][0]["heading"], "role": canon[j][1]},
                                   "pair": f"{canon[j][1]} 先于 {canon[i][1]}"})
    for inv in inversions[:6]:
        tgt = inv["before"]
        sev = "high" if (inv["before"]["role"] in ("method", "results", "conclusion", "experiment")
                         or inv["after"]["role"] == "conclusion") else "medium"
        add("章节顺序与论证顺序倒置", inv["after"]["heading"], None, None,
            inv["after"]["heading"],
            f"章节角色序列表出现逆序对：{inv['pair']}（规范序 {CANONICAL_ORDER}），"
            "读者尚未获得方法/证据即看到结果或结论，信息释放顺序不服务论证。",
            "move", f"将「{inv['after']['heading']}」移至「{tgt['heading']}」之后，"
                    "恢复 引言→方法→实验/结果→讨论→结论 的论证顺序；若为期刊模板要求请在报告中说明。",
            sev, 0.7 if not short_doc else 0.55)

    # ---- b) 核心章节缺失 ----
    present = {r for _, r in leveled}
    core_missing = []
    if "introduction" not in present:
        core_missing.append(("introduction", "引言", "add", "补充独立「引言」章节：交代研究背景、缺口与本文目标。"))
    if "method" not in present:
        core_missing.append(("method", "方法", "add",
                             "补充独立「方法/材料与方法」章节：使结果可复现；或将结果章中的制备/测试细节移出组建方法章。"))
    if "results" not in present and "experiment" not in present:
        core_missing.append(("results", "结果", "add", "补充独立「结果」章节：以数据/图表锚点呈现主要发现。"))
    if "conclusion" not in present:
        core_missing.append(("conclusion", "结论", "add",
                             "补充独立「结论」章节：回应引言提出的问题，说明主要发现与适用范围。"))
    if review:  # 综述类文体不设方法/结果章属正常
        core_missing = [x for x in core_missing if x[0] not in ("method", "results")]
    for role, name, op, instr in core_missing:
        if role not in present:
            if short_doc:
                add("核心章节疑似缺失（短文档降级提示）", "(全文)", None, None,
                    f"(全文仅 {len(leveled)} 节，未检出'{name}'类章节)",
                    f"全文仅 {len(leveled)} 个标题节，未检出{name}章。短文档可能本就如此，降级为提示。",
                    op, instr + "（若为短文/摘要体裁可忽略本条）", "low", 0.55)
            else:
                add(f"核心章节缺失：{name}", "(全文)", None, None,
                    f"(未检出'{name}'类章节标题)",
                    f"章节角色归类（标题关键词匹配）未发现{name}章节；论证链缺环，叙事顺序无法闭合。",
                    op, instr, "high", 0.6)

    # ---- c) 篇幅分析 ----
    for s, r in body:
        share = s["n_char"] / total_char
        if share > IMBALANCE and len(body) >= 3:
            add("篇幅失衡（该拆分）", s["heading"], None, None, s["heading"],
                f"该章节占正文 {share:.0%}（阈值 {IMBALANCE:.0%}），其他章节合计仅 "
                f"{1 - share:.0%}；可能混入应拆分/后移/移附录的内容。",
                "split", f"审读「{s['heading']}」：按主题拆分为 2-3 个小节，细节性内容（参数、推导、附加数据）"
                        "移入附录或方法章。",
                "medium", 0.65)
        if r == "introduction" and share > INTRO_MAX:
            add("铺垫过长（细节应后移）", s["heading"], None, None, s["heading"],
                f"引言占正文 {share:.0%}（阈值 {INTRO_MAX:.0%}），背景铺陈挤压了方法与结果的篇幅。",
                "move", "将引言中的技术细节、文献细节移至相关工作/方法章；引言只保留缺口—目标—贡献路线。",
                "medium", 0.65)
    method_secs = [s for s, r in body if r == "method"]
    if method_secs and not review:
        m_share = sum(s["n_char"] for s in method_secs) / total_char
        has_results = any(r in ("results", "experiment") for _, r in body)
        if m_share < METHOD_THIN and has_results:
            add("方法过薄（结果无从复现）", method_secs[0]["heading"], None, None,
                method_secs[0]["heading"],
                f"方法章占正文 {m_share:.1%}（下限 {METHOD_THIN:.0%}）而结果章存在："
                "结果缺乏可复现的方法支撑，叙事上“怎么得到的”缺失。",
                "add", "扩充方法章：样品制备、测试条件、评价指标、统计方式；或把散见于结果章的方法性描述移回本章。",
                "medium", 0.6)

    # ---- d) 标题层级 ----
    prev = None
    for s in secs:
        if prev is not None and s["level"] - prev > 1:
            add("标题层级跳变", s["heading"], None, None, s["heading"],
                f"标题层级由 H{prev} 直接跳到 H{s['level']}，中间层级缺失，目录层级关系断裂。",
                "reorder", f"补齐 H{prev + 1} 中间层级标题，或将「{s['heading']}」调整为 H{prev + 1}。",
                "low", 0.7)
        prev = s["level"]
    seen = {}
    for s, r in leveled:
        key = (s["level"], re.sub(r"\s+", "", s["heading"]).lower())
        if key in seen and r not in BACKMATTER:
            add("同级重复标题（合并候选）", s["heading"], None, None, s["heading"],
                f"与「{seen[key]['heading']}」（{seen[key]['id']}）同为 H{s['level']} 且标题名相同，"
                "两个同名章节并存使叙事线断裂。",
                "merge", f"将「{s['heading']}」（{s['id']}）并入「{seen[key]['heading']}」（{seen[key]['id']}），"
                        "或改名以区分二者职责。",
                "low", 0.6)
        else:
            seen[key] = s
    for i, (s, r) in enumerate(leveled):
        if n_para(s) == 0 and i > 0 and r not in BACKMATTER:
            nxt = leveled[i + 1][0]["heading"] if i + 1 < len(leveled) else "（文末）"
            add("空章节", s["heading"], None, None, s["heading"],
                f"「{s['heading']}」（{s['id']}）下没有任何段落，其内容与后文「{nxt}」的关系悬空。",
                "add", f"向「{s['heading']}」补入内容，或将其标题删除/并入「{nxt}」。",
                "low", 0.6)

    # ---- f) 结果/结论章混入大段方法性描述（先于缩写扫描执行，避免被上限挤掉） ----
    leak_roles = ("results", "discussion", "conclusion")
    leak_hits = 0
    for p in model["paragraphs"]:
        if leak_hits >= 3 or n >= MAX_FINDINGS:
            break
        if classify_role(p["section"]) not in leak_roles:
            continue
        cue_sents = [s for s in model["sentences"]
                     if s["para_id"] == p["id"] and METHOD_LEAK.search(s["text"])]
        if len(cue_sents) >= 2:
            leak_hits += 1
            first = cue_sents[0]
            add("方法性描述混入结果章（应后移）", p["section"], p["id"], first["id"],
                first["text"],
                f"结果/结论章段落 {p['id']} 含 {len(cue_sents)} 句方法性描述"
                f"（采用/步骤/配置为等提示词），打断“结果先行”的叙事节奏，且与方法章职责重复。",
                "move", "将该段方法性描述移至方法章（或附录），结果章只保留指向性一句"
                        "（“采用 X 法，详见第 Y 节”）。",
                "medium", 0.6)

    # ---- e) 信息释放顺序：缩写首现未定义 ----
    body_sents = [s for s in model["sentences"]
                  if classify_role(s["section"]) not in BACKMATTER]
    abbr_rows, first_seen = [], {}
    for s in body_sents:
        for m in ABBR_RE.finditer(s["text"]):
            a = m.group(0)
            if a in ABBR_STOP or a.rstrip("s") in ABBR_STOP:
                continue
            if a not in first_seen:
                first_seen[a] = s
    undef_abbr = 0
    for a, s in first_seen.items():
        idx = body_sents.index(s)
        window = " ".join(x["text"] for x in body_sents[max(0, idx - 1): idx + 2])
        defined = abbrev_defined(a, window)
        abbr_rows.append({"abbr": a, "first_at": s["id"], "section": s["section"],
                          "defined_at_first": defined, "context": short(s["text"], 80)})
        if not defined and undef_abbr < MAX_UNDEF_ABBR:
            undef_abbr += 1
            add("缩写首现未定义", s["section"], s["para_id"], s["id"], s["text"],
                f"缩写 {a} 于 {s['id']} 首次出现，该句及相邻句均无"
                f"“全称（{a}）”或“{a}（全称）”定义模式；首次出现的读者无法解码。",
                "add", f"在 {a} 首次出现处补全称定义（“全称（{a}）”格式），后文直接使用缩写。",
                "low", 0.6)

    # ---- e2) 回指无前文对应 ----
    backref_hits = 0
    for s in body_sents:
        if backref_hits >= 3 or n >= MAX_FINDINGS:
            break
        if BACKREF_CUES.search(s["text"]):
            idx = body_sents.index(s)
            prev_text = " ".join(x["text"] for x in body_sents[max(0, idx - 20):idx])
            prev200 = terms(prev_text[-600:])
            ov = jaccard(terms(s["text"]), prev200)
            if ov < 0.02 and len(prev_text) > 50:
                backref_hits += 1
                add("回指无前文对应", s["section"], s["para_id"], s["id"], s["text"],
                    f"该句含回指提示词（如前所述/上述/aforementioned），但前 200 词内内容词重叠 "
                    f"Jaccard={ov:.2f}≈0，找不到其所指内容，叙事参照悬空。",
                    "add_transition", "核实回指对象：若所指内容确实缺失则补写该内容；若已出现但术语不同，"
                                     "改用与上文一致的措辞指回。",
                    "medium", 0.55)

    # ---- g) 交叉引用完整性审计（v2.0.4 新增 xref_audit；dimension=argument_chain）----
    # 引用侧：正文全部句子（排除参考文献章）正则提取；定义侧：独立图注/表注段、
    # 标题数字编号、公式编号（段末"(n)"或 \tag{n}）、参考文献条目。判据细节见
    # references/structure_rules.md 第 8 节；已知误报源见 failure_modes.md。
    XREF_FIGTAB = re.compile(r"(图|表|Figure|Fig\.?|Table)\s*(\d+)", re.I)
    XREF_EQ = re.compile(r"(?:式|公式|Eq\.?)\s*\(?\s*(\d+)\)?", re.I)
    XREF_SEC_CN = re.compile(r"第\s*(\d+)\s*[章节]")
    XREF_SEC_EN = re.compile(r"Section\s*(\d+(?:\.\d+)*)", re.I)
    XREF_CITE = re.compile(r"\[(\d+(?:\s*[-–,，]\s*\d+)*)\]")
    CAPTION_RE = re.compile(r"^\s*(图|表|Figure|Fig\.?|Table)\s*(\d+)\s*([:：])?\s*(\S.*)?$", re.I)
    EQ_TAG_RE = re.compile(r"(?:[（(]\s*(\d+)\s*[）)]\s*$|\\tag\{\s*(\d+)\s*\})")
    SENT_PUNCT_END = re.compile(r"[。！？!?]$")
    MAX_XREF_PER_TYPE = 3   # 每类 xref finding 上限（完整清单仍写入 xref_audit）

    def figtab_kind(word):
        w = word.lower()
        return "fig" if (word == "图" or w.startswith("fig")) else "tab"

    def expand_cite(body):
        """[1-3,5] → {1,2,3,5}；区间上限差 >50 视为异常不展开。"""
        nums = set()
        for part in re.split(r"[,，]", body):
            part = part.strip()
            m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                if 0 < a <= b and b - a <= 50:
                    nums.update(range(a, b + 1))
            elif part.isdigit():
                nums.add(int(part))
        return nums

    sent_by_id = {s["id"]: s for s in model["sentences"]}
    ref_sents = [s for s in model["sentences"]
                 if classify_role(s["section"]) != "references"]

    # 引用侧提取
    figtab_refs, eq_refs, sec_refs, cite_refs = {}, {}, {}, {}
    for s in ref_sents:
        t = s["text"]
        for m in XREF_FIGTAB.finditer(t):
            key = (figtab_kind(m.group(1)), int(m.group(2)))
            figtab_refs.setdefault(key, []).append(s["id"])
        for m in XREF_EQ.finditer(t):
            eq_refs.setdefault(int(m.group(1)), []).append(s["id"])
        for m in XREF_SEC_CN.finditer(t):
            sec_refs.setdefault(m.group(1), []).append(s["id"])
        for m in XREF_SEC_EN.finditer(t):
            sec_refs.setdefault(m.group(1), []).append(s["id"])
        for m in XREF_CITE.finditer(t):
            for num in expand_cite(m.group(1)):
                cite_refs.setdefault(num, []).append(s["id"])

    # 定义侧锚点：独立图注/表注段（单句段、编号后随非数字文本或冒号、无句末标点）
    figtab_defs = {}
    for p in model["paragraphs"]:
        txt = p["text"].strip()
        m = CAPTION_RE.match(txt)
        if not m or p["n_sent"] != 1:
            continue
        rest = (m.group(4) or "").strip()
        caption_like = bool(m.group(3)) or (rest and not rest[0].isdigit())
        if caption_like and not SENT_PUNCT_END.search(txt):
            figtab_defs.setdefault((figtab_kind(m.group(1)), int(m.group(2))), p["id"])
    # 公式编号锚点：段末 "(n)"/"（n）" 或 \tag{n}
    eq_defs = set()
    for p in model["paragraphs"]:
        m = EQ_TAG_RE.search(p["text"].strip())
        if m:
            eq_defs.add(int(m.group(1) or m.group(2)))
    # 章节编号锚点：标题文本开头的数字编号（含"第N章/节"写法）
    sec_nums = set()
    for s in secs:
        m = re.match(r"^\s*(\d+(?:\.\d+)*)", s["heading"])
        if m:
            sec_nums.add(m.group(1))
        m2 = re.match(r"^\s*第\s*(\d+)\s*[章节]", s["heading"])
        if m2:
            sec_nums.add(m2.group(1))
    # 参考文献条目：参考文献章内 [n] 或行首/句界后数字编号。注意 parse 会把相邻行
    # 合并为一个段落（换行丢失），故逐段 findall 而非仅匹配段首：方括号式取全部
    # [n]；非方括号式取段首或句界标点（。/. /;）后的 "n." 编号，规避 "2022." 年份。
    entry_nums, n_entries = set(), 0
    for p in model["paragraphs"]:
        if classify_role(p["section"]) != "references":
            continue
        t = p["text"].strip()
        bracketed = re.findall(r"\[(\d+)\]", t)
        if bracketed:
            entry_nums.update(int(x) for x in bracketed)
            n_entries += len(bracketed)
            continue
        ordinal = re.findall(r"(?:^|[。.;；]\s*)(\d+)\s*[.、．)]", t)
        entry_nums.update(int(x) for x in ordinal)
        n_entries += len(ordinal)

    # 审计：悬空清单
    dangling_figtab = sorted(k for k in figtab_refs if k not in figtab_defs)
    dangling_eq = sorted(k for k in eq_refs if k not in eq_defs)
    dangling_sec = sorted(k for k in sec_refs
                          if k not in sec_nums and k.split(".")[0] not in sec_nums) \
        if sec_nums else []
    dangling_cite = sorted(k for k in cite_refs if k > n_entries) if n_entries > 0 else []
    uncited = sorted(set(range(1, n_entries + 1)) - set(cite_refs)) if n_entries > 0 else []

    def xref_loc(sids):
        s = sent_by_id[sids[0]]
        return s["section"], s["para_id"], s["id"], s["text"]

    CN_KIND = {"fig": "图", "tab": "表"}
    for kind, num in dangling_figtab[:MAX_XREF_PER_TYPE]:
        sec_, pid, sid, txt = xref_loc(figtab_refs[(kind, num)])
        defined = sorted(x[1] for x in figtab_defs if x[0] == kind)
        add("图表引用悬空", sec_, pid, sid, txt,
            f"正文 {sid} 引用{CN_KIND[kind]}{num}，但全文未检出其图注/表注定义"
            f"（独立图注段）；被引{CN_KIND[kind]}编号={sorted(x[1] for x in figtab_refs if x[0] == kind)}，"
            f"已定义{CN_KIND[kind]}编号={defined}。交叉引用断裂，读者无法定位该{CN_KIND[kind]}。",
            "add", f"补定义或修正编号：若系漏排图注，补「{CN_KIND[kind]}{num} 标题」独立图注；"
                   "若编号笔误，改为已定义编号并同步正文引用。",
            "high", 0.7, dim="argument_chain")
    for num in dangling_eq[:MAX_XREF_PER_TYPE]:
        sec_, pid, sid, txt = xref_loc(eq_refs[num])
        add("公式引用悬空", sec_, pid, sid, txt,
            f"正文 {sid} 引用式({num})，但全文未检出编号为 ({num}) 的公式锚点"
            f"（段末“(n)”或 \\tag{{n}}）；已定义公式编号={sorted(eq_defs) or '无'}。",
            "add", f"补定义或修正编号：为对应公式补编号 ({num})，或将引用改为已定义编号。",
            "high", 0.7, dim="argument_chain")
    for num in dangling_sec[:MAX_XREF_PER_TYPE]:
        sec_, pid, sid, txt = xref_loc(sec_refs[num])
        add("章节引用悬空", sec_, pid, sid, txt,
            f"正文 {sid} 引用第{num}章/节（Section {num}），但标题编号集合={sorted(sec_nums)} "
            "中无此目标，跨章节呼应断裂。",
            "add", f"补定义或修正编号：确认目标章节实际编号并改正引用；若该节被删，改写为"
                   "对现有章节的指回。",
            "high", 0.7, dim="argument_chain")
    for num in dangling_cite[:MAX_XREF_PER_TYPE]:
        sec_, pid, sid, txt = xref_loc(cite_refs[num])
        add("文献引用悬空", sec_, pid, sid, txt,
            f"正文 {sid} 引用文献 [{num}]，但参考文献表仅 {n_entries} 条"
            f"（条目编号={sorted(entry_nums)}），引用编号超出文献表范围。",
            "add", f"补定义或修正编号：在参考文献表补第 [{num}] 条完整条目，或将引用编号改为"
                   "已有条目并核对所指文献。",
            "high", 0.7, dim="argument_chain")
    for num in uncited[:MAX_XREF_PER_TYPE]:
        add("文献条目未被引用", "(参考文献)", None, None,
            f"(参考文献表第 [{num}] 条)",
            f"参考文献表共 {n_entries} 条，正文引用编号集合={sorted(cite_refs)}；"
            f"第 [{num}] 条从未被正文引用，文献表与正文不呼应。",
            "narrow", f"删除第 [{num}] 条，或在正文论述其依据的位置补引 [{num}]。",
            "medium", 0.65, dim="argument_chain")
    # 编号连续性：全部被引图表均存在（该 kind 无悬空）但引用∪定义编号跳号 → low 提示
    numbering_gaps = {}
    for kind in ("fig", "tab"):
        if any(k == kind for k, _ in dangling_figtab):
            continue
        nums = sorted({x[1] for x in figtab_refs if x[0] == kind}
                      | {x[1] for x in figtab_defs if x[0] == kind})
        if nums and len(nums) != nums[-1] - nums[0] + 1:
            missing = sorted(set(range(nums[0], nums[-1] + 1)) - set(nums))
            numbering_gaps[kind] = {"present": nums, "missing": missing}
            add(f"图表编号不连续（{CN_KIND[kind]}）", "(全文)", None, None,
                f"({CN_KIND[kind]}编号序列 {nums}，缺 {missing})",
                f"全部被引{CN_KIND[kind]}均有定义，但编号在 {nums[0]}–{nums[-1]} 内缺 "
                f"{missing}；编号跳号易使读者怀疑漏图/漏表。",
                "reorder", f"将{CN_KIND[kind]}编号调整为连续（补齐缺失编号或整体重排），"
                           "并同步更新正文全部引用。",
                "low", 0.55, dim="argument_chain")

    n_figtab_refs = sum(len(v) for v in figtab_refs.values())
    xref_audit = {
        "method_note": "引用侧=正文句子（排除参考文献章）正则提取 图/表/Fig/Table/式/公式/Eq/"
                       "第N章节/Section/[n]（文献区间 [a-b] 展开）；定义侧=独立图注段（单句段、"
                       "编号后随非数字文本或冒号、无句末标点）+段末(n)/\\tag{n} 公式锚点+标题数字"
                       "编号+参考文献条目（^[n] 或行首数字）。悬空=引用编号不在定义集合；未引用="
                       "[1..n] 中未被正文引用的文献条目；连续性仅在无悬空时提示。",
        "reference_side": {
            "figtab_refs": {f"{CN_KIND[k]}{v}": sids for (k, v), sids in sorted(figtab_refs.items())},
            "equation_refs": {str(k): v for k, v in sorted(eq_refs.items())},
            "section_refs": {k: v for k, v in sorted(sec_refs.items())},
            "cited_numbers": sorted(cite_refs),
        },
        "definition_side": {
            "figtab_defs": {f"{CN_KIND[k]}{v}": pid for (k, v), pid in sorted(figtab_defs.items())},
            "equation_defs": sorted(eq_defs),
            "section_numbers": sorted(sec_nums),
            "reference_entries": n_entries,
            "entry_numbers": sorted(entry_nums),
        },
        "dangling": {
            "figtab": [f"{CN_KIND[k]}{v}" for k, v in dangling_figtab],
            "equation": dangling_eq,
            "section": dangling_sec,
            "citation": dangling_cite,
        },
        "uncited_entries": uncited,
        "numbering_gaps": numbering_gaps,
        "skipped": {
            "citation_audit": "参考文献表缺失（条目=0），文献悬空/未引用审计跳过"
            if n_entries == 0 and cite_refs else None,
            "section_audit": "标题无数字编号，章节引用悬空审计跳过"
            if not sec_nums and sec_refs else None,
        },
    }

    # ---- findings 总量截断：xref 类与原有类合并按 severity 稳定截断（≤15） ----
    if len(findings) > MAX_FINDINGS:
        sev_rank = {"high": 0, "medium": 1, "low": 2}
        findings.sort(key=lambda f: sev_rank.get(f["severity"], 3))  # Python sort 稳定
        del findings[MAX_FINDINGS:]
        for i, f_ in enumerate(findings, 1):
            f_["id"] = f"E-{i:02d}"

    # ---- 中间产物：section_map.json ----
    section_map = {
        "method_note": "角色由标题关键词归类（scanutil.ROLE_MAP）；占比=章节字符/正文总字符；"
                       "缩写定义=首现句±1句内“全称（ABBR）/ABBR（全称）”模式；阈值见 scanutil.THRESH。",
        "genre": (insp.get("constraints") or {}).get("genre"),
        "role_sequence": role_rows,
        "inversions": inversions,
        "abbrev_table": abbr_rows,
        "xref_audit": xref_audit,
        "summary": {"n_sections": len(leveled), "n_inversions": len(inversions),
                    "core_missing": [x[1] for x in core_missing if x[0] not in present],
                    "n_undefined_abbr": sum(1 for r in abbr_rows if not r["defined_at_first"]),
                    "n_xref_dangling": (len(dangling_figtab) + len(dangling_eq)
                                        + len(dangling_sec) + len(dangling_cite)),
                    "n_xref_uncited": len(uncited),
                    "n_findings": len(findings)},
    }
    with open(os.path.join(args.work, "section_map.json"), "w", encoding="utf-8") as f:
        json.dump(section_map, f, ensure_ascii=False, indent=1)

    # ---- 重组大纲草稿 ----
    L = ["# 重组大纲草稿（示例性建议，供作者对照执行；非改写稿）", "",
         "> 由 section_flow v2.0.4 依据角色归类、篇幅表与交叉引用审计生成；数据见 work/section_map.json（含 xref_audit 键）。", "",
         "## 一、现状章节序列（按出现顺序）", ""]
    for i, (s, r) in enumerate(leveled, 1):
        L.append(f"{i}. {s['heading']}（{s['id']}，H{s['level']}，角色={r}，"
                 f"{n_para(s)} 段，占正文 {(s['n_char'] / total_char):.0%}）")
    L += ["", "## 二、建议叙事顺序（按论证链）", ""]
    head_roles = ("abstract", "keywords")
    head_secs = [(s, r) for s, r in leveled if r in head_roles]
    core_secs = sorted([(s, r) for s, r in leveled if r in CANONICAL_ORDER
                        and r not in head_roles and r not in BACKMATTER],
                       key=lambda x: CANONICAL_ORDER.index(x[1]))
    tail_secs = [(s, r) for s, r in leveled if r in BACKMATTER]
    canon_doc_ids = [s["id"] for s, r in leveled
                     if r in CANONICAL_ORDER and r not in head_roles and r not in BACKMATTER]
    i = 0
    for s, r in head_secs + core_secs + tail_secs:
        i += 1
        notes = []
        if (r in CANONICAL_ORDER and r not in head_roles and r not in BACKMATTER
                and s["id"] in canon_doc_ids
                and canon_doc_ids.index(s["id"]) != i - 1 - len(head_secs)):
            notes.append("移动")
        share = s["n_char"] / total_char if r not in BACKMATTER else 0
        if share > IMBALANCE:
            notes.append("拆分")
        if n_para(s) == 0 and r not in BACKMATTER and r not in head_roles:
            notes.append("补内容或删标题")
        note = f"  ← 建议：{'、'.join(notes)}" if notes else ""
        L.append(f"{i}. {s['heading']}（{s['id']}，角色={r}）{note}")
    missing_now = [x for x in core_missing if x[0] not in present]
    if missing_now:
        L += ["", "### 需新增章节"]
        for role, name, op, instr in missing_now:
            L.append(f"- 新增「{name}」：{instr}")
    L += ["", "## 三、编辑动作汇总（对应 findings.json）", ""]
    by_op = {}
    for f_ in findings:
        by_op.setdefault(f_["action"]["op"], []).append(f_["id"])
    for op, ids in by_op.items():
        L.append(f"- `{op}`：{', '.join(ids)}")
    L += ["", "## 四、复核提示",
          "- 本大纲仅按规范叙事顺序给出去向建议；合并/拆分边界需作者通读后决定。",
          "- 若期刊模板规定章节顺序（如结果在方法前），以模板为准并在报告中说明。"]
    with open(os.path.join(args.work, "restructured_outline.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")

    save_findings(args.work, "findings_engine.json", findings)
    append_change_log(args.work, [{
        "step": "section_flow", "action": "章节结构与叙事顺序深度分析 + 交叉引用完整性审计",
        "detail": f"章节={len(leveled)} 逆序对={len(inversions)} 未定义缩写="
                  f"{section_map['summary']['n_undefined_abbr']} 深度问题 {len(findings)} 条；"
                  f"xref: figrefs={n_figtab_refs} dangling={len(dangling_figtab)} "
                  f"citerefs={len(cite_refs)} dangling={len(dangling_cite)} uncited={len(uncited)}",
        "artifact": "work/section_map.json + work/findings_engine.json + work/restructured_outline.md"}])
    print(f"[section_flow] 章节={len(leveled)} 逆序对={len(inversions)} "
          f"未定义缩写={section_map['summary']['n_undefined_abbr']} 深度findings={len(findings)} "
          f"xref: figrefs={n_figtab_refs} dangling={len(dangling_figtab)} "
          f"citerefs={len(cite_refs)} dangling={len(dangling_cite)} uncited={len(uncited)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
