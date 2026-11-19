#!/usr/bin/env python3
"""relation_engine.py — 关系图谱引擎（v1.0.2）：类型化关系边的审计、补全建议与渲染。

用法:
  python3 relation_engine.py audit  [--work /app/work]  # 关系审计 + 候选关系建议
  python3 relation_engine.py render [--work /app/work] [--out /app/output]  # 关系图渲染
七类关系: causes/depends_on/contrasts/precedes/cites/supports/conflicts
审计规则:
  - 每条边必须有 evidence（或 note 标明"推断"），否则 warning
  - 方向语义: causes/precedes/depends_on 为有向边，from→to 必须与语义一致（由 Agent 保证，脚本
    检查同一对节点的双向冲突，如 A precedes B 且 B precedes A → critical）
  - 冲突检出: 不同节点对同一主体给出不同数字 → conflict 候选
  - 候选补全: 共享同一证据单元但无边的节点对 → 建议 supports/cites
渲染: relations.mmd（Mermaid flowchart）+ relations.svg（分层 DAG，纯标准库）+ relations.md（关系表）
"""
import argparse, html, json, os, re, sys

RELATIONS = {"causes", "depends_on", "contrasts", "precedes", "cites", "supports", "conflicts"}
DIRECTED = {"causes", "depends_on", "precedes", "cites", "supports"}
NUM_RE = re.compile(r"\d+(?:\.\d+)?%?")

def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d

def esc(s):
    return html.escape(str(s or ""), quote=True)

def subject_of(title):
    t = NUM_RE.sub("", title)
    t = re.sub(r"[\s:：，,。.（）()%~→\-]", "", t)
    return t[:12]

def audit_relations(mm):
    issues, candidates = [], []
    by_id = {n["id"]: n for n in mm["nodes"]}
    edges = mm.get("edges") or []
    seen_pairs = {}
    for e in edges:
        a, b, rel = e.get("from"), e.get("to"), e.get("relation")
        if a not in by_id or b not in by_id:
            issues.append({"severity": "critical", "type": "edge_endpoint",
                           "message": f"边端点不存在: {a}->{b}"})
            continue
        if rel not in RELATIONS:
            issues.append({"severity": "critical", "type": "edge_relation",
                           "message": f"关系 {rel} 不在七类词表内"})
        key = (a, b)
        rev = (b, a)
        if rev in seen_pairs and rel in DIRECTED and seen_pairs[rev] in DIRECTED:
            issues.append({"severity": "critical", "type": "edge_direction_conflict",
                           "message": f"双向有向边冲突: {a}<-{seen_pairs[rev]}-{b} 与 {a}-{rel}->{b}"})
        seen_pairs[key] = rel
        if not e.get("evidence") and "推断" not in (e.get("note") or ""):
            issues.append({"severity": "warning", "type": "edge_no_evidence",
                           "message": f"边 {a} -[{rel}]-> {b} 无证据也未注明推断"})

    # 数字冲突候选：不同节点、同一主体词、不同数字
    num_claims = []
    for n in mm["nodes"]:
        subj = subject_of(n["title"])
        nums = NUM_RE.findall(n["title"])
        if subj and nums:
            num_claims.append((n["id"], subj, nums, n["title"]))
    for i in range(len(num_claims)):
        for j in range(i + 1, len(num_claims)):
            a, b = num_claims[i], num_claims[j]
            if a[1] and b[1] and (a[1] in b[1] or b[1] in a[1]) and set(a[2]) != set(b[2]):
                candidates.append({"type": "conflict_candidate", "nodes": [a[0], b[0]],
                                   "message": f"数字表述不同: 「{a[3][:30]}」 vs 「{b[3][:30]}」，"
                                              f"请核实并用 conflicts/contrasts 边连接或修正"})

    # 共享证据但无边的节点对
    unit2nodes = {}
    for n in mm["nodes"]:
        for ev in n.get("evidence", []):
            u = ev.get("unit")
            if u:
                unit2nodes.setdefault(u, set()).add(n["id"])
    edge_pairs = {(e["from"], e["to"]) for e in edges} | {(e["to"], e["from"]) for e in edges}
    for u, nset in unit2nodes.items():
        nlist = sorted(nset)
        for i in range(len(nlist)):
            for j in range(i + 1, len(nlist)):
                if (nlist[i], nlist[j]) not in edge_pairs and len(candidates) < 30:
                    candidates.append({"type": "missing_relation_candidate", "unit": u,
                                       "nodes": [nlist[i], nlist[j]],
                                       "message": f"共享证据 {u} 但无关系边，考虑 supports/cites"})
    return issues, candidates

def topo_layers(mm):
    by_id = {n["id"]: n for n in mm["nodes"]}
    edges = [e for e in (mm.get("edges") or []) if e["from"] in by_id and e["to"] in by_id]
    indeg = {nid: 0 for nid in by_id}
    adj = {}
    for e in edges:
        adj.setdefault(e["from"], []).append(e["to"])
        indeg[e["to"]] += 1
    layer = {nid: 0 for nid in by_id}
    queue = [n for n, d in indeg.items() if d == 0]
    seen = set(queue)
    while queue:
        cur = queue.pop(0)
        for nxt in adj.get(cur, []):
            layer[nxt] = max(layer[nxt], layer[cur] + 1)
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return layer

