# 测试文本（标注：全部为合成文本，仅用于功能测试）

## 1. 正例工单（`_test/input/organizer-edit-workorder.json`）

```json
{"rounds": [{"round": 1, "opinions": [
  {"id": "R1", "target": "ch1_intro.md", "type": "补充",
   "content": "绪论应补充说明两步烧结法与已有的一步烧结的区别"},
  {"id": "R2", "target": "ch2_method.md", "type": "改写",
   "content": "EIS 测试条件需写明频率范围与偏置电压"}]}]}
```

预期：R1 定位 `C01-S001-P003`，R2 定位 `C02-S001-P002`，apply 后均"已落实"。

## 2. 负例工单 A：目标文件缺失

```json
{"rounds": [{"round": 2, "opinions": [
  {"id": "R3", "target": "ch9_missing.md", "type": "补充", "content": "补充循环寿命测试数据"}]}]}
```

预期：locate 记 `目标文件缺失`；apply（action=edit）判 `无法落实 / 目标文件缺失`。

## 3. 负例工单 B：冲突意见

```json
{"rounds": [{"round": 2, "opinions": [
  {"id": "R4", "target": "ch2_method.md", "type": "补充", "content": "EIS 测试条件需补充写明频率范围"},
  {"id": "R5", "target": "ch2_method.md", "type": "删除", "content": "删除 EIS 测试条件中频率范围的描述"}]}]}
```

预期：两条同落 `C02-S001-P002` → locate 输出 conflicts 1 组；Agent 裁决一 defer 一 skip。

## 4. 负例工单 C：格式异常 / 键名变体

```json
{"items": [{"no": 7, "file": "ch1_intro.md", "kind": "修改",
            "opinion": "绪论第二段关于界面稳定性的表述改为更谨慎的定性说法"}]}
```

预期：parse 兼容 `items/no/file/kind/opinion` 键名，rid="7"，类型=改写。

## 5. 负例场景 D：无工单

删除工单后运行 parse：从 task.md 抽取含 修改/补充/删除/改写/调整/统一/检查 动词的
意见行，round=0 且标注"非组织方工单，需人工确认"。

## 6. 章节文本（合成，见 `_test/input/chapters/`）

- ch1_intro.md：第1章 绪论，3 段（SSE 背景 / 已有研究电导率 3.2 mS/cm / 提出两步烧结法）。
- ch2_method.md：第2章 实验方法，3 段（两步烧结工艺参数 / EIS 测量 / XRD+SEM）。

测试命令序列见 examples/minimal_example.md 与 CHANGELOG.md 的测试记录。
