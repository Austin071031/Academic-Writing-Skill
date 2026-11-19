# results-discussion-structuring vv1.0.1-｜双组织模式

写作10｜结果与讨论章节写作——按图序/按问题两种组织模式决策规则；发现清单先行、段落骨架（主题句→呈现→比较→阴性）；check_structure.py 检测结果段解释性/因果性/评价性词汇混入、段落无图锚、长度失衡、推测未标注与发现遗漏。

## 依赖与安装

- 仅 Python 3.8+ 标准库（脚本零第三方依赖）；PDF 抽取使用 `pdftotext`/`pdftoppm`（poppler），缺失时按 SKILL.md 异常处理降级。
- 安装：将本目录整体复制到 `/skills/weekly-skill`（平台执行时由评测方安装）；本地开发以本目录为根。
- 无网络依赖、无个人文件依赖。

## 快速开始（Agent 视角）

1. 读取 `/input/case.json` 与 `/input/task.md`，记录 case_id 与 output_contract 全字段。
2. 按 SKILL.md 工作流程抽取材料、建工作底稿（`/app/work/`）。
3. 按本方向方法写结果段与讨论段（`/app/output/results_and_discussion.md`）。
4. 运行 `scripts/` 下的自检脚本，未通过必须修改后重跑至 PASS。
5. 按 `checklists/final_checklist.md` 自查，生成 `result.json`（含 output_contract 全字段 + case_id + status + sources + uncertainty + change_log）。

完整规则见 [SKILL.md](SKILL.md)；最小调用示例见 SKILL.md 第 5 节（已标明为示意）。

## 输入 / 输出

- 输入：`/input/case.json`、`/input/task.md`、`/input/` 下科研材料（PDF/图表/数据表/统计输出）。
- 输出（`/app/output/`）：`result.json`、`results_and_discussion.md`、本方向核验报告（JSON）、可编辑 docx/PDF（环境允许时）。

## 适用边界

- 适用于：依据固定科研材料撰写/核查结果与讨论章节中与本方向对应的问题。
- 不适用于：无材料的自由写作、需要真实重跑实验的任务。
- 材料缺口按 SKILL.md 异常处理表降级为 partial 并显式标注。

## 维护信息

- 版本：v1.0.1-（2026-11-19）。变更见 [CHANGELOG.md](CHANGELOG.md)。
- 玻尔产品周赛第四期 写作10 参赛版（attempt 89798）。
