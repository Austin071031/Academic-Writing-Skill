## 通用异常处置（所有方向共用）

| 情形 | 处置 |
|-|-|
| 材料文件缺失或不可读 | 记入 exceptions；相关论断标 unsupported 或 out_of_scope；result.json status 降档 |
| PDF 转换失败（扫描版/加密/损坏） | 在 text_manifest.json 记 failed 与原错误；该文档全部摘录标 needs_ocr 或 exclusion_reason，不臆造内容 |
| 仅有摘要、无全文 | 摘录 doc_type 记 abstract_only；摘要性论断强度上限 C；所有依据摘要的表述必须写"摘要显示"而非"原文证明" |
| 原文与摘要矛盾 | 以全文为准；矛盾本身记入 uncertainty 与 change_log，成稿处加限定语并指向证据表 |
| 证据相互冲突 | 双方证据都登记（support_type=conflicting）；成稿并陈双方并加限定语；不得只取有利一方 |
| 材料不足以下任何结论 | 论断标 unsupported，写入 open_questions（人工确认项），不补造事实 |
| output_contract 字段语义不明 | 按最保守解释填写并在 assumptions 说明；字段名一个不改 |
| 单次响应接近 16384 token 上限 | 分片写文件（每次追加一段），禁止一次输出整份大表 |
| 预算将尽（>56 次请求或 >800 秒） | 立即跑 validate_output.py，把当前最优产物定格为 result.json，status 如实标 partial |
| 需要联网才能完成的核验 | 不伪造联网结果；给可回查路径（DOI/Crossref/出版社检索式）并标 offline_unverified |

## 方向专属注意

- 摘录类：原文为扫描件且无 OCR 时，该文档证据全部标 needs_ocr，不得凭题名臆造摘录；
- 关联类：案例未提供证据库时，先从材料建立 evidence.csv 再匹配；匹配不到就是 unsupported；
- 引用类：参考文献表与文内引用体系不一致（如作者-年 vs 编号混用）时，两种体系分别建列，不强行合并；
- 强度类：材料未报告样本量时 sample_size 记 unknown，按保守口径降级；
- 不确定性类：题面要求“保留作者确定性”的审稿回复场景，限定改写只针对超出证据的部分，不移除作者明确表态。
