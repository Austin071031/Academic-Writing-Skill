#!/usr/bin/env python3
"""decompose_engine.py — 意见拆解主攻引擎：子要求矩阵 + 交叉冲突检测 + 覆盖台账。

对应题面"答得全"：每条意见及其包含的多个子要求是否都被识别并给出明确处理结论。

两个阶段：
  first   仅读 comments.json → 拆解矩阵草稿 + 跨意见重叠/冲突/依赖检测
          （Agent 据此时复核拆分、修订 comments.json）
  audit   再读 dispositions.json + edit_report.json → 覆盖台账与缺口清单

用法:
  python3 decompose_engine.py --work /app/work --out /app/output --stage first
  python3 decompose_engine.py --work /app/work --out /app/output --stage audit
输出: out/decomposition_report.md ; work/decomposition.json
"""
import argparse, json, os, re, sys

STOP = set("的了和是在有与被对为其及或并而于中上下一二等不没无这那你也我他她它们"
           "the a an of to in on for and or with by is are was were be been")

def tokens(text):
    """中英混合 3-gram 字符切片 + 英文词，用于重叠检测。"""
    text = re.sub(r"\s+", "", text.lower())
    cn = re.sub(r"[a-z0-9]", "", text)
    grams = {cn[i:i + 3] for i in range(max(0, len(cn) - 2))}
    words = {w for w in re.findall(r"[a-z]{3,}", text) if w not in STOP}
    return grams | words

def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0

CONTRA = [("删除", "补充"), ("删去", "增加"), ("压缩", "扩展"), ("缩短", "增加"),
          ("remove", "add"), ("delete", "include"), ("shorten", "expand")]

def load_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def build_matrix(comments, disp_by_sub, ops_by_id):
    rows = []
    for c in comments.get("comments", []):
        for s in c["sub_requests"]:
            d = disp_by_sub.get(s["sub_id"], {})
            ops = d.get("edit_ops", [])
            op_status = ";".join(f"{o}:{ops_by_id.get(o, {}).get('status', '?')}"
                                 for o in ops) or "—"
            rows.append({
                "sub_id": s["sub_id"], "comment_id": c["id"], "reviewer": c["reviewer"],
                "text": s["text"], "type": s["type"], "severity": s["severity"],
                "action_kind": s["action_kind"], "needs_evidence": s["needs_evidence"],
                "decision": d.get("decision", "（未处置）"),
                "edit_ops": ops, "op_status": op_status,
                "evidence": d.get("evidence", []),
                "covered": bool(d.get("decision")) and bool((d.get("response") or "").strip()),
            })
    return rows

def detect_relations(rows):
    """跨意见重叠 / 冲突 / 证据依赖检测。"""
    overlaps, conflicts, evid_groups = [], [], {}
    toks = {r["sub_id"]: tokens(r["text"]) for r in rows}
    ids = [r["sub_id"] for r in rows]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = rows[i], rows[j]
            if a["comment_id"] == b["comment_id"]:
                continue
            sim = jaccard(toks[ids[i]], toks[ids[j]])
            if sim >= 0.35:
                pair = {"a": ids[i], "b": ids[j], "similarity": round(sim, 2)}
                contra = None
                for w1, w2 in CONTRA:
                    if (w1 in a["text"] and w2 in b["text"]) or (w2 in a["text"] and w1 in b["text"]):
                        contra = f"{w1}↔{w2}"
                        break
                if contra:
                    pair["conflict_signal"] = contra
                    conflicts.append(pair)
                else:
                    overlaps.append(pair)
    for r in rows:
        if r["needs_evidence"]:
            key = re.sub(r"\d+", "", r["text"])[:12]
            evid_groups.setdefault(key, []).append(r["sub_id"])
    deps = [{"shared_evidence_hint": k, "sub_ids": v}
            for k, v in evid_groups.items() if len(v) > 1]
    return overlaps, conflicts, deps

