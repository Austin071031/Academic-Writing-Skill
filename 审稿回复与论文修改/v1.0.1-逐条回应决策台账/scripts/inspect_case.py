#!/usr/bin/env python3
"""inspect_case.py — 解析 case.json / task.md / 材料文件，生成 work/inspection.json。

审稿回复与论文修改专用：分别识别 基线稿件（manuscript-baseline）与 审稿意见（reviewer-comments）
两类候选文件，避免把意见当稿件、把稿件当意见。

用法: python3 inspect_case.py [--case /input/case.json] [--task /input/task.md]
                              [--input-dir /input] [--work /app/work]
只读输入；所有判断写入 inspection.json，供 SKILL.md 工作流与后续脚本消费。
"""
import argparse, json, os, re, sys, hashlib

TEXT_EXT = {".md", ".txt", ".tex", ".docx", ".pdf"}
BASELINE_HINT = re.compile(
    r"(baseline|manuscript|原稿|基线|稿件|论文|paper|draft|main|fulltext|revised|v\d+)", re.I)
COMMENT_HINT = re.compile(
    r"(reviewer|review|comment|审稿|评审|意见|返修|decision|referee)", re.I)
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
            "material_files": [], "baseline_candidates": [], "comment_candidates": [],
            "other_files": [], "constraints": {}, "output_contract": [],
            "language_hint": "unknown", "encoding_map": {}, "issues": [], "file_sha256": {}}

    case = {}
    if os.path.exists(args.case):
        try:
            with open(args.case, encoding="utf-8") as f:
                case = json.load(f)
            insp["case_id"] = case.get("case_id") or case.get("id") or case.get("caseId")
            for key in ("constraints", "requirements", "instructions", "genre", "audience",
                        "round", "revision_round", "journal"):
                if isinstance(case.get(key), (dict, list, str, int)):
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
                if ext not in TEXT_EXT:
                    insp["other_files"].append(entry)
                    continue
                if size == 0:
                    insp["issues"].append(f"空文件: {rel}")
                bscore, cscore = 0, 0
                if BASELINE_HINT.search(fn):
                    bscore += 10**9
                if COMMENT_HINT.search(fn):
                    cscore += 10**9
                # 内容嗅探：意见文件通常含 reviewer/审稿人 标记
                if ext in (".md", ".txt", ".tex") and 0 < size < 2_000_000:
                    head, _enc = read_text(p, 30_000)
                    if head:
                        if re.search(r"(reviewer\s*#?\s*\d|审稿人|评审意见|comments?\s+to)", head, re.I):
                            cscore += 5 * 10**8
                        if re.search(r"(摘要|abstract|引言|introduction|参考文献|references)", head, re.I):
                            bscore += 5 * 10**8
                entry["bscore"] = bscore + size
                entry["cscore"] = cscore + size
                insp["baseline_candidates"].append(entry)
                insp["comment_candidates"].append(entry)

    insp["baseline_candidates"].sort(key=lambda e: -e["bscore"])
    insp["comment_candidates"].sort(key=lambda e: -e["cscore"])
    # 同一文件不得同时充当两类角色：若第一名相同，把意见候选顺延
    if insp["baseline_candidates"] and insp["comment_candidates"]:
        if insp["baseline_candidates"][0]["path"] == insp["comment_candidates"][0]["path"]:
            if len(insp["comment_candidates"]) > 1:
                insp["comment_candidates"].pop(0)
            else:
                insp["issues"].append("基线稿件与审稿意见疑似同一文件，需人工确认输入布局")
    if not insp["baseline_candidates"]:
        insp["issues"].append("未找到基线稿件候选文件")
    if not insp["comment_candidates"]:
        insp["issues"].append("未找到审稿意见候选文件")

    for c in insp["baseline_candidates"][:1]:
        if c["ext"] in (".md", ".txt", ".tex"):
            text, enc = read_text(c["path"], 60_000)
            if text:
                insp["language_hint"] = detect_lang(text)
                insp["encoding_map"][c["path"]] = enc

    out = os.path.join(args.work, "inspection.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(insp, f, ensure_ascii=False, indent=2)
    b0 = insp["baseline_candidates"][0]["rel"] if insp["baseline_candidates"] else None
    c0 = insp["comment_candidates"][0]["rel"] if insp["comment_candidates"] else None
    print(f"[inspect_case] case_id={insp['case_id']} 材料={len(insp['material_files'])} "
          f"基线={b0} 意见={c0} 语言={insp['language_hint']}")
    for iss in insp["issues"]:
        print(f"[inspect_case][issue] {iss}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
