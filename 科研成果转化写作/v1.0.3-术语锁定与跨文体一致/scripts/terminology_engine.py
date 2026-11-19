#!/usr/bin/env python3
"""terminology_engine.py — 术语锁定与跨文体一致引擎（v1.0.3 专属）。

子命令:
  candidates --source work/source.json [--work /app/work]
      → work/term_table_draft.json：机选术语表草稿，供 Agent 审定后另存为 work/term_table.json。
      每条: {term_id, canonical(标准说法), variants[](异写/全称/缩写), kind(zh_term/acronym/symbol),
             first_expand(bool), cross_genre{科普文章/新闻通稿/项目申报材料}, note}
      异写检测:
        a) 全称↔缩写配对（源文"全称（ABBR）"或"ABBR（全称）"）；
        b) 中文异写：相似度 ≥0.70（共享字符覆盖率/最长公共子串/编辑相似度取最大）；
        c) 大小写/连字符/空格变体：拉丁 token 归一化（去非字母数字、小写）后同键归并。
  audit --table work/term_table.json --rewrite <改写稿.md> [--more 其他产物.md ...] [--work /app/work]
      → work/terminology_audit.json + work/terminology_audit.md（人读报告，逐条定位 file:rpid）。
      检查项:
        variant_used(warn)            使用了非 canonical 的中文/符号异写 → 给出统一建议；
        acronym_not_expanded(critical) first_expand=true 的缩写全文无"全称（缩写）"或"缩写（全称）"；
        symbol_conflict(critical)     同一缩写在文中出现两种展开，或文中展开与术语表冲突；
        cross_file_inconsistent(warn) 同一概念在不同产物中的主导说法不一致；
        unlocked_change(warn)         文中出现与表内 canonical 相似度≥0.70 但未登记的"新说法"。
      exit 0 = 无 critical（PASS）；2 = 有 critical（FAIL）；1 = 输入错误。
判据与 references/terminology_rules.md 保持一致。纯 Python3 标准库。
"""
import argparse, json, os, re, sys
from difflib import SequenceMatcher

SIM_THRESHOLD = 0.70                 # 异写/新说法相似度阈值（与 references 一致）
GENRES = ["科普文章", "新闻通稿", "项目申报材料"]

RE_ZH_TERM = re.compile(r"[一-鿿]{3,10}(?:材料|电池|电解质|电极|模型|算法|蛋白|基因|细胞|体系|结构|界面|机制|器件|催化|合成|表征|性能|效应|通路|网络|光谱|晶体|合金|薄膜|纳米|复合)")
RE_ACRONYM = re.compile(r"\b[A-Z][A-Z0-9]{1,9}(?:[-/][A-Z0-9]+)*\b")
RE_LATIN = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:[-–/][A-Za-z0-9]+)*\b")
RE_FORMULA = re.compile(r"\b(?:[A-Z][a-z]?\d*(?:\.\d+)?){2,}\b")  # LiNbO3 / NCM811 / LiNi0.8Co0.1Mn0.1O2
RE_EXPAND_FW = re.compile(r"([一-鿿A-Za-z][一-鿿A-Za-z0-9. /·-]{1,30}?)[（(]\s*([A-Z][A-Z0-9]{1,9})\s*[)）]")
RE_EXPAND_RV = re.compile(r"\b([A-Z][A-Z0-9]{1,9})\s*[（(]([^（）()]{2,40})[)）]")
RE_LEAD_STRIP = re.compile(r"^(?:本研究|本工作|本文|本课题|我们|该|此|这些|通过|采用|使用|利用|基于|借助|以|将|对|在|了|的|用|由|从|和|与|及|并|其)+")
RE_UNIT_TOKEN = re.compile(r"(?i)^(?:m?s/cm|mah/g|wh/kg|w/kg|mol/l|mm?|cm|km|nm|μm|kpa|mpa|gpa|pa|ev|kev|mv|kv|ma|ms|hz|khz|mhz|rpm|wt%|vol%|at%)$")
ROMAN = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
         "A", "B", "C", "D", "E", "F", "G", "H"}


