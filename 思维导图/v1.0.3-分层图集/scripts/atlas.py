#!/usr/bin/env python3
"""atlas.py — 分层图集引擎（v1.0.3）：总览图 + 分主题详图，防止节点爆炸。

用法: python3 atlas.py [--work /app/work] [--out /app/output]
                       [--overview-budget 20] [--topic-budget 40]
读取 work/mindmap.normalized.json（须先跑 map_audit.py）:
  - 节点总数 ≤ topic_budget: 直接整体渲染（单图即图集）
  - 否则: 总览图 = 根 + 一级分支（附各分支规模计数）；每个一级分支子树 → 独立详图
产物（--out 下）:
  overview.{md,mm,opml,mmd,svg,html,png?}  topic_XX.{...}  atlas_index.md  atlas.html（导航）
跨图编号: 节点 id 全图集唯一且保持稳定；索引记录每个节点所在图。
"""
import argparse, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def load(p, d=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d

def subtree(nid, children):
    out = []
    stack = [nid]
    while stack:
        cur = stack.pop()
        out.append(cur)
        stack.extend(children.get(cur, []))
    return out

def make_submap(mm, root_id, keep, title, purpose_note):
    by_id = {n["id"]: n for n in mm["nodes"]}
    nodes = []
    for nid in keep:
        n = dict(by_id[nid])
        if nid == root_id:
            n["parent"] = None
        nodes.append(n)
    edges = [e for e in (mm.get("edges") or []) if e.get("from") in keep and e.get("to") in keep]
    return {"title": title, "purpose": mm.get("purpose"), "audience": mm.get("audience"),
            "root": root_id, "atlas_note": purpose_note, "nodes": nodes, "edges": edges}

def render_sub(work, out, submap_path, prefix):
    r = subprocess.run([sys.executable, os.path.join(HERE, "map_render.py"),
                        "--work", work, "--map", submap_path, "--out", out,
                        "--prefix", prefix],
                       capture_output=True, text=True, timeout=300)
    tail = (r.stdout or "").strip().splitlines()
    for line in tail[-2:]:
        print(f"  [render:{prefix}] {line}")
    return r.returncode

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--overview-budget", type=int, default=20)
    ap.add_argument("--topic-budget", type=int, default=40)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    atlas_dir = os.path.join(args.work, "atlas")
    os.makedirs(atlas_dir, exist_ok=True)

    mm = load(os.path.join(args.work, "mindmap.normalized.json"))
    if mm is None:
        sys.exit("[atlas] 找不到 work/mindmap.normalized.json，请先运行 map_audit.py")
    by_id = {n["id"]: n for n in mm["nodes"]}
    children = {}
    for n in mm["nodes"]:
        children.setdefault(n.get("parent"), []).append(n["id"])
    root = mm["root"]
    total = len(mm["nodes"])

    index = {"total_nodes": total, "maps": []}
    if total <= args.topic_budget:
        sp = os.path.join(atlas_dir, "overview.json")
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(mm, f, ensure_ascii=False, indent=1)
        render_sub(args.work, args.out, sp, "overview")
        index["maps"].append({"map": "overview", "nodes": total,
                              "scope": "全图（规模在预算内，单图交付）",
                              "node_ids": [n["id"] for n in mm["nodes"]]})
        mode = "single"
    else:
        branches = children.get(root, [])
        # 总览图：根 + 一级分支 + 规模注释
        ov_keep = [root] + branches
        ov = make_submap(mm, root, ov_keep, mm.get("title", "思维导图") + "（总览）",
                         "总览图：仅含一级分支；各分支详图见 topic_XX")
        ov_nodes = []
        for nid in ov_keep:
            n = dict(by_id[nid])
            if nid != root:
                size = len(subtree(nid, children))
                n["note"] = (n.get("note", "") + f" [分支规模 {size} 节点 → 详见对应 topic 图]").strip()
            if nid == root:
                n["parent"] = None
            ov_nodes.append(n)
        ov["nodes"] = ov_nodes
        sp = os.path.join(atlas_dir, "overview.json")
        with open(sp, "w", encoding="utf-8") as f:
            json.dump(ov, f, ensure_ascii=False, indent=1)
        render_sub(args.work, args.out, sp, "overview")
        index["maps"].append({"map": "overview", "nodes": len(ov_nodes),
                              "scope": "总览（根+一级分支）", "node_ids": ov_keep})
        # 详图
        for i, b in enumerate(branches, 1):
            keep = subtree(b, children)
            if len(keep) > args.topic_budget:
                # 超预算分支再截断到二级
                keep = [b] + children.get(b, [])
                for c in children.get(b, []):
                    keep.extend(children.get(c, []))
                keep = keep[:args.topic_budget]
            title = by_id[b]["title"][:40]
            sub = make_submap(mm, b, set(keep), f"{title}（详图 {i:02d}）",
                              f"分支详图：{title}")
            prefix = f"topic_{i:02d}"
            sp = os.path.join(atlas_dir, f"{prefix}.json")
            with open(sp, "w", encoding="utf-8") as f:
                json.dump(sub, f, ensure_ascii=False, indent=1)
            render_sub(args.work, args.out, sp, prefix)
            index["maps"].append({"map": prefix, "branch": title, "nodes": len(keep),
                                  "scope": f"一级分支 {b} 的子树", "node_ids": keep})
        mode = "atlas"

    # 索引
    lines = [f"# 图集索引（共 {total} 节点，{len(index['maps'])} 张图）", ""]
    for m in index["maps"]:
        lines.append(f"- **{m['map']}**: {m['scope']}，{m['nodes']} 节点"
                     + (f"（分支: {m.get('branch')}）" if m.get("branch") else ""))
    lines += ["", "每个节点 id 在全图集中唯一；evidence 单元号与 materials.json 一致，可跨图溯源。"]
    with open(os.path.join(args.out, "atlas_index.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    links = "".join(f'<li><a href="{m["map"]}.html">{m["map"]}</a> — {m["scope"]}，{m["nodes"]} 节点</li>'
                    for m in index["maps"])
    with open(os.path.join(args.out, "atlas.html"), "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>图集导航</title>
<style>body{{font-family:"Noto Sans CJK SC",sans-serif;max-width:760px;margin:2em auto;line-height:1.8}}</style>
</head><body><h1>思维导图图集（{total} 节点 / {len(index['maps'])} 图）</h1><ul>{links}</ul>
<p>每张图均有同名 .md/.mm/.opml/.mmd/.svg 可编辑源文件。</p></body></html>""")
    with open(os.path.join(args.work, "atlas_index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=1)
    print(f"[atlas] 模式={mode} 总节点={total} 图数={len(index['maps'])} -> "
          f"overview/topic_* + atlas_index.md + atlas.html")
    return 0

if __name__ == "__main__":
    sys.exit(main())
