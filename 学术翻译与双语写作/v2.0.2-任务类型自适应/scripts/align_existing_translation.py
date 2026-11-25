#!/usr/bin/env python3
"""align_existing_translation.py — 已有译文对齐（v2.0.2 任务自适应·校对模式）。

材料中已含现成译文时，把译文句子映射回源文句段（segments.json 坐标），
直接生成 work/translations.jsonl —— 使后续的机检（数字/引用/术语/边界）、
双语对照组装、修订标记交付完全复用翻译模式管线，Agent 转入“审校+修订”角色。

映射方法：按源文句段顺序与译文句子顺序做长度比例对齐
（英文词数→中文字符约 1:1.9；中文→英文约 1:0.6），逐段消耗译文句子；
比例异常的映射标 needs_review，交 Agent 复核。

用法:
  python3 align_existing_translation.py --work /app/work \
      --translation-file /input/xxx_zh.md
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trans_utils as tu
from parse_manuscript import split_sentences, read_text

def load_translation_text(path):
    if path.endswith(".docx"):
        from parse_manuscript import docx_to_blocks
        return "\n".join(b[2] for b in docx_to_blocks(path) if b[0] == "para")
    if path.endswith(".pdf"):
        import subprocess
        r = subprocess.run(["pdftotext", "-layout", path, "-"],
                           capture_output=True, timeout=120)
        if r.returncode != 0:
            raise RuntimeError("pdftotext 失败: " + r.stderr.decode("utf-8", "ignore")[:200])
        return r.stdout.decode("utf-8", "ignore")
    text, _enc = read_text(path)
    return text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--translation-file", required=True)
    args = ap.parse_args()

    segdata = tu.load_json(os.path.join(args.work, "segments.json"))
    if not segdata:
        print("[align_existing][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    insp = tu.load_json(os.path.join(args.work, "inspection.json"), {}) or {}
    tt = insp.get("translation_task") or {}
    source_lang = tt.get("source_lang") or "en"

    try:
        text = load_translation_text(args.translation_file)
    except Exception as e:
        print(f"[align_existing][FATAL] 译文读取失败: {e}", file=sys.stderr)
        return 1
    if not text:
        print("[align_existing][FATAL] 译文为空", file=sys.stderr)
        return 1

    t_sents = [s for s in split_sentences(text) if len(s.strip()) > 1]
    segs = [s for s in segdata["segments"] if s["needs_translation"]]

    # 长度比例：源语言→目标语言的期望字符比
    def src_len(s):
        return len(s.split()) if source_lang == "en" else len(re.sub(r"\s", "", s))
    RATIO = 1.9 if source_lang == "en" else 0.6  # 目标字符/源单位

    records, reviews = [], []
    ti = 0
    buf = ""
    for s in segs:
        expect = max(src_len(s["source"]) * RATIO, 8)
        buf = ""
        used = 0
        while ti < len(t_sents) and (not buf or len(buf) < expect * 0.75):
            buf = (buf + t_sents[ti]) if buf else t_sents[ti]
            ti += 1
            used += 1
            if len(buf) >= expect * 1.6:
                break
        if not buf:
            break
        ratio = len(buf) / expect if expect else 1
        rec = {"seg_id": s["seg_id"], "translation": buf.strip()}
        records.append(rec)
        if ratio < 0.45 or ratio > 2.2 or used > 2:
            reviews.append({"seg_id": s["seg_id"], "ratio": round(ratio, 2),
                            "t_sents_used": used,
                            "note": "映射比例异常，需 Agent 对照原文人工确认"})

    fp = os.path.join(args.work, "translations.jsonl")
    with open(fp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    coverage = len(records) / max(len(segs), 1)
    tu.save_json(os.path.join(args.work, "existing_translation_alignment.json"), {
        "translation_file": args.translation_file,
        "translation_sentences": len(t_sents),
        "segments_need_translation": len(segs),
        "mapped": len(records), "coverage": round(coverage, 4),
        "needs_review": reviews})
    print(f"[align_existing] 译文句={len(t_sents)} 映射={len(records)}/{len(segs)} "
          f"覆盖={coverage:.0%} 待复核={len(reviews)}")
    if coverage < 0.9:
        print("[align_existing][warn] 覆盖率不足 90%，译文可能不完整或映射错位，"
              "请人工复核 existing_translation_alignment.json", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
