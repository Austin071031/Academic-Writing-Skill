#!/usr/bin/env python3
"""assemble_result.py — 汇总 work/ 产物与可编辑工程，生成 /app/output/result.json。

用法:
  python3 assemble_result.py [--work /app/work] [--out /app/output]
      [--case /input/case.json] --skill "name vX.Y.Z"
      [--status success|partial|failed] [--deliver /app/work/project]
      [--field k=json ...]

行为:
  1. 把 work/ 下已知产物复制到 /app/output/reports/（若 Agent 尚未复制）。
  2. --deliver 指向的工程目录复制为 /app/output/latex_project/（剔除编译中间文件，
     保留 .tex/.bib/.sty/.cls/图片等可编辑源码与最终 PDF 预览）。
  3. 读取 case.json 的 output_contract，保证 result.json 顶层包含全部契约字段 + case_id。
  4. 自动汇总 evidence_map/change_log/uncertainty/manual_confirmations/exceptions/stats。
"""
import argparse, json, os, shutil, sys, datetime

REPORTS = ["build_report.json", "log_report.json", "source_check.json",
           "inspection.json", "fix_log.json", "instruction_checklist.json",
           "instruction_report.json", "math_report.json",
           "table_report.json", "cite_report.json", "template_report.json",
           "build_manifest.json", "reproducibility_report.md",
           "evidence_map.json", "change_log.json", "uncertainty.json",
           "manual_confirmations.json", "exceptions.json", "stats.json",
           "task_copy.md", "fix_summary.md", "audit_summary.md",
           "BUILD_MANIFEST.md"]
AUX_EXT = {".aux", ".out", ".toc", ".lof", ".lot", ".fls", ".fdb_latexmk",
           ".blg", ".bcf", ".nav", ".snm", ".vrb", ".xdv", ".ent", ".mw",
           ".run.xml", ".synctex.gz", "-blx.bib"}


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def copy_project(src, dst):
    n = 0
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
        rel = os.path.relpath(dirpath, src)
        for fn in filenames:
            if fn.startswith(".") or fn.endswith(tuple(AUX_EXT)):
                continue
            sp = os.path.join(dirpath, fn)
            dp = os.path.join(dst, rel, fn) if rel != "." else os.path.join(dst, fn)
            os.makedirs(os.path.dirname(dp), exist_ok=True)
            shutil.copyfile(sp, dp)
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--skill", required=True)
    ap.add_argument("--status", default="partial", choices=["success", "partial", "failed"])
    ap.add_argument("--deliver", default=None, help="可编辑工程目录（默认 work/project 若存在）")
    ap.add_argument("--field", action="append", default=[], help="附加字段 k=json 或 k=str")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    reports_dir = os.path.join(args.out, "reports")
    os.makedirs(reports_dir, exist_ok=True)

    copied = []
    for name in REPORTS:
        sp = os.path.join(args.work, name)
        if os.path.exists(sp):
            dp = os.path.join(reports_dir, name)
            shutil.copyfile(sp, dp)
            copied.append(name)

    build = load_json(os.path.join(args.work, "build_report.json"), {}) or {}
    pdf_copied = None
    if build.get("pdf") and os.path.exists(build["pdf"]):
        pdf_copied = os.path.join(args.out, "preview.pdf")
        shutil.copyfile(build["pdf"], pdf_copied)

    deliver = args.deliver
    if not deliver and os.path.isdir(os.path.join(args.work, "project")):
        deliver = os.path.join(args.work, "project")
    nfiles = 0
    if deliver and os.path.isdir(deliver):
        nfiles = copy_project(deliver, os.path.join(args.out, "latex_project"))
        # 若工程内有最终 PDF 且 preview 未生成，用工程 PDF
        if not pdf_copied:
            for dirpath, _, filenames in os.walk(deliver):
                for fn in filenames:
                    if fn.endswith(".pdf"):
                        pdf_copied = os.path.join(args.out, "preview.pdf")
                        shutil.copyfile(os.path.join(dirpath, fn), pdf_copied)
                        break
                if pdf_copied:
                    break

    insp = load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    evidence = load_json(os.path.join(args.work, "evidence_map.json"), []) or []
    changes = load_json(os.path.join(args.work, "change_log.json"), []) or []
    uncertainty = load_json(os.path.join(args.work, "uncertainty.json"), []) or []
    manual = load_json(os.path.join(args.work, "manual_confirmations.json"), []) or []
    exceptions = load_json(os.path.join(args.work, "exceptions.json"), []) or []
    stats = load_json(os.path.join(args.work, "stats.json"), {}) or {}
    fixes = load_json(os.path.join(args.work, "fix_log.json"), []) or []
    if fixes and not changes:
        changes = fixes

    outputs = {"reports": "reports/", }
    if nfiles:
        outputs["latex_project"] = f"latex_project/（{nfiles} 个可编辑源文件）"
    if pdf_copied:
        outputs["pdf_preview"] = "preview.pdf"

    result = {
        "case_id": insp.get("case_id") or "unknown",
        "status": args.status,
        "skill": args.skill,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "task_summary": (insp.get("task_head") or "")[:400] or None,
        "outputs": outputs,
        "build": {"engine": build.get("engine"), "success": build.get("success"),
                  "converged": build.get("converged"),
                  "passes": len(build.get("passes", [])),
                  "last_pass": (build.get("passes") or [{}])[-1],
                  "exception": build.get("exception")},
        "evidence_map": evidence,
        "change_log": changes,
        "uncertainty": uncertainty,
        "manual_confirmations": manual,
        "exceptions": exceptions + (insp.get("exceptions") or []),
        "stats": stats,
        "sources": {"reports_dir": "reports/", "copied_reports": copied,
                    "build_log": (build.get("log") or None)},
    }

    contract_names = []
    if os.path.exists(args.case):
        case = load_json(args.case, {}) or {}
        result["case_id"] = result["case_id"] if result["case_id"] != "unknown" \
            else (case.get("case_id") or case.get("id") or "unknown")
        oc = case.get("output_contract") or case.get("outputContract") or {}
        if isinstance(oc, dict):
            contract_names = list(oc.keys())
        elif isinstance(oc, list):
            contract_names = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in oc]
    alias = {"result": "outputs", "deliverables": "outputs", "main_output": "outputs",
             "report": "outputs", "evidence": "evidence_map", "sources": "sources",
             "changes": "change_log", "uncertainties": "uncertainty",
             "verification": "build", "findings": "outputs", "artifacts": "outputs",
             "manuscript": "outputs", "tex": "outputs", "latex": "outputs"}
    for name in contract_names:
        if name in result and result[name]:
            continue
        tgt = alias.get(name)
        result[name] = result.get(tgt) if tgt else result.get("outputs")
    if contract_names:
        result["output_contract_fields"] = contract_names

    for kv in args.field:
        k, _, v = kv.partition("=")
        try:
            result[k] = json.loads(v)
        except Exception:
            result[k] = v

    with open(os.path.join(args.out, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[assemble] status={args.status} 工程文件={nfiles} 报告={len(copied)} "
          f"PDF={'有' if pdf_copied else '无'} 契约字段={contract_names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
