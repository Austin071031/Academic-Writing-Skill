#!/usr/bin/env python3
"""inspect_case.py — 读取 /input/case.json、task.md 与材料清单，暂存工程到 work/project。

用法:
  python3 inspect_case.py [--case /input/case.json] [--task /input/task.md]
                          [--input-dir /input] [--work /app/work] [--no-stage]

输出 work/inspection.json:
  case_id, task_head, task_path, materials[{path,kind,size}],
  tex_project{main, mains_candidates, engine, documentclass, packages[],
              bib{style,bib_files[],backend}, inputs[], graphics_refs[], missing_refs[]},
  staged_project_dir, output_contract_fields, exceptions[]
仅标准库。不修改 /input；--stage 默认把输入材料复制到 work/project 供后续编辑。
"""
import argparse, json, os, re, shutil, sys, datetime

TEX_EXT = {".tex", ".sty", ".cls", ".bib", ".bst", ".clo", ".def", ".cfg", ".ltx"}
IMG_EXT = {".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg", ".gif", ".tif", ".tiff", ".bmp"}
DOC_EXT = {".md", ".txt", ".docx", ".doc", ".rtf", ".odt"}
DATA_EXT = {".json", ".csv", ".tsv", ".yaml", ".yml", ".xml", ".ris", ".enw", ".ciw"}

XELATEX_HINTS = ("ctex", "xeCJK", "fontspec", "unicode-math", "xecjk")
LUALATEX_HINTS = ("luatexja", "luacode")

CMD_PACKAGE = {
    "toprule": "booktabs", "midrule": "booktabs", "bottomrule": "booktabs",
    "includegraphics": "graphicx", "SI": "siunitx", "si": "siunitx", "num": "siunitx",
    "unit": "siunitx", "qty": "siunitx", "ang": "siunitx",
    "mathbb": "amssymb", "mathfrak": "amssymb", "boldsymbol": "amsmath",
    "dfrac": "amsmath", "cfrac": "amsmath", "operatorname": "amsmath",
    "text": "amsmath", "eqref": "amsmath", "tag": "amsmath",
    "url": "hyperref", "href": "hyperref", "textcolor": "xcolor",
    "multirow": "multirow", "subcaption": "subcaption", "cref": "cleveref",
    "todo": "todonotes", "citep": "natbib", "citet": "natbib",
    "lstinline": "listings", "algorithmic": "algorithmic",
    "autoref": "hyperref", "captionof": "caption", "rowcolor": "xcolor",
    "ce": "mhchem", "tikz": "tikz", "pgfplots": "pgfplots",
    "bm": "bm", "nicefrac": "nicefrac", "sout": "ulem", "uline": "ulem",
}


def kind_of(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in TEX_EXT:
        return "tex:" + ext[1:]
    if ext in IMG_EXT:
        return "image:" + ext[1:]
    if ext in DOC_EXT:
        return "doc:" + ext[1:]
    if ext in DATA_EXT:
        return "data:" + ext[1:]
    return "other:" + (ext[1:] or "none")


def list_materials(root):
    items = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("__pycache__",)]
        for fn in filenames:
            if fn.startswith("."):
                continue
            p = os.path.join(dirpath, fn)
            try:
                items.append({"path": os.path.relpath(p, root), "kind": kind_of(p),
                              "size": os.path.getsize(p)})
            except OSError:
                pass
    items.sort(key=lambda x: x["path"])
    return items


