#!/usr/bin/env python3
"""verify_engine.py — 版本5「来源核验与一致性检查（对得上）」专属引擎。

两层核验：
  (a) 条目级真实性体检（纯本地、确定性）：
      doi_syntax / year_plausibility / field_conflict /
      duplicate_title_in_library / title_ends_with_period
      每条体检给 verdict ∈ {verified_internal, suspicious, insufficient_metadata, note} + evidence。
  (b) 论断级引用匹配裁决汇总：
      读取 Agent 写的 work/match_verdicts.jsonl（每行
      {pid, sentence, entry_ids[], verdict(supports|partially|unrelated|insufficient_evidence), rationale}），
      审计覆盖率（缺漏列出），生成 evidence_map.json、annotated_manuscript.md。

联网核验（可选，--online）：urllib 请求 https://api.crossref.org/works/<doi>，timeout=5；
成功比对题名相似度（≥0.8 → verified_online，否则 metadata_mismatch）；失败记 unverified_offline。
默认离线运行同样产出完整报告，联网状态如实标注。

用法:
  python3 verify_engine.py --library work/library.json --manuscript work/manuscript.json \
      --verdicts work/match_verdicts.jsonl --work /app/work --out /app/output [--online]

输出:
  <out>/verification_report.json   机读：逐条目体检 + 联网状态 + 逐论断裁决 + 覆盖审计 + 编号一致性
  <out>/verification_report.md     人读：可疑条目表 / 不匹配论断表 / 证据不足清单 / 总体结论
  <out>/annotated_manuscript.md    在不匹配/证据不足论断句后插 <!-- ⚠ verdict: ... -->，原文可编辑
  work/evidence_map.json           由 match_verdicts 生成（assemble_result.py 汇总用）
  work/stats.json / uncertainty.json / exceptions.json  合并写入
另调用 cite_engine.py audit 做编号连续性体检，结论并入报告（consistency_audit.json 同时复制到 out）。
"""
import argparse, difflib, json, os, re, subprocess, sys, datetime, urllib.parse, urllib.request

CURRENT_YEAR = 2026  # 运行时上限；本地体检的合理年份窗口 1500–CURRENT_YEAR
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
DOI_BAD_CHARS = re.compile(r"[\s<>'\"\\]")
VERDICT_SET = {"supports", "partially", "unrelated", "insufficient_evidence"}
FLAG_VERDICTS = {"partially", "unrelated", "insufficient_evidence"}


# ---------------- 通用工具 ----------------

def norm_text(s):
    """归一化用于相似度比较：小写、去标点、压缩空白。"""
    s = (s or "").lower()
    s = re.sub(r"[\W_]+", " ", s, flags=re.UNICODE)
    return " ".join(s.split())

