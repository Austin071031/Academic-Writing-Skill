#!/usr/bin/env python3
"""parse_comments.py — 把审稿意见解析为结构化 comments.json。

功能：
1. 按审稿人分节（Reviewer 1 / 审稿人1 / R1 ...）；
2. 抽取编号意见（1. / 1.1 / Comment 2 / - 项目符号）；
3. 把每条意见拆成原子子要求（连接词切分 + 动作信号过滤）；
4. 对每个子要求给出类型、严重程度、动作类别、是否需要证据的初判，
   供 Agent 复核调整（脚本输出是草稿，不是最终裁决）。

输出: work/comments.json
  {source, comments:[{id, reviewer, raw_text,
      sub_requests:[{sub_id, text, type, severity, action_kind, needs_evidence}]}],
   stats, issues}
只依赖标准库。
"""
import argparse, json, os, re, sys

RE_REVIEWER = re.compile(
    r"^#+\s*(?:Reviewer|Referee|审稿人|评审人|评审专家)\s*[#＃]?\s*(\d+|[A-Za-z])"
    r"|^(?:Reviewer|Referee|审稿人|评审人|评审专家)\s*[#＃]?\s*(\d+|[A-Za-z])\s*[:：]?\s*$", re.I)
RE_ITEM = re.compile(
    r"^\s*(?:[-*•]\s+)?(?:Comment|Major|Minor|意见|问题|建议)?\s*"
    r"(\d+(?:\.\d+)?)\s*[.、)）:：]\s+(\S.*)$")
RE_BULLET = re.compile(r"^\s*[-*•]\s+(\S.*)$")
RE_SENT = re.compile(r"[^。！？!?；;]+[。！？!?；;]*")
RE_CONNECT = re.compile(
    r"(?:并且|同时|另外|此外|而且|还需要|还需|建议同时|以及|；|;"
    r"|\bfurthermore\b|\bmoreover\b|\bin addition\b|\badditionally\b|\balso\b)", re.I)

ACTION_WORDS = re.compile(
    r"(补充|增加|添加|删除|删去|去掉|修改|改写|重写|澄清|解释|说明|提供|给出|列出|讨论|引用|"
    r"检查|核对|报告|比较|分析|重做|重新|补做|补|缩短|压缩|扩展|润色|规范|统一|标注|"
    r"add|include|remove|delete|revise|rewrite|clarify|explain|provide|discuss|cite|"
    r"check|report|compare|analy[sz]e|redo|repeat|shorten|expand|polish|specify|justify)", re.I)

TYPE_LEX = [
    ("experiment", re.compile(r"实验|试验|对照组?|control|experiment|重复实验|replicate|验证实验|补做", re.I)),
    ("data",       re.compile(r"数据|样本量?|sample|dataset|原始数据|数据库|data\b", re.I)),
    ("statistics", re.compile(r"统计|statistic|p\s*值|p-value|显著性|significan|误差棒|error bar|标准差|置信区间", re.I)),
    ("method",     re.compile(r"方法|method|methodology|protocol|步骤|流程|算法|参数|模型设置|实验设计", re.I)),
    ("citation",   re.compile(r"引用|参考文献|文献|reference|citation|\bcite\b", re.I)),
    ("format",     re.compile(r"格式|排版|单位|缩写|图注|表注|caption|format|unit|abbreviation|字体|模板", re.I)),
    ("writing",    re.compile(r"语言|表述|写作|润色|语法|措辞|清晰|冗长|clarity|language|grammar|writing", re.I)),
    ("ethics",     re.compile(r"伦理|ethic|知情同意|consent|利益冲突|conflict of interest|数据可用性|availability", re.I)),
    ("discussion", re.compile(r"讨论|结论|机制|局限|意义|外推|discussion|conclusion|mechanism|limitation", re.I)),
]
SEV_MAJOR = re.compile(r"必须|需要|应当|务必|major|must|require|necessary|essential|critical", re.I)
SEV_MINOR = re.compile(r"建议|可以考虑|minor|suggest|recommend|optional|最好", re.I)
SEV_QUESTION = re.compile(r"为何|为什么|如何|是否|？|\?|why|how\b|whether|what", re.I)

ACTION_KIND = [
    ("add_experiment", re.compile(r"补做实验|补充实验|增加实验|对照实验|additional experiment|further experiment|control experiment", re.I)),
    ("reanalysis",     re.compile(r"重新分析|重做分析|重新统计|re-?analy|recompute|重新计算|重新拟合", re.I)),
    ("add_data",       re.compile(r"补充数据|提供数据|原始数据|样本|more data|provide.*data|数据可用", re.I)),
    ("add_citation",   re.compile(r"引用|参考文献|文献|reference|citation|\bcite\b", re.I)),
    ("delete",         re.compile(r"删除|删去|去掉|压缩|缩短|remove|delete|shorten", re.I)),
    ("format",         re.compile(r"格式|排版|单位|缩写|图注|表注|format|unit|abbreviation", re.I)),
    ("rewrite",        re.compile(r"澄清|解释|说明|改写|重写|修改|润色|clarify|explain|rewrite|revise|polish", re.I)),
]
NEEDS_EVIDENCE = {"add_experiment", "add_data", "add_citation", "reanalysis"}

def split_sentences(text):
    return [m.group(0).strip() for m in RE_SENT.finditer(text.replace("\n", " ").strip())
            if m.group(0).strip()]

