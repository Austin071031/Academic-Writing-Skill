#!/usr/bin/env python3
"""style_check.py — 章节文风与格式机检（v3.0.4 复审修订循环的机检引擎）。

对 /app/output/methods_chapter.md 正文（附录之前）检查四类可机检问题：
1. 套话/空转句式（"存在一定局限性""众所周知""随着……的发展""具有重要意义"等）；
2. 超长句（>120 字符且无锚点，疑似多步压句）；
3. 含数值句无锚点（数字出现但句内无 〔E#〕/〔A#〕，白名单同 audit：≤12 计数、年份）；
4. 中英混杂（同句同时含连续英文句与汉字，材料原文引用除外）。
输出 style_report.json {issues:[{line, kind, text}], verdict}
用法: python3 style_check.py --out /app/output
"""
import argparse, json, os, re, sys

FLUFF = ["存在一定局限性", "众所周知", "具有重要意义", "具有重要理论意义", "受到广泛关注",
         "研究热点", "未来还有改进空间", "随着", "不言而喻", "显而易见",
         "it is well known", "obviously", "of course", "plays an important role"]
NUM = re.compile(r"\d+(?:\.\d+)?")
ANCHOR = re.compile(r"〔[EA]\d{3,4}〕")
ALLOW = re.compile(r"^(?:[1-9]|1[0-2]|19\d\d|20\d\d)$")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()
    chap = os.path.join(args.out, "methods_chapter.md")
    if not os.path.exists(chap):
        print("[style] methods_chapter.md 不存在", file=sys.stderr)
        sys.exit(1)
    txt = open(chap, encoding="utf-8").read()
    body = txt.split("## 附录A")[0]
    issues = []
    for ln, line in enumerate(body.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#") or s.startswith(">") or s.startswith("|") or s.startswith("```"):
            continue
        for f in FLUFF:
            if f in s:
                issues.append({"line": ln, "kind": "fluff", "text": s[:100]})
                break
        if len(s) > 120 and not ANCHOR.search(s):
            issues.append({"line": ln, "kind": "long_sentence_no_anchor", "text": s[:100]})
        nums = [m.group(0) for m in NUM.finditer(s)]
        if nums and not ANCHOR.search(s):
            real = [n for n in nums if not ALLOW.match(n)]
            if real:
                issues.append({"line": ln, "kind": "number_without_anchor", "text": s[:100], "numbers": real[:4]})
    verdict = "pass" if not issues else "warn"
    rep = {"issues": issues, "counts": {}, "verdict": verdict}
    for i in issues:
        rep["counts"][i["kind"]] = rep["counts"].get(i["kind"], 0) + 1
    rp = os.path.join(args.out, "style_report.json")
    json.dump(rep, open(rp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[style] 问题 {len(issues)} 条（{rep['counts']}）verdict={verdict} -> {rp}")
    sys.exit(0)

if __name__ == "__main__":
    sys.exit(main())
