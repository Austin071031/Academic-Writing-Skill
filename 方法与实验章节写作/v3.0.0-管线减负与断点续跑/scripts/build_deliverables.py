#!/usr/bin/env python3
"""build_deliverables.py — 装配方法与实验章节与交付件，重写 result.json。

用法: python3 build_deliverables.py [--work /app/work] [--out /app/output]
Agent 在 work/ 下准备：
  sections/01_steps.md 02_setup.md 03_params.md 04_datasets.md 05_baselines.md 06_repro.md 07_limitations.md
  evidence_used.json（采信证据 eid 列表，可含手工补充行） table_rows.json（参数表行） gaps.json（缺口/追问）
  status.json（status/task_summary/stats） changes.json（变更记录） contract_extra.json（output_contract 附加字段）
产物（/app/output）：
  methods_chapter.md（含附录A参数表/附录B证据对照/附录C缺口清单）
  provenance_map.json build_report.json result.json
"""
import argparse, json, os, re, sys, datetime

SECTION_FILES = [
    ("steps", "1 方法步骤"),
    ("setup", "2 实验设置"),
    ("params", "3 参数与来源"),
    ("datasets", "4 数据集与划分"),
    ("baselines", "5 对照实验"),
    ("repro", "6 可复现清单"),
    ("limitations", "7 限制条件与适用范围"),
]
ANCHOR = re.compile(r"〔(E\d{3,4}|A\d{3,4})〕")

def load_json(p, default):
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[build][WARN] {p} 解析失败: {e}", file=sys.stderr)
    return default

