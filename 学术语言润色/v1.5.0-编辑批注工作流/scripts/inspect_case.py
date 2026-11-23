#!/usr/bin/env python3
"""inspect_case.py — 阶段0预检：读取 /input/case.json 与 /input/task.md，盘点材料，提取润色约束。

用法: python3 inspect_case.py [--input-dir /input] [--work-dir /app/work]

只做读取与结构化，不做任何推断性改写。所有不确定项写入 issues。
输出: /app/work/brief.json
"""
import argparse, json, os, re, sys

TEXT_EXT = {".txt", ".md", ".markdown", ".tex", ".rst", ".json", ".csv", ".tsv",
            ".html", ".htm", ".xml", ".bib", ".log", ".yaml", ".yml"}
DOC_EXT = {".docx"}
PDF_EXT = {".pdf"}
UNSUPPORTED_EXT = {".doc", ".xls", ".ppt", ".pptx", ".xlsx"}


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f), None
    except Exception as e:
        return None, f"{path}: {e}"


def detect_encoding(path):
    """返回 (encoding, note)。note 非空表示发生过降级或替换。"""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "big5"):
        try:
            raw.decode(enc)
            return enc, ("" if enc.startswith("utf-8") else f"以 {enc} 解码（非 UTF-8，原编码已记录）")
        except UnicodeDecodeError:
            continue
    try:
        raw.decode("latin-1")
        return "latin-1", "无法识别编码，按 latin-1 读取，可能存在乱码，需人工确认"
    except Exception as e:  # pragma: no cover
        return None, f"编码检测失败: {e}"


