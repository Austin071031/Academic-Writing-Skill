#!/usr/bin/env python3
"""tex_build.py — 可控的 LaTeX 多轮编译封装：探测引擎、按需跑 bib、收敛判断、日志归档。

用法:
  python3 tex_build.py [--project /app/work/project] [--main main.tex]
      [--engine auto|pdflatex|xelatex|lualatex] [--bib auto|bibtex|biber|none]
      [--passes 3] [--until-converge] [--timeout 180]
      [--work /app/work] [--tag baseline]

输出 work/build_report.json（含每次运行的命令、返回码、错误/警告计数、PDF 路径）。
若系统没有任何 TeX 引擎，如实记录 success=false 与 exception，不伪造编译结果。
仅标准库；每个子进程独立超时，stdin 重定向到 DEVNULL 防止交互挂起。
"""
import argparse, json, os, re, shutil, subprocess, sys, time, datetime

ENGINES = {"pdflatex": "pdflatex", "xelatex": "xelatex", "lualatex": "lualatex"}
AUX_EXT = (".aux", ".out", ".toc", ".lof", ".lot", ".fls", ".fdb_latexmk",
           ".synctex.gz", ".bbl", ".blg", ".bcf", ".run.xml", ".nav", ".snm", ".vrb")


def which(cmd):
    return shutil.which(cmd) is not None


def has_cjk(text):
    return bool(re.search(r"[一-鿿぀-ヿ가-힯]", text))


def pick_engine(requested, project_dir, main_rel):
    if requested != "auto":
        return requested if which(ENGINES.get(requested, requested)) else None
    hints = ""
    try:
        with open(os.path.join(project_dir, main_rel), encoding="utf-8", errors="replace") as f:
            hints = f.read(60000)
    except OSError:
        pass
    if re.search(r"\\usepackage(\[[^\]]*\])?\{(ctex|xeCJK|fontspec|unicode-math)", hints) or \
       re.search(r"\\documentclass(\[[^\]]*\])?\{ctex", hints) or has_cjk(hints):
        order = ["xelatex", "lualatex", "pdflatex"]
    else:
        order = ["pdflatex", "xelatex", "lualatex"]
    for e in order:
        if which(e):
            return e
    return None


def count_log(log_path):
    errors, warnings, overfull = 0, 0, 0
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            txt = f.read()
        errors = len(re.findall(r"^! ", txt, flags=re.M)) + \
            len(re.findall(r"^[^\n]*\.(?:tex|sty|cls):\d+: ", txt, flags=re.M))
        warnings = len(re.findall(r"LaTeX Warning:", txt))
        overfull = len(re.findall(r"Overfull \\hbox", txt))
    except OSError:
        pass
    return errors, warnings, overfull


def run_one(cmd, cwd, timeout):
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, timeout=timeout,
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return p.returncode, time.time() - t0, False
    except subprocess.TimeoutExpired:
        return -9, time.time() - t0, True
    except OSError as e:
        return -1, time.time() - t0, False


