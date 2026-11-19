# 标注示例（合成稿件，仅演示标注格式，非正式案例结果）

## 输入片段（合成）

```
## 1 引言
LIBs 已广泛用于电动汽车。本文比较两种固态电解质。
## 2 结果
图1 给出离子电导率。LLZO 为 0.52 mS/cm，LATP 为 1.10 mS/cm。
样品采用固相烧结法制备，步骤如下：按化学计量比球磨 12 h，100 MPa 压制后 1150°C 烧结 12 h。
测试采用阻塞电极，频率 0.1 Hz 至 1 MHz，振幅 10 mV。
## 3 方法
详见附件。
## 4 讨论
如前所述，界面阻抗是主要障碍。
## 参考文献
[1] Goodenough J B. Energy Environ. Sci., 2013.
```

## 标注产出（示例）

### 顺序倒置（SS-A）

```json
{
  "id": "D2-01",
  "dimension": "section_structure",
  "type": "章节顺序与论证顺序倒置",
  "location": {"section": "3 方法", "para_id": null, "sentence_id": null},
  "quote": "3 方法",
  "evidence": "章节角色序列表出现逆序对：method 先于 results（规范序 摘要→…→方法→实验→结果→…），读者先见结果后见方法。",
  "action": {"op": "move", "instruction": "将「3 方法」移至「2 结果」之前，恢复 引言→方法→结果 的论证顺序；若为期刊模板要求请在报告中说明。"},
  "severity": "high", "confidence": 0.7, "status": "待作者复核"
}
```

### 信息过早释放（SS-I，缩写首现未定义）

```json
{
  "id": "D2-04",
  "dimension": "section_structure",
  "type": "缩写首现未定义",
  "location": {"section": "1 引言", "para_id": "P001", "sentence_id": "P001-s1"},
  "quote": "LIBs 已广泛用于电动汽车。本文比较两种固态电解质。",
  "evidence": "缩写 LIBs 于 P001-s1 首次出现，该句及相邻句均无“全称（LIBs）”或“LIBs（全称）”定义模式；首次出现的读者无法解码。",
  "action": {"op": "add", "instruction": "在 LIBs 首次出现处补全称定义（“全称（LIBs）”格式），后文直接使用缩写。"},
  "severity": "low", "confidence": 0.6, "status": "待作者复核"
}
```

### 该拆分/后移（SS-C + SS-H）

```json
{
  "id": "D2-06",
  "dimension": "section_structure",
  "type": "方法性描述混入结果章（应后移）",
  "location": {"section": "2 结果", "para_id": "P004", "sentence_id": "P004-s2"},
  "quote": "样品采用固相烧结法制备，步骤如下：按化学计量比球磨 12 h……",
  "evidence": "结果/结论章段落 P004 含 2 句方法性描述（采用/步骤/配置为等提示词），打断“结果先行”的叙事节奏，且与方法章职责重复。",
  "action": {"op": "move", "instruction": "将该段方法性描述移至方法章（或附录），结果章只保留指向性一句（“采用 X 法，详见第 Y 节”）。"},
  "severity": "medium", "confidence": 0.6, "status": "待作者复核"
}
```

## 作者复核流转

- **采纳**：按 action 执行编辑，在 edit_plan.json 将 review_status 改为"采纳-已执行"。
- **部分采纳**：方法章保留原位（模板要求），仅把结果章中方法段落后移；对应逆序对条目驳回并备注"模板所致"。
- **驳回**：若"方法"实为"3.1 测试方法"小节、全文另有完整方法章（角色误归类），驳回并在 uncertainty 记录"归类失败"。
