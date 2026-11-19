# 版本谱系方法说明

## 版本模型

- 快照 = 文件内容的 sha256，文件以摘要命名存入 vault。内容相同 → 同 rev，
  天然去重；内容不同 → 必然不同 rev，不存在“同名不同内容”的歧义副本。
- manifest（lineage.json）每条版本记录：rev、sha256、label、parent、
  source（author/skill/model）、段落数、字节数、时间。
- 谱系 = parent 链。交付稿的完整来源 = 沿 parent 链回溯到 author 快照。

## diff 的解读

diff 按位置对齐（±3 容差），未变段落先精确匹配。新增/删除段落会造成
其后段落号位移，解读时以文本内容为准。diff 输出 before/after 全文片段，
本身就是“版本间差异对比”的交付证据。

## 回退语义

restore = 从 vault 拷贝快照到目标路径，sha256 必然一致；
verify 遍历 manifest 校验全部快照。回退不修改 vault 中任何历史版本
（不可变），只产生新检出。

## 与其他方向的关系

定点修改的“锚定—最小—台账”纪律、保真核验、诚实 result.json 为通用要求；
本方向在此之上叠加版本不可变性与谱系可回溯性。修订标记（v1）可叠加：
快照可在修订稿/接受稿两个状态分别建立。

## 核验清单

1. manifest 首版本 source=author 且与 /app/work/originals 原稿 sha256 一致；
2. 除首版本外每条均有 parent，parent rev 存在；
3. verify 全部通过；
4. result.json 的 change_records 与最终 diff 数量一致。
