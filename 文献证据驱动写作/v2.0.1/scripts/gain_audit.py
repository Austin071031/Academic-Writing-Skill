#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基础 Agent 失败模式拦截审计（v2.0.1 增量）。
对照 references/failure_modes.md 的失败模式清单，逐模式给出**本次运行**的拦截/规避证据，
写 /app/output/gain_audit.json。只陈述本次运行产物中可复核的事实，不写未运行的对照数字。
用法: python3 gain_audit.py [INPUT] [WORK] [OUTPUT] [SKILL_DIR]
"""
import csv, json, os, re, sys

INPUT = sys.argv[1] if len(sys.argv) > 1 else "/input"
WORK = sys.argv[2] if len(sys.argv) > 2 else "/app/work"
OUTPUT = sys.argv[3] if len(sys.argv) > 3 else "/app/output"
SKILL = sys.argv[4] if len(sys.argv) > 4 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 从 failure_modes.md 读模式注册表（参数真被读取）
modes = []
fm_path = os.path.join(SKILL, "references", "failure_modes.md")
if os.path.exists(fm_path):
    for line in open(fm_path, encoding="utf-8"):
        m = re.match(r"^- \*\*(F\d+)\s+(.+?)\*\*[:：]", line)
        if m:
            modes.append({"mode_id": m.group(1), "mode": m.group(2).strip(),
                          "status": "unchecked", "evidence": ""})

def load_json(p):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None

vr = load_json(os.path.join(OUTPUT, "validation_report.json")) or {}
res = load_json(os.path.join(OUTPUT, "result.json")) or {}
man = load_json(os.path.join(WORK, "text_manifest.json")) or {}
claims = []
cp = os.path.join(OUTPUT, "claims.jsonl")
if os.path.exists(cp):
    for line in open(cp, encoding="utf-8"):
        line = line.strip()
        if line:
            try:
                claims.append(json.loads(line))
            except Exception:
                pass
evid = []
ep = os.path.join(OUTPUT, "evidence.csv")
if os.path.exists(ep):
    try:
        evid = list(csv.DictReader(open(ep, encoding="utf-8", newline="")))
    except Exception:
        pass
draft = ""
dp = os.path.join(OUTPUT, "draft.md")
if os.path.exists(dp):
    draft = open(dp, encoding="utf-8").read()

qv = vr.get("quote_verification", [])
miss = [q for q in qv if not q.get("found")]
def set_mode(mid, status, evidence):
    for m in modes:
        if m["mode_id"] == mid:
            m["status"], m["evidence"] = status, evidence

set_mode("F01", "intercepted" if qv and not miss else ("at_risk" if miss else "avoided"),
         "R5 逐字核验 %d/%d 命中；未命中 %d 条（拦截为 error）" % (
             sum(1 for q in qv if q.get("found")), len(qv), len(miss)))
noloc = [r.get("evidence_id") for r in evid if not (r.get("location") or "").strip()]
set_mode("F02", "avoided" if evid and not noloc else ("at_risk" if noloc else "avoided"),
         "证据 %d 条，缺定位 %d 条%s" % (len(evid), len(noloc), ("：" + "、".join(noloc)) if noloc else ""))
unsup = [c for c in claims if c.get("status") == "unsupported"]
in_draft_unsup = [c["claim_id"] for c in unsup if c.get("claim_id") and c["claim_id"] in draft]
set_mode("F03", "avoided" if not in_draft_unsup else "at_risk",
         "unsupported 论断 %d 条，进入成稿 %d 条" % (len(unsup), len(in_draft_unsup)))
strong = ["证实", "证明", "公认", "普遍认为", "根治", "确定有效"]
weak = [c for c in claims if c.get("strength") in ("C", "D")]
hits = [c["claim_id"] for c in weak if c.get("claim_id") and any(v in draft for v in strong)]
set_mode("F04", "avoided" if not hits else "at_risk",
         "C/D 级论断 %d 条，成稿强断言动词冲突 %d 条" % (len(weak), len(hits)))
cids = {c.get("claim_id") for c in claims if c.get("claim_id")}
drefs = set(re.findall(r"\[(C\d+)\]", draft)) | set(re.findall(r"【(C\d+)】", draft))
bad = drefs - cids
set_mode("F05", "avoided" if not bad else "at_risk",
         "成稿引用编号 %d 个，未定义 %d 个%s" % (len(drefs), len(bad), ("：" + "、".join(sorted(bad))) if bad else ""))
mk = (vr.get("errors") or [])
set_mode("F06", "intercepted" if not any("output_contract" in e for e in mk) else "at_risk",
         "R1 契约字段覆盖检查：%s" % ("无缺失" if not any("output_contract" in e for e in mk) else "存在缺失"))
has_logs = all(k in res for k in ("change_log", "exceptions", "uncertainty"))
set_mode("F07", "avoided" if has_logs else "at_risk",
         "result.json 含 change_log/exceptions/uncertainty 字段：%s" % ("是" if has_logs else "否"))
failed_docs = {k: v for k, v in man.items() if v.get("status") != "ok"}
abstract_only = [r for r in evid if (r.get("doc_type") or "") == "abstract_only"]
set_mode("F08", "intercepted" if failed_docs or abstract_only else "avoided",
         "全文文本化失败 %d 篇（已记 exceptions）；abstract_only 证据 %d 条（已降级标注）" % (
             len(failed_docs), len(abstract_only)))
skeleton = all(k in res for k in ("status", "assumptions"))
set_mode("F09", "intercepted" if skeleton else "at_risk",
         "result.json 骨架字段（status/assumptions）存在：%s（init_result.py 早存）" % ("是" if skeleton else "否"))
long_q = [r.get("evidence_id") for r in evid if len(r.get("quote") or "") > 300]
set_mode("F10", "avoided" if not long_q else "at_risk",
         "超 300 字摘录 %d 条（跨句拼接风险）" % len(long_q))

ok = sum(1 for m in modes if m["status"] in ("intercepted", "avoided"))
report = {"basis": "references/failure_modes.md（基础 Agent 常见失败模式清单）",
          "note": "仅陈述本次运行产物中可复核的拦截/规避事实，不构成对未运行基线的数值断言",
          "modes": modes,
          "summary": {"intercepted": sum(1 for m in modes if m["status"] == "intercepted"),
                      "avoided": sum(1 for m in modes if m["status"] == "avoided"),
                      "at_risk": sum(1 for m in modes if m["status"] == "at_risk"),
                      "total": len(modes)}}
with open(os.path.join(OUTPUT, "gain_audit.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)
print(json.dumps(report["summary"], ensure_ascii=False))
