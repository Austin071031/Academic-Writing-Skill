#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""source_audit.py --work W

材料外事实机检：draft.json 每段的数字/引用必须 ①在该段〔F…〕对应的
台账值集合中 ②或在全局台账值集合中 ③或该段带〔拟〕标记；否则
severity=high finding（"材料外数字/引用：值 X 未在材料台账中"）。
另全稿扫不可核验修饰词（首次|国际领先|填补空白|国际先进|国内首创|
世界领先）→ severity=low 提示。
输出 work/source_audit.json {findings:[{dpid,severity,kind,value,msg}]}。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "source_audit"
HYPE_RE = re.compile(r"首次|国际领先|填补空白|国际先进|国内首创|世界领先")
FID_RE = re.compile(r"〔(F\d+)〕")
# 条目标号（(1)/（2）/3. 等）不是事实数字，审计前剔除
ENUM_RE = re.compile(r"（\s*\d{1,2}\s*）|\(\s*\d{1,2}\s*\)|(?:(?<=^)|(?<=[\s；;：:]))\d{1,2}[.、]\s")


def build_ledger_index(ledger):
    """返回 (by_fid, global_numbers, global_citations)。"""
    by_fid = {}
    g_nums, g_cites = [], []
    for e in ledger.get("entries", []):
        if not isinstance(e, dict):
            continue
        by_fid[e.get("fid", "")] = e
        if e.get("type") == "number":
            g_nums.append(e)
        elif e.get("type") == "citation":
            g_cites.append(e)
    return by_fid, g_nums, g_cites


def in_ledger(entry, num=None, cite=None):
    """entry 是否匹配某数字/引用。数字 ±0 容差、单位等价；引用集合宽松相交。"""
    if num is not None:
        if entry.get("type") != "number":
            return False
        eu, nu = gu.norm_unit(entry.get("unit")), gu.norm_unit(num.get("unit"))
        if gu.norm_value(entry.get("value")) != gu.norm_value(num.get("value")):
            return False
        if eu == nu:
            return True
        # 单位一侧缺失时宽松匹配；% / 万 / 亿等有语义量级，不可省略
        strict = {"%", "万", "亿", "℃", "m²"}
        if not eu or not nu:
            return (eu or nu) not in strict
        if "年" in (eu, nu):
            return True
        return False
    if cite is not None:
        if entry.get("type") != "citation":
            return False
        return gu.citation_overlap(entry.get("value", ""), cite)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    work = args.work

    draft = gu.read_json(os.path.join(work, "draft.json"), None)
    ledger = gu.read_json(os.path.join(work, "fact_ledger.json"), {"entries": []})
    if not isinstance(draft, dict) or "paragraphs" not in draft:
        gu.record_exception(work, STAGE, "draft.json", "缺失或结构不符",
                            "写空 source_audit.json")
        gu.write_json(os.path.join(work, "source_audit.json"), {"findings": []})
        return 0

    by_fid, g_nums, g_cites = build_ledger_index(ledger)
    findings = []

    for p in draft["paragraphs"]:
        text = p.get("text", "")
        dpid = p.get("dpid", "?")
        markers = p.get("markers", [])
        planned = "拟" in markers
        para_entries = [by_fid[m] for m in FID_RE.findall(text)
                        if m in by_fid]
        # 全稿修饰词扫描（与数字检查独立）
        for m in HYPE_RE.finditer(text):
            findings.append({
                "dpid": dpid, "severity": "low", "kind": "hype_word",
                "value": m.group(0),
                "msg": f"不可核验修饰词「{m.group(0)}」：建议改为可核验的差异表述"})
        if planned:
            continue  # 拟开展段允许写目标值
        num_text = ENUM_RE.sub(" ", text)
        for n in gu.extract_numbers(num_text):
            hit_para = any(in_ledger(e, num=n) for e in para_entries)
            hit_global = any(in_ledger(e, num=n) for e in g_nums)
            if not hit_para and not hit_global:
                findings.append({
                    "dpid": dpid, "severity": "high", "kind": "off_source_number",
                    "value": n["raw"],
                    "msg": f"材料外数字/引用：值 {n['raw']} 未在材料台账中"})
        for c in gu.extract_citations(text):
            hit_para = any(in_ledger(e, cite=c) for e in para_entries)
            hit_global = any(in_ledger(e, cite=c) for e in g_cites)
            if not hit_para and not hit_global:
                findings.append({
                    "dpid": dpid, "severity": "high", "kind": "off_source_citation",
                    "value": c,
                    "msg": f"材料外数字/引用：引用 {c} 未在材料台账中"})

    gu.write_json(os.path.join(work, "source_audit.json"), {"findings": findings})
    high = sum(1 for x in findings if x["severity"] == "high")
    low = sum(1 for x in findings if x["severity"] == "low")
    print(f"[source_audit] findings={len(findings)} (high={high}, low={low})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[source_audit] ERROR: {e}")
        raise SystemExit(1)
