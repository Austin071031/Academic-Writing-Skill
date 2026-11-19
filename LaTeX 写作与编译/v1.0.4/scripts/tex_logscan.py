#!/usr/bin/env python3
"""tex_logscan.py — 解析 LaTeX 编译日志：错误分类、file:line 定位、级联根因归并。

用法:
  python3 tex_logscan.py [--log /app/work/build_build.log] [--work /app/work] [--top 15]

输出 work/log_report.json:
  errors[{file,line,message,category,likely_package,cascade}],
  warnings[{message,kind,line}], overfull[{points,at}],
  summary{...}, root_cause_hypothesis, first_error
分类体系见 references/error_taxonomy.md（各版本附带）。
仅标准库；兼容 -file-line-error 与经典 "! 错误 / l.NN" 两种格式。
"""
import argparse, json, os, re, sys

FILE_LINE_RE = re.compile(r"^(?P<file>[^\s()]+\.(?:tex|sty|cls|ltx|dtx|bib|bst|clo)):(?P<line>\d+):\s*(?P<msg>.*)$")
BANG_RE = re.compile(r"^!\s*(?P<msg>.*)$")
LNN_RE = re.compile(r"^l\.(?P<line>\d+)\s*(?P<ctx>.*)$")
PKG_ERR_RE = re.compile(r"^! Package (?P<pkg>\S+) Error:\s*(?P<msg>.*)$")
CLS_ERR_RE = re.compile(r"^! Class (?P<cls>\S+) Error:\s*(?P<msg>.*)$")
WARN_RE = re.compile(r"(?:LaTeX|Package (?P<pkg>\S+)) Warning:\s*(?P<msg>.*?)(?: on input line (?P<line>\d+))?\.?\s*$")
OVERFULL_RE = re.compile(r"Overfull \\hbox \((?P<pt>[\d.]+)pt too wide\)(?P<rest>.*)")
UNDEF_CS_RE = re.compile(r"Undefined control sequence")
FILE_NOT_FOUND_RE = re.compile(r"File [`'](?P<f>[^']+)' not found")
UNDEF_CMD_RE = re.compile(r"^\\[A-Za-z@]+")

CMD_PACKAGE = {
    "toprule": "booktabs", "midrule": "booktabs", "bottomrule": "booktabs",
    "cmidrule": "booktabs", "includegraphics": "graphicx", "SI": "siunitx",
    "si": "siunitx", "num": "siunitx", "unit": "siunitx", "qty": "siunitx",
    "ang": "siunitx", "mathbb": "amssymb", "mathfrak": "amssymb",
    "dfrac": "amsmath", "cfrac": "amsmath", "operatorname": "amsmath",
    "eqref": "amsmath", "text": "amsmath", "boldsymbol": "amsbsy(amsmath)",
    "url": "hyperref/url", "href": "hyperref", "autoref": "hyperref",
    "textcolor": "xcolor", "rowcolor": "xcolor(colortbl)", "multirow": "multirow",
    "subcaption": "subcaption", "cref": "cleveref", "Cref": "cleveref",
    "todo": "todonotes", "citep": "natbib", "citet": "natbib",
    "lstinline": "listings", "ce": "mhchem", "bm": "bm", "sout": "ulem",
    "nicefrac": "nicefrac", "captionof": "caption", "adjustbox": "adjustbox",
    "algorithm": "algorithm(float)", "procedure": "float?",
}

MISSING_PKG_HINT = re.compile(r"[`'](?P<name>[^']+\.(?:sty|cls))' not found")


