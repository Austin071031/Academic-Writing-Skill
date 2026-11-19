#!/usr/bin/env python3
"""place_citations.py — 版本1 专属：论断级引用定位与插入引擎（确定性，纯标准库）。

输入:
  --decisions  work/citation_decisions.jsonl  （Agent 写；每行一条 JSON）
      {claim_id, pid, sentence, claim_type, entry_ids[], rationale,
       position: "after_sentence"(默认)|"before_sentence",
       form: "numeric"|"author_year"(可缺省，缺省跟随 --form)}
  --manuscript work/manuscript.json   （parse_manuscript.py 产物）
  --library    work/library.json      （parse_library.py 产物）
  --style      gbt2015_numeric|gbt2015_author|apa7|vancouver （渲染参考文献表样式）
  --form       auto|numeric|author_year（全局引用形式；auto 按 --style 推断；
               decision 级 form 字段优先）

职责（全部确定性，不做任何判断）:
  1. 在指定 pid 段落内定位 sentence 文本，在论断句末（终结标点之前）插入引用标记；
     定位失败 -> 记入 work/exceptions.json 并跳过，绝不臆造插入位置。
  2. 同一句子的多条引用合并为一个标记 [n,m] /（著者, 年; 著者, 年）。
  3. 按首次出现顺序对全部 numeric 标记全局重排，编号 1..N 连续。
  4. 调用 cite_engine.py render 生成 /app/output/references.md（按引用顺序排列）。
  5. 插入后全文写 /app/output/edited_manuscript.md（保留原段落结构与标题）。
  6. 写 work/placement_audit.json：段末 30 字符错放疑似、一句多引合并、多句一引展开。
  7. 写 work/change_log.json / work/evidence_map.json / work/stats.json 供 assemble 汇总。

默认行为（可用开关改变）:
  --keep-existing  保留稿件中已有的 numeric 标记；默认剥除并逐条记入 change_log
                   （版本1 以 Agent 的 decisions 为权威引用集，旧标记视为待整理对象）。
  --keep-old-refs  保留稿件末尾旧参考文献段落；默认移除（新表见 references.md）并记录。
"""
import argparse, json, os, re, subprocess, sys

SENT_END = "。！？!?；;.．"
CJK_RE = re.compile(r"[一-鿿]")
NUM_MARK_RE = re.compile(r"\[(\d+(?:\s*[-–—,，]\s*\d+)*)\]")


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, obj):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def expand_nums(raw):
    nums = []
    for part in re.split(r"[,，]", raw):
        part = part.strip()
        m = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 0 < b - a <= 200:
                nums.extend(range(a, b + 1))
        elif part.isdigit():
            nums.append(int(part))
    return nums


def compress_nums(nums):
    nums = sorted(set(nums))
    if not nums:
        return ""
    out, start, prev = [], nums[0], nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        out.append(f"{start}-{prev}" if prev > start else f"{start}")
        start = prev = n
    out.append(f"{start}-{prev}" if prev > start else f"{start}")
    return ",".join(out)


def flex_pattern(sentence):
    """空白宽容匹配：任意空白（含换行、全角空格）对应 \\s+。"""
    pat = re.escape(sentence.strip())
    pat = re.sub(r"(\\ )+|(\\　)+", r"\\s+", pat)
    pat = pat.replace("\\ ", r"\s+")
    return pat


def find_sentence_span(text, sentence):
    """三级定位：精确 -> 空白宽容正则 -> 去空白映射。返回 (start, end) 或 None。"""
    sentence = (sentence or "").strip()
    if not sentence:
        return None
    idx = text.find(sentence)
    if idx >= 0:
        return (idx, idx + len(sentence))
    try:
        m = re.search(flex_pattern(sentence), text)
        if m:
            return (m.start(), m.end())
    except re.error:
        pass
    # 去空白映射
    stripped, idx_map = [], []
    for i, ch in enumerate(text):
        if not ch.isspace():
            stripped.append(ch)
            idx_map.append(i)
    needle = "".join(ch for ch in sentence if not ch.isspace())
    pos = "".join(stripped).find(needle)
    if pos >= 0 and needle:
        return (idx_map[pos], idx_map[pos + len(needle) - 1] + 1)
    return None


def insertion_point(text, span, position):
    """计算插入偏移。after_sentence: 论断句末、终结标点之前。"""
    s, e = span
    while e > s and text[e - 1].isspace():
        e -= 1
    if position == "before_sentence":
        return s
    if e > s and text[e - 1] in SENT_END:
        return e - 1
    if e < len(text) and text[e] in SENT_END:
        return e
    return e