def norm_key(tok):
    """拉丁 token 归一化：小写、去非字母数字（吸收大小写/连字符/空格变体）。"""
    return re.sub(r"[^0-9a-z]", "", tok.lower())


def similarity(a, b):
    """相似度 = max(编辑相似度, 最长公共子串覆盖, 共享字符覆盖率)。"""
    if not a or not b:
        return 0.0
    sm = SequenceMatcher(None, a, b)
    ratio = sm.ratio()
    lcs = sm.find_longest_match(0, len(a), 0, len(b)).size / max(len(a), len(b))
    ca, cb = {}, {}
    for ch in a:
        ca[ch] = ca.get(ch, 0) + 1
    for ch in b:
        cb[ch] = cb.get(ch, 0) + 1
    shared = sum(min(ca.get(c, 0), cb.get(c, 0)) for c in ca)
    cover = 2.0 * shared / (len(a) + len(b))
    return max(ratio, lcs, cover)


def is_acronym(tok):
    return bool(re.fullmatch(r"[A-Z][A-Z0-9]{1,9}(?:[-/][A-Z0-9]+)*", tok))


def clean_expansion(exp):
    """清理"全称（ABBR）"捕获中混入的前导动词/虚词（如"本研究采用硫化物固态电解质"）。"""
    prev = None
    exp = exp.strip()
    while prev != exp:
        prev = exp
        exp = RE_LEAD_STRIP.sub("", exp)
    return exp.strip()


ZH_CORES = ["材料", "电池", "电解质", "电极", "模型", "算法", "蛋白", "基因", "细胞", "体系",
            "结构", "界面", "机制", "器件", "催化", "合成", "表征", "性能", "效应", "通路",
            "网络", "光谱", "晶体", "合金", "薄膜", "纳米", "复合", "沉积"]
ZH_STOP = set("的了和与及并在对将由从以为是其这那该本各等用于通过采用使用利用基借助研究"
              "表明显示发现如上说下中内间之他建都过可要把被让向到即或不没无有也还就才再又着"
              "但虽若因所而然且更最很极均皆已曾正将又再")


def zh_token_scan(full_text):
    """中文术语抽取：以核心词（电解质/电池/界面…）向右锚定，向左扩展至多 6 字修饰语，
    遇虚词/动词/标点停止。仅保留"至少一次出现在边界处"或"出现≥2 次"的候选，
    避免把跨越词界的碎片（如"物固态电解质界面"）收入。"""
    cands = {}
    for core in ZH_CORES:
        start = 0
        while True:
            i = full_text.find(core, start)
            if i < 0:
                break
            start = i + 1
            j, mod = i - 1, []
            while j >= 0 and len(mod) < 6:
                ch = full_text[j]
                if not ("一" <= ch <= "鿿") or ch in ZH_STOP:
                    break
                mod.append(ch)
                j -= 1
            term = "".join(reversed(mod)) + core
            if len(term) < 4:
                continue
            prev = full_text[j] if j >= 0 else "\n"
            boundary = not ("一" <= prev <= "鿿") or prev in ZH_STOP
            e = cands.setdefault(term, [0, False])
            e[0] += 1
            e[1] = e[1] or boundary
    out = {}
    for t, (c, b) in cands.items():
        cnt = full_text.count(t)
        if cnt >= 2 or b:
            out[t] = cnt
    return out


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def split_paragraphs(text):
    out = []
    for b in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n")):
        b = re.sub(r"^#{1,6}\s*", "", b.strip())
        if b:
            out.append(b)
    return out


def find_spans(text, form):
    """返回 form 在 text 中的匹配 span 列表；拉丁形式用词边界。"""
    spans = []
    if re.search(r"[A-Za-z0-9]", form) and not re.search(r"[一-鿿]", form):
        pat = re.compile(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % re.escape(form))
    else:
        pat = re.compile(re.escape(form))
    for m in pat.finditer(text):
        spans.append((m.start(), m.end()))
    return spans


