#!/usr/bin/env python3
"""align_rewrite.py — 源文段落与改写稿段落双向对齐，生成 work/alignment.json。

用法: python3 align_rewrite.py --source work/source.json --rewrite <改写稿.md> [--work /app/work]
输出 alignment.json:
  rewrite_paragraphs: [{rpid(R001…), text, n_chars}]
  links: [{source_pid, rpid, sim, relation(aligned|partial)}]   # sim>=0.28 aligned; 0.12-0.28 partial
  dropped: [{source_pid, head}]     # 源文段落未被任何改写段落覆盖
  added:   [{rpid, head}]           # 改写段落无源文对应（过渡句/新增，需人工确认是否含源外事实）
相似度: 字符 2-gram 包含度 |∩|/min（改写重述比例高时比 Jaccard 稳健），数字遮蔽看语义骨架。
"""
import argparse, json, os, re, sys

def ngrams(text, n=2):
    t = re.sub(r"\s+", "", text)
    t = re.sub(r"[-+−]?\d+(?:\.\d+)?%?", "#", t)  # 数字遮蔽，对齐看语义骨架
    return {t[i:i + n] for i in range(len(t) - n + 1)} if len(t) >= n else {t}

def containment(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))

def split_paragraphs(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    out = []
    for b in re.split(r"\n\s*\n", text):
        b = re.sub(r"^#{1,6}\s*", "", b.strip())
        if b:
            out.append(b)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--rewrite", required=True)
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    try:
        with open(args.source, encoding="utf-8") as f:
            src = json.load(f)
    except Exception as e:
        print(f"[align] source.json 读取失败: {e}", file=sys.stderr)
        return 1
    if not os.path.exists(args.rewrite):
        print(f"[align] 改写稿不存在: {args.rewrite}", file=sys.stderr)
        return 1
    with open(args.rewrite, encoding="utf-8") as f:
        rtext = f.read()

    sparas = src.get("paragraphs", [])
    rparas = [{"rpid": f"R{i:03d}", "text": t, "n_chars": len(t)}
              for i, t in enumerate(split_paragraphs(rtext), 1)]

    s_grams = [(p["pid"], ngrams(p["text"])) for p in sparas]
    r_grams = [(r["rpid"], ngrams(r["text"])) for r in rparas]

    links = []
    covered_src = set()
    covered_rw = set()
    for rpid, rg in r_grams:
        best, best_sim = None, 0.0
        for spid, sg in s_grams:
            sim = containment(sg, rg)
            if sim > best_sim:
                best, best_sim = spid, sim
        if best and best_sim >= 0.12:
            rel = "aligned" if best_sim >= 0.28 else "partial"
            links.append({"source_pid": best, "rpid": rpid,
                          "sim": round(best_sim, 3), "relation": rel})
            covered_src.add(best)
            covered_rw.add(rpid)

    dropped = [{"source_pid": p["pid"], "head": p["text"][:60]}
               for p in sparas if p["pid"] not in covered_src]
    added = [{"rpid": r["rpid"], "head": r["text"][:60]}
             for r in rparas if r["rpid"] not in covered_rw]

    out = {"rewrite_paragraphs": rparas, "links": links,
           "dropped": dropped, "added": added,
           "stats": {"n_source": len(sparas), "n_rewrite": len(rparas),
                     "n_aligned": sum(1 for l in links if l["relation"] == "aligned"),
                     "n_partial": sum(1 for l in links if l["relation"] == "partial"),
                     "n_dropped": len(dropped), "n_added": len(added)}}
    op = os.path.join(args.work, "alignment.json")
    with open(op, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    s = out["stats"]
    print(f"[align] 源文={s['n_source']} 改写={s['n_rewrite']} 对齐={s['n_aligned']} "
          f"部分={s['n_partial']} 源文未覆盖={s['n_dropped']} 改写新增={s['n_added']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
