#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""alignment_engine.py — 目标—内容—路线—指标对应矩阵引擎（grant-alignment-matrix 专属）。

子命令：
  seed  —— 解析 work/draft.json 四节（研究目标/研究内容/技术路线/考核指标）编号条目
            → work/alignment_seed.json（sections/counts/notes），打印计数，
            供 Agent 写作前自查条目数设计（幂等，写完 sections 后可重跑）
  audit —— 跨节条目 trigram 相似度矩阵 + 覆盖规则 + 数量一致性 + 缺节审计
            → work/alignment_matrix.json + work/findings.json
            （report_builder 自动合并 findings.json）；传 --out 另写
            <out>/alignment_table.md（四节条目×对应关系 Markdown 表）

判据设计见 references/alignment_method.md。只读 work/ 下文件，幂等可重跑。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu  # noqa: E402

ENGINE = "alignment_engine"

# 对应判定阈值：跨节条目 trigram_jaccard ≥ 0.12 视为"对应"。
# 依据：中文 3-gram 对同义改写敏感，阈值取低不取高，宁可由 Agent 复核误报，
# 不可漏报真实孤儿；依据与误报来源见 references/alignment_method.md。
SIM_THRESHOLD = 0.12

SEC_GOAL, SEC_CONTENT, SEC_ROUTE, SEC_METRIC = \
    "研究目标", "研究内容", "技术路线", "考核指标"
SECTIONS = [SEC_GOAL, SEC_CONTENT, SEC_ROUTE, SEC_METRIC]

# 考核指标节识别：element 直接命名，或 研究目标 节中含指标信号的段落
METRIC_ELEMENTS = {"考核指标", "预期成果"}
METRIC_SIGNALS = ["指标", "考核", "预期"]

# 编号条目行首模式：1. / 1、 / 1) / （1）/ （一）/ ① / 目标一 / 内容一 /
# 步骤一 / 指标一 / 第一条（中文数字括号体例为兼容扩展，见 references）
ITEM_RE = re.compile(
    r"^\s*(?:"
    r"(?P<num>\d+)\s*[\.、）\)]"
    r"|[（(]\s*(?P<num_paren>\d+)\s*[）)]"
    r"|[（(]\s*(?P<cn_paren>[一二三四五六七八九十]+)\s*[）)]"
    r"|(?P<circ>[①-⑨])"
    r"|(?P<prefix>目标|内容|步骤|指标)\s*(?P<cn>[一二三四五六七八九])"
    r"|第\s*(?P<cn_tiao>[一二三四五六七八九十]+)\s*条"
    r")")
# 行内编号信号（用于"编号未换行"提示，不参与切分）：仅在整节只切出 1 条
# 但全文出现 ≥2 处编号信号时提示，避免把"针对研究内容（一）"类互引误报
INLINE_RE = re.compile(
    r"(?:目标|内容|步骤|指标)\s*[一二三四五六七八九]"
    r"|[（(]\s*[一二三四五六七八九十\d]{1,2}\s*[）)]"
    r"|[①-⑨]|第\s*[一二三四五六七八九十]+\s*条"
    r"|^\s*\d+\s*[\.、）\)]", re.M)

# 编号互引：条目正文显式引用他节编号（目标一/研究内容（一）/步骤2/指标三）
# 即判对应，不受同义改写影响（依据见 references/alignment_method.md）
SEC_REF_WORD = {SEC_GOAL: "目标", SEC_CONTENT: "内容",
                SEC_ROUTE: "步骤", SEC_METRIC: "指标"}
REF_RES = {sec: re.compile(word + r"\s*[（(]?\s*([一二三四五六七八九十\d]+)\s*[）)]?")
           for sec, word in SEC_REF_WORD.items()}
CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
MARK_STRIP = re.compile(r"〔[^〕]*〕")


def cn_to_int(s):
    """中文/阿拉伯序号 → int；无法解析返回 None。"""
    s = (s or "").strip()
    if s.isdigit():
        return int(s)
    if s in CN_NUM:
        return CN_NUM[s]
    if "十" in s:
        a, _, b = s.partition("十")
        return CN_NUM.get(a, 1) * 10 + CN_NUM.get(b, 0)
    return None


def sim_text(t):
    """相似度计算前剥掉证据标记，避免〔拟〕〔Fxxxx〕制造虚假重叠。"""
    return MARK_STRIP.sub("", t or "")


