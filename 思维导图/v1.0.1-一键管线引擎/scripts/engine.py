#!/usr/bin/env python3
"""engine.py — 一键管线引擎（v1.0.1）：自动修复 → 审计 → 渲染 → 汇总 → 闸门。

用法:
  python3 engine.py fix  [--work /app/work]   # 结构自动修复（扇出分组/深层提升）
  python3 engine.py run  [--work /app/work] [--out /app/output] [--case /input/case.json]
                          [--status success|partial] [--skill "mindmap-pipeline v1.0.1"]
自动修复规则（全部记入 change_log，可复核）:
  - 扇出 > 7: 按子节点 (kind, 证据材料号) 聚类，插入中间分组节点
  - 深度 > 6: 把超深子树上提一层
run = fix + map_audit + map_render + assemble_result + validate_output（调用同目录脚本）。
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d

def group_key(node):
    kinds = {"question": "问题", "method": "方法", "evidence": "证据", "conclusion": "结论",
             "task": "任务", "risk": "风险", "concept": "概念", "background": "背景",
             "limitation": "局限", "decision": "决议", "action": "待办", "milestone": "里程碑"}
    if node.get("kind") in kinds:
        return node["kind"], kinds[node["kind"]]
    mids = { (e.get("unit") or "").split("-")[0] for e in node.get("evidence", []) if e.get("unit") }
    mids.discard("")
    if len(mids) == 1:
        mid = mids.pop()
        return f"mat_{mid}", f"来自 {mid} 的内容"
    return "misc", "其他"

def fix(mm):
    changes = []
    by_id = {n["id"]: n for n in mm["nodes"]}
    children = {}
    for n in mm["nodes"]:
        children.setdefault(n.get("parent"), []).append(n["id"])

    # 1) 扇出分组（自底向上，一次处理一层即可收敛到 ≤7 组）
    new_nodes = []
    counter = [0]
    def new_group(parent, label):
        counter[0] += 1
        gid = f"grp{counter[0]:03d}"
        while gid in by_id:
            counter[0] += 1
            gid = f"grp{counter[0]:03d}"
        g = {"id": gid, "title": label, "parent": parent, "kind": "group",
             "note": "引擎自动分组节点（扇出控制）", "evidence": [], "status": "confirmed"}
        by_id[gid] = g
        new_nodes.append(g)
        return gid
    for pid in list(children):
        kids = children[pid]
        if pid is None or len(kids) <= 7:
            continue
        buckets = {}
        for k in kids:
            key, label = group_key(by_id[k])
            buckets.setdefault((key, label), []).append(k)
        if len(buckets) <= 1:
            # 单桶仍超扇出：按顺序切分为每组 ≤6
            buckets = {}
            for i in range(0, len(kids), 6):
                part = kids[i:i + 6]
                buckets[(f"part{i//6}", f"分组 {i//6 + 1}（自动）")] = part
        children[pid] = []
        for (key, label), members in buckets.items():
            if len(members) == len(kids) and len(buckets) == 1:
                children[pid] = members
                continue
            gid = new_group(pid, label)
            children[pid].append(gid)
            children[gid] = members
            for m in members:
                by_id[m]["parent"] = gid
        changes.append({"op": "auto_group", "location": pid,
                        "before": len(kids), "after": len(children[pid]),
                        "reason": "扇出 > 7，按 kind/材料来源自动分组"})
    mm["nodes"].extend(new_nodes)

    # 2) 深度提升
    depth = {mm["root"]: 0}
    stack = [mm["root"]]
    while stack:
        cur = stack.pop()
        for c in children.get(cur, []):
            depth[c] = depth[cur] + 1
            stack.append(c)
    lifted = 0
    for nid, d in list(depth.items()):
        if d > 6:
            p = by_id[nid]["parent"]
            gp = by_id.get(p, {}).get("parent")
            if gp:
                by_id[nid]["parent"] = gp
                children[p].remove(nid)
                children.setdefault(gp, []).append(nid)
                lifted += 1
    if lifted:
        changes.append({"op": "lift_deep", "location": None, "before": "depth>6",
                        "after": f"提升 {lifted} 个节点", "reason": "层级过深，自动上提一层"})
    return mm, changes

def run_script(name, extra):
    cmd = [sys.executable, os.path.join(HERE, name)] + extra
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    out = (r.stdout or "") + (r.stderr or "")
    for line in out.strip().splitlines()[-4:]:
        print(f"  [{name}] {line}")
    return r.returncode

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fix", "run"])
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--status", default="partial")
    ap.add_argument("--skill", default="mindmap-pipeline v1.0.1")
    args = ap.parse_args()

    mp = os.path.join(args.work, "mindmap.json")
    mm = load(mp)
    if mm is None:
        sys.exit(f"[engine] 无法解析 {mp}：请先按 SKILL.md 写好 mindmap.json")
    mm, changes = fix(mm)
    fp = os.path.join(args.work, "mindmap.json")
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(mm, f, ensure_ascii=False, indent=1)
    print(f"[engine] fix: 自动修复 {len(changes)} 处")
    if changes:
        cl = os.path.join(args.work, "change_log.json")
        old = load(cl, []) or []
        with open(cl, "w", encoding="utf-8") as f:
            json.dump(old + changes, f, ensure_ascii=False, indent=2)
    if args.cmd == "fix":
        return 0

    rc = run_script("map_audit.py", ["--work", args.work])
    rc |= run_script("map_render.py", ["--work", args.work, "--out", args.out])
    # 若审计存在 critical，强制如实降级
    audit = load(os.path.join(args.work, "audit.json"), {}) or {}
    status = args.status
    if (audit.get("stats") or {}).get("n_critical", 0) and status == "success":
        status = "partial"
        print("[engine] 审计存在 critical，状态降级为 partial（请按 audit.json 修复后重跑）")
    rc |= run_script("assemble_result.py", ["--work", args.work, "--out", args.out,
                                            "--case", args.case, "--skill", args.skill,
                                            "--status", status])
    vrc = run_script("validate_output.py", ["--out", args.out, "--work", args.work])
    print(f"[engine] 管线完成: audit/render/assemble rc={rc} validate rc={vrc}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
