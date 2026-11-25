#!/usr/bin/env python3
"""inspect_case.py — 解析 case.json / task.md / 材料文件，生成 work/inspection.json。

用法: python3 inspect_case.py [--case /input/case.json] [--task /input/task.md]
                              [--input-dir /input] [--work /app/work]
只读输入；所有判断写入 inspection.json，供 SKILL.md 工作流与后续脚本消费。
"""
import argparse, json, os, re, sys, hashlib

MANUSCRIPT_EXT = {".md", ".txt", ".tex", ".docx", ".pdf"}
MANUSCRIPT_HINT = re.compile(
    r"(manuscript|paper|draft|main|fulltext|稿件|论文|正文|原稿|essay|thesis|article)", re.I)
SKIP_HINT = re.compile(r"(readme|license|config|metadata)", re.I)

def read_text(path, limit=200_000):
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read(limit), enc
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError:
            return None, None
    return None, None

def detect_lang(text):
    cn = len(re.findall(r"[一-鿿]", text))
    en = len(re.findall(r"[A-Za-z]", text))
    if cn + en == 0:
        return "unknown"
    return "zh" if cn >= en * 0.3 else "en"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--task", default="/input/task.md")
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    insp = {"case_id": None, "task_file": None, "task_head": None,
            "material_files": [], "manuscript_candidates": [], "other_files": [],
            "constraints": {}, "output_contract": [], "language_hint": "unknown",
            "encoding_map": {}, "issues": [], "file_sha256": {}}

    case = {}
    if os.path.exists(args.case):
        try:
            with open(args.case, encoding="utf-8") as f:
                case = json.load(f)
            insp["case_id"] = case.get("case_id") or case.get("id") or case.get("caseId")
            for key in ("constraints", "requirements", "instructions", "genre", "audience"):
                if isinstance(case.get(key), (dict, list, str)):
                    insp["constraints"][key] = case.get(key)
            oc = case.get("output_contract") or case.get("outputContract") or {}
            if isinstance(oc, dict):
                insp["output_contract"] = [{"name": k, "spec": v} for k, v in oc.items()]
            elif isinstance(oc, list):
                insp["output_contract"] = oc
        except Exception as e:
            insp["issues"].append(f"case.json 解析失败: {e}")
    else:
        insp["issues"].append("case.json 不存在")

    if os.path.exists(args.task):
        insp["task_file"] = args.task
        text, enc = read_text(args.task)
        if text:
            insp["encoding_map"][args.task] = enc
            insp["task_head"] = text[:1500]
    else:
        insp["issues"].append("task.md 不存在")

    if os.path.isdir(args.input_dir):
        for root, _dirs, files in os.walk(args.input_dir):
            for fn in sorted(files):
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, args.input_dir)
                ext = os.path.splitext(fn)[1].lower()
                try:
                    size = os.path.getsize(p)
                except OSError:
                    size = -1
                entry = {"path": p, "rel": rel, "ext": ext, "size": size}
                insp["material_files"].append(entry)
                try:
                    h = hashlib.sha256()
                    with open(p, "rb") as f:
                        for chunk in iter(lambda: f.read(65536), b""):
                            h.update(chunk)
                    insp["file_sha256"][rel] = h.hexdigest()
                except OSError as e:
                    insp["issues"].append(f"无法读取 {rel}: {e}")
                if fn in ("task.md", "case.json") or SKIP_HINT.search(fn):
                    continue
                if ext in MANUSCRIPT_EXT:
                    score = size
                    if MANUSCRIPT_HINT.search(fn):
                        score += 10**9
                    entry["rank_score"] = score
                    if size == 0:
                        insp["issues"].append(f"空文件: {rel}")
                    insp["manuscript_candidates"].append(entry)
                else:
                    insp["other_files"].append(entry)

    insp["manuscript_candidates"].sort(key=lambda e: -e.get("rank_score", 0))
    if not insp["manuscript_candidates"]:
        insp["issues"].append("未找到稿件候选文件（md/txt/tex/docx/pdf）")
    if len(insp["manuscript_candidates"]) > 1:
        insp["issues"].append(
            "存在多个稿件候选: " + ", ".join(c["rel"] for c in insp["manuscript_candidates"])
            + "（默认取第一个，可在 parse_manuscript.py 用 --file 指定）")

    # 语言嗅探（取第一个可读文本类稿件）
    for c in insp["manuscript_candidates"]:
        if c["ext"] in (".md", ".txt", ".tex"):
            text, enc = read_text(c["path"], 60_000)
            if text:
                insp["language_hint"] = detect_lang(text)
                insp["encoding_map"][c["path"]] = enc
                break

    out = os.path.join(args.work, "inspection.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(insp, f, ensure_ascii=False, indent=2)
    print(f"[inspect_case] case_id={insp['case_id']} 材料={len(insp['material_files'])} "
          f"稿件候选={len(insp['manuscript_candidates'])} 语言={insp['language_hint']}")
    for iss in insp["issues"]:
        print(f"[inspect_case][issue] {iss}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
