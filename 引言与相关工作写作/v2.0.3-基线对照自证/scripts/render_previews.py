#!/usr/bin/env python3
"""render_previews.py — 为可编辑产物渲染 HTML 预览（必出），尽力渲染 PDF（可降级）。

用法: python3 render_previews.py --out /app/output [--work /app/work]
将 introduction.md / related_work.md / references.md 及各版本报告转为一个自包含 preview.html；
若环境存在 wkhtmltopdf 则另出 preview.pdf，否则在 preview_status.json 中诚实记录。
"""
import argparse, html, json, os, re, shutil, subprocess, sys

def md_to_html(text):
    out = []
    in_list = False
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
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(re.match(r"^:?-{2,}:?$", c) for c in cells if c):
                continue
            out.append("<p class='row'>" + " ｜ ".join(html.escape(c) for c in cells) + "</p>")
        elif line.strip():
            out.append(f"<p>{html.escape(line)}</p>")
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    status = {"html": None, "pdf": None, "notes": []}
    sections = []
    titles = {"introduction.md": "引言", "related_work.md": "相关工作",
              "references.md": "参考文献", "report.md": "运行报告",
              "comparison_matrix.md": "相关工作比较矩阵",
              "gap_derivation.md": "研究空白推导链",
              "contributions_check.md": "贡献-证据对照表",
              "coverage_report.md": "引用覆盖审计报告",
              "anti_fluff_audit.md": "背景空转铺垫审计"}
    for name, title in titles.items():
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
li{{margin-left:1.5em}} p{{text-align:justify}} .row{{font-size:.92em;color:#222}}
</style></head><body>{body}</body></html>"""
    hp = os.path.join(args.out, "preview.html")
    with open(hp, "w", encoding="utf-8") as f:
        f.write(doc)
    status["html"] = "preview.html"

    pdf_tool = None
    if shutil.which("wkhtmltopdf"):
        try:
            r = subprocess.run(["wkhtmltopdf", hp, os.path.join(args.out, "preview.pdf")],
                               capture_output=True, timeout=120)
            if r.returncode == 0 and os.path.exists(os.path.join(args.out, "preview.pdf")):
                pdf_tool = "wkhtmltopdf"
                status["pdf"] = "preview.pdf"
            else:
                status["notes"].append("wkhtmltopdf 运行失败，已跳过 PDF")
        except Exception as e:
            status["notes"].append(f"wkhtmltopdf 异常: {e}")
    if not pdf_tool:
        status["notes"].append("环境无 HTML->PDF 工具，仅交付 HTML 预览（可编辑原稿见 .md 文件）")

    with open(os.path.join(args.out, "preview_status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    print(f"[render_previews] preview.html 已生成" + (" + preview.pdf" if status["pdf"] else ""))
    return 0

if __name__ == "__main__":
    sys.exit(main())
