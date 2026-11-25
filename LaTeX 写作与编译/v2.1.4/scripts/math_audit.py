#!/usr/bin/env python3
r"""v2_math_audit.py — 数学公式专项审查：环境、编号引用、符号与单位、算子正体。

用法:
  python3 v2_math_audit.py [--project /app/work/project] [--main main.tex] [--work /app/work]

检查项（每条 finding 含 file:line、证据片段、建议改法；脚本只诊断不擅自改写）:
  M1  $$...$$ 显示数学（建议 \[...\]）
  M2  eqnarray/eqnarray* 环境（建议 align，且对其 \&= 对齐风险给出说明）
  M3  公式编号与 \eqref 引用：带 \label 的公式从未被引用（info）/
      \eqref 指向非公式标签（疑似串号）
  M4  斜体多字母下标 x_{max}（建议 x_{\mathrm{max}}）
  M5  数学模式中的物理单位（建议 siunitx 的 \si/\unit，正文单位不正体）
  M6  未加反斜杠的算子名 sin( cos( log( lim 等（建议 \sin 等，避免斜体连乘歧义）
  M7  \left 与 \right 数量不配对的行
  M8  编号/不编号公式环境混用统计（equation vs equation* 等，供任务比对）
输出 work/math_report.json + 控制台摘要。仅标准库。
"""
import argparse, json, os, re, sys

MATH_ENVS = ("equation", "equation*", "align", "align*", "gather", "gather*",
             "multline", "multline*", "eqnarray", "eqnarray*", "alignat", "flalign")
OPERATORS = ("sin", "cos", "tan", "cot", "sec", "csc", "log", "ln", "exp",
             "max", "min", "lim", "sup", "inf", "det", "arg", "deg", "dim", "ker")
UNITS = ("m", "s", "kg", "g", "Hz", "K", "mol", "V", "W", "Pa", "J", "N",
         "A", "eV", "MeV", "GeV", "nm", "um", "mm", "cm", "km", "ms", "MPa", "kPa")


def strip_comments(line):
    out, i = [], 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            out.append(line[i:i + 2]); i += 2; continue
        if c == "%":
            break
        out.append(c); i += 1
    return "".join(out)


