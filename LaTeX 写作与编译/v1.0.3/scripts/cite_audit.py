#!/usr/bin/env python3
r"""v4_cite_audit.py — 引用与参考文献收敛专项：键解析、条目去重、样式一致、收敛编译。

用法:
  python3 v4_cite_audit.py [--project /app/work/project] [--main main.tex] [--work /app/work]
  python3 v4_cite_audit.py --converge [--engine auto] [--timeout 180]   # 驱动多轮编译直至交叉引用收敛

检查项:
  C1  \cite 键在 .bib 中不存在（悬空引用，定位 file:line）
  C2  .bib 条目从未被引用（列表冗余；报告但不擅自删除）
  C3  疑似重复条目：规范化标题相似度 ≥0.90（预印本 vs 正式版、字段差异）
      → 给出合并建议与保留键，交 Agent 决策
  C4  条目关键字段缺失（author/year/title；article 缺 journal）
  C5  样式混用：\citep/\citet 存在但未加载 natbib/biblatex；
      \bibliographystyle 与 biblatex 并存等
  C6  重复 bib key（同键多条）
  C7  DOI 缺失统计（info，供任务要求补全时参考）
输出 work/cite_report.json。仅标准库；相似度用 difflib。
"""
import argparse, difflib, json, os, re, subprocess, sys

BIB_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,")
CITE_RE = re.compile(r"\\cite\w*\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}")


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


def norm_title(t):
    t = re.sub(r"[{}\\]", "", (t or "").lower())
    t = re.sub(r"[^a-z0-9一-鿿]+", " ", t)
    return " ".join(t.split())


