# 失败模式与对策（v1.0.1）

| 失败模式 | 症状 | 对策 |
|-|-|-|
| JSON 语法错误 | engine 退出"无法解析" | `python3 -m json.tool work/mindmap.json` 定位 |
| 分组不合一 | 同类节点被拆到不同组 | 手工调整 parent 后重跑 |
| 数字查无出处 | number_unverified | 核对原文；派生数字在 note 写明计算式 |
| 覆盖率过低 | stats.coverage < 0.3 | 对照 digest 补重要分支，而非堆叶节点 |
| 引擎降级被忽视 | 输出提示 partial 但装作 success | 修 critical 或接受 partial 并写 uncertainty |
| 预览缺失当失败 | PNG 未生成 | 看 preview_status.json；SVG/HTML 是有效预览 |
| 手工改 .mm/.opml | 与 mindmap.json 不一致 | 只改 mindmap.json，重跑渲染 |
| 装饰性节点 | "意义重大"成节点 | 删除或改 note；节点须可核验 |
