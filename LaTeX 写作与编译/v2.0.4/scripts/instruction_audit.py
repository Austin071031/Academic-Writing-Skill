r"""instruction_audit.py — 题面指令原子化与产物落实审计（v2.0.4 增量，本版唯一改动）。

把 task.md（辅以 case.json）拆成原子机检指令清单 work/instruction_checklist.json，
并在交付前对照编译/审查产物逐条审计 work/instruction_report.json：
  error 级：指定引擎/编译器、编译通过、收敛、必含项；
  warn 级 ：三线表、公式编号策略、参考文献样式、模板类、修改记录；
指令参数读自 direction.json 的 instruction_audit 节（参数真被读取，不是装饰）。

用法:
  python3 instruction_audit.py [--task /input/task.md] [--case /input/case.json]
      [--work /app/work] [--project /app/work/project] [--dir <skill根目录>]

审计数据源（均只读）：build_report.json / source_check.json / template_report.json /
inspection.json / change_log.json / fix_log.json + 工程源码直扫。
判定：pass / fail / unknown（证据不足，交 Agent 人工核）/ na（指令不涉及）。
仅标准库；单次运行 <5s。
"""
import argparse, json, os, re, sys

DEFAULTS = {
    "engine_keys": ["pdflatex", "xelatex", "lualatex", "latexmk", "tectonic"],
    "bibtool_keys": ["bibtex", "biber"],
    "booktabs_keys": ["三线表", "booktabs"],
    "eqnum_patterns": ["被引用公式.*编号", "所有公式.*编号", "公式.*编号", "编号.*公式"],
    "template_keys": ["IEEEtran", "elsarticle", "acmart", "ctexart", "ctex", "revtex",
                      "llncs", "ieeetran", "模板"],
    "bibstyle_keys": ["GB/T 7714", "gbt7714", "plain", "unsrt", "IEEEtran",
                      "apalike", "numeric", "author-year", "著者-出版年", "顺序编码"],
    "required_patterns": ["须包含", "需包含", "必须包含", "应包含", "须涵盖", "保留",
                          "不得删除", "不可删除"],
    "changelog_keys": ["修改记录", "改动记录", "变更记录", "记录每处修改", "记录所有修改"],
}


def load_params(skill_dir):
    p = os.path.join(skill_dir, "direction.json")
    params = dict(DEFAULTS)
    try:
        d = json.load(open(p, encoding="utf-8"))
        user = d.get("instruction_audit") or {}
        for k, v in user.items():
            if isinstance(v, list) and v:
                params[k] = v
    except Exception:
        pass
    return params


