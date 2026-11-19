#!/usr/bin/env python3
"""consistency_engine.py — 声称-操作-差异三方对账 + 多轮承诺台账（主攻引擎）。

核心思想（对应评分"对得上"）：
返修交付有三方说法必须一致——
  ① 声称：dispositions.json 的决策/回复 + response_letter.md 的 E# 引用；
  ② 操作：edit_report.json 中实际应用成功的编辑（applied ops）；
  ③ 差异：基线稿件与 revised_manuscript.md 之间的真实行级 diff。
verify_revision 只核对"声称↔操作↔成稿子串"，本引擎再进一步：
核对每一方是否落在【真实差异区域】内部，并跨轮追踪上一轮承诺。

检查项：
A. op→diff：每个 applied op 的 new_text_head 必须落在某个 diff region 内
   （强校验：差异区域内部，而非全稿子串）。找不到 → FAIL「声称已改但无实际差异」。
B. diff→op：每个非豁免 diff region 必须被至少一个 op 认领；
   无认领 → WARN「存在未声明的改动」（可能是重排噪音，列出供人工确认）。
C. 承诺兑现：dispositions 中 decision=采纳/部分采纳 但 edit_ops 与 evidence 均空
   → FAIL「承诺未兑现」。
D. 回复信引用：response_letter.md 中每个 E# 引用必须存在、applied 且落在 diff region。
E. 多轮承诺台账：嗅探上一轮回复信/历史文件，抽取承诺句式，逐条核对本轮是否兑现。

噪音豁免：diff region 两侧去除全部空白字符后完全相等（纯空行/空白差异）自动豁免。

产物：
  /app/output/consistency_report.md   人类可读对账报告（含承诺台账节）
  work/consistency.json               机器可读对账结果
  /app/output/revision_ledger.json    多轮承诺台账

用法:
  python3 consistency_engine.py --work /app/work --out /app/output \
      [--baseline 路径] [--case /input/case.json] [--input-dir /input]
exit: 0=通过（可含 WARN）  1=存在 FAIL 项  2=致命输入缺失
"""
import argparse, difflib, json, os, re, sys

# ---------- 常量 ----------

# 承诺句式标记词表（命中其一即视为承诺句候选）
PROMISE_MARKERS = ["将", "会", "下一步", "下一轮", "后续", "in the next", "we will"]
# 历史回复文件嗅探：文件名命中其一（小写匹配）
HISTORY_NAME_PAT = re.compile(r"response|reply|回复|rebuttal|round|r\d", re.I)
# 当前轮次自产文件名（从历史嗅探中排除）
CURRENT_ROUND_PAT = re.compile(r"^(response_letter|revised_manuscript|consistency_report"
                               r"|revision_ledger|edit_locations|evidence_checklist"
                               r"|result|verification|task)\b", re.I)
# 回复信中的编辑操作引用
RE_OPID = re.compile(r"\bE\d+\b")
# 句子切分
RE_SENT = re.compile(r"(?<=[。！？!?；;])\s*|\n+")
# 停用字符（构造关键词 bigram 前剔除）
RE_STRIP = re.compile(r"[\s，。、：:；;（）()【】《》<>\"'“”‘’\-—…·!！?？/\\|*%#@\[\]{}]+")
# 中文/英文停用词（避免虚词造成虚假重叠）
STOP_TOKENS = {"我们", "将在", "会在", "be", "the", "a", "an", "of", "to", "in",
               "and", "or", "is", "are", "was", "were", "this", "that", "it"}


# ---------- 工具 ----------

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def read_text(path):
    """多编码容错读文本。"""
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError:
            return None
    return None


def squash(s):
    """去除全部空白字符，用于稳健子串匹配。"""
    return re.sub(r"\s+", "", s or "")


def head_of(lines, n=40):
    """取若干行中首个非空行的前 n 字符，作为区域内容头。"""
    for ln in lines:
        if ln.strip():
            return ln.strip()[:n]
    return ""


