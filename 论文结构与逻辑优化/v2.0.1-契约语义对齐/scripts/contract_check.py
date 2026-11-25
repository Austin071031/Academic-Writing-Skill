#!/usr/bin/env python3
"""contract_check.py — output_contract 逐字段语义对齐（v2.0.1 单点新增）。

用法: python3 contract_check.py --case /input/case.json --work /app/work --out /app/output

对 case.json 声明的每个契约字段（兼容 dict{字段:规格文本} 与
list[含 name/spec 的对象或字符串]），用「字段名 + 规格文本」与产物清单
（每个产物带中文职责描述）做关键词重叠打分（中文按二字组、英文按词），
选出语义最匹配的产物，给出 mapped_artifact / score / justification /
coverage（filled: score≥0.25；partial: 0.1–0.25；missing: <0.1）。
missing 时附 required_content（所需内容说明）。

输出 work/contract_map.json（含 method_note），供 assemble_result.py 回填
result.json 的契约字段；stdout 打印统计行。
exit 0 恒成立（语义对齐是辅助通道，不构成硬闸门）。
"""
import argparse, json, os, re, sys

# 产物清单：文件名 -> 一句话中文职责描述（语义对齐的匹配语料，也是回填用摘要）
ARTIFACTS = [
    ("diagnosis_report.md",
     "六维结构诊断报告：逐条问题含章节/段落/句子位置、原文锚点、判断依据、编辑动作、严重度与置信度"),
    ("edit_plan.json",
     "机读编辑动作清单：与 findings 同 id 的 move/merge/split/add 等编辑操作，供逐条采纳或驳回"),
    ("findings.json",
     "全部问题的统一结构化清单：维度、类型、位置、原文锚点、依据、动作、严重度、置信度"),
    ("section_map.json",
     "章节角色序列表（含逆序对）、篇幅占比表、缩写首现表：章节结构与叙事顺序的中间产物"),
    ("restructured_outline.md",
     "重组大纲草稿：现状章节序列到建议叙事顺序，各节去向与 move/merge/split/add 汇总"),
    ("evidence_map.json",
     "证据映射：每条结论或问题逐条指回原文位置与产物来源的可核验证据表"),
    ("result.json",
     "平台契约结果汇总：case_id、status、outputs、证据映射、变更日志、不确定性说明与统计"),
]

METHOD_NOTE = (
    "契约逐字段语义对齐：字段名+规格文本 与 产物职责描述做关键词重叠打分"
    "（中文按二字组、英文按词）；score=命中token数/字段token数；"
    "coverage: filled≥0.25, partial 0.1-0.25, missing<0.1；"
    "missing 时 required_content 说明所需内容，由 Agent 决定补产物或在 uncertainty 登记。"
)

CJK = re.compile(r"[一-鿿]+")
ENG = re.compile(r"[A-Za-z][A-Za-z0-9_\-]*")


def tokenize(text):
    """中文连续段切二字组（单字段保留单字），英文按词（小写、长度≥2）。"""
    toks = set()
    for m in CJK.finditer(text or ""):
        s = m.group(0)
        if len(s) == 1:
            toks.add(s)
        else:
            toks.update(s[i:i + 2] for i in range(len(s) - 1))
    for m in ENG.finditer(text or ""):
        w = m.group(0).lower()
        if len(w) >= 2:
            toks.add(w)
    return toks


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def parse_contract(case):
    """返回 [(field, spec_text), ...]，兼容 dict 与 list 两种 output_contract 形态。"""
    oc = case.get("output_contract") or case.get("outputContract") or {}
    fields = []
    if isinstance(oc, dict):
        for k, v in oc.items():
            spec = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            fields.append((str(k), spec))
    elif isinstance(oc, list):
        for c in oc:
            if isinstance(c, dict):
                name = str(c.get("name") or c.get("field") or c)
                spec = c.get("spec") or c.get("description") or c.get("spec_text") or ""
                fields.append((name, str(spec)))
            else:
                fields.append((str(c), ""))
    return fields


def coverage_of(score):
    if score >= 0.25:
        return "filled"
    if score >= 0.10:
        return "partial"
    return "missing"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    case = load_json(args.case, {}) or {}
    fields = parse_contract(case)

    # 收集存在的产物：work 优先，out 兜底
    available = []
    for name, desc in ARTIFACTS:
        for base in (args.work, args.out):
            p = os.path.join(base, name)
            if os.path.exists(p) and os.path.getsize(p) > 0:
                available.append((name, desc))
                break

    results = []
    n_filled = n_partial = n_missing = 0
    for field, spec in fields:
        q_tokens = tokenize(f"{field} {spec}")
        best, best_score, best_hits = None, 0.0, set()
        for name, desc in available:
            d_tokens = tokenize(f"{name} {desc}")
            hits = q_tokens & d_tokens
            score = (len(hits) / len(q_tokens)) if q_tokens else 0.0
            if score > best_score:
                best, best_score, best_hits = name, score, hits
        cov = coverage_of(best_score) if best else "missing"
        if cov == "missing":
            best, best_score = None, 0.0
        entry = {
            "field": field,
            "spec": spec,
            "mapped_artifact": best,
            "score": round(best_score, 3),
            "coverage": cov,
        }
        if best:
            desc = dict(available)[best]
            entry["artifact_summary"] = desc
            entry["justification"] = (
                f"字段「{field}」（{spec or '无规格文本'}）与产物 {best} 的职责描述"
                f"关键词重叠 {len(best_hits)} 项（{', '.join(sorted(best_hits))[:120]}），"
                f"score={best_score:.3f}，判定 {cov}。"
            )
        else:
            need = spec or field
            entry["required_content"] = (
                f"需产出满足契约字段「{field}」的内容：{need}。"
                f"现有产物职责描述与该字段关键词重叠不足（最高 score<0.1），"
                f"请补交对应产物，或在 uncertainty 中说明无法产出的原因。"
            )
            entry["justification"] = (
                f"字段「{field}」与全部产物职责描述关键词重叠 score<0.1，判定 missing。"
            )
        results.append(entry)
        if cov == "filled":
            n_filled += 1
        elif cov == "partial":
            n_partial += 1
        else:
            n_missing += 1

    os.makedirs(args.work, exist_ok=True)
    cmap = {
        "case_id": case.get("case_id") or "unknown",
        "method_note": METHOD_NOTE,
        "fields": results,
        "stats": {"fields": len(results), "filled": n_filled,
                  "partial": n_partial, "missing": n_missing},
    }
    path = os.path.join(args.work, "contract_map.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cmap, f, ensure_ascii=False, indent=2)
    print(f"[contract_check] fields={len(results)} filled={n_filled} "
          f"partial={n_partial} missing={n_missing}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
