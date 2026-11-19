#!/usr/bin/env python3
"""feasibility_engine.py — 研究基础与可行性证据链引擎（grant-feasibility-evidence 专属）。

子命令：
  seed  —— 从材料机选证据链行（能力—证据—与本研究关系三列中的前两列）：
             prior_work 角色文件的段落，以及其他文件中含 申请人/本团队/平台/实验室
             信号的段落 → work/evidence_chain_seed.json
             {rows:[{row_id, capability, evidence_fids[], sources[], relation_to_project}]}
             relation_to_project 留空，由 Agent 审定后另存 evidence_chain.json 填写。
  audit —— 审计草稿「研究基础与可行性」节（兼容 研究基础 / 研究基础与工作条件 /
             可行性分析）：体貌冲突（拟开展写成已完成、已完成成果写成拟开展）、
             成果断言无来源锚定、证据链行完整性、可行性信号缺失
             → work/findings.json（report_builder 自动合并）

判据设计见 references/feasibility_method.md。只读 work/ 下文件，幂等。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu  # noqa: E402

# 研究基础节要素名（兼容常见写法）
FEASIBILITY_ELEMENTS = ["研究基础与可行性", "研究基础", "研究基础与工作条件",
                        "可行性分析"]
# seed 阶段：非 prior_work 文件中识别前期基础段落的信号词
PRIOR_SIGNALS = ["申请人", "本团队", "平台", "实验室"]
# 成果断言信号（无〔F〕锚定时机检命中）
ACHIEVEMENT_WORDS = ["论文", "专利", "项目", "平台", "奖项", "发表", "授权", "结题"]
# 可行性信号（全节无一命中 → feasibility_missing）
FEASIBILITY_WORDS = ["可行", "条件", "保障", "平台", "团队", "基础"]
# 成果类〔F〕：台账类型限定 pub_mention / number，且来源文件 role_guess=prior_work
ACHIEVEMENT_FID_TYPES = ("pub_mention", "number")

MARK_RE = re.compile(r"〔[^〕]*〕")
FID_RE = re.compile(r"〔(F\d+)〕")


def load_work(work):
    ledger = gu.read_json(os.path.join(work, "fact_ledger.json"),
                          default={"entries": []})
    materials = gu.read_json(os.path.join(work, "materials.json"),
                             default={"files": []})
    draft = gu.read_json(os.path.join(work, "draft.json"),
                         default={"paragraphs": []})
    return ledger, materials, draft


def file_role_map(materials):
    """file_id → role_guess"""
    return {f.get("file_id", ""): f.get("role_guess", "other")
            for f in materials.get("files", [])}


def pid_fids_map(ledger):
    """pid → [fid, ...]（按台账顺序）"""
    m = {}
    for e in ledger.get("entries", []):
        src = e.get("source", {}) or {}
        pid = src.get("pid", "")
        fid = e.get("fid", "")
        if pid and fid:
            m.setdefault(pid, []).append(fid)
    return m


def strip_markers(text):
    return MARK_RE.sub("", text or "")


def is_feasibility_element(element):
    e = element or ""
    if e in FEASIBILITY_ELEMENTS:
        return True
    return e.startswith("研究基础") or e.startswith("可行性")


def cmd_seed(work):
    ledger, materials, _ = load_work(work)
    roles = file_role_map(materials)
    pid_fids = pid_fids_map(ledger)

    rows = []
    seen_pid = set()
    prior_files = 0
    for f in materials.get("files", []):
        file_id = f.get("file_id", "")
        role = f.get("role_guess", "other")
        if role == "prior_work":
            prior_files += 1
        for p in f.get("paragraphs", []):
            if p.get("kind") == "heading":
                continue
            text = (p.get("text") or "").strip()
            if not text:
                continue
            # prior_work 文件全取；其他文件只取含前期基础信号的段落
            if role != "prior_work" and not any(s in text
                                                for s in PRIOR_SIGNALS):
                continue
            pid = p.get("pid", "")
            if pid in seen_pid:
                continue
            seen_pid.add(pid)
            rows.append({
                "row_id": "R%03d" % (len(rows) + 1),
                "capability": text[:30],
                "evidence_fids": pid_fids.get(pid, []),
                "sources": [{"file_id": file_id, "pid": pid}],
                "relation_to_project": "",
            })

    seed = {
        "note": "研究基础证据链机选行（能力—证据—与本研究关系）。"
                "Agent 审定取舍、填写 relation_to_project 后另存为 "
                "work/evidence_chain.json（本文件为机器初稿，勿直接交付）",
        "rows": rows,
        "row_count": len(rows),
    }
    gu.write_json(os.path.join(work, "evidence_chain_seed.json"), seed)
    print("[feasibility seed] 证据链行=%d（prior_work 文件=%d 个）"
          " → work/evidence_chain_seed.json" % (len(rows), prior_files))
    if prior_files == 0:
        print("[feasibility seed] 警告：未发现 role_guess=prior_work 的材料文件，"
              "Agent 须复核 parse_materials 的 role_guess 或如实登记材料缺口")
    elif not rows:
        print("[feasibility seed] 警告：prior_work 文件中无可取段落，"
              "研究基础节缺乏证据链素材，须登记 manual_confirmations")
    return 0


def cmd_audit(work):
    ledger, materials, draft = load_work(work)
    roles = file_role_map(materials)
    fid_entry = {e.get("fid"): e for e in ledger.get("entries", [])}
    paragraphs = [p for p in draft.get("paragraphs", [])
                  if is_feasibility_element(p.get("element"))]
    findings = []

    # 1) 章节缺失
    if not paragraphs:
        findings.append({"severity": "high", "kind": "missing_section",
                         "dpid": None,
                         "msg": "草稿中未找到「研究基础与可行性」章节"
                                "（兼容 研究基础 / 研究基础与工作条件 / 可行性分析）",
                         "suggestion": "补写研究基础节后重跑 draft_builder 与本审计"})
        gu.write_json(os.path.join(work, "findings.json"),
                      {"engine": "feasibility_engine", "findings": findings})
        print("[feasibility audit] findings=1 (high=1)")
        return 0

    full_text = "\n".join(strip_markers(p.get("text", "")) for p in paragraphs)

    for p in paragraphs:
        dpid = p.get("dpid")
        text = p.get("text", "")
        body = strip_markers(text)
        markers = p.get("markers", [])
        fids = FID_RE.findall(text)
        label, hits = gu.aspect_classify(body)

        # 2) 拟开展内容写成了已完成体（high）
        if "拟" in markers and label == "completed":
            findings.append({
                "severity": "high", "kind": "aspect_violation_planned_as_done",
                "dpid": dpid,
                "msg": "拟开展内容写成了已完成体：段落带〔拟〕标记但体貌判为 "
                       "completed（完成信号：%s）" % "、".join(hits),
                "suggestion": "拟开展内容改用拟态表述（拟/将/计划/预期），"
                              "删除 已/了/发表/获得/建立 等完成信号；"
                              "若确为已完成成果则去掉〔拟〕并补〔F〕锚定"})

        # 3) 已完成成果写成了拟开展体（medium）
        achievement_fids = []
        for fid in fids:
            e = fid_entry.get(fid)
            if not e:
                continue
            src = e.get("source", {}) or {}
            if (e.get("type") in ACHIEVEMENT_FID_TYPES
                    and roles.get(src.get("file_id", ""), "") == "prior_work"):
                achievement_fids.append(fid)
        if achievement_fids and label == "planned":
            findings.append({
                "severity": "medium", "kind": "aspect_violation_done_as_planned",
                "dpid": dpid,
                "msg": "已完成成果写成了拟开展体：段落锚定前期成果〔%s〕"
                       "但体貌判为 planned（拟态信号：%s）"
                       % ("、".join(achievement_fids), "、".join(hits)),
                "suggestion": "已完成前期成果改用完成体（已发表/已获授权/已建立），"
                              "〔拟〕只保留给本课题拟开展内容"})

        # 4) 成果断言无来源锚定（high）
        hit_words = [w for w in ACHIEVEMENT_WORDS if w in body]
        if hit_words and not fids:
            findings.append({
                "severity": "high", "kind": "unsourced_achievement",
                "dpid": dpid,
                "msg": "成果断言无来源锚定：段落含成果信号（%s）但无任何〔F〕标记"
                       % "、".join(hit_words),
                "suggestion": "为每条成果断言补〔Fxxxx〕指向台账中的论文/专利/项目号/"
                              "平台事实；材料中无据的成果删除或标〔确认〕"})

    # 5) 证据链行完整性
    chain_path = os.path.join(work, "evidence_chain.json")
    chain = gu.read_json(chain_path, default=None)
    if isinstance(chain, dict) and isinstance(chain.get("rows"), list):
        for row in chain["rows"]:
            if not str(row.get("relation_to_project", "")).strip():
                findings.append({
                    "severity": "medium", "kind": "chain_incomplete",
                    "dpid": None,
                    "msg": "证据链行 %s（%s）的 relation_to_project 为空"
                           % (row.get("row_id", "?"),
                              str(row.get("capability", ""))[:20]),
                    "suggestion": "填写该行能力/证据与本课题的支撑关系，"
                                  "或删除与本研究无关的行"})
    else:
        findings.append({
            "severity": "low", "kind": "chain_incomplete",
            "dpid": None,
            "msg": "未生成审定版 evidence_chain.json（仅有机器初稿 "
                   "evidence_chain_seed.json 或种子也未生成）",
            "suggestion": "Agent 审定 evidence_chain_seed.json、填写 "
                          "relation_to_project 后另存 work/evidence_chain.json"})

    # 6) 可行性信号缺失
    if not any(w in full_text for w in FEASIBILITY_WORDS):
        findings.append({
            "severity": "low", "kind": "feasibility_missing",
            "dpid": None,
            "msg": "研究基础节全节无可行性信号词（可行/条件/保障/平台/团队/基础）",
            "suggestion": "补写可行性论证：平台条件、团队分工、技术保障与本研究基础"
                          "如何支撑拟开展内容"})

    gu.write_json(os.path.join(work, "findings.json"),
                  {"engine": "feasibility_engine", "findings": findings})
    sev = {}
    for f in findings:
        sev[f["severity"]] = sev.get(f["severity"], 0) + 1
    print("[feasibility audit] findings=%d %s"
          % (len(findings),
             " ".join("%s=%d" % kv for kv in sorted(sev.items())) or "(无)"))
    return 0


def main():
    ap = argparse.ArgumentParser(description="研究基础与可行性证据链引擎")
    ap.add_argument("cmd", choices=["seed", "audit"])
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    if args.cmd == "seed":
        return cmd_seed(args.work)
    return cmd_audit(args.work)


if __name__ == "__main__":
    sys.exit(main())
