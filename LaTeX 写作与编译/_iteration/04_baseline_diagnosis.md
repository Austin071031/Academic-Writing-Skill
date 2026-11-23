# 阶段 4 · 基线确认与诊断

## 基线判定

- 台账最高分 = 68（attempt 66367）：内容不可得（仓库无目录、bundleAvailable=null），
  R1 要求新版为基线超集，故**不能**作为代码基线；仅作"本题可达 68+"的方向证据。
- **代码基线 = v1.0.4（模板适配与可重复构建，attempt 90655，55 分，内容可得最高分）。**
- 分支判定：台账最高分 68 ≥ 80×0.7=56 → 基线健康，走阶段 5 方向迭代。
  （若以代码基线 55 计则 55<56 触发契约层分支；此处按 §0-9"自动=台账最高分"执行，
  并说明：两已出分版 outcome=partial 暴露的预算问题已作为共性短板 #2 单列修复，
  契约字段本身经 validate_output 验证 PASS，无弃权型契约缺陷。）

## 机制资产清单（白名单 = 表 3 共有文件 + v1.0.4 独有，逐项禁改接口）

| 资产 | 做什么 |
|-|-|
| init_result.py | 落盘 result.json 骨架（case_id + 契约字段），防超时空手 |
| inspect_case.py | 侦察输入、暂存工程、识别主文件/引擎/文档类/缺失引用 |
| tex_build.py | 多轮编译：引擎探测（CJK→xelatex）、bib 链路、needs_rerun 收敛判断、单进程超时 |
| tex_logscan.py | 19 类错误分类、file:line 定位、级联根因归并、overfull 统计 |
| tex_check.py | 源码静态审查：label/ref/cite/bib 键、环境配平、占位符、元数据 |
| template_audit.py | P1 类必填项、P2 冲突对、P3 加载顺序、P4 过时项、P5 模板差异 |
| build_manifest.py | 真实版本/源码 sha256/命令序列/轮次 → BUILD_MANIFEST |
| assemble_result.py | 契约化交付（latex_project + preview.pdf + reports + result.json） |
| validate_output.py | 交付闸门（契约字段/case_id/可编辑产物/status 一致） |
| SKILL.md 异常表+预算兜底 | 8 类异常处置与请求过半降级规则 |

## 余量缺口表（基线 55 → 目标 80，缺口 25 = 每评分单元 +8.3）

| 缺口 | 归属维度 | 根因 | 对应活路 | 可拿回(折算后) | 承担版本 |
|-|-|-|-|-|-|
| 题面指令（引擎/格式/改动点）未逐项落实审计 | 实际效果 40 | B 内容型 | instruction_audit.py（真跑证据：normal case 引擎约束漏检） | +2~4 | v2.0.0 |
| partial 频发，无最小闭环保底 | 实际效果+可靠体验 | A 弃权型倾向 | fast_lane 保底管线（证据：双 attempt outcome=partial） | +2~4 | v2.0.1 |
| PDF-only 案例停摆 | 实际效果 | B 内容型 | pdf_extract.py（证据：degraded case tex_build 失败） | +1~3 | v2.0.2 |
| 模板只审不修，必填项靠手工 | 实际效果+使用增益 | C 增量 | template_fix.py 受限自动适配 | +1~3 | v2.0.3 |
