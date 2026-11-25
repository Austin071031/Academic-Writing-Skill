# CHANGELOG

## v2.0.1（2026-11-25）

- **唯一机制增量**（父版 v1.0.1-编号连锁更新，attempt 89250，63 分）：六阶段压缩为 prep/edit_ops/finish 三步；Agent 的 edit_ops 判断完整保留（v1.1.0 全自动版 50 分证明去掉判断会降分），悬空自动处置保留为兜底，机械环节全部脚本化。
- 新增 `scripts/run_pipeline.py` 编排器；引擎与共享核心判据与父版一致，未改动。
- SKILL.md 重写为三步/单命令快轨流程；docs/USAGE.md 增补快轨说明。


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