def effective_spans(text, forms):
    """每个形式的"有效"出现：剔除被更长形式包含的匹配（如 固态电解质 之于 硫化物固态电解质）。"""
    all_spans = {}
    for f in forms:
        all_spans[f] = find_spans(text, f)
    eff = {}
    ordered = sorted(forms, key=len, reverse=True)
    for i, f in enumerate(ordered):
        longer = []
        for g in ordered[:i]:
            longer.extend(all_spans[g])
        kept = []
        for (s, e) in all_spans[f]:
            if not any(s >= ls and e <= le for (ls, le) in longer):
                kept.append((s, e))
        eff[f] = kept
    return eff


def rpid_of(para_starts, pos):
    """由全文偏移定位段落 rpid。"""
    r = 1
    for i, st in enumerate(para_starts, 1):
        if st <= pos:
            r = i
        else:
            break
    return r


# ---------------------------------------------------------------- candidates
def cmd_candidates(args):
    src = load_json(args.source)
    if not src or not src.get("paragraphs"):
        print(f"[terminology:candidates] source.json 不存在或无段落: {args.source}", file=sys.stderr)
        return 1
    paras = src["paragraphs"]
    full_text = "\n\n".join(p["text"] for p in paras)
    insp = load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    audience = insp.get("audience", "unspecified")
    expert_audience = audience == "本领域同行"

    # 1) 全文展开配对：全称（ABBR） 与 ABBR（全称）
    expansion = {}
    for m in RE_EXPAND_FW.finditer(full_text):
        expansion.setdefault(m.group(2), clean_expansion(m.group(1)))
    for m in RE_EXPAND_RV.finditer(full_text):
        expansion.setdefault(m.group(1), clean_expansion(m.group(2)))

    # 2) 拉丁 token 聚类（大小写/连字符/空格变体归并；含化学式）
    latin_groups = {}   # norm_key -> {form: count}
    for p in paras:
        fspans = [(m.start(), m.end(), m.group(0)) for m in RE_FORMULA.finditer(p["text"])]
        found = [g for _, _, g in fspans]
        for m in RE_LATIN.finditer(p["text"]):
            if any(m.start() >= s and m.end() <= e for s, e, _ in fspans):
                continue  # 已被化学式整体覆盖（如 LiNi0 之于 LiNi0.8Co0.1Mn0.1O2）
            found.append(m.group(0))
        for tok in found:
            if tok in ROMAN or len(tok) < 2 or RE_UNIT_TOKEN.match(tok):
                continue
            if not (re.search(r"\d", tok) or tok.isupper() or re.search(r"[-–/]", tok)):
                continue  # 普通英文单词跳过
            k = norm_key(tok)
            if not k:
                continue
            latin_groups.setdefault(k, {})
            latin_groups[k][tok] = latin_groups[k].get(tok, 0) + 1
    # 已作为某缩写全称/化学式登记的拉丁串不重复成条目
    latin_exp_keys = {norm_key(v) for v in expansion.values()
                      if re.search(r"[A-Za-z]", v) and not re.search(r"[一-鿿]", v)}

    # 3) 中文术语聚类（相似度 ≥0.70 的异写归并，并查集；引擎自扫描，不限于 parse_source 高频候选）
    zh_count = zh_token_scan(full_text)
    zh_terms = sorted(zh_count)
    parent = {t: t for t in zh_terms}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    sim_notes = {}
    for i in range(len(zh_terms)):
        for j in range(i + 1, len(zh_terms)):
            a, b = zh_terms[i], zh_terms[j]
            if find(a) == find(b):
                continue
            s = similarity(a, b)
            if s >= SIM_THRESHOLD and abs(len(a) - len(b)) <= 3:
                union(a, b)
                sim_notes.setdefault(find(a), []).append(f"「{a}」/「{b}」相似度 {s:.2f}")

    zh_clusters = {}
    for t in zh_terms:
        zh_clusters.setdefault(find(t), []).append(t)

    # 4) 若中文聚类含某缩写的全称 → 并入该缩写条目
    entries = []
    used_zh = set()

    def pick_zh_canonical(members):
        return sorted(members, key=lambda t: (-zh_count.get(t, 1), -len(t)))[0]

    for k, forms in sorted(latin_groups.items(), key=lambda kv: -sum(kv[1].values())):
        if k in latin_exp_keys:
            continue  # 该拉丁串是某缩写的全称/化学式，已并入对应条目
        rep = sorted(forms.items(), key=lambda kv: -kv[1])[0][0]
        kind = "acronym" if is_acronym(rep) and not re.search(r"\d", rep) else "symbol"
        # 展开名归并：cluster 内任一形式有展开即采用
        exp = None
        for f in forms:
            if f in expansion:
                exp = expansion[f]
                break
        variants = [f for f in forms if f != rep]
        note_parts = []
        if len(forms) > 1:
            note_parts.append("检测到大小写/连字符变体: " + "、".join(
                f"「{f}」×{c}" for f, c in sorted(forms.items(), key=lambda kv: -kv[1])))
        canonical = rep
        first_expand = False
        if kind == "acronym":
            if exp:
                canonical = exp
                variants = [rep] + [f for f in variants if f != exp]
                first_expand = not expert_audience
            else:
                note_parts.append("源文未给全称：不得猜测，科普/通稿建议用中文描述性说法替换并标待确认")
        # 并入与全称相同/高度相似的中文聚类
        if exp:
            for root, members in zh_clusters.items():
                if root in used_zh:
                    continue
                if exp in members or any(similarity(m, exp) >= SIM_THRESHOLD for m in members):
                    for m in members:
                        if m != exp and m not in variants:
                            variants.append(m)
                    used_zh.add(root)
                    extra = [m for m in members if m != exp]
                    if extra:
                        note_parts.append("检测到中文异写: " + "、".join(f"「{m}」" for m in extra))
                    break
        if kind == "symbol" and exp and exp not in variants and exp != canonical:
            variants.append(exp)
            note_parts.append(f"源文全称/化学式写作「{exp}」：全文二选一锁定，不得混用")
        if kind == "symbol":
            note_parts.append("材料/化学式类符号：全文保持同一写法；科普文体建议首次给中文名或说明")
        cg = cross_genre_for(kind, canonical, rep, exp)
        entries.append({"term_id": "", "canonical": canonical, "variants": variants,
                        "kind": kind, "first_expand": first_expand,
                        "cross_genre": cg, "note": "；".join(note_parts)})

    # 5) 剩余中文聚类独立成条目
    for root, members in sorted(zh_clusters.items(),
                                key=lambda kv: -sum(zh_count.get(m, 1) for m in kv[1])):
        if root in used_zh:
            continue
        canonical = pick_zh_canonical(members)
        variants = [m for m in members if m != canonical]
        note_parts = []
        if variants:
            note_parts.append("疑似异写（相似度≥%.2f），请人工确认后收敛" % SIM_THRESHOLD)
            note_parts.extend(sim_notes.get(root, []))
        entries.append({"term_id": "", "canonical": canonical, "variants": variants,
                        "kind": "zh_term", "first_expand": False,
                        "cross_genre": cross_genre_for("zh_term", canonical, None, None),
                        "note": "；".join(note_parts)})

    for i, e in enumerate(entries, 1):
        e["term_id"] = "T%03d" % i

    draft = {"meta": {"audience": audience, "sim_threshold": SIM_THRESHOLD,
                      "n_terms": len(entries),
                      "hint": "机选草稿：请 Agent 逐条审定 canonical/variants/first_expand/cross_genre "
                              "后另存为 work/term_table.json（可增删改），audit 只认审定后的表。"},
             "terms": entries}
    op = os.path.join(args.work, "term_table_draft.json")
    os.makedirs(args.work, exist_ok=True)
    with open(op, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False, indent=2)
    n_var = sum(1 for e in entries if e["variants"])
    print(f"[terminology:candidates] 术语条目={len(entries)}（含异写 {n_var} 条）"
          f" audience={audience} -> {op}")
    return 0


