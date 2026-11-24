# CHANGELOG

## v1.1.0（2026-11-24）快轨版

- **唯一机制增量**（父版 v1.0.1，attempt 89250，63 分）：新增
  `scripts/run_pipeline.py` 一命令全流水线编排器，将 Phase 0-5 六条命令压缩为
  一条命令，解决回放中"流程过长→主产物不完整"的失分点：
  - 自动选择稿件/文献库候选并解析；自动从稿件 reference_list 段抽取文末列表基准
    （reference_list.json）。
  - 任务书编辑指令保守自动派生：仅处理带编号或唯一题名定位的"删除/插入"指令，
    逐条写 evidence_map（含任务书出处句）；定位不唯一一律进 manual_confirmations，不猜。
  - 悬空引用自动处置：移除指向被删条目的正文标记并全程留痕 change_log/uncertainty。
  - change_log 从引擎 mapping 自动生成；audit→assemble→validate→preview 一键收尾。
  - 支持 `--stage prep|finish` 两阶段人工覆盖（检测到人工 edit_ops.json 时跳过自动派生）。
- 引擎 `renumber_plan.py` 与共享核心脚本与父版逐字节一致，未改动判据。
- SKILL.md 重写为快轨用法（一条命令 + 2 步收尾 + 人工覆盖入口）。

## v2.0.0（2026-11-19）

- 首个发布：编号连锁更新引擎 `renumber_plan.py`。
  - 输入 `work/edit_ops.json`（delete / reorder / insert_existing / merge 四种语义化
    操作；ref_id 支持 R00X 条目身份与纯数字当前序号两种定位）。
  - 编译 旧号→新号 mapping（删除=null，含 insert_existing 拉入条目的恒等映射），
    驱动共享 `cite_engine renumber` 连锁重排正文全部 kind 段落（区间 [n-m] 自动压缩）。
  - 重建文末列表（references.md/json，每条保留 source_file+source_index 出处）；
    Agent 可手工提供 `work/reference_list.json` 作为列表基准与原措辞来源。
  - 悬空引用清单（删除后仍被引用的段落，含 pid/kind/原文标记）+ 不变量终检
    （正文最大编号==列表条数、1..N 无缺口、样式统一），stdout 输出 PASS/FAIL。
  - 著者-出版年模式：不做数字重排，检查列表排序并标注 stale 条目。
- 端到端合成自测通过（删除+调换 PASS；删被引条目 FAIL 并正确报悬空 2 处；
  merge/insert_existing/reference_list 基准/著者-出版年均实测），实测记录见
  `docs/USAGE.md` 附录。
