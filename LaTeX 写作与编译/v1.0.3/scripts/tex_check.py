#!/usr/bin/env python3
"""tex_check.py — 源码级一致性审查：交叉引用、引用键、bib 条目、环境配平、占位符、元数据。

用法:
  python3 tex_check.py [--project /app/work/project] [--main main.tex] [--work /app/work]

输出 work/source_check.json:
  labels[{key,file,line}], refs[{key,file,line,cmd}], undefined_refs[],
  cite_keys[{key,file,line}], bib_entries[{key,type,title,year,doi,fields_missing[]}],
  undefined_cites[], uncited_entries[], unused_labels[],
  env_imbalance[{file,env,begins,ends}], placeholders[{file,line,text}],
  metadata{title,author,date,abstract,keywords}, stats{}
仅标准库。\\input/\\include 递归展开（深度≤6），找不到的子文件记 exception。
"""
import argparse, json, os, re, sys

REF_CMDS = r"(?:ref|eqref|pageref|autoref|cref|Cref|vref|nameref)"
CITE_RE = re.compile(r"\\cite\w*\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}")
LABEL_RE = re.compile(r"\\label\{([^}]+)\}")
REF_RE = re.compile(r"\\" + REF_CMDS + r"\{([^}]+)\}")
BEGIN_RE = re.compile(r"\\begin\{([^}]+)\}")
END_RE = re.compile(r"\\end\{([^}]+)\}")
BIB_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,")
PLACEHOLDER_RE = re.compile(r"TODO|FIXME|XXX|待补充|占位|\?\?")


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


def collect_tex_files(project, main_rel, depth=6):
    seen, order, missing = set(), [], []
    def visit(rel, d):
        if d > depth or rel in seen:
            return
        seen.add(rel)
        path = os.path.join(project, rel)
        if not os.path.exists(path):
            missing.append(rel)
            return
        order.append(rel)
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                txt = f.read()
        except OSError:
            return
        base = os.path.dirname(rel)
        for m in re.finditer(r"\\(?:input|include)\{([^}]+)\}", txt):
            sub = m.group(1)
            if not sub.endswith(".tex"):
                sub += ".tex"
            visit(os.path.normpath(os.path.join(base, sub)).replace("\\", "/"), d + 1)
    visit(main_rel, 0)
    return order, missing


