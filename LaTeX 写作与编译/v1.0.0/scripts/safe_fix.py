#!/usr/bin/env python3
r"""v1_safe_fix.py — 编译得通方向的白名单机械修复器。

只执行三类高置信机械修复，其余一律交还 Agent 判断：
  A. 缺宏包：依据 log_report.json 中 undefined_control_sequence 的 likely_package，
     若导言区尚未加载则插入 \usepackage{pkg}（hyperref 置于宏包末尾）；
  B. 引擎魔法注释：存在 unicode_char_pdflatex 根因时在首行插入
     "% !TEX program = xelatex"，帮助复现方选对引擎（不改变内容）；
  C. 缺失 \input/\include：创建带 TODO 注释的空占位文件，避免编译中断，
     同时登记 manual_confirmations（内容需人工补写）。
每次修复先备份原文件到 <file>.prefix.bak，修复记录写入 work/fix_log.json。
用法:
  python3 v1_safe_fix.py [--project /app/work/project] [--work /app/work]
                         [--main main.tex] [--dry-run]
"""
import argparse, json, os, re, shutil, sys, datetime

CMD_PACKAGE = {
    "toprule": "booktabs", "midrule": "booktabs", "bottomrule": "booktabs",
    "cmidrule": "booktabs", "includegraphics": "graphicx", "SI": "siunitx",
    "si": "siunitx", "num": "siunitx", "unit": "siunitx", "qty": "siunitx",
    "ang": "siunitx", "mathbb": "amssymb", "mathfrak": "amssymb",
    "dfrac": "amsmath", "cfrac": "amsmath", "operatorname": "amsmath",
    "eqref": "amsmath", "text": "amsmath", "url": "url", "href": "hyperref",
    "autoref": "hyperref", "textcolor": "xcolor", "multirow": "multirow",
    "subcaption": "subcaption", "cref": "cleveref", "Cref": "cleveref",
    "todo": "todonotes", "citep": "natbib", "citet": "natbib",
    "lstinline": "listings", "ce": "mhchem", "bm": "bm", "sout": "ulem",
    "adjustbox": "adjustbox", "threeparttable": "threeparttable",
}
PKG_NORMALIZE = {"hyperref/url": "url", "xcolor(colortbl)": "xcolor",
                 "amsbsy(amsmath)": "amsmath", "algorithm(float)": "algorithm"}
LATE_PACKAGES = {"hyperref", "cleveref"}


def load_json(p, d):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return d


