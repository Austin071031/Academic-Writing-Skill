#!/usr/bin/env python3
"""response_engine.py — 逐条回应决策台账引擎（回复信自动生成 + 答非所问检测 + 语气审计）。

设计要点（对应评分"答得全""证得住""可靠体验"）：
- 回复信不由 Agent 临场撰写，而由结构化台账（dispositions.json）自动装配：
  审稿人→意见→子要求三级，每个子要求输出 决策 + 回应 + 修改指涉(E#) + 证据指涉(EV#)；
- disposition 引用的修改操作若 status!=applied，该行自动标 ⚠ 并写入问题清单，
  防止"声称已改但实际失败"的虚报；
- audit 阶段三类检查：答非所问检测（按 action_kind 核验回应是否对症）、
  决策-语气一致性（不采纳必须有依据、采纳不许空转）、语气红线扫描
  （冒犯/过度承诺/无原则顺从，逐条给四档句式改写建议）；
- 回复信被 Agent 手工润色后必须重跑 audit（红线扫描针对信件全文）。

输入: work/comments.json, work/dispositions.json, work/edit_report.json,
      work/evidence_checklist.json(可选), work/edit_plan.json(可选兜底)
输出: stage=generate → /app/output/response_letter.md + work/response_problems.json
      stage=audit    → /app/output/audit_report.json + 控制台汇总
用法: python3 response_engine.py --work /app/work --out /app/output [--stage generate|audit]
exit: generate 0=成功 2=输入缺失；audit 0=PASS 1=FAIL 2=输入缺失
"""
import argparse, json, os, re, sys

# ---------- 词表（与 references/response_rules.md 保持一致，改动须同步） ----------

# 需要证据支撑的动作类型：回应必须含 EV# 引用或"待补/无法/补做"字样
EVIDENCE_KINDS = {"add_experiment", "add_data", "add_citation", "reanalysis"}
RE_EVIDENCE_OK = re.compile(r"EV\d+|待补|无法|补做", re.I)
# delete 类：回应须含"删"字或引用 delete 动作的 op
RE_DELETE_OK = re.compile(r"删")
# format 类：回应须含格式类词或引用任意 op
RE_FORMAT_WORD = re.compile(r"格式|缩写|全称|简称|单位|排版|字体|编号|图表|标点|大小写")
# question 类：回应须含直接回答信号词
RE_ANSWER_WORD = re.compile(r"因为|由于|是由于|原因是|原因在于|is because|because|due to", re.I)
# 不采纳的依据词：response ≥40 字且须含其一
RE_BASIS_WORD = re.compile(r"因为|由于|依据|基线|原文")
# 采纳/部分采纳的理由词（防空洞接受）
RE_REASON_WORD = re.compile(
    r"因为|由于|依据|鉴于|无法|难以|超出|待补|已在|已修改|已补充|已删除|已澄清|"
    r"EV\d+|E\d+|P\d{3}|because|since|cannot|unable", re.I)

REJECT_TONES = {"澄清", "礼貌反驳", "申诉"}

# 语气红线：类别 → (词表, 改写建议句式，详见 references/response_rules.md 四档句式库)
REDLINES = {
    "offensive": (
        ["荒谬", "毫无道理", "审稿人误解了", "明显错误", "nonsense"],
        "改用礼貌反驳句式：感谢审稿人提出的观点。经核对，基线〈P0##〉原文「……」表明……，"
        "因此我们认为……；为避免歧义，已在〈章节〉补充澄清（E#）。"),
    "overpromise": (
        ["保证", "一定会", "彻底解决", "guarantee", "definitely will"],
        "改用有边界的接受句式：我们已按建议修改（E#），并将……；受〈条件〉限制，"
        "……部分以【待补：…】占位，到位后填入。"),
    "submissive": (
        ["完全同意您的所有意见", ],
        "改用逐条对应句式：感谢审稿人的细致意见，我们逐条回应如下（同意处说明已做修改 E#，"
        "保留处给出依据）。"),
}

