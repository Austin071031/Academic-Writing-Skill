#!/usr/bin/env python3
"""contract_fill.py — 契约精确交付（v2.0.1 方向）：逐字段语义化填充 result.json。

读取 case.json 的 output_contract（字段名 + 说明文字），把每个字段与
/app/output 实际产物做语义匹配，写入：
  result[field] = {"file": <交付文件>, "sha256": ..., "summary": <一句内容说明>,
                   "content_preview": <前 300 字符>, "verified": true}
匹配不到的字段：置 null 并在 uncertainty 如实记录（不虚构内容）。
匹配规则：字段名+说明的关键词 → 产物注册表（正则打分），人工可用
work/contract_override.json {"<field>": "<filename>"} 指定映射。

用法: python3 contract_fill.py --work /app/work --out /app/output \
        [--case /input/case.json]
在 assemble_result.py 之后运行（覆写/补齐契约字段），随后必须重跑 validate_output.py。
"""
import argparse, hashlib, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trans_utils as tu

# 产物注册表：文件名 → (一句话说明, 匹配关键词)
ARTIFACT_INFO = {
    "translation_full.md": ("纯译文全文（结构原位保留）",
                            r"译文|翻译|translation|target|主产物|deliverable|纯译文"),
    "bilingual.md": ("双语对照稿（逐段原文+译文，带稳定段 ID）",
                     r"双语|对照|bilingual|alignment|对齐"),
    "revised_translation.md": ("修订后译文",
                               r"修订|改稿|revised|revision"),
    "audit_annotated.md": ("机检标注稿（问题句段 ⚠ 三联对照）",
                           r"标注|批注|annotated|审校|proofread"),
    "report.md": ("翻译质量报告（问题清单+修订指令+统计）",
                  r"报告|report|质量|quality|summary|总结"),
    "findings.json": ("机检问题清单（含位置/锚点/依据/修订指令）",
                      r"问题|findings|缺陷|issue"),
    "edit_plan.json": ("机读修订计划（逐条可采纳/驳回）",
                       r"修订计划|edit.?plan|修改计划"),
    "evidence_map.json": ("逐句段原文/译文溯源映射",
                          r"溯源|证据|evidence|来源|source.?map|映射"),
    "number_ledger.json": ("数字台账（逐句段值/单位/原文形态）",
                           r"数字|台账|ledger|数据"),
    "number_audit.json": ("数字忠实性比对表",
                          r"数字|忠实|fidelity|数值"),
    "glossary.json": ("审定锁定术语表",
                      r"术语|glossary|terminology|词表"),
    "term_audit.json": ("术语一致性核对表",
                        r"术语|一致性|consisten"),
    "alignment.json": ("逐句段双语对齐状态",
                       r"对齐|alignment|对照"),
    "align_audit.json": ("对齐结构不变量审计",
                         r"对齐|结构|structure"),
    "style_report.json": ("风格指标与逐句段问题",
                          r"风格|style|语域"),
    "boundary_audit.json": ("引用与语义边界核对表",
                            r"引用|边界|citation|boundary"),
    "citation_index.json": ("引用/语气译前索引",
                            r"引用|索引|citation|index"),
    "result.json": ("契约结果（本文件）", r"result|结果"),
}

def file_entry(path, name):
    with open(path, "rb") as f:
        data = f.read()
    preview = ""
    try:
        preview = data.decode("utf-8")[:300]
    except UnicodeDecodeError:
        preview = "(二进制/非 UTF-8 内容)"
    return {"file": name, "sha256": hashlib.sha256(data).hexdigest(),
            "bytes": len(data), "summary": ARTIFACT_INFO.get(name, ("交付产物", ""))[0],
            "content_preview": preview, "verified": True}

def score_field(field_text, out_files):
    best, best_s = None, 0
    for name in out_files:
        info = ARTIFACT_INFO.get(name)
        if not info:
            continue
        kw = info[1]
        s = len(re.findall(kw, field_text, re.I)) if kw else 0
        # 文件名直接出现在字段说明里加权
        if name.split(".")[0].replace("_", " ") in field_text.lower():
            s += 2
        if s > best_s:
            best, best_s = name, s
    return best

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--case", default="/input/case.json")
    args = ap.parse_args()

    rp = os.path.join(args.out, "result.json")
    result = tu.load_json(rp)
    if not result:
        print("[contract_fill][FATAL] 先运行 assemble_result.py 生成 result.json",
              file=sys.stderr)
        return 1
    case = tu.load_json(args.case, {}) or {}
    oc = case.get("output_contract") or case.get("outputContract") or {}
    fields = []
    if isinstance(oc, dict):
        fields = [{"name": k, "spec": v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}
                  for k, v in oc.items()]
    elif isinstance(oc, list):
        for c in oc:
            if isinstance(c, dict):
                fields.append({"name": c.get("name", str(c)),
                               "spec": c.get("spec") or c.get("description") or ""})
            else:
                fields.append({"name": str(c), "spec": ""})
    if not fields:
        print("[contract_fill] case.json 无 output_contract，无需填充")
        return 0

    out_files = [f for f in os.listdir(args.out)
                 if os.path.isfile(os.path.join(args.out, f)) and f != "result.json"]
    override = tu.load_json(os.path.join(args.work, "contract_override.json"), {}) or {}
    uncertainty = result.get("uncertainty") or []

    filled = {}
    for fd in fields:
        name, spec = fd["name"], fd["spec"] or ""
        chosen = override.get(name)
        if chosen and chosen not in out_files:
            uncertainty.append({"kind": "contract_override_invalid", "field": name,
                                "note": f"contract_override 指定文件 {chosen} 不存在，回退自动匹配"})
            chosen = None
        if not chosen:
            chosen = score_field((name + " " + spec).lower(), out_files)
        if chosen:
            filled[name] = file_entry(os.path.join(args.out, chosen), chosen)
        else:
            filled[name] = None
            uncertainty.append({"kind": "contract_field_unmapped", "field": name,
                                "note": f"契约字段「{name}」（{spec[:60]}）无匹配产物，"
                                        "如实置 null；如需映射请在 work/contract_override.json 指定"})

    result.update(filled)
    result["contract_fill"] = {
        "fields": [{"name": f["name"], "mapped_to": (filled[f["name"]] or {}).get("file")}
                   for f in fields],
        "unmapped": [f["name"] for f in fields if filled[f["name"]] is None],
    }
    result["uncertainty"] = uncertainty
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    n_mapped = sum(1 for v in filled.values() if v)
    print(f"[contract_fill] 契约字段={len(fields)} 已映射={n_mapped} "
          f"未映射={len(fields) - n_mapped}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
