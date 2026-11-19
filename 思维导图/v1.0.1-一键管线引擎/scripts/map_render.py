#!/usr/bin/env python3
"""map_render.py — 把规范化思维导图渲染为多种可编辑格式与真实预览图。

用法: python3 map_render.py [--work /app/work] [--map work/mindmap.normalized.json]
                            [--out /app/output] [--prefix mindmap] [--max-svg-nodes 400]
产物（--out 下，prefix 可替换以便一图多文件）:
  <prefix>.md    Markdown 大纲（节点附证据锚点）
  <prefix>.mm    FreeMind XML（XMind/Freeplane 可直接导入）
  <prefix>.opml  OPML 大纲
  <prefix>.mmd   Mermaid mindmap 源码
  <prefix>.svg   纯标准库布局渲染的树图（真实渲染预览）
  <prefix>.html  可折叠交互预览（自包含）
  <prefix>.png   若 matplotlib 可用且有 CJK 字体则输出，否则诚实记录
  preview_status.json 记录各格式成败与原因
"""
import argparse, html, json, os, re, sys

def esc(s):
    return html.escape(str(s or ""), quote=True)

def xml_escape(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))

def text_width(t, size):
    w = 0.0
    for ch in t:
        w += size * (1.0 if ord(ch) > 0x2E7F else 0.56)
    return w

def load(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def build_tree(mm):
    by_id = {n["id"]: n for n in mm["nodes"]}
    children = {nid: [] for nid in by_id}
    for n in mm["nodes"]:
        p = n.get("parent")
        if p in children:
            children[p].append(n["id"])
    return by_id, children

# ---------- Markdown 大纲 ----------
def render_md(mm, by_id, children, unit_idx):
    lines = [f"# {mm.get('title') or '思维导图'}", ""]
    if mm.get("purpose"):
        lines.append(f"> 用途: {mm['purpose']}  受众: {mm.get('audience') or '未指定'}")
        lines.append("")
    def walk(nid, lv):
        n = by_id[nid]
        evs = " ".join(f"[{e.get('unit')}]" for e in n.get("evidence", []) if e.get("unit"))
        flag = "" if n.get("status") == "confirmed" else f" ⚠{n.get('status')}"
        note = f" — {n['note']}" if n.get("note") else ""
        lines.append(f"{'  ' * lv}- **{n['title']}**{flag}{note} {evs}".rstrip())
        for c in children.get(nid, []):
            walk(c, lv + 1)
    walk(mm["root"], 0)
    if mm.get("edges"):
        lines += ["", "## 关系", ""]
        for e in mm["edges"]:
            evs = " ".join(f"[{x.get('unit')}]" for x in e.get("evidence", []) if x.get("unit"))
            lines.append(f"- {by_id[e['from']]['title']} —*{e['relation']}*→ {by_id[e['to']]['title']} {evs}".rstrip())
    lines += ["", "---", "图例: [Mxx-Sxx-Pxxx] 为材料单元溯源锚点；⚠uncertain/⚠missing 为待人工确认项。"]
    return "\n".join(lines) + "\n"

# ---------- FreeMind .mm ----------
def render_mm(mm, by_id, children):
    def walk(nid):
        n = by_id[nid]
        txt = xml_escape(n["title"] + (f" — {n['note']}" if n.get("note") else ""))
        evs = " ".join(e.get("unit", "") for e in n.get("evidence", []))
        attr = f' TEXT="{txt}"'
        if evs:
            attr += f' LINK="{xml_escape(evs)}"'
        kids = "".join(walk(c) for c in children.get(nid, []))
        if kids:
            return f"<node{attr}>{kids}</node>"
        return f"<node{attr}/>"
    return ('<map version="1.0.1">\n<!-- 由思维导图 Skill 生成；可用 FreeMind/Freeplane/XMind 打开编辑；'
            "LINK 属性保存证据单元锚点 -->\n" + walk(mm["root"]) + "\n</map>\n")

# ---------- OPML ----------
def render_opml(mm, by_id, children):
    def walk(nid, lv):
        n = by_id[nid]
        evs = " ".join(f"[{e.get('unit')}]" for e in n.get("evidence", []) if e.get("unit"))
        txt = xml_escape((n["title"] + (f" — {n['note']}" if n.get("note") else "") + " " + evs).strip())
        kids = "".join(walk(c, lv + 1) for c in children.get(nid, []))
        pad = "  " * (lv + 1)
        if kids:
            return f'{pad}<outline text="{txt}">\n{kids}{pad}</outline>\n'
        return f'{pad}<outline text="{txt}"/>\n'
    title = xml_escape(mm.get("title") or "思维导图")
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<opml version="2.0">\n<head><title>{title}</title></head>\n<body>\n'
            + walk(mm["root"], 0) + "</body>\n</opml>\n")