def needs_rerun(log_path):
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            tail = f.read()[-20000:]
    except OSError:
        return False
    return bool(re.search(r"Rerun to get|Label\(s\) may have changed|"
                          r"There were undefined references|Please rerun", tail))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="/app/work/project")
    ap.add_argument("--main", default=None, help="主文件相对路径；缺省读 inspection.json")
    ap.add_argument("--engine", default="auto")
    ap.add_argument("--bib", default="auto")
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--until-converge", action="store_true")
    ap.add_argument("--timeout", type=int, default=180, help="单次编译秒数上限")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--tag", default="build")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    report = {"tag": args.tag, "project": args.project, "success": False,
              "engine": None, "commands": [], "passes": [], "pdf": None, "log": None,
              "exception": None, "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}

    main_rel = args.main
    if not main_rel:
        try:
            with open(os.path.join(args.work, "inspection.json"), encoding="utf-8") as f:
                main_rel = json.load(f)["tex_project"]["main"]
        except Exception:
            main_rel = None
    if not main_rel:
        main_rel = "main.tex" if os.path.exists(os.path.join(args.project, "main.tex")) else None
    if not main_rel or not os.path.exists(os.path.join(args.project, main_rel)):
        report["exception"] = f"主文件不存在: {main_rel}"
        with open(os.path.join(args.work, "build_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"[tex_build] 失败: {report['exception']}")
        return 1

    engine = pick_engine(args.engine, args.project, main_rel)
    if not engine:
        report["exception"] = "未找到任何可用 TeX 引擎（pdflatex/xelatex/lualatex）"
        with open(os.path.join(args.work, "build_report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"[tex_build] 失败: {report['exception']}")
        return 1
    report["engine"] = engine

    base = os.path.splitext(os.path.basename(main_rel))[0]
    main_dir = os.path.dirname(os.path.join(args.project, main_rel)) or args.project
    main_base = os.path.basename(main_rel)

    has_bib = False
    bib_tool = None
    if args.bib != "none":
        try:
            with open(os.path.join(args.project, main_rel), encoding="utf-8", errors="replace") as f:
                txt = f.read()
            uses_biblatex = "\\usepackage" in txt and "biblatex" in txt
            uses_bibtex = "\\bibliography" in txt or "\\bibliographystyle" in txt
            if args.bib == "biber" or (args.bib == "auto" and uses_biblatex):
                bib_tool = "biber" if which("biber") else None
                has_bib = uses_biblatex or args.bib == "biber"
            elif args.bib == "bibtex" or (args.bib == "auto" and uses_bibtex):
                bib_tool = "bibtex" if which("bibtex") else None
                has_bib = uses_bibtex or args.bib == "bibtex"
        except OSError:
            pass

    tex_flags = ["-interaction=nonstopmode", "-file-line-error", "-recorder", main_base]
    log_path = os.path.join(main_dir, base + ".log")
    pdf_path = os.path.join(main_dir, base + ".pdf")
    if os.path.exists(pdf_path):
        try:
            os.remove(pdf_path)
        except OSError:
            pass

    max_passes = max(args.passes, 4) if args.until_converge else args.passes
    bib_done = False
    for i in range(1, max_passes + 1):
        cmd = [engine] + tex_flags
        rc, dur, timed_out = run_one(cmd, main_dir, args.timeout)
        report["commands"].append(" ".join(cmd))
        e, w, o = count_log(log_path)
        report["passes"].append({"pass": i, "rc": rc, "seconds": round(dur, 2),
                                 "timed_out": timed_out, "errors": e, "warnings": w,
                                 "overfull_hbox": o})
        if timed_out:
            report["exception"] = f"第 {i} 轮编译超时（>{args.timeout}s），疑似交互挂起或死循环"
            break
        if has_bib and bib_tool and not bib_done and i == 1:
            bcmd = [bib_tool, base]
            brc, bdur, btout = run_one(bcmd, main_dir, min(args.timeout, 120))
            report["commands"].append(" ".join(bcmd))
            report["passes"].append({"pass": f"bib-{bib_tool}", "rc": brc,
                                     "seconds": round(bdur, 2), "timed_out": btout})
            bib_done = True
        if i >= 2 and args.until_converge and not needs_rerun(log_path):
            break
        if i >= args.passes and not args.until_converge:
            break

    if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0:
        dst_pdf = os.path.join(args.work, f"build_{args.tag}.pdf")
        shutil.copyfile(pdf_path, dst_pdf)
        report["pdf"] = dst_pdf
    if os.path.exists(log_path):
        dst_log = os.path.join(args.work, f"build_{args.tag}.log")
        shutil.copyfile(log_path, dst_log)
        report["log"] = dst_log

    last = report["passes"][-1] if report["passes"] else {}
    report["success"] = bool(report["pdf"]) and last.get("errors", 1) == 0 \
        and not last.get("timed_out")
    report["converged"] = (not needs_rerun(log_path)) if os.path.exists(log_path) else False

    with open(os.path.join(args.work, "build_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[tex_build] tag={args.tag} engine={engine} 轮次={len(report['passes'])} "
          f"success={report['success']} converged={report['converged']} "
          f"末轮错误={last.get('errors')} 警告={last.get('warnings')} overfull={last.get('overfull_hbox')}")
    if report["exception"]:
        print(f"[tex_build] 异常: {report['exception']}")
    return 0 if report["success"] else 2


if __name__ == "__main__":
    sys.exit(main())
