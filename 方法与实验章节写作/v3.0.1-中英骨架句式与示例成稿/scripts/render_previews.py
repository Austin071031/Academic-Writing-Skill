#!/usr/bin/env python3
"""render_previews.py — 为可编辑产物生成可检查的预览（PDF/PNG/TXT）。

用法: python3 render_previews.py --out /app/output
优先 pandoc(+xelatex) 渲染 methods_chapter.md -> methods_chapter_preview.pdf；
不可用时降级为同名 .txt 预览并在 result.json exceptions 留痕（由 Agent 调用时记录）。
"""
import argparse, os, shutil, subprocess, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()
    src = os.path.join(args.out, "methods_chapter.md")
    if not os.path.exists(src):
        print("[preview] methods_chapter.md 不存在，跳过", file=sys.stderr)
        return 1
    pandoc = shutil.which("pandoc")
    if pandoc:
        pdf = os.path.join(args.out, "methods_chapter_preview.pdf")
        for engine in ("xelatex", "pdflatex"):
            r = subprocess.run([pandoc, src, "-o", pdf, "--pdf-engine", engine],
                               capture_output=True, timeout=180)
            if r.returncode == 0 and os.path.exists(pdf):
                print(f"[preview] 已渲染 {pdf}")
                return 0
        print(f"[preview][WARN] pandoc 渲染失败: {r.stderr.decode('utf-8','ignore')[:200]}", file=sys.stderr)
    txt = os.path.join(args.out, "methods_chapter_preview.txt")
    shutil.copyfile(src, txt)
    print(f"[preview] 无 pandoc/latex，降级为文本预览 {txt}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