def _load_reg(work):
    return load_json(os.path.join(work, "registration.json"), {})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    # --- 证据台账 ---
    cands = {}
    ecp = os.path.join(args.work, "evidence_candidates.jsonl")
    if os.path.exists(ecp):
        with open(ecp, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    cands[r["eid"]] = r
                except Exception:
                    pass
    reg = _load_reg(args.work)
    used = reg.get("evidence_used") if "evidence_used" in reg else load_json(os.path.join(args.work, "evidence_used.json"), [])
    if used is None:
        used = []
    ledger = {}
    for item in used:
        if isinstance(item, str) and item in cands:
            ledger[item] = cands[item]
        elif isinstance(item, dict) and item.get("eid"):
            ledger[item["eid"]] = {k: item.get(k) for k in ("eid", "source", "locator", "kind", "name", "value", "quote")}
    prov_path = os.path.join(args.out, "provenance_map.json")
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(list(ledger.values()), f, ensure_ascii=False, indent=2)

    # --- 章节装配 ---
    sections, missing_files, used_anchors, missing_anchors = [], [], set(), set()
    for idx, (key, title) in enumerate(SECTION_FILES, 1):
        candidates = [os.path.join(args.work, "sections", f"{idx:02d}_{key}.md"),
                      os.path.join(args.work, "sections", f"{key}.md")]
        p = next((c for c in candidates if os.path.exists(c)), None)
        if p is None:
            missing_files.append(key)
            sections.append((title, f"> ⚠ 本节材料不足，未生成。详见附录C缺口清单。\n"))
            continue
        with open(p, encoding="utf-8") as f:
            body = f.read().strip()
        for a in ANCHOR.findall(body):
            used_anchors.add(a)
            if a not in ledger:
                missing_anchors.add(a)
        sections.append((title, body))

    # --- 附录（v3.0.0：优先读单一 registration.json，分散文件为兼容回退） ---
    def pick(key, fname, default):
        if key in reg:
            return reg[key]
        return load_json(os.path.join(args.work, fname), default)
    table_rows = pick("table_rows", "table_rows.json", [])
    gaps = pick("gaps", "gaps.json", [])
    changes = pick("changes", "changes.json", [])
    status = pick("status", "status.json", {})
    contract_extra = pick("contract_extra", "contract_extra.json", {})

    lines = ["# 方法与实验章节", ""]
    lines.append(f"> 生成方式：本稿由 Skill 依据所供材料写成；句中 〔E#〕/〔A#〕 为证据锚点，附录B可逐条回溯；"
                 f"附录C列出材料缺口与需作者确认项。生成时间：{datetime.datetime.now(datetime.timezone.utc).isoformat()[:19]}Z")
    lines.append("")
    coverage = {}
    for title, body in sections:
        lines += [f"## {title}", "", body, ""]
        coverage[title.split()[0]] = len(body) > 40 and "⚠ 本节材料不足" not in body
    lines += ["## 附录A 参数表", "", "| 参数 | 取值 | 单位 | 作用对象 | 来源锚点 |", "|-|-|-|-|-|"]
    for r in table_rows:
        lines.append(f"| {r.get('name','')} | {r.get('value','')} | {r.get('unit','—')} | {r.get('scope','—')} | {r.get('source_eid','—')} |")
    if not table_rows:
        lines.append("| — | — | — | — | — |")
    lines += ["", "## 附录B 证据对照表", "", "| 锚点 | 来源文件 | 位置 | 类别 | 名称 | 取值 | 原文摘录 |", "|-|-|-|-|-|-|-|-|"]
    for eid in sorted(used_anchors):
        r = ledger.get(eid)
        if r:
            q = (r.get("quote") or "").replace("|", "\\|")[:120]
            lines.append(f"| {eid} | {r.get('source','')} | {r.get('locator','')} | {r.get('kind','')} | {r.get('name','')} | {r.get('value','')} | {q} |")
    lines += ["", "## 附录C 材料缺口与人工确认清单", ""]
    if gaps:
        lines += ["| 要素 | 缺口描述 | 严重度 | 追问作者 | 状态 |", "|-|-|-|-|-|"]
        for g in gaps:
            lines.append(f"| {g.get('element','')} | {str(g.get('desc','')).replace('|','/')} | {g.get('severity','')} | {str(g.get('question_for_author','')).replace('|','/')} | {g.get('status','')} |")
    else:
        lines.append("无：全部要素均有材料支撑。")
    lines.append("")
    chap_path = os.path.join(args.out, "methods_chapter.md")
    with open(chap_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # --- direction.json（方向元数据，§4-11：脚本必须真实读取） ---
    direction = {}
    dpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "direction.json")
    if os.path.exists(dpath):
        try:
            with open(dpath, encoding="utf-8") as f:
                direction = json.load(f)
        except Exception as e:
            print(f"[build][WARN] direction.json 解析失败: {e}", file=sys.stderr)

    # --- build_report ---
    report = {
        "direction": {k: direction.get(k) for k in ("name", "version", "mechanism", "engine_script") if direction.get(k)},
        "sections": {k: v for (k, v) in zip([s[0].split()[0] for s in SECTION_FILES],
                                            [c for _t, c in sections])},
        "coverage": coverage,
        "missing_section_files": missing_files,
        "anchors": {"used": len(used_anchors), "resolved": len(used_anchors & set(ledger)),
                    "missing": sorted(missing_anchors)},
        "table_rows": len(table_rows),
        "gaps_by_severity": {},
        "changes": len(changes),
    }
    for g in gaps:
        report["gaps_by_severity"][g.get("severity", "unknown")] = report["gaps_by_severity"].get(g.get("severity", "unknown"), 0) + 1
    rep_path = os.path.join(args.out, "build_report.json")
    with open(rep_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # --- result.json ---
    result = {
        "case_id": status.get("case_id", "unknown"),
        "status": status.get("status", "partial"),
        "skill": status.get("skill"),
        "task_summary": status.get("task_summary"),
        "outputs": {
            "methods_chapter": "methods_chapter.md",
            "provenance_map": "provenance_map.json",
            "build_report": "build_report.json",
        },
        "evidence_map": [{"eid": r.get("eid"), "source": r.get("source"),
                          "locator": r.get("locator"), "quote": (r.get("quote") or "")[:150]}
                         for r in ledger.values()],
        "change_log": changes,
        "uncertainty": [g for g in gaps if g.get("status") == "unresolved"],
        "manual_confirmations": [g for g in gaps if g.get("question_for_author")],
        "exceptions": status.get("exceptions", []),
        "stats": status.get("stats", {}),
        "sources": status.get("sources", {}),
        "output_contract_fields": status.get("output_contract_fields", []),
        "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    result.update(contract_extra)
    rp = os.path.join(args.out, "result.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[build] chapter={chap_path} anchors_used={len(used_anchors)} missing={sorted(missing_anchors)} gaps={len(gaps)}")

if __name__ == "__main__":
    sys.exit(main())