def normalize_marker(m):
    """把 ITEM_RE 匹配归一为可读条目 ID。"""
    if m.group("num"):
        return m.group("num")
    if m.group("num_paren"):
        return "（%s）" % m.group("num_paren")
    if m.group("cn_paren"):
        return "（%s）" % m.group("cn_paren")
    if m.group("circ"):
        return m.group("circ")
    if m.group("prefix"):
        return "%s%s" % (m.group("prefix"), m.group("cn"))
    if m.group("cn_tiao"):
        return "第%s条" % m.group("cn_tiao")
    return "?"


def is_metric_para(p):
    """考核指标节段落判定：element ∈ {考核指标,预期成果} 的全部段落，
    或 element=研究目标 且含 指标/考核/预期 信号的段落。"""
    el = p.get("element", "")
    if el in METRIC_ELEMENTS:
        return True
    if el == SEC_GOAL and any(s in (p.get("text") or "") for s in METRIC_SIGNALS):
        return True
    return False


def select_section_paras(draft):
    """draft.paragraphs → {sec: [para...]} + 各节段落数。"""
    paras = draft.get("paragraphs", []) if isinstance(draft, dict) else []
    out = {s: [] for s in SECTIONS}
    for p in paras:
        el = p.get("element", "")
        if el == SEC_GOAL:
            out[SEC_GOAL].append(p)
        elif el == SEC_CONTENT:
            out[SEC_CONTENT].append(p)
        elif el == SEC_ROUTE:
            out[SEC_ROUTE].append(p)
        if is_metric_para(p):
            out[SEC_METRIC].append(p)
    return out


def split_items(sec, paras, notes):
    """把一节段落切成编号条目 [{section,item_id,text,dpids}]。

    规则：行首命中 ITEM_RE 开新条目；未命中行并入上一条目（节内已有条目时），
    否则记节首引导语（preamble，不计入条目）。整节无编号 → 每段落整体作为
    单条目并记 note。
    """
    items, preamble = [], []
    for p in paras:
        dpid = p.get("dpid")
        for line in (p.get("text") or "").splitlines():
            line = line.rstrip()
            if not line.strip():
                continue
            m = ITEM_RE.match(line)
            if m:
                body = line[m.end():].lstrip(" ：:、.．").strip()
                items.append({"section": sec, "item_id": normalize_marker(m),
                              "text": body,
                              "dpids": [dpid] if dpid else []})
            elif items:
                items[-1]["text"] = (items[-1]["text"] + "\n" + line.strip())
                if dpid and dpid not in items[-1]["dpids"]:
                    items[-1]["dpids"].append(dpid)
            else:
                preamble.append(line.strip())
    if preamble and items:
        notes.append("「%s」节首有 %d 行无编号引导语，未计入条目"
                     % (sec, len(preamble)))
    if not items and paras:
        for i, p in enumerate(paras, 1):
            text = (p.get("text") or "").strip()
            if not text:
                continue
            items.append({"section": sec, "item_id": "段%d" % i,
                          "text": text,
                          "dpids": [p.get("dpid")] if p.get("dpid") else []})
        if items:
            notes.append("「%s」节未识别到编号条目，按段落整体作为单条目（%d 段）；"
                         "建议改用 目标一/（一）/步骤一/指标一 等行首编号体例"
                         % (sec, len(items)))
    elif len(items) == 1:
        # 行内编号提示：整节仅切出 1 条但全文有多处编号信号，疑似编号未换行
        full = "\n".join((p.get("text") or "") for p in paras)
        inline = len(INLINE_RE.findall(full))
        if inline >= 2:
            notes.append("「%s」节检测到 %d 处编号信号但仅切出 1 条，"
                         "疑似编号未换行或体例混用，请 Agent 复核"
                         % (sec, inline))
    return items


def parse_sections(work):
    """读 work/draft.json → (sections{sec:[item]}, para_counts, notes)。"""
    draft = gu.read_json(os.path.join(work, "draft.json"), None)
    notes = []
    if not draft or not draft.get("paragraphs"):
        notes.append("work/draft.json 不存在或为空：写作前首次 seed 仅给出条目"
                     "设计指引；请在 draft_builder 之后重跑 seed 自查条目数")
        notes.append("条目设计建议：研究目标 2-4 条；研究内容与研究目标一一对应；"
                     "技术路线逐条支撑研究内容；考核指标逐条回溯研究目标；"
                     "四节统一行首编号体例（目标一/（一）/步骤一/指标一）")
        return {s: [] for s in SECTIONS}, {s: 0 for s in SECTIONS}, notes
    sparas = select_section_paras(draft)
    para_counts = {s: len(ps) for s, ps in sparas.items()}
    sections = {}
    for sec in SECTIONS:
        sections[sec] = split_items(sec, sparas[sec], notes)
    return sections, para_counts, notes


