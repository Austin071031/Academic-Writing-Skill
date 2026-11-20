# 速查表：切分与五值支撑（claim-source-mapper）

## 切分规则
一条一判；数值/比较/因果/机制各成条；复合句必拆；claim_text 不依赖上下文暗指。

## 五值支撑
direct=原文直接陈述（计入 supported）；partial=支持更弱版本（→partial）；
background=仅背景（不计入）；conflicting=方向相反（→conflicting）；not_supporting=相关不支持（记差异）。

## status 推导
有 direct 且无 conflicting→supported；仅 partial→partial；有 conflicting→conflicting；全无→unsupported（进 open_questions）。

## 铁律
unsupported 绝不补造引用；background 不冒充 direct；多对多关系在 claim_source_matrix.csv 逐格标注。
