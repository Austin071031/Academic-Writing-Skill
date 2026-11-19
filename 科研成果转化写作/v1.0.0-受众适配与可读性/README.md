# transfer-audience-adapt（科研成果转化写作·受众适配与可读性）

把论文/技术报告改写为面向指定读者的科普文章、新闻稿、简报或申报材料，
用脚本保证"读得懂"（句长、缩写展开、术语解释、篇幅达标）且事实不漂移。

## 用途与适用条件

- 适用：给定科研源文 + 目标受众 + 目标文体（可能含篇幅上限）的转化改写任务。
- 不适用：从头写论文、纯语言润色、引用管理（另有专门 Skill）。

## 安装

目录即 Skill 本体，安装为 `/skills/weekly-skill` 即可。仅依赖 Python3 标准库；
处理 PDF 源文时需环境自带 pdftotext（评测镜像已提供）。

## 快速开始

按 `SKILL.md` Phase 0-5 执行；完整说明见 `docs/USAGE.md`，最小示例见 `examples/minimal_example.md`。

## 边界

- 不生成源文外事实；源文未给全称的缩写用描述性说法替换并标注待确认。
- 可读性判据为工程阈值（见 references/audience_rules.md），不替代人工终审。