EXPLANATION_BLOCK = """\
## 阅读说明（编号与记号）

- **编号对应**：子要求编号形如 R1-C2-s1（审稿人1-意见2-子要求1），与《审稿意见摘要》逐条一一对应，未做归并或省略；
- **E#** 为修改操作编号，括号内为其应用状态（applied=已真实落入修订稿 / failed=未落实）与修订稿行号，可在 edit_locations.md 与 edit_report.json 中核对；
- **EV#** 为证据清单条目编号（补实验/补数据/补文献等需求），状态与替代说明见 evidence_checklist.md；
- **【待补：…】** 为占位标记，表示基线未提供、本环境无法补做的内容，**不视为已完成**，全部列入信尾"待办与确认"。"""

TAIL_NOTE = ("---\n本信由 response_engine.py 依据决策台账（dispositions.json）自动装配生成；"
             "作者可润色措辞，但润色后必须重跑 `response_engine.py --stage audit` 复核语气与对症性，"
             "且不得改动决策、E#/EV# 指涉与【待补】占位的事实表述。")


def load_json(path, default=None):
    """宽容读取 JSON；文件缺失或损坏返回 default。"""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def fatal(msg):
    print(f"[response_engine][FATAL] {msg}", file=sys.stderr)
    return 2


# ---------- 公共：加载台账 ----------

def load_ledger(work):
    """读取 comments / dispositions / edit_report / evidence_checklist / edit_plan。

    返回 (comments, disp_by_sub, op_index, ev_index)；op_index 以 edit_report 为准，
    edit_plan 兜底补充 action 信息（edit_report 缺失的 op 视为不存在）。"""
    comments = load_json(os.path.join(work, "comments.json"))
    dispositions = load_json(os.path.join(work, "dispositions.json"))
    if comments is None:
        return None, None, None, None, "缺少 work/comments.json（先跑 parse_comments）"
    if dispositions is None:
        return None, None, None, None, "缺少 work/dispositions.json（先由 Agent 撰写处置决策）"
    edit_report = load_json(os.path.join(work, "edit_report.json"), {}) or {}
    edit_plan = load_json(os.path.join(work, "edit_plan.json"), []) or []
    ev_list = load_json(os.path.join(work, "evidence_checklist.json"), []) or []

    op_index = {o["op_id"]: o for o in edit_report.get("ops", [])}
    plan_action = {o.get("op_id"): o.get("action") for o in edit_plan}
    for oid, act in plan_action.items():
        if oid in op_index and not op_index[oid].get("action"):
            op_index[oid]["action"] = act
    ev_index = {e.get("ev_id"): e for e in ev_list}
    disp_by_sub = {d.get("sub_id"): d for d in dispositions}
    return comments, disp_by_sub, op_index, ev_index, None


def op_ref_text(opid, op_index, problems, sub_id):
    """生成单个 E# 指涉文本；失败/不存在的 op 记 ⚠ 并写入问题清单。"""
    op = op_index.get(opid)
    if op is None:
        problems.append({"sub_id": sub_id, "op_id": opid,
                         "issue": "disposition 引用的修改操作在 edit_report 中不存在"})
        return f"{opid}（⚠ 该操作不存在于修改报告，请核实）"
    status = op.get("status", "?")
    line = op.get("revised_line")
    if status != "applied":
        problems.append({"sub_id": sub_id, "op_id": opid,
                         "issue": f"修改操作 status={status}，不得在回复中声称已落实"})
        return f"{opid}（⚠ status={status}，未落实）"
    loc = f"，修订稿第 {line} 行" if line else ""
    ph = "，含【待补】占位" if op.get("has_placeholder") else ""
    return f"{opid}（applied{loc}{ph}）"


def ev_ref_text(evid, ev_index):
    """生成单个 EV# 指涉文本。"""
    ev = ev_index.get(evid)
    if not ev:
        return f"{evid}（见证据清单）"
    status = ev.get("status", "状态未填")
    demand = ev.get("demand", "")
    return f"{evid}（{demand}｜{status}）"


# ---------- stage=generate ----------

