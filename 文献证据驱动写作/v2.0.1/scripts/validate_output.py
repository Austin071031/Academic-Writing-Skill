#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""终检：对 /app/output 产物做一致性校验，输出 validation_report.json 并回写 result.json。
校验是"机器能查的硬约束"，包括：
  R1 result.json 可解析、含 case_id、覆盖 output_contract 全部键（递归）；
  R2 三段产物齐备且非空：claims.jsonl（论断清单）、evidence.csv（证据表）、draft.md（成稿）；
  R3 论断记录结构合法：claim_id 唯一、状态词表内、evidence_ids 可解析；
  R4 证据记录结构合法：定位非空、类型/关系/强度词表内；
  R5 逐字核验：每条摘录在 /app/work/text/ 中可检索到（空白归一化），报告命中页码；
  R6 成稿覆盖：每个 claim_id 在 draft.md 中出现，或被显式排除并说明理由；
  R7 方向专属检查（见 direction_checks）。
用法: python3 validate_output.py [INPUT_DIR] [WORK_DIR] [OUTPUT_DIR] [SKILL_DIR]
退出码: 0 全部通过；1 存在 error；2 仅 warning。
"""
import csv, json, os, re, sys

INPUT = sys.argv[1] if len(sys.argv) > 1 else "/input"
WORK = sys.argv[2] if len(sys.argv) > 2 else "/app/work"
OUTPUT = sys.argv[3] if len(sys.argv) > 3 else "/app/output"
SKILL = sys.argv[4] if len(sys.argv) > 4 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

errors, warnings, notes = [], [], []

def norm(s):
    return re.sub(r"\s+", "", (s or "")).lower()

# ---------- R1 result.json ----------
result = {}
rp = os.path.join(OUTPUT, "result.json")
if not os.path.exists(rp):
    errors.append("缺少 result.json")
else:
    try:
        with open(rp, encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        errors.append("result.json 解析失败: %s" % e)

case = {}
cpath = os.path.join(INPUT, "case.json")
if os.path.exists(cpath):
    try:
        with open(cpath, encoding="utf-8") as f:
            case = json.load(f)
    except Exception:
        case = {}
oc = case.get("output_contract") or case.get("outputContract") or {}

missing_keys = []
def check_contract(contract, data, prefix=""):
    if not isinstance(contract, dict):
        return
    for k, v in contract.items():
        key = "%s.%s" % (prefix, k) if prefix else k
        if k not in data or data.get(k) is None:
            missing_keys.append(key)
        elif isinstance(v, dict) and isinstance(data.get(k), dict):
            check_contract(v, data[k], key)
check_contract(oc, result)
if missing_keys:
    errors.append("result.json 缺 output_contract 字段（值为 null）: %s" % ", ".join(missing_keys[:20]))
if not result.get("case_id"):
    warnings.append("result.json 未填 case_id")

# ---------- 载入文本库（逐字核验用） ----------
texts = {}
tdir = os.path.join(WORK, "text")
if os.path.isdir(tdir):
    for fn in os.listdir(tdir):
        if fn.endswith(".txt"):
            try:
                with open(os.path.join(tdir, fn), encoding="utf-8") as f:
                    texts[fn[:-4]] = f.read()
            except Exception:
                pass
if not texts:
    warnings.append("无 /app/work/text/ 文本库，R5 逐字核验跳过（可能未运行 extract_text.py）")

def find_quote(quote):
    q = norm(quote)
    if len(q) < 8:
        return None, "摘录过短（<8 字符），无法可靠核验"
    hits = []
    for did, t in texts.items():
        nt = norm(t)
        start = 0
        while True:
            pos = nt.find(q, start)
            if pos < 0:
                break
            # 反查页码：页标记位于每页内容之前，最后一个不晚于摘录位置的标记即所在页
            pg = None
            for m in re.finditer(r"===== \[PAGE (\d+)\] =====", t):
                if len(norm(t[: m.start()])) <= pos:
                    pg = int(m.group(1))
                else:
                    break
            hits.append({"doc": did, "page": pg})
            break  # 每条摘录记录首个命中即可
    return hits, None

# ---------- R2 产物齐备 ----------
def nonempty(path):
    return os.path.exists(path) and os.path.getsize(path) > 0

claims_p = os.path.join(OUTPUT, "claims.jsonl")
evid_p = os.path.join(OUTPUT, "evidence.csv")
draft_p = os.path.join(OUTPUT, "draft.md")
for name, p in (("claims.jsonl", claims_p), ("evidence.csv", evid_p), ("draft.md", draft_p)):
    if not nonempty(p):
        errors.append("缺少或为空: %s" % name)

# ---------- R3 论断清单 ----------
claims, claim_ids = [], set()
if nonempty(claims_p):
    with open(claims_p, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
            except Exception as e:
                errors.append("claims.jsonl 第%d行非合法JSON: %s" % (ln, e))
                continue
            claims.append(c)
            cid = c.get("claim_id")
            if not cid:
                errors.append("claims.jsonl 第%d行缺 claim_id" % ln)
            elif cid in claim_ids:
                errors.append("claim_id 重复: %s" % cid)
            claim_ids.add(cid)
            if not c.get("claim_text"):
                warnings.append("论断 %s 缺 claim_text" % cid)
            if c.get("status") not in ("supported", "partial", "conflicting", "unsupported", "out_of_scope"):
                warnings.append("论断 %s 状态非法: %r" % (cid, c.get("status")))
            eids = c.get("evidence_ids")
            if eids is not None and not isinstance(eids, list):
                warnings.append("论断 %s evidence_ids 非列表" % cid)

# ---------- R4 证据表 ----------
evid, evid_ids = [], set()
SUPPORT = {"direct", "partial", "background", "conflicting", "not_supporting", "metadata"}
DOCTYPE = {"primary_study", "review", "guideline", "consensus", "preprint", "editorial", "dataset", "other"}
STRENGTH = {"A", "B", "C", "D"}
if nonempty(evid_p):
    with open(evid_p, encoding="utf-8", newline="") as f:
        try:
            for row in csv.DictReader(f):
                evid.append(row)
        except Exception as e:
            errors.append("evidence.csv 解析失败: %s" % e)
    for i, row in enumerate(evid):
        eid = row.get("evidence_id") or "row%d" % (i + 2)
        if row.get("evidence_id") in evid_ids:
            errors.append("evidence_id 重复: %s" % eid)
        evid_ids.add(row.get("evidence_id"))
        if not (row.get("quote") or "").strip():
            errors.append("证据 %s 缺原文摘录 quote" % eid)
        if not (row.get("location") or "").strip():
            warnings.append("证据 %s 缺定位 location（章节/页码）" % eid)
        if row.get("support_type") and row["support_type"] not in SUPPORT:
            warnings.append("证据 %s support_type 非法: %r" % (eid, row.get("support_type")))
        if row.get("doc_type") and row["doc_type"] not in DOCTYPE:
            warnings.append("证据 %s doc_type 非法: %r" % (eid, row.get("doc_type")))
        if row.get("strength") and row["strength"] not in STRENGTH:
            warnings.append("证据 %s strength 非法: %r" % (eid, row.get("strength")))

# ---------- R5 逐字核验 ----------
quote_report = []
for row in evid:
    eid = row.get("evidence_id")
    q = row.get("quote", "")
    if not q.strip():
        continue
    hits, msg = find_quote(q)
    quote_report.append({"evidence_id": eid, "found": bool(hits), "hits": hits or [], "note": msg})
    if hits:
        notes.append("摘录 %s 命中 %d 处" % (eid, len(hits)))
    else:
        if msg:
            warnings.append("摘录 %s 未核验: %s" % (eid, msg))
        else:
            errors.append("摘录 %s 在任何材料文本中都未找到（非逐字摘录或来源不明）" % eid)

# ---------- R6 成稿覆盖 ----------
draft = ""
if nonempty(draft_p):
    with open(draft_p, encoding="utf-8") as f:
        draft = f.read()
for c in claims:
    cid = c.get("claim_id")
    if not cid:
        continue
    if re.search(re.escape(cid) + r"\b", draft) or ("【%s】" % cid) in draft or ("[%s]" % cid) in draft:
        continue
    if c.get("status") in ("out_of_scope",):
        notes.append("论断 %s 显式排除于成稿（out_of_scope）" % cid)
    else:
        warnings.append("成稿未引用论断 %s（[%s] 标注缺失）" % (cid, cid))

# ---------- 方向专属检查 ----------
direction = "generic"
dcfg_p = os.path.join(SKILL, "direction.json")
dcfg = {}
if os.path.exists(dcfg_p):
    try:
        with open(dcfg_p, encoding="utf-8") as f:
            dcfg = json.load(f)
        direction = dcfg.get("direction", "generic")
    except Exception:
        pass
direction_notes = []

if direction == "evidence-extraction":
    man_p = os.path.join(OUTPUT, "doc_profile.json")
    if not nonempty(man_p):
        warnings.append("缺 doc_profile.json（文档画像与类型判定）")
    else:
        try:
            prof = json.load(open(man_p, encoding="utf-8"))
            docs = prof.get("documents", []) if isinstance(prof, dict) else []
            covered = {r.get("doc_id") for r in evid if r.get("doc_id")}
            for d in docs:
                if d.get("doc_id") not in covered:
                    direction_notes.append("文档 %s 无证据摘录（须在 doc_profile.json 说明排除理由）" % d.get("doc_id"))
        except Exception as e:
            warnings.append("doc_profile.json 解析失败: %s" % e)

elif direction == "claim-source-linking":
    for c in claims:
        if c.get("status") == "unsupported" and c.get("evidence_ids"):
            warnings.append("论断 %s 标 unsupported 但仍挂证据，关系矛盾" % c.get("claim_id"))
        if c.get("status") == "supported" and not c.get("evidence_ids"):
            errors.append("论断 %s 标 supported 但无证据" % c.get("claim_id"))
    used = {e for c in claims for e in (c.get("evidence_ids") or [])}
    multi = sum(1 for c in claims if len(c.get("evidence_ids") or []) > 1)
    shared = sum(1 for e in used if sum(1 for c in claims if e in (c.get("evidence_ids") or [])) > 1)
    direction_notes.append("多证据论断 %d 条；被多篇共用的证据 %d 条" % (multi, shared))

elif direction == "citation-accuracy":
    reg_p = os.path.join(OUTPUT, "reference_registry.json")
    audit_p = os.path.join(OUTPUT, "citation_audit.csv")
    if not nonempty(reg_p):
        warnings.append("缺 reference_registry.json（参考文献登记表）")
    if not nonempty(audit_p):
        warnings.append("缺 citation_audit.csv（引用核验表）")
    else:
        with open(audit_p, encoding="utf-8", newline="") as f:
            for i, row in enumerate(csv.DictReader(f)):
                if (row.get("in_text") or "").strip() in ("yes", "是") and not (row.get("in_list") or "").strip() in ("yes", "是"):
                    errors.append("引用 %s 文内出现但参考文献表缺失" % (row.get("ref_id") or i))
                if (row.get("metadata_complete") or "").strip() in ("no", "否"):
                    warnings.append("引用 %s 著录不完整: %s" % (row.get("ref_id"), row.get("missing_fields")))
                if (row.get("verification_path") or "").strip() == "":
                    warnings.append("引用 %s 缺可回查核验路径" % (row.get("ref_id")))
    for w in list(warnings):
        pass

elif direction == "evidence-strength":
    rp_ = os.path.join(OUTPUT, "strength_rationale.csv")
    if not nonempty(rp_):
        warnings.append("缺 strength_rationale.csv（分级判定理由表）")
    strong_verbs = dcfg.get("strong_verbs", ["证实", "证明", "决定", "根治", "消除"])
    weak_grade = {"C", "D"}
    for c in claims:
        if c.get("strength") in weak_grade:
            cid = c.get("claim_id")
            m = re.search(re.escape(cid), draft)
            seg = ""
            if m:
                seg = draft[max(0, m.start() - 120): m.end() + 120]
            else:
                seg = draft[:200]
            for v in strong_verbs:
                if v in seg:
                    errors.append("分级为 %s 的论断 %s 成稿中出现强断言动词 %r" % (c.get("strength"), cid, v))

elif direction == "uncertainty-expression":
    hr_p = os.path.join(OUTPUT, "hedging_report.json")
    if not nonempty(hr_p):
        warnings.append("缺 hedging_report.json（限定语审查报告）")
    causal = dcfg.get("causal_markers", ["导致", "引起", "证明了", "决定", "引发"])
    absolute = dcfg.get("absolute_markers", ["首次", "唯一", "彻底", "必然", "完全治愈", "无风险", "没有任何"])
    hits = []
    for ln, line in enumerate(draft.splitlines(), 1):
        for w in causal + absolute:
            if w in line:
                hits.append({"line": ln, "marker": w, "text": line.strip()[:100]})
    if hits:
        direction_notes.append("成稿中触发限定审查的表述 %d 处（须逐一在 hedging_report.json 有处置记录）" % len(hits))
    for c in claims:
        if c.get("status") == "conflicting":
            cid = c.get("claim_id")
            if cid not in draft:
                warnings.append("冲突论断 %s 未在成稿中呈现" % cid)


# ---------- R8 v2 增量检查（由 direction.json 开关驱动；未启用则跳过） ----------
if dcfg.get("instruction_audit"):
    da_p = os.path.join(OUTPUT, "draft_audit.json")
    if not nonempty(da_p):
        warnings.append("缺 draft_audit.json（题面指令落实审计，须运行 scripts/instruction_audit.py）")
    else:
        try:
            da = json.load(open(da_p, encoding="utf-8"))
            for it in da.get("instructions", []):
                if it.get("required") and it.get("passed") is False and it.get("type") in ("min_words", "max_words", "language"):
                    errors.append("题面硬约束未满足: %s（%s）" % (it.get("text", "")[:60], it.get("detail", "")))
                elif it.get("required") and it.get("passed") is False:
                    warnings.append("题面必含项疑似未覆盖: %s（%s）" % (it.get("text", "")[:60], it.get("detail", "")))
            for gc in da.get("genre_checks", []):
                if gc.get("passed") is False:
                    warnings.append("体裁结构未满足: %s" % gc.get("check"))
        except Exception as e:
            warnings.append("draft_audit.json 解析失败: %s" % e)

if dcfg.get("gain_audit"):
    ga_p = os.path.join(OUTPUT, "gain_audit.json")
    if not nonempty(ga_p):
        warnings.append("缺 gain_audit.json（增益拦截审计，须运行 scripts/gain_audit.py）")
    else:
        try:
            ga = json.load(open(ga_p, encoding="utf-8"))
            for m in ga.get("modes", []):
                if m.get("status") == "at_risk":
                    warnings.append("失败模式存在风险: %s %s — %s" % (m.get("mode_id"), m.get("mode"), m.get("evidence")))
            s = ga.get("summary", {})
            direction_notes.append("增益审计: 失败模式 %d 类中 intercepted %d / avoided %d / at_risk %d" % (
                s.get("total", 0), s.get("intercepted", 0), s.get("avoided", 0), s.get("at_risk", 0)))
        except Exception as e:
            warnings.append("gain_audit.json 解析失败: %s" % e)

if dcfg.get("span_verify"):
    sp_p = os.path.join(OUTPUT, "span_report.json")
    if not nonempty(sp_p):
        warnings.append("缺 span_report.json（分句级支撑核验，须运行 scripts/span_verify.py）")
    else:
        try:
            sp = json.load(open(sp_p, encoding="utf-8"))
            for v in sp.get("violations", []):
                errors.append("支撑范围核验失败: %s — %s" % (v.get("evidence_id"), v.get("reason")))
            direction_notes.append("分句级支撑核验: checked %d / skipped %d" % (sp.get("checked", 0), sp.get("skipped", 0)))
        except Exception as e:
            warnings.append("span_report.json 解析失败: %s" % e)

if dcfg.get("number_trace"):
    nt_p = os.path.join(OUTPUT, "number_trace.json")
    if not nonempty(nt_p):
        warnings.append("缺 number_trace.json（数值溯源核验，须运行 scripts/number_trace.py）")
    else:
        try:
            nt = json.load(open(nt_p, encoding="utf-8"))
            for v in nt.get("untraced", []):
                errors.append("成稿数值无来源: %s（%s）" % (v.get("number"), v.get("context", "")[:50]))
            for v in nt.get("in_source_not_evidence", []):
                warnings.append("数值见于材料但未入证据表: %s（%s）" % (v.get("number"), v.get("context", "")[:50]))
        except Exception as e:
            warnings.append("number_trace.json 解析失败: %s" % e)

# ---------- 回写 result.json ----------
report = {"errors": errors, "warnings": warnings, "notes": notes + direction_notes,
          "quote_verification": quote_report, "counts": {
              "claims": len(claims), "evidence": len(evid),
              "claims_with_evidence": sum(1 for c in claims if c.get("evidence_ids"))},
          "direction": direction}
ok = not errors and nonempty(claims_p) and nonempty(evid_p) and nonempty(draft_p)
if result:
    result["validation"] = {"errors": len(errors), "warnings": len(warnings),
                            "quote_check": "%d/%d 摘录逐字命中" % (
                                sum(1 for q in quote_report if q["found"]), max(1, len(quote_report))),
                            "report": "validation_report.json"}
    result["status"] = "success" if ok else "partial"
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)

with open(os.path.join(OUTPUT, "validation_report.json"), "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=1)

print(json.dumps({"direction": direction, "errors": len(errors), "warnings": len(warnings),
                  "status": "success" if ok else "partial"}, ensure_ascii=False))
sys.exit(0 if ok else 1)
