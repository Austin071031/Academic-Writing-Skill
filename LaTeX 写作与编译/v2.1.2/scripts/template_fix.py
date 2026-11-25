r"""template_fix.py — 模板合规受限自动修复（v2.1.2 增量，本版唯一机制改动）。

基线 template_audit.py 只审不修；本脚本对 template_report.json 的发现做
**三类受限机械修复**，其余仍交 Agent：
  F1 必填元数据 TODO 骨架：P1 error 项（title/author/abstract/keywords/email 等）
     在正确位置插入带 TODO 占位的骨架（不含内容），并登记 manual_confirmations
     （内容须由 Agent 从材料回填，脚本绝不编造元数据）；
  F2 hyperref 加载顺序：把 \usepackage{hyperref} 移到导言区宏包块末尾
     （cleveref 保持在其后，若存在）；
  F3 过时宏包白名单替换：epsfig→graphicx、subfigure→subcaption、times→newtxtext
     （逐条记修复日志；若新包已加载则只删旧包）。
每次修复先备份（<file>.tfix.bak）；--dry-run 预演。
参数读自 direction.json 的 template_fix 节（真被读取）。

用法:
  python3 template_fix.py [--work /app/work] [--project /app/work/project]
                          [--main main.tex] [--dir <skill根目录>] [--dry-run]
前置：需先运行 template_audit.py 生成 work/template_report.json。
"""
import argparse, json, os, re, shutil, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULTS = {
    "insert_metadata": True,
    "fix_hyperref_order": True,
    "replace_packages": {"epsfig": "graphicx", "subfigure": "subcaption",
                         "times": "newtxtext"},
}
P1_SNIPPETS = {
    "title": ("\\title{TODO-Title}", "% TODO(人工确认): 标题须从稿件原文回填"),
    "author": ("\\author{TODO-Author}", "% TODO(人工确认): 作者须从稿件原文回填"),
    "affiliation": ("\\affiliation{TODO-Affiliation}", "% TODO(人工确认): 单位须从稿件原文回填"),
    "email": ("\\email{TODO@example.com}", "% TODO(人工确认): 邮箱须从稿件原文回填"),
    "abstract": ("\\begin{abstract}\nTODO-Abstract\n\\end{abstract}",
                 "% TODO(人工确认): 摘要须从稿件原文回填"),
    "keywords": ("\\begin{IEEEkeywords}\nTODO-Keywords\n\\end{IEEEkeywords}",
                 "% TODO(人工确认): 关键词须按模板格式从原文回填"),
    "maketitle": ("\\maketitle", "% 自动补充: 模板要求 \\maketitle"),
    "date": ("\\date{}", "% 自动补充: \\date{}（留空取默认）"),
    "ccs": ("% TODO(人工确认): ACM CCS 分类须按模板要求从原文确定\n% \\ccsdesc[500]{TODO-CCS}",
            None),
}


def load_params(skill_dir):
    d = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULTS.items()}
    try:
        user = (json.load(open(os.path.join(skill_dir, "direction.json"),
                               encoding="utf-8")).get("template_fix") or {})
        for k in d:
            if k in user:
                d[k] = user[k]
    except Exception:
        pass
    return d