def tex_files(project, main_rel):
    seen, order = set(), []
    def visit(rel, d):
        if d > 6 or rel in seen:
            return
        seen.add(rel)
        p = os.path.join(project, rel)
        if not os.path.exists(p):
            return
        order.append(rel)
        try:
            txt = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            return
        for m in re.finditer(r"\\(?:input|include)\{([^}]+)\}", txt):
            sub = m.group(1)
            if not sub.endswith(".tex"):
                sub += ".tex"
            visit(os.path.normpath(os.path.join(os.path.dirname(rel), sub)), d + 1)
    visit(main_rel, 0)
    return order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--main", default=None)
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    insp = {}
    try:
        insp = json.load(open(os.path.join(args.work, "inspection.json"), encoding="utf-8"))
    except Exception:
        pass
    project = args.project or insp.get("staged_project_dir") or "/app/work/project"
    main_rel = args.main or (insp.get("tex_project") or {}).get("main") or "main.tex"

    findings = []
    eq_labels = {}        # label -> env
    all_labels_env = {}
    eqref_used = set()
    env_count = {}
    inline_math_lines = []

    for rel in tex_files(project, main_rel):
        try:
            lines = open(os.path.join(project, rel), encoding="utf-8",
                         errors="replace").read().splitlines()
        except OSError:
            continue
        cur_env = None
        disp_open = False
        for ln, raw in enumerate(lines, 1):
            line = strip_comments(raw)
            # 跟踪 \[...\] 与 $$...$$ 显示数学，使其中的 \label 记为公式标签
            if "\\[" in line:
                cur_env = cur_env or "display"
                disp_open = True
            if "$$" in line:
                if not disp_open:
                    cur_env = cur_env or "display"
                    disp_open = True
                elif cur_env == "display":
                    cur_env = None
                    disp_open = False
            if "\\]" in line and cur_env == "display":
                cur_env = None
                disp_open = False
            if "$$" in line:
                findings.append({"id": "M1", "severity": "warn", "file": rel, "line": ln,
                                 "evidence": raw.strip()[:120],
                                 "suggestion": "$$...$$ 为 plain TeX 写法，改用 \\[...\\] "
                                               "以获得正确的间距与编号行为"})
            for env in MATH_ENVS:
                if re.search(r"\\begin\{" + re.escape(env) + r"\}", line):
                    cur_env = env
                    env_count[env] = env_count.get(env, 0) + 1
                    if env.startswith("eqnarray"):
                        findings.append({"id": "M2", "severity": "warn", "file": rel,
                                         "line": ln, "evidence": raw.strip()[:120],
                                         "suggestion": "eqnarray 间距错误且与 amsmath 不兼容，"
                                                       "改用 align（注意把 & = & 调整为 &=）"})
                if re.search(r"\\end\{" + re.escape(env) + r"\}", line):
                    cur_env = None
            lm = re.search(r"\\label\{([^}]+)\}", line)
            if lm:
                all_labels_env[lm.group(1)] = cur_env or "text"
                if cur_env and not cur_env.endswith("*") and \
                   (cur_env in MATH_ENVS or cur_env == "display"):
                    eq_labels[lm.group(1)] = {"file": rel, "line": ln, "env": cur_env}
            for m in re.finditer(r"\\eqref\{([^}]+)\}", line):
                eqref_used.update(k.strip() for k in m.group(1).split(","))
            # M4 斜体多字母下标
            for m in re.finditer(r"_\{([A-Za-z]{2,})\}", line):
                word = m.group(1)
                if word not in ("mathrm", "text", "mathit") and not word.startswith("math"):
                    findings.append({"id": "M4", "severity": "info", "file": rel, "line": ln,
                                     "evidence": raw.strip()[:120],
                                     "suggestion": f"下标 _{{{word}}} 将以斜体连乘排版；若为文字含义"
                                                   f"改用 _{{\\mathrm{{{word}}}}}"})
                    break
            # M5 数学中单位
            if "$" in line or cur_env:
                um = re.search(r"\$[^$]*\d\s*\\?(?:,\s*)?(" + "|".join(UNITS) + r")\b[^$]*\$", line)
                if um and "\\si" not in line and "\\unit" not in line:
                    findings.append({"id": "M5", "severity": "info", "file": rel, "line": ln,
                                     "evidence": raw.strip()[:120],
                                     "suggestion": "数学模式中的单位将排成斜体且间距错误；"
                                                   "用 siunitx：\\qty{10}{\\m} 或 \\SI{10}{\\m}"})
            # M6 裸算子
            for op in OPERATORS:
                if re.search(r"(?<![\\A-Za-z])" + op + r"\s*[\( ]", line) and \
                   ("$" in line or cur_env) and "\\" + op not in line:
                    findings.append({"id": "M6", "severity": "warn", "file": rel, "line": ln,
                                     "evidence": raw.strip()[:120],
                                     "suggestion": f"算子 {op} 未加反斜杠，将以斜体字母连乘排版；"
                                                   f"改用 \\{op}（必要时 \\operatorname）"})
                    break
            # M7 \left \right 配对
            nl = line.count("\\left")
            nr = line.count("\\right")
            if nl != nr and cur_env is None and "$" not in line:
                pass
            elif nl != nr:
                findings.append({"id": "M7", "severity": "info", "file": rel, "line": ln,
                                 "evidence": raw.strip()[:120],
                                 "suggestion": f"\\left({nl}) 与 \\right({nr}) 数量不配对；"
                                               "跨行配对用 \\right. / \\left. 占位"})
            if "$" in line:
                inline_math_lines.append((rel, ln))

    # M3 公式标签引用核查
    for key, info in eq_labels.items():
        if key not in eqref_used:
            findings.append({"id": "M3a", "severity": "info", "file": info["file"],
                             "line": info["line"],
                             "evidence": f"\\label{{{key}}} 于 {info['env']}",
                             "suggestion": "带编号的公式从未被 \\eqref 引用；若任务要求"
                                           "'只给被引用公式编号'，改用 * 环境或 \\notag"})
    for key in sorted(eqref_used):
        if key in all_labels_env and key not in eq_labels:
            findings.append({"id": "M3b", "severity": "warn", "file": None, "line": None,
                             "evidence": f"\\eqref{{{key}}} 指向 {all_labels_env[key]} 环境的标签",
                             "suggestion": "\\eqref 应用于公式标签；指向章节/图表标签疑似串号，"
                                           "改用 \\ref/\\autoref 或核对标签位置"})

    report = {
        "env_counts": env_count,
        "equation_labels": len(eq_labels),
        "eqref_marks": len(eqref_used),
        "findings": findings,
        "stats": {"findings": len(findings),
                  "warn": sum(1 for f in findings if f["severity"] == "warn"),
                  "info": sum(1 for f in findings if f["severity"] == "info")},
        "note": "脚本只诊断；所有改写由 Agent 判断后执行并记入 change_log。",
    }
    with open(os.path.join(args.work, "math_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[math_audit] 公式环境={env_count} 编号公式={len(eq_labels)} "
          f"\\eqref={len(eqref_used)} findings={len(findings)}")
    for f in findings[:15]:
        loc = f"{f['file']}:{f['line']}" if f.get("file") else "-"
        print(f"  [{f['id']}/{f['severity']}] {loc} {f['suggestion'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
