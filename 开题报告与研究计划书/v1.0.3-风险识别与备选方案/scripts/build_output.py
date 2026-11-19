#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开题报告产物构建脚本：可编辑稿件 → docx → 真实 PDF 渲染 → 首页 PNG 预览 → result.json。

用法:
  python3 build_output.py --work /app/work --out /app/output --case /input/case.json

行为约定（诚实性优先）:
- work 目录需含 proposal.md（可编辑主稿件）与 result_content.json（output_contract 字段值，由撰写 Agent 填写）。
- 若 case.json 含 output_contract，其全部键必须出现在最终 result.json 中；缺失键以 null 填充并记入 uncertainty。
- pandoc / libreoffice / pdftoppm 任一不可用或渲染失败时，status 降级为 partial 并记录原因，绝不伪造预览文件。
- 若 work/milestones.json 存在（[{"id","label","start_month","end_month"}...]），渲染甘特图 gantt.png。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys


def run(cmd, timeout=180):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def render(proposal_md, work, out, notes):
    artifacts = []
    name = os.path.splitext(os.path.basename(proposal_md))[0]
    docx = os.path.join(out, name + ".docx")
    r = run(["pandoc", proposal_md, "-o", docx, "--standalone"])
    if r.returncode == 0 and os.path.isfile(docx):
        artifacts.append(docx)
    else:
        notes.append("pandoc 渲染 docx 失败: " + (r.stderr or "")[:300])
        docx = None
    pdf = None
    if docx and shutil.which("soffice"):
        r = run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", out, docx], timeout=240)
        cand = os.path.join(out, name + ".pdf")
        if r.returncode == 0 and os.path.isfile(cand):
            pdf = cand
            artifacts.append(pdf)
        else:
            notes.append("libreoffice 渲染 pdf 失败: " + (r.stderr or r.stdout or "")[:300])
    elif docx:
        notes.append("环境中无 soffice，跳过 pdf 渲染")
    if pdf and shutil.which("pdftoppm"):
        r = run(["pdftoppm", "-png", "-f", "1", "-singlefile", pdf, os.path.join(out, name + "_preview")])
        png = os.path.join(out, name + "_preview.png")
        if r.returncode == 0 and os.path.isfile(png):
            artifacts.append(png)
        else:
            notes.append("pdftoppm 生成首页预览失败: " + (r.stderr or "")[:300])
    elif pdf:
        notes.append("环境中无 pdftoppm，跳过 png 预览")
    return artifacts


def render_gantt(work, out, notes):
    src = os.path.join(work, "milestones.json")
    if not os.path.isfile(src):
        return None
    try:
        items = json.load(open(src, encoding="utf-8"))
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
        # 中文字体尽力探测；找不到则回退英文标签不报错
        zh = None
        for fp in font_manager.findSystemFonts():
            if any(k in os.path.basename(fp) for k in ("NotoSansCJK", "Noto Serif CJK", "wqy", "WenQuanYi", "SimHei")):
                zh = font_manager.FontProperties(fname=fp)
                break
        fig, ax = plt.subplots(figsize=(9, 0.6 * max(3, len(items)) + 1.5))
        for i, it in enumerate(items):
            s, e = float(it["start_month"]), float(it["end_month"])
            lbl = it["label"]
            ax.barh(i, e - s, left=s, height=0.55, color="#3a6ea5")
            ax.text(e + 0.15, i, lbl, va="center", fontproperties=zh)
        ax.set_yticks([])
        ax.invert_yaxis()
        ax.set_xlabel("month", fontproperties=zh)
        ax.set_title("Milestones", fontproperties=zh)
        ax.grid(axis="x", alpha=0.3)
        path = os.path.join(out, "gantt.png")
        fig.tight_layout()
        fig.savefig(path, dpi=150)
        plt.close(fig)
        return path
    except Exception as e:  # noqa: BLE001
        notes.append(f"甘特图渲染失败（不影响主产物）: {e}")
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--out", default="/app/output")
    ap.add_argument("--case", default="/input/case.json")
    ap.add_argument("--status", default=None, help="success|partial，缺省时按缺失项自动判定")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    notes, artifacts = [], []

    proposal = os.path.join(args.work, "proposal.md")
    if not os.path.isfile(proposal):
        print("[build_output] 未找到 /app/work/proposal.md，无法构建主产物", file=sys.stderr)
        sys.exit(2)
    md_copy = os.path.join(args.out, os.path.basename(proposal))
    if os.path.abspath(md_copy) != os.path.abspath(proposal):
        shutil.copyfile(proposal, md_copy)
    artifacts.append(md_copy)
    artifacts += render(proposal, args.work, args.out, notes)
    g = render_gantt(args.work, args.out, notes)
    if g:
        artifacts.append(g)

    case_id, contract = None, {}
    if os.path.isfile(args.case):
        try:
            case = json.load(open(args.case, encoding="utf-8"))
            case_id = case.get("case_id") or case.get("id")
            contract = case.get("output_contract") or {}
        except Exception as e:  # noqa: BLE001
            notes.append(f"case.json 解析失败: {e}")
    else:
        notes.append("未找到 /input/case.json，result.json 中将缺少 case 侧契约信息")

    content = {}
    rc = os.path.join(args.work, "result_content.json")
    if os.path.isfile(rc):
        content = json.load(open(rc, encoding="utf-8"))
    elif contract:
        notes.append("未提供 result_content.json，契约字段以 null 填充")

    uncertainty = content.pop("uncertainty", []) or []
    change_log = content.pop("change_log", []) or []
    sources = content.pop("sources", []) or []

    missing_keys = [k for k in contract if k not in content]
    if missing_keys:
        uncertainty.append("output_contract 中以下字段未能填写，暂以 null 占位: " + ", ".join(missing_keys))
    result = {"case_id": case_id, "status": args.status or "success", **{k: content.get(k) for k in contract},
              "artifacts": [os.path.relpath(a, args.out) for a in artifacts],
              "sources": sources, "uncertainty": uncertainty, "change_log": change_log,
              "build_notes": notes}
    if missing_keys or notes or (args.status == "partial"):
        result["status"] = "partial" if args.status != "success" else "success"

    with open(os.path.join(args.out, "result.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[build_output] 完成: result.json, artifacts={len(artifacts)}, notes={len(notes)}")
    sys.exit(0)


if __name__ == "__main__":
    main()