def classify(msg):
    m = msg.lower()
    if "unicode character" in m and ("not set up" in m or "u+" in m):
        return "unicode_char_pdflatex"
    if "undefined control sequence" in m:
        return "undefined_control_sequence"
    if "file" in m and "not found" in m:
        return "missing_file"
    if "missing $" in m or "math mode" in m:
        return "math_mode"
    if "undefined" in m and "citation" in m:
        return "undefined_citation"
    if "undefined" in m and "reference" in m:
        return "undefined_reference"
    if "multiply" in m and "defined" in m:
        return "multiply_defined"
    if "runaway argument" in m or "paragraph ended" in m:
        return "runaway_argument"
    if "missing \\begin{document}" in m:
        return "missing_begin_document"
    if "no \\author" in m:
        return "missing_metadata"
    if "font" in m and ("not found" in m or "cannot" in m):
        return "font_missing"
    if "option clash" in m:
        return "option_clash"
    if "environment" in m and "undefined" in m:
        return "undefined_environment"
    if "extra }" in m or "missing }" in m or "too many }" in m:
        return "brace_mismatch"
    if "misplaced \\noalign" in m or "misplaced \\omit" in m:
        return "table_rule_misplaced"
    if "extra alignment tab" in m:
        return "table_column_mismatch"
    if "missing number" in m or "illegal unit" in m:
        return "dimension_error"
    if "emergency stop" in m:
        return "emergency_stop"
    if "capacity exceeded" in m:
        return "capacity_exceeded"
    return "other"


def likely_package(msg, ctx_lines):
    """从 undefined control sequence 上下文猜宏包。"""
    blob = msg + " " + " ".join(ctx_lines)
    m = re.search(r"\\([A-Za-z@]{2,})", blob)
    if m:
        cmd = m.group(1)
        if cmd in CMD_PACKAGE:
            return CMD_PACKAGE[cmd], cmd
    return None, None


