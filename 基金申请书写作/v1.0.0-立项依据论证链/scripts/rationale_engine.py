#!/usr/bin/env python3
"""rationale_engine.py — 立项依据必要性论证链引擎（grant-rationale-chain 专属）。

子命令：
  seed  —— 从材料与事实台账构建论证链三段槽位候选：现状（别人做到哪一步）、
            瓶颈（还差什么）、我们（为什么是我们）→ work/rationale_chain.json
  audit —— 审计草稿立项依据节：政策口号无证据、现状论断无引用、三段链缺环
            → work/findings.json（report_builder 自动合并）

判据设计见 references/rationale_method.md。只读 work/ 下文件，幂等。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu  # noqa: E402

# gap / 瓶颈信号词（材料中抽取瓶颈候选用；草稿中识别瓶颈环用）
GAP_WORDS = ["尚不清楚", "机制不明", "尚未", "缺乏", "难以", "亟待", "瓶颈",
             "不足", "挑战", "仍待", "仍未", "受限于", "制约", "悬而未决",
             "有待", "尚未见"]
# 政策口号/空泛意义词（无证据锚定时审计命中）
SLOGAN_WORDS = ["意义重大", "迫切需要", "迫切需求", "国家战略", "卡脖子",
                "备受关注", "潜力巨大", "具有重要意义", "重大需求",
                "刻不容缓", "举足轻重", "战略性", "双碳"]
# 现状环信号（领域状态断言）
STATE_WORDS = ["目前", "现有", "近年来", "已报道", "已有研究", "已有工作",
               "国内外", "研究者", "文献", "研究表明", "已实现", "已达到",
               "当前", "迄今"]
# 我们环信号
OUR_WORDS = ["申请人", "本团队", "本课题组", "我们", "前期工作", "前期研究",
             "前期成果", "本实验室", "申请人团队"]


def load_work(work):
    ledger = gu.read_json(os.path.join(work, "fact_ledger.json"),
                          default={"entries": []})
    materials = gu.read_json(os.path.join(work, "materials.json"),
                             default={"files": []})
    draft = gu.read_json(os.path.join(work, "draft.json"),
                         default={"paragraphs": []})
    return ledger, materials, draft


def para_index(materials):
    """pid → (role_guess, file_id, text)"""
    idx = {}
    for f in materials.get("files", []):
        for p in f.get("paragraphs", []):
            idx[p.get("pid", "")] = (f.get("role_guess", "other"),
                                     f.get("file_id", ""), p.get("text", ""))
    return idx


def cmd_seed(work):
    ledger, materials, _ = load_work(work)
    pidx = para_index(materials)
    entries = ledger.get("entries", [])

    state_cand, gap_cand, our_cand = [], [], []
    for e in entries:
        src = e.get("source", {})
        pid = src.get("pid", "")
        role, file_id, ptext = pidx.get(pid, ("other", "", ""))
        item = {"fid": e.get("fid"), "type": e.get("type"),
                "value": e.get("value"), "unit": e.get("unit", ""),
                "context": e.get("context", ""), "source": src}
        # 现状槽：论文角色文件中的引用/数字/年份事实
        if role == "paper" and e.get("type") in ("citation", "number",
                                                 "year", "pub_mention"):
            state_cand.append(item)
        # 我们槽：前期成果角色文件中的事实
        if role == "prior_work":
            our_cand.append(item)
    # 瓶颈槽：全材料 gap 关键词上下文（不依赖台账类型）
    seen_gap = set()
    for f in materials.get("files", []):
        for p in f.get("paragraphs", []):
            text = p.get("text", "")
            for w in GAP_WORDS:
                for m in re.finditer(re.escape(w), text):
                    key = (p.get("pid"), w)
                    if key in seen_gap:
                        continue
                    seen_gap.add(key)
                    s = max(0, m.start() - 50)
                    gap_cand.append({"pid": p.get("pid"),
                                     "file_id": f.get("file_id"),
                                     "signal": w,
                                     "excerpt": text[s:m.end() + 50].strip()})
                    break  # 每段每词取一次

    chain = {
        "note": "论证链三段槽位候选（机器初筛，Agent 审定取舍后据此撰写立项依据）",
        "slots": [
            {"slot": "现状", "question": "别人做到哪一步",
             "writing_requirement": "每条现状论断须带〔F〕引用标记；只用 paper 角色材料事实",
             "candidates": state_cand[:40]},
            {"slot": "瓶颈", "question": "还差什么",
             "writing_requirement": "瓶颈须从材料 gap 表述提炼，写成可科学回答的差距，不写空泛困难",
             "candidates": gap_cand[:40]},
            {"slot": "我们", "question": "为什么是我们",
             "writing_requirement": "每条前期基础须带〔F〕标记且为已完成态；与瓶颈一一呼应",
             "candidates": our_cand[:40]},
        ],
        "candidate_counts": {"现状": len(state_cand), "瓶颈": len(gap_cand),
                             "我们": len(our_cand)},
    }
    gu.write_json(os.path.join(work, "rationale_chain.json"), chain)
    print("[rationale seed] 现状候选=%d 瓶颈候选=%d 我们候选=%d → work/rationale_chain.json"
          % (len(state_cand), len(gap_cand), len(our_cand)))
    if not state_cand:
        print("[rationale seed] 警告：现状槽无候选（paper 角色材料缺失？），"
              "Agent 须复核 parse_materials 的 role_guess 或如实标注材料缺口")
    if not our_cand:
        print("[rationale seed] 警告：我们槽无候选（prior_work 材料缺失？），"
              "立项依据之为什么是我们一环须登记 manual_confirmations")
    return 0


def cmd_audit(work):
    ledger, materials, draft = load_work(work)
    paragraphs = [p for p in draft.get("paragraphs", [])
                  if p.get("element") == "立项依据"]
    findings = []
    if not paragraphs:
        findings.append({"severity": "high", "kind": "missing_section",
                         "dpid": None,
                         "msg": "草稿中未找到「立项依据」章节（sections 文件首行 # 立项依据）",
                         "suggestion": "补写立项依据节后重跑 draft_builder 与本审计"})
        gu.write_json(os.path.join(work, "findings.json"),
                      {"engine": "rationale_engine", "findings": findings})
        print("[rationale audit] findings=1 (high=1)")
        return 0

    full_text = "\n".join(p.get("text", "") for p in paragraphs)

    # 1) 政策口号无证据锚定
    for p in paragraphs:
        text = p.get("text", "")
        has_marker = bool(p.get("markers"))
        for w in SLOGAN_WORDS:
            if w in text and not has_marker:
                findings.append({
                    "severity": "medium", "kind": "slogan_without_evidence",
                    "dpid": p.get("dpid"),
                    "msg": "政策口号/空泛意义词「%s」所在段落无任何〔F〕证据标记" % w,
                    "suggestion": "删除口号堆叠，或改为「事实〔Fxxxx〕→因此有必要」的论证句式"})

    # 2) 现状论断无引用锚定
    for p in paragraphs:
        text = p.get("text", "")
        if any(w in text for w in STATE_WORDS):
            # 该段须有台账标记，且其中至少一个来自 paper 角色或 citation 类
            fids = p.get("markers", [])
            fid_set = {e.get("fid"): e for e in ledger.get("entries", [])}
            anchored = False
            for fid in fids:
                e = fid_set.get(fid)
                if not e:
                    continue
                if e.get("type") in ("citation", "pub_mention", "number",
                                     "year"):
                    anchored = True
                    break
            if not anchored:
                findings.append({
                    "severity": "medium", "kind": "state_claim_unanchored",
                    "dpid": p.get("dpid"),
                    "msg": "领域现状论断未锚定具体已有工作（无引用/数字类〔F〕标记）",
                    "suggestion": "为该论断补〔Fxxxx〕指向材料中具体文献或数据；"
                                  "无法锚定的改写为申请人观察或删除"})

    # 3) 三段链完整性
    has_state = any(w in full_text for w in STATE_WORDS)
    has_gap = any(w in full_text for w in GAP_WORDS)
    has_our = any(w in full_text for w in OUR_WORDS)
    for slot, ok, hint in [
            ("现状", has_state, "补写「别人做到哪一步」：引用材料中已有工作与数据"),
            ("瓶颈", has_gap, "补写「还差什么」：从材料 gap 表述提炼关键差距"),
            ("我们", has_our, "补写「为什么是我们」：锚定申请人已完成前期成果〔F〕")]:
        if not ok:
            findings.append({
                "severity": "high", "kind": "chain_link_missing",
                "dpid": None,
                "msg": "必要性论证链缺「%s」一环" % slot,
                "suggestion": hint})

    # 4) 瓶颈环与科学问题衔接提示（low）
    insp = gu.read_json(os.path.join(work, "draft.json"), default={})
    qtext = "\n".join(p.get("text", "") for p in insp.get("paragraphs", [])
                      if p.get("element") == "科学问题")
    if has_gap and qtext:
        linked = any(w in qtext for w in GAP_WORDS) or \
            gu.trigram_jaccard(full_text[-400:], qtext[:400]) > 0.08
        if not linked:
            findings.append({
                "severity": "low", "kind": "gap_question_disjoint",
                "dpid": None,
                "msg": "立项依据瓶颈表述与科学问题节衔接弱（无共同信号词且相似度低）",
                "suggestion": "科学问题应直接承接立项依据提炼的瓶颈，复核两节措辞"})

    gu.write_json(os.path.join(work, "findings.json"),
                  {"engine": "rationale_engine", "findings": findings})
    sev = {}
    for f in findings:
        sev[f["severity"]] = sev.get(f["severity"], 0) + 1
    print("[rationale audit] findings=%d %s"
          % (len(findings), " ".join("%s=%d" % kv for kv in sorted(sev.items()))))
    return 0


def main():
    ap = argparse.ArgumentParser(description="立项依据必要性论证链引擎")
    ap.add_argument("cmd", choices=["seed", "audit"])
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    if args.cmd == "seed":
        return cmd_seed(args.work)
    return cmd_audit(args.work)


if __name__ == "__main__":
    sys.exit(main())
