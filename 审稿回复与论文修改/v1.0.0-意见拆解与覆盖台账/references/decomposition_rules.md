# 意见拆解规则

## 拆分判据

1. 一个子要求只含一个可执行动作或一个待答问题；
2. 连接词（并且/同时/另外/此外/furthermore/in addition/;）两侧若各有动作信号，必须拆开；
3. 背景句（"作者声称 X，但未提供 Y"）与其后的要求句合并为一条，不单独成项；
4. "如图 1 所示……此外表 2 也……"这类图表并列，若要求动作不同（一个改图、一个改表）必须拆开；
5. 审稿人写"同上""同意见 2"时，本子要求保留，response 中引用被指向的处置，不重复修改。

## 类型词表（type）

experiment（补做/对照/重复实验）、data（数据/样本/数据集）、statistics（统计/显著性/误差棒）、method（方法/参数/流程）、citation（引用/参考文献）、format（格式/单位/缩写/图注）、writing（语言/表述/润色）、ethics（伦理/知情同意/数据可用性）、discussion（讨论/结论/机制/局限）、other。

## 严重度（severity）

- major：必须/需要/应当/major/must/require，或涉及结论有效性；
- minor：建议/可以考虑/minor/suggest/optional；
- question：纯疑问句且不含动作要求；
- unspecified：脚本无法初判，Agent 复核时必须改判。

## 动作类别（action_kind）

add_experiment / add_data / add_citation / reanalysis / rewrite / format / delete / other。
前三者加 reanalysis 自动标记 needs_evidence=true。

## 冲突与重叠裁决

- 重叠（相似度≥0.35 无冲突信号）：合并回应，两处回复互相引用"同 R#-C#"；修改只做一次，两个子要求的 edit_ops 指向同一 op；
- 冲突（方向相反信号）：列入手动确认；处置策略二选一并说明理由（通常以 major 优先、以编辑要求优先）；回复信中两条意见都要解释取舍；
- 依赖（共享证据）：证据清单只建一条 EV，多处引用。

## 覆盖台账（答得全终检）

audit 阶段每个子要求必须同时满足：decision 非空、response ≥20 字含可核查指涉、引用的 op 状态 applied。任一不满足即未覆盖，必须补齐。
