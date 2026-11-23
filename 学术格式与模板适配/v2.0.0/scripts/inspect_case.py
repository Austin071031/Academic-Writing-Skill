#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inspect_case.py — Parse /input/case.json + task.md into a normalized `plan.json`.

The three fixed cases are platform-provided; their JSON schema is not frozen,
so this resolver is defensive: it scans common key spellings for the case id,
task text, material list, template and output contract, then resolves every
referenced path against the usual locations.

Usage:
    python3 inspect_case.py --case /input/case.json --task /input/task.md \
        --out /app/work/plan.json

Stdlib only.
"""
import argparse
import json
import os
import sys

SEARCH_DIRS = ["/input", "/input/materials", "/input/files", "/app/input",
               "/app/work", os.getcwd()]

CASE_ID_KEYS = ["case_id", "caseId", "case", "id", "case_name", "name"]
TASK_KEYS = ["task", "instruction", "prompt", "requirements", "description",
             "task_text", "question"]
MATERIAL_KEYS = ["materials", "inputs", "files", "attachments", "references",
                 "source_files", "resources", "inputs_files", "docs"]
TEMPLATE_KEYS = ["template", "target_template", "template_file", "style_template",
                 "target", "template_path", "format_template", "style_guide"]
CONTRACT_KEYS = ["output_contract", "outputs", "required_outputs",
                 "deliverables", "output", "output_requirements",
                 "expected_outputs", "deliverable"]


def _first(d, keys):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] not in (None, "", []):
            return d[k]
    return None


def _flatten_materials(obj):
    """Normalize many shapes into [{path?, name?, role?, type?}]."""
    out = []
    if obj is None:
        return out
    if isinstance(obj, str):
        return [{"path": obj}]
    if isinstance(obj, dict):
        # {name: path} mapping or a single descriptor
        if "path" in obj or "file" in obj or "name" in obj:
            d = dict(obj)
            if "file" in d and "path" not in d:
                d["path"] = d["file"]
            return [d]
        return [{"path": v, "name": k} for k, v in obj.items()
                if isinstance(v, str)]
    if isinstance(obj, list):
        for it in obj:
            out.extend(_flatten_materials(it))
    return out


def resolve_path(p):
    if not p:
        return None
    p = str(p)
    if os.path.isabs(p) and os.path.exists(p):
        return p
    cands = [p] + [os.path.join(d, p) for d in SEARCH_DIRS] + \
        [os.path.join(d, os.path.basename(p)) for d in SEARCH_DIRS]
    for c in cands:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None


DOC_EXT = {".docx", ".doc", ".tex", ".md", ".txt", ".pdf", ".rtf"}
TEMPLATE_EXT = {".docx", ".dotx", ".tex", ".cls", ".pdf", ".md", ".txt"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".eps"}


def classify(entry, resolved):
    ext = os.path.splitext(resolved or entry.get("path") or "")[1].lower()
    text = " ".join(str(entry.get(k, "")) for k in ("role", "type", "name", "label")).lower()
    if ext in TEMPLATE_EXT and any(k in text for k in ("template", "模板", "target", "格式")):
        return "template"
    if ext in DOC_EXT:
        if any(k in text for k in ("manuscript", "draft", "论文", "稿件", "原文", "底稿", "source")):
            return "manuscript"
        return "document"
    if ext in IMG_EXT:
        return "image"
    return "other"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--task", default="/input/task.md")
    ap.add_argument("--out", default="plan.json")
    args = ap.parse_args(argv)

    # dynamically extend search roots with the directories that actually hold
    # the case descriptor / task file (covers non-standard mounts and local sims)
    for extra in (os.path.dirname(os.path.abspath(args.case)),
                  os.path.dirname(os.path.abspath(args.task))):
        if extra and extra not in SEARCH_DIRS and os.path.isdir(extra):
            SEARCH_DIRS.append(extra)

    case = {}
    case_raw = None
    if os.path.exists(args.case):
        with open(args.case, encoding="utf-8") as f:
            case_raw = f.read()
        try:
            case = json.loads(case_raw)
        except json.JSONDecodeError:
            case = {"_raw_text": case_raw}

    task_text = _first(case, TASK_KEYS) or ""
    if isinstance(task_text, (list, dict)):
        task_text = json.dumps(task_text, ensure_ascii=False)
    task_md = ""
    if os.path.exists(args.task):
        with open(args.task, encoding="utf-8", errors="replace") as f:
            task_md = f.read()
    # case-level "task" may itself hold a nested structure
    if isinstance(case.get("task"), dict):
        inner = case["task"]
        task_text = task_text or (_first(inner, TASK_KEYS) or "")

    case_id = _first(case, CASE_ID_KEYS)
    if case_id is None and isinstance(case, dict):
        # nested {"case": {...}}
        for v in case.values():
            if isinstance(v, dict):
                cid = _first(v, CASE_ID_KEYS)
                if cid:
                    case_id = cid
                    break
    if isinstance(case_id, dict):
        case_id = _first(case_id, ["id", "case_id", "name"])

    materials_raw = _first(case, MATERIAL_KEYS)
    template_raw = _first(case, TEMPLATE_KEYS)
    contract = _first(case, CONTRACT_KEYS)

    materials = []
    for e in _flatten_materials(materials_raw):
        p = e.get("path")
        resolved = resolve_path(p) if p else None
        materials.append({
            "name": e.get("name") or (os.path.basename(str(p)) if p else None),
            "path": p, "resolved": resolved,
            "role": e.get("role") or e.get("type") or e.get("label"),
            "kind": classify(e, resolved),
            "exists": bool(resolved),
        })

    template = None
    if template_raw:
        e = _flatten_materials(template_raw)[0] if _flatten_materials(template_raw) else {"path": template_raw}
        p = e.get("path") if isinstance(e, dict) else str(template_raw)
        if isinstance(template_raw, str):
            p = template_raw
        resolved = resolve_path(p)
        template = {"path": p, "resolved": resolved,
                    "exists": bool(resolved),
                    "ext": os.path.splitext(str(p))[1].lower()}

    # fallback: if no explicit template, any material classified as template
    if not template or not template.get("exists"):
        for m in materials:
            if m["kind"] == "template" and m["exists"]:
                template = {"path": m["path"], "resolved": m["resolved"],
                            "exists": True,
                            "ext": os.path.splitext(m["resolved"])[1].lower()}
                break

    doc_materials = [m for m in materials if m["kind"] in ("manuscript", "document")
                     and m["exists"] and m["resolved"].lower().endswith((".docx",))]
    plan = {
        "case_id": case_id,
        "task_text": (task_text or "")[:4000],
        "task_md_head": task_md[:2000],
        "materials": materials,
        "template": template,
        "output_contract": contract,
        "docx_candidates": [m["resolved"] for m in doc_materials],
        "notes": [],
    }
    if not case_id:
        plan["notes"].append("case.json 中未找到 case_id 字段，请在 result.json 中回填原始标识")
    if not plan["docx_candidates"]:
        plan["notes"].append("未发现 docx 稿件；可能需要在 case 任务文本中确认输入文件")
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print(json.dumps({"ok": True, "case_id": case_id,
                      "materials": len(materials),
                      "template": (template or {}).get("resolved"),
                      "docx_candidates": plan["docx_candidates"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
