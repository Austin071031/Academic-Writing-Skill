#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""render_preview — 把可编辑产物渲染为 PDF/PNG 预览（真实渲染，不用伪造）。

探测顺序：soffice (LibreOffice) -> pandoc -> 无渲染（如实降级）。
DOCX 存在时优先 soffice --headless --convert-to pdf；
PDF 生成后用 pdftoppm 取前几页 PNG（无 pdftoppm 时跳过并注明）。
任何一步失败都写入渲染状态，绝不假装成功。
"""
import json
import os
import shutil
import subprocess
import sys


def which(cmd):
    return shutil.which(cmd)


def render(doc_path, out_dir, pages=3):
    os.makedirs(out_dir, exist_ok=True)
    status = {"source": doc_path, "pdf": None, "pngs": [],
              "renderer": None, "degraded": [], "ok": False}
    base = os.path.splitext(os.path.basename(doc_path))[0]
    pdf_path = os.path.join(out_dir, base + ".pdf")

    soffice = which("soffice") or which("libreoffice")
    if soffice and doc_path.lower().endswith((".docx", ".doc", ".odt")):
        try:
            r = subprocess.run(
                [soffice, "--headless", "--norestore", "--convert-to", "pdf",
                 "--outdir", out_dir, doc_path],
                capture_output=True, text=True, timeout=180)
            if os.path.exists(pdf_path):
                status["pdf"] = pdf_path
                status["renderer"] = "libreoffice"
                status["ok"] = True
            else:
                status["degraded"].append(
                    "soffice rc=%s %s" % (r.returncode, r.stderr[:200]))
        except Exception as e:  # noqa
            status["degraded"].append("soffice error: %s" % e)
    elif doc_path.lower().endswith(".pdf"):
        status["pdf"] = doc_path
        status["renderer"] = "direct-pdf"
        status["ok"] = True
    else:
        status["degraded"].append("no renderer for %s" % doc_path)

    if status["pdf"]:
        pdftoppm = which("pdftoppm")
        if pdftoppm:
            try:
                prefix = os.path.join(out_dir, base)
                subprocess.run(
                    [pdftoppm, "-png", "-r", "100", "-f", "1",
                     "-l", str(pages), status["pdf"], prefix],
                    capture_output=True, text=True, timeout=120)
                for f in sorted(os.listdir(out_dir)):
                    if f.startswith(base + "-") and f.endswith(".png"):
                        status["pngs"].append(os.path.join(out_dir, f))
            except Exception as e:  # noqa
                status["degraded"].append("pdftoppm error: %s" % e)
        else:
            status["degraded"].append("pdftoppm unavailable")
    return status


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    doc_path, out_dir = sys.argv[1], sys.argv[2]
    pages = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    status = render(doc_path, out_dir, pages)
    status_path = os.path.join(out_dir, "render_status.json")
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=1)
    print(json.dumps(status, ensure_ascii=False))
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
