# transfer-claim-calibration（科研成果转化写作·论断强度校准与论据边界）

把论文/技术报告改写为科普文章、新闻稿、简报或申报材料时，用脚本保证"说得准"：
论断强度与源文证据同级，不把相关写成因果、不把初步结果写成定论、不绝对化、
不翻转否定、不新增源文外结论。

## 用途与适用条件

- 适用：给定科研源文 + 目标受众/文体的转化改写任务，且评审关注论断强度保真。
- 不适用：从头写论文、纯语言润色、引用管理（另有专门 Skill）。

## 安装

目录即 Skill 本体，安装为 `/skills/weekly-skill` 即可。仅依赖 Python3 标准库；
处理 PDF 源文时需环境自带 pdftotext（评测镜像已提供）。

## 快速开始

按 `SKILL.md` Phase 0-5 执行；完整说明见 `docs/USAGE.md`，最小示例见 `examples/minimal_example.md`。
核心两步：`claim_engine.py extract` 抽取源文论断（强度分级 L0-L3 + 因果性），
改写后 `claim_engine.py check` 逐条判定 kept/downgraded/upgraded/negation_flip/missing/new_claim，
critical 必须清零（exit=0）方可交付。

## 边界

- 不生成源文外结论；句级对齐为 2-gram Dice 启发式，疑似漏配可人工复核（见 SKILL.md 异常表）。
- 强度阶梯与判定阈值为工程经验值（见 references/claim_rules.md），不替代人工终审。
