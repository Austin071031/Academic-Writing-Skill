#!/usr/bin/env python3
"""render_preview.py — manuscript.md → docx → PDF → PNG 预览，逐级降级、如实记录。

产物（--out 下）：manuscript.docx、manuscript.pdf、preview/page-*.png、preview_manifest.json。
缺失工具不报错造假，manifest 中写明 unavailable 原因。仅用标准库 + 系统工具。
"""
import argparse, json, os, subprocess, sys, datetime, shutil

def which(cmd):
    return shutil.which(cmd) is not None

def run(cmd, timeout=240):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.returncode, r.stderr.decode("utf-8", "replace")[:300]
    except Exception as e:
        return -1, str(e)[:300]

def md_to_docx_fallback(md_path, docx_path):
    """无 pandoc 时用 python-docx 做简版转换（标题/段落/列表/表格忽略格式）。"""
    try:
        import docx
        from docx.shared import Pt
    except Exception:
        return False, "python-docx 不可用"
    try:
        d = docx.Document()
        for line in open(md_path, encoding="utf-8", errors="replace"):
            s = line.rstrip("\n")
            if s.startswith("#### "):
                d.add_heading(s[5:].strip(), level=4)
            elif s.startswith("### "):
                d.add_heading(s[4:].strip(), level=3)
            elif s.startswith("## "):
                d.add_heading(s[3:].strip(), level=2)
            elif s.startswith("# "):
                d.add_heading(s[2:].strip(), level=1)
            elif s.startswith(("- ", "* ")):
                d.add_paragraph(s[2:].strip(), style="List Bullet")
            elif s.strip() == "":
                continue
            elif s.startswith("|"):
                d.add_paragraph(s)  # 表格行原样保留，保证内容不丢
            else:
                d.add_paragraph(s)
        d.save(docx_path)
        return True, ""
    except Exception as e:
        return False, str(e)[:200]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manuscript", default="/app/output/manuscript.md")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--pages", type=int, default=4)
    args = ap.parse_args()
    out, ms = args.out, args.manuscript
    prev_dir = os.path.join(out, "preview")
    os.makedirs(prev_dir, exist_ok=True)
    manifest = {"created_utc": datetime.datetime.utcnow().isoformat() + "Z", "steps": {}}

    if not (os.path.isfile(ms) and os.path.getsize(ms) > 0):
        manifest["steps"]["docx"] = {"status": "skipped", "reason": "manuscript.md 缺失或为空"}
        with open(os.path.join(out, "preview_manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        print(json.dumps({"ok": False, "reason": "no manuscript"}, ensure_ascii=False))
        return 0

    docx_path = os.path.join(out, "manuscript.docx")
    # 1) md -> docx
    if which("pandoc"):
        rc, err = run(["pandoc", ms, "-o", docx_path, "--standalone"])
        if rc == 0 and os.path.isfile(docx_path):
            manifest["steps"]["docx"] = {"status": "ok", "tool": "pandoc"}
        else:
            ok, err2 = md_to_docx_fallback(ms, docx_path)
            manifest["steps"]["docx"] = {"status": "ok" if ok else "unavailable",
                                         "tool": "python-docx fallback",
                                         "reason": "" if ok else f"pandoc:{err}; docx:{err2}"}
    else:
        ok, err2 = md_to_docx_fallback(ms, docx_path)
        manifest["steps"]["docx"] = {"status": "ok" if ok else "unavailable",
                                     "tool": "python-docx fallback", "reason": "" if ok else err2}

    # 2) -> pdf
    pdf_path = os.path.join(out, "manuscript.pdf")
    done = False
    if manifest["steps"]["docx"]["status"] == "ok" and (which("libreoffice") or which("soffice")):
        exe = "libreoffice" if which("libreoffice") else "soffice"
        rc, err = run([exe, "--headless", "--convert-to", "pdf", "--outdir", out, docx_path], timeout=300)
        if rc == 0 and os.path.isfile(pdf_path):
            manifest["steps"]["pdf"] = {"status": "ok", "tool": exe}
            done = True
        else:
            manifest["steps"]["pdf"] = {"status": "unavailable", "reason": f"{exe}: {err}"}
    if not done and which("pandoc"):
        rc, err = run(["pandoc", ms, "-o", pdf_path, "-V", "CJKmainfont=Noto Sans CJK SC",
                       "--pdf-engine=xelatex"], timeout=300)
        if rc == 0 and os.path.isfile(pdf_path):
            manifest["steps"]["pdf"] = {"status": "ok", "tool": "pandoc+xelatex"}
            done = True
        elif "pdf" not in manifest["steps"]:
            manifest["steps"]["pdf"] = {"status": "unavailable",
                                        "reason": "无 LibreOffice；pandoc/xelatex 也失败: " + err[:200]}
    if "pdf" not in manifest["steps"]:
        manifest["steps"]["pdf"] = {"status": "unavailable", "reason": "无可用转换工具"}

    # 3) pdf -> png
    if manifest["steps"]["pdf"]["status"] == "ok" and which("pdftoppm"):
        prefix = os.path.join(prev_dir, "page")
        rc, err = run(["pdftoppm", "-png", "-r", "110", "-f", "1", "-l", str(args.pages),
                       pdf_path, prefix], timeout=180)
        pages = sorted(fn for fn in os.listdir(prev_dir) if fn.startswith("page") and fn.endswith(".png"))
        manifest["steps"]["png"] = {"status": "ok" if pages else "unavailable",
                                    "pages": [f"preview/{p}" for p in pages],
                                    "reason": "" if pages else err}
    else:
        manifest["steps"]["png"] = {"status": "unavailable",
                                    "reason": "无 PDF 或缺 pdftoppm"}

    with open(os.path.join(out, "preview_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    try:
        with open(os.path.join(out, "run_log.md"), "a", encoding="utf-8") as f:
            f.write(f"\n## render_preview {manifest['created_utc']} "
                    + " ".join(f"{k}={v['status']}" for k, v in manifest["steps"].items()) + "\n")
    except Exception:
        pass
    print(json.dumps({"ok": True,
                      "steps": {k: v["status"] for k, v in manifest["steps"].items()}}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    sys.exit(main())
