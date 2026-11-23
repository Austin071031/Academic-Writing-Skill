# 阶段 5 · 路线卡（基线 v1.0.4 / attempt 90655 / 55 分；N=3，预期均已 ÷3 折算）

```
R1 → v2.0.0（基线 v1.0.4 / 90655 / 55 分）
类型：共性短板修复 #1（题面指令原子化落实审计）
增量一句话：把 task.md 拆成原子机检指令清单（引擎/编译命令/模板/三线表/公式编号/必含项），
  交付前逐条审计产物并出 instruction_report.json，未落实项显式闭环
新增：scripts/instruction_audit.py → work/instruction_checklist.json + work/instruction_report.json；
  direction.json（instruction_audit 参数被脚本真读）
命中维度：实际效果·任务完成度(15) + 实际效果·结果正确性(15) + 实际效果·可核验性(5)
  —— 三维同受益：指令清单即完成度核对表，审计报告即可核验证据
预期：机制真实增益估 G≈+6~12 → 兑现 +2~4（55→57~59）
回归风险：审计误报干扰 Agent → 全部 finding 分级（error 才阻断），白名单资产零改动
回归用例：3 个代理 case 基线原有检查项全过；instruction_audit 在 normal case 必须检出引擎约束
回退：单 commit，可 revert
```

```
R2 → v2.0.1（基线 v1.0.4 / 90655 / 55 分）
类型：共性短板修复 #2（最小闭环保底 + 预算守门）
增量一句话：新增 fast_lane.py 一条命令跑完 保底闭环（init→inspect→build→logscan→
  safe_check→assemble partial→validate），SKILL.md 将其前置为强制第一步，
  先保 partial 再迭代增强
新增：scripts/fast_lane.py（顺序调白名单脚本，任一步失败仍落盘 partial）→
  /app/output 在首个模型请求后即存在合法产物；direction.json（fast_lane.min_reserve_requests）
命中维度：实际效果·任务完成度(15) + 可靠体验·运行稳定性(4) —— partial→completed 转化
预期：G≈+6~12 → 兑现 +2~4（55→57~59）
回归风险：fast_lane 与细流程重复编译浪费预算 → fast_lane 限 1 轮编译且标签 fixed=fastlane；
  资产零改动
回归用例：3 个代理 case fast_lane 均产出 validate PASS 的 result.json；总耗时不超基线
回退：单 commit，可 revert
```

```
R3 → v2.0.2（基线 v1.0.4 / 90655 / 55 分）
类型：单点机制 A（PDF 材料直通）
增量一句话：pdf_extract.py 封装 pdftotext（缺失则诚实降级），从 PDF 文本重建
  章节/公式/参考文献骨架 .tex 与 rebuild_map.json，使 PDF-only 案例进入正常修复闭环
新增：scripts/pdf_extract.py → work/pdf_text.txt + work/rebuild_map.json +
  work/project/main.tex 骨架（TODO 占位处登记 manual_confirmations）；direction.json
命中维度：实际效果·任务完成度(15) + 可靠体验·异常处理(3) —— 契约明示"PDF parsing
  receives the actual PDF"，基线该路径停摆
预期：G≈+3~9 → 兑现 +1~3（55→56~58）
回归风险：pdftotext 不存在 → 记 exceptions 并退回原文字指引路径（行为守恒）
回归用例：degraded case 产出可编译骨架或诚实 partial；normal/overbudget 不受影响
回退：单 commit，可 revert
```

```
R4 → v2.0.3（基线 v1.0.4 / 90655 / 55 分）
类型：单点机制 B（模板自动修复闭环）
增量一句话：template_fix.py 对 template_audit 的 P1/P3/P4 发现做受限自动适配
  （必填项 TODO 骨架插入+人工确认登记、hyperref 后置、过时宏包白名单替换），全部留痕
新增：scripts/template_fix.py → work/template_fix_log.json；direction.json
命中维度：实际效果·任务完成度(15) + 使用增益·效率(5) —— 高分方向直接加深，
  只审不修→审修闭环
预期：G≈+3~9 → 兑现 +1~3（55→56~58）
回归风险：自动插入骨架污染稿件 → 全部插入带 TODO 标记+manual_confirmations 登记，
  语义内容仍 Agent 回填
回归用例：3 个代理 case 基线检查全过；template_fix dry-run 与应用结果一致
回退：单 commit，可 revert
```

## 提交顺序（最稳 → 最激进）

v2.0.0（指令审计，纯增量只读检测，风险最低）→ v2.0.1（保底管线，动流程不动资产）→
v2.0.3（受限自动修复，白名单边界）→ v2.0.2（PDF 重建，路径最新）。
（§0-7 留空，按默认自排；组合版需第 5 个版本号，§0-5=4 故不做。）
