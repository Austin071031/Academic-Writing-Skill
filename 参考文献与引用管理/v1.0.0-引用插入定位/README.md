# citation-placement-skill（v1.0.0｜引用插入与定位 — 挂得对）

论断级引用定位 Skill：Agent 依据 rubric 识别稿件中**需要来源支撑的论断句**并选择插入位置，
确定性引擎负责把引用标记插到**论断句末（而非段末）**、按首次出现顺序全局重排编号 1..N、
生成按引用顺序排列的参考文献表，并审计"段末集中堆放引用"等错放模式。

## 用途

- 给无引用/引用混乱的学术稿件插入规范引用（GB/T 7714 顺序编码制、著者-出版年、APA7、Vancouver）。
- 修复"段末堆放引用、编号与文献表不同步、一句多引写成相邻标记"等常见缺陷。
- 定位失败诚实跳过（记 exceptions），绝不臆造插入位置，绝不臆造文献。

## 安装

将本目录整体安装为 `/skills/weekly-skill` 即可；仅依赖 Python 3 标准库。

## 快速开始

```bash
python3 scripts/init_result.py --case /input/case.json --out /app/output
python3 scripts/inspect_case.py --case /input/case.json --task /input/task.md --input-dir /input --work /app/work
python3 scripts/parse_manuscript.py /input/<稿件> --work /app/work
python3 scripts/parse_library.py /input/<文献库...> --work /app/work
# Agent 按 references/claim_rubric.md 写 work/citation_decisions.jsonl
python3 scripts/place_citations.py --decisions /app/work/citation_decisions.jsonl \
  --manuscript /app/work/manuscript.json --library /app/work/library.json \
  --work /app/work --out /app/output --style gbt2015_numeric --form auto
python3 scripts/assemble_result.py --work /app/work --out /app/output --case /input/case.json \
  --skill "citation-placement-skill v1.0.0" --status success
python3 scripts/validate_output.py --out /app/output --work /app/work --expect-status success
python3 scripts/render_previews.py --out /app/output --work /app/work
```

## 目录

- `SKILL.md` — 触发条件、Phase 0-5 流程、红线、异常表、预算兜底
- `scripts/` — 共享核心 8 脚本 + `place_citations.py`（专属引擎）
- `references/` — 论断判定 rubric、位置规则、worked example、失败模式
- `evaluation/` — 100 分制自查表、合成测试文本
- `docs/USAGE.md` — 完整步骤与自查方法（含合成案例实测记录）
- `examples/minimal_example.md` — 最小输入输出示意

## 边界

- 不做文献去重（v1.0.2）、编号连锁更新（v1.0.1）、来源逐条核验（v1.0.4）。
- sentence 定位要求逐字子串（三级容错）；完全改写过的句子会进入 exceptions 而非猜位置。
- 文献库为空或全部解析失败时交付 partial，不臆造引用。