# ---------- 1. 真实差异计算 ----------

def compute_diff_regions(base_lines, rev_lines):
    """difflib 行级 opcodes → diff region 列表（1-based 行号，含两侧内容头）。

    region = {id, tag, base_start, base_end, rev_start, rev_end,
              base_head, rev_head, base_text, rev_text, exempt, claimed_by}
    """
    sm = difflib.SequenceMatcher(None, [squash(l) for l in base_lines],
                                 [squash(l) for l in rev_lines], autojunk=False)
    regions, rid = [], 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        rid += 1
        b_lines = base_lines[i1:i2]
        r_lines = rev_lines[j1:j2]
        b_txt, r_txt = squash("".join(b_lines)), squash("".join(r_lines))
        # 噪音豁免：两侧去空白后相等（纯空行/缩进/换行差异）
        exempt = (b_txt == r_txt)
        regions.append({
            "id": f"D{rid}", "tag": tag,
            "base_start": i1 + 1, "base_end": i2,      # 1-based，end 取 i2（末行）
            "rev_start": j1 + 1, "rev_end": j2,
            "base_head": head_of(b_lines), "rev_head": head_of(r_lines),
            "base_text": b_txt, "rev_text": r_txt,
            "exempt": exempt, "claimed_by": [],
        })
    return regions


# ---------- 2. 三方对账 ----------

def reconcile_ops(ops, regions):
    """A. 每个 applied op 的 new_text_head 必须落在某个 diff region 内。"""
    fails, mapping = [], {}
    for o in ops:
        if o.get("status") != "applied":
            continue
        oid = o.get("op_id", "?")
        head = squash((o.get("new_text_head") or "")[:30])
        if not head:
            fails.append({"op_id": oid, "reason": "new_text_head 为空，无法对账"})
            continue
        hit = None
        for rg in regions:
            if rg["exempt"]:
                continue
            if head in rg["rev_text"]:
                hit = rg
                break
        if hit:
            hit["claimed_by"].append(oid)
            mapping[oid] = hit["id"]
        else:
            fails.append({"op_id": oid,
                          "reason": "声称已改但其新文本未落在任何真实差异区域内"
                                    "（声称已改但无实际差异）",
                          "new_text_head": (o.get("new_text_head") or "")[:60]})
    return mapping, fails


def reconcile_unclaimed(regions):
    """B. 未被任何 op 认领的非豁免 diff region → WARN。"""
    warns = []
    for rg in regions:
        if rg["exempt"] or rg["claimed_by"]:
            continue
        warns.append({"region": rg["id"], "tag": rg["tag"],
                      "rev_lines": f"{rg['rev_start']}-{rg['rev_end']}",
                      "rev_head": rg["rev_head"],
                      "reason": "存在未声明的改动：无编辑操作认领该区域，"
                                "可能是重排/格式噪音，请人工确认"})
    return warns


def check_dispositions(dispositions):
    """C. 采纳/部分采纳 但 edit_ops 与 evidence 均空 → FAIL 承诺未兑现。"""
    fails = []
    for d in dispositions:
        if d.get("decision") in ("采纳", "部分采纳") \
                and not d.get("edit_ops") and not d.get("evidence"):
            fails.append({"sub_id": d.get("sub_id"),
                          "decision": d.get("decision"),
                          "reason": "承诺采纳却无任何编辑操作或证据条目（承诺未兑现）"})
    return fails


def check_letter_refs(letter, ops, op_region):
    """D. 回复信中每个 E# 引用：存在 + applied + 落在 diff region。"""
    fails, ok_refs = [], []
    op_by_id = {o.get("op_id"): o for o in ops}
    for ref in sorted(set(RE_OPID.findall(letter or ""))):
        o = op_by_id.get(ref)
        if o is None:
            fails.append({"ref": ref, "reason": "回复信引用的编辑操作不存在"})
        elif o.get("status") != "applied":
            fails.append({"ref": ref,
                          "reason": f"引用的操作状态为 {o.get('status')}，未真实应用"})
        elif ref not in op_region:
            fails.append({"ref": ref,
                          "reason": "引用的操作未落在任何真实差异区域内"
                                    "（声称已改但无实际差异）"})
        else:
            ok_refs.append({"ref": ref, "region": op_region[ref]})
    return ok_refs, fails


