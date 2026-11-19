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
