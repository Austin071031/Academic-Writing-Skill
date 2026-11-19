# research-gap-derivation v1.0.2｜研究空白说得实

参赛 Skill 版本之三，主攻**研究空白**方向：空白以"前提→缺口→本文对应"三元结构登记
（gap_chain.json），引擎校验前提可溯源、强制数字泄漏检查、渲染 gap_derivation.md 推导链报告；
推不出空白时判 fail，倒逼如实标注或 partial 降级，杜绝"少有研究"式空泛空白。

## 适用场景

- 起草/修改引言中的研究空白段；
- 把选题必要性与已引工作的具体缺口建立可复核的对应关系。

## 快速开始

共享管线 + Phase 3 登记 gap_chain.json → Phase 4 `gap_chain.py` + `build_deliverables.py` →
assemble/validate/render。详见 [docs/USAGE.md](docs/USAGE.md)。

## 依赖与边界

- Python 3.8+ 纯标准库。
- 空白质量上限取决于材料中 limitation 信息的丰富程度；材料单薄时按 SKILL.md 降级路径执行。

## 仓库

https://github.com/Austin071031/Academic-Writing-Skill （目录：引言与相关工作写作/v1.0.2-研究空白推导链）
