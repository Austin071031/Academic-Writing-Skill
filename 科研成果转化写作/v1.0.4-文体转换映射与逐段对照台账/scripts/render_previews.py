#!/usr/bin/env python3
"""render_previews.py — 为 /app/output 下全部 Markdown 产物渲染自包含 HTML 预览（必出）。

用法: python3 render_previews.py --out /app/output [--work /app/work]
- 预览全部 *.md 产物（跳过 result.json / preview*.html），按文件名排序；
- 尽力用 wkhtmltopdf 渲染 preview.pdf，失败则在 preview_status.json 如实记录（不伪造）。
"""
import argparse, html, json, os, re, shutil, subprocess, sys

def md_to_html(text):
    out = []
    in_list = False
    for line in text.splitlines():
        if line.startswith("#### "):
            out.append(f"<h4>{html.escape(line[5:])}</h4>")
        elif line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif re.match(r"^[-*] ", line):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{html.escape(line[2:])}</li>")
        elif line.strip():
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{html.escape(line)}</p>")
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append("")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    status = {"html": None, "pdf": None, "notes": [], "sections": []}
    mds = sorted(fn for fn in os.listdir(args.out)
                 if fn.endswith(".md") and os.path.isfile(os.path.join(args.out, fn)))
    sections = []
    for fn in mds:
        with open(os.path.join(args.out, fn), encoding="utf-8") as f:
            sections.append((fn, md_to_html(f.read())))
        status["sections"].append(fn)
    if not sections:
        status["notes"].append("无可预览产物（无 .md 输出）")
        with open(os.path.join(args.out, "preview_status.json"), "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
        print("[render_previews] 无可预览产物")
        return 0

    body = "".join(f"<section><h1 style='border-bottom:2px solid #333'>{html.escape(t)}</h1>{c}</section>"
                   for t, c in sections)
    doc = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>preview</title><style>
body{{font-family:"Noto Sans CJK SC","WenQuanYi Micro Hei",sans-serif;max-width:780px;
margin:2em auto;padding:0 1em;line-height:1.75;color:#111}}
li{{margin-left:1.5em}} p{{text-align:justify}}
blockquote{{color:#555;border-left:3px solid #ccc;padding-left:.8em}}
</style></head><body>{body}</body></html>"""
    hp = os.path.join(args.out, "preview.html")
    with open(hp, "w", encoding="utf-8") as f:
        f.write(doc)
    status["html"] = "preview.html"

    if shutil.which("wkhtmltopdf"):
        try:
            r = subprocess.run(["wkhtmltopdf", hp, os.path.join(args.out, "preview.pdf")],
                               capture_output=True, timeout=120)
            if r.returncode == 0 and os.path.exists(os.path.join(args.out, "preview.pdf")):
                status["pdf"] = "preview.pdf"
            else:
                status["notes"].append("wkhtmltopdf 运行失败，已跳过 PDF")
        except Exception as e:
            status["notes"].append(f"wkhtmltopdf 异常: {e}")
    if not status["pdf"]:
        status["notes"].append("环境无 HTML->PDF 工具或转换失败，仅交付 HTML 预览（可编辑原稿见 .md 文件）")

    with open(os.path.join(args.out, "preview_status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    print(f"[render_previews] preview.html 已生成（{len(sections)} 个产物）"
          + (" + preview.pdf" if status["pdf"] else ""))
    return 0

if __name__ == "__main__":
    sys.exit(main())
