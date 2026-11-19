#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""draft_builder.py --work W --out O

组装 work/sections/*.md（按文件名排序；首行 `# 要素名` 定 element）：
  - O/proposal_draft.md      清洁版（去除所有〔…〕标记）
  - O/proposal_annotated.md  留痕版（段首 D-Pxxx + 〔F…〕〔拟〕〔确认〕原位）
  - work/draft.json          {paragraphs:[{dpid,element,text,markers[]}]}
校验〔F\d+〕在 fact_ledger.json 存在；不存在 → work/findings_draft.json
（severity=high，"证据标记指向不存在的台账条目"）。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "draft_builder"
MARK_RE = re.compile(r"〔(F\d+|拟|确认)〕")
FID_RE = re.compile(r"〔(F\d+)〕")
H1_RE = re.compile(r"^\s*#\s+(?P<name>\S.*)$")


def clean_text(text):
    """去掉所有〔…〕标记并收拢空白。"""
    t = MARK_RE.sub("", text)
    t = re.sub(r"〔[^〕]*〕", "", t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    work, out = args.work, gu.env_output_dir(args.out)
    gu.ensure_dir(work)
    gu.ensure_dir(out)

    ledger = gu.read_json(os.path.join(work, "fact_ledger.json"), {"entries": []})
    known_fids = {e["fid"] for e in ledger.get("entries", [])
                  if isinstance(e, dict) and e.get("fid")}

    sections_dir = os.path.join(work, "sections")
    section_files = []
    try:
        section_files = sorted(
            f for f in os.listdir(sections_dir) if f.endswith(".md"))
    except Exception as e:
        gu.record_exception(work, STAGE, "work/sections/", e,
                            "按空草稿处理，仅写骨架文件")

    paragraphs = []
    findings = []
    clean_parts, ann_parts = [], []
    counter = 0

    for fname in section_files:
        path = os.path.join(sections_dir, fname)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            gu.record_exception(work, STAGE, fname, e, "跳过该章节文件")
            continue
        element = os.path.splitext(fname)[0]
        first = text.splitlines()[0] if text.splitlines() else ""
        m = H1_RE.match(first)
        if m:
            element = m.group("name").strip()
        blocks = gu.split_paragraphs(text)
        file_clean = [f"# {element}", ""]
        file_ann = [f"# {element}", ""]
        for b in blocks:
            if b["kind"] == "heading":
                # 章节内小标题原样保留，不分配 D-P 编号
                file_clean.append(clean_text(b["text"]))
                file_clean.append("")
                file_ann.append(b["text"])
                file_ann.append("")
                continue
            counter += 1
            dpid = f"D-P{counter:03d}"
            markers = MARK_RE.findall(b["text"])
            paragraphs.append({"dpid": dpid, "element": element,
                               "text": b["text"], "markers": markers})
            for fmark in FID_RE.findall(b["text"]):
                if fmark not in known_fids:
                    findings.append({
                        "dpid": dpid, "severity": "high",
                        "kind": "marker_missing_ledger",
                        "value": fmark,
                        "msg": f"证据标记指向不存在的台账条目〔{fmark}〕"})
            file_clean.append(clean_text(b["text"]))
            file_clean.append("")
            file_ann.append(f"{dpid} {b['text']}")
            file_ann.append("")
        clean_parts.append("\n".join(file_clean).strip() + "\n")
        ann_parts.append("\n".join(file_ann).strip() + "\n")

    gu.write_json(os.path.join(work, "draft.json"), {
        "paragraphs": paragraphs,
        "elements": sorted({p["element"] for p in paragraphs}),
        "markers_summary": {
            "fid_refs": sum(len(FID_RE.findall(p["text"])) for p in paragraphs),
            "planned": sum(1 for p in paragraphs if "拟" in p["markers"]),
            "confirm": sum(1 for p in paragraphs if "确认" in p["markers"]),
        }})
    gu.write_json(os.path.join(work, "findings_draft.json"), findings)

    draft_md = "\n".join(clean_parts) if clean_parts else "# （空草稿）\n"
    ann_md = "\n".join(ann_parts) if ann_parts else "# （空草稿，留痕版）\n"
    with open(os.path.join(out, "proposal_draft.md"), "w", encoding="utf-8") as f:
        f.write(draft_md)
    with open(os.path.join(out, "proposal_annotated.md"), "w", encoding="utf-8") as f:
        f.write(ann_md)

    if not section_files:
        gu.record_exception(work, STAGE, "work/sections/",
                            "未发现任何章节 md 文件",
                            "已写空骨架 draft/proposal，Agent 需补写 sections")
    print(f"[draft_builder] paragraphs={counter} findings={len(findings)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[draft_builder] ERROR: {e}")
        raise SystemExit(1)