# ---------- 3. 多轮承诺台账 ----------

def detect_round(case):
    """轮次：constraints.round / revision_round / round，缺省 1。"""
    for container in (case.get("constraints") or {}, case):
        for key in ("round", "revision_round"):
            v = container.get(key)
            if isinstance(v, int) and v >= 1:
                return v
            if isinstance(v, str) and v.isdigit():
                return int(v)
    return 1


def sniff_history_files(input_dir, exclude_paths):
    """在 input_dir 及其 materials/ 下嗅探上一轮回复信/历史版本文件。"""
    found = []
    roots = [input_dir, os.path.join(input_dir, "materials")]
    seen = set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for fn in sorted(files):
                if not fn.lower().endswith((".md", ".txt")):
                    continue
                if not HISTORY_NAME_PAT.search(fn):
                    continue
                if CURRENT_ROUND_PAT.match(fn):
                    continue
                p = os.path.abspath(os.path.join(dirpath, fn))
                if p in seen or p in exclude_paths:
                    continue
                seen.add(p)
                found.append(p)
    return sorted(found)


def extract_promises(text):
    """抽取承诺句式所在句。"""
    promises = []
    for sent in RE_SENT.split(text or ""):
        s = sent.strip().strip("#>*- ").strip()
        if len(s) < 8:
            continue
        low = s.lower()
        if any(m in low for m in ("in the next", "we will")) \
                or any(m in s for m in PROMISE_MARKERS[:5]):
            promises.append(s[:200])
    return promises


def keywords(text):
    """抽取内容 bigram 集合（去停用、去标点）作为兑现判定的关键词。"""
    t = RE_STRIP.sub("", (text or "").lower())
    grams = {t[i:i + 2] for i in range(len(t) - 1)}
    return {g for g in grams if g not in STOP_TOKENS and len(g.strip()) == 2}


def match_promise(promise, dispositions, ops):
    """关键词重叠判定承诺兑现状态；返回 (status, score, best_sub, best_op, note)。"""
    p_kw = keywords(promise)
    if len(p_kw) < 3:
        return "无法判定", 0.0, None, None, "承诺句过短或关键词不足，无法可靠匹配"
    op_by_id = {o.get("op_id"): o for o in ops}
    best, best_score, best_ops = None, 0.0, []
    for d in dispositions:
        target = (d.get("response") or "")
        related_ops = [op_by_id[o] for o in (d.get("edit_ops") or []) if o in op_by_id]
        for o in related_ops:
            target += " " + (o.get("new_text_head") or "") + " " + (o.get("rationale") or "")
        t_kw = keywords(target)
        inter = len(p_kw & t_kw)
        score = inter / max(len(p_kw), 1)
        if score > best_score:
            best, best_score, best_ops = d, score, related_ops
    if best is None or best_score < 0.15:
        return "未兑现", round(best_score, 3), None, None, \
               "本轮 dispositions/编辑操作中未找到可对应内容"
    best_op = best_ops[0].get("op_id") if best_ops else None
    has_placeholder = any(o.get("has_placeholder") for o in best_ops)
    if best_score >= 0.4 and not has_placeholder:
        status, note = "已兑现", "关键词高度重叠且对应修改无占位"
    elif best_score >= 0.4 and has_placeholder:
        status, note = "部分兑现", "内容高度对应但以【待补】占位落实，尚非完整兑现"
    else:
        status, note = "部分兑现", "关键词部分重叠，建议人工复核兑现程度"
    return status, round(best_score, 3), best.get("sub_id"), best_op, note


