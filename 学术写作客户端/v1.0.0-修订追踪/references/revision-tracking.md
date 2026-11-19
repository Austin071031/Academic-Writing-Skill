# 修订追踪方法说明

## 方法

修订追踪方向解决两个基础 Agent 真实失败模式：

1. **交付一段游离文字**：基础 Agent 常输出“改写后的段落文本”，无法回填进
   稿件，作者仍需手工粘贴、对位、核对。本 Skill 的修订直接在 DOCX 的 XML 层
   落地（`w:ins`/`w:del`），Word、WPS、LibreOffice 打开修订稿即可逐条接受或
   拒绝，无需任何手工对位。
2. **改动无法复核**：基础 Agent 很少说明改了哪里、依据是什么。本 Skill 的
   `changes.json` 台账为每条改动记录：指令编号、目标位置（段落号+锚句）、
   原文、改后、依据、状态、出现次数。台账与文档内修订标记一一对应
   （`docxkit.py revisions` 可复核数量一致）。

## 修订粒度纪律

- 措辞层（术语、单句）→ 单条 tracked_replace；
- 结构层（删句、并段）→ delete / replace，保留段内其余内容原样；
- 新增内容 → `insert_after` 插入同样式段落，内容整体包在 `w:ins` 中；
- 核对类指令 → `note`，只记录核对结论，不产生修订（防止为改而改）。

## OOXML 实现要点（纯标准库）

- 跨 run 替换：先拼接段落内全部 `w:t` 定位子串，再把替换摊回各 run，
  保留每个 run 的格式属性；祖先链遇到域（`w:fldChar`/`w:instrText`）不进入，
  遇到 `w:hyperlink` 仍可写普通文本但不写域指令。
- 修订元素带 `w:author` 与 `w:date`，作者侧可筛选本 Skill 的修订。
- 接受 = 提升 `w:ins` 子节点并移除 `w:del`；拒绝 = 反向恢复；两者均由
  `docxkit.accept_all/reject_all` 完成，拒绝稿应与原稿内容一致
  （用 `audit_diff.py` 段落对比可验证）。
- 文件保存仅重写 `word/document.xml` 一个部件，其余部件（styles、numbering、
  字体表、关系）原字节写回，杜绝 OPC 关系损坏。

## 核验清单

1. `changes.json.counts` 与 `docxkit.py revisions` 解析数一致；
2. `audit_diff.fidelity_breaks` 为空（结构性要素零变化）；
3. `rejected.docx` 与 `/app/work/originals` 原稿段落级一致；
4. result.json `missing_fields` 为空。
