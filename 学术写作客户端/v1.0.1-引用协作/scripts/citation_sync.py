#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""citation_sync — 正文引用与参考文献表的依赖图、审计与同步重编号。

能力：
  audit   提取正文引用序列；定位参考文献表；检查
          - 首次出现是否按序编号（Vancouver 顺序编码制）
          - 引用缺失（引用了不存在的编号）
          - 未引用条目（参考文献表中从未被正文引用）
          - DOI 形态校验（10.NNNN/...）
  sync    以正文首次出现顺序为权威，重排参考文献表并重写正文引用编号；
          产出对照表 old->new、同步后 DOCX 与审计报告。
  plan    仅输出重编号方案（不写文件），供人工确认后再 sync。

用法：
  python3 citation_sync.py audit   <docx> [report.json]
  python3 citation_sync.py plan    <docx> [plan.json]
  python3 citation_sync.py sync    <docx> <out_docx> [report.json]
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import docxkit as dk  # noqa: E402

DOI_RE = re.compile(r"10\.\d{4,9}/\S+", re.I)
REF_HEAD_RE = re.compile(r"^(参考文献|References)\s*$", re.I)
REF_ITEM_RE = re.compile(r"^\[(\d+)\]\s*(.+)$", re.S)


def build_graph(docx):
    """构建引用依赖图。

    返回 {citations: [(para, raw, [nums])], first_order: [num...],
          ref_section_para: idx|None, ref_items: [{para, num, text}],
          issues: [...]}
    """
    dk._build_parent_map(docx.tree().getroot())
    paras = list(docx.paragraphs())
    texts = [docx.para_text(p) for p in paras]
    # 参考文献表定位：标题匹配，或文末连续 [n] 开头的段落
    ref_head = None
    for i, t in enumerate(texts):
        if REF_HEAD_RE.match(t.strip()):
            ref_head = i
            break
    ref_items = []
    if ref_head is not None:
        for i in range(ref_head + 1, len(paras)):
            m = REF_ITEM_RE.match(texts[i].strip())
            if m:
                ref_items.append({"para": i, "num": int(m.group(1)),
                                  "text": m.group(2)})
            elif texts[i].strip() and not ref_items:
                continue
            elif texts[i].strip():
                break
    if not ref_items:
        # 无显式 [n] 标记：按参考文献标题后的非空段落顺序编号
        if ref_head is not None:
            k = 0
            for i in range(ref_head + 1, len(paras)):
                if texts[i].strip():
                    k += 1
                    ref_items.append({"para": i, "num": k,
                                      "text": texts[i].strip()})
    # 正文引用（参考文献表之后的不计）
    cite_paras = ref_head if ref_head is not None else len(paras)
    citations = []
    for i in range(cite_paras):
        for m in dk.CITE_RE.finditer(texts[i]):
            nums = []
            for part in re.split(r"[,，、]", m.group(1)):
                part = part.strip()
                if "-" in part:
                    a, b = part.split("-", 1)
                    if a.strip().isdigit() and b.strip().isdigit():
                        nums.extend(range(int(a), int(b) + 1))
                elif part.isdigit():
                    nums.append(int(part))
            citations.append({"para": i, "raw": m.group(0), "nums": nums})
    first_order = []
    for c in citations:
        for n in c["nums"]:
            if n not in first_order:
                first_order.append(n)
    # 问题检查
    issues = []
    ref_nums = {it["num"] for it in ref_items}
    cited_nums = set(first_order)
    for n in sorted(cited_nums - ref_nums):
        issues.append({"kind": "missing-reference", "num": n,
                       "note": "正文引用了参考文献表中不存在的编号"})
    for n in sorted(ref_nums - cited_nums):
        issues.append({"kind": "uncited-reference", "num": n,
                       "note": "参考文献表条目未被正文引用"})
    seen = set()
    expected = 1
    for c in citations:
        for n in c["nums"]:
            if n in seen:
                continue
            seen.add(n)
            if n != expected and ref_items:
                issues.append({"kind": "order-mismatch", "num": n,
                               "expected_first_position": expected,
                               "note": "顺序编码制下首次出现编号与位次不一致"})
            expected += 1
    for it in ref_items:
        dois = DOI_RE.findall(it["text"])
        it["doi"] = dois[0].rstrip(".") if dois else None
        if not dois:
            issues.append({"kind": "doi-missing", "num": it["num"],
                           "note": "条目缺少 DOI（如原文确实无 DOI 则忽略）"})
    return {"citations": citations, "first_order": first_order,
            "ref_head_para": ref_head, "ref_items": ref_items,
            "issues": issues}


