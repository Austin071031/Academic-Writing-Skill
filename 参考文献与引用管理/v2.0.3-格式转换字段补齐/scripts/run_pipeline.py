#!/usr/bin/env python3
"""run_pipeline.py — 格式转换与字段补齐编排器（v2.0.3），全自动单命令。

v2.0.3 唯一机制增量（父版 v1.0.3，attempt 89252，49 分，五方向最低）：本方向判断环节
本就为零（转换是确定性的），把目标规范识别也脚本化——从 task.md 关键词自动判定
GB/T 7714 顺序编码 / 著者-出版年 / APA 7 / Vancouver，一条命令完成全部转换+审计+组装，
消除任何"流程没走完"的可能。

用法: python3 scripts/run_pipeline.py [--input /input] [--work /app/work] [--out /app/output]
                                     [--to gbt2015_numeric|gbt2015_author|apa7|vancouver]
"""
import argparse, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    for line in ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-3:]:
        print("  |", line)
    return r

def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

STYLE_RULES = [
    (re.compile(r"GB/?T\s*7714.{0,20}(著者|author[ -]?date)|著者[—-]出版年", re.I), "gbt2015_author"),
    (re.compile(r"GB/?T\s*7714|国标|顺序编码|numeric", re.I), "gbt2015_numeric"),
    (re.compile(r"APA", re.I), "apa7"),
    (re.compile(r"Vancouver|温哥华|IEEE", re.I), "vancouver"),
]

def detect_style(task_text, inspection):
    for pat, style in STYLE_RULES:
        if pat.search(task_text):
            return style, f"task.md 命中规则: {pat.pattern[:40]}"
    hint = (inspection.get("constraints") or {}).get("style_mentioned")
    if hint:
        for pat, style in STYLE_RULES:
            if pat.search(str(hint)):
                return style, f"案例约束字段命中: {hint}"
    return "gbt2015_numeric", "任务书未指明，默认 GB/T 7714—2015 顺序编码制（记 uncertainty）"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="/input")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--to", default="auto")
    ap.add_argument("--skill", default="ref-format-converter v2.0.3")
    args = ap.parse_args()
    W, O = args.work, args.out
    os.makedirs(W, exist_ok=True); os.makedirs(O, exist_ok=True)

    print("== [1/4] init_result / inspect_case / parse_library")
    run(["python3", f"{HERE}/init_result.py", "--case", f"{args.input}/case.json", "--out", O])
    run(["python3", f"{HERE}/inspect_case.py", "--case", f"{args.input}/case.json",
         "--task", f"{args.input}/task.md", "--input-dir", args.input, "--work", W])
    insp = load_json(os.path.join(W, "inspection.json"), {}) or {}
    lib_cands = [c["path"] for c in insp.get("library_candidates", [])
                 if c.get("library_format") not in ("pdf", "docx")]
    if not lib_cands:
        lib_cands = [c["path"] for c in insp.get("manuscript_candidates", [])]
    if lib_cands:
        run(["python3", f"{HERE}/parse_library.py"] + lib_cands + ["--work", W])
    else:
        save_json(os.path.join(W, "library.json"), {"records": [], "issues": ["无文献库"], "count": 0})
    lib = load_json(os.path.join(W, "library.json"), {}) or {}
    n = len(lib.get("records", []))

    print("== [2/4] 目标规范识别 + convert_engine")
    task_text = ""
    if os.path.exists(f"{args.input}/task.md"):
        task_text = open(f"{args.input}/task.md", encoding="utf-8", errors="ignore").read()
    style, basis = (args.to, "命令行指定") if args.to != "auto" else detect_style(task_text, insp)
    print(f"  | 目标规范: {style}（{basis}）")
    lib_path = os.path.join(W, "library.json")
    if n:
        run(["python3", f"{HERE}/convert_engine.py", "--library", lib_path,
             "--to", style, "--outdir", O, "--work", W])
        # 回转导出 bibtex/ris（可复用性交付）
        run(["python3", f"{HERE}/cite_engine.py", "convert", "--library", lib_path,
             "--to", "bibtex", "--out", os.path.join(O, "converted.bib")])
        run(["python3", f"{HERE}/cite_engine.py", "convert", "--library", lib_path,
             "--to", "ris", "--out", os.path.join(O, "converted.ris")])
    else:
        save_json(os.path.join(W, "exceptions.json"), ["无文献库记录，无法转换"])

    print("== [3/4] 证据与统计")
    audit = load_json(os.path.join(O, "field_audit.json"), []) or []
    missing = [a for a in audit if a.get("missing_fields")] if isinstance(audit, list) else []
    save_json(os.path.join(W, "evidence_map.json"),
              [{"entry_id": a.get("rid"), "location": a.get("source_file", "library"),
                "source": f"目标规范 {style}", "support": basis,
                "rationale": f"缺字段 {a.get('missing_fields') or '无'}；"
                             f"补齐 {a.get('fills') or '无'}"} for a in audit]
              if isinstance(audit, list) else [])
    save_json(os.path.join(W, "stats.json"),
              {"n_records": n, "target_style": style, "style_basis": basis,
               "n_entries_missing_fields": len(missing)})
    if "未指明" in basis:
        save_json(os.path.join(W, "uncertainty.json"),
                  [f"目标规范{basis}；若案例实际要求其他规范，请用 --to 重跑"])

    print("== [4/4] assemble / validate / preview")
    status = "success" if n else "partial"
    run(["python3", f"{HERE}/assemble_result.py", "--work", W, "--out", O,
         "--case", f"{args.input}/case.json", "--skill", args.skill, "--status", status])
    rv = run(["python3", f"{HERE}/validate_output.py", "--out", O])
    run(["python3", f"{HERE}/render_previews.py", "--out", O])
    print("[run_pipeline] DONE")
    return 0 if rv.returncode == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
