# 方法规则与失败模式（v2 合并版：原 condition_matrix_rules.md + failure_modes.md）

# 六要素×阶段矩阵登记规则（v1.0.1）

## 1. 矩阵结构（work/element_matrix.json）

```json
{
  "steps":  {"train": {"eids": ["E0006"], "section_anchor": "sections/01_steps"},
             "val":   {"na": true, "reason": "…"},
             "test":  {"eids": ["E0019"], "section_anchor": "sections/01_steps"}},
  "setup":  {"train": {...}, "val": {...}, "test": {...}},
  "params": {"train": {...}, "val": {...}, "test": {...}},
  "datasets":{"train": {...}, "val": {...}, "test": {...}},
  "baselines":{"train": {...}, "val": {...}, "test": {...}},
  "repro":  {"train": {...}, "val": {...}, "test": {...}}
}
```

- 有材料支撑：`{"eids": [...], "section_anchor": "sections/0N_xxx"}`，二者至少其一。
- 不适用：`{"na": true, "reason": "具体原因"}`——理由必须指向事实（如"早停只用验证集，
  无测试阶段超参"），禁止写"无"。
- engine 检查：缺格、na 无理由、有 eids 但锚点不存在台账 → matrix_report 记 missing。

## 2. 串台判定标准

- 训练专属超参：learning_rate / batch_size / epochs / warmup / weight_decay / grad_clip 等
  带新取值的赋值句，不得出现在验证/测试/评测描述中；对照小节说明基线训练预算属于合法例外，
  但必须写明"同预算"。
- 评测协议句（Accuracy/F1/显著性）不得混进训练设置小节。
- 数据划分：train/val/test 比例与种子必须归属数据集要素格，不得散写在设置小节。

## 3. scope 标注（与 parameter_table_template 协同）

每个参数行的 scope 取 train/val/test/环境/通用 之一；"通用"仅允许种子、设备、精度等
真正跨阶段共享项；超参一律分阶段。engine 对不可判定 scope 记 scope_violations。

## 4. 从矩阵到段落

- 每要素一节：先写 train 格事实，再写 val，再写 test；na 格不进正文，进附录C说明（可选）。
- 段落首句给出阶段归属（"训练阶段……"），避免读者自行推断。
- 对照小节引用实验行编号（R#），保证矩阵到正文可追溯。

---

# 基础 Agent 典型失败模式（矩阵/串台视角对照自查）

1. **整列留白**：只写训练阶段，验证/测试流程一句带过。→ 对策：18 格强制登记，na 也要有理由。
2. **条件串台**：评测节里写"以 3e-4 学习率训练 10 轮后……"，把训练细节塞进评测描述；
   或验证集口径混入测试结论。→ 对策：engine 串台检测 + 段落首句阶段归属。
3. **scope 含混**：参数表写"训练/评测通用"，读者无法判断该在哪个阶段复用。→ 对策：
   scope 枚举约束 + scope_violations 报告。
4. **步骤压句**：把"加载数据、训练、评测"压成一句。→ 对策：步骤要素格逐格一行一步。
5. **基线预算不明**：对照不写是否同预算，比较成为断言。→ 对策：baselines 格登记预算，
   正文写"同预算"或给出差异。
6. **缺格隐藏**：某阶段材料缺失时静默略过。→ 对策：缺格 fail + gaps(high) + partial 降级。
7. **超时空手**：大材料解析耗时导致空手。→ 对策：Phase 0 骨架 + 预算告急立即装配 partial。
