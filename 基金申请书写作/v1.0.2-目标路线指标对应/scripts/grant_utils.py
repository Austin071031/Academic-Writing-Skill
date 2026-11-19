#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""grant_utils.py — 共享 io/文本工具（基金申请书写作 Skill 核心脚本）"""
import json
import os
import re
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET
# ==== 路径契约
def env_input_dir(cli_value=None):
    """--input-dir 优先，其次 GRANT_INPUT_DIR，默认 /input。"""
    if cli_value:
        return cli_value
    return os.environ.get("GRANT_INPUT_DIR", "/input")
def env_output_dir(cli_value=None):
    """--out 优先，其次 GRANT_OUTPUT_DIR，默认 /app/output。"""
    if cli_value:
        return cli_value
    return os.environ.get("GRANT_OUTPUT_DIR", "/app/output")
def ensure_dir(path):
    if path:
        os.makedirs(path, exist_ok=True)
# ==== JSON io
def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default
def write_json(path, data):
    ensure_dir(os.path.dirname(path) or ".")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)
def append_jsonl(path, obj):
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
def record_exception(work, stage, file, error, action):
    """把异常追加到 work/exceptions.json（幂等可重跑）。"""
    try:
        path = os.path.join(work, "exceptions.json")
        data = read_json(path, [])
        if not isinstance(data, list):
            data = []
        entry = {"stage": stage, "file": str(file), "error": str(error)[:500],
                 "action": action}
        if entry not in data:
            data.append(entry)
        write_json(path, data)
    except Exception:
        pass  # 记录异常本身绝不能成为新的崩溃点
# ==== 输入枚举
SKIP_INPUT_NAMES = {"case.json", "task.md", "organizer-workorder.json"}
def iter_input_files(input_dir):
    """枚举 input_dir 下文件（递归一层），跳过 case/task/workorder。"""
    out = []
    try:
        input_dir = os.path.abspath(input_dir)
        for root, dirs, files in os.walk(input_dir):
            depth = os.path.relpath(root, input_dir).count(os.sep)
            if os.path.relpath(root, input_dir) != "." and depth >= 1:
                dirs[:] = []
            for name in sorted(files):
                if name in SKIP_INPUT_NAMES:
                    continue
                full = os.path.join(root, name)
                out.append((full, os.path.relpath(full, input_dir)))
    except Exception:
        return []
    return sorted(out, key=lambda x: x[1])
# ==== 文本抽取
_TEX_CMD = re.compile(r"\\(?:[a-zA-Z@]+\*?|.)")
def _strip_tex(text):
    text = text.replace(r"\%", "\x00PCT\x00")
    text = re.sub(r"(?<!\\)%.*", "", text)
    text = text.replace("\x00PCT\x00", "%")
    text = re.sub(r"\\(?:title|section|subsection)\*?\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\(?:begin|end)\{[^{}]*\}", "\n", text)
    text = re.sub(r"\\cite\{[^{}]*\}", "", text)
    text = _TEX_CMD.sub(" ", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"[ \t]+", " ", text)
    return text
def _extract_docx(path):
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as z:
        with z.open("word/document.xml") as f:
            root = ET.parse(f).getroot()
    lines = []
    for p in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        texts = [t.text or "" for t in p.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")]
        lines.append("".join(texts))
    return "\n".join(lines)
def _extract_pdf(path):
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "-layout", path, "-"], capture_output=True,
                           timeout=30)
        if r.returncode == 0 and r.stdout:
            return r.stdout.decode("utf-8", errors="replace")
    except Exception:
        return None
    return None
