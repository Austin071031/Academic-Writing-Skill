# citation-coverage-audit v1.0.4｜引用覆盖对得上

参赛 Skill 版本之五，主攻**引用覆盖**方向：角色分类（foundation/key/representative/recent/context/other）
+ 三类引擎审计（分类完整性、论断-引用双向绑定、关键/近期覆盖充分性），漏引与覆盖不足自动转
manual_confirmations；与 build/validate 的正文-文献表双向一致性复检形成两层防线。

## 适用场景

- 补引用、审校引言与相关工作的引用覆盖；
- 修复引用悬空、关键工作漏引、近期进展缺失、段末堆放引用等问题。

## 快速开始

共享管线 + Phase 3 登记 ref_classification.jsonl（+高质量 claim_bindings.jsonl）→
Phase 4 `coverage_audit.py` + `build_deliverables.py` → assemble/validate/render。
详见 [docs/USAGE.md](docs/USAGE.md)。

## 依赖与边界

- Python 3.8+ 纯标准库。
- 覆盖判据依赖文献库元数据质量（年份缺失会影响近期窗口判定）。

## 仓库

https://github.com/Austin071031/Academic-Writing-Skill （目录：引言与相关工作写作/v1.0.4-引用覆盖审计）
