#!/usr/bin/env python3
"""audit_provenance.py — 双向溯源审计（v1.0.0 方向核心引擎）。

正向：章节正文每个数值必须能在采信证据台账的某条 quote/value 中找到（白名单：章节号、
锚点号、≤12 的列举计数、19xx/20xx 年份、页码标记）。
反向：台账每条证据须被章节引用，或在 work/unused_evidence.json 中登记未使用理由。
用法: python3 audit_provenance.py --work /app/work --out /app/output
输出: audit_report.json {forward_leaks, backward_unused, verdict}
exit 0 = 无泄漏；1 = 存在泄漏或未说明的未使用证据。
"""
import argparse, json, os, re, sys

NUM = re.compile(r"\d+(?:\.\d+)?")
ANCHOR = re.compile(r"〔[EA]\d{3,4}〕")
ALLOW = re.compile(r"^(?:[1-9]|1[0-2]|19\d\d|20\d\d)$")

def norm(n):
    return n.rstrip("0").rstrip(".") if "." in n else n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    prov = []
    pp = os.path.join(args.out, "provenance_map.json")
    if os.path.exists(pp):
        with open(pp, encoding="utf-8") as f:
            prov = json.load(f)
    corpus = " \n ".join([(r.get("quote") or "") + " " + str(r.get("value") or "") for r in prov])
    corpus_norm = {norm(m.group(0)) for m in NUM.finditer(corpus)}

    chap = os.path.join(args.out, "methods_chapter.md")
    leaks = []
    if os.path.exists(chap):
        with open(chap, encoding="utf-8") as f:
            txt = f.read()
        body = txt.split("## 附录A")[0]  # 只审正文，附录本身是台账
        body = "\n".join(l for l in body.splitlines() if not l.startswith("> 生成方式"))
        body = ANCHOR.sub(" ", body)
        for m in NUM.finditer(body):
            n = m.group(0)
            if ALLOW.match(n):
                continue
            if norm(n) not in corpus_norm:
                ctx = body[max(0, m.start()-25):m.end()+25].replace("\n", " ")
                leaks.append({"number": n, "context": ctx})

    used = set()
    with open(chap, encoding="utf-8") as f:
        used = set(re.findall(r"〔([EA]\d{3,4})〕", f.read())) if os.path.exists(chap) else set()
    unused_decl = {}
    up = os.path.join(args.work, "unused_evidence.json")
    if os.path.exists(up):
        with open(up, encoding="utf-8") as f:
            unused_decl = {d.get("eid"): d.get("reason", "") for d in json.load(f)}
    backward = [{"eid": r.get("eid"), "quote": (r.get("quote") or "")[:80]}
                for r in prov if r.get("eid") not in used and r.get("eid") not in unused_decl]

    verdict = "pass" if not leaks and not backward else ("warn" if not leaks else "fail")
    report = {"forward_leaks": leaks, "backward_unused": backward,
              "forward_checked": True, "backward_checked": True, "verdict": verdict}
    rp = os.path.join(args.out, "audit_report.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[audit] 泄漏 {len(leaks)} 未说明未使用 {len(backward)} verdict={verdict} -> {rp}")
    sys.exit(0 if verdict == "pass" else 1)

if __name__ == "__main__":
    sys.exit(main())
