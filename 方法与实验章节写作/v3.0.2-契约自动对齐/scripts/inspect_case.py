#!/usr/bin/env python3
"""inspect_case.py — 解析 case.json / task.md / 材料文件，生成 work/inspection.json。

用法: python3 inspect_case.py [--case /input/case.json] [--task /input/task.md]
                              [--input-dir /input] [--work /app/work]
只读输入；PDF 用 pdftotext 文本化（按页标记），供后续抽取与逐条溯源。
"""
import argparse, json, os, re, subprocess, sys, hashlib

PDF_EXT = {".pdf"}
CONFIG_EXT = {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".conf", ".properties", ".xml"}
LOG_EXT = {".log", ".out", ".stdout", ".stderr", ".trace"}
CODE_EXT = {".py", ".sh", ".bash", ".ipynb", ".jl", ".cu", ".c", ".cpp", ".h", ".java", ".js", ".ts", ".R"}
DATA_EXT = {".csv", ".tsv", ".jsonl", ".parquet", ".pkl", ".npy", ".npz"}
DOC_EXT = {".md", ".txt", ".tex", ".rst"}

MAX_HEAD = 4000

def sha256(path, limit=1 << 20):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            h.update(f.read(limit))
        return h.hexdigest()[:16]
    except OSError:
        return None

def classify(path):
    ext = os.path.splitext(path)[1].lower()
    name = os.path.basename(path).lower()
    if ext in PDF_EXT:
        return "pdf"
    # 扩展名优先；仅当扩展名不识别时才用文件名提示
    if ext in CONFIG_EXT:
        return "config"
    if ext in LOG_EXT:
        return "log"
    if ext in CODE_EXT:
        return "code"
    if re.search(r"(config|conf|setting|param)", name):
        return "config"
    if re.search(r"\.(log|out)$|(stdout|stderr)$", name):
        return "log"
    if ext in DATA_EXT:
        return "data"
    if ext in DOC_EXT:
        return "doc"
    return "other"

def read_head(path, limit=MAX_HEAD):
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            with open(path, encoding=enc, errors="strict") as f:
                return f.read(limit)
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError:
            return None
    return None

def textify_pdf(path, out_path):
    """pdftotext 按页文本化；页间以 \f 分隔，写为带页码标记的文本。"""
    try:
        r = subprocess.run(["pdftotext", "-enc", "UTF-8", path, "-"],
                           capture_output=True, timeout=120)
        if r.returncode != 0 or not r.stdout:
            return None, f"pdftotext 失败: {r.stderr.decode('utf-8', 'ignore')[:200]}"
        text = r.stdout.decode("utf-8", "ignore")
    except FileNotFoundError:
        return None, "环境中无 pdftotext"
    except Exception as e:
        return None, f"pdftotext 异常: {e}"
    pages = text.split("\f")
    with open(out_path, "w", encoding="utf-8") as f:
        for i, p in enumerate(pages, 1):
            f.write(f"\n===== PAGE {i} =====\n")
            f.write(p)
    return len(pages), None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--task", default="/input/task.md")
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    os.makedirs(os.path.join(args.work, "text"), exist_ok=True)
    exceptions = []

    case_id, contract, task_text = None, [], ""
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
        except Exception as e:
            exceptions.append(f"case.json 解析失败: {e}")
    if os.path.exists(args.task):
        try:
            with open(args.task, encoding="utf-8") as f:
                task_text = f.read(20000)
        except Exception as e:
            exceptions.append(f"task.md 读取失败: {e}")

    materials = {"pdf": [], "config": [], "log": [], "code": [], "data": [], "doc": [], "other": []}
    if os.path.isdir(args.input_dir):
        for root, _dirs, files in os.walk(args.input_dir):
            for fn in sorted(files):
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, args.input_dir)
                if rel in ("case.json", "task.md"):
                    continue
                cls = classify(p)
                size = os.path.getsize(p) if os.path.isfile(p) else 0
                entry = {"path": p, "rel": rel, "class": cls, "size": size,
                         "sha256_head": sha256(p)}
                if cls == "pdf":
                    stem = re.sub(r"\W+", "_", os.path.splitext(fn)[0])
                    out_txt = os.path.join(args.work, "text", stem + ".pages.txt")
                    n_pages, err = textify_pdf(p, out_txt)
                    if err:
                        exceptions.append(f"PDF 文本化失败 {rel}: {err}")
                        entry["textified"] = False
                    else:
                        entry["textified"] = True
                        entry["pages"] = n_pages
                        entry["text_path"] = out_txt
                    materials["pdf"].append(entry)
                elif cls in ("config", "log", "code", "doc"):
                    head = read_head(p)
                    entry["head"] = head[:1500] if head else None
                    if head is None:
                        exceptions.append(f"文本读取失败（编码）: {rel}")
                    materials[cls].append(entry)
                else:
                    materials[cls].append(entry)

    lang_hint = "zh" if re.search(r"[\u4e00-\u9fff]", task_text[:500]) else "en"
    inspection = {
        "case_id": case_id, "output_contract_fields": contract,
        "task_excerpt": task_text[:1200], "language_hint": lang_hint,
        "materials": materials, "exceptions": exceptions,
        "counts": {k: len(v) for k, v in materials.items()},
    }
    out = os.path.join(args.work, "inspection.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(inspection, f, ensure_ascii=False, indent=2)
    print(f"[inspect] case_id={case_id} counts={inspection['counts']} -> {out}")
    if exceptions:
        for e in exceptions:
            print(f"[inspect][WARN] {e}", file=sys.stderr)

if __name__ == "__main__":
    sys.exit(main())