def render(rows, overlaps, conflicts, deps, stage, comments):
    L = ["# 意见拆解报告（子要求矩阵与覆盖台账）", ""]
    st = comments.get("stats", {})
    L.append(f"- 意见数：{st.get('n_comments')}；子要求数：{st.get('n_sub_requests')}；"
             f"含多子要求的意见：{st.get('n_multi_sub_comments')}；需证据子要求：{st.get('n_needs_evidence')}")
    L.append(f"- 阶段：{'拆解草稿（待 Agent 复核）' if stage == 'first' else '覆盖台账（终版）'}")
    L.append("")
    L.append("## 1. 子要求矩阵")
    L.append("")
    L.append("| 子要求ID | 审稿人 | 意见 | 类型 | 严重度 | 动作 | 需证据 | 决策 | 编辑操作(状态) | 证据 |")
    L.append("|-|-|-|-|-|-|-|-|-|-|")
    for r in rows:
        txt = r["text"].replace("|", "｜")
        txt = txt[:60] + ("…" if len(txt) > 60 else "")
        L.append(f"| {r['sub_id']} | {r['reviewer']} | {txt} | {r['type']} | "
                 f"{r['severity']} | {r['action_kind']} | {'是' if r['needs_evidence'] else '否'} | "
                 f"{r['decision']} | {r['op_status']} | {','.join(r['evidence']) or '—'} |")
    L.append("")
    L.append("## 2. 跨意见重叠（同一问题被多位审稿人/多条意见提及，应合并回应并互相引用）")
    L.append("")
    if overlaps:
        for o in overlaps:
            L.append(f"- {o['a']} ↔ {o['b']}（相似度 {o['similarity']}）：回应中注明“同 R x-C y”")
    else:
        L.append("- 未检出")
    L.append("")
    L.append("## 3. 潜在冲突（要求方向相反，必须人工裁决并在回复信中说明取舍）")
    L.append("")
    if conflicts:
        for c in conflicts:
            L.append(f"- ⚠ {c['a']} ↔ {c['b']}：{c['conflict_signal']}（相似度 {c['similarity']}）")
    else:
        L.append("- 未检出")
    L.append("")
    L.append("## 4. 证据依赖分组（共享同一证据需求的子要求，证据清单只列一次、多处引用）")
    L.append("")
    if deps:
        for d in deps:
            L.append(f"- {', '.join(d['sub_ids'])}（线索：{d['shared_evidence_hint']}…）")
    else:
        L.append("- 未检出")
    L.append("")
    if stage == "audit":
        L.append("## 5. 覆盖台账审计（答得全）")
        L.append("")
        missing = [r["sub_id"] for r in rows if not r["covered"]]
        if missing:
            L.append(f"- ❌ 未给出明确处置结论的子要求：{', '.join(missing)}")
        else:
            L.append("- ✅ 全部子要求均有明确决策与回复")
        bad_ops = [f"{r['sub_id']}:{r['op_status']}" for r in rows
                   if r["edit_ops"] and "failed" in r["op_status"]]
        if bad_ops:
            L.append(f"- ❌ 引用了失败编辑操作：{'; '.join(bad_ops)}")
        L.append("")
    return "\n".join(L)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--stage", choices=["first", "audit"], default="first")
    args = ap.parse_args()

    comments = load_json(os.path.join(args.work, "comments.json"))
    if not comments:
        print("[decompose][FATAL] 缺 comments.json，先跑 parse_comments.py", file=sys.stderr)
        return 1
    dispositions = load_json(os.path.join(args.work, "dispositions.json"), []) or []
    edit_report = load_json(os.path.join(args.work, "edit_report.json"), {}) or {}
    if args.stage == "audit" and not dispositions:
        print("[decompose][FATAL] audit 阶段缺 dispositions.json", file=sys.stderr)
        return 1

    disp_by_sub = {d.get("sub_id"): d for d in dispositions}
    ops_by_id = {o["op_id"]: o for o in edit_report.get("ops", [])}
    rows = build_matrix(comments, disp_by_sub, ops_by_id)
    overlaps, conflicts, deps = detect_relations(rows)

    os.makedirs(args.out, exist_ok=True)
    report = render(rows, overlaps, conflicts, deps, args.stage, comments)
    with open(os.path.join(args.out, "decomposition_report.md"), "w", encoding="utf-8") as f:
        f.write(report)
    with open(os.path.join(args.work, "decomposition.json"), "w", encoding="utf-8") as f:
        json.dump({"stage": args.stage, "rows": rows, "overlaps": overlaps,
                   "conflicts": conflicts, "evidence_deps": deps}, f, ensure_ascii=False, indent=1)

    n_cov = sum(1 for r in rows if r["covered"])
    print(f"[decompose] stage={args.stage} 子要求={len(rows)} 已覆盖={n_cov} "
          f"重叠={len(overlaps)} 冲突={len(conflicts)} 证据依赖={len(deps)}")
    if args.stage == "audit" and n_cov < len(rows):
        print("[decompose][WARN] 存在未覆盖子要求，详见报告第 5 节", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(main())