def counts_of(sections):
    return {s: len(items) for s, items in sections.items()}


# ---------- seed ----------

def cmd_seed(work):
    sections, _para_counts, notes = parse_sections(work)
    counts = counts_of(sections)
    seed = {
        "note": "四节编号条目机选（供 Agent 写作前/落稿后自查条目数设计；"
                "对应关系审计请跑 audit）",
        "threshold": SIM_THRESHOLD,
        "sections": sections,
        "counts": counts,
        "notes": notes,
    }
    gu.write_json(os.path.join(work, "alignment_seed.json"), seed)
    print("[alignment seed] 目标=%d 内容=%d 路线=%d 指标=%d → "
          "work/alignment_seed.json"
          % (counts[SEC_GOAL], counts[SEC_CONTENT],
             counts[SEC_ROUTE], counts[SEC_METRIC]))
    for n in notes:
        print("[alignment seed] note: %s" % n)
    return 0


# ---------- audit ----------

def build_matrix(sections):
    """跨节条目两两比对。返回 (matches, matrix_summary)。
    matches: {(secA,secB): {idA: [(idB, score, via)]}}，
    via="sim"（trigram ≥ 阈值）或 "ref"（正文显式编号互引）。"""
    matches = {}
    by_pair = {}
    total = matched = 0
    ord_of = {sec: {i + 1: it["item_id"]
                    for i, it in enumerate(sections[sec])}
              for sec in SECTIONS}
    for i, sa in enumerate(SECTIONS):
        for sb in SECTIONS[i + 1:]:
            key = "%s×%s" % (sa, sb)
            by_pair[key] = {"total": 0, "matched": 0, "ref": 0}
            pair = {}

            def add(aid, bid, score, via, _pair=pair, _key=key):
                hits = _pair.setdefault(aid, [])
                if not any(b == bid for b, _, _ in hits):
                    hits.append((bid, score, via))

            for ia in sections[sa]:
                for ib in sections[sb]:
                    sim = gu.trigram_jaccard(sim_text(ia["text"]),
                                             sim_text(ib["text"]))
                    total += 1
                    by_pair[key]["total"] += 1
                    if sim >= SIM_THRESHOLD:
                        add(ia["item_id"], ib["item_id"], round(sim, 3), "sim")
                        by_pair[key]["matched"] += 1
                        matched += 1
            # 编号互引（双向）：条目正文出现他节编号即建立对应
            for ia in sections[sa]:
                for m in REF_RES[sb].finditer(ia["text"]):
                    o = cn_to_int(m.group(1))
                    if o in ord_of[sb]:
                        add(ia["item_id"], ord_of[sb][o], 1.0, "ref")
                        by_pair[key]["ref"] += 1
            for ib in sections[sb]:
                for m in REF_RES[sa].finditer(ib["text"]):
                    o = cn_to_int(m.group(1))
                    if o in ord_of[sa]:
                        add(ord_of[sa][o], ib["item_id"], 1.0, "ref")
                        by_pair[key]["ref"] += 1
            for hits in pair.values():
                hits.sort(key=lambda x: -x[1])
            matches[(sa, sb)] = pair
    summary = {"threshold": SIM_THRESHOLD,
               "pair_total": total, "matched": matched,
               "by_pair": by_pair,
               "similarity": "grant_utils.trigram_jaccard（中文字符 3-gram，"
                             "剥除〔…〕标记后计算）；编号互引（ref）直接判对应"}
    return matches, summary


def matched_ids(matches, sec_a, sec_b):
    """sec_a item_id → [sec_b item_id]（仅对应命中）。"""
    pair = matches.get((sec_a, sec_b), {})
    return {a: [b for b, _score, _via in hits] for a, hits in pair.items()}


