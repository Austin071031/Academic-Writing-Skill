#!/usr/bin/env python3
"""log_audit.py — 修改清单质量审计：先审"讲得清"，再审"没改坏"。

用法: python3 log_audit.py --work-dir /app/work

对 /app/work/polish_chunks/*.jsonl 做结构与理由质量检查：
  - 每行必须是合法 JSON，含 id/original/polished/decision/types/reason；
  - id 必须存在于源文本（extract_text.py 产出的 source_segments.json）；
  - types 必须取自受控词表；
  - modify 句的 reason 不得为空、不得是空泛套话，且须 ≥8 字并指向具体语言现象；
  - 同一句被多个 chunk 重复记录时以最后一条为准并报 warning。
输出: /app/work/log_audit.json / log_audit.md；exit 1 表示存在 critical。
"""
import argparse, glob, json, os, re, sys

VALID_TYPES = {"grammar", "syntax", "collocation", "punctuation", "spelling", "long-sentence",
               "terminology", "abbreviation", "register", "redundancy", "logic", "clarity",
               "hedging", "formatting", "other"}
GENERIC_REASONS = {"更通顺", "更规范", "更好", "更符合学术风格", "润色", "修改", "优化表达",
                   "提高可读性", "语言优化", "表达更准确", "使句子更流畅", "改成书面语"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work-dir", default="/app/work")
    args = ap.parse_args()
    wd = args.work_dir

    src_ids = set()
    sp = os.path.join(wd, "source_segments.json")
    if os.path.exists(sp):
        for seg in json.load(open(sp, encoding="utf-8")):
            sents = seg.get("sentences") or []
            for i in range(1, len(sents) + 1):
                src_ids.add(f"{seg['id']}-S{i}" if len(sents) > 1 else seg["id"])

    problems, warnings, seen = [], [], {}
    n = 0
    for p in sorted(glob.glob(os.path.join(wd, "polish_chunks", "*.jsonl"))):
        with open(p, encoding="utf-8") as f:
            for ln, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                n += 1
                tag = f"{os.path.basename(p)}:{ln}"
                try:
                    e = json.loads(line)
                except json.JSONDecodeError as ex:
                    problems.append(f"{tag} 非法 JSON: {ex}")
                    continue
                sid = e.get("id")
                if not sid:
                    problems.append(f"{tag} 缺 id")
                    continue
                if src_ids and sid not in src_ids:
                    warnings.append(f"{tag} id '{sid}' 不在源文本中（对齐可能错位）")
                if sid in seen:
                    warnings.append(f"{tag} id '{sid}' 与 {seen[sid]} 重复记录，以本条为准")
                seen[sid] = tag
                for fld in ("original", "polished", "decision", "reason"):
                    if fld not in e:
                        problems.append(f"{tag} 缺字段 {fld}")
                bad = [t for t in (e.get("types") or []) if t not in VALID_TYPES]
                if bad:
                    warnings.append(f"{tag} types 含受控词表之外的值: {bad}")
                if e.get("decision") == "modify":
                    reason = (e.get("reason") or "").strip()
                    if len(reason) < 8:
                        problems.append(f"{tag} reason 过短（{reason!r}），第三方无法判断该不该改")
                    if reason in GENERIC_REASONS:
                        problems.append(f"{tag} reason 为空泛套话（{reason!r}），须指向具体语言现象")
                    if not e.get("types"):
                        problems.append(f"{tag} modify 但 types 为空")

    rep = {"entries": n, "unique_ids": len(seen), "problems": problems,
           "warnings": warnings, "passed": not problems}
    with open(os.path.join(wd, "log_audit.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    with open(os.path.join(wd, "log_audit.md"), "w", encoding="utf-8") as f:
        f.write("# 修改清单质量审计（log_audit.py）\n\n")
        f.write(f"记录 {n} 条，去重后 {len(seen)} 句；critical {len(problems)}，warning {len(warnings)}。\n\n")
        for x in problems:
            f.write(f"- **[critical]** {x}\n")
        for x in warnings:
            f.write(f"- [warning] {x}\n")
        if not problems and not warnings:
            f.write("- 结构与理由质量全部通过。\n")
    print(f"[log_audit] entries={n} unique={len(seen)} critical={len(problems)} warning={len(warnings)}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
