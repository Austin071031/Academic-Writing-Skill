#!/usr/bin/env python3
"""refine.py — 迭代精炼引擎（v1.0.4）：覆盖矩阵 + 五维 rubric 机检 + 修复清单。

用法: python3 refine.py [--work /app/work]
读取 work/mindmap.json（或 mindmap.normalized.json）与 work/materials.json，输出:
  work/refine_report.json — 五维评分（0-100）+ 指标明细
  work/fix_list.md        — 按严重度排序的可执行修复清单（Agent 按单修订后重跑 map_audit.py）
五维（对齐题面）:
  抓得准: fact 证据 quote 原文命中率；数字可溯源率
  理得清: 层级/扇出平衡；重复标题；分类混杂度（同父节点 kind 种类）
  连得对: 边证据率；边词表合法率；孤立事实节点（有证据但无边且无子节点）
  可追溯: 证据节点率；材料覆盖率；重要单元覆盖（含数字/标题/长段落）
  实际有用: 用途/受众填写；kind 多样性；待确认项显式标注
"""
import argparse, json, os, re, sys

NUM_RE = re.compile(r"\d+(?:\.\d+)?%?")
STOP = set("的了和与及或在是有为以对从向被把让其这那我们你他它们之也都而就但并且或者")

def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d

def norm(t):
    return re.sub(r"\s+", "", t or "")

def bigrams(t):
    t = re.sub(r"[^\w一-鿿]", "", (t or "").lower())
    return {t[i:i + 2] for i in range(len(t) - 1)} if len(t) > 1 else {t} if t else set()

