#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""elements_check.py --work W [--out O]

七要素覆盖检查：presence / 段落数 / 字数（厚度阈值，可在 inspection.json
的 thickness 中覆盖：立项依据≥400、技术路线≥300、研究基础≥300、其余≥150）。
element_map：{element → {dpids[], fids[], chars, status(ok/thin/missing)}}。
findings（缺失/过薄）→ work/element_findings.json；
element_map → work/element_map.json；若给 --out 另写 element_mapping.md。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "elements_check"
FID_RE = re.compile(r"〔(F\d+)〕")


def strip_markers(text):
    return re.sub(r"〔[^〕]*〕", "", text or "")


def element_key(name, elements):
    """把实际 element 名映射到 required_elements 中的标准名（前缀匹配）。"""
    for e in elements:
        if name.startswith(e) or e.startswith(name):
            return e
    return name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    work = args.work
    out = gu.env_output_dir(args.out) if args.out else None
    if out:
        gu.ensure_dir(out)

    draft = gu.read_json(os.path.join(work, "draft.json"), None)
    inspection = gu.read_json(os.path.join(work, "inspection.json"), {}) or {}
    if not isinstance(draft, dict) or "paragraphs" not in draft:
        gu.record_exception(work, STAGE, "draft.json", "缺失或结构不符",
                            "写空 element_map/findings")
        gu.write_json(os.path.join(work, "element_map.json"), {})
        gu.write_json(os.path.join(work, "element_findings.json"), [])
        return 0

    required = inspection.get("required_elements") or list(gu.DEFAULT_ELEMENTS)
    thickness_override = inspection.get("thickness") or {}

    element_map = {}
    for e in required:
        element_map[e] = {"dpids": [], "fids": [], "chars": 0, "status": "missing"}

    for p in draft["paragraphs"]:
        key = element_key(p.get("element", ""), required)
        if key not in element_map:
            element_map[key] = {"dpids": [], "fids": [], "chars": 0,
                                "status": "missing"}
        text_clean = strip_markers(p.get("text", ""))
        element_map[key]["dpids"].append(p["dpid"])
        element_map[key]["fids"].extend(FID_RE.findall(p.get("text", "")))
        element_map[key]["chars"] += len(re.sub(r"\s", "", text_clean))

    findings = []
    for e, m in element_map.items():
        m["fids"] = sorted(set(m["fids"]))
        if not m["dpids"]:
            m["status"] = "missing"
            findings.append({
                "element": e, "severity": "high", "kind": "element_missing",
                "chars": 0, "dpids": [],
                "msg": f"要素「{e}」缺失：无对应段落"})
            continue
        threshold = gu.thickness_for(e, thickness_override)
        if m["chars"] < threshold:
            m["status"] = "thin"
            findings.append({
                "element": e, "severity": "medium", "kind": "element_thin",
                "chars": m["chars"], "dpids": m["dpids"],
                "msg": f"要素「{e}」过薄：{m['chars']} 字 < 阈值 {threshold} 字"})
        else:
            m["status"] = "ok"

    gu.write_json(os.path.join(work, "element_map.json"), element_map)
    gu.write_json(os.path.join(work, "element_findings.json"), findings)

    # 交付物 element_mapping.md（七要素 × 章节 × 段落数/字数 × 证据数 × 状态
    # + 三级对应清单）
    if out:
        lines = ["# 要素对照说明（element_mapping）", "",
                 "| 要素 | 段落数 | 字数 | 证据数(FID) | 状态 |", "",
                 "|---|---|---|---|---|"]
        ok = sum(1 for m in element_map.values() if m["status"] == "ok")
        for e, m in element_map.items():
            lines.append(f"| {e} | {len(m['dpids'])} | {m['chars']} | "
                         f"{len(m['fids'])} | {m['status']} |")
        lines += ["", f"覆盖：{ok}/{len(element_map)} 个要素达标。", "",
                  "## 三级对应清单（段落 → 要素 → 证据 FID）", ""]
        for p in draft["paragraphs"]:
            fids = sorted(set(FID_RE.findall(p.get("text", ""))))
            lines.append(f"- {p['dpid']} → {p.get('element','?')} → "
                         f"{' '.join('〔'+f+'〕' for f in fids) if fids else '（无 FID）'}")
        with open(os.path.join(out, "element_mapping.md"), "w",
                  encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    covered = sum(1 for m in element_map.values() if m["dpids"])
    print(f"[elements_check] covered={covered}/{len(element_map)} "
          f"findings={len(findings)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[elements_check] ERROR: {e}")
        raise SystemExit(1)
