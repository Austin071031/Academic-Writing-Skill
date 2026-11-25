#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_result.py — Assemble the final /app/output/result.json.

Rules (from the runtime contract):
  * result.json MUST contain `case_id` and every field of the case's original
    `output_contract` (values filled with real deliverable references).
  * Honest status (success / partial / failed), sources, uncertainty and a
    unit-level change log must be included.
  * Never fabricate: any stage that did not run is reported as such.

Usage:
    python3 build_result.py --plan /app/work/plan.json --work /app/work \
        --outdir /app/output [--adapted manuscript_adapted.docx]

Stdlib only.
"""
import argparse
import glob
import json
import os
import sys

STAGE_FILES = ["stage_inspect.json", "stage_measure.json", "stage_spec.json",
               "stage_adapt.json", "stage_fidelity.json", "stage_compliance.json",
               "stage_render.json"]


def _load(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


ALIASES = {
    "editable_docx": ["docx", "adapted", "manuscript", "document", "draft", "paper",
                      "editable", "source", "成稿", "稿件", "可编辑", "word"],
    "rendered_pdf": ["pdf", "rendered", "render", "预览pdf", "导出"],
    "preview_png": ["png", "preview", "image", "截图", "预览图"],
    "spec_json": ["spec", "specification", "规格", "格式规格", "structured"],
    "checklist_md": ["checklist", "检查项", "清单", "检查单"],
    "compliance_md": ["compliance", "合规", "符合", "核查"],
    "fidelity_md": ["fidelity", "保真", "一致性", "完整性", "diff"],
    "changelog_json": ["change", "changelog", "changes", "修改记录", "变更", "log"],
    "result_json": ["result", "结果", "summary", "汇总"],
}


def fill_contract(contract, deliverables_map, type_paths=None):
    """Return {field: value} honoring the contract's shape.

    Matching order: exact key -> normalized containment -> word-overlap
    scoring over semantic aliases of deliverable types.
    """
    import re as _re
    filled = {}
    tp = dict(type_paths or {})

    def _norm(s):
        return _re.sub(r"[^a-z0-9一-鿿]", "", str(s).lower())

    def _fill(name, desc=""):
        if name in deliverables_map:
            return deliverables_map[name]
        low, dn = _norm(name), _norm(desc)
        for key, val in deliverables_map.items():
            kl = _norm(key)
            if kl and (kl in low or low in kl):
                return val
        # word-overlap over aliases
        best, best_score = None, 0
        words = set(_re.findall(r"[a-z0-9]+|[一-鿿]{2,}", str(name).lower() + " " + str(desc).lower()))
        for typ, aliases in ALIASES.items():
            path = tp.get(typ)
            if not path:
                continue
            score = sum(1 for a in aliases if a in low or a in dn or
                        any(a in w or w in a for w in words if len(w) > 1))
            if score > best_score:
                best, best_score = path, score
        if best:
            return best
        return {"status": "unresolved",
                "note": "无法在产物中确定该契约字段的对应物，需人工确认"}

    if isinstance(contract, dict):
        for k, v in contract.items():
            filled[k] = _fill(k, str(v))
    elif isinstance(contract, list):
        for item in contract:
            if isinstance(item, str):
                filled[item] = _fill(item)
            elif isinstance(item, dict):
                name = item.get("name") or item.get("field") or item.get("key") \
                    or json.dumps(item, ensure_ascii=False)[:60]
                filled[name] = _fill(name, json.dumps(item, ensure_ascii=False))
    return filled


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", default="/app/work/plan.json")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--outdir", default="/app/output")
    ap.add_argument("--adapted", default=None)
    ap.add_argument("--extra", default=None,
                    help="JSON file merged into result (agent-settled fields)")
    ap.add_argument("--extra-uncertainty-note", default=None,
                    help="string appended to uncertainty.notes (contract-safe)")
    args = ap.parse_args(argv)

    plan = _load(args.plan, {}) or {}
    outdir = args.outdir
    os.makedirs(outdir, exist_ok=True)

    stages = {}
    for sf in STAGE_FILES:
        p = os.path.join(args.work, sf)
        if os.path.exists(p):
            stages[sf.replace("stage_", "").replace(".json", "")] = _load(p, {})

    adapted = args.adapted
    if not adapted:
        cands = sorted(glob.glob(os.path.join(outdir, "*_adapted.docx")))
        adapted = cands[0] if cands else None

    compliance = _load(os.path.join(args.work, "compliance.json"), {}) or {}
    fidelity = _load(os.path.join(args.work, "fidelity.json"), {}) or {}
    changes = _load(os.path.join(args.work, "changes.json"), []) or []
    spec = _load(os.path.join(args.work, "spec.json"), {}) or {}
    render = _load(os.path.join(outdir, "render_report.json"), {}) or {}

    # ---- deliverables --------------------------------------------------------
    deliverables = []
    if adapted and os.path.exists(adapted):
        deliverables.append({"path": adapted, "type": "editable_docx",
                             "description": "按目标模板结构化套用后的可编辑稿件"})
    pdf = render.get("pdf")
    if pdf and os.path.exists(pdf):
        deliverables.append({"path": pdf, "type": "rendered_pdf",
                             "description": "可编辑稿件的真实渲染 PDF（用于目检与字体嵌入核验）"})
    for png in sorted(glob.glob(os.path.join(outdir, "preview*.png"))):
        deliverables.append({"path": png, "type": "preview_png",
                             "description": "渲染预览图"})
    for extra_path, typ, desc in (
        (os.path.join(args.work, "spec.json"), "spec_json", "结构化格式规格（模板实测+任务文本抽取+冲突登记）"),
        (os.path.join(args.work, "checklist.md"), "checklist_md", "模板检查项清单"),
        (os.path.join(args.work, "compliance.md"), "compliance_md", "逐项合规检查报告"),
        (os.path.join(args.work, "fidelity.md"), "fidelity_md", "内容保真度核验报告"),
        (os.path.join(args.work, "changes.json"), "changelog_json", "单元级修改记录"),
    ):
        if os.path.exists(extra_path):
            deliverables.append({"path": extra_path, "type": typ, "description": desc})

    dmap = {d["type"]: d["path"] for d in deliverables}
    dmap.update({
        "adapted_docx": adapted, "manuscript": adapted, "document": adapted,
        "docx": adapted, "pdf": pdf, "result": os.path.join(outdir, "result.json"),
    })
    type_paths = dict(dmap)
    type_paths["result_json"] = os.path.join(outdir, "result.json")

    contract = plan.get("output_contract")
    contract_filled = fill_contract(contract, dmap, type_paths) if contract else {}

    # ---- status ---------------------------------------------------------------
    failed_stages = [k for k, v in stages.items()
                     if isinstance(v, dict) and v.get("status") == "failed"]
    partial_stages = [k for k, v in stages.items()
                      if isinstance(v, dict) and v.get("status") == "partial"]
    fidelity_verdict = fidelity.get("verdict")
    if not adapted:
        status = "failed"
    elif failed_stages or fidelity_verdict == "FAIL":
        status = "partial"
    elif partial_stages or fidelity_verdict == "WARN" \
            or (compliance.get("summary", {}).get("FAIL", 0) > 0):
        status = "partial"
    else:
        status = "success"

    result = {
        "case_id": plan.get("case_id"),
        "status": status,
        "task": (plan.get("task_text") or "")[:600],
        "deliverables": deliverables,
        "output_contract_filled": contract_filled,
        "verification": {
            "compliance": compliance.get("summary", {}),
            "compliance_report": os.path.join(args.work, "compliance.md"),
            "fidelity_verdict": fidelity_verdict,
            "fidelity_report": os.path.join(args.work, "fidelity.md"),
            "render": {k: render.get(k) for k in
                       ("status", "page_size", "all_fonts_embedded")},
        },
        "sources": [
            {"role": m.get("role") or m.get("kind"),
             "path": m.get("resolved") or m.get("path"),
             "used_for": _used_for(m)}
            for m in plan.get("materials", [])
        ] + ([{"role": "template", "path": plan["template"].get("resolved"),
               "used_for": "format_spec_source"}]
             if plan.get("template") and plan["template"].get("resolved") else []),
        "changes": changes[:400],
        "change_count": len(changes),
        "uncertainty": {
            "unresolved_spec_items": spec.get("unresolved", []),
            "conflicts": spec.get("conflicts", []),
            "assumptions": [c for c in changes if isinstance(c, dict) and c.get("assumption")],
            "notes": plan.get("notes", []),
        },
        "stages": {k: v.get("status", "unknown") for k, v in stages.items()},
        "limits": _limits(status, stages, fidelity_verdict, render),
    }
    if args.extra_uncertainty_note:
        result.setdefault("uncertainty", {}).setdefault("notes", [])
        result["uncertainty"]["notes"].append(args.extra_uncertainty_note)
    extra = _load(args.extra, {}) if args.extra else {}
    if extra:
        result.update(extra)

    out_path = os.path.join(outdir, "result.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "result": out_path, "status": status,
                      "deliverables": len(deliverables)}, ensure_ascii=False))


def _used_for(m):
    k = m.get("kind")
    return {"manuscript": "content_source", "document": "content_source",
            "template": "format_spec_source", "image": "figure_source"}.get(k, "reference")


def _limits(status, stages, fidelity_verdict, render):
    limits = []
    if status == "partial":
        for k, v in stages.items():
            if isinstance(v, dict) and v.get("status") in ("partial", "failed"):
                limits.append("阶段 %s: %s" % (k, v.get("error") or v.get("status")))
        if fidelity_verdict in ("WARN", "FAIL"):
            limits.append("保真度核验存在 %s 项告警/失败，见 fidelity.md" % fidelity_verdict)
    if render and render.get("all_fonts_embedded") is False:
        limits.append("渲染 PDF 存在未嵌入字体，见 render_report.json")
    if not render:
        limits.append("未生成渲染预览（LibreOffice 不可用或转换失败）")
    if not limits:
        limits.append("未发现已知限制；未确认项见 uncertainty.unresolved_spec_items")
    return limits


if __name__ == "__main__":
    main()
