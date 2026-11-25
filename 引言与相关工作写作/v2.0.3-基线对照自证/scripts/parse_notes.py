#!/usr/bin/env python3
"""parse_notes.py — 解析阅读笔记/事实材料（md/txt/json/csv），输出 work/notes.json。

用法: python3 parse_notes.py <笔记文件...> [--work /app/work]
每个文件切分为段落，抽取含数字/年份/结论性动词的"事实候选句"，锚定到 nid。
输出: notes.json {sources:[{file, paragraphs:[{nid, text, numbers[], years[], fact_candidate}]}]}
事实候选是确定性启发式（含数字、百分比、比较动词、"发现/表明/达到"等），仅作建议，
最终采信由 Agent 判断并写入 evidence_map.json。
"""
import argparse, json, os, re, sys

NUM_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|％|倍|个|项|篇|次|h|小时|天|年|MPa|GPa|mAh|mAh/g|Wh/kg|K|°C|nm|μm|mm|cm|m/s|s|ms)?")
YEAR_RE = re.compile(r"(?<!\d)(19|20)\d{2}(?!\d)")
FINDING_RE = re.compile(r"(发现|表明|显示|证实|达到|提升|提高|降低|减少|优于|超过|首次|提出|实现|解决|证明|验证|报道|获得)")

def read_any(path):
    for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
        try:
            with open(path, encoding=enc) as f:
                return f.read(), None
        except (UnicodeDecodeError, LookupError):
            continue
        except OSError as e:
            return None, str(e)
    return None, "无法解码"

def split_sentences(text):
    # 中英混合分句：保留句末标点
    parts = re.split(r"(?<=[。！？；;.!?])\s*", text)
    return [p.strip() for p in parts if p.strip()]

def parse_json_notes(text, file):
    """JSON 笔记：支持 [{title/url/source/... , summary|note|content}] 或 {notes:[...]}。"""
    out = []
    try:
        data = json.loads(text)
    except Exception:
        return out
    items = data.get("notes", data) if isinstance(data, dict) else data
    if not isinstance(items, list):
        return out
    for i, it in enumerate(items):
        if not isinstance(it, dict):
            continue
        title = str(it.get("title") or it.get("name") or it.get("entry_id") or f"note-{i+1}")
        body = str(it.get("summary") or it.get("note") or it.get("content") or it.get("abstract") or "")
        if not body:
            continue
        nums = NUM_RE.findall(body)
        years = YEAR_RE.findall(body)
        out.append({"nid": f"J{i+1:03d}", "title": title, "text": body[:800],
                    "numbers": nums[:10], "years": years[:5],
                    "fact_candidate": bool(nums or FINDING_RE.search(body))})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="笔记/材料文件路径")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    sources = []
    issues = []
    for path in args.files:
        if not os.path.exists(path):
            issues.append(f"笔记文件不存在: {path}")
            continue
        text, err = read_any(path)
        if err:
            issues.append(f"{path}: {err}")
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext == ".json":
            paras = parse_json_notes(text, path)
        else:
            paras = []
            blocks = re.split(r"\n\s*\n", text)
            k = 0
            for b in blocks:
                b = re.sub(r"\s*\n\s*", " ", b).strip()
                if not b:
                    continue
                k += 1
                sents = split_sentences(b)
                fact_sents = [s for s in sents if NUM_RE.search(s) or FINDING_RE.search(s)]
                nums = NUM_RE.findall(b)
                years = YEAR_RE.findall(b)
                paras.append({"nid": f"{os.path.basename(path)[:1].upper()}{k:03d}",
                              "text": b[:800], "numbers": nums[:10], "years": years[:5],
                              "fact_candidate": bool(fact_sents),
                              "fact_sentences": [s[:160] for s in fact_sents[:4]]})
        sources.append({"file": path, "n_paragraphs": len(paras), "paragraphs": paras})

    out = {"sources": sources,
           "n_paragraphs": sum(s["n_paragraphs"] for s in sources),
           "issues": issues}
    with open(os.path.join(args.work, "notes.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[parse_notes] {len(sources)} 个笔记文件, {out['n_paragraphs']} 段")
    for iss in issues:
        print(f"[parse_notes][issue] {iss}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
