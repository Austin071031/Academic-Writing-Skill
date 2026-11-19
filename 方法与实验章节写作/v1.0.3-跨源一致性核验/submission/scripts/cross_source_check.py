#!/usr/bin/env python3
"""cross_source_check.py — 跨源一致性引擎（v1.0.3 方向核心引擎）。

用 work/value_index.json（extract_evidence.py 产物）检测"同一参数名、跨来源、多值"的候选冲突；
Agent 依据 references/consistency_rules.md 的三级优先级（日志 > 配置 > 代码默认 > 论文正文）
在 work/conflict_resolutions.json 中逐项裁决或升级人工确认；本脚本校验裁决覆盖率。
用法: python3 cross_source_check.py [--phase detect|verify] --work /app/work --out /app/output
输出: conflicts.jsonl（detect 阶段）/ consistency_report.json（verify 阶段）
"""
import argparse, json, os, sys

def eid_source(eid, cands):
    return cands.get(eid, {}).get("source", "?")

def norm_value(v):
    """数值语义归一化：3e-4 与 0.0003 同值；非数值原样返回。"""
    try:
        return repr(float(v))
    except (TypeError, ValueError):
        return v

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["detect", "verify"], default="verify")
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    args = ap.parse_args()

    vip = os.path.join(args.work, "value_index.json")
    ecp = os.path.join(args.work, "evidence_candidates.jsonl")
    if not os.path.exists(vip):
        print("[consistency] 缺 value_index.json，请先运行 extract_evidence.py", file=sys.stderr)
        sys.exit(1)
    vindex = json.load(open(vip, encoding="utf-8"))
    cands = {}
    if os.path.exists(ecp):
        for line in open(ecp, encoding="utf-8"):
            try:
                r = json.loads(line)
                cands[r["eid"]] = r
            except Exception:
                pass

    conflicts = []
    for name, values in sorted(vindex.items()):
        if len(values) < 2:
            continue
        # 按数值归并取值
        groups = {}
        for v, eids in values.items():
            groups.setdefault(norm_value(v), []).append((v, eids))
        if len(groups) < 2:
            continue
        occ = []
        srcs = set()
        for _nv, pairs in groups.items():
            for v, eids in pairs:
                for e in eids:
                    s = eid_source(e, cands)
                    srcs.add(s)
                    occ.append({"value": v, "eid": e, "source": s})
        if len(srcs) >= 2:  # 至少两个不同来源才构成跨源冲突
            conflicts.append({"name": name, "occurrences": occ})

    if args.phase == "detect":
        outp = os.path.join(args.work, "conflicts.jsonl")
        with open(outp, "w", encoding="utf-8") as f:
            for c in conflicts:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        print(f"[consistency] 候选冲突 {len(conflicts)} 个 -> {outp}（请逐项裁决）")
        return 0

    res_path = os.path.join(args.work, "conflict_resolutions.json")
    resolutions = {}
    if os.path.exists(res_path):
        for r in json.load(open(res_path, encoding="utf-8")):
            resolutions[r.get("name")] = r
    unresolved = []
    escalated = []
    resolved = 0
    for c in conflicts:
        r = resolutions.get(c["name"])
        if not r:
            unresolved.append(c["name"])
        elif r.get("escalated"):
            escalated.append(c["name"])
        else:
            resolved += 1
    verdict = "pass" if not unresolved else "fail"
    report = {"conflicts_total": len(conflicts), "resolved": resolved,
              "escalated": escalated, "unresolved": unresolved, "verdict": verdict}
    rp = os.path.join(args.out, "consistency_report.json")
    with open(rp, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[consistency] 冲突 {len(conflicts)} 已裁决 {resolved} 升级 {len(escalated)} 未裁决 {len(unresolved)} verdict={verdict}")
    sys.exit(0 if verdict == "pass" else 1)

if __name__ == "__main__":
    sys.exit(main())
