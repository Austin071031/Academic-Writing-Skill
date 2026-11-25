#!/usr/bin/env python3
"""apply_preview.py — 为每条 finding 生成"改前/改后对照预览"（v2.0.2 新增，纯标准库）。

用法: python3 apply_preview.py --work /app/work --out /app/output
时机: 在 report_builder.py 之后运行；Agent 复核增删 findings 后可重跑（幂等）。

输入:  out/findings.json（复核后亦可）、work/structure.json
输出:  work/previews.json            —— [{id, op, before, after, note}]
       out/diagnosis_report.md       —— 每个 finding 块末尾注入两行对照
       out/edit_plan.json            —— 每个 op 增加 "preview" 字段

原则:
- 确定性模板生成，同一 finding 多次运行结果一致；
- after 一律标注"建议示例（非最终文本）"，不新增材料外事实；
- before 只引用原文锚点 quote / 原文段落 snippet。
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scanutil import short  # 复用父辈工具，保持 short() 口径一致

NOTE = "建议示例（非最终文本）"
MAX_PREVIEWS = 12
SEV_ORDER = {"high": 0, "medium": 1, "low": 2}


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def para_index(model):
    paras = model.get("paragraphs") or []
    return {p["id"]: p for p in paras}, [p["id"] for p in paras]


def prev_para_id(order, pid):
    if pid in order:
        i = order.index(pid)
        if i > 0:
            return order[i - 1]
    return None


def make_preview(f, model, pmap, order):
    """按 op 的确定性模板生成对照预览。"""
    op = (f.get("action") or {}).get("op", "")
    instr = (f.get("action") or {}).get("instruction", "")
    quote = f.get("quote") or ""
    loc = f.get("location") or {}
    pid = loc.get("para_id")
    sec = loc.get("section") or "(全文)"
    evidence = f.get("evidence") or ""
    para = pmap.get(pid) or {}
    ptext = para.get("text") or quote

    if op in ("narrow", "qualify"):
        before = quote or short(ptext, 60)
        after = (f"{before} 【建议收窄为：保留原句数据部分，删改绝对化/无源表述，"
                 f"补“在本文实验条件下”类限定语。占位示例（据编辑指令生成）：{short(instr, 80)}】")
    elif op in ("add", "add_transition", "add_limitation"):
        kind = {"add": "补充句", "add_transition": "过渡句", "add_limitation": "局限句"}[op]
        prev = prev_para_id(order, pid)
        pos = f"{pid}（{sec}）" if pid else sec
        before = f"插入位置：{pos} 段首/段末（现文：{short(ptext, 60)}）"
        if op == "add_transition" and prev:
            after = (f"【插入过渡句：承接 {prev} 的 X，引出本段 Y】"
                     f"占位示例（据编辑指令生成）：{short(instr, 80)}")
        else:
            after = f"【插入{kind}：{short(instr, 90)}】"
    elif op == "move":
        before = f"源位置 {pid or sec}：{short(ptext, 60)}"
        after = (f"目标位置（据编辑指令）：{short(instr, 60)}；"
                 f"移动后此处删除【← 源位置标记】")
    elif op == "merge":
        before = f"锚点A：{short(quote or ptext, 60)}；锚点B（见判断依据）：{short(evidence, 60)}"
        after = (f"【建议合并：保留一侧为主章，另一侧内容并入后删除；"
                 f"保留/删除侧见编辑指令：{short(instr, 60)}】")
    elif op == "split":
        sents = re.split(r"(?<=[。！？!?；;])", ptext)
        sents = [s for s in sents if s.strip()]
        mid = max(1, len(sents) // 2)
        head = "".join(sents[:mid]) or ptext
        tail = "".join(sents[mid:]) or ""
        before = f"{pid or sec} 当前为单段：{short(ptext, 60)}"
        after = (f"【建议拆分点（句界）】前半段：…{short(head, 40)} ｜ "
                 f"后半段：{short(tail, 40) or '(见原文后续句)'}…；拆分依据：{short(instr, 40)}")
    elif op == "reorder":
        before = f"原序列（见判断依据）：{short(evidence or quote, 70)}"
        after = f"建议序列（据编辑指令）：{short(instr, 90)}"
    else:  # 未覆盖 op 的兜底（不虚构结构）
        before = quote or short(ptext, 60)
        after = f"【建议示例占位（据编辑指令生成）：{short(instr, 90)}】"

    return {"id": f.get("id"), "op": op, "before": before, "after": after, "note": NOTE}


def inject_report(report_path, previews):
    """每个 finding 块的复核状态行后注入两行对照；先剥离旧注入行保证幂等。"""
    if not os.path.exists(report_path):
        return 0
    with open(report_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    pv = {p["id"]: p for p in previews}
    out, cur_id, injected = [], None, 0
    for ln in lines:
        if ln.startswith("- **改前**: ") or ln.startswith("- **改后（建议示例）**: "):
            continue  # 剥离旧注入（幂等）
        m = re.match(r"^### \[([A-Z0-9\-]+)\]", ln)
        if m:
            cur_id = m.group(1)
        out.append(ln)
        if ln.startswith("- **复核状态**") and cur_id in pv:
            p = pv[cur_id]
            out.append(f"- **改前**: {p['before']}")
            out.append(f"- **改后（建议示例）**: {p['after']}")
            injected += 1
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return injected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    findings = load_json(os.path.join(args.out, "findings.json"), [])
    if not findings:
        print("[apply_preview][WARN] findings.json 缺失或为空，跳过（previews=0）", file=sys.stderr)
        with open(os.path.join(args.work, "previews.json"), "w", encoding="utf-8") as fp:
            json.dump([], fp, ensure_ascii=False, indent=1)
        print("[apply_preview] previews=0 injected=0")
        return 0
    model = load_json(os.path.join(args.work, "structure.json"), {})
    pmap, order = para_index(model)

    ranked = sorted(findings,
                    key=lambda f: (SEV_ORDER.get(f.get("severity"), 3), f.get("id", "")))
    previews = [make_preview(f, model, pmap, order) for f in ranked[:MAX_PREVIEWS]]

    os.makedirs(args.work, exist_ok=True)
    with open(os.path.join(args.work, "previews.json"), "w", encoding="utf-8") as fp:
        json.dump(previews, fp, ensure_ascii=False, indent=1)

    injected = inject_report(os.path.join(args.out, "diagnosis_report.md"), previews)

    plan_path = os.path.join(args.out, "edit_plan.json")
    plan = load_json(plan_path, None)
    if plan is not None:
        pv = {p["id"]: p for p in previews}
        for o in plan.get("ops") or []:
            if o.get("op_id") in pv:
                o["preview"] = pv[o["op_id"]]
        with open(plan_path, "w", encoding="utf-8") as fp:
            json.dump(plan, fp, ensure_ascii=False, indent=1)

    print(f"[apply_preview] previews={len(previews)} injected={injected}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
