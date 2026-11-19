#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开题报告与研究计划书 质量自检脚本（七要素 / 对齐 / 排得开 / 说得清）。

用法:
  python3 validate_proposal.py /app/output/proposal.md [--profile gap|objective|roadmap|risk|delivery] [--report /app/output/validation_report.json]

退出码: 0 = 全部硬性检查通过; 1 = 存在硬性失败项; 2 = 文件不可读。
本脚本只做基于规则的一致性核验，不替代人工评审；所有结论写入 JSON 报告。
"""
import argparse
import json
import os
import re
import sys

SECTION_PATTERNS = {
    "研究背景": [r"研究背景", r"立项依据", r"背景与缺口"],
    "研究问题": [r"研究问题", r"问题定义", r"科学问题"],
    "研究目标": [r"研究目标", r"目标设定"],
    "技术路线": [r"技术路线", r"研究方法", r"研究方案"],
    "阶段计划": [r"阶段计划", r"研究计划", r"进度安排", r"里程碑", r"年度计划"],
    "风险": [r"风险", r"备选方案"],
    "预期成果": [r"预期成果", r"预期结果", r"考核方式"],
    "参考文献": [r"参考文献", r"References"],
    "人工确认与材料缺口": [r"人工确认", r"材料缺口", r"不确定性"],
    "论断来源映射": [r"论断.{0,4}来源", r"来源映射", r"证据矩阵", r"证据清单"],
}

# 证据/论断编号标记，如 〔E1〕 (E12) 〔C3〕
MARKER_RE = re.compile(r"[〔\(]\s*([EC]\d{1,3})\s*[〕\)]")
# 正文引用编号，如 [1] [23]
CITE_RE = re.compile(r"(?<![\w\)])\[(\d{1,3})\]")
DATE_HINT_RE = re.compile(r"(20\d\d\s*年|第\s*\d+\s*[个月季度]|[MQ]\d|20\d\d[-/.]Q[1-4]|季度|月份)")


def find_headings(text):
    heads = []
    for line in text.splitlines():
        m = re.match(r"^#{1,6}\s+(.*)", line)
        if m:
            heads.append(m.group(1).strip())
    return heads


def check_sections(text, headings):
    results = {}
    joined = "\n".join(headings)
    for name, pats in SECTION_PATTERNS.items():
        hit = any(re.search(p, joined) for p in pats)
        # 也允许无标题但正文出现关键词（弱匹配）
        weak = (not hit) and any(re.search(p, text) for p in pats)
        results[name] = "pass" if hit else ("weak" if weak else "fail")
    return results


def check_markers(text):
    """证据/论断编号：正文使用过的编号必须在清单处定义，反之未使用的定义要提示。"""
    used = MARKER_RE.findall(text)
    defined = set(re.findall(r"[EC]\d{1,3}", text))
    undef = [u for u in set(used) if u not in defined and f"{u}:" not in text and f"{u}：" not in text]
    return {"markers_used": sorted(set(used)), "undefined_in_text": sorted(set(undef))}


def check_citations(text):
    """正文 [n] 与参考文献列表一一对应检查。返回 (正文引用集合, 列表条目数, 未定义引用, 未引用条目)。"""
    body, _, refs = text.partition("参考文献") if "参考文献" in text else text.partition("References")
    body_cites = set(int(x) for x in CITE_RE.findall(body))
    ref_lines = [l for l in refs.splitlines() if re.match(r"^\s*\[?\d+\]?", l.strip())]
    ref_ids = set()
    for l in ref_lines:
        m = re.match(r"^\s*\[(\d+)\]", l.strip())
        if m:
            ref_ids.add(int(m.group(1)))
    if not ref_ids and ref_lines:
        ref_ids = set(range(1, len(ref_lines) + 1))
    undef = sorted(body_cites - ref_ids)
    uncited = sorted(ref_ids - body_cites)
    return body_cites, len(ref_ids), undef, uncited


def check_schedule(text):
    """阶段计划是否含时间表达、里程碑是否有验收物表述。"""
    plan_sec = ""
    m = re.search(r"(#{1,6}[^\n]*(?:阶段计划|研究计划|进度|里程碑)[^\n]*)(.*?)(?=\n#{1,6}|\Z)", text, re.S)
    if m:
        plan_sec = m.group(2)
    has_dates = bool(DATE_HINT_RE.search(plan_sec)) if plan_sec else bool(DATE_HINT_RE.search(text))
    has_accept = bool(re.search(r"交付物|验收|考核", plan_sec)) if plan_sec else False
    return {"has_time_axis": has_dates, "has_deliverable_acceptance": has_accept}


def check_risks(text):
    """风险条目完整性：触发信号 / 备选方案 / 决策时点 关键词覆盖。"""
    risk_sec = ""
    m = re.search(r"(#{1,6}[^\n]*风险[^\n]*)(.*?)(?=\n#{1,6}|\Z)", text, re.S)
    if m:
        risk_sec = m.group(2)
    rows = [l for l in risk_sec.splitlines() if l.strip().startswith("|") and not re.match(r"^\s*\|[\s:\-|]+\|\s*$", l)]
    body = risk_sec if risk_sec else text
    return {
        "table_rows": max(0, len(rows) - 1),
        "has_trigger": bool(re.search(r"触发信号|触发条件|预警信号", body)),
        "has_alternative": bool(re.search(r"备选方案|降级方案|Plan B|替代方案", body)),
        "has_decision_point": bool(re.search(r"决策时点|决策点|止损点", body)),
        "categories": {c: bool(re.search(c, body)) for c in ["数据", "方法", "进度", "伦理", "合规", "经费"]},
    }


def check_alignment(text):
    """问题—目标—路线—成果 数量对齐粗检（各章节列举项计数）。"""
    def count_items(sec_pat):
        m = re.search(sec_pat + r"(.*?)(?=\n#{1,6}|\Z)", text, re.S)
        if not m:
            return None
        sec = m.group(1)
        return len(re.findall(r"(?m)^\s*(?:[-*]|\d+[\.、)])\s+", sec))
    q = count_items(r"(?s)(?:研究问题|问题定义)")
    g = count_items(r"(?s)(?:研究目标)")
    return {"question_items": q, "goal_items": g}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("proposal")
    ap.add_argument("--profile", default="gap", choices=["gap", "objective", "roadmap", "risk", "delivery"])
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    if not os.path.isfile(args.proposal):
        print(f"[validate] 无法读取文件: {args.proposal}", file=sys.stderr)
        sys.exit(2)
    text = open(args.proposal, encoding="utf-8").read()
    headings = find_headings(text)

    report = {"proposal": args.proposal, "profile": args.profile, "checks": {}}
    hard_fails = []

    sections = check_sections(text, headings)
    report["checks"]["sections"] = sections
    for k in ["研究背景", "研究问题", "研究目标", "技术路线", "阶段计划", "风险", "预期成果"]:
        if sections[k] == "fail":
            hard_fails.append(f"缺少必备章节: {k}")
    if sections["人工确认与材料缺口"] == "fail":
        hard_fails.append("缺少『人工确认与材料缺口/不确定性』章节")
    if sections["参考文献"] == "fail" and "引用" in text:
        hard_fails.append("正文出现引用但缺少参考文献章节")

    markers = check_markers(text)
    report["checks"]["evidence_markers"] = markers
    if markers["undefined_in_text"]:
        hard_fails.append("存在未在文中定义的证据/论断编号: " + ",".join(markers["undefined_in_text"]))

    body_cites, n_refs, undef, uncited = check_citations(text)
    report["checks"]["citations"] = {
        "cited_in_body": sorted(body_cites), "reference_entries": n_refs,
        "cited_but_missing": undef, "listed_but_uncited": uncited,
    }
    if undef:
        hard_fails.append("正文引用编号在参考文献列表中缺失: " + ",".join(map(str, undef)))
    if args.profile == "delivery" and uncited:
        hard_fails.append("参考文献存在未被正文引用的条目: " + ",".join(map(str, uncited)))

    schedule = check_schedule(text)
    report["checks"]["schedule"] = schedule
    if not schedule["has_time_axis"]:
        hard_fails.append("阶段计划缺少时间轴表达（年月/季度/第X月）")

    risks = check_risks(text)
    report["checks"]["risks"] = risks
    if risks["table_rows"] == 0:
        hard_fails.append("风险章节缺少结构化条目")
    for key, label in [("has_trigger", "触发信号"), ("has_alternative", "备选方案"), ("has_decision_point", "决策时点")]:
        if not risks[key]:
            hard_fails.append(f"风险章节缺少『{label}』字段")

    alignment = check_alignment(text)
    report["checks"]["alignment_counts"] = alignment

    if args.profile == "objective" and alignment["question_items"] and alignment["goal_items"]:
        if abs(alignment["question_items"] - alignment["goal_items"]) > 1:
            hard_fails.append("研究问题与研究目标条目数明显不齐（差>1）")

    report["hard_failures"] = hard_fails
    report["overall"] = "pass" if not hard_fails else "fail"
    out = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(out + "\n")
    print(out)
    print(f"\n[validate] overall={report['overall']}  hard_failures={len(hard_fails)}")
    sys.exit(0 if not hard_fails else 1)


if __name__ == "__main__":
    main()