def read_text(path):
    for enc in ("utf-8", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    return ""


def strip_comments(line):
    out, i, n = [], 0, len(line)
    while i < n:
        c = line[i]
        if c == "\\" and i + 1 < n:
            out.append(line[i:i + 2]); i += 2; continue
        if c == "%":
            break
        out.append(c); i += 1
    return "".join(out)


def analyze_tex_project(root):
    tex_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if fn.lower().endswith((".tex", ".ltx")):
                tex_files.append(os.path.join(dirpath, fn))
    mains = []
    for p in tex_files:
        if re.search(r"\\documentclass", read_text(p)):
            mains.append(p)
    main = None
    if mains:
        def score(p):
            s = 0
            base = os.path.basename(p).lower()
            if base in ("main.tex", "paper.tex", "manuscript.tex", "article.tex", "thesis.tex"):
                s += 10
            txt = read_text(p)
            s += len(re.findall(r"\\(?:input|include)\{", txt))
            s += len(txt) / 10000.0
            return s
        main = sorted(mains, key=score, reverse=True)[0]

    proj = {"main": os.path.relpath(main, root) if main else None,
            "mains_candidates": [os.path.relpath(p, root) for p in mains],
            "tex_files": [os.path.relpath(p, root) for p in sorted(tex_files)],
            "engine": "pdflatex", "documentclass": None, "documentclass_options": [],
            "packages": [], "bib": {"style": None, "bib_files": [], "backend": None},
            "inputs": [], "graphics_refs": [], "missing_refs": []}
    if not main:
        return proj

    txt = read_text(main)
    m = re.search(r"\\documentclass(?:\[([^\]]*)\])?\{([^}]+)\}", txt)
    if m:
        proj["documentclass"] = m.group(2)
        proj["documentclass_options"] = [o.strip() for o in (m.group(1) or "").split(",") if o.strip()]
    pkgs = re.findall(r"\\usepackage(?:\[[^\]]*\])?\{([^}]+)\}", txt)
    flat = []
    for g in pkgs:
        flat.extend([x.strip() for x in g.split(",") if x.strip()])
    proj["packages"] = sorted(set(flat))

    joined = set(flat) | {proj["documentclass"] or ""}
    has_cjk = bool(re.search(r"[一-鿿぀-ヿ가-힯]", txt))
    if any(h in joined for h in XELATEX_HINTS) or has_cjk:
        proj["engine"] = "xelatex"
    elif any(h in joined for h in LUALATEX_HINTS):
        proj["engine"] = "lualatex"

    bm = re.search(r"\\bibliographystyle\{([^}]+)\}", txt)
    if bm:
        proj["bib"]["style"] = bm.group(1)
        proj["bib"]["backend"] = "bibtex"
    if "biblatex" in flat:
        proj["bib"]["backend"] = "biber" if re.search(r"backend\s*=\s*biber", txt) else \
            (proj["bib"]["backend"] or "biber")
        for g in re.findall(r"\\addbibresource(?:\[[^\]]*\])?\{([^}]+)\}", txt):
            proj["bib"]["bib_files"].append(g)
    for g in re.findall(r"\\bibliography\{([^}]+)\}", txt):
        for b in g.split(","):
            b = b.strip()
            if b:
                proj["bib"]["bib_files"].append(b if b.endswith(".bib") else b + ".bib")
    proj["bib"]["bib_files"] = sorted(set(proj["bib"]["bib_files"]))

    incs = re.findall(r"\\(?:input|include)\{([^}]+)\}", txt)
    proj["inputs"] = [i if i.endswith(".tex") else i + ".tex" for i in incs]
    proj["graphics_refs"] = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", txt)

    missing = []
    for rel in proj["inputs"]:
        if not os.path.exists(os.path.join(root, rel)):
            missing.append({"kind": "input", "ref": rel})
    for g in proj["graphics_refs"]:
        cand = [g] if os.path.splitext(g)[1] else [g + e for e in (".pdf", ".png", ".jpg", ".eps")]
        if not any(os.path.exists(os.path.join(root, c)) for c in cand):
            missing.append({"kind": "graphics", "ref": g})
    for b in proj["bib"]["bib_files"]:
        if not os.path.exists(os.path.join(root, b)):
            missing.append({"kind": "bib", "ref": b})
    proj["missing_refs"] = missing
    return proj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--task", default="/input/task.md")
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--no-stage", action="store_true", help="不复制材料到 work/project")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    exceptions = []

    case_id, contract = None, []
    if os.path.exists(args.case):
        try:
            with open(args.case, encoding="utf-8") as f:
                case = json.load(f)
            case_id = case.get("case_id") or case.get("id") or case.get("caseId")
            oc = case.get("output_contract") or case.get("outputContract") or {}
            if isinstance(oc, dict):
                contract = list(oc.keys())
            elif isinstance(oc, list):
                contract = [c.get("name", str(c)) if isinstance(c, dict) else str(c) for c in oc]
            with open(os.path.join(args.work, "case_snapshot.json"), "w", encoding="utf-8") as f:
                json.dump(case, f, ensure_ascii=False, indent=2)
        except Exception as e:
            exceptions.append({"where": "inspect_case", "error": f"case.json 解析失败: {e}"})
    else:
        exceptions.append({"where": "inspect_case", "error": f"未找到 {args.case}"})

    task_head = ""
    if os.path.exists(args.task):
        task_txt = read_text(args.task)
        task_head = task_txt[:2000]
        with open(os.path.join(args.work, "task_copy.md"), "w", encoding="utf-8") as f:
            f.write(task_txt)
    else:
        exceptions.append({"where": "inspect_case", "error": f"未找到 {args.task}"})

    materials = list_materials(args.input_dir) if os.path.isdir(args.input_dir) else []

    staged = None
    scan_root = args.input_dir
    if not args.no_stage and os.path.isdir(args.input_dir):
        staged = os.path.join(args.work, "project")
        if not os.path.exists(staged):
            try:
                shutil.copytree(args.input_dir, staged,
                                ignore=shutil.ignore_patterns("case.json", "task.md",
                                                              ".*", "__pycache__"))
            except Exception as e:
                exceptions.append({"where": "inspect_case", "error": f"暂存工程失败: {e}"})
                staged = None
        if staged:
            scan_root = staged

    proj = analyze_tex_project(scan_root) if os.path.isdir(scan_root) else {}

    insp = {
        "case_id": case_id or "unknown",
        "task_head": task_head,
        "task_path": args.task,
        "materials": materials,
        "tex_project": proj,
        "staged_project_dir": staged,
        "output_contract_fields": contract,
        "cmd_package_map_hint": CMD_PACKAGE,
        "exceptions": exceptions,
        "inspected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    with open(os.path.join(args.work, "inspection.json"), "w", encoding="utf-8") as f:
        json.dump(insp, f, ensure_ascii=False, indent=2)

    print(f"[inspect] case_id={insp['case_id']} 材料={len(materials)} "
          f"主文件={proj.get('main')} 引擎={proj.get('engine')} 类={proj.get('documentclass')}")
    if proj.get("missing_refs"):
        print(f"[inspect] 缺失引用 {len(proj['missing_refs'])} 处: "
              + ", ".join(f"{m['kind']}:{m['ref']}" for m in proj["missing_refs"][:8]))
    if not proj.get("main"):
        print("[inspect] 警告: 未发现含 \\documentclass 的主文件，请人工确认材料形态")
    return 0


if __name__ == "__main__":
    sys.exit(main())
