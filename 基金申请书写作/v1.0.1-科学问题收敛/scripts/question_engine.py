#!/usr/bin/env python3
"""question_engine.py — 科学问题收敛引擎（grant-question-convergence 专属）。

子命令：
  seed  —— 从材料全部段落抽取科学问题候选：gap/未知信号词上下文（±50 字），
            另给出材料与 task.md 中「宽泛表述」警示 → work/question_seed.json
  audit —— 审计草稿科学问题节：缺节 / 问题数量未收敛 / 无子问题分解 /
            无边界声明 / 问题过大 / 与研究目标·技术路线错位
            → work/findings.json（report_builder 自动合并）

判据设计见 references/question_method.md。只读 work/ 与输入目录，幂等。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu  # noqa: E402

# gap / 未知信号词（材料中抽取科学问题候选用）
GAP_WORDS = ["尚不清楚", "机制不明", "尚未", "缺乏", "亟待", "有待",
             "悬而未决", "未知", "谜", "争议"]
# 宽泛表述（seed 中给警示；audit 中 scope_too_broad 前五个之外的「彻底解决」仅草稿侧命中）
BROAD_WORDS = ["系统研究", "全面揭示", "各个方面", "诸方面", "全方位"]
BROAD_DRAFT_EXTRA = ["彻底解决"]
# 子问题分解标记
DECOMPOSE_MARKS = ["子问题", "分解为", "具体包括", "（1）", "1）", "其一"]
# 边界表述标记
BOUNDARY_MARKS = ["不涉及", "边界", "限定", "聚焦", "仅限于", "排除"]
# 编号条目（用于识别核心问题数）
_NUMBERED = re.compile(
    r"^\s*(?:\d+[.、）)]|（\d+）|\(\d+\)|第[一二三四五六七八九十]+[个问题]"
    r"|问题[一二三四五六七八九十\d])")
# 错位判定相似度阈值
ALIGN_THRESHOLD = 0.05
CTX = 50  # 上下文截取半径（字）


def load_work(work):
    materials = gu.read_json(os.path.join(work, "materials.json"),
                             default={"files": []})
    draft = gu.read_json(os.path.join(work, "draft.json"),
                         default={"paragraphs": []})
    return materials, draft


def _contexts(text, words):
    """text 中命中 words 的 ±CTX 上下文列表，返回 [(signal, excerpt)]。"""
    out = []
    seen = set()
    for w in words:
        for m in re.finditer(re.escape(w), text or ""):
            if w in seen:
                break  # 每段每词取一次
            seen.add(w)
            s = max(0, m.start() - CTX)
            out.append((w, text[s:m.end() + CTX].strip()))
    return out


def cmd_seed(work):
    materials, _ = load_work(work)
    candidates, warnings = [], []

    # 科学问题候选：全部段落的 gap/未知信号词上下文
    for f in materials.get("files", []):
        for p in f.get("paragraphs", []):
            for signal, excerpt in _contexts(p.get("text", ""), GAP_WORDS):
                candidates.append({"pid": p.get("pid"),
                                   "file_id": f.get("file_id"),
                                   "signal": signal,
                                   "excerpt": excerpt})

    # 宽泛表述警示：材料全部段落 + task.md
    for f in materials.get("files", []):
        for p in f.get("paragraphs", []):
            for signal, excerpt in _contexts(p.get("text", ""), BROAD_WORDS):
                warnings.append({"where": "materials",
                                 "pid": p.get("pid"),
                                 "file_id": f.get("file_id"),
                                 "signal": signal,
                                 "excerpt": excerpt})
    task_text = ""
    input_dir = gu.env_input_dir(None)
    task_path = os.path.join(input_dir, "task.md")
    if os.path.isfile(task_path):
        task_text = gu.extract_text(task_path) or ""
    for signal, excerpt in _contexts(task_text, BROAD_WORDS):
        warnings.append({"where": "task.md", "pid": None, "file_id": None,
                         "signal": signal, "excerpt": excerpt})

    seed = {
        "note": "科学问题候选（机器初筛，Agent 审定后据此收敛核心问题与子问题树）；"
                "warnings 为宽泛表述警示，写作时须把此类表述收敛为有边界的问题",
        "candidates": candidates[:60],
        "warnings": warnings[:40],
        "candidate_count": len(candidates),
        "warning_count": len(warnings),
    }
    gu.write_json(os.path.join(work, "question_seed.json"), seed)
    print("[question seed] 问题候选=%d 宽泛表述警示=%d → work/question_seed.json"
          % (len(candidates), len(warnings)))
    if not candidates:
        print("[question seed] 警告：材料中未检出 gap/未知信号词，"
              "科学问题缺少材料支点，Agent 须复核材料角色或如实标注材料缺口")
    return 0


def _count_questions(full_text):
    """识别核心问题数：？/? 结尾句 与 编号条目 取较大者（两种写法视为同一枚举）。"""
    q_sents = [s for s in gu.cn_sentences(full_text)
               if s.rstrip().endswith(("？", "?"))]
    numbered = [l for l in full_text.splitlines() if _NUMBERED.match(l)]
    return max(len(q_sents), len(numbered)), len(q_sents), len(numbered)


def cmd_audit(work):
    _, draft = load_work(work)
    paragraphs = [p for p in draft.get("paragraphs", [])
                  if p.get("element") == "科学问题"]
    findings = []
    if not paragraphs:
        findings.append({"severity": "high", "kind": "missing_section",
                         "dpid": None,
                         "msg": "草稿中未找到「科学问题」章节（sections 文件首行 # 科学问题）",
                         "suggestion": "补写科学问题节后重跑 draft_builder 与本审计"})
        gu.write_json(os.path.join(work, "findings.json"),
                      {"engine": "question_engine", "findings": findings})
        print("[question audit] findings=1 (high=1)")
        return 0

    full_text = "\n".join(p.get("text", "") for p in paragraphs)

    # 1) question_count：核心问题数期望 1-3 个，>4 视为未收敛
    qcount, n_qsent, n_numbered = _count_questions(full_text)
    if qcount > 4:
        findings.append({
            "severity": "medium", "kind": "question_count",
            "dpid": None,
            "msg": "识别到核心问题 %d 个（问句 %d / 编号条目 %d），超过 4 个，问题数量过多，未收敛"
                   % (qcount, n_qsent, n_numbered),
            "suggestion": "把研究兴趣收敛为 1-3 个核心科学问题，其余降为子问题或研究内容"})

    # 2) no_decomposition：核心问题存在但全节无子问题分解标记
    if qcount > 0 and not any(m in full_text for m in DECOMPOSE_MARKS):
        findings.append({
            "severity": "medium", "kind": "no_decomposition",
            "dpid": None,
            "msg": "核心问题存在，但全节无子问题分解标记"
                   "（子问题/分解为/具体包括/（1）/1）/其一）",
            "suggestion": "把每个核心问题分解为 2-4 个可执行的子问题，"
                          "并与研究内容逐条对应"})

    # 3) no_boundary：全节无边界表述
    if not any(m in full_text for m in BOUNDARY_MARKS):
        findings.append({
            "severity": "medium", "kind": "no_boundary",
            "dpid": None,
            "msg": "问题无边界声明（无不涉及/边界/限定/聚焦/仅限于/排除表述）",
            "suggestion": "补写研究边界：本问题聚焦于…，不涉及…，限定于…"})

    # 4) scope_too_broad：过大表述逐段命中
    broad_all = BROAD_WORDS + BROAD_DRAFT_EXTRA
    for p in paragraphs:
        text = p.get("text", "")
        for w in broad_all:
            if w in text:
                findings.append({
                    "severity": "high", "kind": "scope_too_broad",
                    "dpid": p.get("dpid"),
                    "msg": "过大表述「%s」：科学问题写成系统性工程而非可回答的问题（问题过大）" % w,
                    "suggestion": "删除「%s」类表述，改写为单一变量/机制明确的可回答问句，"
                                  "并声明边界（不涉及/限定于）" % w})

    # 5) method_misaligned：与研究目标、技术路线两两 trigram 相似度，均 < 阈值
    aligned_targets = []
    for elem in ("研究目标", "技术路线"):
        etext = "\n".join(p.get("text", "") for p in draft.get("paragraphs", [])
                          if p.get("element") == elem)
        if etext.strip():
            aligned_targets.append((elem, gu.trigram_jaccard(full_text, etext)))
    if aligned_targets and all(sim < ALIGN_THRESHOLD for _, sim in aligned_targets):
        detail = "；".join("与%s相似度 %.3f" % (e, s) for e, s in aligned_targets)
        findings.append({
            "severity": "medium", "kind": "method_misaligned",
            "dpid": None,
            "msg": "问题与目标/路线错位：科学问题节%s，均低于阈值 %.2f"
                   % (detail, ALIGN_THRESHOLD),
            "suggestion": "核心问题的关键词（机制/对象/方法）应在研究目标与技术路线中复现，"
                          "复核三节是否围绕同一问题展开"})

    gu.write_json(os.path.join(work, "findings.json"),
                  {"engine": "question_engine", "findings": findings})
    sev = {}
    for f in findings:
        sev[f["severity"]] = sev.get(f["severity"], 0) + 1
    print("[question audit] findings=%d %s"
          % (len(findings), " ".join("%s=%d" % kv for kv in sorted(sev.items()))))
    return 0


def main():
    ap = argparse.ArgumentParser(description="科学问题收敛引擎")
    ap.add_argument("cmd", choices=["seed", "audit"])
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    if args.cmd == "seed":
        return cmd_seed(args.work)
    return cmd_audit(args.work)


if __name__ == "__main__":
    sys.exit(main())
