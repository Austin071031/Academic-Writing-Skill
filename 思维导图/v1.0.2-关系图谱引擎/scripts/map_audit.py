#!/usr/bin/env python3
"""map_audit.py — 规范化并审计 work/mindmap.json，产出 audit.json 与 evidence_map.json。

用法: python3 map_audit.py [--work /app/work] [--map work/mindmap.json]
规范化（自动修复并记入 change_log）:
  - 节点去重 id（重名自动加后缀）、补缺失字段、parent 悬空节点挂回根、破除环
审计（写入 audit.json，severity ∈ critical/warning/info）:
  - 结构: 深度>6、扇出>9、孤立节点、重复标题、空标题
  - 溯源: evidence.unit 必须存在于 materials.json；type=fact 的 quote 必须是该单元原文子串；
          节点标题/备注中的数字必须能在其证据单元文本中找到（找不到→number_unverified）
  - 关系: edges 端点存在、relation 在七类词表内、edges 缺证据→warning
  - 覆盖: 材料单元被至少一个节点引用的比例（completeness 指标）
输出:
  work/mindmap.normalized.json / work/audit.json / work/evidence_map.json
  （change_log / uncertainty 追加写 work/change_log.json、work/uncertainty.json）
"""
import argparse, json, os, re, sys

RELATIONS = {"causes", "depends_on", "contrasts", "precedes", "cites", "supports", "conflicts"}
NUM_RE = re.compile(r"\d+(?:\.\d+)?%?")

def norm_text(t):
    return re.sub(r"\s+", "", t or "")

