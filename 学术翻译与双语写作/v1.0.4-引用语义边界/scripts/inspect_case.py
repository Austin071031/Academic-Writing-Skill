#!/usr/bin/env python3
"""inspect_case.py — 解析 case.json / task.md / 材料文件，生成 work/inspection.json。

翻译题扩展：从 task.md 嗅探翻译方向（en→zh / zh→en）、交付形态
（纯译文 pure / 双语对照 bilingual / 带修订标记 tracked）、目标语言与文体约束。

用法: python3 inspect_case.py [--case /input/case.json] [--task /input/task.md]
                              [--input-dir /input] [--work /app/work]
只读输入；所有判断写入 inspection.json，供 SKILL.md 工作流与后续脚本消费。
"""
import argparse, json, os, re, sys, hashlib

MANUSCRIPT_EXT = {".md", ".txt", ".tex", ".docx", ".pdf"}
MANUSCRIPT_HINT = re.compile(
    r"(manuscript|paper|draft|main|fulltext|source|稿件|论文|正文|原稿|原文|essay|thesis|article)", re.I)
SKIP_HINT = re.compile(r"(readme|license|config|metadata)", re.I)

def read_text(path, limit=400_000):
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

def sniff_translation_task(task_text, lang_hint):
    """从任务说明推断翻译方向与交付形态；无法确定时按材料语言给出默认并标注置信度。"""
    t = task_text or ""
    low = t.lower()
    info = {"direction": None, "target_lang": None, "source_lang": None,
            "output_form": None, "genre": None, "audience": None,
            "confidence": "low", "hints": []}
    if re.search(r"(英译中|翻译成中文|译为中文|译成中文|translate\s+(into|to)\s+chinese|"
                 r"chinese\s+translation|中文译文)", low):
        info.update(direction="en2zh", target_lang="zh", source_lang="en",
                    confidence="high")
        info["hints"].append("task.md 明示英译中")
    elif re.search(r"(中译英|翻译成英文|译为英文|译成英文|translate\s+(into|to)\s+english|"
                   r"english\s+translation|英文译文)", low):
        info.update(direction="zh2en", target_lang="en", source_lang="zh",
                    confidence="high")
        info["hints"].append("task.md 明示中译英")
    if re.search(r"(双语对照|中英对照|英中对照|bilingual|side[- ]by[- ]side|逐句对照|句段对照)", low):
        info["output_form"] = "bilingual"
        info["hints"].append("task.md 要求双语对照")
    elif re.search(r"(修订标记|修改痕迹|track(ed)?\s+changes|带批注|标注稿)", low):
        info["output_form"] = "tracked"
        info["hints"].append("task.md 要求修订标记")
    elif re.search(r"(纯译文|仅译文|translation\s+only|target[- ]only)", low):
        info["output_form"] = "pure"
        info["hints"].append("task.md 要求纯译文")
    # 未明示时按材料语言推断方向（默认：英译中为本题高频形态）
    if info["direction"] is None:
        if lang_hint == "en":
            info.update(direction="en2zh", target_lang="zh", source_lang="en")
            info["hints"].append("task.md 未明示方向；按材料为英文推断英译中（需 Agent 复核）")
        elif lang_hint == "zh":
            info.update(direction="zh2en", target_lang="en", source_lang="zh")
            info["hints"].append("task.md 未明示方向；按材料为中文推断中译英（需 Agent 复核）")
        else:
            info.update(direction="en2zh", target_lang="zh", source_lang="en")
            info["hints"].append("语言未知；暂按英译中处理（需 Agent 复核）")
    if info["output_form"] is None:
        info["output_form"] = "bilingual+pure"
        info["hints"].append("task.md 未限定形态；默认同时交付纯译文与双语对照")
    m = re.search(r"(摘要|abstract|全文|整篇|full\s+text|introduction|结论)", low)
    if m:
        info["scope_hint"] = m.group(1)
    return info

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
            "translation_task": {}, "encoding_map": {}, "issues": [], "file_sha256": {}}

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

    task_text = None
    if os.path.exists(args.task):
        insp["task_file"] = args.task
        task_text, enc = read_text(args.task)
        if task_text:
            insp["encoding_map"][args.task] = enc
            insp["task_head"] = task_text[:1500]
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
            + "（默认取第一个，可用 parse_manuscript.py --file 指定；若 task.md 指定对象以其为准）")

    for c in insp["manuscript_candidates"]:
        if c["ext"] in (".md", ".txt", ".tex"):
            text, enc = read_text(c["path"], 60_000)
            if text:
                insp["language_hint"] = detect_lang(text)
                insp["encoding_map"][c["path"]] = enc
                break

    insp["translation_task"] = sniff_translation_task(task_text, insp["language_hint"])

    out = os.path.join(args.work, "inspection.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(insp, f, ensure_ascii=False, indent=2)
    tt = insp["translation_task"]
    print(f"[inspect_case] case_id={insp['case_id']} 材料={len(insp['material_files'])} "
          f"稿件候选={len(insp['manuscript_candidates'])} 语言={insp['language_hint']} "
          f"方向={tt.get('direction')} 形态={tt.get('output_form')}")
    for iss in insp["issues"]:
        print(f"[inspect_case][issue] {iss}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
