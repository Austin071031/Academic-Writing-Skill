# 方法规则与失败模式（v2 合并版：原 reproduction_checklist_rules.md + failure_modes.md）

# 复现清单登记规则（v1.0.2）

## 1. 七项要素（work/repro_checklist.json）

| 键 | 内容 | 无材料时 |
|-|-|-|
| code_version | commit/tag/版本号文件位置 | gaps(high)：追问仓库地址与 commit |
| environment | os、python、关键库版本（dict） | 写已确认项，缺的进 gaps(medium) |
| hardware | 机型/卡数/显存 | 论文 Hardware 段落通常有；没有则 gaps(medium) |
| data_acquisition | url 或 hash 或 path 三选一必填 | 都无则 gaps(high)：复现者拿不到数据 |
| commands | 可执行命令数组（训练+评测+数据准备） | 由配置/日志/代码重构，changes 注明推演 |
| seeds | 种子数组（含数据划分种子） | gaps(high)：随机性不可控 |
| est_cost | 预计开销（据日志 wall time 推算） | 可写"未提供，无法估算" |

- data_acquisition 必须含 url/hash/path 之一，否则闸门判缺失（该项是复现失败的常见根因）。
- est_cost 推算过程写进 changes.json（"3.2h/epoch × 10 epoch ≈ 32 GPU·时"）。

## 2. 命令转录规范

- 照抄日志中的原始启动命令（extract 的 command/env_var 候选）；日志没有时按
  `python <入口脚本> <配置>` 重构，并在 changes 注明"重构，未经日志确认"。
- 命令必须是"复制即可执行"形态：含必要环境变量（CUDA_VISIBLE_DEVICES）与配置路径。
- 每条命令在第六节正文以代码行出现；repro_gate 会校验命令首令牌确实在文中。

## 3. 失效场景句式（第七节）

- 合格句式："在训练数据超过 X 规模时未验证显存可行性（峰值显存 Y GB，接近 80GB 上限）。"
- 不合格句式："本文方法存在一定局限性。"/"未来还有改进空间。"
- 每条限制尽量挂证据（峰值显存来自日志）或标注"无材料支撑，属保守声明"。

## 4. 复现分级（写进 result.stats）

- full：七项齐全且命令经日志确认。
- partial：七项齐全但部分命令为重构，或 est_cost 缺失。
- minimal：缺任一项——status 必须 partial 并在 uncertainty 说明缺什么。

---

# 基础 Agent 典型失败模式（复现视角对照自查）

1. **复现清单空转**：写了"代码将公开"却不给版本、地址与命令。→ 对策：七项强制登记 +
   repro_gate 逐项 fail。
2. **命令不在正文**：清单文件有命令，正文没有，读者翻不到。→ 对策：命令首令牌入章校验。
3. **版本缺失**：只写"PyTorch"，复现者装 2.0 与 2.4 结果不同。→ 对策：version 类候选
   逐项锚定，缺进 gaps。
4. **数据不可获取**：数据名称有了，无 URL/校验和，复现卡在第一步。→ 对策：
   data_acquisition 三选一必填。
5. **种子遗漏**：写了训练种子漏划分种子，复现划分对不上。→ 对策：seeds 数组含划分种子。
6. **限制套话**："存在一定局限性"不指向任何失效场景。→ 对策：第七节句式规范 + 附录C
   追问具体场景。
7. **超时空手**：→ Phase 0 骨架 + 预算告急立即装配 partial。

---

## 复审修订清单（v3.0.4 追加，Phase 4.5 用）

- [ ] 每个含数值的句子都有锚点紧随
- [ ] 无"随着/众所周知/重要意义/存在局限性"类套话
- [ ] 无多步压句（一句一个动作）
- [ ] 阶段归属（训练/验证/测试）在每段首句可见
- [ ] 每条限制含具体失效场景
- [ ] 表格数值与正文一致