def load(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def append_json(path, items):
    old = load(path, []) or []
    with open(path, "w", encoding="utf-8") as f:
        json.dump(old + items, f, ensure_ascii=False, indent=2)

def build_unit_index(materials):
    idx = {}
    for mat in materials.get("materials", []):
        for u in mat.get("units", []):
            idx[u["uid"]] = u
    return idx

def normalize(mm):
    changes = []
    nodes = mm.get("nodes") or []
    seen = {}
    for n in nodes:
        n.setdefault("title", "")
        n["title"] = str(n["title"]).strip()
        n.setdefault("note", "")
        n.setdefault("kind", "topic")
        n.setdefault("evidence", [])
        n.setdefault("status", "confirmed")
        base = str(n.get("id") or "").strip() or "n?"
        nid, k = base, 2
        while nid in seen:
            nid = f"{base}_{k}"
            k += 1
        if nid != n.get("id"):
            changes.append({"op": "rename_node_id", "before": n.get("id"), "after": nid,
                            "reason": "节点 id 重复或缺失，自动改名"})
            n["id"] = nid
        seen[nid] = n
    mm["nodes"] = list(seen.values())

    # 根节点
    root_id = mm.get("root")
    if root_id not in seen:
        roots = [n for n in mm["nodes"] if not n.get("parent")]
        if len(roots) == 1:
            mm["root"] = roots[0]["id"]
            changes.append({"op": "fix_root", "after": mm["root"], "reason": "root 字段无效，取唯一无父节点"})
        else:
            # 造一个总根
            rid = "root"
            while rid in seen:
                rid += "_"
            mm["nodes"].insert(0, {"id": rid, "title": mm.get("title") or "主题",
                                   "parent": None, "kind": "root", "note": "",
                                   "evidence": [], "status": "confirmed"})
            seen[rid] = mm["nodes"][0]
            for n in mm["nodes"][1:]:
                if not n.get("parent") or n["parent"] not in seen:
                    n["parent"] = rid
            mm["root"] = rid
            changes.append({"op": "create_root", "after": rid,
                            "reason": "存在多个/零个根候选，自动创建总根并挂载"})

    # 悬空 parent 挂回根
    for n in mm["nodes"]:
        if n["id"] == mm["root"]:
            n["parent"] = None
            continue
        if not n.get("parent") or n["parent"] not in seen:
            changes.append({"op": "reattach", "node": n["id"], "before": n.get("parent"),
                            "after": mm["root"], "reason": "父节点不存在，挂回根"})
            n["parent"] = mm["root"]

    # 破环（沿 parent 上溯）
    for n in mm["nodes"]:
        chain, cur, hit = set(), n, False
        while cur and cur.get("parent"):
            p = cur["parent"]
            if p in chain:
                hit = True
                break
            chain.add(cur["id"])
            cur = seen.get(p)
        if hit:
            changes.append({"op": "break_cycle", "node": n["id"],
                            "after": mm["root"], "reason": "检测到父链环，挂回根"})
            n["parent"] = mm["root"]

    # 边端点与词表
    edges = []
    for e in mm.get("edges") or []:
        if e.get("from") not in seen or e.get("to") not in seen:
            changes.append({"op": "drop_edge", "edge": e, "reason": "边端点不存在，删除"})
            continue
        rel = e.get("relation")
        if rel not in RELATIONS:
            changes.append({"op": "fix_relation", "edge": {"from": e["from"], "to": e["to"]},
                            "before": rel, "after": "supports",
                            "reason": f"relation 不在词表 {sorted(RELATIONS)}，改为 supports 并标记"})
            e["relation"] = "supports"
            e.setdefault("note", "")
            e["note"] = (e["note"] + f" [原标注:{rel}]").strip()
        e.setdefault("evidence", [])
        edges.append(e)
    mm["edges"] = edges
    return mm, changes, seen

def audit(mm, unit_idx):
    issues = []
    stats = {}
    nodes = mm["nodes"]
    by_id = {n["id"]: n for n in nodes}
    root = mm["root"]

    depth = {root: 0}
    children = {}
    for n in nodes:
        children.setdefault(n.get("parent"), []).append(n["id"])
    stack = [root]
    while stack:
        cur = stack.pop()
        for c in children.get(cur, []):
            depth[c] = depth[cur] + 1
            stack.append(c)
    stats["n_nodes"] = len(nodes)
    stats["max_depth"] = max(depth.values()) if depth else 0
    stats["n_edges"] = len(mm.get("edges", []))
    if stats["max_depth"] > 6:
        issues.append({"severity": "warning", "type": "too_deep", "node": None,
                       "message": f"最大层级 {stats['max_depth']} > 6，建议合并深层分支"})
    for pid, kids in children.items():
        if pid is not None and len(kids) > 9:
            issues.append({"severity": "warning", "type": "fanout", "node": pid,
                           "message": f"节点 {pid} 子节点 {len(kids)} > 9，建议分组"})

    titles = {}
    for n in nodes:
        key = norm_text(n["title"]).lower()
        if not key:
            issues.append({"severity": "critical", "type": "empty_title", "node": n["id"],
                           "message": "节点标题为空"})
            continue
        if key in titles:
            issues.append({"severity": "warning", "type": "dup_title", "node": n["id"],
                           "message": f"与 {titles[key]} 标题重复: {n['title'][:30]}"})
        else:
            titles[key] = n["id"]

    # 溯源审计
    ev_map = []
    n_verbatim_ok = n_verbatim_bad = n_num_bad = 0
    used_units = set()
    for n in nodes:
        ev_texts = []
        for ev in n.get("evidence", []):
            uid = ev.get("unit")
            u = unit_idx.get(uid)
            if not u:
                issues.append({"severity": "critical", "type": "evidence_missing", "node": n["id"],
                               "message": f"证据单元 {uid} 不存在于材料索引"})
                continue
            used_units.add(uid)
            ev_texts.append(u["text"])
            q = ev.get("quote") or ""
            etype = ev.get("type", "summary")
            if etype == "fact" and q:
                if norm_text(q) in norm_text(u["text"]):
                    n_verbatim_ok += 1
                else:
                    n_verbatim_bad += 1
                    issues.append({"severity": "critical", "type": "quote_not_verbatim",
                                   "node": n["id"],
                                   "message": f"fact 证据 quote 不是 {uid} 原文子串: {q[:40]}…"})
            ev_map.append({"node_id": n["id"], "node_title": n["title"][:60],
                           "unit": uid, "material": u["uid"].split("-")[0],
                           "page": u.get("page"), "type": etype,
                           "quote": q[:120], "verification": "script_checked"})
        # 数字核验
        joined = norm_text(" ".join(ev_texts))
        if joined:
            for m in NUM_RE.finditer(n["title"] + " " + (n.get("note") or "")):
                tok = m.group(0)
                if len(tok) < 2 and not tok.endswith("%"):
                    continue
                cands = {tok, tok.rstrip("%")}
                if tok.endswith("%"):
                    cands.add(tok)
                if not any(norm_text(c) in joined for c in cands):
                    # 允许 0.81 ↔ 81% 换算
                    ok = False
                    try:
                        v = float(tok.rstrip("%"))
                        for alt in (v / 100, v * 100):
                            for fmt in (f"{alt:.4g}", f"{alt:.2f}", f"{alt:.1f}", str(int(alt)) if alt == int(alt) else None):
                                if fmt and norm_text(fmt) in joined:
                                    ok = True
                                    break
                            if ok:
                                break
                    except ValueError:
                        pass
                    if not ok:
                        n_num_bad += 1
                        issues.append({"severity": "warning", "type": "number_unverified",
                                       "node": n["id"],
                                       "message": f"数字 {tok} 未在该节点证据单元中出现（含百分比换算）"})
        else:
            if n["id"] != root and n.get("kind") not in ("root",):
                issues.append({"severity": "info", "type": "no_evidence", "node": n["id"],
                               "message": "节点无证据挂载（组织性节点可接受，事实性节点应挂载）"})

    # 边审计
    for e in mm.get("edges", []):
        if not e.get("evidence"):
            issues.append({"severity": "warning", "type": "edge_no_evidence",
                           "node": e.get("from"),
                           "message": f"边 {e['from']} -[{e['relation']}]-> {e['to']} 无证据"})

    total_units = len(unit_idx)
    stats["coverage"] = round(len(used_units) / total_units, 3) if total_units else 0
    stats["n_evidence"] = len(ev_map)
    stats["verbatim_ok"] = n_verbatim_ok
    stats["verbatim_bad"] = n_verbatim_bad
    stats["number_unverified"] = n_num_bad
    stats["n_critical"] = sum(1 for i in issues if i["severity"] == "critical")
    stats["n_warning"] = sum(1 for i in issues if i["severity"] == "warning")
    return issues, stats, ev_map, used_units

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--map", default=None)
    args = ap.parse_args()
    mp = args.map or os.path.join(args.work, "mindmap.json")
    mm = load(mp)
    if mm is None:
        sys.exit(f"[map_audit] 无法解析 {mp}")
    materials = load(os.path.join(args.work, "materials.json"), {"materials": []})
    unit_idx = build_unit_index(materials)

    mm, changes, _seen = normalize(mm)
    issues, stats, ev_map, _used = audit(mm, unit_idx)

    with open(os.path.join(args.work, "mindmap.normalized.json"), "w", encoding="utf-8") as f:
        json.dump(mm, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.work, "audit.json"), "w", encoding="utf-8") as f:
        json.dump({"issues": issues, "stats": stats}, f, ensure_ascii=False, indent=1)
    with open(os.path.join(args.work, "evidence_map.json"), "w", encoding="utf-8") as f:
        json.dump(ev_map, f, ensure_ascii=False, indent=1)
    if changes:
        append_json(os.path.join(args.work, "change_log.json"),
                    [{"op": c.get("op"), "location": c.get("node") or c.get("location"),
                      "before": c.get("before"), "after": c.get("after"),
                      "reason": c.get("reason")} for c in changes])
    print(f"[map_audit] 节点={stats['n_nodes']} 边={stats['n_edges']} 覆盖率={stats['coverage']} "
          f"critical={stats['n_critical']} warning={stats['n_warning']} 规范化修复={len(changes)}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
