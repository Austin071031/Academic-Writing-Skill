# 使用说明

## 调用方式

由 Agent 在 Harbor 评测环境中按 SKILL.md 执行；本地调试时把 `/input`、`/app/work`、`/app/output`
替换为实际目录即可，五个脚本均接受路径参数。

## 输入解释

- `case.json`：权威输入。`case_id` 原样回填；`output_contract` 的全部键必须出现在 result.json 中（键名与结构不变）。
- `task.md`：任务要求（体裁、受众、格式、写作动作）。
- 材料文件：唯一事实来源；不依据文件名或领域标签推测内容。

## 输出解释

见 references/output_spec.md。核心纪律：摘录逐字、定位可回查、论断编号与成稿互指、
result.json 含 case_id + output_contract 全字段 + status + assumptions/uncertainty/change_log/exceptions。

## 失败处理与自查

1. 先跑 run_pipeline.sh，看 brief.json 的 issues 与 text_manifest.json 的 failed 文档；
2. 完成阶段1-4 后跑 validate_output.py：errors 必须修复或在 uncertainty 诚实说明；
3. 预算耗尽前把当前最优产物定格为 partial，不要空跑。

## 适用范围与限制

适用于有明确材料集、要求来源可回溯的中英文学术写作任务；不适用于无材料创作与联网检索任务。
