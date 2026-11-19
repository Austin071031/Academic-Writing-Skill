#!/usr/bin/env python3
"""genre_engine.py — 文体转换映射与逐段对照台账引擎（v1.0.4 专属）。

子命令:
  map    --inspection work/inspection.json --source work/source.json [--work /app/work]
      → work/genre_mapping.json：按 inspection.json 的 genre 选择内置文体模板
        （科普文章/新闻通稿/项目申报材料/简报，与 references/genre_templates.md 一致），
        把源文段落按内容关键词映射到模板要素（mapping: 要素→[source_pid]），
        标出缺失要素（源文无对应 → 写作时不得编造，标注「源文未提供」）；
        genre 未识别时默认科普文章并写入 manual_confirmations。
  ledger --source work/source.json --rewrite <改写稿.md> --reasons work/change_reasons.jsonl
         [--work /app/work]
      → work/change_ledger.json + work/traceability_report.md：
        结合 work/alignment.json（先跑 align_rewrite.py）生成逐段对照台账。
        判定规则:
          - 源文段落 dropped 且 reasons 无「删除」理由 → critical；
          - 改写新增段落 reasons 未标「新增-过渡」 → warn；
          - 新增段落含数值+单位 → warn（提示核对是否源外事实）；
          - reasons 的 action 与对齐结果矛盾（如「保留」但 sim<0.12） → warn。
        verdict=PASS（无 critical）时 exit 0，否则 exit 2。
change_reasons.jsonl 每行一条:
  {"rpid":"R002","source_pid":"S001-P003","action":"保留|压缩|改写|新增-过渡","reason":"..."}
  或对删除的源文段落: {"source_pid":"S001-P005","action":"删除","reason":"..."}
"""
import argparse, json, os, re, sys

