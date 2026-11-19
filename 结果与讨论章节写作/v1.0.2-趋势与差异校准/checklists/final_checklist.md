# 交付前自查清单

## A. 契约与产物

- [ ] result.json 含 output_contract 全部字段 + case_id + status + sources + uncertainty + change_log
- [ ] results_and_discussion.md 存在；环境有 pandoc/LaTeX 时已生成 docx/pdf，否则已注明
- [ ] calibration_report.json 存在且 verdict = PASS

## B. 校准（本 Skill 核心）

- [ ] 每个比较句的措辞级别与 comparisons.md 定级一致
- [ ] 所有"显著/significantly"句子同句含 p（或 n/CI/±）
- [ ] 无统计输出的材料中未出现"显著"
- [ ] p ≥ 0.05 的比较写为"相当/无显著差异"，无方向暗示
- [ ] 边缘 p 值写为"趋势，未达显著（p = …）"
- [ ] 单条件现象均带"仅/只在/only"限定
- [ ] 幅度全部量化（+% / 倍数 / 绝对差），无裸"大幅""明显"
- [ ] 讨论段回引未升级措辞强度

## C. 事实一致与诚实性

- [ ] 抽查 3 处统计量回统计输出原文核对一致
- [ ] 正文无材料之外的数据；引用均出自材料参考文献列表
- [ ] uncertainty 列出统计缺失（效应量/校正方法等）与脚本误报说明
- [ ] change_log 记录至少一处措辞降级的修改
