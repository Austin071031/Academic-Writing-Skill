# GB/T 7714—2015 文献类型标识映射表（可复用资源，convert_engine.py 运行时解析）

> 本文件是**数据文件**：`scripts/convert_engine.py` 用简单表格解析读取，不在脚本内硬编码。
> 修改本表即可改变 GB/T 输出的类型标识，无需改代码。内容为规范示例整理。

## 映射表（解析格式：`| entry_type | 标识 |`）

| entry_type | 标识 | 含义 |
|---|---|---|
| journal_article | J | 期刊文章 |
| conference_paper | C | 会议论文集文章 |
| book | M | 专著 |
| book_chapter | M | 专著中析出的章节（析出文献宜标注 [M]//源文献） |
| thesis | D | 学位论文 |
| patent | P | 专利 |
| standard | S | 标准 |
| report | R | 报告/科技报告 |
| newspaper_article | N | 报纸文章 |
| preprint | EB | 电子预印本（按电子资源 EB/OL 处理） |
| misc | EB | 其他/电子资源兜底 |
| dataset | DS | 数据集 |

## 解析规则（与脚本约定）

- 仅解析以 `|` 开头、第一列为小写 entry_type、第二列为 1-4 个大写字母的行。
- 第一列出现 `entry_type` 的表头行被跳过。
- 未命中时引擎退回 `EB` 并在 exceptions.json 记录。

## 载体类型标识（电子资源）

- `[EB/OL]` 联机网络电子公告；`[J/OL]` 网上期刊；`[DB/OL]` 联机数据库。
- 本引擎对无卷期页但有 DOI/URL 的电子条目保留 `[EB]` 并保留 DOI，不臆造载体细化。
