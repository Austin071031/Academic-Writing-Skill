#!/usr/bin/env python3
"""verify_numbers.py — 结果与讨论正文数值 ↔ 数值台账一致性核验器。

用法:
  python3 verify_numbers.py --ledger evidence_ledger.json --text section.md --out report.json

规则:
  1. 从正文抽取全部数值token（含 87.3%、(87.3 ± 4.1)、8.7×10^-3、1.2e-5 等形式）。
  2. 与台账中的 value/error.value/stat.p 等数值逐一比对，按小数位四舍五入容差匹配。
  3. 每个数值给出 matched / unmatched / ambiguous（数值匹配但出现多处）。
  4. 退出码: 0 = 无 unmatched; 1 = 存在 unmatched（正文必须修正后重跑）。
仅依赖 Python 3 标准库。
"""
import argparse
import json
import math
import re
import sys

NUM_RE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?:\s*[×x*]\s*10\^?\(?(-?\d+)\)?|e(-?\d+))?"
    r"(?![A-Za-z0-9])"
)


def parse_number(tok: str, sci_exp):
    v = float(tok.replace(",", ""))
    if sci_exp is not None:
        v *= 10.0 ** int(sci_exp)
    return v


def decimals(tok: str) -> int:
    if "." in tok:
        return len(tok.split(".")[1].rstrip("0")) or 1
    return 0


def norm(v: float) -> float:
    return 0.0 if (math.isnan(v) or math.isinf(v)) else v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    with open(args.ledger, encoding="utf-8") as f:
        ledger_raw = json.load(f)
    entries = ledger_raw.get("entries", ledger_raw if isinstance(ledger_raw, list) else [])
    if not isinstance(entries, list):
        print("ledger 格式错误: 需要 list 或 {'entries': [...]}", file=sys.stderr)
        return 2

    ledger_vals = []  # (value, tolerance, source_id, description)
    for e in entries:
        try:
            if "value" in e and e["value"] is not None:
                v = norm(float(e["value"]))
                tol = max(0.5 * 10 ** (-6), abs(v) * 1e-9)
                ledger_vals.append((v, tol, e.get("id", "?"), e.get("source", "?")))
            err = e.get("error") or {}
            if err.get("value") is not None:
                v = norm(float(err["value"]))
                ledger_vals.append((v, max(1e-9, abs(v) * 1e-9), e.get("id", "?"), "error"))
            stat = e.get("stat") or {}
            for k in ("p", "t", "f", "z", "chi2", "r2", "effect_size"):
                if stat.get(k) is not None:
                    v = norm(float(stat[k]))
                    ledger_vals.append((v, max(1e-12, abs(v) * 1e-9), e.get("id", "?"), f"stat.{k}"))
            if stat.get("ci") and isinstance(stat["ci"], (list, tuple)) and len(stat["ci"]) == 2:
                for v in stat["ci"]:
                    ledger_vals.append((norm(float(v)), 1e-9, e.get("id", "?"), "stat.ci"))
            if e.get("n") is not None:
                try:
                    ledger_vals.append((norm(float(e["n"])), 1e-9, e.get("id", "?"), "n"))
                except (TypeError, ValueError):
                    pass
        except (TypeError, ValueError):
            continue

    with open(args.text, encoding="utf-8") as f:
        text = f.read()

    report = {"text": args.text, "ledger": args.ledger, "numbers": [], "summary": {}}
    n_match = n_unmatch = n_amb = 0
    seen = {}
    for m in NUM_RE.finditer(text):
        tok, sci1, sci2 = m.group(1), m.group(2), m.group(3)
        sci = sci1 if sci1 is not None else sci2
        # 排除年份(1900-2099 且前后文为文献语境的粗略排除: 单独出现的 4 位整数年份)
        if sci is None and re.fullmatch(r"(19|20)\d{2}", tok) and not re.search(r"[±×.^]\s*$", text[max(0, m.start()-3):m.start()]):
            prev = text[max(0, m.start()-12):m.start()]
            if re.search(r"[（(]\s*$|et al\.?,?\s*$|,\s*$", prev) or re.fullmatch(r"(19|20)\d{2}", tok):
                # 年份不核验，跳过
                continue
        try:
            v = parse_number(tok, sci)
        except ValueError:
            continue
        dec = decimals(tok)
        tol = max(0.5 * 10 ** (-dec), abs(v) * 1e-12)
        hits = [(sid, desc) for (lv, lt, sid, desc) in ledger_vals if abs(lv - v) <= max(tol, lt)]
        line = text.count("\n", 0, m.start()) + 1
        if len(hits) == 1:
            status = "matched"
        elif len(hits) > 1:
            status = "ambiguous"
        else:
            status = "unmatched"
        key = (round(v, 9))
        seen.setdefault(key, []).append(status)
        report["numbers"].append({"token": m.group(0), "value": v, "line": line, "status": status,
                                  "matched_to": hits[:3] if hits else []})
        if status == "matched":
            n_match += 1
        elif status == "ambiguous":
            n_amb += 1
        else:
            n_unmatch += 1

    report["summary"] = {"total": len(report["numbers"]), "matched": n_match,
                         "ambiguous": n_amb, "unmatched": n_unmatch,
                         "verdict": "PASS" if n_unmatch == 0 else "FAIL"}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if n_unmatch == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
