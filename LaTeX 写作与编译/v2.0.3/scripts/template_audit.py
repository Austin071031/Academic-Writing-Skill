#!/usr/bin/env python3
r"""v5_template_audit.py — 模板适配审查：必填元数据、宏包冲突、加载顺序、迁移差异。

用法:
  python3 v5_template_audit.py [--project /app/work/project] [--main main.tex]
                               [--template DIR_OR_FILE] [--work /app/work]

检查项:
  P1  模板/类必填元数据缺失（按 \documentclass 识别：IEEEtran/elsarticle/acmart/
      ctexart/article/report/book 及 --template 提供的 .cls 名称启发式）
  P2  已知宏包冲突对（natbib×biblatex、subfigure×subcaption、times×newtxtext、
      inputenc×xelatex 引擎、babel×polyglossia、algorithm2e×algorithmicx）
  P3  加载顺序违规：hyperref 未置宏包区末尾；cleveref 早于 hyperref
  P4  过时宏包/命令（epsfig、subfigure、psfig、\\bf/\\it/\\rm 声明式字体命令）
  P5  与 --template 的差异：模板已加载而稿件缺失的宏包、模板要求的文件结构
      （摘要/关键词环境、\bibliographystyle 规定值）
输出 work/template_report.json。仅标准库；所有判定给证据行。
"""
import argparse, json, os, re, sys

CLASS_REQUIREMENTS = {
    "IEEEtran": {"title": r"\\title\{", "author": r"\\author\{",
                 "abstract": r"\\begin\{abstract\}", "keywords": r"\\begin\{IEEEkeywords\}|\\keywords\{",
                 "maketitle": r"\\maketitle"},
    "elsarticle": {"title": r"\\title\{", "author": r"\\author", "affiliation": r"\\affiliation|\\address",
                   "abstract": r"\\begin\{abstract\}", "keywords": r"\\begin\{keyword\}",
                   "maketitle": r"\\maketitle"},
    "acmart": {"title": r"\\title\{", "author": r"\\author\{", "affiliation": r"\\affiliation",
               "email": r"\\email\{", "abstract": r"\\begin\{abstract\}",
               "keywords": r"\\keywords\{", "ccs": r"\\ccsdesc|\\begin\{CCSXML\}",
               "maketitle": r"\\maketitle"},
    "ctexart": {"title": r"\\title\{", "author": r"\\author\{", "maketitle": r"\\maketitle"},
    "article": {"title": r"\\title\{", "author": r"\\author\{", "maketitle": r"\\maketitle"},
    "report": {"title": r"\\title\{", "author": r"\\author\{", "maketitle": r"\\maketitle"},
    "book": {"title": r"\\title\{", "author": r"\\author\{", "maketitle": r"\\maketitle"},
}
CONFLICT_PAIRS = [
    ("natbib", "biblatex", "两种参考文献机制互斥，须按模板二选一"),
    ("subfigure", "subcaption", "subfigure 已过时且与 subcaption 冲突，保留 subcaption"),
    ("times", "newtxtext", "旧 times 与 newtxtext 字体方案叠加会冲突"),
    ("babel", "polyglossia", "babel 与 polyglossia 互斥（xelatex 用 polyglossia/ctex）"),
    ("algorithm2e", "algorithmicx", "两套算法排版体系混用易冲突，按模板选一套"),
]
DEPRECATED = [("epsfig", "改用 graphicx 的 \\includegraphics"),
              ("subfigure", "改用 subcaption"),
              ("psfig", "改用 graphicx"),
              ("times", "改用 newtxtext/newtxmath 或模板默认字体")]
OLD_FONT_CMDS = re.compile(r"(?<![\\a-zA-Z])\\(bf|it|rm|sc|sf|tt|cal)\s")


