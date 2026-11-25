#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""assemble_result.py --work W --out O --skill "name vX.Y.Z" --status success|partial|failed

组装 result.json：case_id、status、skill、outputs、evidence_map、
change_log/uncertainty/manual_confirmations/exceptions/stats、
output_contract 回填（dict→逐键 {artifact, note}；list→逐字段同法；
无对应产物填 null + note，不臆填）。

v2.0.2 补丁：回填 output_contract 时优先读 work/contract_map.json
（contract_check.py 产物，缺失则走原有关键词映射逻辑，默认行为兼容）。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "assemble_result"

# output_contract 键名 → 最相关输出（O 下相对路径 / 结构引用）
CONTRACT_RULES = [
    (re.compile(r"draft|稿", re.I), "proposal_draft.md"),
    (re.compile(r"mapping|对照", re.I), "element_mapping.md"),
    (re.compile(r"report|报告", re.I), "report.md"),
    (re.compile(r"evidence|溯源", re.I), "evidence_map"),
    (re.compile(r"preview|预览", re.I), "preview.html"),
]

OUTPUT_DESC = {
    "result.json": "结构化结果（契约字段回填、evidence_map、change_log）",
    "proposal_draft.md": "申请书章节稿（清洁版，无标记）",
    "proposal_annotated.md": "留痕稿（D-Pxxx + 〔F…〕〔拟〕〔确认〕）",
    "element_mapping.md": "要素对照说明（七要素 × 段落 × 证据 × 状态）",
    "report.md": "质量报告（覆盖表 / findings 统计 / 限制）",
    "preview.html": "三栏预览（report/draft/mapping）",
    "preview.pdf": "预览 PDF（尽力渲染）",
    "preview_skipped.txt": "PDF 渲染跳过说明",
}


def build_evidence_map(work):
    draft = gu.read_json(os.path.join(work, "draft.json"), {"paragraphs": []}) or {}
    ledger = gu.read_json(os.path.join(work, "fact_ledger.json"),
                          {"entries": []}) or {}
    by_fid = {e.get("fid"): e for e in ledger.get("entries", [])
              if isinstance(e, dict)}
    fid_re = re.compile(r"〔(F\d+)〕")
    out = []
    for p in draft.get("paragraphs", []):
        fids = sorted(set(fid_re.findall(p.get("text", ""))))
        sources = []
        for f in fids:
            e = by_fid.get(f)
            if e and isinstance(e.get("source"), dict):
                src = e["source"]
                if src not in sources:
                    sources.append(src)
        excerpt = re.sub(r"〔[^〕]*〕", "", p.get("text", ""))
        excerpt = re.sub(r"\s+", " ", excerpt).strip()[:80]
        out.append({"dpid": p.get("dpid"), "element": p.get("element"),
                    "text_excerpt": excerpt, "fids": fids, "sources": sources})
    return out


def match_contract_artifact(key, out_dir):
    for pat, artifact in CONTRACT_RULES:
        if pat.search(str(key)):
            if artifact == "evidence_map":
                return "evidence_map", "见 result.json 的 evidence_map 字段"
            if os.path.exists(os.path.join(out_dir, artifact)):
                return artifact, ""
            return None, f"约定产物 {artifact} 缺失，见 report.md"
    return None, "见 report.md"


def contract_entry(key, out_dir, contract_map):
    """单个契约字段回填：优先 contract_map.json，缺失则走原关键词映射。"""
    if isinstance(contract_map, dict):
        entry = contract_map.get(key)
        if isinstance(entry, dict) and "artifact" in entry:
            return {"artifact": entry.get("artifact"),
                    "note": entry.get("note") or f"对应产物 {entry.get('artifact')}"}
    artifact, note = match_contract_artifact(key, out_dir)
    return {"artifact": artifact, "note": note or f"对应产物 {artifact}"}


def fill_contract(work, out_dir):
    contract_map = gu.read_json(os.path.join(work, "contract_map.json"), None)
    case = gu.read_json(os.path.join(gu.env_input_dir(), "case.json"), None)
    if case is None:
        insp = gu.read_json(os.path.join(work, "inspection.json"), {}) or {}
        fields = insp.get("output_contract_fields") or []
        contract = {k: None for k in fields} if fields else None
    elif isinstance(case, dict):
        contract = case.get("output_contract")
    else:
        contract = None
        for item in case:
            if isinstance(item, dict) and "output_contract" in item:
                contract = item["output_contract"]
                break

    if isinstance(contract, dict):
        filled = {}
        for k in contract:
            filled[k] = contract_entry(k, out_dir, contract_map)
        return filled
    if isinstance(contract, list):
        filled = []
        for item in contract:
            key = item if isinstance(item, str) else (
                item.get("field") or item.get("name") or item.get("key")
                if isinstance(item, dict) else None)
            if key is None:
                continue
            entry = contract_entry(key, out_dir, contract_map)
            filled.append({"field": key, "artifact": entry["artifact"],
                           "note": entry["note"]})
        return filled
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--skill", default="grant-writing")
    ap.add_argument("--status", default="success",
                    choices=["success", "partial", "failed"])
    args = ap.parse_args()
    work, out = args.work, gu.env_output_dir(args.out)

    def work_json(name, default):
        v = gu.read_json(os.path.join(work, name), default)
        return default if v is None else v

    inspection = work_json("inspection.json", {})
    case_id = inspection.get("case_id") or "unknown"
    stats = work_json("stats.json", {})

    outputs = {}
    try:
        for name in sorted(os.listdir(out)):
            if name in ("result.json",) or name.startswith("."):
                continue
            full = os.path.join(out, name)
            if os.path.isfile(full):
                outputs[name] = {"desc": OUTPUT_DESC.get(name, ""),
                                 "size": os.path.getsize(full)}
    except Exception as e:
        gu.record_exception(work, STAGE, out, e, "outputs 清单为空")

    result = {
        "case_id": case_id,
        "status": args.status,
        "skill": args.skill,
        "outputs": outputs,
        "evidence_map": build_evidence_map(work),
        "change_log": work_json("change_log.json", []),
        "uncertainty": work_json("uncertainty.json", {}),
        "manual_confirmations": work_json("manual_confirmations.json", []),
        "exceptions": work_json("exceptions.json", []),
        "stats": stats,
    }
    contract = fill_contract(work, out)
    if contract is not None:
        result["output_contract"] = contract

    gu.write_json(os.path.join(out, "result.json"), result)
    print(f"[assemble_result] case_id={case_id} status={args.status} "
          f"outputs={len(outputs)} evidence_map={len(result['evidence_map'])}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[assemble_result] ERROR: {e}")
        raise SystemExit(1)