def cross_genre_for(kind, canonical, rep, exp):
    if kind == "acronym" and exp:
        return {"科普文章": f"首次写「{exp}（{rep}）」并给一句通俗解释，之后可用「{rep}」或中文简称",
                "新闻通稿": f"首次写「{exp}（{rep}）」，之后可用「{rep}」",
                "项目申报材料": f"保留「{rep}」，首次出现展开一次即可"}
    if kind == "acronym":
        return {"科普文章": "源文未给全称：用中文描述性说法替换，全称标待确认（不得猜测）",
                "新闻通稿": "用中文描述性说法替换，全称标待确认",
                "项目申报材料": f"保留「{canonical}」，并标待确认全称"}
    if kind == "symbol":
        return {"科普文章": f"保留「{canonical}」，首次出现附中文名/通俗说明（无中文名则标待确认）",
                "新闻通稿": f"保留「{canonical}」，必要时附中文名",
                "项目申报材料": "保留"}
    return {"科普文章": f"统一用「{canonical}」，首次出现给一句解释或类比",
            "新闻通稿": f"统一用「{canonical}」",
            "项目申报材料": "保留"}


# ---------------------------------------------------------------- audit
def load_table(path):
    data = load_json(path)
    if data is None:
        return None
    if isinstance(data, dict):
        return data.get("terms") or []
    return data


