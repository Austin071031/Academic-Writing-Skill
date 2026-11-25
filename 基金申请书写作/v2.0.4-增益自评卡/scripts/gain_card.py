#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gain_card.py --work W --out O  （v2.0.4 唯一新增脚本）

增益自评卡：汇总 work/ 下各 findings 文件（findings_draft/source_audit/
element_findings/findings）、change_log.json 与 stats.json，生成 O/gain_card.md：
  ① 反事实缺陷表——若无本技能机检，以下缺陷将直接留在交付稿中（按 kind 聚合，
    每类附 1 个真实定位示例；0 处类别如实标注，不编造）；
  ② 修订闭环表——change_log 按 op 聚合 + 各 findings 文件当前 high/medium/low 统计
    + 历史快照（findings_round1.json 类）如实说明；
  ③ 机械劳动清单——脚本替代的核对项与量级（数字实读自 stats.json 与各 json）。

只读不写 work/（除读取）；幂等：同输入生成同内容。stdlib only。
"""
import argparse
import glob
import os
import sys
from collections import Counter, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grant_utils as gu

STAGE = "gain_card"

FINDINGS_FILES = ["findings_draft.json", "source_audit.json",
                  "element_findings.json", "findings.json"]

# 机检全程开启的缺陷类别清单（kind → 中文名）；findings 中出现的其他 kind 自动追加
CORE_KINDS = [
    ("off_source_number", "材料外数字"),
    ("off_source_citation", "材料外引用"),
    ("banned_modifier", "不可核验修饰词（创新点节，high 级）"),
    ("hype_word", "不可核验修饰词（全稿扫描，low 提示）"),
    ("marker_missing_ledger", "证据标记指向不存在的台账条目"),
    ("missing_section", "创新点节缺失"),
    ("no_baseline_anchor", "创新点无对比锚点"),
    ("no_difference_statement", "创新点无差异表述"),
    ("three_dim_incomplete", "创新点三维覆盖缺环（新在哪/难在哪/凭什么成）"),
    ("element_missing", "七要素缺失"),
    ("element_thin", "要素厚度不达标"),
]

SEVERITIES = ["high", "medium", "low"]


def load_findings(work):
    """读各 findings 文件 → {fname: [finding,...]}；兼容 list 与 {findings:[...]}。"""
    per_file = OrderedDict()
    for name in FINDINGS_FILES:
        data = gu.read_json(os.path.join(work, name), None)
        items = []
        if isinstance(data, list):
            items = [x for x in data if isinstance(x, dict)]
        elif isinstance(data, dict) and isinstance(data.get("findings"), list):
            items = [x for x in data["findings"] if isinstance(x, dict)]
        per_file[name] = items
    return per_file


def load_change_log(work):
    """change_log.json → list；兼容 list 与 {entries/changes:[...]}；缺文件返回 None。"""
    path = os.path.join(work, "change_log.json")
    if not os.path.isfile(path):
        return None
    data = gu.read_json(path, None)
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("entries", "changes", "items"):
            if isinstance(data.get(key), list):
                return [x for x in data[key] if isinstance(x, dict)]
    return []


def is_active(x):
    """人工复核标记「已驳回」的误报不计入反事实表。"""
    return str(x.get("status", "")).strip() not in ("已驳回", "rejected", "驳回")


def loc_of(x):
    return x.get("dpid") or x.get("element") or x.get("location") or "-"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    work, out = args.work, args.out
    gu.ensure_dir(out)

    per_file = load_findings(work)
    change_log = load_change_log(work)
    stats = gu.read_json(os.path.join(work, "stats.json"), {}) or {}
    materials = gu.read_json(os.path.join(work, "materials.json"), {}) or {}
    ledger = gu.read_json(os.path.join(work, "fact_ledger.json"), {}) or {}
    draft = gu.read_json(os.path.join(work, "draft.json"), {}) or {}

    all_findings = []
    for name, items in per_file.items():
        for x in items:
            x = dict(x)
            x.setdefault("source_file", name)
            all_findings.append(x)
    active = [x for x in all_findings if is_active(x)]
    rejected = len(all_findings) - len(active)

    # ---- ① 反事实缺陷表
    by_kind = {}
    for x in active:
        by_kind.setdefault(x.get("kind", "unknown"), []).append(x)
    ordered_kinds = list(CORE_KINDS)
    known = {k for k, _ in CORE_KINDS}
    for k in by_kind:
        if k not in known:
            ordered_kinds.append((k, f"其他机检发现（{k}）"))

    L = ["# 增益自评卡（gain_card）", "",
         "> 本卡由 gain_card.py 自动汇总生成；数据全部实读自 work/ 下机检产物"
         "（findings/change_log/stats），未人工填写、不编造。",
         "> 用途：显式回答「基础 Agent（无本技能）会错什么、本技能挡住了什么、"
         "脚本替代了多少人工核对」。", "",
         "## 一、反事实缺陷表", "",
         "若无本技能机检，以下缺陷将直接留在交付稿中（按 findings kind 聚合计数；"
         "每类附 1 个真实定位示例）：", "",
         "| 缺陷类型 | 机检 kind | 处数 | 真实定位示例 |", "|---|---|---|---|"]
    total_defects = 0
    for kind, label in ordered_kinds:
        items = by_kind.get(kind, [])
        n = len(items)
        total_defects += n
        if n == 0:
            L.append(f"| {label} | `{kind}` | 0 处（本案例未出现，机检仍全程开启） | — |")
        else:
            ex = items[0]
            msg = str(ex.get("msg", ""))[:80]
            L.append(f"| {label} | `{kind}` | {n} 处 | {loc_of(ex)}：{msg} |")
    L.append("")
    L.append(f"- 合计：机检发现有效缺陷 **{total_defects} 处**"
             f"（high {sum(1 for x in active if x.get('severity')=='high')} / "
             f"medium {sum(1 for x in active if x.get('severity')=='medium')} / "
             f"low {sum(1 for x in active if x.get('severity')=='low')}）。")
    if rejected:
        L.append(f"- 另有 {rejected} 条 findings 经人工复核标记为「已驳回」（误报），"
                 "不计入上表。")
    L.append("")

    # ---- ② 修订闭环表
    L += ["## 二、修订闭环表", ""]
    if change_log is None or len(change_log) == 0:
        L.append("- 修订记录：本次无修订记录（work/change_log.json 不存在或为空）。")
    else:
        op_counter = Counter(str(x.get("op", "unknown")) for x in change_log)
        L.append(f"- 修订记录：change_log.json 共 {len(change_log)} 条，按 op 聚合：")
        L += ["", "| 操作 op | 次数 |", "|---|---|"]
        for op, c in op_counter.most_common():
            L.append(f"| {op} | {c} |")
        L.append("")
    L += ["", "各 findings 文件当前分级统计：", "",
          "| findings 文件 | high | medium | low | 其他 | 合计 |", "|---|---|---|---|---|---|"]
    for name, items in per_file.items():
        sev = Counter(x.get("severity", "other") for x in items)
        other = sum(c for s, c in sev.items() if s not in SEVERITIES)
        L.append(f"| {name} | {sev.get('high',0)} | {sev.get('medium',0)} | "
                 f"{sev.get('low',0)} | {other} | {len(items)} |")
    L.append("")
    snapshots = sorted(glob.glob(os.path.join(work, "findings_round*.json")) +
                       glob.glob(os.path.join(work, "*round1*.json")))
    if snapshots:
        L.append("- 历史快照：")
        for sp in snapshots:
            data = gu.read_json(sp, None)
            items = data if isinstance(data, list) else (data or {}).get("findings", [])
            sev = Counter(x.get("severity", "?") for x in items if isinstance(x, dict))
            L.append(f"  - {os.path.basename(sp)}：{len(items)} 条（{dict(sev)}）")
        L.append("  与上方当前统计对照即为修订前后对比。")
    else:
        if change_log:
            L.append("- 历史快照：存在修订记录，但未检测到 findings_round1.json 类首轮快照"
                     "（本版工作流不要求产生快照），无法逐类给出修订前后计数对比；"
                     "当前 findings 统计见上表（如实说明）。")
        else:
            L.append("- 历史快照：无修订记录且无首轮快照——首轮即清零/未做第二轮修订"
                     "（如实说明）。")
    L.append("")

    # ---- ③ 机械劳动清单
    mstats = materials.get("stats") or {}
    n_files = mstats.get("files", stats.get("material_files", 0))
    n_paras = mstats.get("paragraphs", 0)
    n_ledger = len(ledger.get("entries", []) or []) or stats.get("ledger_entries", 0)
    n_draft = len(draft.get("paragraphs", []) or []) or stats.get("paragraphs", 0)
    n_checks = len(ordered_kinds)
    n_findings = len(all_findings)
    L += ["## 三、机械劳动清单（脚本替代的人工核对项）", "",
          "| 脚本 | 一句话职责 | 替代的人工核对项（量级实读） |", "|---|---|---|",
          f"| parse_materials.py | 抽取全部材料文本并分段编号 | 人工逐段通读并编号 "
          f"{n_files} 个材料文件 / {n_paras} 段 |",
          f"| fact_ledger.py | 数字/引用/成果/术语台账去重编号 | 人工摘抄并溯源 "
          f"{n_ledger} 条事实 |",
          f"| draft_builder.py | 组装章节稿并校验证据标记存在性 | 人工逐段核对 "
          f"{n_draft} 段草稿的〔F〕标记是否存在于台账 |",
          f"| source_audit.py | 材料外数字/引用与修饰词机检 | 人工把每段的每个数字/引用"
          f"逐值回查原始材料（本案例审计出 {len(per_file.get('source_audit.json', []))} 条） |",
          f"| elements_check.py | 七要素覆盖与厚度检查 | 人工逐要素数段落、数字数、"
          f"对阈值（7 要素） |",
          f"| innovation_engine.py | 创新点锚点机选 + 五类规则审计 | 人工逐条比对创新点的"
          f"锚点/差异表述/三维覆盖 |",
          f"| gain_card.py | 本卡：聚合并对照全部机检产物 | 人工跨 "
          f"{len(FINDINGS_FILES)} 个 findings 文件汇总 {n_findings} 条发现并计数分类 |",
          "",
          f"> 机检共覆盖 {n_checks} 类缺陷检查，全程开启；stats.json 记录："
          f"草稿 {stats.get('paragraphs', n_draft)} 段 / 台账 {stats.get('ledger_entries', n_ledger)} 条 / "
          f"材料 {stats.get('material_files', n_files)} 个文件。", ""]

    out_path = os.path.join(out, "gain_card.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"[gain_card] defects={total_defects} kinds={len(by_kind)} "
          f"change_log={'none' if not change_log else len(change_log)} → {out_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as e:
        print(f"[gain_card] ERROR: {e}")
        raise SystemExit(1)
