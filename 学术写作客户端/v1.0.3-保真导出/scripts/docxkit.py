#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""docxkit — 纯标准库 OOXML/DOCX 处理工具包。

不依赖任何第三方库（无 pip 安装需求）。提供：
  - DOCX 打开/保存（保留全部原有部件与关系）
  - 段落/表格/样式/编号/题注/域/脚注的结构化提取
  - 跨 run 的“目标替换”（保留书签、域、超链接、修订标记）
  - 修订追踪（w:ins / w:del / w:delText）的生成与解析
  - 引用 [n] / [n,m] / [n-m] 的提取与重编号
  - 内容清单（images/equations/footnotes/hyperlinks/fields/sections）审计

设计原则（对应学术写作客户端运行契约）：
  - 只改看得见的文本，绝不打散域结构（fldChar/instrText 保持原样）
  - 祖先链遇到 w:hyperlink 时仍可写普通文本，但绝不写域指令
  - 所有修改可回溯：替换/修订均返回结构化记录
"""
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from collections import OrderedDict

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
DC = "http://purl.org/dc/elements/1.1/"

for _p, _u in [("w", W), ("r", R), ("wp", WP), ("a", A), ("m", M)]:
    ET.register_namespace(_p, _u)


def qn(tag):
    """'w:p' -> '{...}p'"""
    p, local = tag.split(":", 1)
    ns = {"w": W, "r": R, "wp": WP, "a": A, "m": M}[p]
    return "{%s}%s" % (ns, local)


def wtag(el):
    return el.tag.split("}", 1)[-1] if "}" in el.tag else el.tag


# ---------- 部件级读写 ----------

class Docx:
    """一个 DOCX 包。parts 保留原始字节，未改动的部件原样写回。"""

    def __init__(self, path):
        self.path = path
        self.parts = OrderedDict()
        with zipfile.ZipFile(path, "r") as z:
            for name in z.namelist():
                self.parts[name] = z.read(name)
        self._trees = {}

    def _xml_names(self):
        return [n for n in self.parts if n.endswith(".xml") or n.endswith(".rels")]

    def tree(self, part="word/document.xml"):
        if part not in self._trees:
            self._trees[part] = ET.ElementTree(
                ET.fromstring(self.parts[part]))
        return self._trees[part]

    def has_part(self, part):
        return part in self.parts

    def save(self, out_path):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in self.parts.items():
                if name in self._trees:
                    z.writestr(name, ET.tostring(
                        self._trees[name].getroot(), encoding="UTF-8",
                        xml_declaration=True))
                else:
                    z.writestr(name, data)
        with open(out_path, "wb") as f:
            f.write(buf.getvalue())

    # ---- 结构提取 ----
    def body(self):
        return self.tree().getroot().find(qn("w:body"))

    def paragraphs(self):
        """全文所有 w:p（含表格内），按文档顺序。"""
        root = self.tree().getroot()
        return root.iter(qn("w:p"))

    def blocks(self):
        """顶层块级元素（段落与表格）。"""
        out = []
        for el in self.body():
            t = wtag(el)
            if t in ("p", "tbl"):
                out.append(el)
        return out

    def para_text(self, p):
        """段落可见文本（跳过 w:del 内的删除文本）。"""
        parts = []
        for t in p.iter():
            tg = wtag(t)
            if tg == "t" and not _in_deleted(t):
                parts.append(t.text or "")
            elif tg == "tab":
                parts.append("\t")
            elif tg in ("br", "cr"):
                parts.append("\n")
        return "".join(parts)

    def para_full_text(self, p):
        """含删除文本的段落全文（用于修订对照）。"""
        parts = []
        for t in p.iter():
            tg = wtag(t)
            if tg in ("t", "delText"):
                parts.append(t.text or "")
        return "".join(parts)

    def para_style(self, p):
        ps = p.find(qn("w:pPr") + "/" + qn("w:pStyle"))
        return ps.get(qn("w:val")) if ps is not None else None

    def outline(self):
        """(index, style, text) 列表，用于章节定位。"""
        out = []
        for i, p in enumerate(self.paragraphs()):
            out.append((i, self.para_style(p), self.para_text(p)))
        return out


def _in_deleted(el):
    cur = el
    while cur is not None:
        if wtag(cur) == "del":
            return True
        cur = _parent(cur)
    return False


_PARENT_MAP = {}


def _parent(el):
    return _PARENT_MAP.get(el)


def _build_parent_map(root):
    _PARENT_MAP.clear()
    for parent in root.iter():
        for child in parent:
            _PARENT_MAP[child] = parent


# ---------- 跨 run 目标替换 ----------

def locate_span(p, needle):
    """在段落中定位子串，返回 (t_elem_list, start, end) 或 None。

    t_elem_list: 有序的 (w:t 元素, 文本) 对；start/end 是拼接串中的偏移。
    跳过 w:instrText、w:delText 与 w:fldChar 内部，避免破坏域。
    """
    elems = []
    for t in p.iter():
        tg = wtag(t)
        if tg == "t" and not _in_deleted(t):
            elems.append((t, t.text or ""))
    if not elems:
        return None
    full = "".join(x[1] for x in elems)
    idx = full.find(needle)
    if idx < 0:
        return None
    return elems, idx, idx + len(needle)


def _map_offset(elems, off):
    """拼接串偏移 -> (元素序号, 元素内偏移)。"""
    acc = 0
    for i, (_, txt) in enumerate(elems):
        if off < acc + len(txt):
            return i, off - acc
        acc += len(txt)
    return len(elems) - 1, len(elems[-1][1])


def replace_span(p, old, new, record=None):
    """把段落中 old 的首次出现替换为 new，保留 run 级格式。

    返回 True/False。record 提供时写入结构化记录：
      {old, new, runs_touched}
    说明：替换优先落在首个被覆盖的 run 上，其余 run 清空被覆盖部分；
    若 old 跨越多个 run，中间的 run 仅保留格式壳（空文本），格式随原 run。
    """
    loc = locate_span(p, old)
    if loc is None:
        return False
    elems, s, e = loc
    si, so = _map_offset(elems, s)
    ei, eo = _map_offset(elems, e - 1)
    touched = []
    if si == ei:
        t = elems[si][0]
        txt = t.text or ""
        t.text = txt[:so] + new + txt[eo + 1:]
    else:
        first = elems[si][0]
        first.text = (first.text or "")[:so] + new
        for j in range(si + 1, ei):
            elems[j][0].text = ""
        last = elems[ei][0]
        last.text = (last.text or "")[eo + 1:]
    touched = [elems[j][0] for j in range(si, ei + 1)]
    if record is not None:
        record.update({"old": old, "new": new,
                       "runs_touched": len(touched)})
    return True


# ---------- 修订追踪 ----------

def make_ins(text, author="skill-agent", date=None, rpr=None):
    """生成 w:ins 包裹的 run 列表。"""
    ins = ET.Element(qn("w:ins"))
    ins.set(qn("w:author"), author)
    if date:
        ins.set(qn("w:date"), date)
    r = ET.SubElement(ins, qn("w:r"))
    if rpr is not None:
        r.append(_clone(rpr))
    t = ET.SubElement(r, qn("w:t"))
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return ins


def make_del(old_run, text, author="skill-agent", date=None):
    """生成 w:del 包裹的 run（w:delText）。"""
    d = ET.Element(qn("w:del"))
    d.set(qn("w:author"), author)
    if date:
        d.set(qn("w:date"), date)
    r = ET.SubElement(d, qn("w:r"))
    rpr = old_run.find(qn("w:rPr")) if wtag(old_run) == "r" else None
    if rpr is not None:
        r.append(_clone(rpr))
    t = ET.SubElement(r, qn("w:delText"))
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t.text = text
    return d


def tracked_replace(p, old, new, author="skill-agent", date=None,
                    record=None):
    """以修订形式替换：old 标删、new 标插。保留原 run 格式。

    返回 True/False。record 写入 {old, new, ins_text, del_text}。
    """
    loc = locate_span(p, old)
    if loc is None:
        return False
    elems, s, e = loc
    si, so = _map_offset(elems, s)
    ei, eo = _map_offset(elems, e - 1)
    parent_run = _parent(elems[si][0])
    while parent_run is not None and wtag(parent_run) != "r":
        parent_run = _parent(parent_run)
    rpr = parent_run.find(qn("w:rPr")) if parent_run is not None else None

    head_txt = ""
    tail_txt = ""
    if si == ei:
        txt = elems[si][0].text or ""
        head_txt = txt[:so]
        tail_txt = txt[eo + 1:]
    else:
        head_txt = (elems[si][0].text or "")[:so]
        tail_txt = (elems[ei][0].text or "")[eo + 1:]

    # 清理被覆盖文本
    if si == ei:
        elems[si][0].text = head_txt
    else:
        elems[si][0].text = head_txt
        for j in range(si + 1, ei):
            elems[j][0].text = ""
        elems[ei][0].text = tail_txt

    # 插入点：最后一个被触及 run 之后
    anchor = elems[ei][0]
    run_el = anchor
    while _parent(run_el) is not None and wtag(_parent(run_el)) != "p":
        run_el = _parent(run_el)
    ins_el = _parent(elems[ei][0])
    # 找到该 w:t 在祖先 run/智能标记中的直接父容器
    container = _parent(elems[ei][0])
    # 向上直到段落级容器
    while _parent(container) is not None and wtag(_parent(container)) not in ("p", "ins", "del", "hyperlink", "smartTag"):
        container = _parent(container)
    pos = list(container).index(elems[ei][0])
    parent_of_t = container
    # w:t 的父是 run
    run_of_t = parent_of_t
    if si == ei:
        # 同 run：head 保留在原 run，del+ins 插到该 run 之后
        pass
    del_el = make_del(run_of_t if wtag(run_of_t) == "r" else parent_run,
                      old, author, date)
    # 插入顺序：del 在前、ins 在后，紧邻原 run；new 为空则只标删
    target_run = run_of_t
    if wtag(target_run) != "r":
        target_run = parent_run
    par = _parent(target_run)
    idx = list(par).index(target_run)
    par.insert(idx + 1, del_el)
    if new:
        ins_el = make_ins(new, author, date, rpr=rpr)
        par.insert(idx + 2, ins_el)
    if record is not None:
        record.update({"old": old, "new": new,
                       "ins_text": new, "del_text": old})
    return True


def revisions(docx):
    """解析文档中全部修订，返回 [{author,date,kind,del,ins,para_index}]。"""
    _build_parent_map(docx.tree().getroot())
    out = []
    for i, p in enumerate(docx.paragraphs()):
        for el in p.iter():
            tg = wtag(el)
            if tg == "ins":
                txt = "".join(t.text or "" for t in el.iter(qn("w:t")))
                out.append({"para_index": i, "kind": "insert",
                            "author": el.get(qn("w:author")),
                            "date": el.get(qn("w:date")), "ins": txt})
            elif tg == "del":
                txt = "".join(t.text or ""
                              for t in el.iter(qn("w:delText")))
                out.append({"para_index": i, "kind": "delete",
                            "author": el.get(qn("w:author")),
                            "date": el.get(qn("w:date")), "del": txt})
    return out


def accept_all(docx):
    """接受全部修订：w:ins 提升为普通内容，w:del 移除。"""
    root = docx.tree().getroot()
    _build_parent_map(root)
    _unwrap_all(root, "ins")
    _unwrap_all(root, "del")
    # 删除孤立 delText
    for dt in list(root.iter(qn("w:delText"))):
        par = _parent(dt)
        run = _parent(par)
        if run is not None and wtag(run) == "r":
            rpar = _parent(run)
            rpar.remove(run)


def reject_all(docx):
    """拒绝全部修订：w:del 恢复为普通文本，w:ins 移除。"""
    root = docx.tree().getroot()
    _build_parent_map(root)
    for d in list(root.iter(qn("w:del"))):
        par = _parent(d)
        idx = list(par).index(d)
        for r in d.findall(qn("w:r")):
            nr = ET.Element(qn("w:r"))
            rpr = r.find(qn("w:rPr"))
            if rpr is not None:
                nr.append(_clone(rpr))
            for dt in r.findall(qn("w:delText")):
                t = ET.SubElement(nr, qn("w:t"))
                t.set("{http://www.w3.org/XML/1998/namespace}space",
                      "preserve")
                t.text = dt.text
            par.insert(idx, nr)
            idx += 1
        par.remove(d)
    _unwrap_all(root, "ins")
    for dt in list(root.iter(qn("w:delText"))):
        par = _parent(dt)
        run = _parent(par)
        if run is not None and wtag(run) == "r":
            _parent(run).remove(run)


def _unwrap_all(root, kind):
    for el in list(root.iter(qn("w:" + kind))):
        par = _parent(el)
        if par is None:
            continue
        idx = list(par).index(el)
        for child in list(el):
            par.insert(idx, child)
            idx += 1
        par.remove(el)


def _clone(el):
    return ET.fromstring(ET.tostring(el))


# ---------- 引用处理 ----------

CITE_RE = re.compile(r"\[(\d+(?:\s*[-,，、]\s*\d+)*)\]")


def extract_citations(docx):
    """提取正文编号引用（跳过参考文献表常见样式不作特殊处理，由调用方按位置过滤）。

    返回 [(para_index, raw, [nums])]。
    """
    out = []
    for i, p in enumerate(docx.paragraphs()):
        txt = docx.para_text(p)
        for m in CITE_RE.finditer(txt):
            nums = []
            for part in re.split(r"[,，、]", m.group(1)):
                part = part.strip()
                if "-" in part:
                    a, b = part.split("-", 1)
                    if a.strip().isdigit() and b.strip().isdigit():
                        nums.extend(range(int(a), int(b) + 1))
                elif part.isdigit():
                    nums.append(int(part))
            out.append((i, m.group(0), nums))
    return out


def renumber_citations(docx, order_map, record=None):
    """按 order_map {旧号: 新号} 重写正文引用文本（保留 run 格式）。

    返回成功替换的处数。record 收集 {old_raw, new_raw, para_index}。
    """
    count = 0
    for i, p in enumerate(docx.paragraphs()):
        txt = docx.para_text(p)
        for m in list(CITE_RE.finditer(txt)):
            def remap(mm):
                nums = []
                for part in re.split(r"[,，、]", mm.group(1)):
                    part = part.strip()
                    if "-" in part:
                        a, b = part.split("-", 1)
                        nums.extend(range(int(a), int(b) + 1))
                    elif part.isdigit():
                        nums.append(int(part))
                new_nums = [order_map.get(n, n) for n in nums]
                # 压缩连续区间
                new_nums = sorted(set(new_nums))
                segs = []
                j = 0
                while j < len(new_nums):
                    k = j
                    while k + 1 < len(new_nums) and \
                            new_nums[k + 1] == new_nums[k] + 1:
                        k += 1
                    if k > j + 1:
                        segs.append("%d-%d" % (new_nums[j], new_nums[k]))
                    else:
                        segs.extend(str(n) for n in new_nums[j:k + 1])
                    j = k + 1
                return "[" + ",".join(segs) + "]"
            new_raw = remap(m)
            if new_raw != m.group(0):
                rec = {}
                if replace_span(p, m.group(0), new_raw, record=rec):
                    count += 1
                    if record is not None:
                        record.setdefault("items", []).append({
                            "para_index": i,
                            "old_raw": m.group(0),
                            "new_raw": new_raw})
    return count


# ---------- 内容清单审计 ----------

def inventory(docx):
    """结构化内容清单，用于保真核验与版本对比。"""
    root = docx.tree().getroot()
    _build_parent_map(root)
    imgs = list(root.iter(qn("w:drawing"))) + \
        list(root.iter(qn("w:pict")))
    eqs = list(root.iter("{%s}oMath" % M)) + \
        list(root.iter("{%s}oMathPara" % M))
    links = list(root.iter(qn("w:hyperlink")))
    flds = [fc for fc in root.iter(qn("w:fldChar"))]
    instr = [it.text or "" for it in root.iter(qn("w:instrText"))]
    footnotes = endnotes = 0
    if docx.has_part("word/footnotes.xml"):
        ft = docx.tree("word/footnotes.xml").getroot()
        footnotes = len([f for f in ft.findall(qn("w:footnote"))
                         if f.get(qn("w:id")) not in ("-1", "0", None) or
                         f.get(qn("w:type")) is None])
    if docx.has_part("word/endnotes.xml"):
        en = docx.tree("word/endnotes.xml").getroot()
        endnotes = len([e for e in en.findall(qn("w:endnote"))
                        if e.get(qn("w:type")) is None])
    paras = list(docx.paragraphs())
    tables = list(root.iter(qn("w:tbl")))
    sects = list(root.iter(qn("w:sectPr")))
    return {
        "paragraphs": len(paras),
        "tables": len(tables),
        "images": len(imgs),
        "equations_omml": len(eqs),
        "hyperlinks": len(links),
        "field_chars": len(flds),
        "field_instructions": instr,
        "footnotes": footnotes,
        "endnotes": endnotes,
        "sections": len(sects),
        "parts": list(docx.parts.keys()),
    }


def para_dump(docx):
    """全文段落快照 [{index, style, text}]，用于版本间 diff。"""
    return [{"index": i, "style": docx.para_style(p),
             "text": docx.para_text(p)}
            for i, p in enumerate(docx.paragraphs())]


# ---------- CLI ----------

def _cmd_inspect(args):
    docx = Docx(args.docx)
    _build_parent_map(docx.tree().getroot())
    info = inventory(docx)
    info["path"] = args.docx
    info["paragraph_outline"] = [
        {"index": i, "style": s, "text": (t[:120] + ("…" if len(t) > 120
                                                   else ""))}
        for i, s, t in docx.outline() if t.strip()
    ]
    json.dump(info, sys.stdout, ensure_ascii=False, indent=1)


def _cmd_dump(args):
    docx = Docx(args.docx)
    _build_parent_map(docx.tree().getroot())
    json.dump(para_dump(docx), sys.stdout, ensure_ascii=False, indent=1)


def _cmd_revisions(args):
    docx = Docx(args.docx)
    _build_parent_map(docx.tree().getroot())
    json.dump(revisions(docx), sys.stdout, ensure_ascii=False, indent=1)


def _cmd_inventory(args):
    docx = Docx(args.docx)
    _build_parent_map(docx.tree().getroot())
    json.dump(inventory(docx), sys.stdout, ensure_ascii=False, indent=1)


def main():
    import sys
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    cmd, docx_path = sys.argv[1], sys.argv[2]
    class A: pass
    args = A()
    args.docx = docx_path
    {"inspect": _cmd_inspect, "dump": _cmd_dump,
     "revisions": _cmd_revisions,
     "inventory": _cmd_inventory}[cmd](args)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
