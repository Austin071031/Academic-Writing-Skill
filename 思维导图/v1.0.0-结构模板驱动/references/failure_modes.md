# 失败模式与对策（v1.0.0）

| 失败模式 | 症状 | 对策 |
|-|-|-|
| 装饰词当节点 | "研究意义重大""方法先进"成节点 | 节点必须是可核验的实质内容；意义类表述放 note 或删除 |
| 层级混乱 | 方法与结果同级混排、深度 >6 | 按模板分支归位；map_audit 会报 too_deep/fanout |
| 证据悬空 | evidence.unit 不存在 | critical；回 digest 重新定位单元号 |
| quote 改写 | fact 证据 paraphrase | critical；改回逐字（可截取子串），或把 type 改 summary |
| 数字凭印象 | 标题数字不在证据单元 | warning(number_unverified)；核对原文或删除数字 |
| 结论当事实 | 推断内容标 confirmed | 推断节点 type=inference 且 status=uncertain |
| 材料冲突被抹平 | 只写一方说法 | 两节点并列 + conflicts 边，双方挂证据，标 uncertain |
| 缺口被编造 | 材料无局限/风险内容却写了 | 改标 status="missing" |
| 模板错判 | 会议材料判成论文 | 以任务说明为准，换用对应分支维度 |
| 导图不可编辑 | 只交图片 | 必须交 .md/.mm/.opml/.mmd 源文件（脚本自动生成） |
