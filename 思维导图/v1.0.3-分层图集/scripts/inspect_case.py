#!/usr/bin/env python3
"""inspect_case.py — 解析 case.json / task.md / 材料清单，生成 work/inspection.json。

用法: python3 inspect_case.py [--case /input/case.json] [--task /input/task.md]
                              [--input-dir /input] [--work /app/work]
只读输入；所有判断写入 inspection.json，供 SKILL.md 工作流与后续脚本消费。
思维导图专用：额外抽取受众、用途、材料类型线索与导图交付约束。
"""
import argparse, json, os, re, sys, hashlib

TEXT_EXT = {".md", ".txt", ".tex", ".rst", ".org", ".html", ".htm", ".csv", ".json", ".xml"}
BIN_EXT = {".pdf", ".docx", ".doc", ".pptx", ".xlsx"}
SKIP_NAMES = {"case.json", "task.md"}

PURPOSE_HINTS = [
    (re.compile(r"(文献梳理|论文|综述|paper|review|literature)", re.I), "论文与综述结构"),
    (re.compile(r"(实验|方案|变量|对照|步骤|experiment|protocol)", re.I), "实验与研究方案"),
    (re.compile(r"(项目|里程碑|任务|负责人|交付|风险|milestone|project)", re.I), "项目与任务计划"),
    (re.compile(r"(会议|纪要|议题|决议|待办|meeting|minutes)", re.I), "会议纪要"),
    (re.compile(r"(概念|知识体系|术语|concept|knowledge)", re.I), "知识体系与概念关系"),
]
AUDIENCE_HINT = re.compile(r"(受众|读者|面向|audience)[:：]?\s*([^\n。；;]{2,40})")
FORMAT_HINT = re.compile(r"(xmind|freemind|freeplane|opml|mermaid|markdown|markmap|导图格式|输出格式)[:：]?\s*([^\n。；;]{0,40})", re.I)

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--task", default="/input/task.md")
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    insp = {"case_id": None, "task_file": None, "task_head": None,
            "material_files": [], "skipped_files": [], "other_files": [],
            "constraints": {}, "output_contract": [],
            "purpose_hint": "通用", "audience_hint": None, "format_hint": None,
            "encoding_map": {}, "issues": [], "file_sha256": {}}

    case = {}
    if os.path.exists(args.case):
        try:
            with open(args.case, encoding="utf-8") as f:
                case = json.load(f)
            insp["case_id"] = case.get("case_id") or case.get("id") or case.get("caseId")
            for key in ("constraints", "requirements", "instructions", "materials"):
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
            insp["task_head"] = text[:2000]
            for rx, label in PURPOSE_HINTS:
                if rx.search(text):
                    insp["purpose_hint"] = label
                    break
            m = AUDIENCE_HINT.search(text)
            if m:
                insp["audience_hint"] = m.group(2).strip()
            m = FORMAT_HINT.search(text)
            if m:
                insp["format_hint"] = (m.group(1) + " " + (m.group(2) or "")).strip()[:60]
    else:
        insp["issues"].append("task.md 不存在")

    # 材料文件清点（跳过任务说明与案例描述本身）
    if os.path.isdir(args.input_dir):
        for root, _dirs, files in os.walk(args.input_dir):
            for fn in sorted(files):
                p = os.path.join(root, fn)
                rel = os.path.relpath(p, args.input_dir)
                ext = os.path.splitext(fn)[1].lower()
                entry = {"path": p, "rel": rel, "ext": ext, "size": os.path.getsize(p)}
                try:
                    h = hashlib.sha256()
                    with open(p, "rb") as f:
                        for chunk in iter(lambda: f.read(65536), b""):
                            h.update(chunk)
                    insp["file_sha256"][rel] = h.hexdigest()
                except OSError as e:
                    insp["issues"].append(f"无法读取 {rel}: {e}")
                if fn in SKIP_NAMES:
                    insp["skipped_files"].append(entry)
                    continue
                if ext in TEXT_EXT or ext in BIN_EXT or ext == "":
                    insp["material_files"].append(entry)
                else:
                    insp["other_files"].append(entry)

    if not insp["material_files"]:
        insp["issues"].append("未发现可用材料文件（仅找到 case.json/task.md）")

    path = os.path.join(args.work, "inspection.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(insp, f, ensure_ascii=False, indent=2)
    print(f"[inspect] case_id={insp['case_id']} 材料={len(insp['material_files'])} "
          f"用途线索={insp['purpose_hint']} issues={len(insp['issues'])} -> {path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