def extract_text(path):
    """按扩展名抽取纯文本。失败返回 None（调用方记录 exceptions）。"""
    try:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".md", ".txt", ".text", ".markdown", ""):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        if ext == ".docx":
            return _extract_docx(path)
        if ext == ".tex":
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return _strip_tex(f.read())
        if ext == ".pdf":
            return _extract_pdf(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None
# ==== 分段
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S")
_LIST = re.compile(r"^\s*(?:[-*+>]|\d+[.、)]|（\d+）|\(\d+\)|第[一二三四五六七八九十]+[条点])")
def split_paragraphs(text):
    """空行分段，识别 heading/list_item/table_row/body，跟踪章节 sec。"""
    blocks = re.split(r"\n\s*\n", text or "")
    out = []
    sec = ""
    for raw in blocks:
        raw = raw.strip("\n")
        if not raw.strip():
            continue
        lines = raw.splitlines()
        if any(_HEADING.match(l) for l in lines):
            kind = "heading"
            for l in lines:
                m = _HEADING.match(l)
                if m:
                    sec = re.sub(r"^\s*#{1,6}\s*", "", l).strip()
        elif any(_LIST.match(l) for l in lines):
            kind = "list_item"
        elif any(l.strip().startswith("|") and l.strip().endswith("|") for l in lines):
            kind = "table_row"
        else:
            kind = "body"
        out.append({"kind": kind, "sec": sec, "text": raw.strip()})
    return out

_SENT_SPLIT = re.compile(r"(?<=[。！？!?；;])")
def cn_sentences(text):
    """中文断句；小数点（3.14）与常见缩写（et al., Fig.）不做切分点。"""
    if not text:
        return []
    text = re.sub(r"(?<=\d)\.(?=\d)", "@DOT@", text)
    text = re.sub(r"(?i)\b(et al|e\.g|i\.e|Fig|No|Vol|pp|vs|Dr|Prof)\.", r"\1@DOT@", text)
    parts = []
    for seg in _SENT_SPLIT.split(text):
        seg = seg.replace("@DOT@", ".")
        if seg.strip():
            parts.append(seg.strip())
    return parts
# ==== 数字
_UNITS = ["Wh/kg", "mAh/g", "mA h/g", "MPa", "GPa", "μm", "nm", "mA", "eV",
          "m²", "m2", "℃", "K", "h", "g", "次", "篇", "项", "年", "万", "亿", "%", "％"]
_UNIT_ALT = {"％": "%", "m2": "m²", "mA h/g": "mAh/g", "摄氏度": "℃"}
_NUM = r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
_NUM_UNIT_RE = re.compile(
    r"(?P<num>-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*(?P<unit>" +
    "|".join(re.escape(u) for u in sorted(_UNITS, key=len, reverse=True)) + r")")
def norm_unit(unit):
    unit = (unit or "").strip()
    return _UNIT_ALT.get(unit, unit)
def norm_value(v):
    """数值归一：可解析为 float 则去尾零，否则去空白。"""
    s = str(v).strip()
    try:
        f = float(s)
        if f == int(f) and "." not in s and "e" not in s.lower():
            return str(int(f))
        return ("%s" % f).rstrip("0").rstrip(".") if "." in s else s
    except Exception:
        return s
def number_matches(a, b):
    """a/b 为 extract_numbers 条目；±0 容差、单位等价（不强制 %↔小数换算）。"""
    if norm_unit(a.get("unit")) != norm_unit(b.get("unit")):
        return False
    return norm_value(a.get("value")) == norm_value(b.get("value"))
def extract_numbers(text):
    """抽取数字：整数/小数/科学计数/百分数/中文量级（万、亿）/带单位/"""
    out = []
    if not text:
        return out
    seen = set()
    for m in _NUM_UNIT_RE.finditer(text):
        raw = m.group(0)
        if raw in seen:
            continue
        seen.add(raw)
        out.append({"value": norm_value(m.group("num")),
                    "unit": norm_unit(m.group("unit")), "raw": raw})
    # 科学计数（未被上面带单位匹配覆盖时）
    for m in re.finditer(r"(?<![\w.])(?P<v>-?\d+(?:\.\d+)?[eE][+-]?\d+)(?![\w%])", text):
        raw = m.group(0)
        if raw in seen:
            continue
        seen.add(raw)
        out.append({"value": norm_value(m.group("v")), "unit": "", "raw": raw})
    # 年份 19xx / 20xx
    for m in re.finditer(r"(?<![\w.])(?P<y>(?:19|20)\d{2})(?![\w.])", text):
        raw = m.group(0)
        if raw in seen:
            continue
        seen.add(raw)
        out.append({"value": raw, "unit": "年", "raw": raw})
    # 其余裸数（跳过已匹配区间，粗略判断）
    spans = [m.span() for m in _NUM_UNIT_RE.finditer(text)]
    for m in re.finditer(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.%])", text):
        raw = m.group(0)
        if raw in seen:
            continue
        if any(s <= m.start() < e for s, e in spans):
            continue
        seen.add(raw)
        out.append({"value": norm_value(raw), "unit": "", "raw": raw})
    return out