def similarity(a, b):
    a, b = norm_text(a), norm_text(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()

def norm_author(a):
    a = (a or "").lower().strip()
    a = re.sub(r"[,.，。;；\s]+", "", a)
    return a

def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def merge_json_file(path, updater):
    """读旧 JSON（list 或 dict），用 updater 变换后写回。"""
    old = load_json(path, None)
    new = updater(old)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[verify_engine] 无法写 {path}: {e}", file=sys.stderr)

def mk(check, verdict, evidence):
    return {"check": check, "verdict": verdict, "evidence": evidence}


# ---------------- (a) 条目级体检 ----------------

def check_doi_syntax(rec):
    doi = (rec.get("doi") or "").strip()
    if not doi:
        return mk("doi_syntax", "insufficient_metadata",
                  "条目无 DOI 字段；本地无法做 DOI 语法体检（非判定造假）")
    if DOI_RE.match(doi) and not DOI_BAD_CHARS.search(doi):
        return mk("doi_syntax", "verified_internal",
                  f"DOI '{doi}' 符合注册语法 10.XXXX(4-9位)/后缀")
    return mk("doi_syntax", "suspicious",
              f"DOI '{doi}' 不符合注册规则 10.\\d{{4,9}}/…"
              + ("（含空白/非法字符）" if DOI_BAD_CHARS.search(doi) else "（前缀或结构非法）"))

def check_year(rec):
    y = rec.get("year")
    if not y:
        return mk("year_plausibility", "insufficient_metadata", "条目无年份字段")
    try:
        yi = int(str(y)[:4])
    except ValueError:
        return mk("year_plausibility", "suspicious", f"年份 '{y}' 无法解析为整数年份")
    if 1500 <= yi <= CURRENT_YEAR:
        return mk("year_plausibility", "verified_internal", f"年份 {yi} 在 1500–{CURRENT_YEAR} 合理区间")
    return mk("year_plausibility", "suspicious",
              f"年份 {yi} 超出 1500–{CURRENT_YEAR} 合理区间（晚于当前年份或为远古值）")

def check_field_conflict(rec):
    if rec.get("entry_type") != "journal_article":
        return mk("field_conflict", "verified_internal",
                  f"类型 {rec.get('entry_type')} 不适用刊名/卷期页缺失体检")
    missing = [k for k in ("venue", "volume", "issue", "pages") if not rec.get(k)]
    if len(missing) == 4:
        return mk("field_conflict", "suspicious",
                  "类型为 journal_article 但刊名、卷、期、页全部缺失——正规期刊条目极少如此，疑似编造/残缺条目")
    return mk("field_conflict", "verified_internal",
              f"刊名/卷/期/页 至少存在其一（缺失: {missing or '无'}）")

def check_title_period(rec):
    t = (rec.get("title") or "").rstrip()
    if t.endswith((".", "。")):
        return mk("title_ends_with_period", "note",
                  "题名著录以句点结尾（轻量提示：多为录入笔误，不影响真实性判定）")
    return mk("title_ends_with_period", "verified_internal", "题名著录无句点结尾")

def health_checks(records):
    """对全部记录做本地体检；重复题名检查需要两两比较。"""
    results = {}
    norm_titles = {r["id"]: norm_text(r.get("title")) for r in records}
    first_auth = {r["id"]: norm_author((r.get("authors") or [""])[0]) for r in records}
    dup_of = {}
    for i, ra in enumerate(records):
        for rb in records[i + 1:]:
            ta, tb = norm_titles[ra["id"]], norm_titles[rb["id"]]
            if not ta or not tb:
                continue
            if similarity(ra.get("title"), rb.get("title")) > 0.95:
                if first_auth[ra["id"]] and first_auth[ra["id"]] == first_auth[rb["id"]]:
                    dup_of.setdefault(ra["id"], []).append(rb["id"])
                    dup_of.setdefault(rb["id"], []).append(ra["id"])
    for r in records:
        checks = [check_doi_syntax(r), check_year(r),
                  check_field_conflict(r), check_title_period(r)]
        if r["id"] in dup_of:
            others = ", ".join(dup_of[r["id"]])
            checks.append(mk("duplicate_title_in_library", "suspicious",
                             f"与 {others} 题名相似度>0.95 且第一作者相同，疑似重复录入"))
        else:
            checks.append(mk("duplicate_title_in_library", "verified_internal",
                             "库内无高相似同作者重复条目"))
        # 条目级总体判定
        if any(c["verdict"] == "suspicious" for c in checks):
            overall = "suspicious"
        elif not norm_text(r.get("title")):
            overall = "insufficient_metadata"
            checks.append(mk("title_present", "insufficient_metadata", "条目缺题名，无法做多数体检"))
        else:
            overall = "verified_internal"
        results[r["id"]] = {"id": r["id"], "title": r.get("title") or "",
                            "entry_type": r.get("entry_type"), "year": r.get("year"),
                            "doi": r.get("doi") or "", "overall": overall,
                            "checks": checks}
    return results


# ---------------- (a2) 联网核验 Crossref ----------------

def crossref_verify(doi, timeout=5):
    """返回 (status, evidence)。绝不抛出。"""
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi.strip(), safe="")
    req = urllib.request.Request(url, headers={
        "User-Agent": "citation-verification-audit/5.0 (skill; mailto:skill@example.invalid)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data.get("message", {})
        cr_titles = msg.get("title") or []
        return msg, cr_titles
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def online_checks(entry_results, timeout=5):
    """对每条目给 online_status ∈ {verified_online, metadata_mismatch, unverified_offline,
    online_skipped_no_doi, online_skipped_invalid_doi, not_attempted_offline_mode}。"""
    for eid, e in entry_results.items():
        doi = (e.get("doi") or "").strip()
        if not doi:
            e["online_status"] = "online_skipped_no_doi"
            e["online_evidence"] = "条目无 DOI，跳过联网核验"
            continue
        if not (DOI_RE.match(doi) and not DOI_BAD_CHARS.search(doi)):
            e["online_status"] = "online_skipped_invalid_doi"
            e["online_evidence"] = "DOI 语法体检未通过，不浪费联网请求"
            continue
        msg, titles = crossref_verify(doi, timeout)
        if msg is None:
            e["online_status"] = "unverified_offline"
            e["online_evidence"] = f"Crossref 请求失败（{titles}）；网络不可用或超时，如实记为未联网核验"
            continue
        if not titles:
            e["online_status"] = "metadata_mismatch"
            e["online_evidence"] = f"Crossref 记录 {doi} 无题名，与本地条目无法比对"
            continue
        sim = similarity(e.get("title"), titles[0])
        if sim >= 0.8:
            e["online_status"] = "verified_online"
            e["online_evidence"] = (f"Crossref 题名相似度 {sim:.2f}≥0.8：'{titles[0][:80]}'")
        else:
            e["online_status"] = "metadata_mismatch"
            e["online_evidence"] = (f"Crossref 题名相似度 {sim:.2f}<0.8：注册题名为 '{titles[0][:80]}'")
    return entry_results


# ---------------- (b) 裁决审计 + evidence_map ----------------

def read_verdicts(path, paragraphs, lib_ids):
    """读取 Agent 的 match_verdicts.jsonl 并审计。返回 (claims, audit)。"""
    claims, audit_issues = [], []
    covered = {}
    para_by_id = {p["pid"]: p for p in paragraphs}
    if not os.path.exists(path):
        return [], [{"type": "verdicts_missing",
                     "detail": f"match_verdicts.jsonl 不存在: {path}（Agent 未写裁决，全部带引用段落计为缺漏）"}]
    lineno = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            lineno += 1
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                audit_issues.append({"type": "verdict_bad_json",
                                     "detail": f"第 {lineno} 行非合法 JSON: {e}"})
                continue
            pid = obj.get("pid"); v = obj.get("verdict")
            if v not in VERDICT_SET:
                audit_issues.append({"type": "verdict_bad_value",
                                     "detail": f"第 {lineno} 行 verdict='{v}' 非法，应为 {sorted(VERDICT_SET)}"})
            p = para_by_id.get(pid)
            if p is None:
                audit_issues.append({"type": "verdict_bad_pid",
                                     "detail": f"第 {lineno} 行 pid='{pid}' 不在稿件段落中"})
            else:
                sent = norm_text(obj.get("sentence"))
                ptext = norm_text(p.get("text"))
                if sent and (sent in ptext
                             or difflib.SequenceMatcher(None, sent, ptext).ratio() >= 0.5):
                    pass
                else:
                    audit_issues.append({"type": "verdict_sentence_mismatch",
                                         "detail": f"第 {lineno} 行 sentence 与 {pid} 段落文本对不上，按段落级裁决处理"})
            bad_entries = [e for e in (obj.get("entry_ids") or []) if e not in lib_ids]
            if bad_entries:
                audit_issues.append({"type": "verdict_bad_entry",
                                     "detail": f"第 {lineno} 行 entry_ids {bad_entries} 不在文献库中"})
            if not obj.get("rationale"):
                audit_issues.append({"type": "verdict_no_rationale",
                                     "detail": f"第 {lineno} 行缺 rationale（裁决必须引用双方原文短语）"})
            claims.append({"pid": pid, "sentence": obj.get("sentence", ""),
                           "entry_ids": obj.get("entry_ids") or [], "verdict": v,
                           "rationale": obj.get("rationale", ""), "line": lineno})
            covered.setdefault(pid, 0)
            covered[pid] += 1
    return claims, audit_issues

def build_evidence_map(claims, entry_results):
    em = []
    for i, c in enumerate(claims, 1):
        verif = "; ".join(f"{eid}={entry_results.get(eid, {}).get('overall', 'unknown')}"
                          for eid in c["entry_ids"]) or "no_entry"
        em.append({"claim_id": f"C{i:03d}", "pid": c["pid"], "entry_id": c["entry_ids"],
                   "location": f"manuscript#{c['pid']}",
                   "source": f"稿件句子 + 文献库条目 {c['entry_ids'] or '∅'}",
                   "support": c["verdict"], "rationale": c["rationale"],
                   "verification": verif})
    return em


# ---------------- annotated manuscript ----------------

def annotate(paragraphs, claims):
    """在不匹配/证据不足/部分匹配论断句后插 <!-- ⚠ verdict: ... -->；原文不动。"""
    by_pid = {}
    for c in claims:
        if c["verdict"] in FLAG_VERDICTS:
            by_pid.setdefault(c["pid"], []).append(c)
    out_lines = []
    for p in paragraphs:
        text = p["text"]
        if p["pid"] in by_pid:
            for c in by_pid[p["pid"]]:
                sent = (c["sentence"] or "").strip()
                note = (f"<!-- ⚠ verdict: {c['verdict']} | entries: {','.join(c['entry_ids']) or '∅'} "
                        f"| rationale: {c['rationale']} -->")
                inserted = False
                # 尝试在论断句原句之后插入；找不到（或句子为空，如缺裁决占位）则段落行尾追加
                for m in (re.finditer(re.escape(sent[:40]) if len(sent) >= 40 else re.escape(sent), text)
                          if sent else iter([])):
                    tail = len(sent)
                    pos = m.start() + tail
                    while pos < len(text) and text[pos] not in "。！？.!?\n":
                        pos += 1
                    text = text[:pos] + " " + note + text[pos:]
                    inserted = True
                    break
                if not inserted:
                    text = text.rstrip() + "\n\n" + note
        out_lines.append(text)
    return "\n\n".join(out_lines) + "\n"


# ---------------- 报告 ----------------

def build_report(entry_results, claims, coverage, audit_issues, consistency, mode, case_id):
    n = len(entry_results)
    sus = [e for e in entry_results.values() if e["overall"] == "suspicious"]
    ins = [e for e in entry_results.values() if e["overall"] == "insufficient_metadata"]
    vcount = {}
    for c in claims:
        vcount[c["verdict"]] = vcount.get(c["verdict"], 0) + 1
    ocount = {}
    for e in entry_results.values():
        ocount[e.get("online_status", "?")] = ocount.get(e.get("online_status", "?"), 0) + 1
    conclusion = "pass"
    if sus or coverage["missing_pids"] or vcount.get("unrelated") or vcount.get("insufficient_evidence"):
        conclusion = "issues_found"
    if not claims and coverage["cited_body_pids"]:
        conclusion = "incomplete"
    return {
        "case_id": case_id, "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": mode, "conclusion": conclusion,
        "summary": {"n_entries": n, "n_suspicious_entries": len(sus),
                    "n_insufficient_metadata": len(ins),
                    "online_status_counts": ocount,
                    "claim_verdict_counts": vcount,
                    "cited_body_pids": coverage["cited_body_pids"],
                    "covered_pids": coverage["covered_pids"],
                    "missing_pids": coverage["missing_pids"]},
        "entries": list(entry_results.values()),
        "claims": claims,
        "coverage": coverage,
        "verdict_audit_issues": audit_issues,
        "consistency": consistency,
        "limits": ("离线模式下联网状态为 unverified_offline/not_attempted_offline_mode，"
                   "仅表示未联网核验，不表示条目造假；条目真实性最终判定需人工或联网复核。"),
    }

def md_report(rep):
    s = rep["summary"]
    L = []
    L.append("# 来源核验与一致性检查报告\n")
    L.append(f"- case_id: {rep['case_id']}    模式: {rep['mode']}    生成时间: {rep['generated_at']}")
    L.append(f"- 总体结论: **{rep['conclusion']}**（issues_found=存在可疑条目或不匹配论断；"
             f"incomplete=裁决缺漏；pass=本地体检与裁决均通过）")
    L.append(f"- 条目 {s['n_entries']} 条：可疑 {s['n_suspicious_entries']}，元数据不足 "
             f"{s['n_insufficient_metadata']}；联网状态分布 {s['online_status_counts']}")
    L.append(f"- 论断裁决 {sum(s['claim_verdict_counts'].values())} 条：{s['claim_verdict_counts']}")
    L.append(f"- 带引用正文段落 {len(s['cited_body_pids'])} 个，已覆盖 {len(s['covered_pids'])} 个，"
             f"缺漏 {s['missing_pids'] or '无'}\n")
    # 可疑条目表
    L.append("## 可疑条目表（本地体检 suspicious）\n")
    sus = [e for e in rep["entries"] if e["overall"] == "suspicious"]
    if sus:
        L.append("| 条目 | 题名 | 可疑体检项 | evidence |")
        L.append("|---|---|---|---|")
        for e in sus:
            bad = [c for c in e["checks"] if c["verdict"] == "suspicious"]
            for c in bad:
                L.append(f"| {e['id']} | {(e['title'] or '')[:50]} | {c['check']} | {c['evidence']} |")
    else:
        L.append("（无）")
    L.append("")
    # 联网状态
    L.append("## 联网核验状态（Crossref）\n")
    L.append("| 状态 | 数量 |")
    L.append("|---|---|")
    for k, v in sorted(rep["summary"]["online_status_counts"].items()):
        L.append(f"| {k} | {v} |")
    mism = [e for e in rep["entries"] if e.get("online_status") == "metadata_mismatch"]
    for e in mism:
        L.append(f"\n- ⚠ {e['id']} metadata_mismatch: {e['online_evidence']}")
    L.append("")
    # 不匹配论断表
    L.append("## 不匹配/部分匹配论断表\n")
    flagged = [c for c in rep["claims"] if c["verdict"] in ("unrelated", "partially")]
    if flagged:
        L.append("| pid | 论断句 | 所引条目 | 裁决 | rationale |")
        L.append("|---|---|---|---|---|")
        for c in flagged:
            L.append(f"| {c['pid']} | {(c['sentence'] or '')[:60]} | {','.join(c['entry_ids']) or '∅'} "
                     f"| {c['verdict']} | {c['rationale']} |")
    else:
        L.append("（无）")
    L.append("")
    # 证据不足清单
    L.append("## 证据不足清单（insufficient_evidence）\n")
    insuf = [c for c in rep["claims"] if c["verdict"] == "insufficient_evidence"]
    if insuf:
        for c in insuf:
            L.append(f"- {c['pid']}: “{(c['sentence'] or '')[:80]}” — 所引 {','.join(c['entry_ids']) or '∅'}；"
                     f"缺什么/为何不足：{c['rationale']}")
    else:
        L.append("（无）")
    L.append("")
    # 覆盖审计
    L.append("## 裁决覆盖审计\n")
    if rep["coverage"]["missing_pids"]:
        L.append(f"⚠ 以下带引用正文段落没有对应裁决行（Agent 漏判，已在正文标注请补裁决）: "
                 f"{rep['coverage']['missing_pids']}")
    else:
        L.append("全部带引用正文段落均已覆盖。")
    for iss in rep["verdict_audit_issues"]:
        L.append(f"- [{iss['type']}] {iss['detail']}")
    L.append("")
    # 一致性
    L.append("## 编号一致性（cite_engine audit）\n")
    cs = rep.get("consistency") or {}
    L.append(f"- 文献表条数 n_refs={cs.get('n_refs')}，正文标记 {cs.get('n_inline_marks')} 处，"
             f"越界 {cs.get('out_of_range') or '无'}，缺口 {cs.get('gaps') or '无'}，"
             f"顺序连续={cs.get('sequential')}，样式一致={cs.get('style_consistent')}")
    for i in (cs.get("issues") or []):
        L.append(f"- [{i.get('type')}] {i.get('detail')}")
    L.append("")
    # 总体结论
    L.append("## 总体结论与诚实声明\n")
    L.append(f"- 结论：**{rep['conclusion']}**")
    L.append(f"- {rep['limits']}")
    L.append("- 本地体检只发现'像编造的条目'，绝不声称确证造假；supports 裁决只表示材料内主题匹配，"
             "不担保文献真实存在。")
    return "\n".join(L) + "\n"


# ---------------- 主流程 ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--library", default="/app/work/library.json")
    ap.add_argument("--manuscript", default="/app/work/manuscript.json")
    ap.add_argument("--verdicts", default="/app/work/match_verdicts.jsonl")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--online", action="store_true", help="联网核验 Crossref（timeout=5s/条，失败诚实降级）")
    ap.add_argument("--timeout", type=float, default=5.0)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    lib = load_json(args.library, None)
    ms = load_json(args.manuscript, None)
    if lib is None or ms is None:
        print("[verify_engine] library.json 或 manuscript.json 缺失，无法核验", file=sys.stderr)
        return 2
    records = lib.get("records") or []
    paragraphs = ms.get("paragraphs") or []

    # (a) 条目体检 + 联网
    entry_results = health_checks(records)
    mode = "offline"
    if args.online:
        mode = "online"
        online_checks(entry_results, timeout=args.timeout)
    else:
        for e in entry_results.values():
            doi_ok = e["online_status"] = ("not_attempted_offline_mode" if (DOI_RE.match((e.get('doi') or '').strip())
                                            and not DOI_BAD_CHARS.search(e.get('doi') or '')) else "online_skipped_no_doi_or_invalid")
            e["online_evidence"] = ("离线模式未发联网请求（可加 --online 复核）；此为未核验状态，非造假判定"
                                    if "not_attempted" in e["online_status"]
                                    else "无 DOI 或 DOI 语法未通过，无需联网")

    # (b) 裁决审计
    lib_ids = {r["id"] for r in records}
    claims, audit_issues = read_verdicts(args.verdicts, paragraphs, lib_ids)
    cited_pids = [p["pid"] for p in paragraphs if p["kind"] == "body" and p.get("cite_marks")]
    covered_pids = sorted({c["pid"] for c in claims if c["pid"] in cited_pids})
    coverage = {"cited_body_pids": cited_pids, "covered_pids": covered_pids,
                "missing_pids": [p for p in cited_pids if p not in set(covered_pids)]}

    # 一致性联动：cite_engine audit
    consistency = {}
    ce = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cite_engine.py")
    try:
        subprocess.run([sys.executable, ce, "audit", "--manuscript", args.manuscript,
                        "--nrefs", str(len(records))],
                       capture_output=True, timeout=60)
        ca_path = os.path.join(os.path.dirname(args.manuscript) or ".", "consistency_audit.json")
        consistency = load_json(ca_path, {}) or {}
        if os.path.exists(ca_path):
            with open(ca_path, encoding="utf-8") as f:
                dest = os.path.join(args.out, "consistency_audit.json")
                with open(dest, "w", encoding="utf-8") as g:
                    g.write(f.read())
    except Exception as e:
        audit_issues.append({"type": "consistency_failed", "detail": f"cite_engine audit 调用失败: {e}"})

    insp = load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    rep = build_report(entry_results, claims, coverage, audit_issues, consistency, mode,
                       insp.get("case_id") or "unknown")

    with open(os.path.join(args.out, "verification_report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "verification_report.md"), "w", encoding="utf-8") as f:
        f.write(md_report(rep))
    # 兼容共享脚本命名约定：报告同时以 report.md 落盘，供 assemble_result/render_previews 消费
    with open(os.path.join(args.out, "report.md"), "w", encoding="utf-8") as f:
        f.write(md_report(rep))

    # annotated manuscript：缺漏段落也要标注（请 Agent 补裁决）
    missing_note = [{"pid": pid, "sentence": "", "entry_ids": [],
                   "verdict": "insufficient_evidence",
                   "rationale": "【引擎审计】该带引用段落缺少 Agent 裁决行，请补 match_verdicts.jsonl；暂记证据不足"} for pid in coverage["missing_pids"]]
    annotated = annotate(paragraphs, claims + missing_note)
    with open(os.path.join(args.out, "annotated_manuscript.md"), "w", encoding="utf-8") as f:
        f.write(annotated)
    # 标注稿即"可编辑审校稿"，按共享约定同时落 edited_manuscript.md 供预览/组装消费
    with open(os.path.join(args.out, "edited_manuscript.md"), "w", encoding="utf-8") as f:
        f.write(annotated)

    # work/ 中间产物
    merge_json_file(os.path.join(args.work, "evidence_map.json"),
                    lambda _old: build_evidence_map(claims, entry_results))
    stats = {"entries_total": rep["summary"]["n_entries"],
             "entries_suspicious": rep["summary"]["n_suspicious_entries"],
             "claims_total": sum(rep["summary"]["claim_verdict_counts"].values()),
             "claims_flagged": sum(v for k, v in rep["summary"]["claim_verdict_counts"].items()
                                   if k in FLAG_VERDICTS),
             "coverage_missing_pids": coverage["missing_pids"],
             "mode": mode, "conclusion": rep["conclusion"]}
    merge_json_file(os.path.join(args.work, "stats.json"),
                    lambda old: {**(old if isinstance(old, dict) else {}), **stats})
    unc = [{"item": f"条目 {e['id']}", "reason": c["evidence"], "severity": "warning"}
           for e in entry_results.values() for c in e["checks"]
           if c["verdict"] in ("suspicious", "insufficient_metadata")]
    unc += [{"item": f"论断 {c['pid']}", "reason": f"{c['verdict']}: {c['rationale']}",
             "severity": "info"} for c in claims if c["verdict"] in FLAG_VERDICTS]
    merge_json_file(os.path.join(args.work, "uncertainty.json"),
                    lambda old: (old if isinstance(old, list) else []) + unc)
    exc = [{"type": i["type"], "detail": i["detail"], "handled": "记录在报告 coverage/audit 节"}
           for i in audit_issues]
    merge_json_file(os.path.join(args.work, "exceptions.json"),
                    lambda old: (old if isinstance(old, list) else []) + exc)

    print(f"[verify_engine] 条目 {rep['summary']['n_entries']}（可疑 {rep['summary']['n_suspicious_entries']}）"
          f" 论断 {sum(rep['summary']['claim_verdict_counts'].values())}"
          f" 缺漏段落 {coverage['missing_pids'] or '无'} 结论={rep['conclusion']} 模式={mode}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