def parse_bib(project):
    entries = []
    bib_files = []
    for dirpath, dirnames, filenames in os.walk(project):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if fn.lower().endswith(".bib"):
                bib_files.append(os.path.join(dirpath, fn))
    for bp in sorted(bib_files):
        try:
            with open(bp, encoding="utf-8", errors="replace") as f:
                txt = f.read()
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
                fields[fm.group(1).lower()] = re.sub(r"\s+", " ", fm.group(2)).strip()[:200]
            title = re.sub(r"[{}\\]", "", fields.get("title", ""))
            missing_fields = [f for f in ("author", "year", "title") if f not in fields]
            entries.append({"key": key, "type": etype, "file": rel,
                            "title": title, "year": fields.get("year"),
                            "doi": fields.get("doi"), "fields_missing": missing_fields})
    return entries


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=None)
    ap.add_argument("--main", default=None)
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    if not args.project:
        try:
            with open(os.path.join(args.work, "inspection.json"), encoding="utf-8") as f:
                args.project = json.load(f).get("staged_project_dir")
        except Exception:
            args.project = None
    if not args.project:
        args.project = "/app/work/project"

    main_rel = args.main
    if not main_rel:
        try:
            with open(os.path.join(args.work, "inspection.json"), encoding="utf-8") as f:
                main_rel = json.load(f)["tex_project"]["main"]
        except Exception:
            main_rel = "main.tex"
    if not main_rel:
        print("[tex_check] 未确定主文件")
        return 1

    files, missing = collect_tex_files(args.project, main_rel)
    labels, refs, cites, env_imb, placeholders = [], [], [], [], []
    metadata = {"title": False, "author": False, "date": False,
                "abstract": False, "keywords": False, "maketitle": False}
    main_txt = ""
    for rel in files:
        path = os.path.join(args.project, rel)
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                raw_lines = f.read().splitlines()
        except OSError:
            continue
        if rel == main_rel:
            main_txt = "\n".join(raw_lines)
        begins = {}
        for ln, raw in enumerate(raw_lines, 1):
            line = strip_comments(raw)
            for m in LABEL_RE.finditer(line):
                labels.append({"key": m.group(1), "file": rel, "line": ln})
            for m in REF_RE.finditer(line):
                for k in m.group(1).split(","):
                    refs.append({"key": k.strip(), "file": rel, "line": ln,
                                 "cmd": m.group(0).split("{")[0]})
            for m in CITE_RE.finditer(line):
                for k in m.group(1).split(","):
                    k = k.strip()
                    if k:
                        cites.append({"key": k, "file": rel, "line": ln})
            for m in BEGIN_RE.finditer(line):
                begins[m.group(1)] = begins.get(m.group(1), 0) + 1
            for m in END_RE.finditer(line):
                begins[m.group(1)] = begins.get(m.group(1), 0) - 1
            pm = PLACEHOLDER_RE.search(line)
            if pm:
                placeholders.append({"file": rel, "line": ln, "text": raw.strip()[:120]})
        for env, cnt in begins.items():
            if cnt != 0 and env not in ("document",):
                env_imb.append({"file": rel, "env": env, "net": cnt})

    if main_txt:
        metadata = {
            "title": bool(re.search(r"\\title\{", main_txt)),
            "author": bool(re.search(r"\\author\{", main_txt)),
            "date": bool(re.search(r"\\date\{", main_txt)),
            "abstract": bool(re.search(r"\\begin\{abstract\}", main_txt)),
            "keywords": bool(re.search(r"\\keywords\{|\\begin\{keywords\}|Keywords", main_txt)),
            "maketitle": bool(re.search(r"\\maketitle", main_txt)),
        }

    label_keys = {}
    dup_labels = []
    for l in labels:
        if l["key"] in label_keys:
            dup_labels.append({"key": l["key"], "first": label_keys[l["key"]],
                               "dup": {"file": l["file"], "line": l["line"]}})
        else:
            label_keys[l["key"]] = {"file": l["file"], "line": l["line"]}
    ref_keys_used = {r["key"] for r in refs}
    undefined_refs = [r for r in refs if r["key"] not in label_keys]
    unused_labels = [l for l in labels if l["key"] not in ref_keys_used]

    bib = parse_bib(args.project)
    bib_keys = {}
    dup_bib = []
    for e in bib:
        if e["key"] in bib_keys:
            dup_bib.append({"key": e["key"], "files": [bib_keys[e["key"]], e["file"]]})
        else:
            bib_keys[e["key"]] = e["file"]
    cited = {c["key"] for c in cites}
    undefined_cites = [c for c in cites if c["key"] not in bib_keys]
    uncited = [e for e in bib if e["key"] not in cited]

    report = {
        "main": main_rel, "files_scanned": files, "missing_inputs": missing,
        "labels": labels, "duplicate_labels": dup_labels,
        "refs": refs, "undefined_refs": undefined_refs, "unused_labels": unused_labels,
        "cite_keys": cites, "bib_entries": bib, "duplicate_bib_keys": dup_bib,
        "undefined_cites": undefined_cites, "uncited_entries": uncited,
        "env_imbalance": env_imb, "placeholders": placeholders,
        "metadata": metadata,
        "stats": {"tex_files": len(files), "labels": len(labels), "refs": len(refs),
                  "cite_marks": len(cites), "bib_entries": len(bib),
                  "undefined_refs": len(undefined_refs),
                  "undefined_cites": len(undefined_cites),
                  "uncited_entries": len(uncited),
                  "placeholders": len(placeholders)},
    }
    with open(os.path.join(args.work, "source_check.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    s = report["stats"]
    print(f"[tex_check] 文件={s['tex_files']} 标签={s['labels']} 引用={s['refs']} "
          f"引文={s['cite_marks']} bib={s['bib_entries']}")
    print(f"[tex_check] 悬空 ref={s['undefined_refs']} 悬空 cite={s['undefined_cites']} "
          f"未被引 bib={s['uncited_entries']} 占位符={s['placeholders']} "
          f"重复 label={len(dup_labels)} 重复 bib key={len(dup_bib)} 环境失衡={len(env_imb)}")
    for r in undefined_refs[:10]:
        print(f"  [ref 未定义] {r['file']}:{r['line']} {r['cmd']}{{{r['key']}}}")
    for c in undefined_cites[:10]:
        print(f"  [cite 未定义] {c['file']}:{c['line']} \\cite{{{c['key']}}}")
    if missing:
        print(f"[tex_check] 缺失 \\input 文件: {missing[:8]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
