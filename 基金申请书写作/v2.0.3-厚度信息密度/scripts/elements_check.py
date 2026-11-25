#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""elements_check.py --work W [--out O]   （v2.0.3 厚度信息密度版）

七要素覆盖检查：presence / 段落数 / 字数（厚度阈值）+ 证据密度 + 可执行扩展指令。

相对 v1.0.3 的变更（命令行接口与 element_map.json 原有键保持兼容，仅新增字段）：
1) 厚度阈值提高：立项依据≥600 字、技术路线≥450 字、研究基础与可行性≥400 字、
   其余≥250 字（inspection.json 的 thickness 覆盖只能上调，不允许低于本版下限）。
2) 证据密度检查：事实类要素（立项依据/研究内容/技术路线/研究基础与可行性）
   引用不同 FID 数 ≥3 为达标，否则 element_map 中该要素 density_status="low"；
   非事实类要素 density_status="na"。
3) 对 thin 或 density=low 的要素，在 element_findings.json 的 suggestion 字段写入
   **可执行扩展指令**：该要素尚未引用但相关的 FID 候选（从 fact_ledger.json 按要素
   规则匹配，≤8 条，格式 "可考虑补入：F0012 number 26.1%（F1-P003）；…"）
   + 缺失子点提示（如立项依据缺 现状/瓶颈/我们 哪一环）。
4) element_mapping.md 表格增加"证据密度"列。

findings 原有键（element/severity/kind/chars/dpids/msg）保留，新增 suggestion、
fid_count 等键；element_map 新增 density_status 键。
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "elements_check"
FID_RE = re.compile(r"〔(F\d+)〕")

# ---- v2 厚度阈值（字符数，去空白）----
THICKNESS_V2 = {"立项依据": 600, "技术路线": 450, "研究基础与可行性": 400}
THICKNESS_V2_DEFAULT = 250

# ---- v2 证据密度：事实类要素需 ≥3 个不同 FID ----
FACT_ELEMENTS = ["立项依据", "研究内容", "技术路线", "研究基础与可行性"]
DENSITY_MIN_FIDS = 3

# 扩展指令：候选 FID 匹配规则用到的词表
GAP_WORDS = ["尚不清楚", "机制不明", "缺乏", "难以", "亟待", "瓶颈",
             "不足", "挑战", "短板", "尚待", "仍未"]
SUBPOINT_RULES = {
    "立项依据": [
        ("现状", ["报道", "已有", "目前", "现状", "进展", "表明", "研究"]),
        ("瓶颈", GAP_WORDS),
        ("我们", ["申请人", "本团队", "本课题组", "前期"]),
    ],
}
STATIC_HINTS = {
    "科学问题": "核心问题 1–3 个，须有子问题分解与边界表述（不涉及/聚焦于）",
    "研究目标": "目标条目化（编号），与研究内容逐条对应，预期指标标〔拟〕",
    "研究内容": "条目化分解并与研究目标逐条对应，每条写明拟解决的关键点",
    "创新点": "每条含对比锚点〔F〕＋差异表述（不同于/区别于/而非）＋三维覆盖",
    "技术路线": "路线步骤须与研究内容逐条对应，写明表征/计算手段、输出物与节点",
    "研究基础与可行性": "区分已完成（带〔F〕锚定成果）与拟开展（〔拟〕），覆盖成果/平台/团队",
}
MAX_CANDIDATES = 8


def strip_markers(text):
    return re.sub(r"〔[^〕]*〕", "", text or "")


def element_key(name, elements):
    """把实际 element 名映射到 required_elements 中的标准名（前缀匹配）。"""
    for e in elements:
        if name.startswith(e) or e.startswith(name):
            return e
    return name


def _prefix_hit(element, key):
    return element.startswith(key) or key.startswith(element)


def thickness_v2(element, override=None):
    """v2 厚度阈值；inspection 覆盖只能上调（取 max）。"""
    base = THICKNESS_V2_DEFAULT
    for k, v in THICKNESS_V2.items():
        if _prefix_hit(element, k):
            base = v
            break
    if override and isinstance(override, dict):
        for k, v in override.items():
            if _prefix_hit(element, k):
                try:
                    return max(base, int(v))
                except Exception:
                    pass
    return base


def is_fact_element(element):
    return any(_prefix_hit(element, k) for k in FACT_ELEMENTS)


def _has_gap(text):
    return any(w in (text or "") for w in GAP_WORDS)