def parse_bib(project):
    entries = []
    for dirpath, dirnames, filenames in os.walk(project):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in sorted(filenames):
            if not fn.lower().endswith(".bib"):
                continue
            bp = os.path.join(dirpath, fn)
            try:
                txt = open(bp, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            rel = os.path.relpath(bp, project)
            for m in BIB_ENTRY_RE.finditer(txt):
                etype, key = m.group(1).lower(), m.group(2)
                depth, j = 1, m.end()
                while j < len(txt) and depth > 0:
                    if txt[j] == "{":
                        depth += 1
                    elif txt[j] == "}":
                        depth -= 1
                    j += 1
                body = txt[m.end():j - 1]
                fields = {}
                for fm in re.finditer(r"(\w+)\s*=\s*[\{\"](.+?)[\}\"]\s*,?\s*(?=\n\s*\w+\s*=|\s*$)",
                                      body, flags=re.S):
                    fields[fm.group(1).lower()] = re.sub(r"\s+", " ", fm.group(2)).strip()[:300]
                entries.append({"key": key, "type": etype, "file": rel, "fields": fields,
                                "title": re.sub(r"[{}\\]", "", fields.get("title", ""))})
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--main", default=None)
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--converge", action="store_true")
    ap.add_argument("--engine", default="auto")
    ap.add_argument("--timeout", type=int, default=180)
    args = ap.parse_args()

    insp = {}
    try:
        insp = json.load(open(os.path.join(args.work, "inspection.json"), encoding="utf-8"))
    except Exception:
        pass
    project = args.project or insp.get("staged_project_dir") or "/app/work/project"
    main_rel = args.main or (insp.get("tex_project") or {}).get("main") or "main.tex"

    if args.converge:
        here = os.path.dirname(os.path.abspath(__file__))
        cmd = [sys.executable, os.path.join(here, "tex_build.py"),
               "--project", project, "--main", main_rel, "--engine", args.engine,
               "--bib", "auto", "--until-converge", "--timeout", str(args.timeout),
               "--work", args.work, "--tag", "converge"]
        print("[cite_audit] 驱动收敛编译:", " ".join(cmd))
        rc = subprocess.call(cmd)
        try:
            rep = json.load(open(os.path.join(args.work, "build_report.json"), encoding="utf-8"))
            print(f"[cite_audit] 收敛={rep.get('converged')} 轮次={len(rep.get('passes', []))}")
        except Exception:
            pass
        return rc

    # 收集引用点
    cites, files = [], []
    seen = set()
    def visit(rel, d=0):
        if d > 6 or rel in seen:
            return
        seen.add(rel)
        p = os.path.join(project, rel)
        if not os.path.exists(p):
            return
        files.append(rel)
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            return
        for ln, raw in enumerate(lines, 1):
            line = strip_comments(raw)
            for m in CITE_RE.finditer(line):
                for k in m.group(1).split(","):
                    k = k.strip()
                    if k:
                        cites.append({"key": k, "file": rel, "line": ln,
                                      "cmd": m.group(0).split("{")[0]})
        for m in re.finditer(r"\\(?:input|include)\{([^}]+)\}", "\n".join(lines)):
            sub = m.group(1)
            if not sub.endswith(".tex"):
                sub += ".tex"
            visit(os.path.normpath(os.path.join(os.path.dirname(rel), sub)), d + 1)
    visit(main_rel)

    entries = parse_bib(project)
    bib_keys = {}
    dup_keys = []
    for e in entries:
        if e["key"] in bib_keys:
            dup_keys.append({"key": e["key"], "files": [bib_keys[e["key"]], e["file"]]})
        else:
            bib_keys[e["key"]] = e["file"]
    cited = {c["key"] for c in cites}
    findings = []

    for c in cites:
        if c["key"] not in bib_keys:
            findings.append({"id": "C1", "severity": "error", "file": c["file"],
                             "line": c["line"], "evidence": f"{c['cmd']}{{{c['key']}}}",
                             "suggestion": f"键 {c['key']} 不在任何 .bib 中；在 bib 中检索近义键、"
                                           "补条目或按任务要求处理，不得臆造文献"})
    uncited = [e for e in entries if e["key"] not in cited]
    for e in uncited:
        findings.append({"id": "C2", "severity": "info", "file": e["file"], "line": None,
                         "evidence": f"@{e['type']}{{{e['key']}}} {e['title'][:60]}",
                         "suggestion": "条目未被引用；按任务要求保留（\\nocite）或移除，移除须记 change_log"})
    for dk in dup_keys:
        findings.append({"id": "C6", "severity": "error", "file": dk["files"][1], "line": None,
                         "evidence": f"重复 bib key: {dk['key']} @ {dk['files']}",
                         "suggestion": "同键多条会导致引用歧义；合并保留一条并记 change_log"})
    # C3 标题相似去重
    keys = list({e["key"]: e for e in entries}.values())
    seen_pairs = set()
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            na, nb = norm_title(a["title"]), norm_title(b["title"])
            if not na or not nb or (a["key"], b["key"]) in seen_pairs:
                continue
            r = difflib.SequenceMatcher(None, na, nb).ratio()
            if r >= 0.90:
                seen_pairs.add((a["key"], b["key"]))
                ya, yb = a["fields"].get("year"), b["fields"].get("year")
                keep = a["key"] if (ya and (not yb or ya <= yb)) else b["key"]
                findings.append({"id": "C3", "severity": "warn", "file": b["file"], "line": None,
                                 "evidence": f"{a['key']} ≈ {b['key']}（标题相似度 {r:.2f}）",
                                 "suggestion": f"疑似同一文献重复收录；建议保留 {keep} 并在 change_log "
                                               "写明合并依据（标题/作者/年份比对），不得静默删除"})
    for e in entries:
        f = e["fields"]
        miss = [x for x in ("author", "year", "title") if x not in f]
        if e["type"] in ("article",) and "journal" not in f and "journaltitle" not in f:
            miss.append("journal")
        if miss:
            findings.append({"id": "C4", "severity": "warn", "file": e["file"], "line": None,
                             "evidence": f"@{e['type']}{{{e['key']}}} 缺字段: {', '.join(miss)}",
                             "suggestion": "关键字段缺失影响参考文献著录；从材料中的原文/元数据补齐，"
                                           "查不到则记 uncertainty，不得编造"})
    # C5 样式
    main_txt = ""
    try:
        main_txt = open(os.path.join(project, main_rel), encoding="utf-8",
                        errors="replace").read()
    except OSError:
        pass
    all_txt = main_txt
    for rel in files:
        try:
            all_txt += "\n" + open(os.path.join(project, rel), encoding="utf-8",
                                   errors="replace").read()
        except OSError:
            pass
    uses_natbib_cmds = bool(re.search(r"\\cite[pt]\*?\s*(?:\[|\{)", all_txt))
    has_natbib = "natbib" in main_txt
    has_biblatex = "biblatex" in main_txt
    has_bibstyle = "\\bibliographystyle" in main_txt
    if uses_natbib_cmds and not (has_natbib or has_biblatex):
        findings.append({"id": "C5", "severity": "error", "file": main_rel, "line": None,
                         "evidence": "使用 \\citep/\\citet 但未加载 natbib/biblatex",
                         "suggestion": "加载 natbib（或改用 \\cite）后重编译"})
    if has_biblatex and has_bibstyle:
        findings.append({"id": "C5b", "severity": "warn", "file": main_rel, "line": None,
                         "evidence": "biblatex 与 \\bibliographystyle 并存",
                         "suggestion": "biblatex 不用 \\bibliographystyle；按模板要求二选一"})

    n_doi = sum(1 for e in entries if e["fields"].get("doi"))
    report = {"cited_keys": len(cited), "cite_marks": len(cites),
              "bib_entries": len(entries), "entries_with_doi": n_doi,
              "uncited_keys": [e["key"] for e in uncited],
              "findings": findings,
              "stats": {"findings": len(findings),
                        "errors": sum(1 for f in findings if f["severity"] == "error")}}
    json.dump(report, open(os.path.join(args.work, "cite_report.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[cite_audit] 引用点={len(cites)} 唯一键={len(cited)} bib条目={len(entries)} "
          f"含DOI={n_doi} findings={len(findings)}")
    for f in findings[:15]:
        loc = f"{f['file']}:{f['line']}" if f.get("file") else (f["file"] or "-")
        print(f"  [{f['id']}/{f['severity']}] {loc} {f['evidence'][:70]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
