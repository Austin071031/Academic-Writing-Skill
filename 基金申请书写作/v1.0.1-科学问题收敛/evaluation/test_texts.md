# 合成测试文本（标注：全部为合成材料，非正式案例）

## 测试 A：问题过大（scope_too_broad）

科学问题节段（无边界句）：
> 本课题将系统研究界面工程的各个方面，全面揭示其机理，全方位提升器件性能。

预期：scope_too_broad（high）×3+（系统研究/各个方面/全面揭示/全方位逐词命中）。

## 测试 B：问题数量过多（question_count）

科学问题节含 5 个"?/？"结尾问句或 5 条编号条目。
预期：question_count（medium）×1：问题数量过多，未收敛。

## 测试 C：无子问题分解（no_decomposition）

科学问题节只有 1 个核心问句，无 子问题/分解为/具体包括/（1）/1）/其一 任一标记。
预期：no_decomposition（medium）×1。

## 测试 D：无边界声明（no_boundary）

科学问题节全文不含 不涉及/边界/限定/聚焦/仅限于/排除。
预期：no_boundary（medium）×1。

## 测试 E：问题与目标/路线错位（method_misaligned）

科学问题节写「暗物质与暗能量的耦合机制是什么？」，研究目标与技术路线均为钙钛矿界面工程。
预期：method_misaligned（medium）×1（两节相似度均 <0.05）。

## 测试 F：缺科学问题节（missing_section）

草稿无任何 element=="科学问题" 的段落。
预期：missing_section（high）×1。

## 测试 G：正例零误报

科学问题节（带真实 FID）：
> 本课题聚焦一个核心科学问题：偶极取向如何调控能级排列？该问题可分解为两个子问题：
> 其一，取向对界面势垒的定量贡献〔F0018〕；其二，取向的制备可控性。
> 研究边界限定于模型器件，不涉及大面积制备。

预期：question audit 对该节 0 findings（分解标记=其一/分解为；边界=限定/不涉及；
过大表述=0；与目标/路线相似度 ≥0.05）。

## 测试 H：seed 候选抽取

合成材料含「界面缺陷钝化机制尚不清楚」「其影响机制不明」「亟待建立原位探测手段」三处表述。
预期：question_seed.json candidates 含对应 pid 与 ±50 字上下文，signal 分别为 尚不清楚/机制不明/亟待。

## 测试 I：宽泛表述警示（seed warnings）

task.md 或材料中含「系统研究」「全方位」。
预期：question_seed.json warnings 按 where=materials / task.md 分别登记。
