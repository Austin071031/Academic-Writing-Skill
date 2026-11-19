#!/usr/bin/env python3
"""verify_revision.py — 返修交付五重交叉核验（答得全 / 改得准 / 证得住 / 对得上 / 不杜撰）。

核验项：
1. coverage        comments.json 每个子要求在 dispositions.json 有 decision 且 response 非空；
                   每条意见 id 出现在 response_letter.md 中。
2. edit_claims     dispositions 引用的 edit op 全部真实应用成功（edit_report status=applied）；
                   声称"已修改"却无对应 op 的处置被列出。
3. location        每个 applied op 的 new_text 头部能在 revised_manuscript.md 中找到。
4. empty_talk      每条回复 ≥20 字且含可核查指涉（op id / 段落锚 / 证据编号 / 不采纳理由词）。
5. fabrication     applied op 的 new_text 中数字若在基线全文找不到、且非【待补】占位，
                   列入 unverified_numbers（写入 manual_confirmations，不自动判 FAIL）。

用法: python3 verify_revision.py --work /app/work --out /app/output [--baseline <path>]
exit 0=PASS 1=FAIL（前四项硬失败）
"""
import argparse, json, os, re, sys

RE_NUM = re.compile(r"\d+(?:\.\d+)?%?")
RE_OPID = re.compile(r"\bE\d+\b|OP\d+", re.I)
REASON_WORDS = re.compile(
    r"(因为|由于|依据|鉴于|无法|难以|超出|不在.*范围|待补|【证据|EV\d+|已在|已修改|已补充|"
    r"已删除|见第|如.*所示|P\d{3}|SEC\d+|because|since|cannot|unable|beyond the scope|"
    r"we (?:have )?(?:revised|added|removed|deleted|clarified|provided|discussed))", re.I)

def load_json(p, default=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--baseline", default=None)
    args = ap.parse_args()

    comments = load_json(os.path.join(args.work, "comments.json"), {}) or {}
    dispositions = load_json(os.path.join(args.work, "dispositions.json"), []) or []
    edit_report = load_json(os.path.join(args.work, "edit_report.json"), {}) or {}
    letter_p = os.path.join(args.out, "response_letter.md")
    revised_p = os.path.join(args.out, "revised_manuscript.md")
    letter = open(letter_p, encoding="utf-8").read() if os.path.exists(letter_p) else ""
    revised = open(revised_p, encoding="utf-8").read() if os.path.exists(revised_p) else ""

    baseline_text = ""
    base = args.baseline
    if not base:
        struct = load_json(os.path.join(args.work, "structure.json"), {}) or {}
        base = struct.get("source_file")
    if base and os.path.exists(base):
        for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
            try:
                with open(base, encoding=enc) as f:
                    baseline_text = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue

    checks = {}
    hard_fail = False

    # 1. coverage
    subs = [s for c in comments.get("comments", []) for s in c["sub_requests"]]
    disp_by_sub = {d.get("sub_id"): d for d in dispositions}
    missing = [s["sub_id"] for s in subs
               if s["sub_id"] not in disp_by_sub
               or not disp_by_sub[s["sub_id"]].get("decision")
               or not (disp_by_sub[s["sub_id"]].get("response") or "").strip()]
    letter_missing = [c["id"] for c in comments.get("comments", [])
                      if c["id"] not in letter and c["id"].replace("-C", " 意见") not in letter]
    checks["coverage"] = {"n_subs": len(subs), "n_dispositions": len(dispositions),
                          "missing_subs": missing, "comments_missing_in_letter": letter_missing,
                          "pass": not missing and not letter_missing}
    if missing or letter_missing:
        hard_fail = True

    # 2. edit_claims
    ops = {o["op_id"]: o for o in edit_report.get("ops", [])}
    applied = {k for k, v in ops.items() if v["status"] == "applied"}
    bad_refs, claims_without_edit = [], []
    for d in dispositions:
        for opid in d.get("edit_ops", []):
            if opid not in ops:
                bad_refs.append((d.get("sub_id"), opid, "op 不存在"))
            elif opid not in applied:
                bad_refs.append((d.get("sub_id"), opid, f"op 状态={ops[opid]['status']}"))
        if d.get("decision") in ("采纳", "部分采纳") and not d.get("edit_ops") \
                and not d.get("evidence") and not REASON_WORDS.search(d.get("response", "")):
            claims_without_edit.append(d.get("sub_id"))
    checks["edit_claims"] = {"n_applied_ops": len(applied), "bad_refs": bad_refs,
                             "claims_without_edit": claims_without_edit,
                             "pass": not bad_refs}
    if bad_refs:
        hard_fail = True

    # 3. location
    not_found = []
    for o in edit_report.get("ops", []):
        if o["status"] == "applied" and o.get("new_text_head"):
            head = o["new_text_head"][:30].strip()
            if head and head not in revised:
                not_found.append(o["op_id"])
    checks["location"] = {"not_found_in_revised": not_found, "pass": not not_found}
    if not_found:
        hard_fail = True

    # 4. empty_talk
    empty = []
    for d in dispositions:
        resp = (d.get("response") or "").strip()
        if len(resp) < 20 or not (RE_OPID.search(resp) or REASON_WORDS.search(resp)):
            empty.append(d.get("sub_id"))
    checks["empty_talk"] = {"weak_responses": empty, "pass": not empty}
    if empty:
        hard_fail = True

    # 5. fabrication guard（软告警）
    base_nums = set(RE_NUM.findall(baseline_text))
    unverified = []
    for o in edit_report.get("ops", []):
        if o["status"] != "applied" or o.get("has_placeholder"):
            continue
    plan = load_json(os.path.join(args.work, "edit_plan.json"), []) or []
    for op in plan:
        nt = op.get("new_text") or ""
        if "【待补" in nt:
            continue
        for num in set(RE_NUM.findall(nt)):
            if num not in base_nums and num.rstrip("%") not in baseline_text:
                unverified.append({"op_id": op.get("op_id"), "number": num})
    checks["fabrication"] = {"unverified_numbers": unverified,
                             "pass": True,
                             "note": "数字未在基线出现且非占位：须确认为意见给出的数值或写入人工确认"}

    overall = all(c["pass"] for c in checks.values()) and not hard_fail
    out = {"overall_pass": overall, "checks": checks}
    with open(os.path.join(args.out, "verification.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for name, c in checks.items():
        print(f"[verify] {name}: {'PASS' if c['pass'] else 'FAIL'}")
    if unverified:
        print(f"[verify][WARN] 未核实数字 {len(unverified)} 处，须写入 manual_confirmations",
              file=sys.stderr)
    print(f"[verify] overall={'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1

if __name__ == "__main__":
    sys.exit(main())
