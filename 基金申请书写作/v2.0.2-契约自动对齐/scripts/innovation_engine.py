#!/usr/bin/env python3
"""innovation_engine.py — 创新点差异定位引擎（grant-innovation-precision 专属）。

子命令：
  seed  —— 从材料与事实台账机选「代表性已有工作」对比锚点候选
            （paper 角色材料的 citation/pub_mention 类事实）+ gap 上下文
            → work/innovation_seed.json，供 Agent 写创新点时逐条对比
  audit —— 审计草稿创新点节（兼容 特色与创新 / 创新与特色）：
            missing_section(high) / banned_modifier(high) /
            no_baseline_anchor(medium) / no_difference_statement(medium) /
            three_dim_incomplete(medium) → work/findings.json

判据设计见 references/innovation_method.md。只读 work/ 下文件，幂等。
分工说明：source_audit.py 全稿扫部分修饰词给 low 提示；本引擎负责
创新点节的 high 级判定与差异定位结构审计，两者互补不重复。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu  # noqa: E402

# 创新点节的要素名（兼容别名）
INNOVATION_ELEMENTS = ("创新点", "特色与创新", "创新与特色")

# 不可核验修饰词黑名单（创新点节命中 → high）
BANNED_MODIFIERS = ["首次", "国际领先", "填补空白", "国际先进", "国内首创",
                    "世界领先", "原创性", "重大突破", "国际一流", "领跑"]

# 对比锚点：文本信号词（〔F〕指向 citation/pub_mention 类亦算锚点）
BASELINE_WORDS = ["已有工作", "现有研究", "现有方法", "文献", "传统方法",
                  "目前主流"]

# 差异表述信号词
DIFF_WORDS = ["不同于", "区别于", "相比", "优于", "而非", "改为",
              "突破了", "克服了", "解决了", "避免了"]

# 三维覆盖信号词（全节检查，不要求逐条）
DIM_NEW_WORDS = ["新在", "新机制", "新方法", "新策略", "新体系", "新思路",
                 "新途径", "新原理", "提出", "引入", "建立", "发展"]
DIM_HARD_WORDS = ["难", "挑战", "瓶颈", "复杂", "耦合", "缺乏"]
DIM_FEASIBLE_WORDS = ["申请人", "本团队", "本课题组", "已", "前期", "平台",
                      "基础"]

# gap 信号词（seed 抽取 gap 上下文用）
GAP_WORDS = ["尚不清楚", "机制不明", "尚未", "缺乏", "难以", "亟待", "瓶颈",
             "不足", "挑战", "仍待", "受限于", "制约", "有待", "尚未见"]

# 编号条目起始 pattern（创新点一 / 1. / （1） / ① 等）
ITEM_START = re.compile(
    r"^\s*(?:创新[点性][一二三四五六七八九十\d]*|"
    r"第[一二三四五六七八九十\d]+[点条]|"
    r"\d+\s*[.、]|"
    r"（[一二三四五六七八九十\d]+）|"
    r"\([一二三四五六七八九十\d]+\)|"
    r"[①②③④⑤⑥⑦⑧⑨⑩])")

FID_MARK = re.compile(r"〔(F\d{4})〕")


def load_work(work):
    ledger = gu.read_json(os.path.join(work, "fact_ledger.json"),
                          default={"entries": []})
    materials = gu.read_json(os.path.join(work, "materials.json"),
                             default={"files": []})
    draft = gu.read_json(os.path.join(work, "draft.json"),
                         default={"paragraphs": []})
    return ledger, materials, draft


def para_index(materials):
    """pid → (role_guess, file_id, text)"""
    idx = {}
    for f in materials.get("files", []):
        for p in f.get("paragraphs", []):
            idx[p.get("pid", "")] = (f.get("role_guess", "other"),
                                     f.get("file_id", ""), p.get("text", ""))
    return idx


def cmd_seed(work):
    ledger, materials, _ = load_work(work)
    pidx = para_index(materials)

    anchors, seen = [], set()
    for e in ledger.get("entries", []):
        if e.get("type") not in ("citation", "pub_mention"):
            continue
        src = e.get("source", {})
        pid = src.get("pid", "")
        role, file_id, ptext = pidx.get(pid, ("other", "", ""))
        # 代表性已有工作锚点：只用 paper 角色材料中的引用/成果线索事实
        if role != "paper":
            continue
        key = (e.get("fid"), pid)
        if key in seen:
            continue
        seen.add(key)
        excerpt = (ptext or e.get("context", "")).strip()
        anchors.append({"fid": e.get("fid"), "pid": pid,
                        "type": e.get("type"), "value": e.get("value"),
                        "excerpt": excerpt[:160]})

    gap_contexts, seen_gap = [], set()
    for f in materials.get("files", []):
        for p in f.get("paragraphs", []):
            text = p.get("text", "")
            for w in GAP_WORDS:
                for m in re.finditer(re.escape(w), text):
                    k = (p.get("pid"), w)
                    if k in seen_gap:
                        continue
                    seen_gap.add(k)
                    s = max(0, m.start() - 50)
                    gap_contexts.append({"pid": p.get("pid"),
                                         "file_id": f.get("file_id"),
                                         "signal": w,
                                         "excerpt": text[s:m.end() + 50].strip()})
                    break  # 每段每词取一次

    seed = {
        "note": "创新点对比锚点候选（机器初筛）。写每条创新点时：先锚定一条"
                "已有工作〔F〕，再写差异表述（不同于/区别于/相比/而非/改为），"
                "最后补三维（新在哪/为什么难/凭什么做得成）。禁用修饰词黑名单。",
        "prior_work_anchors": anchors[:40],
        "gap_contexts": gap_contexts[:40],
        "candidate_counts": {"prior_work_anchors": len(anchors),
                             "gap_contexts": len(gap_contexts)},
        "banned_modifiers": BANNED_MODIFIERS,
    }
    gu.write_json(os.path.join(work, "innovation_seed.json"), seed)
    print("[innovation seed] 锚点候选=%d gap 上下文=%d → work/innovation_seed.json"
          % (len(anchors), len(gap_contexts)))
    if not anchors:
        print("[innovation seed] 警告：无 paper 角色 citation/pub_mention 锚点候选，"
              "创新点对比对象须 Agent 复核 role_guess 后手工选取或登记缺口")
    return 0


def split_items(paragraphs):
    """把创新点节段落切成「条目」：编号条目优先，否则整段为一条。
    返回 [{dpid, text}]。"""
    items = []
    for p in paragraphs:
        text = p.get("text", "")
        dpid = p.get("dpid")
        lines = text.split("\n")
        starts = [i for i, ln in enumerate(lines) if ITEM_START.match(ln)]
        if len(starts) >= 2:  # 段内含多个编号条目 → 按起始行切分
            starts.append(len(lines))
            for a, b in zip(starts[:-1], starts[1:]):
                items.append({"dpid": dpid,
                              "text": "\n".join(lines[a:b]).strip()})
        else:
            items.append({"dpid": dpid, "text": text.strip()})
    return [it for it in items if it["text"]]


def cmd_audit(work):
    ledger, _, draft = load_work(work)
    paragraphs = [p for p in draft.get("paragraphs", [])
                  if p.get("element") in INNOVATION_ELEMENTS]
    findings = []
    if not paragraphs:
        findings.append({
            "severity": "high", "kind": "missing_section", "dpid": None,
            "msg": "草稿中未找到「创新点」章节（sections 文件首行 # 创新点；"
                   "兼容 特色与创新 / 创新与特色）",
            "suggestion": "补写创新点节后重跑 draft_builder 与本审计"})
        gu.write_json(os.path.join(work, "findings.json"),
                      {"engine": "innovation_engine", "findings": findings})
        print("[innovation audit] findings=1 (high=1)")
        return 0

    full_text = "\n".join(p.get("text", "") for p in paragraphs)
    fid_type = {e.get("fid"): e.get("type")
                for e in ledger.get("entries", [])}

    # 1) 不可核验修饰词（high；source_audit 的 low 提示与本引擎分工不同）
    seen_mod = set()
    for p in paragraphs:
        text = p.get("text", "")
        for w in BANNED_MODIFIERS:
            if w in text and (p.get("dpid"), w) not in seen_mod:
                seen_mod.add((p.get("dpid"), w))
                findings.append({
                    "severity": "high", "kind": "banned_modifier",
                    "dpid": p.get("dpid"),
                    "msg": "创新点节命中不可核验修饰词「%s」（无法由材料核验，"
                           "评审视为空泛表态）" % w,
                    "suggestion": "删除「%s」，改为与具体已有工作的差异表述并"
                                  "加〔F〕锚点，句式：已有工作 X 做了…〔Fxxxx〕，"
                                  "本课题不同于/区别于 X，改为/而非…" % w})

    # 2) 逐条目：对比锚点 + 差异表述
    items = split_items(paragraphs)
    for it in items:
        text = it["text"]
        # 对比锚点：〔F〕指向 citation/pub_mention 类，或文本含已有工作类信号
        anchor_ok = False
        for fid in FID_MARK.findall(text):
            if fid_type.get(fid) in ("citation", "pub_mention"):
                anchor_ok = True
                break
        if not anchor_ok and any(w in text for w in BASELINE_WORDS):
            anchor_ok = True
        if not anchor_ok:
            findings.append({
                "severity": "medium", "kind": "no_baseline_anchor",
                "dpid": it["dpid"],
                "msg": "创新点无对比锚点：条目「%s…」既无指向 citation/"
                       "pub_mention 类事实的〔F〕标记，也无 已有工作/现有研究/"
                       "文献 等对比对象表述" % text[:30],
                "suggestion": "从 work/innovation_seed.json 的 prior_work_anchors "
                              "选一条代表性已有工作，写明对比对象并加〔Fxxxx〕锚点"})
        # 差异表述
        if not any(w in text for w in DIFF_WORDS):
            findings.append({
                "severity": "medium", "kind": "no_difference_statement",
                "dpid": it["dpid"],
                "msg": "创新点未写明与已有工作的差异：条目「%s…」无 不同于/"
                       "区别于/相比/优于/而非/改为 等差异表述词" % text[:30],
                "suggestion": "补差异句：不同于已有工作 X 的…做法，本课题改为/而非…；"
                              "优势写可核验的机制或指标差异，不写 领先/先进"})

    # 3) 三维覆盖（全节检查，不要求逐条）
    # 「首次提出」不算「新在哪里」的证据：首次属黑名单词，须改用 提出/引入/建立/发展
    dim_text = full_text.replace("首次提出", "")
    dims = [
        ("新在哪里", DIM_NEW_WORDS,
         "补「新在哪里」：用 提出/引入/建立/发展 + 新机制/新方法/新策略 "
         "写清新的对象（不要用「首次提出」凑数，首次属黑名单词）"),
        ("为什么难", DIM_HARD_WORDS,
         "补「为什么难」：写清该创新点难在何处（难点/挑战/瓶颈/耦合复杂/"
         "长期缺乏手段），否则创新点只是愿望不是攻关"),
        ("凭什么做得成", DIM_FEASIBLE_WORDS,
         "补「凭什么做得成」：锚定申请人/本团队已完成的前期成果、平台与"
         "基础（带〔F〕），证明该创新点可落地"),
    ]
    for name, words, hint in dims:
        if not any(w in dim_text for w in words):
            findings.append({
                "severity": "medium", "kind": "three_dim_incomplete",
                "dpid": None,
                "msg": "创新点节三维覆盖不完整：缺「%s」一维（全节未见相应"
                       "信号词）" % name,
                "suggestion": hint})

    gu.write_json(os.path.join(work, "findings.json"),
                  {"engine": "innovation_engine", "findings": findings})
    sev = {}
    for f in findings:
        sev[f["severity"]] = sev.get(f["severity"], 0) + 1
    print("[innovation audit] 条目数=%d findings=%d %s"
          % (len(items), len(findings),
             " ".join("%s=%d" % kv for kv in sorted(sev.items())) or "(clean)"))
    return 0


def main():
    ap = argparse.ArgumentParser(description="创新点差异定位引擎")
    ap.add_argument("cmd", choices=["seed", "audit"])
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    if args.cmd == "seed":
        return cmd_seed(args.work)
    return cmd_audit(args.work)


if __name__ == "__main__":
    sys.exit(main())
