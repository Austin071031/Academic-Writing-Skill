# location_table.md 节段说明模板

> 本文件是节段说明（各节段的写法和判读规则），`location_table.md` 正文由 anchor_engine 自动生成，Agent 不手抄行号。以下为引擎产出应包含的节段与判读要点。

## 第 1 节：文件头

- 基线路径 + 行数 + 采集模式（file / structure-fallback）；
- 修订稿路径 + 总行数。两侧行数是坐标核验的边界依据。

## 第 2 节：双坐标定位表

表头固定：

```
| op_id | 意见 | 动作 | 基线坐标 | 修订稿坐标 | 锚点原文摘录 | 状态 |
```

判读规则：

- **基线坐标**：`§章节 P### 行N`；锚点找不到时显示 `（锚点已由改写消除）`；
- **修订稿坐标**：`行N / P###` + 新文本前 30 字（`<br>` 分隔）；
- **状态**：`applied` 正常；`锚点模糊-需人工复核` 出现在 fuzzy 命中行；
- 新增段（insert_*）的基线坐标落到锚段，读表时以修订稿坐标为准。

## 第 3 节：变更区域（基线行 → 修订稿行）

行级 diff 对齐结果：`类型（replace/insert/delete） | 基线行区间 | 修订稿行区间 | 关联 op`。用于回答"基线第 X 行在修订稿里变成了什么"。

## 第 4 节：⚠ 模糊锚点预警（条件出现）

`fuzzy` 命中的 op 逐条列出：method、ratio、锚点摘录、修订稿行/段、新文本摘录。处置：人工复核定位并写 manual_confirmations。

## 第 5 节：回复信定位声明核验

- 未检测到 response_letter.md：显示"跳过"，属正常分支（引擎首跑）；
- 存在不可核对声明：逐条列出 `[类型] 第N行 声明：说明`，引擎 exit 1；
- 全部可核对：显示 `E# 引用 N 处、引文 N 处、坐标引用 N 处`。

## 重跑纪律

1. 改 edit_plan → 先 revision_engine，再 anchor_engine；
2. 改 response_letter（任何一处）→ 重跑 anchor_engine；
3. 改基线 → 先 parse_manuscript + revision_engine + anchor_engine 全链路重跑。