def overlap(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def importance(u):
    s = 0
    if u["kind"] == "heading":
        s += 2
    if NUM_RE.search(u["text"]):
        s += 2
    if len(u["text"]) > 200:
        s += 1
    if re.search(r"(结论|表明|发现|证明|显著|关键|因此)", u["text"]):
        s += 1
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()
    mm = load(os.path.join(args.work, "mindmap.normalized.json")) \
        or load(os.path.join(args.work, "mindmap.json"))
    materials = load(os.path.join(args.work, "materials.json"), {"materials": []})
    if mm is None:
        sys.exit("[refine] 找不到 mindmap.json，请先按 SKILL.md 构建导图")
    unit_idx = {u["uid"]: u for m in materials.get("materials", []) for u in m.get("units", [])}
    nodes = mm["nodes"]
    by_id = {n["id"]: n for n in nodes}
    fixes = []

    # ---- 覆盖矩阵 ----
    node_bg = {n["id"]: bigrams(n["title"] + " " + (n.get("note") or "")) for n in nodes}
    ev_units = {e.get("unit") for n in nodes for e in n.get("evidence", []) if e.get("unit")}
    uncovered = []
    for uid, u in unit_idx.items():
        if u["kind"] == "heading":
            continue
        if uid in ev_units:
            continue
        ubg = bigrams(u["text"])
        best = max((overlap(ubg, bg) for bg in node_bg.values()), default=0)
        if best < 0.08:
            imp = importance(u)
            if imp >= 2:
                uncovered.append({"unit": uid, "importance": imp, "sim": round(best, 3),
                                  "head": u["text"][:60]})
    uncovered.sort(key=lambda x: -x["importance"])
    for c in uncovered[:15]:
        fixes.append({"severity": "high", "target": c["unit"],
                      "action": f"重要单元 {c['unit']} 未被任何节点覆盖（{c['head']}…），"
                                f"请新增节点或挂到现有节点 evidence"})

    # ---- 抓得准 ----
    fact_ok = fact_all = num_ok = num_all = 0
    for n in nodes:
        ev_texts = " ".join(unit_idx[e["unit"]]["text"] for e in n.get("evidence", [])
                            if e.get("unit") in unit_idx)
        for e in n.get("evidence", []):
            if e.get("type") == "fact" and e.get("quote"):
                fact_all += 1
                u = unit_idx.get(e.get("unit"))
                if u and norm(e["quote"]) in norm(u["text"]):
                    fact_ok += 1
                else:
                    fixes.append({"severity": "critical", "target": n["id"],
                                  "action": f"fact quote 不是原文: {str(e.get('quote'))[:40]}…"})
        if ev_texts:
            for m in NUM_RE.finditer(n["title"] + " " + (n.get("note") or "")):
                if len(m.group(0)) < 2 and not m.group(0).endswith("%"):
                    continue
                num_all += 1
                if norm(m.group(0)) in norm(ev_texts) or norm(m.group(0).rstrip("%")) in norm(ev_texts):
                    num_ok += 1
    s_accuracy = 100 * (0.6 * (fact_ok / fact_all if fact_all else 1)
                        + 0.4 * (num_ok / num_all if num_all else 1))

    # ---- 理得清 ----
    children = {}
    for n in nodes:
        children.setdefault(n.get("parent"), []).append(n["id"])
    depth = {mm["root"]: 0}
    stack = [mm["root"]]
    while stack:
        cur = stack.pop()
        for c in children.get(cur, []):
            depth[c] = depth[cur] + 1
            stack.append(c)
    fanouts = [len(v) for k, v in children.items() if k]
    over_fan = sum(1 for f in fanouts if f > 9)
    titles = [norm(n["title"]).lower() for n in nodes]
    dup = len(titles) - len(set(titles))
    mixed = 0
    for pid, kids in children.items():
        if pid and len(kids) >= 3:
            kinds = {by_id[k].get("kind") for k in kids} - {"group", None}
            if len(kinds) >= 3:
                mixed += 1
    if over_fan:
        fixes.append({"severity": "medium", "target": None,
                      "action": f"{over_fan} 个节点扇出 > 9，建议插入分组节点"})
    if dup:
        fixes.append({"severity": "medium", "target": None, "action": f"{dup} 个重复标题，合并或改写"})
    if mixed:
        fixes.append({"severity": "low", "target": None,
                      "action": f"{mixed} 处同级节点 kind 混杂（问题/方法/结论混排），建议统一分类维度"})
    maxd = max(depth.values()) if depth else 0
    s_structure = max(0, 100 - 8 * max(0, maxd - 5) - 6 * over_fan - 5 * dup - 3 * mixed)

    # ---- 连得对 ----
    edges = mm.get("edges") or []
    ev_edges = sum(1 for e in edges if e.get("evidence") or "推断" in (e.get("note") or ""))
    legal = {"causes", "depends_on", "contrasts", "precedes", "cites", "supports", "conflicts"}
    legal_edges = sum(1 for e in edges if e.get("relation") in legal)
    leaf_with_fact = [n["id"] for n in nodes
                      if not children.get(n["id"]) and n.get("evidence")
                      and n["id"] != mm["root"]
                      and not any(n["id"] in (e.get("from"), e.get("to")) for e in edges)]
    s_relation = 100 * (0.5 * (ev_edges / len(edges) if edges else 0.5)
                        + 0.3 * (legal_edges / len(edges) if edges else 1)
                        + 0.2 * (1 - min(len(leaf_with_fact) / max(len(nodes), 1), 1)))
    if len(edges) < max(1, len(nodes) // 8):
        fixes.append({"severity": "medium", "target": None,
                      "action": f"全图仅 {len(edges)} 条关系边；为因果/对比/依赖/支持关系补边并挂证据"})

    # ---- 可追溯 ----
    n_ev = sum(1 for n in nodes if n.get("evidence"))
    cov = len(ev_units) / len(unit_idx) if unit_idx else 0
    s_trace = 100 * (0.5 * (n_ev / len(nodes) if nodes else 0) + 0.5 * min(cov / 0.6, 1))
    if n_ev / max(len(nodes), 1) < 0.5:
        fixes.append({"severity": "high", "target": None,
                      "action": f"仅 {n_ev}/{len(nodes)} 节点挂证据，事实性节点必须挂 evidence"})

    # ---- 实际有用 ----
    kinds = {n.get("kind") for n in nodes} - {"root", "group", None}
    has_meta = bool(mm.get("purpose")) + bool(mm.get("audience"))
    n_unc = sum(1 for n in nodes if n.get("status") in ("uncertain", "missing"))
    s_useful = min(100, 30 * has_meta + 8 * len(kinds) + (10 if n_unc else 0) + 20)

    scores = {"抓得准": round(s_accuracy, 1), "理得清": round(s_structure, 1),
              "连得对": round(s_relation, 1), "可追溯": round(s_trace, 1),
              "实际有用": round(s_useful, 1)}
    overall = round(sum(scores.values()) / 5, 1)

    report = {"scores": scores, "overall": overall,
              "metrics": {"n_nodes": len(nodes), "n_edges": len(edges), "max_depth": maxd,
                          "fact_quote_hit": f"{fact_ok}/{fact_all}",
                          "number_traced": f"{num_ok}/{num_all}",
                          "edge_evidence_rate": round(ev_edges / len(edges), 3) if edges else None,
                          "node_evidence_rate": round(n_ev / len(nodes), 3) if nodes else None,
                          "material_coverage": round(cov, 3),
                          "uncovered_important": len(uncovered)},
              "n_fixes": len(fixes)}
    with open(os.path.join(args.work, "refine_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    fixes.sort(key=lambda x: order.get(x["severity"], 9))
    lines = [f"# 修复清单（综合分 {overall}/100）", "",
             "五维得分: " + " ｜ ".join(f"{k} {v}" for k, v in scores.items()), "",
             "按严重度排序；逐条修复后重跑 map_audit.py 与本脚本复评。", ""]
    for i, fx in enumerate(fixes, 1):
        lines.append(f"{i}. **[{fx['severity']}]** {fx['action']}")
    if not fixes:
        lines.append("无需修复项。")
    with open(os.path.join(args.work, "fix_list.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[refine] 综合分={overall} 修复项={len(fixes)} -> refine_report.json / fix_list.md")
    return 0

if __name__ == "__main__":
    sys.exit(main())
