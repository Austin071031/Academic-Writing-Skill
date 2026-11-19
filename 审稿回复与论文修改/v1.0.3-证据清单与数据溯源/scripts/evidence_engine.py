#!/usr/bin/env python3
"""evidence_engine.py — 证据需求自动建档 + 回复/修订稿数字逐条溯源（V4 主攻引擎）。

两个子阶段（--stage）：

demand（证据需求建档，步骤 4 后运行）：
  读 work/comments.json + work/dispositions.json + work/edit_plan.json
  （若已存在 work/edit_report.json 则以其 applied 状态为准），
  为每个 needs_evidence=true 的子要求自动建立 EV 条目：
  - demand 由 action_kind 映射（add_experiment→补实验 / add_data→补数据 /
    add_citation→补文献 / reanalysis→重做分析 / 其他→其他证据）；
  - 同一证据被多个子要求共享（dispositions 引用同一 EV 编号，或同意见同需求类型）
    只建一条，条目内列出全部 sub_id；
  - status 初判：引用的 op 已应用且 new_text 无【待补】→到位；有 op 但含【待补】
    →部分到位；无 op →无法补做。初判仅供 Agent 复核，Agent 手工修订
    work/evidence_checklist.json 后重跑本脚本，已修订条目会被保留（按 sub_ids 匹配）。
  产物：work/evidence_checklist.json + /app/output/evidence_checklist.md 草稿。

provenance（交付前溯源核验，步骤 7 运行）：
  1. 数字溯源：抽取 /app/output/response_letter.md 与所有 applied op 的 new_text
     中的全部数字（含百分数），逐个判定：
       基线全文可找到          → 溯源成功（记录 baseline P### 与行号）；
       意见原文可找到          → 意见给出（溯源到 comments.json 的 sub_id）；
       邻近（±20 字）有【待补】  → 待补；
       以上皆非                → 未核实，写入 work/manual_confirmations.json 草稿。
     数字来自意见原文不算未核实（exit 仍为 0 的前提之一）。
  2. 证据-论断映射：为每条 EV 与其关联子要求的 response 生成
     work/evidence_map.json 条目（claim/source/kind）。
  产物：/app/output/provenance_report.md + work/provenance.json +
        work/evidence_map.json + work/manual_confirmations.json（合并草稿）。
  exit：0=全部溯源通过；2=存在未核实数字（告警，不硬 FAIL）。

用法:
  python3 evidence_engine.py --work /app/work --out /app/output --stage demand
  python3 evidence_engine.py --work /app/work --out /app/output --stage provenance
"""
import argparse, json, os, re, sys

PLACEHOLDER = re.compile(r"【待补[:：].*?】")
# 数字 token：整数/小数/百分数；两侧不得紧邻 ASCII 字母数字下划线（排除 R1/E1/P005/EV2 等编号），
# 小数点后的数字不重复匹配（lookbehind 含 "."）。
RE_NUM = re.compile(r"(?<![A-Za-z0-9_.])\d+(?:\.\d+)?\s*%?(?![A-Za-z0-9_])")

DEMAND_MAP = {"add_experiment": "补实验", "add_data": "补数据",
              "add_citation": "补文献", "reanalysis": "重做分析"}

# 各需求类型的替代说明模板（note 字段，供 Agent 改写）
NOTE_TEMPLATES = {
    "补实验": "无法补做时：说明实验条件已不存在（如样品已耗尽、装置已拆除、测试周期"
              "超出返修期限），提供等效佐证（相近工艺的已发表数据、补充表征）或在"
              "修订稿中加入局限声明，不得以模拟数据冒充实验结果。",
    "补数据": "无法补做时：说明原始数据未采集或不可得，改以定性说明加局限声明；可在"
              "可获得范围内提供部分数据并标注样本量与置信度，缺失部分保留【待补】占位。",
    "补文献": "无法补做时：说明本环境无法联网核验文献，列出建议检索关键词与预期结论"
              "方向，请作者核实后补引；禁止编造文献条目或冒称已核验。",
    "重做分析": "无法补做时：说明原始数据或分析代码不可得，给出拟采用的分析方法、统计"
                "检验与判读标准，请作者用原始数据复跑后回填结果。",
    "其他证据": "无法补做时：说明缺口原因（材料外、条件不存在或超出文本修订范围），"
                "给出等效佐证或局限声明，并保留【待补】占位与人工确认项。",
}


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def read_text(path):
    """多编码兜底读文本。"""
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError:
            return ""
    return ""