def make_plan(graph):
    first_order = graph["first_order"]
    order_map = {}
    for new_pos, old_num in enumerate(first_order, start=1):
        order_map[old_num] = new_pos
    return {"order_map": order_map,
            "first_order": first_order,
            "issues": graph["issues"],
            "ref_reorder": [
                {"old_num": it["num"],
                 "new_num": order_map.get(it["num"]),
                 "text_head": it["text"][:60]}
                for it in graph["ref_items"]]}


def sync(docx_path, out_path, report_path=None):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    docx = dk.Docx(docx_path)
    graph = build_graph(docx)
    plan = make_plan(graph)
    order_map = plan["order_map"]
    record = {}
    changed = 0
    if order_map and any(k != v for k, v in order_map.items()):
        changed = dk.renumber_citations(docx, order_map, record=record)
    # 重排参考文献表段落
    ref_items = graph["ref_items"]
    if ref_items and any(order_map.get(it["num"], it["num"]) != it["num"]
                         for it in ref_items):
        dk._build_parent_map(docx.tree().getroot())
        paras = list(docx.paragraphs())
        body = docx.body()
        # 取引用块出现的最小段落位置
        anchor_para = min(it["para"] for it in ref_items)
        ref_ps = [paras[it["para"]] for it in ref_items]
        # 按新号排序后重插
        items = sorted(ref_items, key=lambda it: order_map.get(
            it["num"], it["num"]))
        # 更新每条文本的编号前缀
        new_first_idx = None
        for k, it in enumerate(items):
            p = paras[it["para"]]
            m = REF_ITEM_RE.match(docx.para_text(p).strip())
            if m:
                dk.replace_span(p, "[%s]" % m.group(1),
                                "[%d]" % (k + 1))
        ordered_ps = [paras[it["para"]] for it in items]
        # 先全部摘下再按新序插回
        for p in ordered_ps:
            body.remove(p)
        insert_at = anchor_para
        for k, p in enumerate(ordered_ps):
            body.insert(insert_at + k, p)
    docx.save(out_path)
    report = {"plan": plan,
              "citation_spans_rewritten": changed,
              "span_records": record.get("items", []),
              "issues": graph["issues"],
              "output": out_path}
    if report_path:
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
    print(json.dumps({"ok": True, "output": out_path,
                      "spans_rewritten": changed,
                      "issues": len(graph["issues"])},
                     ensure_ascii=False))
    return 0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    docx = dk.Docx(sys.argv[2])
    if cmd == "audit":
        graph = build_graph(docx)
        report = make_plan(graph)
        out = sys.argv[3] if len(sys.argv) > 3 else None
        s = json.dumps({"issues": graph["issues"],
                        "first_order": graph["first_order"],
                        "ref_count": len(graph["ref_items"]),
                        "citation_count": len(graph["citations"]),
                        "plan": report},
                       ensure_ascii=False, indent=1)
        if out:
            open(out, "w", encoding="utf-8").write(s)
        print(s)
        return 0
    if cmd == "plan":
        graph = build_graph(docx)
        s = json.dumps(make_plan(graph), ensure_ascii=False, indent=1)
        out = sys.argv[3] if len(sys.argv) > 3 else None
        if out:
            open(out, "w", encoding="utf-8").write(s)
        print(s)
        return 0
    if cmd == "sync":
        if len(sys.argv) < 4:
            print("usage: citation_sync.py sync <in.docx> <out.docx> [report]")
            return 2
        return sync(sys.argv[2], sys.argv[3],
                    sys.argv[4] if len(sys.argv) > 4 else None)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