# ==== 引用
_CITE_SQ = re.compile(r"[［\[](\d+(?:\s*[-–,，、]\s*\d+)*)[］\]]")
_CITE_PAREN = re.compile(
    r"[（(]([^（）()]{1,60}?(?:et\s*al\.?|等|and|与|和)[^（）()]{0,30}?"
    r"(?:19|20)\d{2}[a-z]?[^（）()]{0,10})[）)]")
def expand_bracket_citation(inner):
    """'1-3, 5' -> ['1','2','3','5']。"""
    out = []
    for part in re.split(r"[,，、]", inner):
        part = part.strip()
        m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 0 < a <= b <= 500:
                out.extend(str(i) for i in range(a, b + 1))
        elif part.isdigit():
            out.append(part)
    return out
def extract_citations(text):
    """抽取引用标记：[1]、[1-3]、[1,2]、[1, 3-5]（全半角括号兼容）、"""
    out = []
    if not text:
        return out
    for m in _CITE_SQ.finditer(text):
        out.append("[" + ",".join(expand_bracket_citation(m.group(1))) + "]")
    for m in _CITE_PAREN.finditer(text):
        out.append(m.group(0).replace("（", "(").replace("）", ")"))
    seen, dedup = set(), []
    for c in out:
        if c not in seen:
            seen.add(c)
            dedup.append(c)
    return dedup
def citation_overlap(a, b):
    """两条引用是否指向同一文献集合（宽松比较）。"""
    nums_a = set(expand_bracket_citation(a.strip("[]"))) if a.startswith("[") else set()
    nums_b = set(expand_bracket_citation(b.strip("[]"))) if b.startswith("[") else set()
    if nums_a and nums_b:
        return bool(nums_a & nums_b)
    return a == b
# ==== 体貌/相似度
DONE_SIGNALS = ["已", "了", "发表", "获得", "建立", "掌握", "完成", "实现",
                "授权", "结题", "见刊"]
PLANNED_SIGNALS = ["拟", "将", "计划", "预期", "有望", "准备", "旨", "待"]
def aspect_classify(text):
    """已完成 vs 拟开展信号词分类。返回 (label, hits[])。"""
    hits_done = [w for w in DONE_SIGNALS if w in (text or "")]
    hits_plan = [w for w in PLANNED_SIGNALS if w in (text or "")]
    if hits_done and hits_plan:
        return "mixed", sorted(set(hits_done + hits_plan))
    if hits_done:
        return "completed", sorted(set(hits_done))
    if hits_plan:
        return "planned", sorted(set(hits_plan))
    return "neutral", []
def _trigrams(s):
    s = re.sub(r"\s+", "", s or "")
    if len(s) < 3:
        return {s} if s else set()
    return {s[i:i + 3] for i in range(len(s) - 2)}
def trigram_jaccard(a, b):
    """中文字符 3-gram Jaccard 相似度（0..1）。"""
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)
# ==== 七要素
DEFAULT_ELEMENTS = ["立项依据", "科学问题", "研究目标", "研究内容",
                    "创新点", "技术路线", "研究基础与可行性"]

THICKNESS = {"立项依据": 400, "技术路线": 300, "研究基础与可行性": 300}
def thickness_for(element, override=None):
    if override and isinstance(override, dict):
        for k, v in override.items():
            if element.startswith(k) or k.startswith(element):
                try:
                    return int(v)
                except Exception:
                    pass
    for k, v in THICKNESS.items():
        if element.startswith(k) or k.startswith(element):
            return v
    return 150