def append_fix(work, entry):
    path = os.path.join(work, "fix_log.json")
    log = load_json(path, []) or []
    log.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def append_manual(work, entry):
    path = os.path.join(work, "manual_confirmations.json")
    log = load_json(path, []) or []
    log.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def backup(path):
    bak = path + ".prefix.bak"
    if not os.path.exists(bak):
        shutil.copyfile(path, bak)
    return bak


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--main", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    insp = load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    project = args.project or insp.get("staged_project_dir") or "/app/work/project"
    main_rel = args.main or (insp.get("tex_project") or {}).get("main") or "main.tex"
    main_path = os.path.join(project, main_rel)
    if not os.path.exists(main_path):
        print(f"[safe_fix] 主文件不存在: {main_path}")
        return 1

    logrep = load_json(os.path.join(args.work, "log_report.json"), {}) or {}
    with open(main_path, encoding="utf-8", errors="replace") as f:
        src = f.read()

    fixes, manuals = [], []

    # --- A. 缺宏包 ---
    needed = {}
    for e in logrep.get("errors", []):
        if e.get("category") == "undefined_control_sequence":
            pkg = e.get("likely_package")
            cmd = e.get("likely_command")
            if not pkg and cmd and cmd in CMD_PACKAGE:
                pkg = CMD_PACKAGE[cmd]
            if pkg:
                pkg = PKG_NORMALIZE.get(pkg, pkg).split("(")[0]
                needed.setdefault(pkg, {"cmd": cmd, "loc": f"{e.get('file')}:{e.get('line')}"})
    loaded = set()
    for g in re.findall(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}", src):
        loaded.update(x.strip() for x in g.split(","))
    to_add = [p for p in needed if p not in loaded and p]
    if to_add:
        normal = [p for p in to_add if p not in LATE_PACKAGES]
        late = [p for p in to_add if p in LATE_PACKAGES]
        insertion = ""
        if normal:
            insertion += "".join(f"\\usepackage{{{p}}}\n" for p in sorted(normal))
        if late:
            insertion += "".join(f"\\usepackage{{{p}}}\n" for p in sorted(late))
        anchor = None
        for m in re.finditer(r"\\usepackage[^\n]*\n", src):
            anchor = m
        if anchor:
            new_src = src[:anchor.end()] + insertion + src[anchor.end():]
            pos = src[:anchor.end()].count("\n") + 1
        else:
            m = re.search(r"\\documentclass[^\n]*\n", src)
            new_src = src[:m.end()] + insertion + src[m.end():]
            pos = src[:m.end()].count("\n") + 1
        for p in to_add:
            fixes.append({"op": "add_package", "file": main_rel, "line": pos,
                          "before": f"（未加载 {p}）", "after": f"\\usepackage{{{p}}}",
                          "reason": f"日志中 \\{needed[p]['cmd'] or '?'} 未定义，"
                                    f"定位 {needed[p]['loc']}；命令→宏包白名单映射",
                          "evidence": "build_baseline.log / log_report.json"})
        if not args.dry_run:
            backup(main_path)
            src = new_src

    # --- B. 引擎魔法注释 ---
    root = logrep.get("root_cause_hypothesis") or ""
    if "Unicode" in root and "% !TEX program" not in src:
        magic = "% !TEX program = xelatex\n"
        fixes.append({"op": "engine_magic_comment", "file": main_rel, "line": 1,
                      "before": "（首行无引擎标注）", "after": magic.strip(),
                      "reason": "日志含大量 'Unicode character not set up'，"
                                "标注 xelatex 以便复现方选对引擎",
                      "evidence": "log_report.json root_cause_hypothesis"})
        if not args.dry_run:
            backup(main_path)
            src = magic + src

    # --- C. 缺失 \input/\include 占位 ---
    for miss in (insp.get("tex_project") or {}).get("missing_refs", []):
        if miss.get("kind") != "input":
            continue
        rel = miss["ref"]
        stub = os.path.join(project, rel)
        if os.path.exists(stub):
            continue
        os.makedirs(os.path.dirname(stub) or ".", exist_ok=True)
        if not args.dry_run:
            with open(stub, "w", encoding="utf-8") as f:
                f.write(f"% 占位文件：原工程缺失 {rel}，由 Skill 创建以保证编译可继续。\n"
                        f"% TODO(人工确认): 请补写本文件实际内容。\n")
        fixes.append({"op": "stub_missing_input", "file": rel, "line": 1,
                      "before": "（文件缺失）", "after": "创建 TODO 占位文件",
                      "reason": "\\input/\\include 目标缺失导致 'File not found'",
                      "evidence": "inspection.json missing_refs"})
        manuals.append({"item": f"{rel} 为自动创建的占位文件，内容需人工补写",
                        "severity": "high", "blocking": True})

    if not args.dry_run and fixes:
        if re.search(r"% !TEX program", src) or to_add:
            with open(main_path, "w", encoding="utf-8") as f:
                f.write(src)
        for fx in fixes:
            fx["applied_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            append_fix(args.work, fx)
        for mn in manuals:
            append_manual(args.work, mn)

    mode = "DRY-RUN " if args.dry_run else ""
    print(f"[safe_fix] {mode}修复 {len(fixes)} 处: "
          + (", ".join(sorted({f['op'] for f in fixes})) if fixes else "无需机械修复"))
    for fx in fixes:
        print(f"  [{fx['op']}] {fx['file']}:{fx['line']} → {fx['after'][:60]}")
    if manuals:
        print(f"[safe_fix] 登记人工确认 {len(manuals)} 项（占位文件内容待补）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
