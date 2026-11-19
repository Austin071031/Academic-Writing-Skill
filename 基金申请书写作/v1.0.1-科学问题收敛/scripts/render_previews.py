#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_previews.py --out O --work W

O/preview.html：内联 CSS，report/draft/element_mapping 三栏 sections，
内容全部 HTML 转义。preview.pdf 尽力：pandoc/libreoffice/wkhtmltopdf
任一可用则尝试生成；全部不可用或失败 → preview_skipped.txt 说明。exit 0。
"""
import argparse
import html
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "render_previews"

HTML_TMPL = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>基金申请书写作预览</title>
<style>
body{{font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif;margin:0;
background:#f4f5f7;color:#222;}}
h1{{font-size:20px;padding:16px 24px;margin:0;background:#2c3e50;color:#fff;}}
.wrap{{display:flex;gap:12px;padding:12px;}}
.col{{flex:1;background:#fff;border:1px solid #ddd;border-radius:6px;
min-width:0;display:flex;flex-direction:column;max-height:90vh;}}
.col h2{{font-size:14px;margin:0;padding:10px 12px;background:#ecf0f1;
border-bottom:1px solid #ddd;}}
.col pre{{font-family:"Noto Sans Mono CJK SC",monospace;font-size:12px;
line-height:1.55;padding:10px 12px;margin:0;white-space:pre-wrap;
word-break:break-all;overflow-y:auto;}}
</style></head><body>
<h1>基金申请书写作 Skill · 预览（合成/实际运行产物）</h1>
<div class="wrap">
<div class="col"><h2>report.md（质量报告）</h2><pre>{report}</pre></div>
<div class="col"><h2>proposal_draft.md（章节稿）</h2><pre>{draft}</pre></div>
<div class="col"><h2>element_mapping.md（要素对照）</h2><pre>{mapping}</pre></div>
</div></body></html>
"""


def read_or_note(out, name):
    try:
        with open(os.path.join(out, name), "r", encoding="utf-8",
                  errors="replace") as f:
            return f.read()
    except Exception:
        return f"（{name} 不存在或无法读取）"


def try_pdf(out, work):
    html_path = os.path.join(out, "preview.html")
    pdf_path = os.path.join(out, "preview.pdf")
    attempts = []
    exe = shutil.which("wkhtmltopdf")
    if exe:
        attempts.append([exe, "--quiet", html_path, pdf_path])
    exe = shutil.which("libreoffice")
    if exe:
        attempts.append([exe, "--headless", "--convert-to", "pdf",
                         "--outdir", out, html_path])
    exe = shutil.which("pandoc")
    if exe:
        attempts.append([exe, "-f", "html", "-t", "pdf", "-o", pdf_path,
                         html_path])
    for cmd in attempts:
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=120,
                               cwd=out)
            if r.returncode == 0 and os.path.exists(pdf_path) \
                    and os.path.getsize(pdf_path) > 0:
                print(f"[render_previews] preview.pdf via {cmd[0]}")
                return True
        except Exception as e:
            gu.record_exception(work, STAGE, cmd[0], e, "尝试下一种 PDF 方案")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    work, out = args.work, gu.env_output_dir(args.out)
    gu.ensure_dir(out)

    content = HTML_TMPL.format(
        report=html.escape(read_or_note(out, "report.md")),
        draft=html.escape(read_or_note(out, "proposal_draft.md")),
        mapping=html.escape(read_or_note(out, "element_mapping.md")))
    with open(os.path.join(out, "preview.html"), "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[render_previews] preview.html written")

    if not try_pdf(out, work):
        with open(os.path.join(out, "preview_skipped.txt"), "w",
                  encoding="utf-8") as f:
            f.write("preview.pdf 未生成：pandoc/libreoffice/wkhtmltopdf "
                    "均不可用或转换失败（尽力而为，不影响交付）。\n")
        print("[render_previews] preview.pdf skipped (no working converter)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[render_previews] ERROR: {e}")
        raise SystemExit(1)
