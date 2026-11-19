# transfer-terminology-lock（科研成果转化写作·术语锁定与跨文体一致）

把论文/技术报告改写为科普文章、新闻通稿、简报或申报材料时，先建立**可锁定术语表**，
再用引擎强制同一概念在全文与多份产物中说法统一：缩写首次展开、中文异写收敛、
化学式/符号写法唯一、跨文体替换有依据。

## 用途与适用条件

- 适用：给定科研源文 + 目标受众/文体（可能多份产物），要求术语一致性的转化改写任务。
- 不适用：从头写论文、纯语言润色、引用管理（另有专门 Skill）。

## 安装

目录即 Skill 本体，安装为 `/skills/weekly-skill` 即可。仅依赖 Python3 标准库；
处理 PDF 源文时需环境自带 pdftotext（评测镜像已提供）。

## 快速开始

按 `SKILL.md` Phase 0-5 执行；完整说明见 `docs/USAGE.md`，最小示例见 `examples/minimal_example.md`。

## 两个子命令

- `terminology_engine.py candidates`：从 source.json 机选术语表草稿（异写检测：全称↔缩写配对、
  相似度≥0.70 中文异写、大小写/连字符变体）。
- `terminology_engine.py audit`：对审定后的 term_table.json 审计改写稿（`--more` 支持多产物），
  查 variant_used / acronym_not_expanded / symbol_conflict / cross_file_inconsistent / unlocked_change。

## 边界

- 不臆造术语全称；源文未给全称的缩写用描述性说法替换并标注待确认。
- 异写判据为工程阈值（相似度 0.70，见 references/terminology_rules.md），草稿必须经 Agent/作者审定。
- 术语歧义不强行收敛：保留源文说法 + 人工确认。
