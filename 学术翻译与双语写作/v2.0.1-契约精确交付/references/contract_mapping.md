# 契约精确映射方法（contract mapping）

## 问题定义

v1 的 assemble_result 用固定别名表回填 output_contract：字段名命中别名就指向
outputs/evidence_map，否则塞 outputs 汇总。结果是“字段都在、内容空泛”——
评分“结果可核验性”要求每个契约字段对应可定位、可复核的真实内容。

## 机制（contract_fill.py）

1. **产物注册表**：每种交付文件带一句内容说明与匹配关键词（如
   translation_full.md ↔ 译文|翻译|translation|交付|稿件|全文）。
2. **打分匹配**：字段名 + spec 说明文本对注册表关键词打分，取最高分；
   字段说明中直接出现产物基名的加权。
3. **结构化条目**：命中字段写入
   `{file, sha256, bytes, summary, content_preview(前300字符), verified:true}`——
   评审无需打开文件即可核验内容与产物一致性。
4. **内置字段保护**：契约字段与 result.json 内置数据字段同名且已有内容
   （如 uncertainty、经别名填充的 evidence）时保留原语义数据，不被文件映射覆盖。
5. **override 通道**：`work/contract_override.json`（`{"字段名": "文件名"}`）
   人工指定映射；指定文件不存在时回退自动匹配并记 uncertainty（不静默）。
6. **诚实兜底**：匹配不到 → 字段置 null + uncertainty 记录；contract_fill
   报告中列出 mapped/unmapped 全表。

## 运行位置

assemble_result.py 之后、validate_output.py 之前；Agent 在第 12 步复核
unmapped 与 content_preview 后可 override 重跑。幂等。

## 为什么这能提分

“结果可核验性 5 分 + 结果完整性 5 分 + 任务完成度”均依赖交付物与契约的
逐字段对应。v1 的别名兜底使多个字段指向同一 outputs 汇总，评审无法逐字段
核验；精确填充后每个字段自带哈希、字节数、摘要与预览，可核验性直接落地。
