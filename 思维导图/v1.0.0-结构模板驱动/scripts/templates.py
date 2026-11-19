#!/usr/bin/env python3
"""templates.py — 材料类型识别 + 思维导图骨架模板生成（v1.0.0 结构模板驱动）。

用法: python3 templates.py [--work /app/work]
读取 work/inspection.json 与 work/materials.json，判定材料类型
（paper/review/experiment/project/meeting/generic），生成:
  work/skeleton.json      — 带模板槽位的 mindmap.json 骨架（status=missing 的节点为待填槽位）
  work/slot_checklist.md  — 逐槽位填写清单（每个槽位应回答什么问题、证据怎么挂）
Agent 的职责：把骨架槽位替换/扩展为真实内容，为每个事实节点挂 evidence 单元号。
"""
import argparse, json, os, re, sys

TEMPLATES = {
    "paper": {
        "label": "论文（IMRaD 结构）",
        "branches": [
            ("question", "研究问题与目标", "材料要回答的核心科学问题是什么？假设是什么？"),
            ("background", "背景与研究缺口", "已有工作做到哪一步？缺口/动机是什么？"),
            ("method", "方法", "实验/计算方法、材料、参数、数据来源；每个方法节点挂对应章节证据。"),
            ("evidence", "结果与证据", "关键定量结果（数字必须出现在证据单元中）、图表结论。"),
            ("conclusion", "结论", "作者声称的结论，区分事实与推断。"),
            ("limitation", "局限与展望", "作者自述局限、未来工作；材料未提则标 missing。"),
        ],
    },
    "review": {
        "label": "综述",
        "branches": [
            ("scope", "主题范围与纳入标准", "综述覆盖的主题边界、时间范围、文献筛选标准。"),
            ("taxonomy", "分类框架", "作者采用的分类维度；各流派作为子节点。"),
            ("schools", "主要流派/方法族", "每个流派的核心主张与代表证据。"),
            ("consensus", "共识", "各流派一致认可的结论。"),
            ("debate", "分歧与争议", "相互矛盾的结论，用 contrasts/conflicts 边连接。"),
            ("gap", "研究空白", "作者指出的开放问题。"),
        ],
    },
    "experiment": {
        "label": "实验与研究方案",
        "branches": [
            ("goal", "实验目标与假设", "要验证什么假设？判定成功的标准是什么？"),
            ("variable", "变量设计", "自变量/因变量/控制变量分列。"),
            ("step", "步骤与流程", "按时间顺序的步骤，用 precedes 边连接。"),
            ("control", "对照与基线", "对照组设置与基线数据。"),
            ("criteria", "判定标准", "每项指标的阈值/显著性标准，数字须可溯源。"),
            ("risk", "风险与备选", "失败模式、误差来源、备选方案。"),
        ],
    },
    "project": {
        "label": "项目与任务计划",
        "branches": [
            ("goal", "总体目标", "项目要交付的最终结果。"),
            ("milestone", "里程碑", "带时间节点的里程碑，用 precedes 边表达先后。"),
            ("task", "任务分解", "每个任务标注负责人与交付物。"),
            ("dependency", "依赖关系", "任务间依赖，用 depends_on 边。"),
            ("deliverable", "交付物", "每项交付物的验收标准。"),
            ("risk", "风险", "风险、概率与缓解措施。"),
        ],
    },
    "meeting": {
        "label": "会议纪要与决策",
        "branches": [
            ("topic", "议题", "讨论了哪些议题？"),
            ("decision", "结论与决议", "达成的决议，挂原文证据。"),
            ("debate", "分歧", "未达成一致的点，用 conflicts 边连接对立观点。"),
            ("action", "待办事项", "每项待办标注负责人与截止时间；材料未给则标 uncertain。"),
            ("risk", "风险与遗留问题", "会上提出的风险。"),
        ],
    },
    "generic": {
        "label": "通用科研材料",
        "branches": [
            ("topic", "核心概念", "材料中的核心概念与定义。"),
            ("question", "问题与目标", "材料要解决的问题。"),
            ("method", "方法与过程", "采用的方法、步骤。"),
            ("evidence", "证据与数据", "关键数据与事实，逐条挂证据。"),
            ("conclusion", "结论与任务", "结论、后续任务。"),
            ("risk", "风险与不确定", "材料中的不确定点与风险。"),
        ],
    },
}

