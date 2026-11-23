#!/usr/bin/env python3
"""finalize.py — 一段式收尾：渲染预览（逐级降级）→ 按 output_contract 组装 result.json → 终检。
manuscript.md 是唯一硬要求；其余产物缺失如实标注。仅用标准库 + 可选系统工具。"""
import argparse, json, os, re, shutil, subprocess, sys, datetime

def which(c): return shutil.which(c) is not None
def run(cmd, t=240):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=t)
        return r.returncode, r.stderr.decode("utf-8", "replace")[:200]
    except Exception as e:
        return -1, str(e)[:200]
def load(p, d=None):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d

def render(out, ms):
    man = {}
    if not (os.path.isfile(ms) and os.path.getsize(ms) > 0):
        return {"docx": "skipped: 无 manuscript", "pdf": "skipped", "png": "skipped"}
    docx, pdf = os.path.join(out, "manuscript.docx"), os.path.join(out, "manuscript.pdf")
    if which("pandoc"):
        rc, err = run(["pandoc", ms, "-o", docx, "--standalone"])
        man["docx"] = "ok" if rc == 0 and os.path.isfile(docx) else f"unavailable: {err}"
    else:
        man["docx"] = "unavailable: 无 pandoc"
    done = False
    if man["docx"] == "ok" and (which("libreoffice") or which("soffice")):
        exe = "libreoffice" if which("libreoffice") else "soffice"
        rc, err = run([exe, "--headless", "--convert-to", "pdf", "--outdir", out, docx], 300)
        done = rc == 0 and os.path.isfile(pdf)
        man["pdf"] = "ok" if done else f"unavailable: {err}"
    if not done and which("pandoc"):
        rc, err = run(["pandoc", ms, "-o", pdf, "-V", "CJKmainfont=Noto Sans CJK SC", "--pdf-engine=xelatex"], 300)
        done = rc == 0 and os.path.isfile(pdf)
        man["pdf"] = "ok" if done else f"unavailable: {err}"
    os.makedirs(os.path.join(out, "preview"), exist_ok=True)
    if man.get("pdf") == "ok" and which("pdftoppm"):
        run(["pdftoppm", "-png", "-r", "110", "-f", "1", "-l", "4", pdf, os.path.join(out, "preview", "page")], 180)
        pngs = sorted(p for p in os.listdir(os.path.join(out, "preview")) if p.endswith(".png"))
        man["png"] = f"ok ({len(pngs)} 页)" if pngs else "unavailable: pdftoppm 无输出"
    else:
        man["png"] = "unavailable: 无 PDF 或 pdftoppm"
    return man

