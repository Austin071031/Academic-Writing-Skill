# 提交与评分记录（SUBMISSION）

- 题目：学位论文与长文档写作（challenge-32c0210d）
- 本版本：v1.0.3-意见拆解与改稿台账（longdoc-revision-ledger，方向：改得动·持续修改）
- 提交方式：playground CLI 0.1.57（`playground submit --challenge-id challenge-32c0210d --outputs <本目录> --skill <本目录>`）
- 提交时间：2026-11-19 14:22 UTC

## 评分结果

| 项 | 值 |
|-|-|
| Attempt ID | 90748 |
| 状态 | scored（final，2026-11-22 出分） |
| Harbor 得分 | **53.0 / 100** |
| GitHub 附加分 | 0（原因：not_found，见下） |
| 最终得分 | **53.0** |
| Outcome | partial（Harbor 评语：genuinely-derived solution 完成度不足，部分给分） |

## 备注

- GitHub 附加分未计入：评分侧返回 `github_reason = not_found`。本目录 `GITHUB_URL.txt` 存在且链接匿名可访问（HTTP 200 已验证）；下一轮迭代将排查评分侧对 `GITHUB_URL.txt` 位置/格式的预期（候选：要求仓库根链接、首行裸 URL 或提交目录根路径语义）。
- 提分方向（依据 outcome=partial）：提高对 3 个固定案例的任务完成度——确保生成/修改的主产物（章节稿/修订稿）真正落在 /app/output，而非仅交付检查报告；对 organizer-edit-workorder.json 的实际编辑目标逐条落实。

## 出分回填（2026-11-25 查询）

- Harbor 得分 **53.0 / 100**，GitHub 附加分 0（评分侧返回 `github_reason = not_found`；本目录 GITHUB_URL.txt 存在且链接匿名 HTTP 200 可访问，附加分链路待排查）。
- Harbor 评语：genuinely-derived solution 完成度不足，部分给分（outcome=partial）。
- 迭代方向：主产物完整落 /app/output、对 organizer-edit-workorder.json 编辑目标逐条落实、修复附加分链路。