def candidate_pool(element, entries, roles, used_fids):
    """按要素规则从台账中选出该要素尚未引用但相关的 FID 候选。"""
    def role_of(e):
        return roles.get((e.get("source") or {}).get("file_id", ""), "")

    fresh = [e for e in entries if e.get("fid") not in used_fids]
    pool = []
    if _prefix_hit(element, "立项依据"):
        # paper 角色的 citation/number 事实 + 含 gap 关键词的上下文
        pool = [e for e in fresh if role_of(e) == "paper"
                and (e.get("type") in ("citation", "number")
                     or _has_gap(e.get("context", "")))]
    elif _prefix_hit(element, "研究基础与可行性"):
        # prior_work 角色的 pub_mention（论文/专利/基金号等成果线索）
        pool = [e for e in fresh if role_of(e) == "prior_work"
                and e.get("type") == "pub_mention"]
    elif _prefix_hit(element, "技术路线") or _prefix_hit(element, "研究内容"):
        # 方法类术语与数字
        pool = [e for e in fresh if e.get("type") in ("term", "abbrev", "number")]
    elif _prefix_hit(element, "科学问题"):
        pool = [e for e in fresh if _has_gap(e.get("context", ""))]
    elif _prefix_hit(element, "研究目标"):
        pool = [e for e in fresh if e.get("type") == "number"]
    elif _prefix_hit(element, "创新点"):
        pool = [e for e in fresh if e.get("type") in ("citation", "pub_mention")]
    if not pool:
        pool = fresh  # 兜底：任何未引用条目
    # 去重保序，限量
    seen, out = set(), []
    for e in pool:
        fid = e.get("fid")
        if fid and fid not in seen:
            seen.add(fid)
            out.append(e)
        if len(out) >= MAX_CANDIDATES:
            break
    return out


def format_candidates(cands):
    parts = []
    for e in cands:
        disp = str(e.get("value", ""))
        if len(disp) > 24:
            disp = disp[:24] + "…"
        unit = e.get("unit") or ""
        pid = (e.get("source") or {}).get("pid", "?")
        parts.append(f"{e['fid']} {e.get('type','?')} {disp}{unit}（{pid}）")
    return "可考虑补入：" + "；".join(parts) + "。" if parts else ""


def missing_subpoints(element, text):
    """缺失子点提示（立项依据查 现状/瓶颈/我们 三环，其余给静态判据句）。"""
    hints = []
    for key, rules in SUBPOINT_RULES.items():
        if _prefix_hit(element, key):
            missing = [name for name, words in rules
                       if not any(w in text for w in words)]
            if missing:
                hints.append(f"缺失子点提示：{key}缺「{'」「'.join(missing)}」环。")
            return hints
    for key, hint in STATIC_HINTS.items():
        if _prefix_hit(element, key):
            hints.append(f"子点判据：{hint}。")
            return hints
    return hints