def build_ledger(round_no, history_files, dispositions, ops):
    """构造承诺台账。返回 (ledger_dict, warns)。"""
    warns = []
    entries = []
    if not history_files:
        if round_no <= 1:
            note = "第 1 轮，无历史承诺"
        else:
            note = (f"第 {round_no} 轮：未嗅探到历史回复文件，按无历史承诺处理；"
                    f"若实际存在上一轮回复信，请确认其命名与位置")
            warns.append({"reason": note})
        return {"round": round_no, "history_files": [], "promises": [],
                "note": note}, warns

    pid = 0
    for path in history_files:
        text = read_text(path) or ""
        for sent in extract_promises(text):
            pid += 1
            status, score, sub_id, op_id, note = match_promise(sent, dispositions, ops)
            entries.append({"promise_id": f"PR{pid}",
                            "quote": sent,
                            "source_file": path,
                            "status": status,
                            "score": score,
                            "matched_sub_id": sub_id,
                            "matched_op": op_id,
                            "note": note})
            if status == "未兑现":
                warns.append({"promise_id": f"PR{pid}", "quote": sent[:60],
                              "reason": "上一轮承诺在本轮未找到兑现痕迹，"
                                        "需补充兑现或在回复信中说明"})
            elif status == "无法判定":
                warns.append({"promise_id": f"PR{pid}", "quote": sent[:60],
                              "reason": "承诺无法判定，列入 uncertainty 人工确认"})
    return {"round": round_no, "history_files": history_files,
            "promises": entries,
            "note": f"第 {round_no} 轮：嗅探到 {len(history_files)} 个历史文件，"
                    f"抽取承诺 {len(entries)} 条"}, warns


# ---------- 4. 报告渲染 ----------