def render(mm, out):
    by_id = {n["id"]: n for n in mm["nodes"]}
    edges = mm.get("edges") or []
    # Mermaid flowchart
    arrow = {"causes": "-->|导致|", "depends_on": "-->|依赖|", "contrasts": "-.-|对比|",
             "precedes": "-->|先于|", "cites": "-->|引用|", "supports": "-->|支持|",
             "conflicts": "-.->|冲突|"}
    lines = ["flowchart LR"]
    for e in edges:
        a = re.sub(r"\W", "_", e["from"])
        b = re.sub(r"\W", "_", e["to"])
        lines.append(f'  {a}["{esc(by_id[e["from"]]["title"][:30])}"] {arrow.get(e["relation"], "-->")} '
                     f'{b}["{esc(by_id[e["to"]]["title"][:30])}"]')
    with open(os.path.join(out, "relations.mmd"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    # 关系表 md
    rows = ["# 关系表", "", "| 起点 | 关系 | 终点 | 证据 | 备注 |", "|-|-|-|-|-|"]
    for e in edges:
        evs = " ".join(x.get("unit", "") for x in e.get("evidence", []))
        rows.append(f"| {by_id[e['from']]['title'][:24]} | {e['relation']} | "
                    f"{by_id[e['to']]['title'][:24]} | {evs} | {e.get('note','')[:30]} |")
    with open(os.path.join(out, "relations.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(rows) + "\n")
    # SVG 分层 DAG
    layer = topo_layers(mm)
    maxl = max(layer.values()) if layer else 0
    cols = {}
    for nid, l in layer.items():
        cols.setdefault(l, []).append(nid)
    W = (maxl + 1) * 300 + 60
    H = max(len(v) for v in cols.values()) * 60 + 60
    pos = {}
    for l, nids in cols.items():
        for i, nid in enumerate(sorted(nids)):
            pos[nid] = (40 + l * 300, 40 + i * 60)
    rel_color = {"causes": "#c53030", "depends_on": "#b7791f", "contrasts": "#6b46c1",
                 "precedes": "#2b6cb0", "cites": "#2c7a7b", "supports": "#2f855a",
                 "conflicts": "#e53e3e"}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
             'font-family="Noto Sans CJK SC,WenQuanYi Micro Hei,Microsoft YaHei,sans-serif">',
             f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
             '<defs><marker id="arw" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">'
             '<path d="M0,0 L7,3 L0,6 z" fill="#4a5568"/></marker></defs>']
    for e in edges:
        x1, y1 = pos[e["from"]]
        x2, y2 = pos[e["to"]]
        c = rel_color.get(e["relation"], "#4a5568")
        parts.append(f'<path d="M {x1+230} {y1+14} C {x1+270} {y1+14}, {x2-40} {y2+14}, {x2-6} {y2+14}" '
                     f'stroke="{c}" fill="none" stroke-width="1.4" marker-end="url(#arw)"/>')
        mx, my = (x1 + 230 + x2) / 2, (y1 + y2) / 2 + 8
        parts.append(f'<text x="{mx:.0f}" y="{my:.0f}" font-size="10" fill="{c}">{e["relation"]}</text>')
    for nid, (x, y) in pos.items():
        t = by_id[nid]["title"]
        label = t[:16] + ("…" if len(t) > 16 else "")
        parts.append(f'<rect x="{x}" y="{y}" rx="6" width="230" height="28" fill="#ebf4ff" stroke="#2b6cb0"/>')
        parts.append(f'<text x="{x+8}" y="{y+18}" font-size="12" fill="#1a365d">'
                     f'<title>{esc(t)}</title>{esc(label)}</text>')
    parts.append("</svg>")
    with open(os.path.join(out, "relations.svg"), "w", encoding="utf-8") as f:
        f.write("\n".join(parts))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["audit", "render"])
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()
    mm = load(os.path.join(args.work, "mindmap.normalized.json")) \
        or load(os.path.join(args.work, "mindmap.json"))
    if mm is None:
        sys.exit("[relation_engine] 找不到 mindmap(.normalized).json")
    if args.cmd == "audit":
        issues, candidates = audit_relations(mm)
        with open(os.path.join(args.work, "relation_audit.json"), "w", encoding="utf-8") as f:
            json.dump({"issues": issues, "candidates": candidates,
                       "stats": {"n_edges": len(mm.get("edges") or []),
                                 "n_critical": sum(1 for i in issues if i["severity"] == "critical"),
                                 "n_warning": sum(1 for i in issues if i["severity"] == "warning")}},
                      f, ensure_ascii=False, indent=1)
        print(f"[relation_engine] 边={len(mm.get('edges') or [])} "
              f"问题={len(issues)} 候选建议={len(candidates)} -> relation_audit.json")
    else:
        os.makedirs(args.out, exist_ok=True)
        render(mm, args.out)
        print("[relation_engine] 已渲染 relations.mmd / relations.md / relations.svg")
    return 0

if __name__ == "__main__":
    sys.exit(main())
