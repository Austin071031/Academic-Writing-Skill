#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""parse_materials.py --work W [--input-dir /input]

解析输入材料 → work/materials.json + work/materials_digest.md。
role_guess（启发式猜测，字段中注明）：
  成果|简历|专利|项目批准|代表作 → prior_work
  指南|要求|workorder|template  → guide
  DOI/摘要/Abstract/引言        → paper
  表格数据                       → data
  否则                           → other
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "parse_materials"
DIGEST_PARA_MAX = 200
DIGEST_TOTAL_MAX = 30000

ROLE_RULES = [
    ("prior_work", re.compile(r"成果|简历|专利|项目批准|代表作")),
    ("guide", re.compile(r"指南|要求|workorder|template", re.I)),
    ("paper", re.compile(r"10\.\d{4,9}/|摘要|Abstract|引言", re.I)),
]


def role_guess(name, text, paragraphs):
    probe = (name or "") + "\n" + (text or "")[:3000]
    for role, pat in ROLE_RULES:
        if pat.search(probe):
            return role
    table_rows = sum(1 for p in paragraphs if p["kind"] == "table_row")
    if table_rows >= 3 or re.search(r"数据表|表格数据|实验数据", probe):
        return "data"
    return "other"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--input-dir", default=None)
    args = ap.parse_args()
    work, input_dir = args.work, gu.env_input_dir(args.input_dir)
    gu.ensure_dir(work)

    files = []
    digest_lines = ["# 材料摘要（materials_digest）",
                    "",
                    "> 自动抽取，role_guess 为启发式猜测；pid 供证据标记引用。", ""]
    digest_chars = 0
    for i, (full, rel) in enumerate(gu.iter_input_files(input_dir), start=1):
        fid = f"F{i}"
        entry = {"file_id": fid, "path": rel, "role_guess": "other",
                 "role_note": "启发式猜测，Agent 应自行复核",
                 "paragraphs": []}
        text = gu.extract_text(full)
        if text is None:
            gu.record_exception(work, STAGE, rel,
                                "extract_text 返回 None（格式不支持或解析失败）",
                                "该文件段落为空，保留文件条目")
            files.append(entry)
            digest_lines += [f"## {fid} {rel}", "",
                             "> 文本抽取失败，详见 work/exceptions.json。", ""]
            continue
        paras = gu.split_paragraphs(text)
        for j, p in enumerate(paras, start=1):
            entry["paragraphs"].append({
                "pid": f"{fid}-P{j:03d}", "kind": p["kind"],
                "sec": p["sec"], "text": p["text"]})
        entry["role_guess"] = role_guess(rel, text, paras)
        files.append(entry)

        # digest：每段截 200 字，总量 ≤30k 字
        digest_lines += [f"## {fid} {rel}（role_guess={entry['role_guess']}）", ""]
        for p in entry["paragraphs"]:
            line = f"- [{p['pid']}] ({p['kind']}/{p['sec'] or '-'}) " + \
                   p["text"].replace("\n", " ")[:DIGEST_PARA_MAX]
            if digest_chars + len(line) > DIGEST_TOTAL_MAX:
                digest_lines.append("- ……（摘要已达 30000 字上限，其余略）")
                digest_chars = DIGEST_TOTAL_MAX + 1
                break
            digest_lines.append(line)
            digest_chars += len(line)
        digest_lines.append("")
        if digest_chars > DIGEST_TOTAL_MAX:
            digest_lines.append("（摘要整体截断，完整内容见 work/materials.json）")
            break

    gu.write_json(os.path.join(work, "materials.json"),
                  {"files": files,
                   "stats": {"files": len(files),
                             "paragraphs": sum(len(f["paragraphs"]) for f in files)}})
    with open(os.path.join(work, "materials_digest.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(digest_lines))
    print(f"[parse_materials] files={len(files)} "
          f"paragraphs={sum(len(f['paragraphs']) for f in files)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[parse_materials] ERROR: {e}")
        raise SystemExit(1)