def author_key(rec):
    """第一作者（姓/中文全名）+ 年份，用于著者-出版年标签与同名同年消歧。"""
    name = ""
    authors = rec.get("authors") or []
    if authors:
        a = authors[0]
        if "," in a:
            name = a.split(",", 1)[0].strip()
        elif CJK_RE.search(a):
            name = a.strip()
        else:
            name = a.split()[-1] if a.split() else a.strip()
    return name, (rec.get("year") or "n.d.")


def make_mark(form, nums, recs, cjk, labels=None):
    if form == "author_year":
        if labels is None:
            sep = "，" if cjk else ", "
            labels = [f"{author_key(r)[0]}{sep}{author_key(r)[1]}" for r in recs]
        if cjk:
            return "（" + "；".join(labels) + "）"
        return "(" + "; ".join(labels) + ")"
    return "[" + compress_nums(nums) + "]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisions", required=True)
    ap.add_argument("--manuscript", required=True)
    ap.add_argument("--library", required=True)
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--style", default="gbt2015_numeric")
    ap.add_argument("--form", default="auto", choices=["auto", "numeric", "author_year"])
    ap.add_argument("--keep-existing", action="store_true")
    ap.add_argument("--keep-old-refs", action="store_true")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)
    exceptions, change_log, evidence, uncertainty = [], [], [], []

    ms = load_json(args.manuscript)
    lib = load_json(args.library, {}) or {}
    if ms is None:
        print("[place_citations][FATAL] manuscript.json 不可读", file=sys.stderr)
        return 1
    recs_by_id = {r["id"]: r for r in lib.get("records", [])}
    paras = {p["pid"]: p for p in ms.get("paragraphs", [])}
    ordered_pids = [p["pid"] for p in ms.get("paragraphs", [])]

    global_form = args.form
    if global_form == "auto":
        global_form = "author_year" if args.style in ("gbt2015_author", "apa7") else "numeric"

    # ---------- 读取 decisions ----------
    decisions = []
    with open(args.decisions, encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                d["_line"] = ln
                decisions.append(d)
            except json.JSONDecodeError as e:
                exceptions.append({"phase": "place", "line": ln,
                                   "reason": f"decision JSON 解析失败: {e}", "action": "skipped"})
    stats = {"decisions_total": len(decisions), "decisions_applied": 0,
             "decisions_failed": 0, "marks_inserted": 0, "marks_merged_multi": 0,
             "existing_marks_removed": 0, "distinct_entries_cited": 0,
             "exceptions": 0, "style": args.style, "form": global_form}

    # ---------- 预审计：原有标记的段末堆放疑似（剥除前观察） ----------
    observed_existing = []
    for p in ms.get("paragraphs", []):
        if p.get("kind") != "body":
            continue
        text = p["text"]
        n_sent = len([c for c in text if c in "。！？!?"])
        for m in p.get("cite_marks", []):
            if m.get("style") != "numeric":
                continue
            dist_to_end = len(text) - m["span"][1]
            if dist_to_end <= 30 and n_sent >= 2:
                observed_existing.append({
                    "pid": p["pid"], "raw": m["raw"],
                    "dist_to_para_end": dist_to_end, "n_sentences": n_sent,
                    "suspect": "mark_at_paragraph_end_multi_sentence",
                    "note": "标记位于段末30字符内且段落含多句，疑似段末集中堆放（原稿观察，已按 decisions 重放）"})

    # ---------- 逐条 decision 定位 ----------
    # inserts[pid] = [{pos, entry_ids, claim_ids, form, position, sent_span}]
    inserts = {}
    for d in decisions:
        cid = d.get("claim_id") or f"line{d['_line']}"
        pid = d.get("pid")
        sentence = d.get("sentence") or ""
        entry_ids = [e for e in (d.get("entry_ids") or []) if e]
        form = d.get("form") or global_form
        position = d.get("position") or "after_sentence"
        if position not in ("after_sentence", "before_sentence"):
            position = "after_sentence"
        p = paras.get(pid)
        if p is None:
            exceptions.append({"phase": "place", "claim_id": cid, "pid": pid,
                               "reason": "pid 不存在于 manuscript.json", "action": "skipped"})
            continue
        if p.get("kind") in ("reference_list", "heading"):
            exceptions.append({"phase": "place", "claim_id": cid, "pid": pid,
                               "reason": f"目标段落 kind={p.get('kind')}，不允许插入引用标记",
                               "action": "skipped"})
            continue
        missing = [e for e in entry_ids if e not in recs_by_id]
        for e in missing:
            exceptions.append({"phase": "place", "claim_id": cid, "pid": pid,
                               "reason": f"entry_id {e} 不在 library.json 中", "action": "entry_dropped"})
        entry_ids = [e for e in entry_ids if e in recs_by_id]
        if not entry_ids:
            exceptions.append({"phase": "place", "claim_id": cid, "pid": pid,
                               "reason": "无有效 entry_ids", "action": "skipped"})
            continue
        span = find_sentence_span(p["text"], sentence)
        if span is None:
            exceptions.append({"phase": "locate", "claim_id": cid, "pid": pid,
                               "sentence": sentence[:120],
                               "reason": "sentence 在段落内定位失败（精确/空白宽容/去空白三级均未命中）",
                               "action": "skipped_no_fabrication"})
            continue
        pos = insertion_point(p["text"], span, position)
        inserts.setdefault(pid, []).append({
            "pos": pos, "entry_ids": entry_ids, "claim_ids": [cid],
            "form": form, "position": position, "sent_span": list(span),
            "rationale": d.get("rationale", ""), "claim_type": d.get("claim_type", ""),
        })
        for e in entry_ids:
            evidence.append({"claim_id": cid, "entry_id": e, "location": f"{pid}@{span[0]}-{span[1]}",
                             "source": "citation_decisions.jsonl(Agent判断)",
                             "support": "cited_for_claim", "claim_type": d.get("claim_type", ""),
                             "rationale": d.get("rationale", "")})

    # ---------- 同句合并（同 pid 同插入点） ----------
    for pid, lst in inserts.items():
        merged = {}
        order = []
        for it in sorted(lst, key=lambda x: x["pos"]):
            key = (it["pos"], it["form"])
            if key in merged:
                tgt = merged[key]
                for e in it["entry_ids"]:
                    if e not in tgt["entry_ids"]:
                        tgt["entry_ids"].append(e)
                tgt["claim_ids"].extend(it["claim_ids"])
                stats["marks_merged_multi"] += 1
            else:
                merged[key] = it
                order.append(key)
        inserts[pid] = [merged[k] for k in order]

    # ---------- 剥除旧标记（默认） ----------
    if not args.keep_existing:
        for p in ms.get("paragraphs", []):
            if p.get("kind") != "body":
                continue
            old = p["text"]
            new = re.sub(r"\s*\[\d+(?:\s*[-–—,，]\s*\d+)*\]", "", old)
            new = re.sub(r"\s{2,}", " ", new)
            if new != old:
                removed = NUM_MARK_RE.findall(old)
                stats["existing_marks_removed"] += len(removed)
                change_log.append({"op": "remove_existing_mark", "location": p["pid"],
                                   "before": ",".join(f"[{r}]" for r in removed),
                                   "after": "",
                                   "reason": "旧数字标记与文献库映射不可考，按 decisions 权威集重放引用"})
                p["text"] = new
                # 旧标记剥除后插入点偏移可能失效 -> 重新定位
                for it in inserts.get(p["pid"], []):
                    sentence_guess = None
                    # 用原 span 对应的句子（从原段落截取）重新定位
                    s0, e0 = it["sent_span"]
                    sentence_guess = old[s0:e0]
                    span = find_sentence_span(new, sentence_guess)
                    if span is None:
                        exceptions.append({"phase": "replace", "claim_id": it["claim_ids"][0],
                                           "pid": p["pid"],
                                           "reason": "剥除旧标记后句子重定位失败", "action": "skipped"})
                        it["pos"] = None
                    else:
                        it["sent_span"] = list(span)
                        it["pos"] = insertion_point(new, span, it["position"])
        for pid in list(inserts):
            inserts[pid] = [it for it in inserts[pid] if it["pos"] is not None]

    # ---------- 全局重排：按首次出现顺序 1..N ----------
    entry_num = {}
    order = []
    for pid in ordered_pids:
        for it in sorted(inserts.get(pid, []), key=lambda x: x["pos"]):
            for e in it["entry_ids"]:
                if e not in entry_num:
                    entry_num[e] = len(entry_num) + 1
                    order.append(e)
    stats["distinct_entries_cited"] = len(order)

    # ---------- 著者-出版年标签（同名同年加 a/b/c 消歧，全文一致） ----------
    ay_groups = {}
    for e in order:
        ay_groups.setdefault(author_key(recs_by_id[e]), []).append(e)
    ay_label = {}   # entry_id -> 标签主体（不含括号，分隔符在 make_mark 处按段落语言选）
    for (name, year), ids in ay_groups.items():
        for k, e in enumerate(sorted(ids, key=lambda x: entry_num[x])):
            suffix = chr(ord("a") + k) if len(ids) > 1 else ""
            ay_label[e] = (name, year + suffix)
    if len(ay_groups) < len(order):
        change_log.append({"op": "disambiguate_author_year", "location": "global",
                           "before": "", "after": "",
                           "reason": "同名同年条目按引用顺序加 a/b/c 后缀消歧"})

    def labels_for(entry_ids, cjk):
        sep = "，" if cjk else ", "
        out = []
        for e in entry_ids:
            name, yr = ay_label[e]
            out.append(f"{name}{sep}{yr}" if name else yr)
        return out

    # ---------- 执行插入（同段内自后向前，保证偏移有效） ----------
    multi_cite_checks, multi_sentence_checks = [], []
    for pid in ordered_pids:
        lst = inserts.get(pid, [])
        if not lst:
            continue
        p = paras[pid]
        cjk = bool(CJK_RE.search(p["text"]))
        text = p["text"]
        for it in sorted(lst, key=lambda x: -x["pos"]):
            if it["form"] == "author_year":
                mark = make_mark("author_year", None, None, cjk,
                                 labels=labels_for(it["entry_ids"], cjk))
                for e in it["entry_ids"]:
                    if not recs_by_id[e].get("year"):
                        uncertainty.append({"claim_id": it["claim_ids"][0], "entry_id": e,
                                            "issue": "条目缺出版年，著者-出版年标记以 n.d. 占位"})
            else:
                mark = make_mark("numeric", [entry_num[e] for e in it["entry_ids"]], None, cjk)
            it["mark"] = mark
            text = text[:it["pos"]] + mark + text[it["pos"]:]
            stats["marks_inserted"] += 1
            change_log.append({"op": "insert_citation", "location": f"{pid}@{it['pos']}",
                               "before": "", "after": mark,
                               "reason": f"论断句末插入（{it['claim_type'] or 'claim'}; "
                                         f"{'|'.join(it['claim_ids'])}）"})
            if len(it["entry_ids"]) > 1:
                multi_cite_checks.append({
                    "pid": pid, "claim_ids": it["claim_ids"], "mark": mark,
                    "merged_single_mark": True,
                    "no_adjacent_brackets": "][" not in text[max(0, it["pos"] - 2):it["pos"] + len(mark) + 2]})
        p["text"] = text

    # 多句一引：同一 entry 被多个不同论断句引用 -> 每句各自带同号标记
    from collections import defaultdict
    entry_sites = defaultdict(list)
    for pid in ordered_pids:
        for it in inserts.get(pid, []):
            for e in it["entry_ids"]:
                entry_sites[e].append((pid, tuple(it["sent_span"])))
    for e, sites in entry_sites.items():
        uniq = sorted(set(sites))
        if len(uniq) > 1:
            multi_sentence_checks.append({
                "entry_id": e, "assigned_number": entry_num.get(e),
                "n_citation_sites": len(uniq),
                "expanded": True,
                "note": "同一文献支撑多个论断句，各句末均带同一编号标记"})

    # ---------- 插入后错放自检 ----------
    misplacement_after = []
    for pid in ordered_pids:
        p = paras[pid]
        if p.get("kind") != "body":
            continue
        text = p["text"]
        for it in inserts.get(pid, []):
            s0, e0 = it["sent_span"]
            mark_end = it["pos"] + len(it.get("mark", ""))
            dist = len(text) - mark_end
            sent_end_dist = len(text) - e0
            if dist <= 30 and sent_end_dist > 34:
                misplacement_after.append({
                    "pid": pid, "claim_ids": it["claim_ids"],
                    "mark_dist_to_para_end": dist, "sentence_end_dist_to_para_end": sent_end_dist,
                    "suspect": "mark_near_para_end_but_claim_mid_paragraph"})

    # ---------- 重算 cite_marks ----------
    for p in ms.get("paragraphs", []):
        marks = []
        for m in NUM_MARK_RE.finditer(p["text"]):
            marks.append({"raw": m.group(0), "style": "numeric",
                          "nums": expand_nums(m.group(1)), "span": [m.start(), m.end()]})
        p["cite_marks"] = marks

    # ---------- 编号连续性自检 ----------
    all_nums = [n for p in ms["paragraphs"] for m in p["cite_marks"] for n in m["nums"]]
    maxn = max(all_nums) if all_nums else 0
    gaps = [n for n in range(1, maxn + 1) if n not in set(all_nums)]
    stats["max_inline_number"] = maxn
    stats["numbering_sequential"] = not gaps
    stats["numbering_gaps"] = gaps

    # ---------- 参考文献表（调用 cite_engine render，按引用顺序） ----------
    order_path = os.path.join(args.work, "citation_order.json")
    save_json(order_path, order)
    engine = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cite_engine.py")
    ref_out = os.path.join(args.out, "references.md")
    r = subprocess.run([sys.executable, engine, "render", "--records", args.library,
                        "--style", args.style, "--order", order_path, "--out", ref_out],
                       capture_output=True, text=True)
    if r.returncode != 0:
        exceptions.append({"phase": "render", "reason": f"cite_engine render 失败: {r.stderr[:300]}",
                           "action": "references_may_be_missing"})
    else:
        sys.stdout.write(r.stdout)

    # ---------- edited_manuscript.md（保留段落结构与标题；默认移除旧文献表） ----------
    out_paras, dropped_refs = [], 0
    for p in ms.get("paragraphs", []):
        if not args.keep_old_refs and p.get("kind") == "reference_list":
            dropped_refs += 1
            continue
        if (not args.keep_old_refs and dropped_refs == 0 and p.get("kind") == "heading"
                and re.fullmatch(r"#+\s*(参考文献|References|Bibliography|Works Cited)\s*",
                                 p["text"], re.I)):
            # 仅当后面确有 reference_list 段才应删标题；此处保守：若整文含 reference_list 段则删
            if any(q.get("kind") == "reference_list" for q in ms.get("paragraphs", [])):
                change_log.append({"op": "drop_old_reference_heading", "location": p["pid"],
                                   "before": p["text"], "after": "",
                                   "reason": "旧参考文献表已由 references.md（按引用顺序）取代"})
                continue
        out_paras.append(p["text"])
    if dropped_refs:
        change_log.append({"op": "drop_old_reference_list", "location": "manuscript_tail",
                           "before": f"{dropped_refs} 条旧文献条目", "after": "references.md",
                           "reason": "旧参考文献表与文献库映射不可考，由引擎按引用顺序重建"})
    edited = "\n\n".join(t for t in out_paras if t.strip()) + "\n"
    with open(os.path.join(args.out, "edited_manuscript.md"), "w", encoding="utf-8") as f:
        f.write(edited)

    # ---------- 落盘审计与中间产物 ----------
    stats["decisions_applied"] = stats["decisions_total"] and sum(
        1 for d in decisions if not any(e.get("claim_id") == (d.get("claim_id") or f"line{d['_line']}")
                                        and e.get("action", "").startswith("skipped")
                                        for e in exceptions))
    stats["decisions_failed"] = stats["decisions_total"] - stats["decisions_applied"]
    stats["exceptions"] = len(exceptions)

    audit = {
        "pre_existing_end_of_paragraph_dumping_observed": observed_existing,
        "n_observed_existing_suspects": len(observed_existing),
        "post_insertion_misplacement_suspects": misplacement_after,
        "n_post_insertion_suspects": len(misplacement_after),
        "multi_cite_merges": multi_cite_checks,
        "multi_sentence_expansions": multi_sentence_checks,
        "numbering": {"sequential": not gaps, "gaps": gaps, "max": maxn,
                      "order": order},
        "rule": "标记应紧贴论断句末（终结标点之前）；段末30字符内出现标记而论断句在段中部 = 疑似错放",
    }
    save_json(os.path.join(args.work, "placement_audit.json"), audit)
    save_json(os.path.join(args.out, "placement_audit.json"), audit)
    save_json(os.path.join(args.work, "exceptions.json"), exceptions)
    save_json(os.path.join(args.work, "change_log.json"), change_log)
    save_json(os.path.join(args.work, "evidence_map.json"), evidence)
    if uncertainty:
        save_json(os.path.join(args.work, "uncertainty.json"), uncertainty)
    save_json(os.path.join(args.work, "stats.json"), stats)
    save_json(os.path.join(args.work, "manuscript.placed.json"), ms)

    print(f"[place_citations] decisions={stats['decisions_total']} 插入标记={stats['marks_inserted']} "
          f"文献={len(order)} 编号连续={'是' if not gaps else '否' + str(gaps)} "
          f"异常={len(exceptions)} 段末堆放疑似(原稿)={len(observed_existing)} "
          f"插入后错放={len(misplacement_after)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