# ---------- Mermaid ----------
def render_mmd(mm, by_id, children):
    def mmid(nid):
        return re.sub(r"[^0-9A-Za-z_一-鿿]", "_", nid)
    def clean(t):
        return re.sub(r'[\[\]()\{\}"]', "", str(t))[:80]
    lines = ["mindmap"]
    def walk(nid, lv):
        n = by_id[nid]
        pad = "  " * (lv + 1)
        iid = mmid(nid)
        title = clean(n["title"])
        if lv == 0:
            lines.append(f"{pad}{iid}(({title}))")
        else:
            lines.append(f'{pad}{iid}["{title}"]')
        for c in children.get(nid, []):
            walk(c, lv + 1)
    walk(mm["root"], 0)
    return "\n".join(lines) + "\n"

# ---------- SVG 树图 ----------
PALETTE = ["#2b6cb0", "#2f855a", "#b7791f", "#9b2c2c", "#6b46c1", "#2c7a7b", "#c05621"]

def layout(mm, by_id, children, size=13):
    root = mm["root"]
    slot = {}
    counter = [0]
    def assign(nid):
        kids = children.get(nid, [])
        if not kids:
            slot[nid] = counter[0]
            counter[0] += 1
        else:
            for c in kids:
                assign(c)
            slot[nid] = (slot[kids[0]] + slot[kids[-1]]) / 2
    assign(root)
    depth = {root: 0}
    stack = [root]
    while stack:
        cur = stack.pop()
        for c in children.get(cur, []):
            depth[c] = depth[cur] + 1
            stack.append(c)
    maxd = max(depth.values()) if depth else 0
    colw = []
    for d in range(maxd + 1):
        w = max((text_width(by_id[n]["title"], size) for n in by_id if depth.get(n) == d), default=80)
        colw.append(min(max(w + 28, 90), 320))
    x_of = [0]
    for d in range(1, maxd + 1):
        x_of.append(x_of[-1] + colw[d - 1] + 60)
    rowh = 34
    pos = {}
    for nid in by_id:
        d = depth.get(nid, 0)
        pos[nid] = (x_of[d], slot[nid] * rowh + 20, colw[d])
    W = (x_of[-1] + colw[-1] + 40) if x_of else 600
    H = counter[0] * rowh + 40
    return pos, W, H, rowh, depth