def scan(log_path):
    with open(log_path, encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    errors, warnings, overfull = [], [], []
    i = 0
    while i < len(lines):
        ln = lines[i]
        fl = FILE_LINE_RE.match(ln)
        if fl:
            ctx = lines[i + 1:i + 3]
            cat = classify(fl.group("msg"))
            pkg, cmd = likely_package(fl.group("msg"), ctx) if cat == "undefined_control_sequence" else (None, None)
            errors.append({"file": fl.group("file"), "line": int(fl.group("line")),
                           "message": fl.group("msg").strip(), "category": cat,
                           "likely_package": pkg, "likely_command": cmd,
                           "format": "file-line-error", "cascade": False})
            i += 1
            continue
        pe = PKG_ERR_RE.match(ln) or CLS_ERR_RE.match(ln)
        if pe:
            ctx = []
            j = i + 1
            found_line = None
            while j < min(i + 12, len(lines)) and lines[j].strip() != "":
                ctx.append(lines[j])
                lm = LNN_RE.match(lines[j])
                if lm:
                    found_line = int(lm.group("line"))
                j += 1
            msg = ln[2:].strip()
            errors.append({"file": None, "line": found_line, "message": msg,
                           "category": classify(msg), "likely_package": None,
                           "likely_command": None, "format": "bang",
                           "context": ctx[:4], "cascade": False})
            i = j
            continue
        b = BANG_RE.match(ln)
        if b:
            ctx = []
            j = i + 1
            found_line = None
            while j < min(i + 14, len(lines)) and lines[j].strip() != "":
                ctx.append(lines[j])
                lm = LNN_RE.match(lines[j])
                if lm:
                    found_line = int(lm.group("line"))
                j += 1
            msg = b.group("msg").strip()
            cat = classify(msg)
            fnf = FILE_NOT_FOUND_RE.search(msg)
            pkg = fnf.group("f") if fnf else None
            lp, lc = likely_package(msg, ctx) if cat == "undefined_control_sequence" else (None, None)
            errors.append({"file": None, "line": found_line, "message": msg,
                           "category": cat,
                           "likely_package": lp or (pkg if cat == "missing_file" else None),
                           "likely_command": lc, "format": "bang",
                           "context": ctx[:4], "cascade": False})
            i = j
            continue
        w = WARN_RE.search(ln)
        if w and "Warning" in ln:
            msg = w.group("msg").strip()
            kind = "other"
            if "Citation" in msg and "undefined" in msg:
                kind = "undefined_citation"
            elif "Reference" in msg and "undefined" in msg:
                kind = "undefined_reference"
            elif "multiply" in msg and "defined" in msg:
                kind = "multiply_defined_label"
            elif "Rerun" in msg or "Label(s) may have changed" in msg:
                kind = "rerun_needed"
            warnings.append({"message": msg[:300], "kind": kind,
                             "line": int(w.group("line")) if w.group("line") else None})
        of = OVERFULL_RE.search(ln)
        if of:
            at = ""
            for k in range(i, min(i + 4, len(lines))):
                mm = re.search(r"(?:at lines?|detected at line)\s*(\d+)", lines[k])
                if mm:
                    at = mm.group(1)
                    break
            overfull.append({"points": float(of.group("pt")), "at_line": at or None,
                             "context": ln[:200]})
        i += 1
    return errors, warnings, overfull


def triage(errors):
    """级联根因归并：首错为缺宏包/缺文件时，后续未定义命令标为级联。"""
    if not errors:
        return None
    first = errors[0]
    root = None
    uni = sum(1 for e in errors if e["category"] == "unicode_char_pdflatex")
    if uni >= max(3, len(errors) // 2):
        root = (f"{uni} 处 'Unicode character not set up for LaTeX'：正文含 CJK/Unicode 字符而使用 "
                f"pdflatex。首选改用 xelatex/lualatex 编译，或在导言区加载 ctex/inputenc+fontenc；"
                f"其余错误多为级联")
        for e in errors:
            if e is not first and e["category"] != "unicode_char_pdflatex":
                e["cascade"] = True
        return root
    if first["category"] == "missing_file" and first.get("likely_package"):
        root = f"缺少文件 {first['likely_package']}（疑似未安装宏包或模板类文件缺失），其后未定义命令多为级联"
    elif first["category"] == "undefined_control_sequence" and first.get("likely_package"):
        root = f"首个未定义命令疑似缺宏包 {first['likely_package']}，其后同类错误多为级联"
    elif first["category"] in ("runaway_argument", "brace_mismatch"):
        root = "首个错误为括号/参数失控，其后大量错误可能由同一处失衡引发"
    if root and len(errors) > 1:
        for e in errors[1:]:
            if e["category"] in ("undefined_control_sequence", "undefined_environment",
                                 "math_mode", "other"):
                e["cascade"] = True
    return root


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=None)
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--top", type=int, default=15)
    args = ap.parse_args()

    log = args.log
    if not log:
        cand = os.path.join(args.work, "build_report.json")
        if os.path.exists(cand):
            try:
                log = json.load(open(cand, encoding="utf-8")).get("log")
            except Exception:
                log = None
    if not log or not os.path.exists(log):
        print(f"[tex_logscan] 未找到日志（{log}），请先运行 tex_build.py 或用 --log 指定")
        return 1

    errors, warnings, overfull = scan(log)
    root = triage(errors)
    cats = {}
    for e in errors:
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    report = {
        "log": log,
        "summary": {"errors": len(errors), "warnings": len(warnings),
                    "overfull_hbox": len(overfull),
                    "overfull_hbox_gt20pt": sum(1 for o in overfull if o["points"] > 20),
                    "categories": cats,
                    "cascade_marked": sum(1 for e in errors if e.get("cascade"))},
        "first_error": errors[0] if errors else None,
        "root_cause_hypothesis": root,
        "errors": errors,
        "warnings": warnings,
        "overfull": sorted(overfull, key=lambda o: -o["points"]),
    }
    out = os.path.join(args.work, "log_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[tex_logscan] 错误={len(errors)} 警告={len(warnings)} "
          f"overfull={len(overfull)} 分类={cats}")
    if root:
        print(f"[tex_logscan] 根因假设: {root}")
    for e in errors[:args.top]:
        loc = f"{e['file']}:{e['line']}" if e.get("file") else (f"l.{e['line']}" if e.get("line") else "?")
        pkg = f" → 试 \\usepackage{{{e['likely_package']}}}" if e.get("likely_package") else ""
        cas = " [级联]" if e.get("cascade") else ""
        print(f"  [{e['category']}]{cas} {loc} {e['message'][:110]}{pkg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
