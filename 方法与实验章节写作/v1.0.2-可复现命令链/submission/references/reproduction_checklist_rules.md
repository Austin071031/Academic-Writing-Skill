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
