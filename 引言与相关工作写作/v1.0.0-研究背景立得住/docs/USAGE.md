# USAGE｜完整调用步骤

本文件与提交版本一致，供 Agent 或作者独立完成一次"引言与相关工作"起草与核对。

## 1. 运行环境

- Python 3.8+ 标准库；Linux 容器；无网络依赖。
- 路径约定（Harbor）：输入 `/input`，工作 `/app/work`，产物 `/app/output`；Skill 位于 `/skills/weekly-skill`。
- 本地试用：把上述路径替换为本地目录即可，脚本参数一致。

## 2. 逐步执行

```bash
S=/skills/weekly-skill/scripts
python3 $S/init_result.py --case /input/case.json --out /app/output
python3 $S/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 $S/parse_manuscript.py <稿件> --work /app/work
python3 $S/parse_library.py <文献库文件...> --work /app/work
python3 $S/parse_notes.py <笔记文件...> --work /app/work
python3 $S/extract_facts.py --work /app/work
```

然后（Agent 判断与写作阶段）：

1. 读 `work/inspection.json`、`work/fact_candidates.jsonl`；
2. 写 `work/evidence_map.json`、`work/draft_intro.md`、`work/draft_rl.md`、
   `work/claim_bindings.jsonl`、`work/version_notes.md`；
3. 引擎核验与构建：

```bash
python3 $S/anti_fluff.py --work /app/work --out /app/output --patterns /skills/weekly-skill/references/anti_fluff_patterns.txt
python3 $S/build_deliverables.py --work /app/work --out /app/output
```

4. 阅读 `output/build_report.json` 与 `output/anti_fluff_audit.md`，最多修复一轮后重跑第 3 步；
5. 收尾：

```bash
python3 $S/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
  --skill "intro-background-grounding v1.0.0" --status success
python3 $S/validate_output.py --out /app/output --expect-status success
python3 $S/render_previews.py --out /app/output
```

## 3. 输入文件解释

| 文件 | 必需 | 说明 |
|---|---|---|
| case.json | 是 | 含 case_id 与 output_contract；assemble 自动回填契约字段 |
| task.md | 是 | 任务书：体裁、语言、引用格式、受众 |
| 稿件（md/txt/tex/docx/pdf） | 强烈建议 | 本文方法/结果/结论——贡献与背景问题的证据源 |
| 文献库（bib/ris/enw/csv/json/GB-T 文本） | 至少其一 | 相关工作转述与引用元数据来源 |
| 阅读笔记（md/txt/json） | 可选 | 他人工作的结论/局限摘录，加快事实锚定 |

## 4. 输出文件解释

| 文件 | 内容 |
|---|---|
| introduction.md | 引言成稿（背景/空白/贡献三组标题；引用编号已注入） |
| related_work.md | 相关工作成稿（分组小节） |
| references.md | GB/T 7714 顺序编码文献表（仅含被引条目，编号连续） |
| evidence_map.json | 证据映射：eid → source/loc/quote/numbers |
| build_report.json | 锚点解析率、绑定命中率、四要素、编号顺序、异常 |
| anti_fluff_audit.md | 空转铺垫命中句、改写建议、锚定比例、verdict |
| result.json | 结构化结果（契约字段 + evidence_map + change_log + uncertainty + exceptions + stats） |
| preview.html | 全部产物的可视化预览 |

## 5. 失败处理与自查

- `validate_output.py` 非零退出：按 FAIL 信息修复（多为绑定句不逐字、编号不连续、文献表缺失）。
- 想看数字是否漂移：比对 evidence_map 的 numbers 与正文数字。
- 想看空白是否成立：对照 anti_fluff_audit 的问题信号与 draft 的空白段。
- 全部脚本幂等：可重复运行；修复后务必重跑 build → assemble → validate 三件套。