def cmd_audit(work, out=None):
    sections, para_counts, notes = parse_sections(work)
    counts = counts_of(sections)
    findings = []

    # 1) 缺节
    sec_hints = {
        SEC_GOAL: "补写研究目标节（sections 文件首行 # 研究目标），条目用「目标一/二/三」编号",
        SEC_CONTENT: "补写研究内容节（首行 # 研究内容），条目与研究目标一一对应",
        SEC_ROUTE: "补写技术路线节（首行 # 技术路线），条目逐条支撑研究内容",
        SEC_METRIC: "补写考核指标节（首行 # 考核指标，或 # 预期成果），"
                    "条目逐条回溯研究目标并标〔拟〕",
    }
    missing = set()
    for sec in SECTIONS:
        if para_counts.get(sec, 0) == 0:
            missing.add(sec)
            findings.append({
                "severity": "high", "kind": "missing_section",
                "dpid": None,
                "msg": "草稿中未找到「%s」章节（无对应 element 段落）" % sec,
                "suggestion": sec_hints[sec]})

    # 2) 相似度矩阵
    matches, matrix_summary = build_matrix(sections)
    g2c = matched_ids(matches, SEC_GOAL, SEC_CONTENT)
    c2r = matched_ids(matches, SEC_CONTENT, SEC_ROUTE)
    # metric→goal 为 (研究目标,考核指标) 对的反向映射
    m2g = {}
    for gid, mids in matched_ids(matches, SEC_GOAL, SEC_METRIC).items():
        for mid in mids:
            m2g.setdefault(mid, []).append(gid)
    coverage = {"goal_to_content": g2c, "content_to_route": c2r,
                "metric_to_goal": m2g}

    # 3) 覆盖规则（孤儿条目；缺节时跳过，避免与 missing_section 重复轰炸）
    def orphan(sec_items, cov_map, kind, msg_tmpl, sugg):
        for it in sec_items:
            if not cov_map.get(it["item_id"]):
                findings.append({
                    "severity": "medium", "kind": kind,
                    "dpid": (it.get("dpids") or [None])[0],
                    "msg": msg_tmpl % it["item_id"],
                    "suggestion": sugg})
    if SEC_GOAL not in missing and SEC_CONTENT not in missing:
        orphan(sections[SEC_GOAL], g2c, "orphan_goal",
               "研究目标「%s」无任何对应研究内容条目（相似度 < %.2f）"
               % ("%s", SIM_THRESHOLD),
               "为该目标补写对应研究内容条目，或在内容条目中显式呼应目标措辞"
               "（共享关键术语）；若为同义改写误报，Agent 复核后驳回并写理由")
    if SEC_CONTENT not in missing and SEC_ROUTE not in missing:
        orphan(sections[SEC_CONTENT], c2r, "orphan_content",
               "研究内容「%s」无任何对应技术路线条目（相似度 < %.2f）"
               % ("%s", SIM_THRESHOLD),
               "在技术路线节补写针对该内容的步骤条目（步骤X：针对研究内容X…），"
               "或在路线条目中显式引用内容编号与关键术语")
    if SEC_METRIC not in missing and SEC_GOAL not in missing:
        orphan(sections[SEC_METRIC], m2g, "orphan_metric",
               "考核指标「%s」无法回溯到任何研究目标（相似度 < %.2f）"
               % ("%s", SIM_THRESHOLD),
               "删除另起炉灶的指标，或改写为与研究目标条目同源的考核表述"
               "（指标X 对应 目标X）")

    # 4) 数量一致性（两侧均非缺节时才比较，缺节已由 missing_section 报告）
    if SEC_GOAL not in missing and SEC_CONTENT not in missing \
            and counts[SEC_GOAL] != counts[SEC_CONTENT]:
        findings.append({
            "severity": "high", "kind": "count_mismatch",
            "dpid": None,
            "msg": "目标 %d 条、内容 %d 条，数量不一致（应一一对应）"
                   % (counts[SEC_GOAL], counts[SEC_CONTENT]),
            "suggestion": "增删条目使研究目标与研究内容一一对应后，"
                          "重跑 draft_builder 与本审计"})
    if SEC_CONTENT not in missing and SEC_ROUTE not in missing \
            and counts[SEC_CONTENT] != counts[SEC_ROUTE]:
        findings.append({
            "severity": "high", "kind": "count_mismatch",
            "dpid": None,
            "msg": "内容 %d 条、路线 %d 条，数量不一致（每条内容应有对应路线步骤）"
                   % (counts[SEC_CONTENT], counts[SEC_ROUTE]),
            "suggestion": "增删技术路线步骤条目使与研究内容一一对应后，"
                          "重跑 draft_builder 与本审计"})

    matrix = {"items": sections, "counts": counts,
              "matrix_summary": matrix_summary, "coverage": coverage,
              "notes": notes, "findings": findings}
    gu.write_json(os.path.join(work, "alignment_matrix.json"), matrix)
    gu.write_json(os.path.join(work, "findings.json"),
                  {"engine": ENGINE, "findings": findings})
    if out:
        gu.ensure_dir(out)
        write_alignment_table(os.path.join(out, "alignment_table.md"),
                              sections, counts, coverage, matches, findings)

    sev = {}
    for f in findings:
        sev[f["severity"]] = sev.get(f["severity"], 0) + 1
    print("[alignment audit] 目标=%d 内容=%d 路线=%d 指标=%d matches=%d "
          "findings=%d %s"
          % (counts[SEC_GOAL], counts[SEC_CONTENT], counts[SEC_ROUTE],
             counts[SEC_METRIC], matrix_summary["matched"], len(findings),
             " ".join("%s=%d" % kv for kv in sorted(sev.items())) or "(clean)"))
    return 0