def stage_generate(work, out):
    comments, disp_by_sub, op_index, ev_index, err = load_ledger(work)
    if err:
        return fatal(err)
    os.makedirs(out, exist_ok=True)
    problems = []

    lines = [
        "# 审稿回复信（逐条回应草案）",
        "",
        "尊敬的编辑与审稿人：",
        "",
        "感谢对稿件的细致评审。以下按 审稿人→意见→子要求 逐条回应；每处声称的修改均已在"
        "随附修订稿（revised_manuscript.md）中真实落实，失败或无法补做的项目如实标注，不冒称完成。",
        "",
        EXPLANATION_BLOCK,
        "",
    ]

    # 按审稿人分组，保持 comments.json 原始顺序
    groups = {}
    order = []
    for c in comments.get("comments", []):
        rv = c.get("reviewer", "?")
        if rv not in groups:
            groups[rv] = []
            order.append(rv)
        groups[rv].append(c)

    n_subs = 0
    for rv in order:
        lines.append(f"## Reviewer {rv.lstrip('Rr')}（{rv}）")
        lines.append("")
        for c in groups[rv]:
            cid = c.get("id", "?")
            quote = (c.get("raw_text") or "").strip().replace("\n", " ")[:80]
            lines.append(f"### {cid}")
            lines.append("")
            if quote:
                lines.append(f"> 原意见摘录：{quote}")
                lines.append("")
            for sub in c.get("sub_requests", []):
                n_subs += 1
                sid = sub.get("sub_id", "?")
                disp = disp_by_sub.get(sid)
                if disp is None:
                    problems.append({"sub_id": sid, "op_id": None,
                                     "issue": "该子要求在 dispositions.json 中无处置决策"})
                    lines.append(f"- **{sid}** ⚠【未处置】该子要求缺少决策，请补充 dispositions 后重新生成。")
                    lines.append("")
                    continue
                decision = disp.get("decision", "未填")
                tone = disp.get("tone", "未填")
                lines.append(f"- **{sid}**（决策：{decision}｜语气：{tone}）")
                sub_text = (sub.get("text") or "").strip().replace("\n", " ")
                if sub_text:
                    lines.append(f"  - 子要求：{sub_text}")
                lines.append(f"  - 回应：{(disp.get('response') or '').strip() or '（未填写，必须补充）'}")
                ops = disp.get("edit_ops") or []
                if ops:
                    refs = "；".join(op_ref_text(o, op_index, problems, sid) for o in ops)
                    lines.append(f"  - 修改指涉：{refs}")
                evs = disp.get("evidence") or []
                if evs:
                    refs = "；".join(ev_ref_text(e, ev_index) for e in evs)
                    lines.append(f"  - 证据指涉：{refs}")
                lines.append("")
        lines.append("")

    # 信尾：总体修改清单（按 op）
    lines.append("## 总体修改清单")
    lines.append("")
    ops_all = list(op_index.values())
    if ops_all:
        for op in sorted(ops_all, key=lambda o: o.get("op_id", "")):
            oid = op.get("op_id", "?")
            loc = f"，修订稿第 {op['revised_line']} 行" if op.get("revised_line") else ""
            ph = "；含【待补】占位" if op.get("has_placeholder") else ""
            head = (op.get("rationale") or (op.get("new_text_head") or "")[:40]).strip()
            lines.append(f"- {oid}（{op.get('comment_ref', '?')}｜{op.get('action', '?')}｜"
                         f"{op.get('status', '?')}{loc}{ph}）：{head}")
    else:
        lines.append("- （无修改操作记录）")
    lines.append("")

    # 信尾：待办与确认（占位 + 无法补做 + 问题清单）
    lines.append("## 待办与确认")
    lines.append("")
    ph_ops = [o for o in ops_all if o.get("has_placeholder")]
    if ph_ops:
        lines.append("**【待补】占位（不视为已完成）：**")
        for op in sorted(ph_ops, key=lambda o: o.get("op_id", "")):
            lines.append(f"- {op.get('op_id')}：{(op.get('new_text_head') or '')[:60]}")
        lines.append("")
    pending_ev = [e for e in ev_index.values() if e.get("status") and "到位" != e.get("status")]
    if pending_ev:
        lines.append("**证据未到位 / 无法补做项：**")
        for e in pending_ev:
            note = f"——{e.get('note')}" if e.get("note") else ""
            lines.append(f"- {e.get('ev_id')}（{e.get('sub_id', '?')}）：{e.get('demand', '')}"
                         f"｜{e.get('status', '')}{note}")
        lines.append("")
    if problems:
        lines.append("**⚠ 问题清单（必须先处置再交付）：**")
        for p in problems:
            lines.append(f"- {p.get('sub_id')}: {p.get('issue')}"
                         + (f"（{p['op_id']}）" if p.get("op_id") else ""))
        lines.append("")
    if not ph_ops and not pending_ev and not problems:
        lines.append("- 无。")
        lines.append("")

    lines.append(TAIL_NOTE)
    letter = "\n".join(lines) + "\n"
    with open(os.path.join(out, "response_letter.md"), "w", encoding="utf-8") as f:
        f.write(letter)
    with open(os.path.join(work, "response_problems.json"), "w", encoding="utf-8") as f:
        json.dump(problems, f, ensure_ascii=False, indent=1)

    n_comments = sum(len(v) for v in groups.values())
    print(f"[generate] 审稿人={len(order)} 意见={n_comments} 子要求={n_subs} "
          f"op={len(ops_all)} 问题={len(problems)}")
    if problems:
        print("[generate][WARN] 存在未处置子要求或失败/缺失 op，已写入信尾问题清单与 "
              "work/response_problems.json", file=sys.stderr)
    print(f"[generate] 回复信草案 → {os.path.join(out, 'response_letter.md')}")
    return 0