def build_suggestion(element, chars, threshold, density_low, entries, roles,
                     used_fids, text):
    """对 thin 或 density=low 要素生成可执行扩展指令。"""
    parts = []
    if chars < threshold:
        parts.append(f"当前 {chars} 字 < 阈值 {threshold} 字，请扩写至达标厚度；")
    if density_low:
        parts.append(f"当前仅引用 {len(used_fids)} 个不同 FID < {DENSITY_MIN_FIDS} 个，"
                     f"请补入台账事实并逐处标〔F〕；")
    cand = format_candidates(candidate_pool(element, entries, roles, used_fids))
    if cand:
        parts.append(cand)
    parts.extend(missing_subpoints(element, text))
    return "".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    work = args.work
    out = gu.env_output_dir(args.out) if args.out else None
    if out:
        gu.ensure_dir(out)

    draft = gu.read_json(os.path.join(work, "draft.json"), None)
    inspection = gu.read_json(os.path.join(work, "inspection.json"), {}) or {}
    if not isinstance(draft, dict) or "paragraphs" not in draft:
        gu.record_exception(work, STAGE, "draft.json", "缺失或结构不符",
                            "写空 element_map/findings")
        gu.write_json(os.path.join(work, "element_map.json"), {})
        gu.write_json(os.path.join(work, "element_findings.json"), [])
        return 0

    required = inspection.get("required_elements") or list(gu.DEFAULT_ELEMENTS)
    thickness_override = inspection.get("thickness") or {}

    # v2：候选 FID 需要台账与材料角色
    ledger = gu.read_json(os.path.join(work, "fact_ledger.json"), {}) or {}
    entries = ledger.get("entries") or []
    materials = gu.read_json(os.path.join(work, "materials.json"), {}) or {}
    roles = {f.get("file_id"): f.get("role_guess", "")
             for f in materials.get("files", []) if isinstance(f, dict)}

    element_map = {}
    element_text = {}
    for e in required:
        element_map[e] = {"dpids": [], "fids": [], "chars": 0, "status": "missing",
                          "density_status": "na"}
        element_text[e] = []

    for p in draft["paragraphs"]:
        key = element_key(p.get("element", ""), required)
        if key not in element_map:
            element_map[key] = {"dpids": [], "fids": [], "chars": 0,
                                "status": "missing", "density_status": "na"}
            element_text[key] = []
        text_clean = strip_markers(p.get("text", ""))
        element_map[key]["dpids"].append(p["dpid"])
        element_map[key]["fids"].extend(FID_RE.findall(p.get("text", "")))
        element_map[key]["chars"] += len(re.sub(r"\s", "", text_clean))
        element_text[key].append(p.get("text", ""))

    findings = []
    for e, m in element_map.items():
        m["fids"] = sorted(set(m["fids"]))
        text = "\n".join(element_text.get(e, []))
        if not m["dpids"]:
            m["status"] = "missing"
            findings.append({
                "element": e, "severity": "high", "kind": "element_missing",
                "chars": 0, "dpids": [],
                "msg": f"要素「{e}」缺失：无对应段落"})
            continue
        threshold = thickness_v2(e, thickness_override)
        thin = m["chars"] < threshold
        m["status"] = "thin" if thin else "ok"
        # v2 证据密度：事实类要素需 ≥3 个不同 FID
        density_low = False
        if is_fact_element(e):
            m["density_status"] = "ok" if len(m["fids"]) >= DENSITY_MIN_FIDS else "low"
            density_low = m["density_status"] == "low"
        if thin:
            findings.append({
                "element": e, "severity": "medium", "kind": "element_thin",
                "chars": m["chars"], "dpids": m["dpids"],
                "fid_count": len(m["fids"]),
                "msg": f"要素「{e}」过薄：{m['chars']} 字 < 阈值 {threshold} 字",
                "suggestion": build_suggestion(e, m["chars"], threshold,
                                               density_low, entries, roles,
                                               set(m["fids"]), text)})
        if density_low:
            findings.append({
                "element": e, "severity": "medium", "kind": "density_low",
                "chars": m["chars"], "dpids": m["dpids"],
                "fid_count": len(m["fids"]),
                "msg": f"要素「{e}」证据密度不足：{len(m['fids'])} 个不同 FID "
                       f"< {DENSITY_MIN_FIDS} 个",
                "suggestion": build_suggestion(e, m["chars"], threshold,
                                               True, entries, roles,
                                               set(m["fids"]), text)})

    gu.write_json(os.path.join(work, "element_map.json"), element_map)
    gu.write_json(os.path.join(work, "element_findings.json"), findings)

    # 交付物 element_mapping.md（七要素 × 章节 × 段落数/字数 × 证据数 × 证据密度
    # × 状态 + 三级对应清单）
    if out:
        lines = ["# 要素对照说明（element_mapping）", "",
                 "| 要素 | 段落数 | 字数 | 证据数(FID) | 证据密度 | 状态 |", "",
                 "|---|---|---|---|---|---|"]
        ok = sum(1 for m in element_map.values() if m["status"] == "ok")
        for e, m in element_map.items():
            lines.append(f"| {e} | {len(m['dpids'])} | {m['chars']} | "
                         f"{len(m['fids'])} | {m['density_status']} | {m['status']} |")
        lines += ["", f"覆盖：{ok}/{len(element_map)} 个要素达标。", "",
                  "## 三级对应清单（段落 → 要素 → 证据 FID）", ""]
        for p in draft["paragraphs"]:
            fids = sorted(set(FID_RE.findall(p.get("text", ""))))
            lines.append(f"- {p['dpid']} → {p.get('element','?')} → "
                         f"{' '.join('〔'+f+'〕' for f in fids) if fids else '（无 FID）'}")
        with open(os.path.join(out, "element_mapping.md"), "w",
                  encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    covered = sum(1 for m in element_map.values() if m["dpids"])
    thin_n = sum(1 for m in element_map.values() if m["status"] == "thin")
    low_n = sum(1 for m in element_map.values()
                if m.get("density_status") == "low")
    print(f"[elements_check] covered={covered}/{len(element_map)} "
          f"thin={thin_n} density_low={low_n} findings={len(findings)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[elements_check] ERROR: {e}")
        raise SystemExit(1)
