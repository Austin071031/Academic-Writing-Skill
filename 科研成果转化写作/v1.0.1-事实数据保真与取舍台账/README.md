# transfer-fact-fidelity（科研成果转化写作·事实数据保真与取舍台账）

把论文/技术报告改写为科普文章、新闻稿、简报或申报材料时，用脚本保证"留得住"：
每个数字/百分比/样本量/单位/图表编号都能在源文中逐值溯源（含换算式认可），
且每段的保留/压缩/删除都记录在取舍台账中。

## 用途与适用条件

- 适用：给定科研源文 + 转化写作任务，要求数据与源文一致、删改有据可查。
- 不适用：受众可读性打磨（transfer-audience-adapt）、论断强度校准（transfer-claim-calibration）、
  术语统一（transfer-terminology-lock）、纯语言润色、从头撰写论文。

## 安装

目录即 Skill 本体，安装为 `/skills/weekly-skill` 即可。仅依赖 Python3 标准库；
处理 PDF 源文时需环境自带 pdftotext（评测镜像已提供）。

## 快速开始

按 `SKILL.md` Phase 0-5 执行；完整说明见 `docs/USAGE.md`，最小示例见 `examples/minimal_example.md`。

## 边界

- 认可 verbatim（原样/单位等价）与 derived（百分比↔小数、±1% 四舍五入、单位换算、端点重算）四类等价，
  其余一律判 missing/altered/unverified；判据见 `references/fidelity_rules.md`。
- 年份、紧贴字母的数字（化学式、倍率如 0.5C）、章节号/版本号被遮蔽，不参与数据判定。
- 遮蔽规则是启发式：被遮蔽项若构成实质性新事实，仍需人工确认。
