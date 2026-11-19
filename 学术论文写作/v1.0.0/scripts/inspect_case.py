#!/usr/bin/env python3
"""inspect_case.py — 预检：解析 /input/case.json 与 task.md，产出 brief.json，并立即写 result.json 保底骨架。

用法: python3 inspect_case.py --input /input --work /app/work --out /app/output
仅用标准库；任何异常都不得导致无输出。
"""
import argparse, json, os, re, sys, datetime

MATERIAL_EXT = {".pdf", ".csv", ".tsv", ".txt", ".md", ".docx", ".doc", ".json",
                ".png", ".jpg", ".jpeg", ".gif", ".webp", ".xlsx", ".xls", ".bib", ".ris"}

TASK_MODE_PATTERNS = [
    ("generate",  r"撰写|写作|生成|起草|写一|完成.*(章节|论文|摘要|稿)|draft|write|write[- ]?up|compose"),
    ("rewrite",   r"改写|重写|润色|压缩|扩写|换.*受众|rewrite|revise|polish|condense|expand"),
    ("proofread", r"校对|核验|核查|一致性|proofread|check|verify|consisten"),
    ("structure", r"结构化|整理|索引|组织|structur|organiz|index"),
    ("translate", r"翻译|双语|中英|英中|translat|bilingual"),
    ("citation",  r"引用|参考文献|citation|reference|bibliograph"),
    ("format",    r"格式|排版|模板|format|template|layout"),
]

SECTION_PATTERNS = [
    ("title",        r"标题|title"),
    ("abstract",     r"摘要|abstract"),
    ("keywords",     r"关键词|关键字|keywords?"),
    ("introduction", r"引言|前言|introduction"),
    ("methods",      r"方法|材料与方法|实验方法|methods?|methodology|materials?\s+and\s+methods?"),
    ("results",      r"结果|results?|findings?"),
    ("discussion",   r"讨论|discussion"),
    ("conclusion",   r"结论|conclusions?"),
    ("references",   r"参考文献|references?|bibliography"),
    ("acknowledg",   r"致谢|acknowledg"),
    ("data_avail",   r"数据可得性|数据可用性|data\s+availab"),
    ("figures",      r"图注|图\s*\d|figures?|captions?"),
    ("tables",       r"表格?|tables?"),
    ("appendix",     r"附录|appendix|supplement"),
    ("declarations", r"声明|declarations?|conflict|利益冲突|funding|资助"),
]

CITATION_STYLE_PATTERNS = [
    ("gbt7714",  r"GB/?T?\s*7714|国标|gb7714"),
    ("apa",      r"\bAPA\b"),
    ("ieee",     r"\bIEEE\b"),
    ("vancouver", r"vancouver|温哥华"),
    ("numeric",  r"顺序编码|数字编号|numbered|numeric"),
    ("author_year", r"著者.?出版年|author.?year"),
]

