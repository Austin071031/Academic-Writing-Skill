# 异常输入与处置（edge cases）

| 场景 | 识别 | 处置 |
|-|-|-|
| 材料缺失 | brief.material_count=0 且 case.json 无内嵌正文 | result.json 记 status=failed（无米之炊）或按题面只处理内嵌文本；uncertainty 写明缺失清单 |
| 编码混乱 | inspect 的 encoding_note / mojibake_score>0.01 | 按 gb18030/big5 重试；仍乱码则该文件标注"无法可靠读取"，句子不进润色范围，进 manual_review_required |
| 超长输入 | 源文本分块数 > 预算可处理量 | 按章节优先级（题面指定章节 > 摘要/引言 > 其余）逐块闭环；未处理范围写入 partial 说明 |
| LaTeX 混杂 | 保护片段（$\ldots$、\cite{}、\ref{}） | extract 阶段已保护不断句；润色不改写公式与引用命令；纯公式块（kind=math）不逐句记录 |
| 中英日混排 | 句级 lang 字段 / 日文假名检测 | 按句语言选用对应规则；术语表分别登记；不跨语言套用标点规则 |
| 术语表内部冲突 | provided 与 defined/candidate 同概念多写法 | 案例自带优先；取舍写入 note 与 result.json uncertainty |
| 目标文体不明 | task_profile.register 为空 | 默认期刊论文语域（style_guides.md 通用学术档），assumptions 标注"文体不明，按通用学术处理" |
| 重复运行 | /app/work 已存在 chunks | 复用已有 chunks 做增量修正，不推翻先前决策；脚本确定性重建产物，结论不漂移 |
| 引用格式混杂（[1]、(Author, 2023)、\cite{}） | guard_check 三类分别抽取 | 只核对"集合不变"，不要求统一格式；统一格式仅在任务要求时做，且记 types=formatting |
| 纯问答混入润色要求 | 任务同时有"回答X"与"润色Y" | 两部分分开：先直接回答，再对 Y 走润色流程；互不污染 |
| 改后比原文长出数倍 | assemble 长度比 | 最小编辑原则被破坏的典型信号；回读阶段核查是否整句重写，回退到局部修改 |
| PDF 提取失败/扫描件 | extract_report.json status=failed | 如实标注该材料未处理；不编造其内容；如有 OCR 工具可尝试并注明置信度 |

## 预算兜底顺序（时间或调用数不足时）

1. 已完成块的 chunks 落盘（最重要，产物可复现）。
2. assemble 一次，产出 polished/change_log/result.json（此时 status=partial）。
3. terminology check 与 guard_check 至少各跑一次，critical 写进 uncertainty。
4. 有余力再做回读校验与预览渲染。
