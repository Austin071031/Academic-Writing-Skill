#!/usr/bin/env python3
"""inspect_case.py — 解析 case.json / task.md / 材料文件，生成 work/inspection.json。

用法: python3 inspect_case.py [--case /input/case.json] [--task /input/task.md]
                              [--input-dir /input] [--work /app/work]
只读输入；所有判断写入 inspection.json，供 SKILL.md 工作流与后续脚本消费。
"""
import argparse, json, os, re, sys, hashlib

MANUSCRIPT_EXT = {".md", ".txt", ".tex", ".docx", ".pdf"}
LIBRARY_EXT = {".bib", ".ris", ".enw", ".ciw", ".txt", ".csv", ".json", ".nbib"}
LIBRARY_HINT = re.compile(r"(bib|reference|ref|文献|引用|citation|library|works_cited|endnote|cnki|ris)", re.I)
MANUSCRIPT_HINT = re.compile(r"(manuscript|paper|draft|main|稿件|论文|正文|essay|thesis|abs)", re.I)

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
    if ext in (".csv",):
        return "csv"
    if ext == ".json" or head.lstrip().startswith(("{", "[")):
        return "json"
    # CNKI / 知网风格: [1] 作者. 题名[J]. 刊名, 年, 卷(期): 页.
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
            "other_files": [], "constraints": {}, "output_contract": [],
            "citation_style_hint": "unknown", "encoding_map": {},
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
            for key in ("citation_style", "style", "target_style", "format"):
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
            m = re.search(r"(GB/?T\s*7714[—\-–]?\d{4}|APA\s*\d*|MLA|Chicago|Vancouver|IEEE|顺序编码|著者[—-]出版年|author[ -]?year|numeric)", text, re.I)
            if m:
                insp["constraints"]["style_mentioned"] = m.group(1)
    else:
        insp["issues"].append("task.md 不存在")

    # 材料文件清点
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
                    continue  # 任务说明与案例描述不属于科研材料
                if ext in MANUSCRIPT_EXT and not LIBRARY_HINT.search(fn):
                    insp["manuscript_candidates"].append(entry)
                if (ext in LIBRARY_EXT and fn != "case.json") or LIBRARY_HINT.search(fn):
                    head, enc = read_text(p, 4000) if ext != ".docx" else (None, None)
                    if ext == ".docx":
                        fmt = "docx"
                    elif ext == ".pdf":
                        fmt = "pdf"
                    elif head is not None:
                        fmt = sniff_library_format(p, head)
                        insp["encoding_map"][p] = enc
                    else:
                        fmt = "unknown"
                    entry["library_format"] = fmt
                    insp["library_candidates"].append(entry)
                if ext not in MANUSCRIPT_EXT and ext not in LIBRARY_EXT and not LIBRARY_HINT.search(fn):
                    insp["other_files"].append(entry)

    # 从稿件候选里再嗅探引用样式
    for c in insp["manuscript_candidates"]:
        if c["ext"] in (".md", ".txt", ".tex"):
            text, enc = read_text(c["path"], 60_000)
            if text:
                st = detect_style_from_text(text)
                if st != "unknown":
                    insp["citation_style_hint"] = st
                    break

    out = os.path.join(args.work, "inspection.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(insp, f, ensure_ascii=False, indent=2)
    print(f"[inspect_case] case_id={insp['case_id']} 材料={len(insp['material_files'])} "
          f"稿件候选={len(insp['manuscript_candidates'])} 文献库候选={len(insp['library_candidates'])} "
          f"样式={insp['citation_style_hint']}")
    for iss in insp["issues"]:
        print(f"[inspect_case][issue] {iss}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