def load_json(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def append_log(work, name, entries):
    p = os.path.join(work, name)
    old = load_json(p, []) or []
    json.dump(old + entries, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--project", default=None)
    ap.add_argument("--main", default=None)
    ap.add_argument("--dir", default=os.path.dirname(HERE))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    P = load_params(args.dir)
    insp = load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    trep = load_json(os.path.join(args.work, "template_report.json"), None)
    project = args.project or insp.get("staged_project_dir") or "/app/work/project"
    main_rel = args.main or (insp.get("tex_project") or {}).get("main") or "main.tex"
    main_path = os.path.join(project, main_rel)
    if trep is None:
        print("[template_fix] 未找到 template_report.json；请先运行 template_audit.py")
        return 0
    if not os.path.exists(main_path):
        print(f"[template_fix] 主文件不存在: {main_path}")
        return 1

    src = open(main_path, encoding="utf-8", errors="replace").read()
    fixes, manuals = [], []

    # F1 必填元数据骨架
    p1_missing = [f["item"] for f in trep.get("findings", [])
                  if f.get("id") == "P1" and f.get("severity") == "error"]
    if P["insert_metadata"] and p1_missing:
        body_m = re.search(r"\\begin\{document\}", src)
        maketitle_m = re.search(r"\\maketitle", src)
        for item in p1_missing:
            if item not in P1_SNIPPETS:
                continue
            snippet, todo = P1_SNIPPETS[item]
            if item in ("abstract", "keywords"):
                # 插到 \maketitle 之后（无 \maketitle 则 \begin{document} 之后）
                anchor = maketitle_m or body_m
                if not anchor:
                    continue
                new_src = src[:anchor.end()] + "\n" + (todo + "\n" if todo else "") + snippet + "\n" + src[anchor.end():]
                pos = src[:anchor.end()].count("\n") + 1
            elif item == "maketitle":
                # \maketitle 必须在正文内（\begin{document} 之后）
                if not body_m:
                    continue
                new_src = src[:body_m.end()] + "\n" + (todo + "\n" if todo else "") + snippet + src[body_m.end():]
                pos = src[:body_m.end()].count("\n") + 1
            else:
                # 元数据命令插到 \begin{document} 之前
                if not body_m:
                    continue
                new_src = src[:body_m.start()] + (todo + "\n" if todo else "") + snippet + "\n" + src[body_m.start():]
                pos = src[:body_m.start()].count("\n") + 1
            fixes.append({"op": "insert_metadata_skeleton", "file": main_rel, "line": pos,
                          "before": f"（缺 {item}）", "after": snippet.split("\n")[0][:60],
                          "reason": f"template_audit P1：文档类要求 {item}",
                          "evidence": "template_report.json#P1"})
            manuals.append({"item": f"{item} 为 TODO 骨架，内容须从稿件原文回填（template_fix 插入）",
                            "severity": "high", "blocking": True})
            src = new_src
            body_m = re.search(r"\\begin\{document\}", src)
            maketitle_m = re.search(r"\\maketitle", src)

    # F2 hyperref 顺序
    if P["fix_hyperref_order"]:
        pre_end = re.search(r"\\begin\{document\}", src)
        pre = src[:pre_end.start()] if pre_end else src
        hr = re.search(r"^[ \t]*\\usepackage(\[[^\]]*\])?\{hyperref\}[ \t]*\n?", pre, flags=re.M)
        if hr:
            after = pre[hr.end():]
            later = re.findall(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}", after)
            later = [p for g in later for p in g.split(",") if p.strip() and p.strip() != "cleveref"]
            if later:
                line = hr.group(0)
                rest = pre[:hr.start()] + pre[hr.end():]
                pkg_iter = list(re.finditer(r"\\usepackage[^\n]*\n", rest))
                anchor = pkg_iter[-1] if pkg_iter else None
                if anchor:
                    new_pre = rest[:anchor.end()] + line + rest[anchor.end():]
                else:
                    new_pre = line + rest
                pos = new_pre[:new_pre.find(line) + len(line)].count("\n")
                fixes.append({"op": "hyperref_last", "file": main_rel, "line": pos,
                              "before": "hyperref 后仍有宏包: " + ",".join(later[:5]),
                              "after": "hyperref 移至宏包块末尾（cleveref 保持其后）",
                              "reason": "template_audit P3：hyperref 应最后加载",
                              "evidence": "template_report.json#P3"})
                src = new_pre + src[pre_end.start():] if pre_end else new_pre

    # F3 过时宏包替换
    for old, new in (P["replace_packages"] or {}).items():
        m = re.search(r"\\usepackage(\[[^\]]*\])?\{" + re.escape(old) + r"\}", src)
        if m:
            already = bool(re.search(r"\\usepackage(\[[^\]]*\])?\{" + re.escape(new) + r"\}", src))
            if already:
                new_src = src[:m.start()] + f"% 已移除过时宏包 {old}（{new} 已加载）" + src[m.end():]
                after = f"删除 {old}（{new} 已在导言区）"
            else:
                new_src = src[:m.start()] + f"\\usepackage{{{new}}} % 替换过时宏包 {old}" + src[m.end():]
                after = f"\\usepackage{{{new}}}（替换 {old}）"
            fixes.append({"op": "replace_deprecated_package", "file": main_rel,
                          "line": src[:m.start()].count("\n") + 1,
                          "before": f"\\usepackage{{{old}}}", "after": after,
                          "reason": f"template_audit P4：{old} 已过时",
                          "evidence": "template_report.json#P4"})
            src = new_src

    if fixes and not args.dry_run:
        bak = main_path + ".tfix.bak"
        if not os.path.exists(bak):
            shutil.copyfile(main_path, bak)
        open(main_path, "w", encoding="utf-8").write(src)
        for fx in fixes:
            fx["applied_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        append_log(args.work, "template_fix_log.json", fixes)
        append_log(args.work, "fix_log.json", fixes)
        if manuals:
            append_log(args.work, "manual_confirmations.json", manuals)

    mode = "DRY-RUN " if args.dry_run else ""
    print(f"[template_fix] {mode}修复 {len(fixes)} 处: "
          + (", ".join(sorted({f['op'] for f in fixes})) if fixes else "无可机械修复项"))
    for fx in fixes:
        print(f"  [{fx['op']}] {fx['file']}:{fx['line']} → {fx['after'][:70]}")
    if manuals:
        print(f"[template_fix] 登记人工确认 {len(manuals)} 项（TODO 骨架内容待回填）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