# ---------------------------------------------------------------- 文体模板
# 与 references/genre_templates.md 完全一致：要素名、关键词、写作要点。
GENRE_TEMPLATES = {
    "科普文章": [
        {"element": "标题", "kind": "title",
         "keywords": [],
         "hint": "一句话点出核心发现，可有悬念但不得夸大"},
        {"element": "引入钩子", "kind": "body",
         "keywords": ["问题", "挑战", "难题", "为什么", "想象", "设想", "假如", "一直", "困境", "瓶颈"],
         "hint": "用读者熟悉的场景或问题引出，1-2 句"},
        {"element": "背景", "kind": "body",
         "keywords": ["背景", "近年来", "随着", "已有研究", "传统", "现有", "目前", "广泛应用", "然而", "但是", "领域"],
         "hint": "交代研究领域与既有进展，为发现做铺垫"},
        {"element": "核心发现", "kind": "body",
         "keywords": ["表明", "发现", "实现", "首次", "提出", "突破", "证实", "显示", "成功", "解决"],
         "hint": "本文最重要的结论，论断强度与源文一致"},
        {"element": "关键数据", "kind": "data",
         "keywords": ["达", "提升", "提高", "降低", "下降", "保持", "相当于", "倍"],
         "hint": "支撑核心发现的关键数值，数字与单位逐值保留"},
        {"element": "意义与展望", "kind": "body",
         "keywords": ["意义", "有望", "前景", "未来", "展望", "潜力", "奠定基础", "推动", "下一步", "应用"],
         "hint": "成果价值与应用前景，「有望」不得写成「已经」"},
        {"element": "来源说明", "kind": "body",
         "keywords": ["发表", "期刊", "doi", "DOI", "论文", "作者", "单位", "课题组", "资助", "基金", "研究团队"],
         "hint": "交代论文出处/团队；源文未提供则标注「源文未提供」"},
    ],
    "新闻通稿": [
        {"element": "标题", "kind": "title",
         "keywords": [],
         "hint": "主标题点成果，可加副标题；不得使用源文没有的定性词"},
        {"element": "导语(何时何地何人何事)", "kind": "body",
         "keywords": ["近日", "日前", "记者", "团队", "课题组", "大学", "学院", "研究院", "研究所", "实验室", "发表于"],
         "hint": "首段交代何时/何地/何人/何事，四要素缺一不可；缺项标注「源文未提供」"},
        {"element": "核心成果", "kind": "body",
         "keywords": ["表明", "发现", "实现", "首次", "提出", "突破", "证实", "成功", "解决", "研制"],
         "hint": "成果一句话概括+展开，论断强度与源文一致"},
        {"element": "数据支撑", "kind": "data",
         "keywords": ["达", "提升", "提高", "降低", "下降", "保持", "相当于", "倍", "测试"],
         "hint": "关键性能数据，数字/单位/测试条件逐值保留"},
        {"element": "引语", "kind": "quote",
         "keywords": ["表示", "说道", "介绍", "指出", "认为", "强调", "告诉"],
         "hint": "研究者原话或转述；源文无引语则标注「源文未提供」，严禁虚构引语"},
        {"element": "背景", "kind": "body",
         "keywords": ["背景", "近年来", "随着", "已有研究", "传统", "现有", "目前", "然而", "长期", "领域"],
         "hint": "行业/学科背景，帮助媒体读者理解价值"},
        {"element": "联系方式占位", "kind": "body",
         "keywords": ["联系", "邮箱", "电话", "@", "通讯作者", "媒体"],
         "hint": "媒体联络占位；源文未提供一律写占位符并标注「源文未提供」"},
    ],
    "项目申报材料": [
        {"element": "立项背景", "kind": "body",
         "keywords": ["背景", "近年来", "随着", "已有研究", "传统", "现有", "目前", "广泛应用", "需求", "战略", "领域"],
         "hint": "领域需求与研究现状，引出立项必要性"},
        {"element": "科学问题", "kind": "body",
         "keywords": ["问题", "机制", "机理", "尚不清楚", "难点", "瓶颈", "挑战", "关键科学", "制约", "尚未"],
         "hint": "凝练 1-3 个关键科学问题，不得把工程指标冒充科学问题"},
        {"element": "研究内容", "kind": "body",
         "keywords": ["研究内容", "拟开展", "围绕", "针对", "研究包括", "拟解决", "开展"],
         "hint": "分条列出研究内容，每条对应科学问题"},
        {"element": "技术路线", "kind": "body",
         "keywords": ["路线", "方法", "采用", "通过", "利用", "步骤", "方案", "策略", "构建", "制备", "表征"],
         "hint": "方法-步骤-验证链条；源文方法要点必须保留"},
        {"element": "创新点", "kind": "body",
         "keywords": ["创新", "首次", "原创", "突破", "区别于", "不同于", "独有", "新颖"],
         "hint": "与现有工作的本质区别；「首次」须与源文一致"},
        {"element": "可行性", "kind": "body",
         "keywords": ["可行", "基础", "前期", "已建立", "已具备", "条件", "平台", "经验", "初步", "验证"],
         "hint": "前期工作与条件保障；初步结果保持「初步」限定"},
        {"element": "预期成果", "kind": "body",
         "keywords": ["预期", "目标", "有望", "成果", "指标", "发表", "专利", "论文", "形成"],
         "hint": "可考核的成果形式与指标；源文未给指标不得自编"},
    ],
    "简报": [
        {"element": "核心结论(1段)", "kind": "body",
         "keywords": ["表明", "发现", "实现", "首次", "突破", "证实", "显示", "结论", "成功"],
         "hint": "全文只保留 1 段结论，开门见山"},
        {"element": "关键数据(≤5条)", "kind": "data",
         "keywords": ["达", "提升", "提高", "降低", "下降", "保持", "相当于", "倍"],
         "hint": "至多 5 条数据，每条带单位与条件，逐值与源文一致"},
        {"element": "支撑要点", "kind": "body",
         "keywords": ["显示", "结果", "测试", "分析", "验证", "比较", "对照", "图", "表"],
         "hint": "支撑结论的论据要点，含图表引用时保留编号"},
        {"element": "风险与限制", "kind": "body",
         "keywords": ["局限", "限制", "风险", "不足", "有待", "仍需", "挑战", "尚未", "初步", "不确定"],
         "hint": "如实列出限制条件；源文未提供则标注「源文未提供」，不得隐匿"},
        {"element": "建议行动", "kind": "body",
         "keywords": ["建议", "下一步", "应当", "需要", "推荐", "推进", "计划", "关注"],
         "hint": "面向决策者的行动建议，不得超出源文结论范围"},
    ],
}
DEFAULT_GENRE = "科普文章"