def split_subrequests(text):
    """把一条意见拆成原子子要求：先按句子，再按连接词；仅保留含动作信号的片段，
    无动作信号的片段并回前一片段（避免把背景句误拆为独立要求）。"""
    pieces = []
    for sent in split_sentences(text):
        for part in RE_CONNECT.split(sent):
            part = part.strip(" ,，。;；")
            if part:
                pieces.append(part)
    reqs = []
    for p in pieces:
        if ACTION_WORDS.search(p) or SEV_QUESTION.search(p):
            reqs.append(p)
        elif reqs:
            reqs[-1] = reqs[-1] + "，" + p
        else:
            reqs.append(p)  # 首个片段即使无动作词也保留（可能是整体背景要求）
    return reqs or [text.strip()]

def classify(text):
    ctype, action = "other", "other"
    for name, rex in TYPE_LEX:
        if rex.search(text):
            ctype = name
            break
    for name, rex in ACTION_KIND:
        if rex.search(text):
            action = name
            break
    if SEV_MAJOR.search(text):
        sev = "major"
    elif SEV_MINOR.search(text):
        sev = "minor"
    elif SEV_QUESTION.search(text) and not ACTION_WORDS.search(text):
        sev = "question"
    else:
        sev = "unspecified"
    return ctype, sev, action, action in NEEDS_EVIDENCE

def parse(text):
    comments = []
    reviewer = "R?"
    rno = 0
    cur = None
    cno = 0
    lines = text.splitlines()

    def close():
        nonlocal cur
        if cur and cur["raw_text"].strip():
            comments.append(cur)
        cur = None

    for line in lines:
        m = RE_REVIEWER.match(line.strip())
        if m:
            close()
            rno += 1
            reviewer = "R" + (m.group(1) or m.group(2) or str(rno))
            cno = 0
            continue
        m = RE_ITEM.match(line)
        if m:
            close()
            cno += 1
            cur = {"num": m.group(1), "raw_text": m.group(2).strip(), "reviewer": reviewer}
            continue
        b = RE_BULLET.match(line)
        if b and cur is None:
            cno += 1
            cur = {"num": str(cno), "raw_text": b.group(1).strip(), "reviewer": reviewer}
            continue
        if line.strip():
            if cur is not None:
                cur["raw_text"] += " " + line.strip()
            elif len(line.strip()) > 30:  # 无编号长段落也视为一条意见
                cno += 1
                cur = {"num": str(cno), "raw_text": line.strip(), "reviewer": reviewer}
    close()

    out = []
    for c in comments:
        rev = c.get("reviewer", "R?")
        cid = f"{rev}-C{c['num'].replace('.', '_')}"
        subs = []
        for si, sreq in enumerate(split_subrequests(c["raw_text"]), 1):
            ctype, sev, action, need = classify(sreq)
            subs.append({"sub_id": f"{cid}-s{si}", "text": sreq, "type": ctype,
                         "severity": sev, "action_kind": action, "needs_evidence": need})
        out.append({"id": cid, "reviewer": rev, "num": c["num"],
                    "raw_text": c["raw_text"], "sub_requests": subs})
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None, help="意见文件；缺省取 inspection.json 意见候选第一")
    ap.add_argument("--work", default="/app/work")
    args = ap.parse_args()

    src = args.file
    if not src:
        insp_path = os.path.join(args.work, "inspection.json")
        insp = {}
        if os.path.exists(insp_path):
            with open(insp_path, encoding="utf-8") as f:
                insp = json.load(f)
        cands = insp.get("comment_candidates") or []
        if not cands:
            print("[parse_comments][FATAL] 无意见候选文件", file=sys.stderr)
            return 1
        src = cands[0]["path"]
    if not os.path.exists(src):
        print(f"[parse_comments][FATAL] 文件不存在: {src}", file=sys.stderr)
        return 1

    text = None
    if src.lower().endswith(".pdf"):
        import subprocess
        try:
            r = subprocess.run(["pdftotext", "-layout", src, "-"], capture_output=True, timeout=120)
            text = r.stdout.decode("utf-8", "ignore") if r.returncode == 0 else None
        except Exception as e:
            print(f"[parse_comments][FATAL] PDF 抽取失败: {e}", file=sys.stderr)
            return 1
    else:
        for enc in ("utf-8", "utf-8-sig", "gb18030", "latin-1"):
            try:
                with open(src, encoding=enc) as f:
                    text = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue
    if not text or not text.strip():
        print("[parse_comments][FATAL] 意见文件为空或不可读", file=sys.stderr)
        return 1

    comments = parse(text)
    issues = []
    n_sub = sum(len(c["sub_requests"]) for c in comments)
    if not comments:
        issues.append("未解析出任何意见条目，需人工阅读原文件手动建 comments.json")
    multi = sum(1 for c in comments if len(c["sub_requests"]) > 1)
    model = {"source_file": src, "comments": comments,
             "stats": {"n_comments": len(comments), "n_sub_requests": n_sub,
                       "n_multi_sub_comments": multi,
                       "n_needs_evidence": sum(1 for c in comments for s in c["sub_requests"]
                                               if s["needs_evidence"])},
             "issues": issues,
             "note": "脚本初判的 type/severity/action_kind 供 Agent 复核；拆分子要求不得遗漏原意见任何片段。"}
    os.makedirs(args.work, exist_ok=True)
    out = os.path.join(args.work, "comments.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)
    st = model["stats"]
    print(f"[parse_comments] 意见={st['n_comments']} 子要求={st['n_sub_requests']} "
          f"多子要求意见={st['n_multi_sub_comments']} 需证据={st['n_needs_evidence']}")
    for iss in issues:
        print(f"[parse_comments][issue] {iss}", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
