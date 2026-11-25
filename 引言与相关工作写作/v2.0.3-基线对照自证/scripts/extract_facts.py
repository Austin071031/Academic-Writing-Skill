#!/usr/bin/env python3
"""extract_facts.py — 从稿件/笔记/文献库中确定性抽取"可引用事实候选"，输出 work/fact_candidates.jsonl。

用法: python3 extract_facts.py --work /app/work [--max-per-source 12]
输入: work/manuscript.json（parse_manuscript.py 产物，可选）、work/notes.json（parse_notes.py 产物，可选）、
      work/library.json（parse_library.py 产物，可选）。
输出每行: {fid, source_kind, loc, quote, numbers[], years[], suggested_use}
  source_kind ∈ manuscript|note|library
  suggested_use ∈ background_problem|background_fact|related_finding|own_result|method_context|metadata
注意：候选仅为建议，是否采信由 Agent 判断；evidence_map.json 中的 source.loc 必须能指回这些锚点。
"""
import argparse, json, os, re, sys

NUM_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|％|倍|个|项|篇|次|h|天|年|MPa|GPa|mAh/g|Wh/kg|°C|nm|μm|mm|K)")
YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
FINDING_RE = re.compile(r"(发现|表明|显示|证实|达到|提升|提高|降低|减少|优于|超过|首次|提出|实现|解决|证明|验证|报道|获得|不足|局限|挑战|缺乏|难以|瓶颈)")
PROBLEM_RE = re.compile(r"(问题|挑战|不足|局限|缺乏|难以|瓶颈|空白|缺口|尚未|有待|原因不明|争议)")

def split_sentences(text):
    parts = re.split(r"(?<=[。！？；;.!?])\s*", text)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) >= 8]

def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--max-per-source", type=int, default=12)
    args = ap.parse_args()

    cands = []
    fid = 0

    ms = load(os.path.join(args.work, "manuscript.json"))
    if ms and ms.get("paragraphs"):
        for p in ms["paragraphs"]:
            if p.get("kind") in ("reference_list",):
                continue
            text = p.get("text", "")
            for s in split_sentences(text):
                if len(s) > 220:
                    continue
                has_num = bool(NUM_RE.search(s))
                is_find = bool(FINDING_RE.search(s))
                if not (has_num or is_find):
                    continue
                fid += 1
                use = "background_problem" if PROBLEM_RE.search(s) and p.get("kind") == "body" else \
                      "own_result" if has_num else "background_fact"
                if p.get("kind") in ("figure_note", "table_note"):
                    use = "own_result"
                cands.append({"fid": f"F{fid:04d}", "source_kind": "manuscript",
                              "loc": p["pid"], "quote": s[:200],
                              "numbers": NUM_RE.findall(s)[:6],
                              "years": YEAR_RE.findall(s)[:3],
                              "suggested_use": use})
                break  # 每段最多取一句，控制体积

    nt = load(os.path.join(args.work, "notes.json"))
    if nt and nt.get("sources"):
        per = {}
        for src in nt["sources"]:
            for p in src.get("paragraphs", []):
                if not p.get("fact_candidate"):
                    continue
                key = src["file"]
                if per.get(key, 0) >= args.max_per_source:
                    continue
                per[key] = per.get(key, 0) + 1
                fid += 1
                cands.append({"fid": f"F{fid:04d}", "source_kind": "note",
                              "loc": p.get("nid", "?"), "quote": (p.get("text") or "")[:200],
                              "numbers": p.get("numbers", [])[:6],
                              "years": p.get("years", [])[:3],
                              "suggested_use": "related_finding"})

    lib = load(os.path.join(args.work, "library.json"))
    if lib and lib.get("records"):
        for r in lib["records"]:
            fid += 1
            title = r.get("title") or ""
            venue = r.get("venue") or ""
            cands.append({"fid": f"F{fid:04d}", "source_kind": "library",
                          "loc": r.get("id", "?"),
                          "quote": f"{title}（{venue}, {r.get('year','?')}）"[:200],
                          "numbers": [], "years": [str(r.get("year"))] if r.get("year") else [],
                          "suggested_use": "metadata"})

    out = os.path.join(args.work, "fact_candidates.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for c in cands:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"[extract_facts] {len(cands)} 条候选 (manuscript={sum(1 for c in cands if c['source_kind']=='manuscript')} "
          f"note={sum(1 for c in cands if c['source_kind']=='note')} library={sum(1 for c in cands if c['source_kind']=='library')})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