TYPE_RULES = [
    ("review", re.compile(r"(综述|review|survey|研究进展|文献计量)", re.I)),
    ("experiment", re.compile(r"(实验方案|实验设计|protocol|变量|对照组|假设验证)", re.I)),
    ("project", re.compile(r"(项目计划|里程碑|任务分解|负责人|交付物|甘特|milestone)", re.I)),
    ("meeting", re.compile(r"(会议纪要|组会|议题|决议|待办|minutes|meeting)", re.I)),
    ("paper", re.compile(r"(摘要|abstract|introduction|引言|结论|conclusion|参考文献|references|论文|paper)", re.I)),
]

def classify(insp, materials):
    text = (insp.get("task_head") or "") + "\n"
    for mat in materials.get("materials", []):
        for u in mat.get("units", [])[:40]:
            text += u.get("text", "") + "\n"
    hint = insp.get("purpose_hint") or ""
    hint_map = {"论文与综述结构": None, "实验与研究方案": "experiment",
                "项目与任务计划": "project", "会议纪要": "meeting",
                "知识体系与概念关系": "generic"}
    scores = {t: len(rx.findall(text)) for t, rx in TYPE_RULES}
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    return hint_map.get(hint) or "generic"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    def load(p, d=None):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return d

    insp = load(os.path.join(args.work, "inspection.json"), {}) or {}
    materials = load(os.path.join(args.work, "materials.json"), {"materials": []})
    mtype = classify(insp, materials)
    tpl = TEMPLATES[mtype]

    title = None
    for mat in materials.get("materials", []):
        for u in mat.get("units", []):
            if u["kind"] == "heading" and u.get("level", 9) == 1:
                title = u["text"][:60]
                break
        if title:
            break
    title = title or (insp.get("case_id") or "科研材料思维导图")

    nodes = [{"id": "root", "title": title, "parent": None, "kind": "root",
              "note": f"材料类型判定: {tpl['label']}", "evidence": [], "status": "confirmed"}]
    checklist = [f"# 槽位填写清单（材料类型: {tpl['label']}）", "",
                 "规则: 每个槽位节点必须替换为材料中的真实内容；事实节点必须挂 evidence",
                 "（unit 取自 materials_digest.md / materials.json 的单元号，type=fact 时 quote 必须是原文子串）。",
                 "材料中不存在的内容保留节点并标 status=\"missing\"，不得编造。", ""]
    for i, (kind, name, guide) in enumerate(tpl["branches"], 1):
        nid = f"slot{i:02d}"
        nodes.append({"id": nid, "title": name, "parent": "root", "kind": kind,
                      "note": f"[模板槽位] {guide}", "evidence": [], "status": "missing"})
        checklist.append(f"## {nid} {name}")
        checklist.append(f"- 要回答: {guide}")
        checklist.append(f"- 填写后把 status 改为 confirmed，并为关键子节点挂 evidence。")
        checklist.append("")
    skeleton = {"title": title, "purpose": insp.get("purpose_hint") or "科研材料结构化梳理",
                "audience": insp.get("audience_hint") or "未指定", "root": "root",
                "material_type": mtype, "nodes": nodes, "edges": []}

    with open(os.path.join(args.work, "skeleton.json"), "w", encoding="utf-8") as f:
        json.dump(skeleton, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.work, "slot_checklist.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(checklist))
    print(f"[templates] 材料类型={mtype}({tpl['label']}) 槽位={len(tpl['branches'])} -> "
          f"skeleton.json / slot_checklist.md")
    return 0

if __name__ == "__main__":
    sys.exit(main())
