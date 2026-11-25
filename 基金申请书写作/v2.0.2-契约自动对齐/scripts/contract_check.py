#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""contract_check.py --work W --out O  （v2.0.2 新增，契约自动对齐）

从 work/inspection.json 取 output_contract_fields（dict 的键 或 list 的元素），
逐字段语义映射到实际产物并机检产物存在且非空：

  字段名含 稿|draft|章节        → proposal_draft.md
  字段名含 对照|映射|map|要素    → element_mapping.md
  字段名含 报告|report          → report.md
  字段名含 溯源|证据|evidence|来源 → result.json#evidence_map
  字段名含 预览|preview          → preview.html
  字段名含 留痕|标注             → proposal_annotated.md
  无法映射                        → artifact=null + 原因

写 work/contract_map.json：{field: {"artifact": ..., "note": 一句中文内容说明,
"status": ok|missing|unmapped}}；逐字段打印 ok/missing/unmapped；任一 missing →
打印 FAIL 清单但 exit 0（如实记录，不阻断）。幂等：每次全量重写 contract_map.json。
无 output_contract_fields 时优雅跳过并记录 note。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "contract_check"

# (关键词正则, 映射产物, 产物中文说明)
MAP_RULES = [
    (re.compile(r"稿|draft|章节", re.I), "proposal_draft.md",
     "申请书章节稿（清洁版，七要素齐备，可直接进入申请书）"),
    (re.compile(r"对照|映射|map|要素", re.I), "element_mapping.md",
     "要素对照说明（七要素 × 章节 × 段落数/字数 × 证据数 × 状态 + 三级对应清单）"),
    (re.compile(r"报告|report", re.I), "report.md",
     "质量报告（覆盖表、findings 分级统计、来源核验统计、异常与限制）"),
    (re.compile(r"溯源|证据|evidence|来源", re.I), "result.json#evidence_map",
     "证据溯源（result.json 的 evidence_map：段落→要素→证据 FID→材料来源 三级对应）"),
    (re.compile(r"预览|preview", re.I), "preview.html",
     "交付预览（report/draft/mapping 三栏 HTML 预览）"),
    (re.compile(r"留痕|标注", re.I), "proposal_annotated.md",
     "留痕版章节稿（段首 D-Pxxx，〔F〕〔拟〕〔确认〕标记原位保留）"),
]

EVIDENCE_REF = "result.json#evidence_map"


def norm_fields(raw):
    """宽容地把 output_contract_fields 归一成字段名列表（dict 键 或 list 元素）。"""
    if isinstance(raw, dict):
        return [str(k) for k in raw.keys()]
    fields = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item.strip():
                fields.append(item.strip())
            elif isinstance(item, dict):
                for k in ("field", "name", "key", "artifact"):
                    if isinstance(item.get(k), str) and item[k].strip():
                        fields.append(item[k].strip())
                        break
    return fields


def map_field(field):
    """字段名 → (artifact, note) 或 (None, 原因)。"""
    for pat, artifact, desc in MAP_RULES:
        if pat.search(field):
            return artifact, desc
    return None, f"字段名「{field}」不含任何已知契约关键词，无法映射到产物，需人工确认"


def check_artifact(artifact, out_dir):
    """校验映射产物存在且非空；evidence_map 检查 result.json 内字段。返回 bool。"""
    if artifact == EVIDENCE_REF:
        result = gu.read_json(os.path.join(out_dir, "result.json"), None)
        if not isinstance(result, dict):
            return False
        ev = result.get("evidence_map")
        return isinstance(ev, list) and len(ev) > 0
    if not artifact:
        return False
    path = os.path.join(out_dir, artifact)
    return os.path.isfile(path) and os.path.getsize(path) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    work, out = args.work, args.out
    gu.ensure_dir(work)

    inspection = gu.read_json(os.path.join(work, "inspection.json"), None)
    if not isinstance(inspection, dict):
        contract_map = {"_note": "inspection.json 缺失或无法解析，契约映射跳过",
                        "_fields": 0}
        gu.write_json(os.path.join(work, "contract_map.json"), contract_map)
        print("[contract_check] inspection.json 缺失，跳过契约映射（记录 note），exit 0")
        return 0

    fields = norm_fields(inspection.get("output_contract_fields"))
    if not fields:
        contract_map = {"_note": "inspection.json 无 output_contract_fields，"
                                 "本案例未声明输出契约，契约映射优雅跳过",
                        "_fields": 0}
        gu.write_json(os.path.join(work, "contract_map.json"), contract_map)
        print("[contract_check] 无 output_contract_fields，优雅跳过（记录 note），exit 0")
        return 0

    contract_map = {}
    missing, unmapped = [], []
    for field in fields:
        artifact, note = map_field(field)
        if artifact is None:
            contract_map[field] = {"artifact": None, "note": note,
                                   "status": "unmapped"}
            unmapped.append(field)
            print(f"[contract_check] {field}: unmapped → {note}")
            continue
        ok = check_artifact(artifact, out)
        if ok:
            contract_map[field] = {"artifact": artifact, "note": note,
                                   "status": "ok"}
            print(f"[contract_check] {field}: ok → {artifact}")
        else:
            status_note = (note + f"；但产物 {artifact} 当前缺失或为空，"
                                  "需补齐后重跑本脚本（幂等）")
            contract_map[field] = {"artifact": None, "note": status_note,
                                   "status": "missing"}
            missing.append((field, artifact))
            print(f"[contract_check] {field}: missing → {artifact} 缺失或为空")

    gu.write_json(os.path.join(work, "contract_map.json"), contract_map)

    ok_count = len(fields) - len(missing) - len(unmapped)
    print(f"[contract_check] 字段={len(fields)} ok={ok_count} "
          f"missing={len(missing)} unmapped={len(unmapped)}")
    if missing or unmapped:
        print("[contract_check] FAIL 清单（如实记录，不阻断，exit 0）：")
        for field, artifact in missing:
            print(f"  FAIL missing   {field} → 约定产物 {artifact} 缺失或为空")
        for field in unmapped:
            print(f"  FAIL unmapped  {field} → 无法映射到任何已知产物")
    else:
        print("[contract_check] 全部契约字段映射并核验通过")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[contract_check] ERROR: {e}")
        raise SystemExit(1)