GENRE_ALIAS = [
    (re.compile(r"科普|大众传媒|popular", re.I), "科普文章"),
    (re.compile(r"新闻|通稿|press|news", re.I), "新闻通稿"),
    (re.compile(r"项目申报|申报|基金申请|立项|proposal", re.I), "项目申报材料"),
    (re.compile(r"简报|一页纸|brief", re.I), "简报"),
]

# 数值+单位检测（用于新增段落源外事实提示；为 parse_source 单位表的常用子集）
NUM = r"[-+−]?\d+(?:\.\d+)?"
UNIT = (r"(?:nm|μm|mm|cm|km|mA|mV|kV|V|mAh/g|Wh/kg|W/kg|MPa|GPa|kPa|Pa|K|℃|°C|mol/L|mM|"
        r"Hz|kHz|MHz|GHz|ms|s|min|h|mL|μL|L|mg|μg|g|kg|wt%|vol%|at%|ppm|ppb|mol|eV|keV|rpm|倍|%|‰|例|次|年)")
RE_NUM_UNIT = re.compile(r"(%s)\s*%s" % (NUM, UNIT))

ACTIONS_RW = ("保留", "压缩", "改写", "新增-过渡")


def load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def head(text, n=42):
    t = re.sub(r"\s+", " ", text).strip()
    return t[:n] + ("…" if len(t) > n else "")


def pick_genre(insp):
    """从 inspection.genre 候选中识别目标文体；未识别返回 (默认文体, False)。"""
    cands = insp.get("genre") or []
    for g in cands:
        for pat, name in GENRE_ALIAS:
            if pat.search(str(g)):
                return name, True, cands
    return DEFAULT_GENRE, False, cands


def map_paragraphs(template, paragraphs):
    """把源文段落映射到模板要素：mapping[element]=[pid]，并给出缺失要素。"""
    mapping = {e["element"]: [] for e in template}
    headings = [p for p in paragraphs if p.get("kind") == "heading"]
    for e in template:
        el = e["element"]
        if e["kind"] == "title":
            # 标题要素：取源文标题段；无标题段则回落到「核心发现/核心成果」来源段
            if headings:
                mapping[el] = [headings[0]["pid"]]
            continue
        kws = e["keywords"]
        for p in paragraphs:
            text = p.get("text", "")
            score = sum(1 for k in kws if k in text)
            if e["kind"] == "data":
                n_data = sum(1 for f in p.get("facts", [])
                             if f.get("type") in ("number", "percent", "sample", "compare"))
                if n_data:
                    score += 2  # 含数值/比较事实的段落优先映射到数据要素
            if e["kind"] == "quote" and p.get("kind") == "quote":
                score += 2
            if score >= 1:
                mapping[el].append(p["pid"])
    # 标题要素无源文标题段时的回落
    for e in template:
        if e["kind"] == "title" and not mapping[e["element"]]:
            fallback = None
            for key in ("核心发现", "核心成果", "核心结论(1段)", "立项背景"):
                if key in mapping and mapping[key]:
                    fallback = mapping[key][0]
                    break
            if fallback:
                mapping[e["element"]] = [fallback]
            elif paragraphs:
                mapping[e["element"]] = [paragraphs[0]["pid"]]
    missing = [e["element"] for e in template if not mapping[e["element"]]]
    return mapping, missing