def preamble_of(txt):
    m = re.search(r"\\begin\{document\}", txt)
    return txt[:m.start()] if m else txt[:20000]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--main", default=None)
    ap.add_argument("--template", default=None)
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    insp = {}
    try:
        insp = json.load(open(os.path.join(args.work, "inspection.json"), encoding="utf-8"))
    except Exception:
        pass
    project = args.project or insp.get("staged_project_dir") or "/app/work/project"
    main_rel = args.main or (insp.get("tex_project") or {}).get("main") or "main.tex"
    try:
        txt = open(os.path.join(project, main_rel), encoding="utf-8", errors="replace").read()
    except OSError:
        print(f"[template_audit] 主文件不可读: {main_rel}")
        return 1

    findings = []
    cls = None
    m = re.search(r"\\documentclass(?:\[([^\]]*)\])?\{([^}]+)\}", txt)
    cls_opts = []
    if m:
        cls = m.group(2)
        cls_opts = [o.strip() for o in (m.group(1) or "").split(",") if o.strip()]
    pre = preamble_of(txt)
    body = txt

    pkg_order = []
    for pm in re.finditer(r"\\usepackage(?:\[([^\]]*)\])?\{([^}]+)\}", pre):
        for p in pm.group(2).split(","):
            p = p.strip()
            if p:
                pkg_order.append(p)
    pkgs = set(pkg_order)

    # P1 必填元数据
    req = CLASS_REQUIREMENTS.get(cls)
    if req:
        for field, pat in req.items():
            if not re.search(pat, body):
                findings.append({"id": "P1", "severity": "error", "item": field,
                                 "evidence": f"文档类 {cls} 要求 {field}，源码未检出（模式 {pat}）",
                                 "suggestion": f"按模板补 {field}；材料中无此信息时记 "
                                               "manual_confirmations，不得编造作者/单位"})
    else:
        findings.append({"id": "P1i", "severity": "info", "item": "documentclass",
                         "evidence": f"未识别的文档类 {cls}，未做必填项核对",
                         "suggestion": "若 --template 提供模板文件，按其注释/示例核对必填项"})

    # P2 冲突对
    for a, b, why in CONFLICT_PAIRS:
        if a in pkgs and b in pkgs:
            findings.append({"id": "P2", "severity": "error", "item": f"{a}×{b}",
                             "evidence": f"同时加载 {a} 与 {b}",
                             "suggestion": why})
    if "inputenc" in pkgs:
        eng = (insp.get("tex_project") or {}).get("engine")
        if eng in ("xelatex", "lualatex"):
            findings.append({"id": "P2b", "severity": "warn", "item": "inputenc",
                             "evidence": f"引擎 {eng} 下加载 inputenc 无效/有害",
                             "suggestion": "xelatex/lualatex 原生 UTF-8，移除 inputenc"})

    # P3 加载顺序
    if "hyperref" in pkg_order:
        after = pkg_order[pkg_order.index("hyperref") + 1:]
        bad = [p for p in after if p not in ("cleveref",)]
        if bad:
            findings.append({"id": "P3", "severity": "warn", "item": "hyperref",
                             "evidence": f"hyperref 之后仍加载: {', '.join(bad)}",
                             "suggestion": "hyperref 应最后加载（例外：cleveref 须在 hyperref 之后）"})
    if "cleveref" in pkg_order and "hyperref" in pkg_order and \
       pkg_order.index("cleveref") < pkg_order.index("hyperref"):
        findings.append({"id": "P3b", "severity": "error", "item": "cleveref",
                         "evidence": "cleveref 早于 hyperref 加载",
                         "suggestion": "cleveref 必须在 hyperref 之后加载，否则交叉引用失效"})

    # P4 过时项
    for dep, sug in DEPRECATED:
        if dep in pkgs:
            findings.append({"id": "P4", "severity": "warn", "item": dep,
                             "evidence": f"加载了过时宏包 {dep}", "suggestion": sug})
    for i, line in enumerate(txt.splitlines(), 1):
        if OLD_FONT_CMDS.search(line):
            findings.append({"id": "P4b", "severity": "info", "item": "font_cmd",
                             "evidence": f"{main_rel}:{i} {line.strip()[:80]}",
                             "suggestion": "{\\bf ...} 等声明式字体命令已过时，改用 \\textbf{...} 等"})
            break

    # P5 与模板差异
    tpl_diff = None
    if args.template:
        tpath = args.template
        tfiles = []
        if os.path.isdir(tpath):
            for dirpath, _, filenames in os.walk(tpath):
                tfiles.extend(os.path.join(dirpath, f) for f in filenames
                              if f.endswith((".tex", ".cls", ".sty")))
        elif os.path.isfile(tpath):
            tfiles = [tpath]
        tpl_pkgs, tpl_req = set(), []
        for tf in tfiles:
            try:
                ttxt = open(tf, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for pm in re.finditer(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}", ttxt):
                tpl_pkgs.update(x.strip() for x in pm.group(1).split(",") if x.strip())
            for bm in re.finditer(r"\\bibliographystyle\{([^}]+)\}", ttxt):
                tpl_req.append(("bibliographystyle", bm.group(1)))
        missing_pkgs = sorted(tpl_pkgs - pkgs)
        tpl_diff = {"template_files": [os.path.basename(t) for t in tfiles],
                    "template_packages": sorted(tpl_pkgs),
                    "missing_in_manuscript": missing_pkgs}
        for p in missing_pkgs:
            findings.append({"id": "P5", "severity": "info", "item": p,
                             "evidence": f"模板加载 {p} 而稿件未加载",
                             "suggestion": "核对模板说明后按需补载；不要盲目全量复制模板导言区"})
        for kind, val in tpl_req:
            if kind == "bibliographystyle" and f"\\bibliographystyle{{{val}}}" not in txt:
                findings.append({"id": "P5b", "severity": "warn", "item": "bibliographystyle",
                                 "evidence": f"模板规定 \\bibliographystyle{{{val}}}",
                                 "suggestion": f"按模板设置参考文献样式 {val}"})

    report = {"documentclass": cls, "class_options": cls_opts,
              "packages_in_order": pkg_order, "findings": findings,
              "template_diff": tpl_diff,
              "stats": {"findings": len(findings),
                        "errors": sum(1 for f in findings if f["severity"] == "error")}}
    json.dump(report, open(os.path.join(args.work, "template_report.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[template_audit] 类={cls} 宏包={len(pkg_order)} findings={len(findings)}")
    for f in findings[:15]:
        print(f"  [{f['id']}/{f['severity']}] {f['item']}: {f['evidence'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
