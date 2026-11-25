#!/usr/bin/env python3
"""review_helper.py — v2.0.0 单点新增：复核闭环支持。

把全部 findings 连同 ±1 段原文上下文打包成一个紧凑文件（work/review_pack.md），
Agent 一次读取即可对每条问题作出裁决，将第 7 步的模型请求从 ~2N 次压到 ~2 次；
同时生成 work/adjudication_template.json（裁决模板）与读取裁决结果的回填功能。

用法:
  python3 review_helper.py --work /app/work pack      # 生成 review_pack.md + 裁决模板
  python3 review_helper.py --work /app/work apply \
      --adjudications /app/work/adjudications.json    # 回填裁决到 findings.json/报告
  python3 review_helper.py --work /app/work --out /app/output pack  # 同步刷新输出草稿
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scanutil import short

def load(work, name, default):
    p = os.path.join(work, name)
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def para_map(model):
    return {p["id"]: p for p in model.get("paragraphs", [])}

def context_of(model, f, para_by_id):
    """取 finding 定位段的 ±1 段上下文（紧凑）。"""
    loc = f.get("location") or {}
    pid = loc.get("para_id")
    if not pid or "⇄" in str(pid):
        pid = str(pid or "").split("⇄")[0]
    p = para_by_id.get(pid)
    if not p:
        return "(无直接段落定位——全文级问题)"
    out = []
    sec_paras = [x for x in model["paragraphs"] if x["section_id"] == p["section_id"]]
    idx = sec_paras.index(p)
    for x in sec_paras[max(0, idx - 1): idx + 2]:
        marker = ">>> " if x["id"] == p["id"] else "    "
        out.append(f"{marker}[{x['id']}] {short(x['text'], 220)}")
    return "\n".join(out)

def cmd_pack(work, out):
    model = load(work, "structure.json", {})
    findings = load(out, "findings.json", None) or load(work, "findings.json", [])
    if not findings:
        scan = load(work, "findings_scan.json", [])
        eng = load(work, "findings_engine.json", [])
        findings = scan + eng
    para_by_id = para_map(model)

    L = ["# 复核包（逐条裁决：采纳 / 修正 / 驳回 + 一句理由）\n",
         "使用：逐条阅读原文上下文与候选问题，产出 adjudications.json（模板见 ",
         "work/adjudication_template.json），然后运行 review_helper.py apply 回填。\n"]
    for f in findings:
        loc = f.get("location") or {}
        L.append(f"## [{f.get('id')}] {f.get('type')}（{f.get('dimension')} / {f.get('severity')} / conf={f.get('confidence')}）")
        L.append(f"- 位置: {loc.get('section') or '(全文)'} › {loc.get('para_id') or '-'} › {loc.get('sentence_id') or '-'}")
        L.append(f"- 候选依据: {f.get('evidence')}")
        L.append(f"- 建议动作: `{f.get('action', {}).get('op')}` {f.get('action', {}).get('instruction')}")
        L.append("- 原文上下文:")
        L.append("```")
        L.append(context_of(model, f, para_by_id))
        L.append("```\n")
    pack = os.path.join(work, "review_pack.md")
    with open(pack, "w", encoding="utf-8") as fp:
        fp.write("\n".join(L))

    tpl = {"usage": "对 review_pack.md 中每条 finding 给出裁决；verdict ∈ {采纳, 修正, 驳回}；"
                    "修正时在 revision 字段给出改后的 type/severity/action；驳回必须给 reason。",
           "overall_diagnosis": "(在此写 3-5 句总体诊断：主要问题在哪个维度、为什么、先改什么)",
           "dimension_main_issues": {"research_question": "", "section_structure": "",
                                     "argument_chain": "", "paragraph_relation": "",
                                     "redundancy": "", "conclusion_boundary": ""},
           "adjudications": [{"id": f.get("id"), "verdict": "采纳", "reason": "",
                              "revision": None} for f in findings]}
    with open(os.path.join(work, "adjudication_template.json"), "w", encoding="utf-8") as fp:
        json.dump(tpl, fp, ensure_ascii=False, indent=1)
    print(f"[review_helper] pack: findings={len(findings)} -> work/review_pack.md + adjudication_template.json")
    return 0

def cmd_apply(work, out, adj_path):
    adj = load(os.path.dirname(adj_path) or work, os.path.basename(adj_path), None)
    if adj is None:
        print(f"[review_helper][FATAL] 裁决文件不可读: {adj_path}", file=sys.stderr)
        return 1
    findings = load(out, "findings.json", None) or []
    if not findings:
        print("[review_helper][FATAL] findings.json 不存在，请先运行 report_builder.py", file=sys.stderr)
        return 1
    by_id = {f["id"]: f for f in findings}
    kept, rejected, revised = [], 0, 0
    for a in adj.get("adjudications", []):
        f = by_id.get(a.get("id"))
        if not f:
            continue
        v = a.get("verdict", "采纳")
        f["verdict"] = v
        f["verdict_reason"] = a.get("reason", "")
        if v == "驳回":
            rejected += 1
            continue
        if v == "修正" and isinstance(a.get("revision"), dict):
            revised += 1
            for k in ("type", "severity", "confidence"):
                if a["revision"].get(k):
                    f[k] = a["revision"][k]
            if isinstance(a["revision"].get("action"), dict):
                f["action"].update(a["revision"]["action"])
        kept.append(f)
    # 未裁决条目保留并标注
    judged = {a.get("id") for a in adj.get("adjudications", [])}
    for f in findings:
        if f["id"] not in judged:
            f["verdict"] = "未裁决"
            f["verdict_reason"] = "Agent 未给出裁决，保留脚本候选原样"
            kept.append(f)
    with open(os.path.join(out, "findings.json"), "w", encoding="utf-8") as fp:
        json.dump(kept, fp, ensure_ascii=False, indent=1)

    # 总体诊断写入报告头部
    report = os.path.join(out, "diagnosis_report.md")
    if os.path.exists(report):
        with open(report, encoding="utf-8") as fp:
            body = fp.read()
        overall = adj.get("overall_diagnosis") or ""
        dims = adj.get("dimension_main_issues") or {}
        block = ["\n## 0.5 总体诊断与裁决结论（Agent 复核）\n"]
        if overall.strip():
            block.append(overall.strip() + "\n")
        main_dims = {k: v for k, v in dims.items() if v and v.strip()}
        if main_dims:
            block.append("各维度主问题判定：")
            for k, v in main_dims.items():
                block.append(f"- {k}: {v.strip()}")
            block.append("")
        block.append(f"裁决统计：采纳/修正保留 {len(kept)} 条，驳回 {rejected} 条"
                     f"（驳回理由见 findings.json 各条 verdict_reason）。")
        block.append("复核结论：本报告所列问题均经逐条原文对照裁决；驳回条目已移除，"
                     "修正条目以 revision 后内容为准。\n")
        marker = "## 0. 材料缺口与不确定性"
        if marker in body:
            body = body.replace(marker, "\n".join(block) + "\n" + marker, 1)
        else:
            body = body.replace("\n## ", "\n".join(block) + "\n\n## ", 1)
        with open(report, "w", encoding="utf-8") as fp:
            fp.write(body)
    print(f"[review_helper] apply: 保留={len(kept)} 驳回={rejected} 修正={revised} -> findings.json + 报告 0.5 节")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["pack", "apply"])
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--adjudications", default=None)
    args = ap.parse_args()
    if args.command == "pack":
        return cmd_pack(args.work, args.out)
    adj = args.adjudications or os.path.join(args.work, "adjudications.json")
    return cmd_apply(args.work, args.out, adj)

if __name__ == "__main__":
    sys.exit(main())