def mojibake_score(text):
    """粗略检测 UTF-8 被按单字节解码后的乱码特征（如 娴嬭瘯 一类高频乱码字）。"""
    if not text:
        return 0.0
    sample = text[:4000]
    bad = sum(sample.count(ch) for ch in "娴嬮鎴愮珯鏂囨湰鐢ㄦ埛绠＄悊鏁版嵁搴撴潈闄愬畨鍏ㄦ祴璇曠被")
    return bad / max(len(sample), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default="/input")
    ap.add_argument("--work-dir", default="/app/work")
    args = ap.parse_args()

    os.makedirs(args.work_dir, exist_ok=True)
    issues = []

    case_path = os.path.join(args.input_dir, "case.json")
    task_path = os.path.join(args.input_dir, "task.md")
    case, err = read_json(case_path)
    if err:
        issues.append(f"case.json 读取失败: {err}")
        case = {}
    task_text = ""
    if os.path.exists(task_path):
        with open(task_path, "r", encoding="utf-8", errors="replace") as f:
            task_text = f.read()
    else:
        issues.append("task.md 不存在")

    case_id = (case.get("case_id") or case.get("id") or case.get("caseId")
               or case.get("task_id") or os.path.basename(args.input_dir.rstrip("/")) or "unknown")
    contract = (case.get("output_contract") or case.get("outputContract")
                or case.get("outputs") or case.get("output") or {})

    # ---- 任务约束的保守提取：只记录题面中出现的原文片段，不发明规则 ----
    hints = {"register": None, "language": None, "bilingual": False,
             "scope": None, "style_guide": None, "term_table_required": False,
             "raw_clauses": []}

    reg_patterns = [
        (r"期刊论文|期刊投稿|研究论文（?英文）?投稿", "期刊论文"),
        (r"学位论文|毕业论文|硕士论文|博士论文|thesis|dissertation", "学位论文"),
        (r"基金申请|项目申请|基金本子|proposal|申请书", "基金申请书"),
        (r"审稿|回复审稿|rebuttal|response letter|审稿意见", "审稿回复"),
        (r"英文摘要|abstract", "英文摘要"),
        (r"会议论文|conference paper", "会议论文"),
    ]
    for pat, label in reg_patterns:
        m = re.search(pat, task_text, re.I)
        if m:
            hints["register"] = label
            hints["raw_clauses"].append(m.group(0))
            break

    lang_zh = re.search(r"中文|汉语|Chinese", task_text)
    lang_en = re.search(r"英文|英语|English", task_text)
    if lang_zh and lang_en:
        hints["language"] = "中英双语/互译语境"
    elif lang_en:
        hints["language"] = "英文"
    elif lang_zh:
        hints["language"] = "中文"
    if re.search(r"中英对照|双语对照|逐句对照|side[- ]by[- ]side|parallel", task_text, re.I):
        hints["bilingual"] = True
    if re.search(r"术语表|术语统一|terminolog|glossary", task_text, re.I):
        hints["term_table_required"] = True
    m = re.search(r"(?:指定章节|范围|第[一二三四五六七八九十\d]+[章节部分]|摘要|引言|方法|结果|讨论|结论)[^\n]{0,120}", task_text)
    if m:
        hints["scope"] = m.group(0).strip()
    if re.search(r"风格指南|style guide|写作规范|体例", task_text, re.I):
        hints["style_guide"] = "题面提及风格指南/体例要求，需按 task.md 原文执行"

    # 任务正文本身也可能包含待润色原文（直接以文本形式给出）
    inline_text = case.get("text") or case.get("source_text") or case.get("manuscript") or case.get("draft")
    if isinstance(inline_text, str) and inline_text.strip():
        inline_path = os.path.join(args.input_dir, "_inline_case_text.md")
        with open(inline_path, "w", encoding="utf-8") as f:
            f.write(inline_text)
        issues.append("case.json 内嵌正文已转存为 _inline_case_text.md")

    # ---- 材料盘点 ----
    material_files = []
    for root, dirs, files in os.walk(args.input_dir):
        dirs.sort()
        for fn in sorted(files):
            if fn in ("case.json", "task.md"):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, args.input_dir)
            ext = os.path.splitext(fn)[1].lower()
            entry = {"path": p, "rel_path": rel, "ext": ext,
                     "size": os.path.getsize(p), "readable": os.access(p, os.R_OK)}
            if ext in TEXT_EXT or ext in DOC_EXT or ext in PDF_EXT:
                entry["kind"] = "text"
            elif ext in UNSUPPORTED_EXT:
                entry["kind"] = "unsupported"
                issues.append(f"{rel}: 格式 {ext} 无可靠的标准库提取手段，将如实标注为未处理")
            else:
                entry["kind"] = "unknown"
            if entry["kind"] == "text" and ext in TEXT_EXT:
                enc, note = detect_encoding(p)
                entry["encoding"] = enc
                if note:
                    entry["encoding_note"] = note
                    issues.append(f"{rel}: {note}")
                if enc:
                    try:
                        head = open(p, "r", encoding=enc, errors="replace").read(4000)
                        score = mojibake_score(head)
                        entry["mojibake_score"] = round(score, 4)
                        if score > 0.01:
                            issues.append(f"{rel}: 疑似编码混乱（mojibake_score={score:.3f}），需人工确认")
                    except Exception as e:
                        issues.append(f"{rel}: 读取抽样失败 {e}")
            material_files.append(entry)

    if not material_files:
        issues.append("除 case.json/task.md 外未发现材料文件；若正文内嵌于 case.json 已自动转存，否则属于材料缺失")

    brief = {
        "case_id": case_id,
        "output_contract": contract,
        "output_contract_keys": list(contract.keys()) if isinstance(contract, dict) else contract,
        "task_path": task_path,
        "task_length_chars": len(task_text),
        "task_hints": hints,
        "input_dir": args.input_dir,
        "material_count": len(material_files),
        "material_files": material_files,
        "issues": issues,
    }
    out = os.path.join(args.work_dir, "brief.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(brief, f, ensure_ascii=False, indent=2)
    print(f"[inspect_case] case_id={case_id} materials={len(material_files)} issues={len(issues)}")
    print(f"[inspect_case] hints={json.dumps({k: v for k, v in hints.items() if v and v is not False}, ensure_ascii=False)}")
    print(f"[inspect_case] contract keys: {brief['output_contract_keys']}")
    print(f"[inspect_case] brief -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
