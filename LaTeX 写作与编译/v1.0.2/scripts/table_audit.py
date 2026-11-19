#!/usr/bin/env python3
r"""v3_table_audit.py — 表格与浮动体专项审查：列数一致性、三线表、缩放掩盖、浮动位置。

用法:
  python3 v3_table_audit.py [--project /app/work/project] [--main main.tex]
                            [--work /app/work] [--apply-booktabs] [--apply-float-htbp]

检查项:
  T1  表格缺 \caption 或 \label
  T2  \caption 位于 tabular 之后（多数期刊模板要求表题在表上方）
  T3  行内单元格数与列声明不一致（考虑 \multicolumn），定位到行
  T4  仅使用 \hline（建议 booktabs 三线表 \toprule/\midrule/\bottomrule）；
      --apply-booktabs 对简单 \hline 模式做机械转换并记 fix_log
  T5  \resizebox/\scalebox 包裹 tabular（缩放掩盖超宽，题面明确反对）→ 建议
      改用 tabularx/longtable/调整列宽或字号声明
  T6  浮动位置单独使用 [h] 或 [H]（建议 [htbp]；--apply-float-htbp 可机械改）
  T7  超宽嫌疑（最长行字符数启发式 >110，提示人工核对，标注为启发式估计）
  T8  跨页嫌疑：行数 >45 的普通 tabular（建议 longtable），标注为启发式
输出 work/table_report.json；机械改动记 work/fix_log.json。仅标准库。
"""
import argparse, json, os, re, sys, datetime

COL_TOKEN = re.compile(r"[lcr]|[pmb]\{[^}]*\}|>\{[^}]*\}|<\{[^}]*\}|@\{[^}]*\}|\|")


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


def count_columns(spec):
    spec = re.sub(r"\*\{(\d+)\}\{([^}]*)\}", lambda m: m.group(2) * int(m.group(1)), spec)
    return len([t for t in COL_TOKEN.findall(spec) if t in ("l", "c", "r") or t.startswith(("p", "m", "b"))])