def cmd_map(args):
    insp = load(args.inspection, None)
    src = load(args.source, None)
    if insp is None:
        print(f"[genre:map] inspection.json 读取失败: {args.inspection}", file=sys.stderr)
        return 1
    if src is None:
        print(f"[genre:map] source.json 读取失败: {args.source}", file=sys.stderr)
        return 1
    paragraphs = src.get("paragraphs", [])
    if not paragraphs:
        print("[genre:map] source.json 无段落，请先跑 parse_source.py", file=sys.stderr)
        return 1

    genre, recognized, cands = pick_genre(insp)
    template = GENRE_TEMPLATES[genre]
    mapping, missing = map_paragraphs(template, paragraphs)

    confirmations = []
    if not recognized:
        confirmations.append({
            "item": "genre_unrecognized",
            "detail": (f"未从任务中识别出目标文体（候选：{cands or '无'}），"
                       f"已按默认「{DEFAULT_GENRE}」模板处理，请人工确认目标文体"),
            "action": "确认或改用其他模板后重跑 genre_engine.py map"})
    missing_notes = []
    for el in missing:
        note = {"element": el,
                "note": f"源文未提供「{el}」要素的支撑内容：写作时不得编造，"
                        f"在改写稿相应位置标注「源文未提供」"}
        missing_notes.append(note)
        confirmations.append({"item": f"missing_element:{el}",
                              "detail": note["note"],
                              "action": "与原作者确认是否补充材料，或在成稿中保留占位标注"})

    out = {"genre": genre, "genre_recognized": recognized,
           "genre_candidates": cands,
           "template": [{"element": e["element"], "hint": e["hint"]} for e in template],
           "mapping": mapping,
           "missing_elements": missing_notes,
           "manual_confirmations": confirmations,
           "stats": {"n_source_paragraphs": len(paragraphs),
                     "n_elements": len(template),
                     "n_mapped_elements": len(template) - len(missing),
                     "n_missing_elements": len(missing)}}
    op = os.path.join(args.work, "genre_mapping.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # manual_confirmations 落盘（与已有内容合并，幂等去重）
    if confirmations:
        mcp = os.path.join(args.work, "manual_confirmations.json")
        existing = load(mcp, []) or []
        seen = {json.dumps(x, ensure_ascii=False, sort_keys=True) for x in existing}
        for c in confirmations:
            k = json.dumps(c, ensure_ascii=False, sort_keys=True)
            if k not in seen:
                existing.append(c)
        with open(mcp, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)

    s = out["stats"]
    print(f"[genre:map] 文体={genre}{'（默认）' if not recognized else ''} "
          f"要素={s['n_elements']} 已映射={s['n_mapped_elements']} "
          f"缺失={s['n_missing_elements']}"
          + (f"：{'、'.join(missing)}" if missing else ""))
    return 0


# ---------------------------------------------------------------- ledger

def load_reasons(path):
    """读取 change_reasons.jsonl；返回 (rewrite 理由 {rpid:entry}, 删除理由 {source_pid:entry})。"""
    rw, dele = {}, {}
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError as ex:
                print(f"[genre:ledger] reasons 第 {ln} 行 JSON 解析失败: {ex}", file=sys.stderr)
                continue
            if e.get("action") == "删除" or (e.get("source_pid") and not e.get("rpid")):
                if e.get("source_pid"):
                    dele[e["source_pid"]] = e
            elif e.get("rpid"):
                rw[e["rpid"]] = e
    return rw, dele


def cmd_ledger(args):
    src = load(args.source, None)
    if src is None:
        print(f"[genre:ledger] source.json 读取失败: {args.source}", file=sys.stderr)
        return 1
    if not os.path.exists(args.rewrite):
        print(f"[genre:ledger] 改写稿不存在: {args.rewrite}", file=sys.stderr)
        return 1
    if not os.path.exists(args.reasons):
        print(f"[genre:ledger] change_reasons.jsonl 不存在: {args.reasons}", file=sys.stderr)
        return 1
    align = load(os.path.join(args.work, "alignment.json"), None)
    if align is None:
        print("[genre:ledger] 未找到 work/alignment.json，请先运行 align_rewrite.py",
              file=sys.stderr)
        return 1

    reasons_rw, reasons_del = load_reasons(args.reasons)
    paragraphs = src.get("paragraphs", [])
    links = align.get("links", [])
    rparas = align.get("rewrite_paragraphs", [])
    link_by_src = {}
    link_by_rw = {}
    for l in links:
        link_by_src.setdefault(l["source_pid"], []).append(l)
        link_by_rw[l["rpid"]] = l
    linked_rwpids = set(link_by_rw)

    issues = []

    # ---- 源文段落覆盖台账
    source_rows = []
    for p in paragraphs:
        pid = p["pid"]
        n_facts = len(p.get("facts", []))
        row = {"source_pid": pid, "source_head": head(p.get("text", "")),
               "n_facts": n_facts, "rpids": [], "relation": None,
               "action": None, "reason": None, "status": None}
        ls = link_by_src.get(pid)
        if ls:
            best = max(ls, key=lambda x: x["sim"])
            row["rpids"] = [l["rpid"] for l in ls]
            row["relation"] = best["relation"]
            row["status"] = "covered"
            r = reasons_rw.get(best["rpid"])
            if r:
                row["action"], row["reason"] = r.get("action"), r.get("reason", "")
        else:
            d = reasons_del.get(pid)
            if d:
                row["status"] = "dropped_explained"
                row["action"], row["reason"] = "删除", d.get("reason", "")
            else:
                row["status"] = "dropped_unexplained"
                sev = "critical"
                issues.append({"severity": sev, "type": "dropped_without_reason",
                               "location": pid,
                               "detail": (f"源文段落 {pid} 未被改写稿覆盖且 change_reasons.jsonl "
                                          f"中无「删除」理由（涉及事实 {n_facts} 处）："
                                          f"{row['source_head']}")})
        source_rows.append(row)

    # ---- 改写段落溯源台账
    rewrite_rows = []
    for rp in rparas:
        rpid = rp["rpid"]
        text = rp.get("text", "")
        row = {"rpid": rpid, "rewrite_head": head(text),
               "source_pid": None, "sim": None, "relation": None,
               "action": None, "reason": None,
               "n_facts": len(RE_NUM_UNIT.findall(text)), "notes": []}
        l = link_by_rw.get(rpid)
        r = reasons_rw.get(rpid)
        if r:
            row["action"], row["reason"] = r.get("action"), r.get("reason", "")
        if l:
            row["source_pid"], row["sim"], row["relation"] = l["source_pid"], l["sim"], l["relation"]
            if r and r.get("action") == "新增-过渡":
                issues.append({"severity": "warn", "type": "action_contradiction",
                               "location": rpid,
                               "detail": (f"理由称 {rpid} 为「新增-过渡」，但引擎对齐到 "
                                          f"{l['source_pid']}（sim={l['sim']}），请核实动作标注")})
                row["notes"].append("动作标注与对齐结果矛盾")
            if not r:
                row["notes"].append("缺少改写理由")
        else:
            # 新增段落
            if r and r.get("action") == "新增-过渡":
                row["notes"].append("新增-过渡（已声明）")
            elif r:
                issues.append({"severity": "warn", "type": "added_action_mismatch",
                               "location": rpid,
                               "detail": (f"改写段落 {rpid} 无源文对应（sim<0.12 判为新增），"
                                          f"但理由动作标为「{r.get('action')}」（源 "
                                          f"{r.get('source_pid', '?')}）而非「新增-过渡」，"
                                          f"请核实是否事实漂移或理由笔误")})
                row["notes"].append("新增段落未标「新增-过渡」")
            else:
                issues.append({"severity": "warn", "type": "added_without_reason",
                               "location": rpid,
                               "detail": (f"改写段落 {rpid} 为新增段落且 change_reasons.jsonl "
                                          f"未标「新增-过渡」，需确认仅为过渡/背景重述：{row['rewrite_head']}")})
                row["notes"].append("新增段落无理由")
            if RE_NUM_UNIT.search(text):
                nums = [m.group(0) for m in RE_NUM_UNIT.finditer(text)][:5]
                issues.append({"severity": "warn", "type": "added_contains_number",
                               "location": rpid,
                               "detail": (f"新增段落 {rpid} 含数值+单位（{'、'.join(nums)}），"
                                          f"请核对是否为源文外事实；若是必须删除或标注待确认")})
                row["notes"].append("新增段落含数值，需核对源外事实")
        rewrite_rows.append(row)

    # 理由称删除但源文段落仍被覆盖
    for pid, d in reasons_del.items():
        if pid in link_by_src:
            issues.append({"severity": "warn", "type": "action_contradiction",
                           "location": pid,
                           "detail": (f"理由称删除源文段落 {pid}，但其内容仍被改写段落 "
                                      f"{[x['rpid'] for x in link_by_src[pid]]} 覆盖，请核实")})

    n_critical = sum(1 for i in issues if i["severity"] == "critical")
    n_warn = sum(1 for i in issues if i["severity"] == "warn")
    verdict = "PASS" if n_critical == 0 else "FAIL"
    stats = {"n_source": len(paragraphs),
             "n_covered": sum(1 for r in source_rows if r["status"] == "covered"),
             "n_dropped_explained": sum(1 for r in source_rows if r["status"] == "dropped_explained"),
             "n_dropped_unexplained": sum(1 for r in source_rows
                                          if r["status"] == "dropped_unexplained"),
             "n_rewrite": len(rparas),
             "n_added": sum(1 for r in rewrite_rows if not r["source_pid"]),
             "n_reasons": len(reasons_rw) + len(reasons_del),
             "n_critical": n_critical, "n_warn": n_warn}
    ledger = {"verdict": verdict, "issues": issues,
              "source_coverage": source_rows, "rewrite_trace": rewrite_rows,
              "stats": stats,
              "alignment_stats": align.get("stats")}
    with open(os.path.join(args.work, "change_ledger.json"), "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)

    # ---- 人读逐段对照报告
    lines = ["# 逐段对照台账（traceability report）", "",
             f"- 判定：**{verdict}**　critical={n_critical}　warn={n_warn}",
             f"- 源文段落 {stats['n_source']} 段：已覆盖 {stats['n_covered']}、"
             f"删除（有理由）{stats['n_dropped_explained']}、"
             f"删除（无理由→critical）{stats['n_dropped_unexplained']}",
             f"- 改写段落 {stats['n_rewrite']} 段：新增 {stats['n_added']} 段；"
             f"理由记录 {stats['n_reasons']} 条", "",
             "## 一、源文段落 → 改写稿（覆盖核查）", "",
             "| 源文 pid | 原句摘要 | 改写 rpid | 覆盖状态 | 动作 | 理由 | 涉及事实数 |",
             "|-|-|-|-|-|-|-|"]
    status_zh = {"covered": "已覆盖", "dropped_explained": "删除（有理由）",
                 "dropped_unexplained": "**删除（无理由）**"}
    for r in source_rows:
        lines.append("| {pid} | {h} | {rp} | {st} | {a} | {rs} | {nf} |".format(
            pid=r["source_pid"], h=r["source_head"],
            rp="、".join(r["rpids"]) or "—",
            st=status_zh.get(r["status"], r["status"] or "—"),
            a=r["action"] or "—", rs=(r["reason"] or "—"), nf=r["n_facts"]))
    lines += ["", "## 二、改写段落 → 源文（溯源核查）", "",
              "| 改写 rpid | 摘要 | 对应源文 | sim | 动作 | 理由 | 备注 |",
              "|-|-|-|-|-|-|-|"]
    for r in rewrite_rows:
        lines.append("| {rpid} | {h} | {sp} | {sim} | {a} | {rs} | {nt} |".format(
            rpid=r["rpid"], h=r["rewrite_head"],
            sp=r["source_pid"] or "（新增）",
            sim=r["sim"] if r["sim"] is not None else "—",
            a=r["action"] or "—", rs=(r["reason"] or "—"),
            nt="；".join(r["notes"]) or "—"))
    if issues:
        lines += ["", "## 三、问题清单", ""]
        for i, it in enumerate(issues, 1):
            lines.append(f"{i}. [{it['severity']}] {it['type']}（{it['location']}）：{it['detail']}")
    else:
        lines += ["", "全部段落均可追溯，无未说明的删除或新增。"]
    with open(os.path.join(args.work, "traceability_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[genre:ledger] verdict={verdict} critical={n_critical} warn={n_warn} "
          f"源文覆盖={stats['n_covered']}/{stats['n_source']} "
          f"无理由删除={stats['n_dropped_unexplained']} 新增={stats['n_added']}")
    return 0 if verdict == "PASS" else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("map")
    p1.add_argument("--inspection", required=True)
    p1.add_argument("--source", required=True)
    p1.add_argument("--work", default="/app/work")
    p2 = sub.add_parser("ledger")
    p2.add_argument("--source", required=True)
    p2.add_argument("--rewrite", required=True)
    p2.add_argument("--reasons", required=True)
    p2.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    if args.cmd == "map":
        return cmd_map(args)
    return cmd_ledger(args)


if __name__ == "__main__":
    sys.exit(main())