def render_svg(mm, by_id, children, max_nodes=400):
    if len(by_id) > max_nodes:
        return None, f"节点数 {len(by_id)} 超过 SVG 上限 {max_nodes}，跳过总览渲染"
    pos, W, H, rowh, depth = layout(mm, by_id, children)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" '
             f'viewBox="0 0 {W:.0f} {H:.0f}" font-family="Noto Sans CJK SC,WenQuanYi Micro Hei,Microsoft YaHei,sans-serif">',
             f'<rect width="{W:.0f}" height="{H:.0f}" fill="#ffffff"/>']
    for n in mm["nodes"]:
        p = n.get("parent")
        if p and p in pos:
            x1, y1, w1 = pos[p]
            x2, y2, _w2 = pos[n["id"]]
            parts.append(f'<path d="M {x1+w1:.0f} {y1+rowh/2-4:.0f} C {x1+w1+30:.0f} {y1+rowh/2-4:.0f}, '
                         f'{x2-30:.0f} {y2+rowh/2-4:.0f}, {x2:.0f} {y2+rowh/2-4:.0f}" '
                         f'stroke="#a0aec0" fill="none" stroke-width="1.2"/>')
    for n in mm["nodes"]:
        x, y, w = pos[n["id"]]
        d = depth.get(n["id"], 0)
        color = PALETTE[min(d, len(PALETTE) - 1)]
        tw = text_width(n["title"], 13)
        bw = min(max(tw + 16, 60), w - 6)
        fill = color if d == 0 else "#ffffff"
        tcol = "#ffffff" if d == 0 else color
        dash = ' stroke-dasharray="4 3"' if n.get("status") != "confirmed" else ""
        parts.append(f'<rect x="{x:.0f}" y="{y:.0f}" rx="7" width="{bw:.0f}" height="{rowh-10}" '
                     f'fill="{fill}" stroke="{color}" stroke-width="1.4"{dash}/>')
        label = n["title"]
        maxch = int((bw - 12) / 7.2)
        if len(label) > maxch:
            label = label[:maxch - 1] + "…"
        nev = len(n.get("evidence", []))
        badge = f' <tspan fill="#718096" font-size="10">[{nev}]</tspan>' if nev else ""
        parts.append(f'<text x="{x+8:.0f}" y="{y+rowh/2:.0f}" font-size="13" fill="{tcol}">'
                     f'<title>{esc(n.get("note") or n["title"])}</title>{esc(label)}{badge}</text>')
    parts.append("</svg>")
    return "\n".join(parts), None

# ---------- 交互 HTML ----------
def render_html(mm, by_id, children):
    def walk(nid):
        n = by_id[nid]
        evs = " ".join(f'<code>[{esc(e.get("unit"))}]</code>' for e in n.get("evidence", []) if e.get("unit"))
        flag = "" if n.get("status") == "confirmed" else f' <span class="warn">⚠{esc(n.get("status"))}</span>'
        note = f' <span class="note">{esc(n.get("note"))}</span>' if n.get("note") else ""
        kids = "".join(walk(c) for c in children.get(nid, []))
        inner = f"<ul>{kids}</ul>" if kids else ""
        return f"<li><details open><summary><b>{esc(n['title'])}</b>{flag}{note} {evs}</summary>{inner}</details></li>"
    edges_html = ""
    if mm.get("edges"):
        rows = "".join(f"<tr><td>{esc(by_id[e['from']]['title'])}</td><td>{esc(e['relation'])}</td>"
                       f"<td>{esc(by_id[e['to']]['title'])}</td>"
                       f"<td>{' '.join(esc(x.get('unit','')) for x in e.get('evidence',[]))}</td></tr>"
                       for e in mm["edges"])
        edges_html = ("<h2>关系表</h2><table border=1 cellspacing=0 cellpadding=4>"
                      "<tr><th>起点</th><th>关系</th><th>终点</th><th>证据</th></tr>" + rows + "</table>")
    return f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><title>{esc(mm.get('title') or '思维导图')}</title>
