#!/usr/bin/env python3
"""batch_planner.py — 批量翻译计划与进度追踪（v2.0.0 完整率保障方向）。

把待译句段按批次切分为现成可填的批文件，Agent 逐批翻译、追加译文、
脚本实时报告进度与剩余预算策略，保证在模型请求预算内达到 100% 覆盖。

子命令：
  plan     生成 work/batches/batch_NN.md（每批 ≤N 句段，含填写模板与约束提示）
           与 work/progress.json（总句段数、批次表、完成状态）
  status   依据 work/translations*.jsonl 更新 progress.json，
           打印：已完成/剩余/下一批文件/预算建议
用法:
  python3 batch_planner.py plan   --work /app/work [--batch-size 15]
  python3 batch_planner.py status --work /app/work [--used-requests 30]
"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trans_utils as tu

def cmd_plan(work, batch_size):
    segdata = tu.load_json(os.path.join(work, "segments.json"))
    if not segdata:
        print("[batch_planner][FATAL] 缺少 segments.json", file=sys.stderr)
        return 1
    insp = tu.load_json(os.path.join(work, "inspection.json"), {}) or {}
    target = (insp.get("translation_task") or {}).get("target_lang") or "zh"
    segs = [s for s in segdata["segments"] if s["needs_translation"]]
    bdir = os.path.join(work, "batches")
    os.makedirs(bdir, exist_ok=True)

    batches = []
    for bi in range(0, len(segs), batch_size):
        chunk = segs[bi:bi + batch_size]
        bn = f"batch_{bi // batch_size + 1:02d}"
        lines = [
            f"# {bn}（{len(chunk)} 句段）— 翻译后直接追加到 work/translations.jsonl",
            "",
            f"> 目标语：{target}。逐行翻译，每行译文写成一行 JSON：",
            '> {"seg_id":"<段ID>","translation":"<译文>"}',
            "> 〔保留:…〕内片段逐字符保留；数字/单位/引用/公式不得改动。",
            "",
        ]
        for s in chunk:
            prot = "、".join(p["text"] for p in s["protected"][:8])
            hint = f"  〔保留: {prot}〕" if prot else ""
            lines.append(f"{s['seg_id']}\t{s['source']}{hint}")
        fp = os.path.join(bdir, bn + ".md")
        with open(fp, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        batches.append({"batch": bn, "file": f"batches/{bn}.md",
                        "seg_ids": [s["seg_id"] for s in chunk],
                        "n": len(chunk), "done": 0})

    progress = {"total": len(segs), "done": 0, "batch_size": batch_size,
                "batches": batches,
                "policy": "严格按批次顺序翻译；每批翻译完立即追加 translations.jsonl "
                          "并运行 batch_planner.py status 查看下一批与预算建议。"}
    tu.save_json(os.path.join(work, "progress.json"), progress)
    print(f"[batch_planner plan] 待译={len(segs)} 批次={len(batches)} "
          f"每批≤{batch_size} → work/batches/")
    return 0

def cmd_status(work, used_requests):
    progress = tu.load_json(os.path.join(work, "progress.json"))
    if not progress:
        print("[batch_planner][FATAL] 缺少 progress.json，先运行 plan", file=sys.stderr)
        return 1
    merged, _ = tu.load_translations(work)
    done = 0
    nxt = None
    for b in progress["batches"]:
        b["done"] = sum(1 for sid in b["seg_ids"] if sid in merged)
        done += b["done"]
        if nxt is None and b["done"] < b["n"]:
            nxt = b
    progress["done"] = done
    total = progress["total"]
    tu.save_json(os.path.join(work, "progress.json"), progress)

    remaining = total - done
    pct = done / max(total, 1)
    print(f"[batch_planner status] 完成={done}/{total}（{pct:.0%}）剩余={remaining}")
    if nxt:
        print(f"[batch_planner status] 下一批: work/{nxt['file']} "
              f"（{nxt['n'] - nxt['done']} 句段待译）")
    else:
        print("[batch_planner status] 全部句段已译，进入组装与机检阶段")
    if used_requests:
        left = 64 - used_requests
        print(f"[batch_planner status] 已用请求≈{used_requests}，剩余≈{left}")
        if remaining and left > 0:
            # 经验：每批 1 次写文件 + 少量组装；剩余批次是否够用
            batches_left = sum(1 for b in progress["batches"] if b["done"] < b["n"])
            reserve = 8  # 组装/机检/报告/契约预留
            if left - reserve < batches_left:
                print("[batch_planner status][预算告警] 剩余请求不足以从容译完全部批次："
                      "请合并批次（一次写多批译文）、每批句段翻倍，"
                      "并优先保证正文句段全覆盖；收尾预留 8 次请求。", file=sys.stderr)
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "status"])
    ap.add_argument("--work", default="/app/work")
    ap.add_argument("--batch-size", type=int, default=15)
    ap.add_argument("--used-requests", type=int, default=0)
    args = ap.parse_args()
    if args.cmd == "plan":
        return cmd_plan(args.work, args.batch_size)
    return cmd_status(args.work, args.used_requests)

if __name__ == "__main__":
    sys.exit(main())
