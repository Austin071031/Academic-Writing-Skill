#!/usr/bin/env python3
"""inspect_case.py — 解析 case.json / task.md / 材料文件，生成 work/inspection.json。

用法: python3 inspect_case.py [--case /input/case.json] [--task /input/task.md]
                              [--input-dir /input] [--work /app/work]
只读输入；所有判断写入 inspection.json，供 SKILL.md 工作流与后续脚本消费。
长文档特化：识别组织方工单（organizer-edit-workorder*.json）、大纲/提纲文件、
分章节稿件目录、笔记/事实材料、文献库；为每个文件计算 sha256 供溯源。
"""
import argparse, json, os, re, sys, hashlib

MANUSCRIPT_EXT = {".md", ".txt", ".tex", ".docx", ".pdf"}
LIBRARY_EXT = {".bib", ".ris", ".enw", ".ciw", ".nbib"}
LIBRARY_HINT = re.compile(r"(bib|reference|ref|文献|引用|citation|library|works_cited|endnote|cnki|ris|reflist)", re.I)
MANUSCRIPT_HINT = re.compile(r"(manuscript|paper|draft|main|稿件|论文|正文|essay|thesis|chapter|章节|sect|draft)", re.I)
NOTES_HINT = re.compile(r"(note|notes|reading|阅读|笔记|摘录|summary|摘要记录|fact|factsheet|材料|material|data)", re.I)
WORKORDER_HINT = re.compile(r"(organizer[-_]?edit[-_]?workorder|workorder|edit[-_]?order|工单|意见|feedback|review)", re.I)
OUTLINE_HINT = re.compile(r"(outline|提纲|大纲|syllabus|toc)", re.I)

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

def sniff_library_format(path, head):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".bib" or re.search(r"@\w+\s*\{", head):
        return "bibtex"
    if ext == ".ris" or re.search(r"^TY\s+-\s", head, re.M):
        return "ris"
    if ext == ".enw" or re.search(r"^%[A-Z0-9]\s", head, re.M):
        return "endnote"
    if ext == ".ciw":
        return "isi"
    if ext == ".nbib":
        return "nbib"
    if ext == ".json" or head.lstrip().startswith(("{", "[")):
        return "json"
    if re.search(r"\[[JCMDSNRP]\]", head):
        return "cnki_or_gbt"
    if re.search(r"^\s*\[\d+\]\s*\S+", head, re.M):
        return "numbered_plain"
    return "plain"

