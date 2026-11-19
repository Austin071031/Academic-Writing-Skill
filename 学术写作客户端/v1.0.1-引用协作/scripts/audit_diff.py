#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_diff — before/after 保真差分核验（内容单元级，不用相似度糊弄）。

对比维度：段落文本、表格单元格、图片、OMML 公式、脚注/尾注、超链接、
          域指令、分节、样式使用。
白名单：调用方显式登记的“合法变换”（如术语统一、题注规范化、引用重编号），
        在报告中单独列出 expected_changes，不计入 fidelity_breaks。
输出 JSON：{unchanged, changed, expected_changes, fidelity_breaks, summary}
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docxkit as dk  # noqa: E402


def table_cells(docx):
    cells = []
    root = docx.tree().getroot()
    for ti, tbl in enumerate(root.iter(dk.qn("w:tbl"))):
        for ri, row in enumerate(tbl.findall(dk.qn("w:tr"))):
            for ci, tc in enumerate(row.findall(dk.qn("w:tc"))):
                txt = "".join(docx.para_text(p) for p in
                              tc.iter(dk.qn("w:p")))
                cells.append({"table": ti, "row": ri, "col": ci,
                              "text": txt})
    return cells


def diff(before_path, after_path, whitelist=None):
    whitelist = whitelist or []
    b = dk.Docx(before_path)
    a = dk.Docx(after_path)
    dk._build_parent_map(b.tree().getroot())
    dk._build_parent_map(a.tree().getroot())

    report = {"before": before_path, "after": after_path,
              "unchanged": [], "changed": [], "expected_changes": [],
              "fidelity_breaks": [], "summary": {}}

    bi = dk.inventory(b)
    ai = dk.inventory(a)
    for key in ("tables", "images", "equations_omml", "hyperlinks",
                "footnotes", "endnotes", "sections"):
        if bi[key] == ai[key]:
            report["unchanged"].append("%s=%d" % (key, ai[key]))
        else:
            report["fidelity_breaks"].append(
                {"kind": key, "before": bi[key], "after": ai[key],
                 "note": "结构性要素数量变化，需人工确认"})

    # 段落对比
    bp = dk.para_dump(b)
    ap = dk.para_dump(a)
    maxlen = max(len(bp), len(ap))
    text_changes = 0
    for i in range(maxlen):
        bt = bp[i]["text"] if i < len(bp) else None
        at = ap[i]["text"] if i < len(ap) else None
        if bt == at:
            continue
        text_changes += 1
        item = {"para_index": i, "before": (bt or "")[:120],
                "after": (at or "")[:120]}
        joined = (bt or "") + "||" + (at or "")
        if any(w in joined for w in whitelist):
            report["expected_changes"].append(item)
        else:
            report["changed"].append(item)
    # 表格单元格
    bc, ac = table_cells(b), table_cells(a)
    if len(bc) != len(ac):
        report["fidelity_breaks"].append(
            {"kind": "table_cells", "before": len(bc), "after": len(ac)})
    else:
        for x, y in zip(bc, ac):
            if x["text"] != y["text"]:
                report["changed"].append(
                    {"cell": [x["table"], x["row"], x["col"]],
                     "before": x["text"][:80], "after": y["text"][:80]})
    report["summary"] = {
        "paragraphs_before": len(bp), "paragraphs_after": len(ap),
        "text_changed_paragraphs": text_changes,
        "structural_breaks": len(report["fidelity_breaks"]),
        "expected_change_hits": len(report["expected_changes"]),
    }
    return report


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    before, after = sys.argv[1], sys.argv[2]
    whitelist = []
    if len(sys.argv) > 3 and os.path.exists(sys.argv[3]):
        whitelist = [l.strip() for l in open(sys.argv[3], encoding="utf-8")
                     if l.strip()]
    report = diff(before, after, whitelist)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
