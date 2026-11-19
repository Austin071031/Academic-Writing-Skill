# 最小端到端示例（标注：合成示例，非真实论文）

> 本示例基于 `_test/input/` 合成案例：两条工单意见（R1 补充绪论两步烧结区别、
> R2 改写 EIS 测试条件）。所有文本均为合成。

## 1. 输入

`/input/organizer-edit-workorder.json`：

```json
{"rounds": [{"round": 1, "opinions": [
  {"id": "R1", "target": "ch1_intro.md", "type": "补充",
   "content": "绪论应补充说明两步烧结法与已有的一步烧结的区别"},
  {"id": "R2", "target": "ch2_method.md", "type": "改写",
   "content": "EIS 测试条件需写明频率范围与偏置电压"}]}]}
```

章节：`chapters/ch1_intro.md`（第1章 绪论，3 段）、`chapters/ch2_method.md`（第2章 实验方法，3 段）。

## 2. 命令序列与关键输出

```bash
python3 scripts/init_result.py --case /input/case.json --out /app/output
python3 scripts/inspect_case.py --input-dir /input --work /app/work
# → workorder_files=1, manuscript_candidates=2
python3 scripts/parse_chapters.py /input/chapters/ch1_intro.md /input/chapters/ch2_method.md --work /app/work
python3 scripts/revision_engine.py parse --workorder /input/organizer-edit-workorder.json --work /app/work
# → R1 [补充] target=ch1_intro.md / R2 [改写] target=ch2_method.md
python3 scripts/revision_engine.py locate --work /app/work
# → R1: C01-S001-P003（"本研究提出两步烧结法…"）; R2: C02-S001-P002（"采用交流阻抗谱…"）; 冲突 0
```

Agent 写 `work/agent_edits.json`（节选）：

```json
[{"rid": "R1", "action": "edit", "target_pid": "C01-S001-P003", "mode": "replace",
  "new_text": "本研究提出两步烧结法，目标是将电导率提升至 5.0 mS/cm 以上。与已有的一步烧结法……不同，两步烧结法先在较高温度快速致密化、再在较低温度长时间保温……",
  "reason": "落实 R1：保留原句首句，补充与一步烧结的区别"},
 {"rid": "R2", "action": "edit", "target_pid": "C02-S001-P002", "mode": "replace",
  "new_text": "采用交流阻抗谱（EIS）测量离子电导率，阻塞电极为不锈钢；测试频率范围为 1 MHz–0.1 Hz，……偏置电压 0 V（开路电位）。",
  "reason": "落实 R2：写明频率范围与偏置电压，参数取自 materials/facts.md"}]
```

```bash
python3 scripts/revision_engine.py apply --work /app/work
# → 已落实 2/2；work/original/ 备份 2 件；work/revised/ 修订 2 件
python3 scripts/revision_engine.py version --work /app/work
# → version_report.json：第 1 轮 n_opinions=2 n_done=2
```

## 3. 台账记录（revision_ledger.json 节选）

```json
{"rid": "R1", "status": "已落实", "evidence_pid": "C01-S001-P003",
 "before": "本研究提出两步烧结法，目标是将电导率提升至 5.0 mS/cm 以上。",
 "after":  "本研究提出两步烧结法，目标是将电导率提升至 5.0 mS/cm 以上。与已有的一步烧结法……"}
```

## 4. diff 报告（diff_report.md 节选）

```diff
-本研究提出两步烧结法，目标是将电导率提升至 5.0 mS/cm 以上。
+本研究提出两步烧结法，目标是将电导率提升至 5.0 mS/cm 以上。与已有的一步烧结法（单次高温烧结，晶粒易异常长大）不同，……
```

## 5. 交付与闸门

`assemble_result.py --status success` → `validate_output.py` 输出 `PASS` →
`render_previews.py` 生成 preview.html。`/app/output` 含：
`ch1_intro_revised.md`、`ch2_method_revised.md`、`revision_ledger.md`、`diff_report.md`、`result.json`。

负例行为（同引擎、合成负例工单）：target 指向 `ch9_missing.md` → 台账
`无法落实 / 目标文件缺失`；补充+删除两条意见同落 `C02-S001-P002` → locate 检出
`conflict`，Agent 裁决为一 defer 一 skip。
