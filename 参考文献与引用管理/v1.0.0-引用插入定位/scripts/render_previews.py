#!/usr/bin/env python3
"""render_previews.py — 为可编辑产物渲染 HTML 预览（必出），尽力渲染 PDF/PNG（可降级）。

用法: python3 render_previews.py --out /app/output [--work /app/work]
将 edited_manuscript.md / references.md / report.md 转为一个自包含 preview.html；
若环境存在 weasyprint/wkhtmltopdf 则另出 preview.pdf，否则在 preview_status.json 中诚实记录。
"""
import argparse, html, json, os, re, shutil, subprocess, sys, datetime

def md_to_html(text):
    out = []
    for line in text.splitlines():
        if line.startswith("### "):
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif re.match(r"^[-*] ", line):
            out.append(f"<li>{html.escape(line[2:])}</li>")
        elif re.match(r"^\d+\. ", line):
            out.append(f"<li>{html.escape(re.sub(r'^\d+\. ', '', line))}</li>")
        elif line.strip():
            out.append(f"<p>{html.escape(line)}</p>")
        else:
            out.append("")
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    status = {"html": None, "pdf": None, "notes": []}
    sections = []
    for name, title in (("edited_manuscript.md", "改后稿件"),
                        ("references.md", "参考文献表"),
                        ("report.md", "运行报告"),
                        ("dedup_report.md", "去重报告"),
                        ("merge_report.md", "合并报告"),
                        ("renumber_report.md", "编号更新说明")):
        p = os.path.join(args.out, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                sections.append((title, md_to_html(f.read())))
    if not sections:
        status["notes"].append("无可预览产物")
        with open(os.path.join(args.out, "preview_status.json"), "w", encoding="utf-8") as f:
            json.dump(status, f, ensure_ascii=False, indent=2)
        print("[render_previews] 无可预览产物")
        return 0

    body = "".join(f"<section><h1 style='border-bottom:2px solid #333'>{t}</h1>{c}</section>"
                   for t, c in sections)
    doc = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>preview</title><style>
body{{font-family:"Noto Sans CJK SC","WenQuanYi Micro Hei",sans-serif;max-width:760px;
margin:2em auto;padding:0 1em;line-height:1.7;color:#111}}
li{{margin-left:1.5em}} p{{text-align:justify}}
</style></head><body>{body}</body></html>"""
    hp = os.path.join(args.out, "preview.html")
    with open(hp, "w", encoding="utf-8") as f:
        f.write(doc)
    status["html"] = "preview.html"

    pdf_tool = None
    for tool, cmd in (("wkhtmltopdf", ["wkhtmltopdf", hp, os.path.join(args.out, "preview.pdf")]),):
        if shutil.which(tool):
            try:
                r = subprocess.run(cmd, capture_output=True, timeout=120)
                if r.returncode == 0 and os.path.exists(os.path.join(args.out, "preview.pdf")):
                    pdf_tool = tool
                    status["pdf"] = "preview.pdf"
                else:
                    status["notes"].append(f"{tool} 运行失败，已跳过 PDF")
            except Exception as e:
                status["notes"].append(f"{tool} 异常: {e}")
            break
    if not pdf_tool:
        status["notes"].append("环境无 HTML->PDF 工具，仅交付 HTML 预览（可编辑原稿见 .md 文件）")

    with open(os.path.join(args.out, "preview_status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    print(f"[render_previews] preview.html 已生成" + (" + preview.pdf" if status["pdf"] else ""))
    return 0

if __name__ == "__main__":
    sys.exit(main())
