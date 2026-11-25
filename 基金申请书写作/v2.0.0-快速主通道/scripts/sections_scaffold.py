#!/usr/bin/env python3
"""sections_scaffold.py — 七要素章节骨架预生成（v2.0.0 快速主通道专属，stdlib only）。

读 work/fact_ledger.json + work/inspection.json（可选 work/materials.json 取
role_guess），生成 work/sections/01_立项依据.md … 07_研究基础与可行性.md 七个
骨架文件，每个含：
  - 首行 `# 要素名`（draft_builder 依此识别要素）；
  - 字数目标注释（立项依据≥600、技术路线≥450、研究基础与可行性≥400、其余≥250）；
  - 与本要素最相关的 FID 候选清单（HTML 注释，按要素关键词 + role_guess 匹配，
    每要素 ≤12 条，列出 fid/type/value/unit/来源 pid）；
  - 待填槽位「【在此撰写：…】」。

幂等规则：文件已存在且含〔F〕标记（Agent 已写）则不覆盖；仍是骨架（无〔F〕）
则重跑可刷新候选清单。只写 work/sections/，其余文件只读。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu  # noqa: E402

DEFAULT_ELEMENTS = ["立项依据", "科学问题", "研究目标", "研究内容",
                    "创新点", "技术路线", "研究基础与可行性"]

# 字数目标（写作目标；elements_check 机检阈值不变，见 references/method_rules.md）
def char_target(element):
    if "立项" in element:
        return 600
    if "技术路线" in element:
        return 450
    if "研究基础" in element:
        return 400
    return 250

# 每要素匹配画像：角色加权 + 事实类型加权 + 关键词（命中 context/value/sec 计分）
ELEMENT_PROFILE = {
    "立项依据": {
        "roles": {"paper": 3, "guide": 1},
        "types": {"citation": 3, "pub_mention": 2, "number": 2, "term": 1},
        "keywords": ["研究", "报道", "现状", "瓶颈", "尚不清楚", "机制", "亟待",
                     "缺乏", "难以", "效率", "稳定", "进展", "综述"]},
    "科学问题": {
        "roles": {"paper": 2, "guide": 1},
        "types": {"citation": 2, "term": 2, "pub_mention": 1},
        "keywords": ["尚不清楚", "机制不明", "尚未", "缺乏", "难以", "亟待",
                     "瓶颈", "挑战", "关键", "问题", "有待"]},
    "研究目标": {
        "roles": {"paper": 2, "guide": 1},
        "types": {"number": 3, "term": 1},
        "keywords": ["效率", "达到", "提升", "目标", "指标", "保持", "降低"]},
    "研究内容": {
        "roles": {"paper": 2, "data": 2},
        "types": {"number": 2, "term": 2, "abbrev": 1},
        "keywords": ["制备", "表征", "机制", "方法", "工艺", "体系", "研究",
                     "计算", "实验"]},
    "创新点": {
        "roles": {"paper": 3, "prior_work": 1},
        "types": {"citation": 3, "pub_mention": 3, "number": 1},
        "keywords": ["报道", "已有", "方案", "方法", "策略", "机制", "难",
                     "瓶颈", "钝化", "提出"]},
    "技术路线": {
        "roles": {"paper": 2, "data": 2},
        "types": {"number": 2, "term": 2},
        "keywords": ["制备", "表征", "工艺", "平台", "测试", "中试", "计算",
                     "实验", "路线", "涂布"]},
    "研究基础与可行性": {
        "roles": {"prior_work": 4},
        "types": {"pub_mention": 3, "number": 2, "citation": 1},
        "keywords": ["发表", "专利", "项目", "平台", "中试", "团队", "申请人",
                     "基金", "论文", "授权", "结题", "掌握", "建立"]},
}
GENERIC_PROFILE = {"roles": {"paper": 1, "prior_work": 1, "guide": 1},
                   "types": {"number": 1, "citation": 1, "pub_mention": 1,
                             "term": 1},
                   "keywords": ["研究", "方法", "机制"]}

MAX_CANDIDATES = 12
FID_MARK = re.compile(r"〔F\d{4}〕")


def profile_for(element):
    if element in ELEMENT_PROFILE:
        return ELEMENT_PROFILE[element]
    for key in ELEMENT_PROFILE:
        if key in element or element in key:
            return ELEMENT_PROFILE[key]
    if "创新" in element:
        return ELEMENT_PROFILE["创新点"]
    if "基础" in element or "可行" in element:
        return ELEMENT_PROFILE["研究基础与可行性"]
    return GENERIC_PROFILE


def role_index(materials):
    """file_id → role_guess（材料文件级启发式角色）。"""
    idx = {}
    for f in materials.get("files", []):
        idx[f.get("file_id", "")] = f.get("role_guess", "other")
    return idx


def score_entry(e, profile, roles):
    s = 0
    role = roles.get(e.get("source", {}).get("file_id", ""), "other")
    s += profile["roles"].get(role, 0)
    s += profile["types"].get(e.get("type", ""), 0)
    text = "%s %s %s" % (e.get("value", ""), e.get("context", ""),
                         e.get("sec", ""))
    hits = sum(1 for w in profile["keywords"] if w in text)
    s += hits
    return s


def pick_candidates(entries, element, roles):
    profile = profile_for(element)
    scored = [(score_entry(e, profile, roles), e.get("fid", ""), e)
              for e in entries]
    scored.sort(key=lambda t: (-t[0], t[1]))
    top = [e for s, _, e in scored if s > 0][:MAX_CANDIDATES]
    if not top:  # 兜底：台账非空则给前若干条，保证候选清单非空
        top = [e for _, _, e in scored[:MAX_CANDIDATES]]
    return top


def skeleton_text(element, target, candidates):
    lines = ["# %s" % element, ""]
    lines.append("<!-- sections_scaffold 骨架：整文件可覆写为成稿；"
                 "本要素字数目标 ≥%d 字（正式成稿以 inspection/workorder "
                 "字数要求为准） -->" % target)
    lines.append("<!-- 候选事实（fact_ledger.json，按要素关键词+role_guess "
                 "匹配，≤12 条；引用时句末标〔Fxxxx〕）： -->")
    if candidates:
        for e in candidates:
            unit = e.get("unit") or "-"
            lines.append("<!--   %s | %s | %s | %s | 来源 %s -->"
                         % (e.get("fid"), e.get("type"), e.get("value"),
                            unit, e.get("source", {}).get("pid", "?")))
    else:
        lines.append("<!--   （台账为空：材料事实缺失，须标〔确认〕并登记 "
                     "manual_confirmations） -->")
    lines.append("")
    lines.append("【在此撰写：%s 正文，≥%d 字；材料事实句末标〔Fxxxx〕，"
                 "拟开展内容标〔拟〕，材料不足/冲突标〔确认〕】"
                 % (element, target))
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="七要素章节骨架预生成（幂等）")
    ap.add_argument("--work", required=True)
    args = ap.parse_args()
    work = args.work

    ledger = gu.read_json(os.path.join(work, "fact_ledger.json"),
                          default={"entries": []})
    inspection = gu.read_json(os.path.join(work, "inspection.json"), default={})
    materials = gu.read_json(os.path.join(work, "materials.json"),
                             default={"files": []})
    entries = ledger.get("entries", [])
    elements = inspection.get("required_elements") or DEFAULT_ELEMENTS
    roles = role_index(materials)

    sec_dir = os.path.join(work, "sections")
    os.makedirs(sec_dir, exist_ok=True)

    created, skipped = 0, 0
    for i, element in enumerate(elements, 1):
        path = os.path.join(sec_dir, "%02d_%s.md" % (i, element))
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                old = f.read()
            if FID_MARK.search(old):
                skipped += 1
                print("[scaffold] 保留 %s（含〔F〕标记，Agent 已写）"
                      % os.path.basename(path))
                continue
        cand = pick_candidates(entries, element, roles)
        with open(path, "w", encoding="utf-8") as f:
            f.write(skeleton_text(element, char_target(element), cand))
        created += 1
        print("[scaffold] 生成 %s（候选事实 %d 条，字数目标≥%d）"
              % (os.path.basename(path), len(cand), char_target(element)))

    print("[scaffold] done: 生成/刷新=%d 保留=%d → %s"
          % (created, skipped, sec_dir))
    if not entries:
        print("[scaffold] 警告：fact_ledger 为空，候选清单将为空；"
              "请先跑 fact_ledger.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
