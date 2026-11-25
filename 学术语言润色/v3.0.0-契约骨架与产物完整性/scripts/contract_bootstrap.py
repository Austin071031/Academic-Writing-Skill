#!/usr/bin/env python3
"""contract_bootstrap.py — 契约骨架：让交付完整性不依赖 Agent 的记性（v3.0.0 唯一脚本）。

用法:
  python3 contract_bootstrap.py init     [--input-dir /input] [--work-dir /app/work] [--output-dir /app/output]
  python3 contract_bootstrap.py finalize [--work-dir /app/work] [--output-dir /app/output]

init:     读 case.json/task.md → 写 result.json 骨架（case_id + output_contract 全键 +
          null_reason 占位）+ 材料清单与编码状况 material_report.json。
finalize: 扫描 /app/output 现有产物，按名称模糊映射填充 output_contract 各键
          （Agent 可用 /app/work/contract_map.json 显式覆盖），校验必备产物清单，
          判定 status（complete/partial/failed）并写 selfcheck.json。
仅标准库；任何失败都如实记录，不阻断流程。
"""
import argparse, datetime, json, os, re, sys

REQUIRED = ["polished.md", "change_log.md", "terminology_table.md"]
ALIAS = {
    "polished.md": {"polished", "text", "manuscript", "fulltext", "revised", "final", "正文", "全文"},
    "change_log.md": {"change", "log", "changes", "changelog", "修改", "清单", "cards"},
    "terminology_table.md": {"terminology", "terms", "glossary", "term", "术语"},
    "sentence_alignment.md": {"bilingual", "alignment", "parallel", "双语", "对照", "sentence"},
    "conservation_check.md": {"conservation", "守恒", "check"},
    "diff.html": {"diff", "对照", "preview"},
}


def tokens(s):
    return set(re.findall(r"[a-z0-9一-鿿]+", str(s).lower()))


def detect_encoding(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "big5"):
        try:
            raw.decode(enc)
            return enc, ""
        except UnicodeDecodeError:
            continue
    return "latin-1", "无法识别编码，按 latin-1 读取，可能乱码"


def cmd_init(args):
    os.makedirs(args.work_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)
    issues = []
    case = {}
    try:
        case = json.load(open(os.path.join(args.input_dir, "case.json"), encoding="utf-8"))
    except Exception as e:
        issues.append(f"case.json 读取失败: {e}")
    case_id = case.get("case_id") or case.get("id") or "unknown"
    contract = case.get("output_contract") or case.get("outputContract") or case.get("outputs") or {}
    if not os.path.exists(os.path.join(args.input_dir, "task.md")):
        issues.append("task.md 不存在")

    materials = []
    for root, dirs, files in os.walk(args.input_dir):
        dirs.sort()
        for fn in sorted(files):
            if fn in ("case.json", "task.md"):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, args.input_dir)
            ext = os.path.splitext(fn)[1].lower()
            entry = {"rel_path": rel, "ext": ext, "size": os.path.getsize(p)}
            if ext in (".txt", ".md", ".markdown", ".tex", ".rst", ".csv", ".tsv",
                       ".json", ".html", ".xml", ".bib", ".log", ".yaml", ".yml"):
                enc, note = detect_encoding(p)
                entry["encoding"] = enc
                if note:
                    entry["note"] = note
                    issues.append(f"{rel}: {note}")
            elif ext not in (".docx", ".pdf"):
                entry["note"] = "非文本格式，需用对应工具提取；失败须标注"
            materials.append(entry)
    if not materials:
        issues.append("未发现材料文件（除 case.json/task.md）")

    json.dump({"materials": materials, "issues": issues},
              open(os.path.join(args.work_dir, "material_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    oc = ({k: {"spec": v, "delivered": None, "null_reason": "处理中，尚未填充"}
           for k, v in contract.items()} if isinstance(contract, dict) else {})
    result = {"case_id": case_id, "status": "in_progress",
              "generated_by": "academic-polish-surgical v3.0.0 (weekly-skill)",
              "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "output_contract": oc, "artifacts": {},
              "sources": [m["rel_path"] for m in materials],
              "assumptions": [], "uncertainty": issues, "manual_review_required": [],
              "change_records": {}}
    json.dump(result, open(os.path.join(args.output_dir, "result.json"), "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[bootstrap init] case_id={case_id} contract_keys={list(oc)} "
          f"materials={len(materials)} issues={len(issues)}")


def cmd_finalize(args):
    rp = os.path.join(args.output_dir, "result.json")
    result = json.load(open(rp, encoding="utf-8")) if os.path.exists(rp) else {}
    problems, warnings = [], []

    present = {f for f in os.listdir(args.output_dir) if os.path.isfile(os.path.join(args.output_dir, f))}
    cmap = {}
    cm_p = os.path.join(args.work_dir, "contract_map.json")
    if os.path.exists(cm_p):
        try:
            cmap = json.load(open(cm_p, encoding="utf-8"))
        except Exception:
            pass
    art_tokens = {}
    for f in present:
        t = tokens(f) | tokens(os.path.splitext(f)[0])
        for canon, alias in ALIAS.items():
            if t & alias or f == canon:
                t |= alias
        art_tokens[f] = t

    oc = result.get("output_contract") or {}
    for key in oc:
        if not isinstance(oc[key], dict):
            oc[key] = {"spec": oc[key], "delivered": None, "null_reason": "处理中，尚未填充"}
        fname = cmap.get(key)
        if fname and fname not in present:
            warnings.append(f"contract_map 中 '{key}' 指向不存在的文件 {fname}")
            fname = None
        if fname is None:
            kt = tokens(key)
            best, bs = None, 0.0
            for f, at in art_tokens.items():
                if not kt & at:
                    continue
                sc = len(kt & at) / max(len(kt), 1)
                if sc > bs:
                    best, bs = f, sc
            fname = best if bs >= 0.5 else None
        if fname:
            oc[key]["delivered"] = fname
            oc[key]["artifact_path"] = os.path.abspath(os.path.join(args.output_dir, fname))
            oc[key].pop("null_reason", None)

    for req in REQUIRED:
        if req not in present:
            problems.append(f"必备产物缺失: {req}")
    unfilled = [k for k, v in oc.items() if isinstance(v, dict)
                and v.get("delivered") is None and not v.get("null_reason")]
    if unfilled:
        problems.append(f"契约字段未交付且无 null_reason: {unfilled}")
    if not result.get("case_id") or result["case_id"] == "unknown":
        problems.append("result.json 缺少有效 case_id")

    status = "complete" if not problems else (
        "partial" if "polished.md" in present else "failed")
    result["status"] = status
    result.setdefault("artifacts", {}).update(
        {os.path.splitext(f)[0]: f for f in sorted(present) if f != "result.json"})
    json.dump(result, open(rp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump({"status": status, "problems": problems, "warnings": warnings,
               "delivered": {k: v.get("delivered") for k, v in oc.items() if isinstance(v, dict)}},
              open(os.path.join(args.work_dir, "selfcheck.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"[bootstrap finalize] status={status} problems={len(problems)} warnings={len(warnings)}")
    for p in problems:
        print("  PROBLEM:", p)
    return 0 if not problems else 1


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("init", cmd_init), ("finalize", cmd_finalize)):
        p = sub.add_parser(name)
        p.add_argument("--input-dir", default="/input")
        p.add_argument("--work-dir", default="/app/work")
        p.add_argument("--output-dir", default="/app/output")
        p.set_defaults(fn=fn)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
