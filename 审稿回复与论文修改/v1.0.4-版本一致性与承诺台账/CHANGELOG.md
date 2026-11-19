# CHANGELOG

## v1.0.4（2026-11-19）

- 方向：版本一致性与承诺台账。
- 共享核心：init_result / inspect_case / parse_manuscript / parse_comments / revision_engine / verify_revision / assemble_result / validate_output（纯标准库，与 _core 同步）。
- 主攻引擎 consistency_engine.py：
  - 真实差异计算：difflib 行级 opcodes 产出 diff regions（含两侧行号与内容头），纯空白差异自动豁免；
  - 三方对账：applied op → 差异区域强校验（FAIL"声称已改但无实际差异"）、diff region → op 反查认领（WARN"存在未声明的改动"）、采纳但无操作/证据 FAIL"承诺未兑现"、回复信 E# 引用逐项核验；
  - 多轮承诺台账：轮次感知（constraints.round / revision_round）、历史回复文件嗅探、承诺句抽取与关键词重叠兑现判定（已兑现/部分兑现/未兑现/无法判定），输出 revision_ledger.json 与对账报告承诺台账节；
  - exit：任何 FAIL → 1，仅 WARN → 0，致命输入缺失 → 2。
- 文档：SKILL.md（八步工作流 + 10 类异常表）、consistency_rules（对账模型/豁免/词表/命名约定）、承诺台账模板、一致性自查清单、评分对照表、合成最小示例。
- 本地合成案例端到端冒烟：5 个 op 全部落在 diff region、无 FAIL；假上轮回复信（"我们将在下一轮补充对比表"）被检出并匹配本轮 E3 判"部分兑现"；删除历史文件后台账正确记"第 1 轮，无历史承诺"；负向用例（幽灵 E9 引用、采纳无操作、未声明改动）分别正确 FAIL/FAIL/WARN；verify_revision / assemble_result / validate_output 全 PASS。