def cmd_audit(args):
    table = load_table(args.table)
    if table is None or not isinstance(table, list):
        print(f"[terminology:audit] 术语表不可解析: {args.table}", file=sys.stderr)
        return 1
    files = [args.rewrite] + (args.more or [])
    texts = {}
    for fp in files:
        if not os.path.exists(fp):
            print(f"[terminology:audit] 文件不存在: {fp}", file=sys.stderr)
            return 1
        with open(fp, encoding="utf-8") as f:
            texts[fp] = f.read().replace("\r\n", "\n")

    # 表内已知形式全集
    known_forms = set()
    for e in table:
        known_forms.add(e.get("canonical", ""))
        known_forms.update(e.get("variants") or [])
    known_forms.discard("")

    issues = []
    per_file = {}
    dominant = {}   # term_id -> {file: form}

    for fp in files:
        text = texts[fp]
        tag = os.path.basename(fp)
        paras = split_paragraphs(text)
        starts, off = [], 0
        for p in paras:
            idx = text.find(p, off)
            starts.append(idx if idx >= 0 else off)
            off = (idx if idx >= 0 else off) + len(p)

        def loc(pos):
            return f"{tag}:R{rpid_of(starts, pos):03d}"

        # 1) 缩写展开冲突（全文扫描两种写法）
        exp_map = {}
        for m in RE_EXPAND_FW.finditer(text):
            exp_map.setdefault(m.group(2), set()).add(
                re.sub(r"\s+", "", clean_expansion(m.group(1))))
        for m in RE_EXPAND_RV.finditer(text):
            exp_map.setdefault(m.group(1), set()).add(
                re.sub(r"\s+", "", clean_expansion(m.group(2))))
        table_exp = {}
        for e in table:
            if e.get("kind") == "acronym":
                acr = next((v for v in [e.get("canonical", "")] + (e.get("variants") or [])
                            if is_acronym(v)), None)
                zh = next((v for v in [e.get("canonical", "")] + (e.get("variants") or [])
                           if re.search(r"[一-鿿]", v)), None)
                if acr and zh:
                    table_exp[acr] = re.sub(r"\s+", "", zh)
        def same_exp(a, b):
            """后缀包含视为同一展开（"…之一是硫化物固态电解质" ⊇ "硫化物固态电解质"）。"""
            return a == b or a.endswith(b) or b.endswith(a)

        for acr, exps in exp_map.items():
            all_exps = set(exps)
            if acr in table_exp:
                all_exps.add(table_exp[acr])
            distinct = []
            for e in sorted(all_exps, key=len, reverse=True):
                if not any(same_exp(e, d) for d in distinct):
                    distinct.append(e)
            if len(distinct) > 1:
                pos = text.find(acr)
                issues.append({"severity": "critical", "type": "symbol_conflict",
                               "file": tag, "location": loc(pos if pos >= 0 else 0),
                               "detail": f"缩写 {acr} 出现多种展开: {'、'.join(sorted(distinct))}"
                                         + (f"（术语表登记: {table_exp[acr]}）" if acr in table_exp else ""),
                               "suggestion": "全文只保留术语表登记的一种展开"})

        # 2) 逐条术语核查
        for e in table:
            tid = e.get("term_id", "?")
            canonical = e.get("canonical", "")
            variants = e.get("variants") or []
            forms = [canonical] + [v for v in variants if v != canonical]
            forms = [f for f in forms if f]
            eff = effective_spans(text, forms)
            counts = {f: len(sp) for f, sp in eff.items()}

            acr_form = next((f for f in forms if is_acronym(f)), None)
            # variant_used：非缩写形式被使用 → warn（缩写形式由展开规则单独处理）
            for f in forms:
                if f == canonical or f == acr_form:
                    continue
                if counts.get(f):
                    first = eff[f][0][0]
                    issues.append({"severity": "warn", "type": "variant_used",
                                   "file": tag, "location": loc(first),
                                   "detail": f"{tid} 使用异写「{f}」{counts[f]} 次"
                                             f"（标准说法: 「{canonical}」）",
                                   "suggestion": f"统一改为「{canonical}」"
                                                 + ("（在术语表中锁定，勿逐处手改口径）")})
            # acronym_not_expanded
            if acr_form and counts.get(acr_form):
                first = eff[acr_form][0][0]
                if e.get("first_expand"):
                    pat1 = re.search(r"[（(]\s*%s\s*[)）]" % re.escape(acr_form), text)
                    pat2 = re.search(r"%s\s*[（(][^（）()]{2,40}[)）]" % re.escape(acr_form), text)
                    if not (pat1 or pat2):
                        issues.append({"severity": "critical", "type": "acronym_not_expanded",
                                       "file": tag, "location": loc(first),
                                       "detail": f"{tid} 缩写「{acr_form}」首次出现未展开"
                                                 f"（标准说法: 「{canonical}」）",
                                       "suggestion": f"首次出现写「{canonical}（{acr_form}）」，"
                                                     f"之后可用缩写；或按 cross_genre 建议替换"})
            # 记录主导形式（跨文件一致性用）
            used = {f: c for f, c in counts.items() if c > 0}
            if used:
                dom = sorted(used.items(), key=lambda kv: (-kv[1], len(kv[0])))[0][0]
                dominant.setdefault(tid, {})[tag] = dom

        # 3) unlocked_change：未登记但与 canonical 高度相似的新说法
        cands = set()
        for m in RE_ZH_TERM.finditer(text):
            cands.add(m.group(0))
        for m in RE_LATIN.finditer(text):
            tok = m.group(0)
            if tok not in ROMAN and len(tok) >= 2 and (
                    re.search(r"\d", tok) or tok.isupper() or re.search(r"[-–/]", tok)):
                cands.add(tok)
        reported = set()
        for tok in sorted(cands):
            if tok in known_forms or tok in reported:
                continue
            if any(tok in kf or kf in tok for kf in known_forms if len(kf) >= 3):
                continue  # 与已知形式互为子串，视为覆盖
            best, best_s = None, 0.0
            for e in table:
                s = similarity(tok, e.get("canonical", ""))
                if s > best_s:
                    best, best_s = e, s
            if best and best_s >= SIM_THRESHOLD:
                pos = text.find(tok)
                issues.append({"severity": "warn", "type": "unlocked_change",
                               "file": tag, "location": loc(pos if pos >= 0 else 0),
                               "detail": f"出现未登记说法「{tok}」，与 {best.get('term_id')} "
                                         f"「{best.get('canonical')}」相似度 {best_s:.2f}",
                               "suggestion": "若为同一概念：改用 canonical 并把该说法补进术语表 "
                                             "variants；若为新概念：作为新条目补入术语表"})
                reported.add(tok)

        per_file[tag] = {"n_paragraphs": len(paras), "n_chars": len(re.sub(r"\s", "", text))}

    # 4) cross_file_inconsistent：同一概念在不同产物主导说法不同
    if len(files) > 1:
        for e in table:
            tid = e.get("term_id", "?")
            doms = dominant.get(tid, {})
            forms_used = set(doms.values())
            if len(doms) >= 2 and len(forms_used) > 1:
                detail = "；".join(f"{tag} 主导用「{f}」" for tag, f in sorted(doms.items()))
                issues.append({"severity": "warn", "type": "cross_file_inconsistent",
                               "file": "+".join(sorted(doms)), "location": "跨产物",
                               "detail": f"{tid}（{e.get('canonical')}）跨产物说法不一致: {detail}",
                               "suggestion": f"各产物统一以「{e.get('canonical')}」为基准说法，"
                                             f"按 cross_genre 栏执行该文体的替换策略"})

    n_crit = sum(1 for i in issues if i["severity"] == "critical")
    n_warn = sum(1 for i in issues if i["severity"] == "warn")
    verdict = "PASS" if n_crit == 0 else "FAIL"
    report = {"verdict": verdict, "n_critical": n_crit, "n_warn": n_warn,
              "files": list(texts), "n_terms": len(table),
              "issues": issues, "per_file": per_file}
    os.makedirs(args.work, exist_ok=True)
    with open(os.path.join(args.work, "terminology_audit.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    lines = ["# 术语一致性审计报告", "",
             f"- 判定：**{verdict}**（critical {n_crit} / warn {n_warn}）",
             f"- 术语表条目：{len(table)}；审计产物 {len(files)} 个："
             + "、".join(os.path.basename(x) for x in files), ""]
    if issues:
        lines += ["## 问题清单（逐条定位）", ""]
        for i, it in enumerate(issues, 1):
            lines.append(f"{i}. [{it['severity']}] **{it['type']}** @ `{it['location']}`")
            lines.append(f"   - 问题：{it['detail']}")
            lines.append(f"   - 建议：{it['suggestion']}")
    else:
        lines.append("全部术语使用与锁定术语表一致。")
    lines += ["", "## 判定口径", "",
              "- critical（acronym_not_expanded / symbol_conflict）必须修复后重跑 audit 至 exit=0；",
              "- warn（variant_used / cross_file_inconsistent / unlocked_change）逐条统一，"
              "或修订术语表后重跑（术语统一必须走术语表，不得逐处手改口径）。"]
    with open(os.path.join(args.work, "terminology_audit.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[terminology:audit] verdict={verdict} critical={n_crit} warn={n_warn} "
          f"files={len(files)} terms={len(table)}")
    return 0 if verdict == "PASS" else 2


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("candidates")
    p1.add_argument("--source", required=True)
    p1.add_argument("--work", default="/app/work")
    p2 = sub.add_parser("audit")
    p2.add_argument("--table", required=True)
    p2.add_argument("--rewrite", required=True)
    p2.add_argument("--more", nargs="*", default=[])
    p2.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    if args.cmd == "candidates":
        return cmd_candidates(args)
    return cmd_audit(args)


if __name__ == "__main__":
    sys.exit(main())
