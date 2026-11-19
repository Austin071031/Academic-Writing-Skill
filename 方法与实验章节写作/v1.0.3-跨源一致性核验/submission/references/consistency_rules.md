# 跨源一致性裁决规则（v1.0.3）

## 1. 三级优先级

1. **实验日志**（实际运行的值）——最高优先级；
2. **配置文件**（实验意图，若日志未覆盖实际值）；
3. **代码默认值**（argparse default / 常量，仅在日志与配置都没有时作为兜底）；
4. **论文正文**（作者转述，只作交叉印证，不作取值来源）。

例外：论文与日志一致但配置不同——以日志为准并在 changes 注明"配置疑似未同步更新"。

## 2. 裁决格式（work/conflict_resolutions.json）

```json
{"name": "参数名（小写）", "chosen_value": "采信值（与来源逐字一致）",
 "rule": "所用优先级规则", "rationale": "为何这样裁决（指向 eid）",
 "eids": ["支撑采信值的证据"], "rejected": [{"value": "被否值", "eid": "…", "reason": "代码默认值被配置覆盖"}]}
```

- 无法判定：`{"name": "…", "escalated": true, "question_for_author": "请确认生效值"}`，
  正文暂用优先级最高者的值并标注"待作者确认"。
- 别名归并：lr=learning_rate、batchsize=batch_size、random_state=seed；裁决用规范名，
  被并名在 rationale 提及。

## 3. 豁免情形（不算冲突）

- 数值等价：3e-4 = 0.0003 = 0.3e-3（引擎归一化后同组）。
- 单位换算：1024 vs 1k、0.5h vs 30min——换算一致即豁免，changes 注明。
- 不同阶段：train 的 batch_size 与 eval 的 batch_size 分开裁决，scope 不同不算冲突。
- 版本演进：论文写 v1 实验、配置是 v2 实验——进 gaps 问作者实验对应关系。

## 4. 裁决与正文的关系

- 正文参数取值 = chosen_value；table_rows.source_eid 填主证据。
- 被否值不写进正文数值位；确需说明时进附录C（"某文件记 X，经裁决未采用"）。
- changes.json 每条裁决一条：{"change": "X 采信 v1（日志），否 v2（代码默认）", "reason": "…"}。
