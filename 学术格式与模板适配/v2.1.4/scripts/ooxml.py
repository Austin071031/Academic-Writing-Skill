#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ooxml.py — Minimal, dependency-free OOXML/OPC helpers (Python stdlib only).

Design notes (hard-won OOXML constraints encoded here):
1) Child element order inside w:pPr / w:rPr / w:style / w:lvl / w:sectPr is
   schema-enforced.  Out-of-order children make LibreOffice refuse the file
   ("source cannot be loaded") without a useful message.  We therefore keep a
   canonical order table and always *insert in order* (and re-sort on demand).
2) OPC .rels parts and [Content_Types].xml must use DEFAULT namespaces, not
   prefixed ones, or the LibreOffice OPC reader fails outright.
3) Every part we add (styles/numbering/footnotes/...) must be registered both
   in [Content_Types].xml and in word/_rels/document.xml.rels.

Only Python standard library is used so the pipeline runs in a bare sandbox.
"""
import io
import os
import re
import zipfile
import xml.etree.ElementTree as ET

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
XML = "http://www.w3.org/XML/1998/namespace"

NS = {"w": W, "r": R, "rel": REL, "ct": CT, "xml": XML}

# NOTE: we deliberately do NOT register a default ("") namespace.  ElementTree
# keeps a single global prefix->URI map, so registering "" twice would break
# serialization of .rels / [Content_Types].xml (they MUST use a default
# namespace, see module docstring pitfall #2).  Those two flat OPC parts are
# therefore parsed/serialized with the string-level helpers below.
for _p, _u in (("w", W), ("r", R), ("xml", XML)):
    ET.register_namespace(_p, _u)


def qn(tag):
    """'w:p' -> '{...main}p' ; accepts already-qualified tag."""
    if tag.startswith("{"):
        return tag
    pfx, local = tag.split(":", 1)
    return "{%s}%s" % (NS[pfx], local)


def q(tag):
    return "{%s}%s" % (W, tag)


# Canonical child orders (subset of ECMA-376 that we touch).
ORDER = {
    "p": ["pPr"],
    "r": ["rPr"],
    "tc": ["tcPr"],
    "pPr": [
        "pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr",
        "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd",
        "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct",
        "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi",
        "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing",
        "mirrorIndents", "suppressOverlap", "jc", "textDirection",
        "textAlignment", "textboxTightWrap", "outlineLvl", "divId",
        "cnfStyle", "rPr", "sectPr", "pPrChange",
    ],
    "rPr": [
        "rStyle", "rFonts", "b", "bCs", "i", "iCs", "caps", "smallCaps",
        "strike", "dstrike", "outline", "shadow", "emboss", "imprint",
        "noProof", "snapToGrid", "vanish", "webHidden", "color", "spacing",
        "w", "kern", "position", "sz", "szCs", "highlight", "u", "effect",
        "bdr", "shd", "fitText", "vertAlign", "rtl", "cs", "em", "lang",
        "eastAsianLayout", "specVanish", "oMath",
    ],
    "style": [
        "name", "aliases", "basedOn", "next", "link", "autoRedefine",
        "hidden", "uiPriority", "semiHidden", "unhideWhenUsed", "qFormat",
        "locked", "personal", "personalCompose", "personalReply", "rsid",
        "pPr", "rPr", "tblPr", "trPr", "tcPr", "tblStylePr",
    ],
    "lvl": [
        "start", "numFmt", "lvlRestart", "pStyle", "isLgl", "lvlJc", "pPr",
        "rPr",
    ],
    "numPr": ["ilvl", "numId"],
    "sectPr": [
        "headerReference", "footerReference", "footnotePr", "endnotePr",
        "type", "pgSz", "pgMar", "paperSrc", "pgBorders", "lnNumType",
        "pgNumType", "cols", "formProt", "vAlign", "noEndnote", "titlePg",
        "textDirection", "bidi", "rtlGutter", "docGrid", "printerSettings",
    ],
    "tblBorders": [
        "top", "left", "bottom", "right", "insideH", "insideV",
    ],
    "tblPr": [
        "tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
        "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd",
        "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
        "tblCaption", "tblDescription",
    ],
    "tcPr": [
        "cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders",
        "shd", "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign",
        "hideMark",
    ],
    "trPr": [
        "cnfStyle", "divId", "gridBefore", "gridAfter", "wBefore", "wAfter",
        "cantSplit", "trHeight", "tblHeader", "tblCellSpacing", "jc",
        "hidden", "ins", "del", "trPrChange",
    ],
    "pgMar": [],
    "rFonts": [],
}


def _local(tag):
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def _order_key(parent_local, child_local):
    table = ORDER.get(parent_local)
    if table is None:
        return None
    try:
        return table.index(child_local)
    except ValueError:
        return len(table)  # unknown -> put at the end


def get_child(parent, tag, create=True):
    """Get-or-create a direct child, inserting it at the schema-correct place.

    Returns None if not found and create=False.
    """
    full = qn(tag)
    for c in parent:
        if c.tag == full:
            return c
    if not create:
        return None
    el = ET.Element(full)
    insert_in_order(parent, el)
    return el


def insert_in_order(parent, el):
    parent_local = _local(parent.tag)
    my_key = _order_key(parent_local, _local(el.tag))
    if my_key is None:
        parent.append(el)
        return el
    for c in list(parent):
        ck = _order_key(parent_local, _local(c.tag))
        if ck is not None and ck > my_key:
            parent.insert(list(parent).index(c), el)
            return el
    parent.append(el)
    return el


def sort_children_in_place(root):
    """Recursively re-sort children of any element we have order info for."""
    for el in root.iter():
        local = _local(el.tag)
        if local in ORDER and ORDER[local]:
            kids = list(el)
            if kids and any(_order_key(local, _local(k.tag)) is not None for k in kids):
                keyed = [(_order_key(local, _local(k.tag)), i, k) for i, k in enumerate(kids)]
                # stable sort by key; unknown (len) keeps relative order at end
                keyed.sort(key=lambda t: (t[0], t[1]))
                for k in kids:
                    el.remove(k)
                for _, _, k in keyed:
                    el.append(k)
    return root


def set_attr(el, name, value):
    el.set(qn(name) if ":" in name else name, str(value))


def get_attr(el, name, default=None):
    return el.get(qn(name) if ":" in name else name, default)


# --------------------------------------------------------------------------
# String-level OPC helpers for .rels and [Content_Types].xml (default ns!)
# --------------------------------------------------------------------------

_REL_RE = re.compile(
    r'<Relationship\s+([^>/]*?)/?>', re.S)
_ATTR_RE = re.compile(r'(\w+:?\w*)="([^"]*)"')


def _parse_flat_xml(data):
    """Parse a flat <Root><Child attr="v"/>...</Root> doc into (tag, [attrs]).

    Attribute values may contain '/', so the child matcher is quote-aware.
    """
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else data
    m = re.search(r'<(\w+)[^>]*>', text)
    root_tag = m.group(1) if m else "Root"
    children = []
    for cm in re.finditer(r'<(\w+)\s+((?:[^>"]|"[^"]*")*?)/>', text):
        children.append((cm.group(1), dict(_ATTR_RE.findall(cm.group(2)))))
    # a self-closing root ("<Root .../>" with no children) is captured by the
    # child matcher too; drop it so it is not re-serialized as a child
    if children and children[0][0] == root_tag:
        children = children[1:]
    return root_tag, children


def _serialize_flat(root_tag, uri, children):
    """Serialize flat children with a DEFAULT namespace (mandatory for OPC)."""
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
    parts.append('<%s xmlns="%s">' % (root_tag, uri))
    for tag, attrs in children:
        a = "".join(' %s="%s"' % (k, _xml_escape(v)) for k, v in attrs.items())
        parts.append("<%s%s/>" % (tag, a))
    parts.append("</%s>" % root_tag)
    return "".join(parts).encode("utf-8")


def _xml_escape(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# --------------------------------------------------------------------------
# DOCX package wrapper
# --------------------------------------------------------------------------

CONTENT_TYPE_PARTS = {
    "styles": "application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml",
    "numbering": "application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml",
    "footnotes": "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml",
    "endnotes": "application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml",
    "comments": "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml",
    "header": "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml",
    "footer": "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml",
    "settings": "application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml",
    "fontTable": "application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml",
    "theme": "application/vnd.openxmlformats-officedocument.theme+xml",
    "document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
}


class Docx:
    """In-memory DOCX (OPC) package with safe part add/replace."""

    def __init__(self, path):
        self.path = path
        self.parts = {}  # part name -> bytes
        self._xml = {}   # part name -> parsed ElementTree root (write-through cache)
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                self.parts[n] = z.read(n)
        _, self._ct = _parse_flat_xml(self.parts["[Content_Types].xml"])
        _, self._root_rels = _parse_flat_xml(self.parts["_rels/.rels"])
        _, self._doc_rels = _parse_flat_xml(self.parts.get("word/_rels/document.xml.rels", b"<Relationships/>"))
        self._next_rid = self._compute_next_rid()

    def _compute_next_rid(self):
        mx = 0
        for _, attrs in self._doc_rels:
            m = re.match(r"rId(\d+)$", attrs.get("Id", ""))
            if m:
                mx = max(mx, int(m.group(1)))
        return mx + 1

    # -- content types -----------------------------------------------------
    def ensure_content_type(self, part_name, ctype):
        part_name = "/" + part_name.lstrip("/")
        for tag, attrs in self._ct:
            if tag == "Override" and attrs.get("PartName") == part_name:
                attrs["ContentType"] = ctype
                return
        self._ct.append(("Override", {"PartName": part_name, "ContentType": ctype}))

    # -- relationships -----------------------------------------------------
    @staticmethod
    def _rel_target(part_name):
        # targets in word/_rels/document.xml.rels are relative to word/
        return part_name[len("word/"):] if part_name.startswith("word/") else part_name

    def find_rel(self, part_name):
        target = self._rel_target(part_name)
        for _, attrs in self._doc_rels:
            if attrs.get("Target") in (part_name, target):
                return attrs.get("Id")
        return None

    def ensure_rel(self, part_name, rtype):
        """Ensure document.xml.rels has a relationship to part_name; return rId."""
        existing = self.find_rel(part_name)
        if existing:
            return existing
        rid = "rId%d" % self._next_rid
        self._next_rid += 1
        self._doc_rels.append(("Relationship", {
            "Id": rid, "Type": rtype, "Target": self._rel_target(part_name)}))
        return rid

    # -- part access -------------------------------------------------------
    def get_xml(self, name):
        """Parsed part tree.  NOTE: trees are cached; in-place edits to the
        returned root persist automatically on save()."""
        if name in self._xml:
            return self._xml[name]
        data = self.parts.get(name)
        if not data:
            return None
        root = ET.fromstring(data)
        self._xml[name] = root
        return root

    def set_xml(self, name, root, ctype_key=None):
        self._xml[name] = root
        data = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
        self.parts[name] = data
        if ctype_key:
            self.ensure_content_type(name, CONTENT_TYPE_PARTS[ctype_key])

    def has_part(self, name):
        return name in self.parts and bool(self.parts[name])

    def ensure_part(self, name, ctype_key, factory):
        """Create part (via factory() -> ET root) if absent; register types+rels."""
        if not self.has_part(name):
            root = factory()
            self.set_xml(name, root, ctype_key)
        else:
            self.ensure_content_type(name, CONTENT_TYPE_PARTS[ctype_key])
        rtype = {
            "styles": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
            "numbering": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering",
            "footnotes": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes",
            "endnotes": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes",
            "comments": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
            "header": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header",
            "footer": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer",
            "settings": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings",
            "fontTable": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/fontTable",
        }.get(ctype_key)
        if rtype:
            self.ensure_rel(name, rtype)

    # -- document shortcuts --------------------------------------------------
    def document(self):
        return self.get_xml("word/document.xml")

    def styles(self):
        return self.get_xml("word/styles.xml")

    def numbering(self):
        return self.get_xml("word/numbering.xml")

    def body(self):
        return self.document().find(q("body"))

    def save(self, out_path):
        # flush cached XML trees (in-place edits) back to part bytes
        for name, root in self._xml.items():
            self.parts[name] = ET.tostring(
                root, encoding="UTF-8", xml_declaration=True)
        # serialize the two flat OPC parts with DEFAULT namespaces
        self.parts["[Content_Types].xml"] = _serialize_flat("Types", CT, self._ct)
        self.parts["_rels/.rels"] = _serialize_flat("Relationships", REL, self._root_rels)
        self.parts["word/_rels/document.xml.rels"] = _serialize_flat(
            "Relationships", REL, self._doc_rels)
        # deterministic order, no duplicates
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            for name in sorted(self.parts):
                z.writestr(name, self.parts[name])


# --------------------------------------------------------------------------
# High-level helpers
# --------------------------------------------------------------------------

def para_text(p):
    """Concatenate all w:t under paragraph (incl. instrText skipped)."""
    out = []
    for t in p.iter(q("t")):
        out.append(t.text or "")
    return "".join(out)


def para_text_with_tabs(p):
    out = []
    for node in p.iter():
        if node.tag == q("t"):
            out.append(node.text or "")
        elif node.tag == q("tab"):
            out.append("\t")
        elif node.tag in (q("br"), q("cr")):
            out.append("\n")
    return "".join(out)


def set_run_fonts(rPr, ascii_font=None, eastasia_font=None, hansi=None, cs=None):
    rF = get_child(rPr, "w:rFonts")
    if ascii_font:
        set_attr(rF, "w:ascii", ascii_font)
        set_attr(rF, "w:hAnsi", hansi or ascii_font)
    if eastasia_font:
        set_attr(rF, "w:eastAsia", eastasia_font)
    if cs:
        set_attr(rF, "w:cs", cs)
    return rF


def set_run_size(rPr, half_points, half_points_cs=None):
    sz = get_child(rPr, "w:sz")
    set_attr(sz, "w:val", int(half_points))
    szCs = get_child(rPr, "w:szCs")
    set_attr(szCs, "w:val", int(half_points_cs or half_points))


def set_bold(rPr, on=True):
    b = get_child(rPr, "w:b")
    key = qn("w:val")
    if not on:
        set_attr(b, "w:val", 0)
    elif key in b.attrib:
        del b.attrib[key]


def set_spacing(pPr, line=None, line_rule=None, before=None, after=None):
    sp = get_child(pPr, "w:spacing")
    if line is not None:
        set_attr(sp, "w:line", int(line))
        if line_rule:
            set_attr(sp, "w:lineRule", line_rule)
    if before is not None:
        set_attr(sp, "w:before", int(before))
        set_attr(sp, "w:beforeAutospacing", 0)
    if after is not None:
        set_attr(sp, "w:after", int(after))
        set_attr(sp, "w:afterAutospacing", 0)
    return sp


def set_indent(pPr, first_line=None, left=None, hanging=None):
    ind = get_child(pPr, "w:ind")
    if first_line is not None:
        set_attr(ind, "w:firstLine", int(first_line))
    if left is not None:
        set_attr(ind, "w:left", int(left))
    if hanging is not None:
        set_attr(ind, "w:hanging", int(hanging))
    return ind


def set_outline_lvl(pPr, lvl):
    ol = get_child(pPr, "w:outlineLvl")
    set_attr(ol, "w:val", int(lvl))


def make_el(tag, attrs=None):
    el = ET.Element(qn(tag))
    for k, v in (attrs or {}).items():
        set_attr(el, k, v)
    return el


def iter_paragraphs(root):
    return root.iter(q("p"))


def para_style_id(p):
    pPr = p.find(q("pPr"))
    if pPr is None:
        return None
    st = pPr.find(q("pStyle"))
    if st is None:
        return None
    return get_attr(st, "w:val")


def set_para_style(p, style_id):
    pPr = get_child(p, "w:pPr")
    st = get_child(pPr, "w:pStyle")
    set_attr(st, "w:val", style_id)


def style_map(styles_root):
    """styleId -> {'name','type','pPr','rPr'} plus name->styleId index."""
    out = {}
    names = {}
    for st in styles_root.findall(q("style")):
        sid = st.get(q("styleId"))
        name_el = st.find(q("name"))
        name = get_attr(name_el, "w:val") if name_el is not None else sid
        out[sid] = {
            "styleId": sid,
            "name": name,
            "type": st.get(q("type"), "paragraph"),
            "el": st,
        }
        names[(name or "").lower()] = sid
    return out, names


def twips_to_mm(v):
    return round(int(v) * 25.4 / 1440.0, 2) if v is not None else None


def mm_to_twips(mm):
    return int(round(float(mm) * 1440.0 / 25.4))


def pt_to_twips(pt):
    return int(round(float(pt) * 20.0))


def pt_to_half(pt):
    return int(round(float(pt) * 2.0))


def half_to_pt(hp):
    return float(hp) / 2.0