HINTS = [(r"^case_?id$", "case_id"), (r"status|状态", "status"),
 (r"manuscript|稿件|文稿|editable|draft|deliverable|paper|产物|document", "manuscript"),
 (r"evidence|证据|source|来源|溯源|provenance|map|映射|trace|claim", "evidence"),
 (r"uncertaint|不确定|待确认|limit|gap|缺口|exception|异常|边界", "uncertainty"),
 (r"change|修改|留痕|diff|version|log|记录", "change_log"),
 (r"consisten|一致|check|核验|audit|quality|report", "report"),
 (r"preview|预览|render|pdf|png|export", "preview"), (r"summary|摘要|note|说明", "summary")]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work"); ap.add_argument("--out", default="/app/output")
    ap.add_argument("--engine-report", default="", help="专项引擎报告 JSON 路径（verdict 字段联动 status）")
    a = ap.parse_args()
    out = a.out
    brief = load(os.path.join(a.work, "brief.json"), {}) or {}
    cid, contract = brief.get("case_id", "UNKNOWN-CASE"), brief.get("output_contract", []) or []
    rep = load(a.engine_report, {}) if a.engine_report else {}
    verdict = (rep or {}).get("verdict", "PASS")
    ms = os.path.join(out, "manuscript.md")
    ms_ok = os.path.isfile(ms) and os.path.getsize(ms) > 200
    status = "success" if (ms_ok and verdict in ("PASS", "WARN")) else ("partial" if ms_ok else "failed")
    man = render(out, ms)
    artifacts = [f for f in sorted(os.listdir(out)) if os.path.isfile(os.path.join(out, f))]
    pngs = sorted("preview/" + p for p in os.listdir(os.path.join(out, "preview")) if p.endswith(".png")) if os.path.isdir(os.path.join(out, "preview")) else []
    unc = []
    for u in (rep or {}).get("warnings", []): unc.append(u)
    for k, v in man.items():
        if str(v).startswith("unavailable"): unc.append(f"预览 {k}: {v}")
    for i in brief.get("issues", []): unc.append(f"输入: {i}")
    if verdict == "FAIL":
        unc = [f"专项核验未通过: {x}" for x in (rep or {}).get("fails", [])] + unc
        status = "partial"
    unc = list(dict.fromkeys(unc))
    dl = {"manuscript_md": "/app/output/manuscript.md"} if ms_ok else {}
    if man.get("docx") == "ok": dl["manuscript_docx"] = "/app/output/manuscript.docx"
    if man.get("pdf") == "ok": dl["manuscript_pdf"] = "/app/output/manuscript.pdf"
    if pngs: dl["preview_png"] = ["/app/output/" + p for p in pngs]
    for f in artifacts:
        if f.endswith((".md", ".json")) and f not in ("result.json", "manuscript.md", "preview_manifest.json"):
            dl.setdefault(f.rsplit(".", 1)[0], f"/app/output/{f}")
    chlog = []
    cl = os.path.join(out, "change_log.md")
    if os.path.isfile(cl):
        chlog = [l[2:].strip() for l in open(cl, encoding="utf-8", errors="replace") if l.startswith("- ")][:200]
    summary = (f"case {cid}: manuscript={'ok' if ms_ok else 'missing'}, engine_verdict={verdict}, "
               f"status={status}, 产物 {len(dl)} 项, 待确认 {len(unc)} 项")
    vals = {"case_id": cid, "status": status, "manuscript": dl, "evidence": {
                "note": "事实/引用/章节的来源锚点见随附映射与核验文件", "files": [f for f in artifacts if "map" in f or "index" in f or "matrix" in f]},
            "uncertainty": unc, "change_log": chlog or "见 change_log.md（如任务涉及改稿）",
            "report": {"engine_verdict": verdict, "files": [f for f in artifacts if "report" in f or "audit" in f or "check" in f]},
            "preview": {"steps": man, "png": ["/app/output/" + p for p in pngs]}, "summary": summary}
    result = {"case_id": cid, "status": status, "generated_utc": datetime.datetime.now(datetime.UTC).isoformat(),
              "deliverables": dl, "sources": {"brief": "/app/work/brief.json", "engine_report": a.engine_report or None},
              "engine_verdict": verdict, "uncertainty": unc, "change_log": chlog,
              "run_log": "/app/output/run_log.md", "stage": "final"}
    for f in contract:
        if f in result: continue
        kind = next((k for p, k in HINTS if re.search(p, f, re.I)), "summary")
        result[f] = vals[kind]
    json.dump(result, open(os.path.join(out, "result.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    missing = [f for f in contract if f not in result]
    checks = [("manuscript 非空", ms_ok), ("contract 字段齐全", not missing), ("status 合法", status in ("success", "partial", "failed"))]
    overall = "PASS" if all(ok for _n, ok in checks) else "FAIL"
    with open(os.path.join(out, "validation.md"), "w", encoding="utf-8") as f:
        f.write(f"# 交付终检 {datetime.datetime.now(datetime.UTC).isoformat()}\n\n**overall: {overall}**\n\n")
        for n, ok in checks: f.write(f"- [{'PASS' if ok else 'FAIL'}] {n}\n")
        f.write(f"- 渲染: {json.dumps(man, ensure_ascii=False)}\n- status={status} verdict={verdict}\n")
    with open(os.path.join(out, "run_log.md"), "a", encoding="utf-8") as f:
        f.write(f"\n## finalize overall={overall} status={status} verdict={verdict} render={man}\n")
    print(json.dumps({"overall": overall, "status": status, "verdict": verdict,
                      "missing_contract": missing, "render": man}, ensure_ascii=False))

if __name__ == "__main__":
    try: main()
    except Exception as e:
        sys.stderr.write(f"finalize fatal: {e}\n")
        try:
            rj = load("/app/output/result.json", {}) or {}
            rj.setdefault("status", "partial"); rj.setdefault("finalize_error", str(e)[:200])
            json.dump(rj, open("/app/output/result.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception: pass
        sys.exit(1)