# ---------- alignment_table.md ----------

def cell(text, width=42):
    t = re.sub(r"\s+", " ", (text or "")).replace("|", "｜").strip()
    return t[:width] + ("…" if len(t) > width else "")


def item_label(sec_items, item_id):
    for it in sec_items:
        if it["item_id"] == item_id:
            return "%s %s" % (it["item_id"], cell(it["text"], 30))
    return item_id


def write_alignment_table(path, sections, counts, coverage, matches, findings):
    L = ["# 目标—内容—路线—指标对应矩阵（alignment_table）", "",
         "- 生成：`alignment_engine.py audit`；对应判据：trigram Jaccard ≥ %.2f"
         % SIM_THRESHOLD,
         "- 计数：研究目标 %d 条 / 研究内容 %d 条 / 技术路线 %d 条 / 考核指标 %d 条"
         % (counts[SEC_GOAL], counts[SEC_CONTENT],
            counts[SEC_ROUTE], counts[SEC_METRIC]), ""]
    # 一、以研究目标为锚的对应总表
    L += ["## 一、对应总表（以研究目标为锚）", "",
          "| 研究目标 | 对应研究内容 | 对应技术路线（经内容传递或直接匹配） | 对应考核指标 |",
          "|---|---|---|---|"]
    g2r_direct = matched_ids(matches, SEC_GOAL, SEC_ROUTE)
    for g in sections[SEC_GOAL]:
        gid = g["item_id"]
        cs = coverage["goal_to_content"].get(gid, [])
        rs = set(g2r_direct.get(gid, []))
        for cid in cs:
            rs.update(coverage["content_to_route"].get(cid, []))
        ms = [m["item_id"] for m in sections[SEC_METRIC]
              if gid in coverage["metric_to_goal"].get(m["item_id"], [])]
        L.append("| %s | %s | %s | %s |" % (
            item_label(sections[SEC_GOAL], gid),
            "；".join(item_label(sections[SEC_CONTENT], c) for c in cs) or "—",
            "；".join(item_label(sections[SEC_ROUTE], r) for r in sorted(rs)) or "—",
            "；".join(item_label(sections[SEC_METRIC], m) for m in ms) or "—"))
    # 二、四节条目清单
    L += ["", "## 二、四节条目清单", ""]
    for sec in SECTIONS:
        L.append("### %s（%d 条）" % (sec, counts[sec]))
        L += ["", "| 条目 | 文本摘要 | 草稿段 |", "|---|---|---|"]
        if not sections[sec]:
            L.append("| — | （缺节） | — |")
        for it in sections[sec]:
            L.append("| %s | %s | %s |"
                     % (it["item_id"], cell(it["text"]),
                        "、".join(d for d in it.get("dpids", []) if d) or "—"))
        L.append("")
    # 三、孤儿与缺节
    L += ["## 三、审计发现（findings）", ""]
    if findings:
        L += ["| 级别 | 类型 | 说明 |", "|---|---|---|"]
        for f in findings:
            L.append("| %s | %s | %s |"
                     % (f.get("severity"), f.get("kind"), cell(f.get("msg"), 60)))
    else:
        L.append("无 finding：四节条目数量一致、覆盖完整。")
    L += ["", "> 本表由 alignment_engine.py 自动生成；同义改写导致的低相似"
          "孤儿为候选误报，以 Agent 复核结论为准。", ""]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def main():
    ap = argparse.ArgumentParser(description="目标—内容—路线—指标对应矩阵引擎")
    ap.add_argument("cmd", choices=["seed", "audit"])
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", default=None, help="audit 可选：另写 <out>/alignment_table.md")
    args = ap.parse_args()
    if args.cmd == "seed":
        return cmd_seed(args.work)
    return cmd_audit(args.work, out=args.out)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print("[alignment_engine] ERROR: %s" % e)
        raise SystemExit(1)
