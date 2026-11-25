#!/usr/bin/env python3
"""scanutil.py — 结构诊断共享工具库（纯标准库）。
被 six_scan.py 与各版本引擎 import；提供分词、相似度、提示词表、章节角色归类、
统一 finding 构造。所有阈值集中在 THRESH，便于复核与调参。
"""
import re, json, os

# ---------------- 提示词表（中英双语） ----------------
RQ_CUES = re.compile(
    r"(研究问题|本文旨在|旨在|本研究旨在|本文试图|试图解决|核心问题|关键问题|"
    r"为了回答|本文关注|研究目标|研究目的|we aim|this paper (aims|asks|addresses|investigates)|"
    r"research question|RQ\s*\d|we investigate|we address|the goal of this (paper|study|work))", re.I)
CONTRIBUTION_CUES = re.compile(
    r"(本文(的)?(主要)?贡献|我们的贡献|主要工作|创新点|首次提出|首次|"
    r"our (main )?contribution|we (propose|present|introduce)|novel|for the first time|"
    r"贡献(如下|包括|有))", re.I)
CLAIM_CUES = re.compile(
    r"(表明|证明|说明|显示|揭示|反映|可见|意味着|证实了|验证了|导致了|使得|从而|因此|"
    r"显著(优于|提高|提升|降低|改善)|优于|超过|大幅|有效(地)?(提高|提升|降低|改善|解决)|"
    r"show(s|n)? that|demonstrate(s|d)? that|indicate(s|d)? that|suggest(s|ed)? that|"
    r"reveal(s|ed)?|prove(s|n)? that|therefore|thus|hence|significantly (better|higher|lower|improve))", re.I)
EVIDENCE_CITES = re.compile(
    r"(\[\d+(?:\s*[-–,，]\s*\d+)*\]|（[^（）()]{1,50}?(19|20)\d{2}[a-z]?）|"
    r"\([A-Z][A-Za-z\-]+( et al\.?)?,?\s*(19|20)\d{2}[a-z]?\)|\\cite\{[^}]*\})")
EVIDENCE_FIGTAB = re.compile(
    r"(图\s*\d|表\s*\d|附图|附表|Fig\.?\s*\d|Figure\s*\d|Table\s*\d|Tab\.?\s*\d|"
    r"公式\s*\(?\d|Eq\.?\s*\(?\d|Equation\s*\(?\d|附录\s*[A-Z\d]|Appendix\s*[A-Z\d]|"
    r"\\ref\{[^}]*\}|第\s*\d+\s*(章|节)|Section\s*\d)", re.I)
EVIDENCE_NUMBER = re.compile(
    r"(\d+(\.\d+)?\s*(%|％|‰|倍|×|x\b|ms\b|s\b|kg\b|g\b|mg\b|mM\b|mol\b|K\b|°C|℃|"
    r"mAh|Wh|V\b|A\b|MPa|GPa|nm\b|μm|mm\b|cm\b|m\b|Hz\b|GHz\b|dB\b))")
CAUSAL_CUES = re.compile(
    r"(导致|促使|使得|提高了|提升了|降低了|改善了|决定(了)?|驱动|带来|造成|"
    r"cause(s|d)?|lead(s)? to|led to|improve(s|d)?|increase(s|d)?|reduce(s|d)?|"
    r"enhance(s|d)?|boost(s|ed)?|result(s|ed)? in|drive(s|n)?)", re.I)
CORRELATION_CUES = re.compile(
    r"(相关(性)?|关联|伴随|正相关|负相关|correlat\w+|associat\w+|co-occur\w*|linked to)", re.I)
ABSOLUTE_CUES = re.compile(
    r"(所有|任何|任意|完全|彻底|绝对|无一例外|必然|总是|从不|"
    r"\ball\b|\bany\b|\balways\b|\bnever\b|\bcompletely\b|\bguarantee\w*\b|\bprove[ns]?\b)", re.I)
DESIGN_CUES = re.compile(
    r"(对照(组|实验)?|控制变量|随机(分组|采样)?|消融|ablation|control( group|led)?|"
    r"randomi[sz]\w*|baseline|基线|交叉验证|cross-validation|独立测试集)", re.I)
LIMITATION_CUES = re.compile(
    r"(局限|不足|限制|未来工作|展望|适用范围|边界条件|假设|前提条件|"
    r"limitation\w*|future work|threats? to validity|assumption\w*|scope)", re.I)
CONNECTIVES = re.compile(
    r"^(然而|但是|但|不过|此外|另外|同时|因此|所以|于是|进一步(地|说)?|相比之下|"
    r"另一方面|另一方面来看|值得一提|需要注意|综上|总的来看|为此|由此|基于|"
    r"However|But|Moreover|Furthermore|In addition|Additionally|Therefore|Thus|Hence|"
    r"Meanwhile|In contrast|By contrast|Overall|Specifically|Notably|To this end|"
    r"Nevertheless|Nonetheless|Consequently|In summary|First|Second|Third|Finally)", re.I)