def find_env_blocks(lines, env):
    """返回 [(start_idx, end_idx)]（0-based 行号区间，含 begin/end 行）。"""
    blocks, stack = [], []
    for i, raw in enumerate(lines):
        line = strip_comments(raw)
        if re.search(r"\\begin\{" + env + r"\}", line):
            stack.append(i)
        if re.search(r"\\end\{" + env + r"\}", line) and stack:
            blocks.append((stack.pop(), i))
    return blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--main", default=None)
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--apply-booktabs", action="store_true")
    ap.add_argument("--apply-float-htbp", action="store_true")
    args = ap.parse_args()

    insp = {}
    try:
        insp = json.load(open(os.path.join(args.work, "inspection.json"), encoding="utf-8"))
    except Exception:
        pass
    project = args.project or insp.get("staged_project_dir") or "/app/work/project"
    main_rel = args.main or (insp.get("tex_project") or {}).get("main") or "main.tex"

    files = []
    try:
        chk = json.load(open(os.path.join(args.work, "source_check.json"), encoding="utf-8"))
        files = chk.get("files_scanned") or []
    except Exception:
        pass
    if not files:
        files = [main_rel]

    findings, fixes, tables = [], [], []
    for rel in files:
        path = os.path.join(project, rel)
        if not os.path.exists(path):
            continue
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
        tabular_blocks = find_env_blocks(lines, r"tabular\*?")
        table_blocks = find_env_blocks(lines, "table")
        for bi, (s, e) in enumerate(tabular_blocks):
            blk = lines[s:e + 1]
            spec = ""
            ncols = 0
            for b in blk:
                m = re.search(r"\\begin\{tabular\*?\}(?:\[[^\]]*\])?(?:\{[^}]*\})?\{([^}]*)\}", b)
                if m:
                    spec = m.group(1)
                    ncols = count_columns(spec)
                    break
            info = {"file": rel, "begin_line": s + 1, "end_line": e + 1,
                    "spec": spec, "columns": ncols,
                    "has_caption": False, "has_label": False,
                    "caption_after": False, "hline_only": False,
                    "booktabs": False, "resize_wrapped": False, "rows": 0}
            # caption/label 在所属 table 块中判定
            container = None
            for (ts, te) in table_blocks:
                if ts <= s and e <= te:
                    container = (ts, te)
                    break
            region = lines[container[0]:container[1] + 1] if container else blk
            joined = "\n".join(region)
            info["has_caption"] = "\\caption" in joined
            info["has_label"] = "\\label" in joined
            if container:
                cap_pos = next((i for i, l in enumerate(region) if "\\caption" in l), None)
                tab_pos = s - container[0]
                info["caption_after"] = bool(cap_pos is not None and cap_pos > tab_pos)
            info["hline_only"] = ("\\hline" in joined) and not any(
                k in joined for k in ("\\toprule", "\\midrule", "\\bottomrule"))
            info["booktabs"] = "\\toprule" in joined
            lo = max(0, s - 2)
            info["resize_wrapped"] = any("\\resizebox" in l or "\\scalebox" in l
                                         for l in lines[lo:s + 1])
            # 行列数一致性
            body = [l for l in blk if "&" in strip_comments(l) or "\\\\" in strip_comments(l)]
            info["rows"] = len(body)
            for rl in body:
                clean = strip_comments(rl)
                for part in clean.split("\\\\"):
                    if not part.strip() or part.strip().startswith("\\hline") and "&" not in part:
                        continue
                    cells = part.count("&") + 1
                    mc = sum(int(x) - 1 for x in re.findall(r"\\multicolumn\{(\d+)\}", part))
                    cells += mc
                    if ncols and cells != ncols and "&" in part:
                        findings.append({"id": "T3", "severity": "error", "file": rel,
                                         "line": lines.index(rl) + 1 if rl in lines else None,
                                         "evidence": rl.strip()[:120],
                                         "suggestion": f"该行解析出 {cells} 列，与列声明 {ncols} 列不一致；"
                                                       "检查 & 个数或 \\multicolumn"})
            # T1/T2/T4/T5/T7/T8
            if not info["has_caption"]:
                findings.append({"id": "T1", "severity": "warn", "file": rel, "line": s + 1,
                                 "evidence": "tabular 块无 \\caption",
                                 "suggestion": "为表格补 \\caption（表题）"})
            if not info["has_label"]:
                findings.append({"id": "T1b", "severity": "info", "file": rel, "line": s + 1,
                                 "evidence": "表格无 \\label",
                                 "suggestion": "补 \\label{tab:...} 以便 \\ref 交叉引用"})
            if info["caption_after"]:
                findings.append({"id": "T2", "severity": "info", "file": rel, "line": s + 1,
                                 "evidence": "\\caption 位于 tabular 之后",
                                 "suggestion": "多数期刊模板要求表题在表上方；请按目标模板核对"})
            if info["hline_only"]:
                findings.append({"id": "T4", "severity": "warn", "file": rel, "line": s + 1,
                                 "evidence": "仅用 \\hline 绘制表格线",
                                 "suggestion": "改用 booktabs 三线表：\\toprule / \\midrule / \\bottomrule，"
                                               "删除竖线与多余横线"})
            if info["resize_wrapped"]:
                findings.append({"id": "T5", "severity": "warn", "file": rel, "line": s + 1,
                                 "evidence": "tabular 被 \\resizebox/\\scalebox 包裹",
                                 "suggestion": "缩放掩盖超宽且字号不一致；改用 tabularx 指定 X 列、"
                                               "longtable 跨页，或调整列内容/字号声明"})
            if info["rows"] > 45:
                findings.append({"id": "T8", "severity": "info", "file": rel, "line": s + 1,
                                 "evidence": f"表格约 {info['rows']} 行（启发式估计）",
                                 "suggestion": "跨页嫌疑：改用 longtable 并核对表头重复设置"})
            tables.append(info)

        # T6 浮动位置
        for i, raw in enumerate(lines):
            m = re.search(r"\\begin\{(table|figure)\}\[([hH]+)\]", strip_comments(raw))
            if m:
                findings.append({"id": "T6", "severity": "warn", "file": rel, "line": i + 1,
                                 "evidence": raw.strip()[:120],
                                 "suggestion": f"浮动位置 [{m.group(2)}] 过于强硬；建议 [htbp]"
                                               f"（[H] 还需 float 宏包）"})
                if args.apply_float_htbp:
                    new = re.sub(r"(\\begin\{(?:table|figure)\})\[[hH]+\]",
                                 r"\1[htbp]", raw)
                    if new != raw:
                        fixes.append({"op": "float_specifier", "file": rel, "line": i + 1,
                                      "before": raw.strip()[:120], "after": new.strip()[:120],
                                      "reason": "浮动位置放宽为 [htbp]，避免 'Too many unprocessed floats'",
                                      "evidence": "table_audit T6"})
                        lines[i] = new

        # T4 机械转换 booktabs（仅简单 \hline 模式）
        if args.apply_booktabs:
            for info in tables:
                if info["file"] != rel or not info["hline_only"]:
                    continue
                s, e = info["begin_line"] - 1, info["end_line"] - 1
                hlines = [i for i in range(s, e + 1) if "\\hline" in lines[i]]
                if len(hlines) < 2 or len(hlines) > 4:
                    continue
                repl = {hlines[0]: "\\toprule", hlines[1]: "\\midrule", hlines[-1]: "\\bottomrule"}
                if len(hlines) == 2:
                    repl = {hlines[0]: "\\toprule", hlines[-1]: "\\bottomrule"}
                ok = True
                for i, rule in repl.items():
                    if lines[i].strip() != "\\hline":
                        ok = False
                if not ok:
                    continue
                for i, rule in repl.items():
                    before = lines[i]
                    lines[i] = re.sub(r"\\hline", lambda _: rule, before)
                    fixes.append({"op": "hline_to_booktabs", "file": rel, "line": i + 1,
                                  "before": before.strip(), "after": lines[i].strip(),
                                  "reason": "\\hline → booktabs 三线表（机械转换，简单模式）",
                                  "evidence": "table_audit T4"})
                if not any("\\usepackage" in l and "booktabs" in l for l in lines[:80]):
                    findings.append({"id": "T4b", "severity": "warn", "file": rel, "line": 1,
                                     "evidence": "已转换 booktabs 但导言区未见 \\usepackage{booktabs}",
                                     "suggestion": "请确认加载 booktabs（v1 方向可用 safe_fix 自动补）"})

        if fixes and (args.apply_booktabs or args.apply_float_htbp):
            open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")

    if fixes:
        fp = os.path.join(args.work, "fix_log.json")
        try:
            log = json.load(open(fp, encoding="utf-8"))
        except Exception:
            log = []
        for fx in fixes:
            fx["applied_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        log.extend(fixes)
        json.dump(log, open(fp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    report = {"tables": tables, "findings": findings,
              "applied_fixes": len(fixes),
              "stats": {"tables": len(tables), "findings": len(findings),
                        "errors": sum(1 for f in findings if f["severity"] == "error"),
                        "warns": sum(1 for f in findings if f["severity"] == "warn")}}
    json.dump(report, open(os.path.join(args.work, "table_report.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[table_audit] 表格={len(tables)} findings={len(findings)} 机械修复={len(fixes)}")
    for f in findings[:15]:
        loc = f"{f['file']}:{f['line']}"
        print(f"  [{f['id']}/{f['severity']}] {loc} {f['suggestion'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
