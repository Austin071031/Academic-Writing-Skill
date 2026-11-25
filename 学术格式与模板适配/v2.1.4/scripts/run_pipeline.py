#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_pipeline.py — One-shot orchestrator for the academic format & template
adaptation pipeline.  Every stage is isolated: a failure in one stage is
recorded and the pipeline continues with graceful degradation, so an honest
partial result.json is always written to /app/output.

Stages:
    inspect -> measure (template) -> spec -> convert-source (if needed)
    -> adapt -> fidelity -> compliance -> render (+TOC two-pass) -> result

Usage:
    python3 run_pipeline.py [--case /input/case.json] [--task /input/task.md] \
        [--work /app/work] [--outdir /app/output] [--manuscript PATH] \
        [--template PATH] [--no-toc] [--stages a,b,c]

Stdlib only (LibreOffice / pandoc / poppler used opportunistically).
"""
import argparse
import json
import os
import subprocess
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

WORK = "/app/work"
OUTDIR = "/app/output"


def _stage(name):
    def deco(fn):
        def wrapper(ctx):
            st = {"stage": name, "status": "success"}
            try:
                fn(ctx, st)
            except Exception as e:  # noqa: BLE001
                st["status"] = "failed"
                st["error"] = "%s: %s" % (type(e).__name__, e)
                st["traceback"] = traceback.format_exc()[-2000:]
            with open(os.path.join(ctx["work"], "stage_%s.json" % name), "w",
                      encoding="utf-8") as f:
                json.dump(st, f, ensure_ascii=False, indent=2)
            print("[stage:%s] %s" % (name, st["status"]))
            return st
        return wrapper
    return deco


def _sh(cmd, timeout=300):
    return subprocess.run(cmd, capture_output=True, timeout=timeout)


# ---------------------------------------------------------------------------
# stages
# ---------------------------------------------------------------------------

@_stage("inspect")
def s_inspect(ctx, st):
    case = ctx.get("case") or "/input/case.json"
    task = ctx.get("task") or "/input/task.md"
    plan = os.path.join(ctx["work"], "plan.json")
    import inspect_case
    if not os.path.exists(case):
        # synthesize a minimal case descriptor from task.md (work dir, never
        # assume /input is writable)
        case = os.path.join(ctx["work"], "case_synthesized.json")
        with open(case, "w", encoding="utf-8") as f:
            task_txt = ""
            if os.path.exists(task):
                with open(task, encoding="utf-8", errors="replace") as tf:
                    task_txt = tf.read()
            json.dump({"task": task_txt, "materials": []}, f, ensure_ascii=False)
        st["note"] = "/input/case.json 不存在，已从 task.md 合成案例描述"
    inspect_case.main(["--case", case, "--task", task, "--out", plan])
    ctx["plan"] = json.load(open(plan, encoding="utf-8"))
    st["case_id"] = ctx["plan"].get("case_id")


@_stage("measure")
def s_measure(ctx, st):
    tpl = ctx.get("template") or ((ctx["plan"].get("template") or {}).get("resolved"))
    if not tpl or not os.path.exists(tpl):
        # scan /input for a template-like document (name hint, else second docx)
        cands = []
        mdirs = ["/input", "/input/materials", "/input/files",
                 os.path.dirname(ctx.get("task") or "/input/task.md"),
                 os.path.dirname(os.path.abspath(ctx.get("case") or "/input/case.json"))]
        for d in mdirs:
            if os.path.isdir(d):
                for f in sorted(os.listdir(d)):
                    p = os.path.join(d, f)
                    if os.path.isfile(p) and p.lower().endswith((".docx", ".dotx")):
                        cands.append(p)
        named = [c for c in cands if any(k in os.path.basename(c).lower()
                 for k in ("template", "模板", "target", "style", "格式"))]
        msrc = ctx.get("manuscript")
        others = [c for c in cands if c != msrc and c not in
                  ((ctx["plan"].get("docx_candidates")) or [])]
        tpl = (named or others or [None])[0]
        if tpl:
            st["note"] = "模板经文件扫描推断：%s（请人工复核其角色）" % tpl
    if not tpl or not tpl.lower().endswith((".docx", ".dotx")) or not os.path.exists(tpl):
        st["status"] = "partial"
        st["error"] = "无 docx/dotx 模板可实测（模板缺失或为非 docx 格式），跳过实测阶段"
        ctx["measured"] = None
        return
    import measure_template
    out = os.path.join(ctx["work"], "spec_template.json")
    cl = os.path.join(ctx["work"], "checklist.md")
    measure_template.main([tpl, "--out", out, "--checklist", cl])
    ctx["measured"] = out
    st["checklist"] = cl


@_stage("spec")
def s_spec(ctx, st):
    import extract_spec
    plan = ctx["plan"]
    work = ctx["work"]
    text_path = os.path.join(work, "task_text.md")
    with open(text_path, "w", encoding="utf-8") as f:
        f.write(plan.get("task_text") or "")
        f.write("\n\n--- task.md ---\n")
        f.write(plan.get("task_md_head") or "")
    tpl = ctx.get("template") or ((plan.get("template") or {}).get("resolved"))
    tex = pdf = None
    if tpl and os.path.exists(tpl):
        ext = os.path.splitext(tpl)[1].lower()
        if ext in (".tex", ".cls"):
            tex = tpl
        elif ext == ".pdf":
            pdf = tpl
    out = os.path.join(work, "spec.json")
    argv = ["--text", text_path, "--out", out]
    if ctx.get("measured"):
        argv += ["--measured", ctx["measured"]]
    if tex:
        argv += ["--tex", tex]
    if pdf:
        argv += ["--pdf", pdf]
    extract_spec.main(argv)
    ctx["spec"] = out
    spec = json.load(open(out, encoding="utf-8"))
    st["conflicts"] = len(spec.get("conflicts", []))
    st["unresolved"] = spec.get("unresolved", [])


def _docx_from_text(text, out_path, title=""):
    """Minimal docx writer for PDF-derived plain text (honest fallback)."""
    import zipfile
    from xml.sax.saxutils import escape
    paras = []
    if title:
        paras.append('<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>'
                     "<w:r><w:t>%s</w:t></w:r></w:p>" % escape(title))
    for line in text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        paras.append("<w:p><w:r><w:t xml:space=\"preserve\">%s</w:t></w:r></w:p>" % escape(line))
    sectpr = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
              '<w:pgMar w:top="1440" w:right="1800" w:bottom="1440" w:left="1800"/>'
              "</w:sectPr>")
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>" + "".join(paras) + sectpr +
        "</w:body></w:document>")
    ct = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="xml" ContentType="application/xml"/>'
          '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
          "</Types>")
    rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            "</Relationships>")
    drels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct)
        z.writestr("_rels/.rels", rels)
        z.writestr("word/_rels/document.xml.rels", drels)
        z.writestr("word/document.xml", document)


@_stage("convert_source")
def s_convert(ctx, st):
    """Ensure ctx['manuscript'] is a docx; convert tex/md/pdf if needed."""
    src = ctx.get("manuscript") or (
        ctx["plan"].get("docx_candidates") or [None])[0]
    CONVERTIBLE = (".docx", ".tex", ".md", ".txt", ".rtf", ".doc", ".odt", ".pdf")
    if not src or not os.path.exists(src):
        # fall back to any existing convertible material, then to a scan of /input
        for m in ctx["plan"].get("materials", []):
            p = m.get("resolved")
            if p and os.path.splitext(p)[1].lower() in CONVERTIBLE \
                    and m.get("kind") != "template":
                src = p
                break
    if not src or not os.path.exists(src):
        template_resolved = (ctx["plan"].get("template") or {}).get("resolved")
        scan_dirs = ["/input", "/input/materials", "/input/files",
                     os.path.dirname(ctx.get("task") or "/input/task.md")]
        # C3: also scan the directory holding the (possibly nonstandard) case.json
        cdir = os.path.dirname(os.path.abspath(ctx.get("case") or "/input/case.json"))
        if cdir not in scan_dirs:
            scan_dirs.append(cdir)
        for d in scan_dirs:
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                p = os.path.join(d, f)
                if os.path.isfile(p) and os.path.splitext(p)[1].lower() in CONVERTIBLE \
                        and p != template_resolved:
                    src = p
                    break
            if src:
                break
    if not src or not os.path.exists(src):
        st["status"] = "failed"
        st["error"] = "找不到可处理的稿件文件（见 plan.json materials；/input 扫描亦无候选）"
        return
    ext = os.path.splitext(src)[1].lower()
    work = ctx["work"]
    if ext == ".docx":
        ctx["manuscript"] = src
        return
    conv = os.path.join(work, "manuscript_converted.docx")
    if ext in (".tex", ".md", ".txt", ".rtf", ".doc", ".odt"):
        r = _sh(["pandoc", src, "-o", conv] if ext != ".doc" else
                ["soffice", "--headless", "--convert-to", "docx", "--outdir", work, src])
        if not os.path.exists(conv) and ext == ".doc":
            cands = [f for f in os.listdir(work) if f.endswith(".docx")]
            if cands:
                os.replace(os.path.join(work, cands[0]), conv)
        if os.path.exists(conv):
            ctx["manuscript"] = conv
            st["note"] = "源稿 %s 经转换得到 docx（转换可能损失部分格式，保真度以转换后为基线）" % ext
            ctx["converted_from"] = src
            return
        st["status"] = "failed"
        st["error"] = "pandoc/soffice 转换 %s 失败" % ext
        return
    if ext == ".pdf":
        out = _sh(["pdftotext", "-layout", src, "-"], timeout=180)
        text = out.stdout.decode("utf-8", "replace")
        if len(text.strip()) < 400:
            st["status"] = "failed"
            st["error"] = ("PDF 为扫描件或无法抽取文本（%d 字符），无法保真重建；"
                           "如需 OCR 请人工介入" % len(text.strip()))
            return
        _docx_from_text(text, conv, title=os.path.basename(src))
        ctx["manuscript"] = conv
        st["status"] = "partial"
        st["note"] = ("源稿为 PDF，已按文本流重建为 docx；原排版、图片与公式无法自动保留，"
                      "属于有损重建，保真度以文本单元为基线")
        ctx["converted_from"] = src
        return
    st["status"] = "failed"
    st["error"] = "不支持的稿件格式: %s" % ext


@_stage("adapt")
def s_adapt(ctx, st):
    import adapt_docx
    out = os.path.join(ctx["outdir"], "manuscript_adapted.docx")
    changes = os.path.join(ctx["work"], "changes.json")
    adapt_docx.main([ctx["manuscript"], "--spec", ctx["spec"], "--out", out,
                     "--changelog", changes])
    ctx["adapted"] = out
    st["adapted"] = out


def _fidelity_base(ctx):
    """Baseline for unit-level comparison: the original docx when available,
    otherwise the converted docx (lossy rebuild baseline, noted in report)."""
    base = ctx.get("converted_from")
    if base and base.lower().endswith(".docx") and os.path.exists(base):
        return base
    return ctx["manuscript"]


@_stage("fidelity")
def s_fidelity(ctx, st):
    import fidelity_check
    base = _fidelity_base(ctx)
    st["baseline"] = base
    fidelity_check.main([base, ctx["adapted"],
                         "--report", os.path.join(ctx["work"], "fidelity.md"),
                         "--json", os.path.join(ctx["work"], "fidelity.json")])
    verdict = json.load(open(os.path.join(ctx["work"], "fidelity.json"),
                             encoding="utf-8")).get("verdict")
    st["verdict"] = verdict
    if verdict == "FAIL":
        st["status"] = "failed"


@_stage("compliance")
def s_compliance(ctx, st):
    import compliance_check
    compliance_check.main([ctx["adapted"], "--spec", ctx["spec"],
                           "--report", os.path.join(ctx["work"], "compliance.md"),
                           "--json", os.path.join(ctx["work"], "compliance.json")])
    summary = json.load(open(os.path.join(ctx["work"], "compliance.json"),
                             encoding="utf-8")).get("summary", {})
    st["summary"] = summary


@_stage("render")
def s_render(ctx, st):
    import render_preview
    spec = json.load(open(ctx["spec"], encoding="utf-8"))
    want_toc = (spec.get("toc") or {}).get("required") and not ctx.get("no_toc")
    if want_toc:
        r = render_preview.toc_insert(ctx["adapted"])
        st["toc_insert"] = r
    render_preview.cmd_render(type("A", (), {"docx": ctx["adapted"],
                                             "outdir": ctx["outdir"], "pages": 6})())
    rr = json.load(open(os.path.join(ctx["outdir"], "render_report.json"),
                        encoding="utf-8"))
    st["render_status"] = rr.get("status")
    if rr.get("status") != "success":
        st["status"] = "partial"
        st["error"] = rr.get("error", "render failed")
        return
    if want_toc:
        r2 = render_preview.toc_fill(ctx["adapted"], rr["pdf"])
        st["toc_fill"] = r2
        if r2.get("ok"):
            render_preview.cmd_render(type("A", (), {"docx": ctx["adapted"],
                                                     "outdir": ctx["outdir"],
                                                     "pages": 6})())
            rr = json.load(open(os.path.join(ctx["outdir"], "render_report.json"),
                                encoding="utf-8"))
            st["render_status"] = rr.get("status")
            # refresh verification reports so they describe the FINAL file
            import fidelity_check, compliance_check
            base = _fidelity_base(ctx)
            fidelity_check.main([base, ctx["adapted"],
                                 "--report", os.path.join(ctx["work"], "fidelity.md"),
                                 "--json", os.path.join(ctx["work"], "fidelity.json")])
            compliance_check.main([ctx["adapted"], "--spec", ctx["spec"],
                                   "--report", os.path.join(ctx["work"], "compliance.md"),
                                   "--json", os.path.join(ctx["work"], "compliance.json")])
    st["page_size"] = rr.get("page_size")
    st["fonts_embedded"] = rr.get("all_fonts_embedded")


@_stage("result")
def s_result(ctx, st):
    import build_result
    argv = ["--plan", os.path.join(ctx["work"], "plan.json"),
            "--work", ctx["work"], "--outdir", ctx["outdir"]]
    if ctx.get("adapted"):
        argv += ["--adapted", ctx["adapted"]]
    # C6: direction.json contents flow into the existing uncertainty.notes
    # (no new result.json keys — contract keys/structure unchanged)
    if ctx.get("direction"):
        note = "direction.json: %s" % json.dumps(
            {k: v for k, v in ctx["direction"].items() if not k.startswith("_")},
            ensure_ascii=False)
        argv += ["--extra-uncertainty-note", note]
    build_result.main(argv)
    st["result"] = os.path.join(ctx["outdir"], "result.json")


ALL = ["inspect", "measure", "spec", "convert_source", "adapt",
       "fidelity", "compliance", "render", "result"]


def _load_direction(work):
    """Read the skill's direction.json (cross-topic convention) if present.

    The file lives next to SKILL.md, one level above scripts/.  It is real
    metadata: its contents are recorded into the result (never a decoration).
    """
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.path.join(here, "..", "direction.json"),
                 os.path.join(here, "direction.json"),
                 "/skills/weekly-skill/direction.json"):
        try:
            with open(cand, encoding="utf-8") as f:
                d = json.load(f)
            d["_path"] = os.path.abspath(cand)
            return d
        except Exception:  # noqa: BLE001
            continue
    return None


def _emergency_result(outdir, case_id=None, status="failed", note=""):
    """Minimal legal result.json written BEFORE anything can crash (§4-4).

    Uses only inline data so it survives import/path failures of the pipeline
    itself.  s_result overwrites it with the full record on success.
    """
    try:
        os.makedirs(outdir, exist_ok=True)
        payload = {
            "case_id": case_id,
            "status": status,
            "deliverables": [],
            "output_contract_filled": {},
            "verification": {},
            "sources": [],
            "changes": [],
            "uncertainty": {"notes": [note] if note else []},
            "limits": [note or "流水线在初始化阶段即中断；详见 stage_*.json 与运行日志"],
            "stages": {},
        }
        with open(os.path.join(outdir, "result.json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:  # noqa: BLE001
        pass  # nothing more we can do; honest failure is the log itself


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--task", default="/input/task.md")
    ap.add_argument("--work", default=WORK)
    ap.add_argument("--outdir", default=OUTDIR)
    ap.add_argument("--manuscript", default=None)
    ap.add_argument("--template", default=None)
    ap.add_argument("--no-toc", action="store_true")
    ap.add_argument("--stages", default=None, help="comma list, default: all")
    args = ap.parse_args(argv)

    os.makedirs(args.work, exist_ok=True)
    os.makedirs(args.outdir, exist_ok=True)
    # C2: write a legal result.json BEFORE any stage can fail (early honest stub)
    _emergency_result(args.outdir, note="pipeline 初始化完成，阶段执行中（应急占位，完成后被正式结果覆盖）")
    ctx = {"case": args.case, "task": args.task, "work": args.work,
           "outdir": args.outdir, "manuscript": args.manuscript,
           "template": args.template, "no_toc": args.no_toc,
           "plan": {}, "spec": None, "adapted": None, "measured": None}
    ctx["direction"] = _load_direction(args.work)

    stages = ALL if not args.stages else args.stages.split(",")
    registry = {
        "inspect": s_inspect, "measure": s_measure, "spec": s_spec,
        "convert_source": s_convert, "adapt": s_adapt, "fidelity": s_fidelity,
        "compliance": s_compliance, "render": s_render, "result": s_result,
    }
    try:
        for name in stages:
            fn = registry.get(name.strip())
            if not fn:
                print("[stage:%s] unknown, skipped" % name)
                continue
            st = fn(ctx)
            if name == "adapt" and st["status"] == "failed":
                print("adapt 失败，后续依赖阶段跳过；仍尝试生成结果文件")
                registry["result"](ctx)
                break
    except Exception as e:  # noqa: BLE001  (C1: top-level crash guard)
        import traceback
        err = "%s: %s" % (type(e).__name__, e)
        with open(os.path.join(args.work, "stage_fatal.json"), "w",
                  encoding="utf-8") as f:
            json.dump({"stage": "fatal", "status": "failed", "error": err,
                       "traceback": traceback.format_exc()[-2000:]}, f,
                      ensure_ascii=False, indent=2)
        print("[stage:fatal] failed: %s" % err)
        try:
            registry["result"](ctx)
        except Exception:  # noqa: BLE001
            _emergency_result(args.outdir, status="failed",
                              note="流水线顶层异常：%s（stage_fatal.json 有堆栈）" % err)


if __name__ == "__main__":
    main()