def detect_style_from_text(text):
    if re.search(r"\[\d+(?:\s*[-–,，]\s*\d+)*\]", text):
        return "numeric"
    if "\\cite{" in text:
        return "latex_cite"
    if re.search(r"[（(][^（）()]{1,40}?,\s*(19|20)\d{2}[a-z]?[)）]", text):
        return "author_year"
    if re.search(r"[\u4e00-\u9fff]{2,4}(等| et al\.?)[）)]?\s*(19|20)\d{2}", text):
        return "author_year"
    return "unknown"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--task", default="/input/task.md")
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    insp = {"case_id": None, "task_file": None, "task_head": None,
            "material_files": [], "manuscript_candidates": [], "library_candidates": [],
            "notes_candidates": [], "workorder_files": [], "outline_candidates": [],
            "other_files": [], "constraints": {},
            "output_contract": [], "citation_style_hint": "unknown",
            "language_hint": "unknown", "encoding_map": {},
            "issues": [], "file_sha256": {}}

    case = {}
    if os.path.exists(args.case):
        try:
            with open(args.case, encoding="utf-8") as f:
                case = json.load(f)
            insp["case_id"] = case.get("case_id") or case.get("id") or case.get("caseId")
            for key in ("constraints", "requirements", "instructions"):
                if isinstance(case.get(key), (dict, list, str)):
                    insp["constraints"][key] = case.get(key)
            oc = case.get("output_contract") or case.get("outputContract") or {}
            if isinstance(oc, dict):
                insp["output_contract"] = [{"name": k, "spec": v} for k, v in oc.items()]
            elif isinstance(oc, list):
                insp["output_contract"] = oc
            for key in ("citation_style", "style", "target_style", "format", "language"):
                if case.get(key):
                    insp["constraints"][key] = case.get(key)
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
            st = detect_style_from_text(text)
            if st != "unknown":
                insp["citation_style_hint"] = st
            if len(re.findall(r"[\u4e00-\u9fff]", text)) > 50:
                insp["language_hint"] = "zh"
            m = re.search(r"(GB/?T\s*7714[—\-–]?\d{4}|APA\s*\d*|MLA|Chicago|Vancouver|IEEE|顺序编码|著者[—-]出版年|author[ -]?year|numeric)", text, re.I)
            if m:
                insp["constraints"]["style_mentioned"] = m.group(1)
    else:
        insp["issues"].append("task.md 不存在")

    if os.path.isdir(args.input_dir):
        for root, _dirs, files in os.walk(args.input_dir):
            for fn in sorted(files):
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, args.input_dir)
                ext = os.path.splitext(fn)[1].lower()
                entry = {"path": p, "rel": rel, "ext": ext, "size": os.path.getsize(p)}
                insp["material_files"].append(entry)
                try:
                    h = hashlib.sha256()
                    with open(p, "rb") as f:
                        for chunk in iter(lambda: f.read(65536), b""):
                            h.update(chunk)
                    insp["file_sha256"][rel] = h.hexdigest()
                except OSError as e:
                    insp["issues"].append(f"无法读取 {rel}: {e}")
                if fn in ("task.md", "case.json"):
                    continue
                # 组织方工单（edit workorder）优先识别
                if (WORKORDER_HINT.search(fn) and ext in (".json", ".md", ".txt", ".yaml", ".yml")) or \
                   (ext == ".json" and WORKORDER_HINT.search(rel)):
                    entry["kind"] = "workorder"
                    insp["workorder_files"].append(entry)
                    continue
                # 大纲/提纲
                if OUTLINE_HINT.search(fn) and ext in (".md", ".txt", ".json", ".tex", ".yaml", ".yml", ".docx"):
                    insp["outline_candidates"].append(entry)
                    continue
                is_lib = (ext in LIBRARY_EXT and ext != ".json") or LIBRARY_HINT.search(fn)
                if ext in (".csv",) and LIBRARY_HINT.search(fn):
                    is_lib = True
                if ext == ".json" and LIBRARY_HINT.search(fn):
                    is_lib = True
                if is_lib:
                    head, enc = read_text(p, 4000)
                    fmt = sniff_library_format(p, head) if head is not None else "unknown"
                    if head is not None:
                        insp["encoding_map"][p] = enc
                    entry["library_format"] = fmt
                    insp["library_candidates"].append(entry)
                    continue
                if ext in MANUSCRIPT_EXT and MANUSCRIPT_HINT.search(fn):
                    insp["manuscript_candidates"].append(entry)
                    continue
                if ext in (".md", ".txt", ".json", ".csv") and NOTES_HINT.search(fn):
                    insp["notes_candidates"].append(entry)
                    continue
                if ext in MANUSCRIPT_EXT and not LIBRARY_HINT.search(fn):
                    insp["manuscript_candidates"].append(entry)
                elif ext in (".md", ".txt"):
                    insp["notes_candidates"].append(entry)
                else:
                    insp["other_files"].append(entry)

    for c in insp["manuscript_candidates"]:
        if c["ext"] in (".md", ".txt", ".tex"):
            text, enc = read_text(c["path"], 60_000)
            if text:
                st = detect_style_from_text(text)
                if st != "unknown":
                    insp["citation_style_hint"] = st
                if insp["language_hint"] == "unknown":
                    n_zh = len(re.findall(r"[\u4e00-\u9fff]", text))
                    n_la = len(re.findall(r"[a-zA-Z]", text))
                    if n_zh > max(50, n_la // 2):
                        insp["language_hint"] = "zh"
                    elif n_la > 200:
                        insp["language_hint"] = "en"
                break

    out = os.path.join(args.work, "inspection.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(insp, f, ensure_ascii=False, indent=2)
    print(f"[inspect_case] case_id={insp['case_id']} 材料={len(insp['material_files'])} "
          f"稿件={len(insp['manuscript_candidates'])} 文献库={len(insp['library_candidates'])} "
          f"笔记={len(insp['notes_candidates'])} 工单={len(insp['workorder_files'])} "
          f"大纲={len(insp['outline_candidates'])} 样式={insp['citation_style_hint']} 语言={insp['language_hint']}")
    for iss in insp["issues"]:
        print(f"[inspect_case][issue] {iss}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