NUM_IN_CONCL = re.compile(r"\d+(?:\.\d+)?\s*(?:%|％|倍|×)?")
RQ_NUMBERED = re.compile(r"(RQ\s*\d+|问题\s*\d+|Q\s*\d+[:：])", re.I)

ROLE_MAP = [
    ("abstract", ("摘要", "abstract", "summary")),
    ("keywords", ("关键词", "关键字", "keywords")),
    ("introduction", ("引言", "前言", "绪论", "introduction")),
    ("related_work", ("相关工作", "文献综述", "研究现状", "背景", "related work", "literature review", "background")),
    ("method", ("方法", "研究方法", "材料与方法", "实验方法", "模型", "method", "methodology", "materials and methods", "approach", "model", "experimental setup", "实验设置", "实验设计")),
    ("experiment", ("实验", "仿真", "实验结果", "experiments", "evaluation", "评估", "评测")),
    ("results", ("结果", "结果与讨论", "结果分析", "results")),
    ("discussion", ("讨论", "discussion")),
    ("conclusion", ("结论", "总结", "结论与展望", "总结与展望", "conclusion")),
    ("acknowledgment", ("致谢", "acknowledg")),
    ("references", ("参考文献", "引用文献", "references", "bibliography")),
    ("appendix", ("附录", "appendix", "supplement")),
]
CANONICAL_ORDER = ["abstract", "keywords", "introduction", "related_work", "method",
                   "experiment", "results", "discussion", "conclusion",
                   "acknowledgment", "references", "appendix"]

THRESH = {
    "para_dup_jaccard": 0.55,      # 跨章节段落重复
    "para_near_jaccard": 0.30,     # 近似重复
    "sent_dup_jaccard": 0.80,      # 句子级重复
    "gap_lex_jaccard": 0.05,       # 相邻段落衔接缺失的词面重叠下限
    "section_imbalance": 0.55,     # 单一章节占正文比例上限
    "rq_cover_overlap": 0.20,      # 研究问题术语在章节中的覆盖率下限
    "claim_echo_jaccard": 0.35,    # 摘要/引言论断与结论呼应的相似度下限
}

STOP_EN = set("""a an the and or of to in for on with by is are was were be been we our this that
these those it its as at from into such can may might could should would will shall not no""".split())

def cn_bigrams(text):
    chars = re.findall(r"[一-鿿]", text)
    return set("".join(chars[i:i + 2]) for i in range(len(chars) - 1))

def en_words(text):
    return set(w.lower() for w in re.findall(r"[A-Za-z][A-Za-z\-]{2,}", text)
               if w.lower() not in STOP_EN)

def terms(text):
    """内容词集合：中文二字组 + 英文实词。"""
    return cn_bigrams(text) | en_words(text)

def shingles(text, n=3):
    chars = re.findall(r"[一-鿿A-Za-z0-9]", text)
    if len(chars) < n:
        return set(["".join(chars)]) if chars else set()
    return set("".join(chars[i:i + n]) for i in range(len(chars) - n + 1))

def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter) if inter else 0.0

def classify_role(heading):
    low = (heading or "").lower()
    for role, keys in ROLE_MAP:
        for k in keys:
            if k in low:
                return role
    return "other"

def short(text, n=80):
    t = re.sub(r"\s+", " ", text or "").strip()
    return t if len(t) <= n else t[: n - 1] + "…"

def make_finding(fid, dimension, ftype, section, para_id, sent_id, quote,
                 evidence, action_op, action_instruction, severity="medium",
                 confidence=0.7, status="待作者复核"):
    return {
        "id": fid, "dimension": dimension, "type": ftype,
        "location": {"section": section, "para_id": para_id, "sentence_id": sent_id},
        "quote": short(quote, 120), "evidence": evidence,
        "action": {"op": action_op, "instruction": action_instruction},
        "severity": severity, "confidence": round(confidence, 2), "status": status,
    }

def load_structure(work):
    with open(os.path.join(work, "structure.json"), encoding="utf-8") as f:
        return json.load(f)

def save_findings(work, name, findings):
    path = os.path.join(work, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(findings, f, ensure_ascii=False, indent=1)
    return path

def append_change_log(work, entries):
    path = os.path.join(work, "change_log.json")
    log = []
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                log = json.load(f)
        except Exception:
            log = []
    log.extend(entries)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)

def section_sentences(model, roles):
    return [s for s in model["sentences"] if classify_role(
        next((sec["heading"] for sec in model["sections"] if sec["id"] == s["section_id"]), "")
    ) in roles]

def role_of_section(model, sec_id):
    h = next((s["heading"] for s in model["sections"] if s["id"] == sec_id), "")
    return classify_role(h)