def read(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def load_json(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def extract_instructions(task, P):
    items = []
    low = task.lower()
    for ek in P["engine_keys"]:
        if ek in low:
            items.append({"id": f"I_engine_{ek}", "type": "engine", "level": "error",
                          "requirement": f"题面指定编译器/引擎: {ek}", "expect": ek})
    if "bibtex" in low or "biber" in low:
        tool = "biber" if "biber" in low else "bibtex"
        items.append({"id": "I_bibtool", "type": "bibtool", "level": "warn",
                      "requirement": f"题面提及参考文献工具: {tool}", "expect": tool})
    if any(k in task for k in P["booktabs_keys"]):
        items.append({"id": "I_booktabs", "type": "booktabs", "level": "warn",
                      "requirement": "题面要求三线表/booktabs 表式", "expect": "\\toprule"})
    for pat in P["eqnum_patterns"]:
        if re.search(pat, task):
            items.append({"id": "I_eqnum", "type": "eqnum", "level": "warn",
                          "requirement": f"题面含公式编号要求（{pat}）", "expect": "task_items 人工核"})
            break
    if re.search(r"编译(通过|成功)|compile", low):
        items.append({"id": "I_compile", "type": "compile", "level": "error",
                      "requirement": "编译通过", "expect": "build.success=true"})
    if re.search(r"收敛|converge", low):
        items.append({"id": "I_converge", "type": "converge", "level": "error",
                      "requirement": "交叉引用收敛", "expect": "build.converged=true"})
    for k in P["template_keys"]:
        if k in task:
            items.append({"id": f"I_template_{k}", "type": "template", "level": "warn",
                          "requirement": f"题面提及模板/类: {k}", "expect": k})
            break
    for k in P["bibstyle_keys"]:
        if k.lower() in low:
            items.append({"id": "I_bibstyle", "type": "bibstyle", "level": "warn",
                          "requirement": f"题面提及参考文献样式: {k}", "expect": k})
            break
    for m in re.finditer(r"(须包含|需包含|必须包含|应包含|须涵盖|保留|不得删除|不可删除)"
                         r"([^，,。；\n]{2,60})", task):
        body = m.group(2).strip("，,。 ")
        for it in re.split(r"[、，,]|(?:\s*(?:和|与|及)\s*)", body):
            it = it.strip()
            if 1 < len(it) <= 30:
                items.append({"id": f"I_req_{len(items)}", "type": "required_item",
                              "level": "error", "requirement": f"必含/保留: {it}",
                              "expect": it})
    if any(k in task for k in P["changelog_keys"]):
        items.append({"id": "I_changelog", "type": "changelog", "level": "warn",
                      "requirement": "题面要求保留修改记录", "expect": "change_log 非空"})
    return items


def audit(items, work, project):
    build = load_json(os.path.join(work, "build_report.json"), {}) or {}
    insp = load_json(os.path.join(work, "inspection.json"), {}) or {}
    changes = load_json(os.path.join(work, "change_log.json"), []) or []
    fixes = load_json(os.path.join(work, "fix_log.json"), []) or []
    all_src = ""
    for dirpath, dirnames, filenames in os.walk(project):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if fn.endswith((".tex", ".bib", ".sty", ".cls")):
                all_src += "\n" + read(os.path.join(dirpath, fn))
    report = []
    for it in items:
        t, st, ev = it["type"], "unknown", ""
        if t == "engine":
            eng = build.get("engine")
            if eng:
                ok = it["expect"] in (eng, "latexmk") or eng == it["expect"] or \
                    (it["expect"] == "latexmk" and eng in ("pdflatex", "xelatex", "lualatex"))
                st = "pass" if ok else "fail"
                ev = f"build_report.engine={eng}，题面要求 {it['expect']}"
            else:
                ev = "尚无编译报告"
        elif t == "bibtool":
            cmds = " ".join(build.get("commands", []))
            st = "pass" if it["expect"] in cmds else ("unknown" if not cmds else "fail")
            ev = f"编译命令序列{'含' if st=='pass' else '不含'} {it['expect']}"
        elif t == "booktabs":
            has_bt = "\\toprule" in all_src
            has_hl = "\\hline" in all_src
            st = "pass" if has_bt and not has_hl else ("fail" if has_hl and not has_bt else "unknown")
            ev = f"源码 booktabs={has_bt} \\hline={has_hl}"
        elif t == "eqnum":
            ev = "编号策略需 Agent 对照 task_items 人工确认"
            st = "unknown"
        elif t == "compile":
            if "success" in build:
                st = "pass" if build.get("success") else "fail"
                ev = f"build.success={build.get('success')}"
        elif t == "converge":
            if "converged" in build:
                st = "pass" if build.get("converged") else "fail"
                ev = f"build.converged={build.get('converged')}"
        elif t == "template":
            cls = (insp.get("tex_project") or {}).get("documentclass") or ""
            exp = it["expect"]
            if exp == "模板":
                st, ev = "unknown", "题面泛指模板，需 Agent 核对 documentclass 与模板要求"
            else:
                st = "pass" if cls.lower() == exp.lower() else ("unknown" if not cls else "fail")
                ev = f"documentclass={cls or '未检出'}，题面提及 {exp}"
        elif t == "bibstyle":
            exp = it["expect"]
            st = "pass" if exp in all_src or exp.lower() in all_src.lower() else "unknown"
            ev = "源码中检出样式键" if st == "pass" else "源码未直接检出，需 Agent 核对 .bst/biblatex 设置"
        elif t == "required_item":
            kw = it["expect"]
            probe = re.escape(kw[:12])
            st = "pass" if re.search(probe, all_src) else "unknown"
            ev = f"工程源码{'检出' if st=='pass' else '未检出'}关键词 {kw[:12]}，未检出未必缺失，需 Agent 核"
        elif t == "changelog":
            st = "pass" if (changes or fixes) else "fail"
            ev = f"change_log={len(changes)} 条，fix_log={len(fixes)} 条"
        report.append({**it, "status": st, "evidence": ev})
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="/input/task.md")
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--project", default=None)
    ap.add_argument("--dir", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    args = ap.parse_args()

    insp = load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    project = args.project or insp.get("staged_project_dir") or "/app/work/project"
    params = load_params(args.dir)
    task = read(args.task) + "\n" + read(args.case)

    items = extract_instructions(task, params)
    json.dump({"task": args.task, "items": items},
              open(os.path.join(args.work, "instruction_checklist.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    report = audit(items, args.work, project)
    fails = [r for r in report if r["status"] == "fail"]
    unknowns = [r for r in report if r["status"] == "unknown"]
    out = {"items": report,
           "summary": {"total": len(report),
                       "pass": sum(1 for r in report if r["status"] == "pass"),
                       "fail": len(fails),
                       "unknown": len(unknowns),
                       "error_level_fail": sum(1 for r in fails if r["level"] == "error")},
           "note": "fail 级须处置后再交付；unknown 由 Agent 人工核，结论记入 uncertainty。"}
    json.dump(out, open(os.path.join(args.work, "instruction_report.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=2)

    s = out["summary"]
    print(f"[instruction_audit] 指令={s['total']} pass={s['pass']} fail={s['fail']} "
          f"unknown={s['unknown']} error级fail={s['error_level_fail']}")
    for r in fails + unknowns[:8]:
        print(f"  [{r['level']}/{r['status']}] {r['requirement']} — {r['evidence'][:90]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