# ---------- stage=audit ----------

def audit_off_topic(comments, disp_by_sub, op_index):
    """答非所问检测：按子要求 action_kind 核验回应是否对症。"""
    risks = []
    subs = [s for c in comments.get("comments", []) for s in c.get("sub_requests", [])]
    for sub in subs:
        sid = sub.get("sub_id")
        kind = sub.get("action_kind") or "other"
        disp = disp_by_sub.get(sid) or {}
        resp = (disp.get("response") or "").strip()
        ops = disp.get("edit_ops") or []
        reason = None
        if kind in EVIDENCE_KINDS and not RE_EVIDENCE_OK.search(resp):
            reason = (f"action_kind={kind} 要求证据支撑，回应须引用 EV# 或写明 待补/无法/补做")
        elif kind == "delete":
            has_delete_op = any(op_index.get(o, {}).get("action") == "delete" for o in ops)
            if not RE_DELETE_OK.search(resp) and not has_delete_op:
                reason = "action_kind=delete，回应须含“删”字或引用 delete 动作的修改操作"
        elif kind == "format":
            if not RE_FORMAT_WORD.search(resp) and not ops:
                reason = "action_kind=format，回应须含格式类词（缩写/全称/单位/图表…）或引用修改操作"
        elif kind == "question":
            if not RE_ANSWER_WORD.search(resp):
                reason = "action_kind=question，回应须含直接回答信号词（因为/由于/原因是…）"
        if reason:
            risks.append({"sub_id": sid, "action_kind": kind, "reason": reason,
                          "suggestion": "按 action_kind 要求重写该条回应；判据见 references/response_rules.md 第 4 节"})
    return {"pass": not risks, "off_topic_risk": risks, "n_checked": len(subs)}


def audit_tone_consistency(comments, disp_by_sub):
    """决策-语气一致性：不采纳必须有依据与恰当语气；采纳不许空转。"""
    tone_mismatch, weak_reject, hollow_accept = [], [], []
    subs = [s for c in comments.get("comments", []) for s in c.get("sub_requests", [])]
    for sub in subs:
        sid = sub.get("sub_id")
        disp = disp_by_sub.get(sid)
        if not disp:
            continue
        decision = disp.get("decision", "")
        tone = disp.get("tone", "")
        resp = (disp.get("response") or "").strip()
        if decision == "不采纳":
            if tone not in REJECT_TONES:
                tone_mismatch.append({
                    "sub_id": sid, "tone": tone,
                    "reason": f"不采纳的语气须为 {'/'.join(sorted(REJECT_TONES))} 之一",
                    "suggestion": "按 references/response_rules.md 第 3 节四档句式改写"})
            if len(resp) < 40 or not RE_BASIS_WORD.search(resp):
                weak_reject.append({
                    "sub_id": sid,
                    "reason": "不采纳的回应须 ≥40 字且含依据词（因为/由于/依据/基线/原文）",
                    "suggestion": "引基线原文锚点为据说明理由，示例句式见 response_rules.md 礼貌反驳档"})
        elif decision in ("采纳", "部分采纳"):
            if not disp.get("edit_ops") and not disp.get("evidence") \
                    and not RE_REASON_WORD.search(resp):
                hollow_accept.append({
                    "sub_id": sid,
                    "reason": "声称采纳却无修改操作、无证据指涉、无理由词，属空洞接受",
                    "suggestion": "补 E#/EV# 指涉或说明具体理由；确实无动作的改为说明性回应"})
    ok = not tone_mismatch and not weak_reject and not hollow_accept
    return {"pass": ok, "tone_mismatch": tone_mismatch,
            "weak_reject": weak_reject, "hollow_accept": hollow_accept}


