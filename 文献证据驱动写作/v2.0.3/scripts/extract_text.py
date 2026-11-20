#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""材料文本化：把 PDF/文本材料转成带页码标记的纯文本，存 /app/work/text/。
页标记格式: "===== [PAGE n] ====="，供逐字核验时反查定位。
引擎优先级: pdftotext > PyMuPDF(fitz) > pypdf；全部失败则如实标记 failed，不伪造文本。
用法: python3 extract_text.py [INPUT_DIR] [WORK_DIR]
"""
import json, os, re, subprocess, sys

INPUT = sys.argv[1] if len(sys.argv) > 1 else "/input"
WORK = sys.argv[2] if len(sys.argv) > 2 else "/app/work"
TEXTDIR = os.path.join(WORK, "text")
os.makedirs(TEXTDIR, exist_ok=True)

TEXT_EXT = (".pdf", ".txt", ".md", ".tex", ".rst", ".csv", ".tsv")

candidates = []
for root, _dirs, fs in os.walk(INPUT):
    for fn in sorted(fs):
        if os.path.splitext(fn)[1].lower() in TEXT_EXT:
            candidates.append(os.path.join(root, fn))

manifest = {}

def doc_id(p, n):
    base = os.path.splitext(os.path.basename(p))[0]
    base = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", base)[:40] or "doc"
    return "D%02d_%s" % (n, base)

def write_pages(out, txt):
    pages = txt.split("\f")
    with open(out, "w", encoding="utf-8") as f:
        for n, pg in enumerate(pages, 1):
            f.write("\n===== [PAGE %d] =====\n%s" % (n, pg))
    return len(pages)

for i, p in enumerate(sorted(candidates), 1):
    did = doc_id(p, i)
    ext = os.path.splitext(p)[1].lower()
    entry = {"source": os.path.relpath(p, INPUT), "text": None, "pages": 0,
             "chars": 0, "engine": None, "status": "ok", "error": None}
    out = os.path.join(TEXTDIR, did + ".txt")
    try:
        if ext == ".pdf":
            txt, engine, errors = None, None, []
            try:
                r = subprocess.run(["pdftotext", "-layout", p, "-"],
                                   capture_output=True, timeout=180)
                if r.returncode == 0 and r.stdout.strip():
                    txt = r.stdout.decode("utf-8", "replace")
                    engine = "pdftotext"
                else:
                    errors.append("pdftotext rc=%d stderr=%s" % (r.returncode, r.stderr.decode("utf-8", "replace")[:200]))
            except FileNotFoundError:
                errors.append("pdftotext not installed")
            except Exception as e:
                errors.append("pdftotext: %s" % e)
            if not txt:
                for mod in ("fitz", "pypdf"):
                    try:
                        if mod == "fitz":
                            import fitz  # type: ignore
                            d = fitz.open(p)
                            txt = "\n".join(pg.get_text() for pg in d)
                        else:
                            from pypdf import PdfReader  # type: ignore
                            rr = PdfReader(p)
                            txt = "\n".join((pg.extract_text() or "") for pg in rr.pages)
                        if txt and txt.strip():
                            engine = mod
                            break
                        txt = None
                        errors.append("%s: empty output" % mod)
                    except ImportError:
                        errors.append("%s not installed" % mod)
                    except Exception as e:
                        errors.append("%s: %s" % (mod, e))
                        txt = None
            if not txt or not txt.strip():
                entry["status"] = "failed"
                entry["error"] = "; ".join(errors) or "no text extracted"
            else:
                npg = write_pages(out, txt)
                entry.update(text=os.path.basename(out), pages=npg, chars=len(txt), engine=engine)
        else:
            with open(p, "rb") as f:
                raw = f.read()
            txt = raw.decode("utf-8", "replace")
            npg = write_pages(out, txt)
            entry.update(text=os.path.basename(out), pages=npg, chars=len(txt), engine="plain")
    except Exception as e:
        entry["status"] = "failed"
        entry["error"] = "%s: %s" % (type(e).__name__, e)
    manifest[did] = entry

with open(os.path.join(WORK, "text_manifest.json"), "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=1)

ok = sum(1 for v in manifest.values() if v["status"] == "ok")
failed = {k: v["error"] for k, v in manifest.items() if v["status"] != "ok"}
print(json.dumps({"converted": ok, "failed": len(failed), "failures": failed,
                  "docs": sorted(manifest)}, ensure_ascii=False))