def read_text(path, limit=200000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except Exception:
        return ""

def find_case_json(input_dir):
    cand = os.path.join(input_dir, "case.json")
    if os.path.isfile(cand):
        return cand
    for root, _dirs, files in os.walk(input_dir):
        for fn in files:
            if fn.lower() == "case.json":
                return os.path.join(root, fn)
    return None

def scan_materials(input_dir, exclude_names):
    mats = []
    for root, _dirs, files in os.walk(input_dir):
        for fn in sorted(files):
            if fn.lower() in exclude_names:
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext in MATERIAL_EXT:
                p = os.path.join(root, fn)
                try:
                    size = os.path.getsize(p)
                except OSError:
                    size = -1
                mats.append({"path": p, "rel": os.path.relpath(p, input_dir),
                             "ext": ext, "size": size})
    mats.sort(key=lambda m: m["rel"])
    return mats

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)

    issues, case, case_id, contract = [], {}, None, []
    cj_path = find_case_json(args.input)
    if cj_path:
        try:
            case = json.loads(read_text(cj_path, 2_000_000) or "{}")
        except Exception as e:
            issues.append(f"case.json 解析失败: {e}")
            case = {}
    else:
        issues.append("缺少 case.json")
    if isinstance(case, dict):
        case_id = case.get("case_id") or case.get("id") or case.get("caseId")
        oc = case.get("output_contract") or case.get("outputContract")
        if isinstance(oc, list):
            contract = [str(x) for x in oc]
        elif isinstance(oc, dict):
            contract = [str(k) for k in oc.keys()]
        elif isinstance(oc, str):
            contract = [s.strip() for s in re.split(r"[,\s]+", oc) if s.strip()]
    if not case_id:
        case_id = "UNKNOWN-CASE"
        issues.append("case_id 未找到，使用占位 UNKNOWN-CASE")

    task_path = os.path.join(args.input, "task.md")
    task_text = read_text(task_path) if os.path.isfile(task_path) else ""
    if not task_text:
        issues.append("缺少 task.md 或内容为空")

    blob = task_text + "\n" + json.dumps(case, ensure_ascii=False)[:20000]
    modes = [m for m, pat in TASK_MODE_PATTERNS if re.search(pat, blob, re.I)]
    if not modes:
        modes = ["generate"]
        issues.append("未识别任务类型，默认 generate")
    sections = [s for s, pat in SECTION_PATTERNS if re.search(pat, blob, re.I)]
    cstyles = [c for c, pat in CITATION_STYLE_PATTERNS if re.search(pat, blob, re.I)]

    word_target = None
    m = re.search(r"(\d{3,6})\s*(?:字|词|words?|characters?)", blob, re.I)
    if m:
        word_target = int(m.group(1))
    language = "bilingual" if re.search(r"双语|bilingual", blob, re.I) else (
        "en" if re.search(r"英文|英语|in\s+English", blob, re.I) and not re.search(r"中文", blob) else
        "zh" if re.search(r"中文|汉语|Chinese", blob, re.I) else "auto")

    materials = scan_materials(args.input, {"case.json", "task.md"})
    if not materials:
        issues.append("/input 下未发现材料文件")

    brief = {
        "case_id": case_id,
        "created_utc": datetime.datetime.utcnow().isoformat() + "Z",
        "task_modes": modes,
        "required_sections": sections or ["title", "abstract", "introduction", "methods",
                                          "results", "discussion", "references"],
        "required_sections_inferred": not bool(sections),
        "word_target": word_target,
        "citation_style": (cstyles[0] if cstyles else "gbt7714"),
        "citation_style_inferred": not bool(cstyles),
        "language": language,
        "output_contract": contract,
        "materials": materials,
        "case_constraints": {k: v for k, v in case.items()
                             if k not in ("output_contract",) and isinstance(v, (str, int, float, bool, list))},
        "issues": issues,
    }
    with open(os.path.join(args.work, "brief.json"), "w", encoding="utf-8") as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)

    # 立即写 result.json 保底骨架（partial），后续阶段逐步填充
    skel = {
        "case_id": case_id,
        "status": "partial",
        "stage": "inspect_complete",
        "deliverables": {},
        "sources": [],
        "uncertainty": issues + ["骨架阶段：写作尚未完成"],
        "change_log": [],
        "generated_utc": datetime.datetime.utcnow().isoformat() + "Z",
    }
    for field in contract:
        if field not in skel:
            skel[field] = "unavailable: 流水线尚未完成，见 stage 字段"
    rj = os.path.join(args.out, "result.json")
    if not os.path.isfile(rj) or True:
        # 不覆盖已更进一步的 result.json
        cur = read_text(rj, 200000)
        if '"stage"' not in cur or '"inspect_complete"' in cur or not cur:
            with open(rj, "w", encoding="utf-8") as f:
                json.dump(skel, f, ensure_ascii=False, indent=2)

    log = os.path.join(args.out, "run_log.md")
    with open(log, "a", encoding="utf-8") as f:
        f.write(f"\n## inspect_case {brief['created_utc']}\n")
        f.write(f"- case_id={case_id}; modes={','.join(modes)}; style={brief['citation_style']}; "
                f"lang={language}; materials={len(materials)}; contract_fields={len(contract)}\n")
        for i in issues:
            f.write(f"- ISSUE: {i}\n")
    print(json.dumps({"ok": True, "case_id": case_id, "modes": modes,
                      "sections": brief["required_sections"], "materials": len(materials),
                      "contract_fields": contract, "issues": issues}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # 保底：异常也要留痕
        sys.stderr.write(f"inspect_case fatal: {e}\n")
        try:
            os.makedirs("/app/output", exist_ok=True)
            with open("/app/output/run_log.md", "a", encoding="utf-8") as f:
                f.write(f"\n## inspect_case FATAL {e}\n")
        except Exception:
            pass
        sys.exit(1)