def render_report(ctx):
    L = []
    a = L.append
    a("# 版本一致性对账报告")
    a("")
    a(f"- 对账时间基线：`{ctx['baseline_path']}`")
    a(f"- 修订稿：`{ctx['revised_path']}`")
    a(f"- 差异区域：{ctx['n_regions']} 个（豁免噪音 {ctx['n_exempt']} 个，"
      f"有效 {ctx['n_regions'] - ctx['n_exempt']} 个）")
    a(f"- 已应用编辑操作：{ctx['n_applied']} 个；回复信 E# 引用：{ctx['n_refs']} 处")
    a(f"- 结论：**{'FAIL' if ctx['fail_items'] else 'PASS'}**"
      f"（FAIL {len(ctx['fail_items'])} 项，WARN {len(ctx['warn_items'])} 项）")
    a("")
    a("## 1. 差异区域清单（基线 ↔ 修订稿行级 diff）")
    a("")
    a("| 区域 | 类型 | 基线行 | 修订稿行 | 内容头（修订稿侧） | 认领操作 |")
    a("|-|-|-|-|-|-|")
    for rg in ctx["regions"]:
        if rg["exempt"]:
            continue
        # 纯插入时基线侧无行、纯删除时修订稿侧无行，显示为位置说明而非倒置区间
        b_rng = (f"{rg['base_start']}-{rg['base_end']}" if rg["base_end"] >= rg["base_start"]
                 else f"（第 {rg['base_end']} 行后插入）")
        r_rng = (f"{rg['rev_start']}-{rg['rev_end']}" if rg["rev_end"] >= rg["rev_start"]
                 else "（无对应行）")
        a(f"| {rg['id']} | {rg['tag']} | {b_rng} "
          f"| {r_rng} | {rg['rev_head'] or '（删除）'} "
          f"| {', '.join(rg['claimed_by']) or '—'} |")
    if ctx["n_exempt"]:
        a("")
        a(f"> 另有 {ctx['n_exempt']} 个纯空白差异区域已按噪音豁免规则自动豁免。")
    a("")
    a("## 2. 三方对账（声称 ↔ 操作 ↔ 实际差异）")
    a("")
    a("### 2.1 操作 → 差异区域（每个 applied op 必须落在 diff region 内）")
    a("")
    a("| 操作 | 落点区域 | 校验 |")
    a("|-|-|-|")
    for o in ctx["ops"]:
        if o.get("status") != "applied":
            continue
        oid = o.get("op_id")
        reg = ctx["op_region"].get(oid)
        a(f"| {oid} | {reg or '—'} | {'✅ 落在差异区域内' if reg else '❌ 无实际差异'} |")
    a("")
    a("### 2.2 回复信 E# 引用校验")
    a("")
    if ctx["ok_refs"]:
        for r in ctx["ok_refs"]:
            a(f"- {r['ref']} → 区域 {r['region']} ✅")
    else:
        a("- （回复信中无 E# 引用）")
    a("")
    a("### 2.3 未认领差异区域（可能存在未声明的改动）")
    a("")
    unclaimed = [w for w in ctx["warn_items"] if "region" in w]
    if unclaimed:
        for w in unclaimed:
            a(f"- ⚠️ {w['region']}（{w['tag']}，修订稿行 {w['rev_lines']}）："
              f"{w['rev_head']} —— {w['reason']}")
    else:
        a("- 无。所有有效差异区域均被编辑操作认领。")
    a("")
    a("### 2.4 处置决策承诺校验（采纳但无操作/证据）")
    a("")
    disp_fails = [f for f in ctx["fail_items"] if "sub_id" in f]
    if disp_fails:
        for f in disp_fails:
            a(f"- ❌ {f['sub_id']}（{f['decision']}）：{f['reason']}")
    else:
        a("- 无。所有采纳/部分采纳的处置均有编辑操作或证据支撑。")
    a("")
    a("## 3. 多轮承诺台账")
    a("")
    led = ctx["ledger"]
    a(f"轮次：第 {led['round']} 轮。{led['note']}")
    a("")
    if led["promises"]:
        a("| 编号 | 承诺原文摘录 | 来源文件 | 兑现状态 | 对应子要求/操作 | 说明 |")
        a("|-|-|-|-|-|-|")
        for p in led["promises"]:
            tgt = "/".join(x for x in (p["matched_sub_id"], p["matched_op"]) if x) or "—"
            a(f"| {p['promise_id']} | {p['quote'][:50]} | "
              f"{os.path.basename(p['source_file'])} | {p['status']} | {tgt} | {p['note']} |")
    else:
        a("（无历史承诺条目）")
    a("")
    if ctx["fail_items"]:
        a("## 4. FAIL 项汇总")
        a("")
        for f in ctx["fail_items"]:
            key = f.get("op_id") or f.get("ref") or f.get("sub_id") or "?"
            a(f"- ❌ {key}：{f['reason']}")
        a("")
    return "\n".join(L) + "\n"


