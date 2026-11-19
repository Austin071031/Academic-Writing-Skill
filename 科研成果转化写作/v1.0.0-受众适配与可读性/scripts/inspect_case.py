#!/usr/bin/env python3
"""inspect_case.py — 解析 case.json / task.md / 材料文件，生成 work/inspection.json。

用法: python3 inspect_case.py [--case /input/case.json] [--task /input/task.md]
                              [--input-dir /input] [--work /app/work]
只读输入；所有判断写入 inspection.json，供 SKILL.md 工作流与后续脚本消费。
成果转化写作特化：识别源文稿件、事实底稿/数据材料、受众（audience）、目标文体（genre）、
篇幅约束（length_limit）、语言与格式要求；为每个文件计算 sha256 供溯源。
"""
import argparse, json, os, re, sys, hashlib

MANUSCRIPT_EXT = {".md", ".txt", ".tex", ".docx", ".pdf"}
DATA_EXT = {".json", ".csv", ".tsv", ".yaml", ".yml"}
SOURCE_HINT = re.compile(r"(source|original|paper|manuscript|draft|abstract|源文|原文|论文|稿件|摘要|正文|底稿|report|技术报告)", re.I)
FACT_HINT = re.compile(r"(fact|factsheet|material|data|note|事实|材料|数据|笔记|摘录|要点)", re.I)

AUDIENCE_PATTERNS = [
    (re.compile(r"(公众|大众|科普|普通读者|非专业|lay\s*audience|general\s*public)", re.I), "公众/科普读者"),
    (re.compile(r"(中学生|高中生|本科生|学生读者)", re.I), "学生读者"),
    (re.compile(r"(投资人|投资机构|风投|VC|天使|商业|产业界|企业)", re.I), "投资人/产业界"),
    (re.compile(r"(政策|政府|管理部门|决策者|领导)", re.I), "政策制定者/管理者"),
    (re.compile(r"(评审|基金委|项目申报|申报书|立项)", re.I), "项目评审专家"),
    (re.compile(r"(跨学科|交叉学科|其他领域|非本领域)", re.I), "跨学科同行"),
    (re.compile(r"(同行|领域专家|学术读者|研究者)", re.I), "本领域同行"),
]
GENRE_PATTERNS = [
    (re.compile(r"(科普文章|科普|公众号|大众传媒|popular\s*science)", re.I), "科普文章"),
    (re.compile(r"(新闻稿|新闻通稿|媒体报道|press\s*release|news)", re.I), "新闻通稿"),
    (re.compile(r"(项目申报|申报书|基金申请|立项依据|proposal)", re.I), "项目申报材料"),
    (re.compile(r"(技术报告|technical\s*report)", re.I), "技术报告"),
    (re.compile(r"(摘要|abstract)", re.I), "摘要"),
    (re.compile(r"(海报|poster)", re.I), "学术海报"),
    (re.compile(r"(简报|简报材料|一页纸|brief)", re.I), "简报"),
    (re.compile(r"(专利|patent)", re.I), "专利文本"),
    (re.compile(r"(双语|英文版|翻译|中英|bilingual|english\s*version)", re.I), "双语/翻译产物"),
]
LENGTH_PATTERN = re.compile(
    r"(?:篇幅|字数|长度|不超过|控制在|限定|上限|limit|within|at\s+most|no\s+more\s+than)"
    r"[^0-9０-９]{0,12}([0-9０-９]{2,6})\s*(字|词|字符|words?|characters?|字以内|字左右)?", re.I)

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

def detect_audience(text):
    for pat, label in AUDIENCE_PATTERNS:
        if pat.search(text):
            return label
    return "unspecified"

def detect_genre(text):
    hits = []
    for pat, label in GENRE_PATTERNS:
        if pat.search(text):
            hits.append(label)
    return hits

def detect_length(text):
    m = LENGTH_PATTERN.search(text)
    if not m:
        return None
    raw = m.group(1)
    raw = raw.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    unit = m.group(2) or "字"
    try:
        return {"value": int(raw), "unit": unit, "raw": m.group(0)[:80]}
    except ValueError:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--task", default="/input/task.md")
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    insp = {"case_id": None, "task_file": None, "task_head": None,
            "audience": "unspecified", "genre": [], "length_limit": None,
            "material_files": [], "source_candidates": [], "fact_candidates": [],
            "other_files": [], "constraints": {}, "output_contract": [],
            "language_hint": "unknown", "encoding_map": {},
            "issues": [], "file_sha256": {}}

    case = {}
    if os.path.exists(args.case):
        try:
            with open(args.case, encoding="utf-8") as f:
                case = json.load(f)
            insp["case_id"] = case.get("case_id") or case.get("id") or case.get("caseId")
            for key in ("constraints", "requirements", "instructions", "audience",
                        "genre", "target_audience", "target_genre", "length", "length_limit"):
                if case.get(key) is not None:
                    insp["constraints"][key] = case.get(key)
            oc = case.get("output_contract") or case.get("outputContract") or {}
            if isinstance(oc, dict):
                insp["output_contract"] = [{"name": k, "spec": v} for k, v in oc.items()]
            elif isinstance(oc, list):
                insp["output_contract"] = oc
            if isinstance(case.get("audience"), str):
                insp["audience"] = case["audience"]
            if isinstance(case.get("genre"), str):
                insp["genre"].append(case["genre"])
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
            if insp["audience"] == "unspecified":
                insp["audience"] = detect_audience(text)
            for g in detect_genre(text):
                if g not in insp["genre"]:
                    insp["genre"].append(g)
            if insp["length_limit"] is None:
                insp["length_limit"] = detect_length(text)
            if len(re.findall(r"[一-鿿]", text)) > 50:
                insp["language_hint"] = "zh"
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
                if ext in MANUSCRIPT_EXT and SOURCE_HINT.search(fn):
                    insp["source_candidates"].append(entry)
                    continue
                if (ext in DATA_EXT or ext in (".md", ".txt")) and FACT_HINT.search(fn):
                    insp["fact_candidates"].append(entry)
                    continue
                if ext in MANUSCRIPT_EXT:
                    insp["source_candidates"].append(entry)
                elif ext in DATA_EXT:
                    insp["fact_candidates"].append(entry)
                else:
                    insp["other_files"].append(entry)

    for c in insp["source_candidates"]:
        if c["ext"] in (".md", ".txt", ".tex"):
            text, _enc = read_text(c["path"], 60_000)
            if text and insp["language_hint"] == "unknown":
                n_zh = len(re.findall(r"[一-鿿]", text))
                n_la = len(re.findall(r"[a-zA-Z]", text))
                insp["language_hint"] = "zh" if n_zh > max(50, n_la // 2) else ("en" if n_la > 200 else "unknown")
            break

    if insp["audience"] == "unspecified":
        insp["issues"].append("未识别到明确受众：按通用科普读者处理，并记入 manual_confirmations")
    if not insp["genre"]:
        insp["issues"].append("未识别到目标文体：按科普文章模板处理，并记入 manual_confirmations")

    out = os.path.join(args.work, "inspection.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(insp, f, ensure_ascii=False, indent=2)
    print(f"[inspect_case] case_id={insp['case_id']} 材料={len(insp['material_files'])} "
          f"源文候选={len(insp['source_candidates'])} 事实材料={len(insp['fact_candidates'])} "
          f"受众={insp['audience']} 文体={insp['genre']} 篇幅={insp['length_limit']} 语言={insp['language_hint']}")
    for iss in insp["issues"]:
        print(f"[inspect_case][issue] {iss}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