def norm_num(tok):
    """数字 token 归一化：去掉 % 前空白，便于与基线比对。"""
    return re.sub(r"\s+%", "%", tok.strip())


def num_pattern(tok):
    """为具体数字 token 构造边界检索正则（防止命中 1450 中的 45、1.5 中的 5）。"""
    return re.compile(r"(?<![A-Za-z0-9_.])" + re.escape(tok) + r"(?![A-Za-z0-9_.%])"
                      if not tok.endswith("%") else
                      r"(?<![A-Za-z0-9_.])" + re.escape(tok) + r"(?![A-Za-z0-9_.])")


def iter_subs(comments):
    for c in comments.get("comments", []):
        for s in c.get("sub_requests", []):
            yield c, s


# ---------------------------------------------------------------- stage demand
def run_demand(work, out):
    comments = load_json(os.path.join(work, "comments.json"), {}) or {}
    dispositions = load_json(os.path.join(work, "dispositions.json"), []) or []
    plan = load_json(os.path.join(work, "edit_plan.json"), []) or []
    report = load_json(os.path.join(work, "edit_report.json"), {}) or {}
    if not comments.get("comments"):
        print("[evidence_engine][FATAL] comments.json 缺失或无意见，先跑 parse_comments",
              file=sys.stderr)
        return 1

    disp_by_sub = {d.get("sub_id"): d for d in dispositions}
    plan_by_id = {o.get("op_id"): o for o in plan}
    applied_ids = {o["op_id"] for o in report.get("ops", [])
                   if o.get("status") == "applied"} if report.get("ops") else None
    op_para = {o["op_id"]: o.get("para_id") for o in report.get("ops", [])}

    # 1. 分组：同一证据被多个子要求共享时只建一条
    #    共享信号：dispositions 引用同一 EV 编号（最强）；
    #    否则同一条意见内、同一需求类型的子要求视为共享。
    groups, gindex = [], {}
    for c, s in iter_subs(comments):
        if not s.get("needs_evidence"):
            continue
        demand = DEMAND_MAP.get(s.get("action_kind"), "其他证据")
        disp = disp_by_sub.get(s["sub_id"], {})
        ref_evs = [e for e in (disp.get("evidence") or []) if e]
        key = ("ev", ref_evs[0]) if ref_evs else ("auto", c.get("id"), demand)
        if key in gindex:
            g = groups[gindex[key]]
            g["subs"].append(s)
            g["ref_evs"] |= set(ref_evs)
        else:
            gindex[key] = len(groups)
            groups.append({"comment_id": c.get("id"), "demand": demand,
                           "subs": [s], "ref_evs": set(ref_evs),
                           "disps": [disp] if disp else []})
        if disp and disp not in groups[gindex[key]]["disps"]:
            groups[gindex[key]]["disps"].append(disp)

    # 2. 既有清单：按 sub_ids 集合匹配，保留 Agent 手工修订
    old_entries = load_json(os.path.join(work, "evidence_checklist.json"), []) or []
    old_by_subs = {}
    for e in old_entries:
        subs = e.get("sub_ids") or ([e["sub_id"]] if e.get("sub_id") else [])
        old_by_subs[frozenset(subs)] = e

    # 3. 逐组建档
    taken, entries = set(), []
    # 第一轮：dispositions 显式引用的 EV 编号优先保留
    for g in groups:
        g["ev_id"] = None
        for ev in sorted(g["ref_evs"]):
            if ev not in taken:
                g["ev_id"], _ = ev, taken.add(ev)
                break
    n = 0
    for g in groups:
        if g["ev_id"] is None:
            while True:
                n += 1
                if f"EV{n}" not in taken:
                    g["ev_id"] = f"EV{n}"
                    taken.add(g["ev_id"])
                    break

    for g in groups:
        sub_ids = [s["sub_id"] for s in g["subs"]]
        # 关联 op：组内全部 disposition 引用的、edit_plan 中存在的 op
        ops, paras = [], []
        for d in g["disps"]:
            for oid in d.get("edit_ops", []):
                if oid in plan_by_id and oid not in ops:
                    if applied_ids is not None and oid not in applied_ids:
                        continue  # 有编辑报告时只认 applied
                    ops.append(oid)
                    pid = op_para.get(oid) or plan_by_id[oid].get("para_id")
                    if pid and pid not in paras:
                        paras.append(pid)
        has_ph = any(PLACEHOLDER.search(plan_by_id[o].get("new_text") or "")
                     for o in ops)
        # 状态初判（仅供 Agent 复核，终判权在 Agent）
        if ops and not has_ph:
            status = "到位"
            source = "baseline " + "、".join(paras) if paras else "baseline（见编辑报告）"
            note = "证据已随修改落稿，请人工复核数值与出处一致性。"
        elif ops:
            status = "部分到位"
            base = ("baseline " + "、".join(paras) + "（" + "、".join(ops) + " 落稿处）；"
                    if paras else "")
            source = base + "证据本体材料外，待作者补充"
            note = ("已落稿但含【待补】占位，证据到位后替换占位。" +
                    NOTE_TEMPLATES[g["demand"]])
        else:
            status = "无法补做"
            source = "材料外，待作者补充"
            note = NOTE_TEMPLATES[g["demand"]]

        entry = {"ev_id": g["ev_id"], "sub_ids": sub_ids, "sub_id": sub_ids[0],
                 "comment_id": g["comment_id"], "demand": g["demand"],
                 "status": status, "source": source, "note": note,
                 "related_ops": ops,
                 "generated_by": "evidence_engine demand（初判，Agent 终判）"}
        old = old_by_subs.get(frozenset(sub_ids))
        if old:  # 保留 Agent 手工修订的字段
            for fld in ("status", "source", "note"):
                if old.get(fld):
                    entry[fld] = old[fld]
            if old.get("ev_id") and old["ev_id"] not in taken - {g["ev_id"]}:
                entry["ev_id"] = old["ev_id"]
            entry["generated_by"] = "evidence_engine demand + Agent 复核"
        entries.append(entry)

    os.makedirs(work, exist_ok=True)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(work, "evidence_checklist.json"), "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=1)

    # Markdown 草稿
    lines = ["# 证据清单（补实验 / 补数据 / 补文献 / 重做分析）",
             "",
             "> 本表由 evidence_engine --stage demand 自动生成草稿；「到位状态」为脚本初判，",
             "> 最终以 Agent/作者复核为准。修订 work/evidence_checklist.json 后重跑本脚本，",
             "> 已修订条目按 sub_ids 匹配保留。红线：未到位证据不得冒称已补做、不得编造数据。",
             "",
             "| 编号 | 关联子要求 | 需求类型 | 到位状态 | 出处 | 替代说明 / 下一步 |",
             "|-|-|-|-|-|-|"]
    for e in entries:
        lines.append("| {ev_id} | {subs} | {demand} | {status} | {source} | {note} |".format(
            ev_id=e["ev_id"], subs="、".join(e["sub_ids"]), demand=e["demand"],
            status=e["status"], source=e["source"],
            note=e["note"].replace("|", "／")))
    lines += ["",
              "## 填写与使用规则",
              "",
              "- 到位：证据（数据/文献/实验结果）已真实写入修订稿，无【待补】残留；",
              "- 部分到位：修改已落稿但含【待补：…】占位，证据到位前不得删除占位标记；",
              "- 无法补做：本环境/材料内无法获得，必须在回复信中给出替代说明并列入人工确认；",
              "- 同一证据服务多个子要求时只占一行，关联子要求列全部 sub_id。"]
    with open(os.path.join(out, "evidence_checklist.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    stat = {}
    for e in entries:
        stat[e["status"]] = stat.get(e["status"], 0) + 1
    print(f"[evidence_engine] demand: EV 条目={len(entries)} 状态分布={stat} "
          f"→ evidence_checklist.json / evidence_checklist.md")
    return 0


# ------------------------------------------------------------ stage provenance
def find_in_baseline(tok, base_lines, paragraphs):
    """在基线中定位 token：返回 (P###, 行号) 或 (None, None)。"""
    pat = num_pattern(tok)
    pid = None
    for p in paragraphs:
        if pat.search(p.get("text", "")):
            pid = p["id"]
            break
    lineno = None
    for i, line in enumerate(base_lines, 1):
        if pat.search(line):
            lineno = i
            break
    return pid, lineno


def find_in_comments(tok, comments):
    """在意见原文中定位 token：返回 sub_id 或 comment_id 或 None。"""
    pat = num_pattern(tok)
    for c, s in iter_subs(comments):
        if pat.search(s.get("text", "")):
            return s["sub_id"]
    for c in comments.get("comments", []):
        if pat.search(c.get("raw_text", "")):
            return c.get("id")
    return None


def placeholder_spans(text):
    return [(m.start(), m.end()) for m in PLACEHOLDER.finditer(text)]


def extract_numbers(text, location):
    """抽取数字出现：返回 [{number, context, in_placeholder, near_placeholder}]。"""
    spans = placeholder_spans(text)
    items = []
    for m in RE_NUM.finditer(text):
        s, e = m.start(), m.end()
        # 结构性编号不算数据：## Reviewer 1 / Reviewer 2 等标题中的审稿人序号
        if re.search(r"Reviewer\s*$", text[:s], re.I):
            continue
        tok = norm_num(m.group(0))
        in_ph = any(a <= s < b for a, b in spans)
        window = text[max(0, s - 20):e + 20]
        near_ph = ("【待补" in window) or in_ph
        ctx = text[max(0, s - 20):min(len(text), e + 20)]
        items.append({"number": tok, "location": location,
                      "context": ctx.replace("\n", " "),
                      "in_placeholder": in_ph, "near_placeholder": near_ph})
    return items


def run_provenance(work, out):
    comments = load_json(os.path.join(work, "comments.json"), {}) or {}
    dispositions = load_json(os.path.join(work, "dispositions.json"), []) or []
    plan = load_json(os.path.join(work, "edit_plan.json"), []) or []
    report = load_json(os.path.join(work, "edit_report.json"), {}) or {}
    struct = load_json(os.path.join(work, "structure.json"), {}) or {}
    checklist = load_json(os.path.join(work, "evidence_checklist.json"), []) or []

    base_path = struct.get("source_file")
    base_text = read_text(base_path) if base_path else ""
    if not base_text:
        print("[evidence_engine][WARN] 基线原文不可读，全部数字将无法溯源", file=sys.stderr)
    base_lines = base_text.splitlines()
    paragraphs = struct.get("paragraphs", [])

    # 1. 收集待溯源文本：回复信 + applied op 的 new_text
    applied_ids = {o["op_id"] for o in report.get("ops", [])
                   if o.get("status") == "applied"}
    occurrences = []
    letter_p = os.path.join(out, "response_letter.md")
    if os.path.exists(letter_p):
        for i, line in enumerate(read_text(letter_p).splitlines(), 1):
            occurrences += extract_numbers(line, f"response_letter.md L{i}")
    else:
        print("[evidence_engine][WARN] 缺 response_letter.md，仅溯源编辑操作",
              file=sys.stderr)
    for op in plan:
        oid = op.get("op_id")
        if applied_ids and oid not in applied_ids:
            continue  # 有编辑报告时只溯源真实落稿的 op
        occurrences += extract_numbers(op.get("new_text") or "", f"{oid} new_text")

    # 2. 逐数字判定（去重：同数字同位置只保留一条）
    rows, seen = [], set()
    for oc in occurrences:
        key = (oc["number"], oc["location"])
        if key in seen:
            continue
        seen.add(key)
        tok = oc["number"]
        pid, lineno = find_in_baseline(tok, base_lines, paragraphs)
        if pid or lineno:
            verdict = "溯源成功"
            src = "baseline"
            if pid:
                src += " " + pid
            if lineno:
                src += f" L{lineno}"
        else:
            cid = find_in_comments(tok, comments)
            if cid:
                verdict, src = "意见给出", f"comments {cid}"
            elif oc["near_placeholder"]:
                verdict, src = "待补", "【待补】占位（邻近标记）"
            else:
                verdict, src = "未核实", "基线与意见原文均未找到"
        rows.append({"number": tok, "location": oc["location"],
                     "context": oc["context"], "verdict": verdict, "source": src})

    unverified = [r for r in rows if r["verdict"] == "未核实"]

    # 3. 证据-论断映射：EV 条目 × 关联子要求的 response
    disp_by_sub = {d.get("sub_id"): d for d in dispositions}
    evidence_map = []
    for e in checklist:
        for sid in e.get("sub_ids") or ([e["sub_id"]] if e.get("sub_id") else []):
            d = disp_by_sub.get(sid, {})
            claim = (d.get("response") or "").strip()
            if not claim:
                claim = f"{sid}（{e['demand']}）"
            if e.get("status") == "到位":
                kind = "evidence"
            elif e.get("status") in ("部分到位", "无法补做"):
                kind = "placeholder"
            else:
                kind = "evidence"
            evidence_map.append({"claim": claim[:300],
                                 "source": f"{e['ev_id']}（{e.get('source', '')}）",
                                 "kind": kind})
    with open(os.path.join(work, "evidence_map.json"), "w", encoding="utf-8") as f:
        json.dump(evidence_map, f, ensure_ascii=False, indent=1)

    # 4. 未核实数字 → manual_confirmations.json 合并草稿（不覆盖已有条目）
    mc_p = os.path.join(work, "manual_confirmations.json")
    manual = load_json(mc_p, []) or []
    if not isinstance(manual, list):
        manual = []
    added = 0
    for r in unverified:
        item = (f"【数字溯源】'{r['number']}'（{r['location']}，上下文：…{r['context']}…）"
                f"未在基线与意见原文中找到来源，请作者确认出处或改为【待补：…】占位")
        if item not in manual:
            manual.append(item)
            added += 1
    with open(mc_p, "w", encoding="utf-8") as f:
        json.dump(manual, f, ensure_ascii=False, indent=1)

    # 5. provenance.json + 报告
    summary = {"n_numbers": len(rows),
               "verified": sum(1 for r in rows if r["verdict"] == "溯源成功"),
               "from_comments": sum(1 for r in rows if r["verdict"] == "意见给出"),
               "placeholder": sum(1 for r in rows if r["verdict"] == "待补"),
               "unverified": len(unverified),
               "n_evidence_map": len(evidence_map)}
    prov = {"summary": summary, "numbers": rows,
            "unverified_numbers": [dict(r) for r in unverified],
            "evidence_map_entries": len(evidence_map)}
    with open(os.path.join(work, "provenance.json"), "w", encoding="utf-8") as f:
        json.dump(prov, f, ensure_ascii=False, indent=1)

    lines = ["# 数字溯源报告（provenance）",
             "",
             "> 由 evidence_engine --stage provenance 生成。回复信与已落稿修改中的每个数字",
             "> 逐一与基线全文、意见原文比对；「未核实」条目已自动写入 manual_confirmations.json，",
             "> 须由作者确认出处或改为【待补】占位后方可交付 success。",
             "",
             f"- 数字总数：{summary['n_numbers']}；溯源成功 {summary['verified']}；"
             f"意见给出 {summary['from_comments']}；待补 {summary['placeholder']}；"
             f"**未核实 {summary['unverified']}**",
             "",
             "| 数字 | 出现位置 | 基线/意见来源 | 判定 |",
             "|-|-|-|-|"]
    for r in rows:
        ctx = r["context"].replace("|", "／")
        lines.append(f"| {r['number']} | {r['location']}（…{ctx}…） | "
                     f"{r['source']} | {r['verdict']} |")
    if unverified:
        lines += ["", "## 待人工确认（未核实数字）", ""]
        for r in unverified:
            lines.append(f"- `{r['number']}` @ {r['location']}：…{r['context']}…")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "provenance_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[evidence_engine] provenance: 数字={summary['n_numbers']} "
          f"溯源成功={summary['verified']} 意见给出={summary['from_comments']} "
          f"待补={summary['placeholder']} 未核实={summary['unverified']} "
          f"evidence_map={len(evidence_map)} 新增人工确认={added}")
    if unverified:
        print(f"[evidence_engine][WARN] 存在 {len(unverified)} 个未核实数字，"
              f"已写入 manual_confirmations.json（exit=2 告警）", file=sys.stderr)
        return 2
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--stage", required=True, choices=["demand", "provenance"])
    args = ap.parse_args()
    if args.stage == "demand":
        return run_demand(args.work, args.out)
    return run_provenance(args.work, args.out)


if __name__ == "__main__":
    sys.exit(main())