# ---------- 主流程 ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--baseline", default=None, help="基线稿件路径，缺省取 structure.json 的 source_file")
    ap.add_argument("--case", default="/input/case.json", help="case.json 路径（读取轮次）")
    ap.add_argument("--input-dir", default="/input", help="历史回复文件嗅探目录")
    args = ap.parse_args()

    # --- 载入输入 ---
    struct = load_json(os.path.join(args.work, "structure.json"), {}) or {}
    edit_report = load_json(os.path.join(args.work, "edit_report.json"), {}) or {}
    dispositions = load_json(os.path.join(args.work, "dispositions.json"), []) or []
    case = load_json(args.case, {}) or {}

    base_path = args.baseline or struct.get("source_file")
    rev_path = os.path.join(args.out, "revised_manuscript.md")
    letter_path = os.path.join(args.out, "response_letter.md")

    if not base_path or not os.path.exists(base_path):
        print(f"[consistency][FATAL] 基线稿件不可读: {base_path}", file=sys.stderr)
        return 2
    base_text = read_text(base_path)
    rev_text = read_text(rev_path)
    if base_text is None or rev_text is None:
        print("[consistency][FATAL] 基线或修订稿读取失败", file=sys.stderr)
        return 2
    letter = read_text(letter_path) or ""
    if not os.path.exists(letter_path):
        print("[consistency][WARN] 缺 response_letter.md，E# 引用校验跳过", file=sys.stderr)

    ops = edit_report.get("ops", [])

    # --- 1. 差异计算 ---
    regions = compute_diff_regions(base_text.splitlines(), rev_text.splitlines())

    # --- 2. 三方对账 ---
    op_region, op_fails = reconcile_ops(ops, regions)
    unclaimed_warns = reconcile_unclaimed(regions)
    disp_fails = check_dispositions(dispositions)
    ok_refs, ref_fails = check_letter_refs(letter, ops, op_region) if letter else ([], [])

    # --- 3. 承诺台账 ---
    round_no = detect_round(case)
    exclude = {os.path.abspath(base_path)}
    history = sniff_history_files(args.input_dir, exclude)
    ledger, ledger_warns = build_ledger(round_no, history, dispositions, ops)

    fail_items = op_fails + disp_fails + ref_fails
    warn_items = unclaimed_warns + ledger_warns

    # --- 4. 写产物 ---
    os.makedirs(args.out, exist_ok=True)
    n_exempt = sum(1 for r in regions if r["exempt"])
    ctx = {"baseline_path": base_path, "revised_path": rev_path,
           "regions": regions, "n_regions": len(regions), "n_exempt": n_exempt,
           "ops": ops, "n_applied": sum(1 for o in ops if o.get("status") == "applied"),
           "op_region": op_region, "ok_refs": ok_refs, "n_refs": len(ok_refs),
           "fail_items": fail_items, "warn_items": warn_items, "ledger": ledger}
    with open(os.path.join(args.out, "consistency_report.md"), "w", encoding="utf-8") as f:
        f.write(render_report(ctx))
    with open(os.path.join(args.out, "revision_ledger.json"), "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.work, "consistency.json"), "w", encoding="utf-8") as f:
        json.dump({"overall_pass": not fail_items,
                   "round": round_no,
                   "n_regions": len(regions), "n_exempt": n_exempt,
                   "op_region": op_region,
                   "unclaimed_regions": [w for w in warn_items if "region" in w],
                   "fail_items": fail_items, "warn_items": warn_items,
                   "n_promises": len(ledger["promises"])},
                  f, ensure_ascii=False, indent=1)

    # --- 5. 摘要与退出码 ---
    print(f"[consistency] diff 区域={len(regions)}（豁免 {n_exempt}） "
          f"applied_op={ctx['n_applied']} 落点={len(op_region)} "
          f"未认领区域={len(unclaimed_warns)}")
    print(f"[consistency] 承诺台账：round={round_no} 历史文件={len(history)} "
          f"承诺={len(ledger['promises'])} "
          f"（已兑现={sum(1 for p in ledger['promises'] if p['status'] == '已兑现')} "
          f"部分兑现={sum(1 for p in ledger['promises'] if p['status'] == '部分兑现')} "
          f"未兑现={sum(1 for p in ledger['promises'] if p['status'] == '未兑现')} "
          f"无法判定={sum(1 for p in ledger['promises'] if p['status'] == '无法判定')}）")
    for it in fail_items:
        key = it.get("op_id") or it.get("ref") or it.get("sub_id") or "?"
        print(f"[consistency][FAIL] {key}: {it['reason']}", file=sys.stderr)
    for it in warn_items:
        print(f"[consistency][WARN] {it.get('region') or it.get('promise_id') or ''}: "
              f"{it['reason']}", file=sys.stderr)
    print(f"[consistency] overall={'PASS' if not fail_items else 'FAIL'}")
    return 1 if fail_items else 0


if __name__ == "__main__":
    sys.exit(main())
