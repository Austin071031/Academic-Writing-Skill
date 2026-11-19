# 著者-出版年模式说明

## 为什么不做数字重排

著者-出版年（author-year / GB/T 7714 著者-出版年 / APA）稿件的正文标记是
`(张三, 2019)` 形式，**不携带列表序号**。列表的物理顺序只影响排版与查找，不存在
"正文编号与列表错位"这一类错误；对正文做"重排"既无对象也会破坏标记。因此本 Skill
在该模式下只做**列表维护体检**：

1. **排序检查**：列表是否按第一作者升序（不区分大小写）。未排序时在报告中给出
   `list_sorted_by_first_author: false`，建议 Agent 按任务书确认目标排序（有的期刊
   按引用顺序、有的按字母序），不擅自重排。
2. **stale 标注**：缺 `year` 或 `authors` 的条目排序键不可靠，逐条列出
   `{id, reason, source_file, source_index}`。
3. **删除/合并语义**：author-year 下的 delete/merge 只影响列表成员；引擎照常执行
   edit_ops 并重建列表，但正文标记不动。删除后无需悬空检测（正文没有编号可悬空），
   但 Agent 应检查正文是否仍有 `(作者, 年)` 指向被删条目——这是**语义审校**，引擎
   给出条目级清单辅助，不做正文改写。

## 触发判定

`--style auto`（默认）时，引擎依次看：
1. `work/manuscript.json` 的 `styles_detected`：含 `numeric` → 数字模式；
   仅 `author_year` → 本模式；
2. 若 styles_detected 为空（解析失败退化），嗅探非 reference_list 段落的 cite_marks。

任务书或 case.json 显式声明样式时，Agent 用 `--style gbt2015_author` / `--style apa7`
显式指定，跳过嗅探。

## 报告差异

数字模式的报告含映射表/悬空清单/四项终检；author-year 模式的报告替换为：

```markdown
## 著者-出版年检查
- 列表按第一作者排序: 是/否（建议人工确认排序）
- stale 条目: N 条
  - R004 (refs.bib#4): 缺 year 或 authors，排序键不可靠
> 说明: 著者-出版年稿件的引用不携带编号，删除/调序只需维护文末列表；
```

PASS 依据：`list_sorted_by_first_author == true` 且 stale 清单已完整列出
（stale 本身不判 FAIL——它是"需人工确认"信号，如实呈现即达标）。