def audit_redlines(letter_path):
    """语气红线扫描：对回复信全文逐词表命中，给改写建议。"""
    if not os.path.exists(letter_path):
        return {"pass": False, "letter_missing": True,
                "hits": {"offensive": [], "overpromise": [], "submissive": []}}
    with open(letter_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    hits = {}
    for cat, (words, suggestion) in REDLINES.items():
        found = []
        for w in words:
            for i, ln in enumerate(lines, 1):
                if w.lower() in ln.lower():
                    found.append({"phrase": w, "line": i,
                                  "excerpt": ln.strip()[:60], "suggestion": suggestion})
        hits[cat] = found
    ok = all(not v for v in hits.values())
    return {"pass": ok, "letter_missing": False, "hits": hits}


def audit_letter_structure(comments, letter_path):
    """信件完整性：每条意见 id 与每个子要求 sub_id 必须出现在回复信中。"""
    if not os.path.exists(letter_path):
        return {"pass": False, "missing_comments": [], "missing_subs": [],
                "note": "response_letter.md 不存在"}
    with open(letter_path, encoding="utf-8") as f:
        text = f.read()
    missing_c, missing_s = [], []
    for c in comments.get("comments", []):
        if c.get("id") not in text:
            missing_c.append(c.get("id"))
        for s in c.get("sub_requests", []):
            if s.get("sub_id") not in text:
                missing_s.append(s.get("sub_id"))
    return {"pass": not missing_c and not missing_s,
            "missing_comments": missing_c, "missing_subs": missing_s}


def stage_audit(work, out):
    comments, disp_by_sub, op_index, _ev, err = load_ledger(work)
    if err:
        return fatal(err)
    os.makedirs(out, exist_ok=True)
    letter_path = os.path.join(out, "response_letter.md")

    checks = {
        "off_topic": audit_off_topic(comments, disp_by_sub, op_index),
        "tone_consistency": audit_tone_consistency(comments, disp_by_sub),
        "tone_redlines": audit_redlines(letter_path),
        "letter_structure": audit_letter_structure(comments, letter_path),
    }
    overall = all(c["pass"] for c in checks.values())
    report = {"overall_pass": overall, "checks": checks,
              "note": "FAIL 项修复（改 dispositions 后重跑 generate，或直接改信）后须重跑 audit"}
    with open(os.path.join(out, "audit_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    for name, c in checks.items():
        print(f"[audit] {name}: {'PASS' if c['pass'] else 'FAIL'}")
    for r in checks["off_topic"].get("off_topic_risk", []):
        print(f"  [答非所问] {r['sub_id']}（{r['action_kind']}）：{r['reason']}")
    for key in ("tone_mismatch", "weak_reject", "hollow_accept"):
        for r in checks["tone_consistency"].get(key, []):
            print(f"  [语气一致性/{key}] {r['sub_id']}：{r['reason']}")
    for cat, found in checks["tone_redlines"].get("hits", {}).items():
        for h in found:
            print(f"  [语气红线/{cat}] 第{h['line']}行命中“{h['phrase']}”→ 建议：{h['suggestion'][:50]}…")
    ls = checks["letter_structure"]
    if not ls["pass"]:
        print(f"  [信件完整性] 缺失意见={ls.get('missing_comments')} 子要求={ls.get('missing_subs')}")
    print(f"[audit] overall={'PASS' if overall else 'FAIL'} → "
          f"{os.path.join(out, 'audit_report.json')}")
    return 0 if overall else 1


def main():
    ap = argparse.ArgumentParser(description="逐条回应决策台账引擎：回复信自动生成 + 答非所问检测 + 语气审计")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--stage", default="generate", choices=["generate", "audit"])
    args = ap.parse_args()
    if args.stage == "generate":
        return stage_generate(args.work, args.out)
    return stage_audit(args.work, args.out)


if __name__ == "__main__":
    sys.exit(main())