<style>body{{font-family:"Noto Sans CJK SC","WenQuanYi Micro Hei",sans-serif;max-width:900px;margin:2em auto;line-height:1.8;color:#1a202c}}
code{{background:#edf2f7;padding:0 4px;border-radius:3px;font-size:.85em}}.warn{{color:#c53030}}.note{{color:#4a5568;font-size:.9em}}
details{{margin-left:1em}}summary{{cursor:pointer}}</style></head><body>
<h1>{esc(mm.get('title') or '思维导图')}</h1>
<p>用途: {esc(mm.get('purpose') or '未填写')} ｜ 受众: {esc(mm.get('audience') or '未填写')}</p>
<ul>{walk(mm['root'])}</ul>{edges_html}
<hr><p>图例: [Mxx-Sxx-Pxxx] 为材料单元溯源锚点；⚠ 为待人工确认。本文件可折叠浏览，结构化源稿见同名 .md/.mm/.opml/.mmd。</p>
</body></html>"""

# ---------- PNG (matplotlib, 尽力) ----------
def render_png(svg_unused, mm, by_id, children, out_png):
    try:
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib import font_manager, pyplot as plt
    except Exception as e:
        return None, f"matplotlib 不可用: {e}"
    cjk = None
    for name in ("Noto Sans CJK SC", "Noto Sans CJK JP", "WenQuanYi Micro Hei",
                 "SimHei", "Microsoft YaHei", "Droid Sans Fallback", "AR PL UMing CN"):
        try:
            font_manager.findfont(name, fallback_to_default=False)
            cjk = name
            break
        except Exception:
            continue
    if not cjk:
        return None, "未找到 CJK 字体，PNG 会乱码，改用 SVG/HTML 预览"
    pos, W, H, rowh, depth = layout(mm, by_id, children)
    fig, ax = plt.subplots(figsize=(W / 100, H / 100), dpi=100)
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")
    plt.rcParams["font.family"] = cjk
    for n in mm["nodes"]:
        p = n.get("parent")
        if p and p in pos:
            x1, y1, w1 = pos[p]
            x2, y2, _ = pos[n["id"]]
            ax.annotate("", xy=(x2, y2 + rowh / 2 - 4), xytext=(x1 + w1, y1 + rowh / 2 - 4),
                        arrowprops=dict(arrowstyle="-", color="#a0aec0", lw=1.0,
                                        connectionstyle="arc3,rad=0.15"))
    for n in mm["nodes"]:
        x, y, w = pos[n["id"]]
        d = depth.get(n["id"], 0)
        color = PALETTE[min(d, len(PALETTE) - 1)]
        tw = text_width(n["title"], 13)
        bw = min(max(tw + 16, 60), w - 6)
        ax.add_patch(plt.Rectangle((x, y), bw, rowh - 10, facecolor=color if d == 0 else "white",
                                   edgecolor=color, lw=1.2, zorder=2))
        ax.text(x + 8, y + rowh / 2 - 3, n["title"][:40], fontsize=9,
                color="white" if d == 0 else color, va="center", zorder=3)
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)
    return out_png, None

def write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--map", default=None)
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--prefix", default="mindmap")
    ap.add_argument("--max-svg-nodes", type=int, default=400)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    mp = args.map or os.path.join(args.work, "mindmap.normalized.json")
    mm = load(mp)
    if mm is None:
        sys.exit(f"[map_render] 无法解析 {mp}")
    by_id, children = build_tree(mm)
    materials = load(os.path.join(args.work, "materials.json"), {"materials": []})
    unit_idx = {u["uid"]: u for m in materials.get("materials", []) for u in m.get("units", [])}

    status = {"prefix": args.prefix, "formats": {}, "notes": []}
    p = lambda name: os.path.join(args.out, f"{args.prefix}.{name}")
    try:
        write(p("md"), render_md(mm, by_id, children, unit_idx))
        status["formats"]["md"] = True
        write(p("mm"), render_mm(mm, by_id, children))
        status["formats"]["mm"] = True
        write(p("opml"), render_opml(mm, by_id, children))
        status["formats"]["opml"] = True
        write(p("mmd"), render_mmd(mm, by_id, children))
        status["formats"]["mmd"] = True
        write(p("html"), render_html(mm, by_id, children))
        status["formats"]["html"] = True
    except Exception as e:
        print(f"[map_render] 文本格式渲染失败: {e}", file=sys.stderr)
        status["notes"].append(f"文本格式渲染异常: {e}")

    svg, err = render_svg(mm, by_id, children, args.max_svg_nodes)
    if svg:
        write(p("svg"), svg)
        status["formats"]["svg"] = True
    else:
        status["formats"]["svg"] = False
        status["notes"].append(err)
    png_path, err = render_png(svg, mm, by_id, children, p("png"))
    if png_path:
        status["formats"]["png"] = True
    else:
        status["formats"]["png"] = False
        status["notes"].append(f"PNG 未生成: {err}")

    sp = os.path.join(args.out, f"{args.prefix}_preview_status.json" if args.prefix != "mindmap" else "preview_status.json")
    with open(sp, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    ok = [k for k, v in status["formats"].items() if v]
    print(f"[map_render] {args.prefix}: 已渲染 {ok}" + (f" 备注: {status['notes']}" if status["notes"] else ""))
    return 0

if __name__ == "__main__":
    sys.exit(main())
