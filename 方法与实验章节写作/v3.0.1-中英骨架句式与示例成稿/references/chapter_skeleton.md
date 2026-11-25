# 章节骨架与句式库（中英对照，写作时逐句套用，数值处挂〔E#〕）

语言选择：task.md 或材料主体为中文用中文句式，英文用英文句式；拿不准用中文。
**骨架是结构参照，数值一律来自材料，禁止照抄示例数值。**

## 1 方法步骤（Steps）

骨架：总起一句（流程分 N 步）→ 逐步一句（输入→操作→输出）→ 判断条件一句。

- 中："整个流程分为 N 步。第一步，<输入>，经<操作>得到<输出>〔E#〕；第二步，……；
  当<判断条件>满足时停止/进入下一步〔E#〕。"
- En: "The pipeline consists of N stages. First, <input> is <operation> to obtain <output>〔E#〕;
  second, … . The iteration stops once <criterion> is met〔E#〕."
- 禁：把多步压成一句（"随后进行训练和评测"）；用"并/随后"连写三个以上动作。

## 2 实验设置（Setup）

骨架：硬件句 → 软件/环境句 → 种子与重复句 → 训练/验证/测试分段。

- 中："实验在<机型×数量>上进行〔E#〕；软件环境为<框架+版本>〔E#〕；随机种子固定为<n>〔E#〕，
  每组配置重复<k>次。"
- En: "All experiments run on <hardware>〔E#〕 with <framework version>〔E#〕; the random seed is
  fixed to <n>〔E#〕 and each configuration is repeated <k> times."
- 训练/验证/测试三段必须分开成句；评测条件不得混入训练段。

## 3 参数与来源（Parameters）

骨架：总起（主要超参及来源）→ 参数表 → 取舍说明（若有）。

- 中："主要超参数及其取值见表 1，取值均以<配置文件/日志>为准〔E#〕；<若有取舍>代码默认值为 X，
  实际运行以日志记录的 Y 为准〔E#〕。"
- En: "Table 1 lists the hyper-parameters; all values follow <config/log>〔E#〕."

## 4 数据集与划分（Datasets）

- 中："实验采用<数据集 版本>〔E#〕，共<规模>条；按<比例>随机划分为训练/验证/测试集，
  划分种子为<n>〔E#〕；预处理包括<步骤>〔E#〕。"
- En: "We use <dataset vX>〔E#〕 (<size> samples), randomly split into train/val/test by <ratio>
  with seed <n>〔E#〕; preprocessing consists of <steps>〔E#〕."

## 5 对照实验（Baselines）

- 中："基线为<名称+版本>，与本文方法在相同预算（<预算>〔E#〕）、相同划分与相同评测协议下比较；
  评价指标为<指标>，报告<均值±方差/单次结果>〔E#〕。"
- En: "We compare against <baseline+version> under the same budget〔E#〕, split and protocol;
  metrics are <metrics>, reported as <mean±std / single run>〔E#〕."
- 基线数值缺失时写："基线结果未在材料中给出，已列入附录C追问。" 禁止凭记忆补数。

## 6 可复现清单（Reproduction）

- 中："复现所需代码版本为<commit/tag>；环境为<OS/Python/依赖>；数据获取方式：<URL/校验和/路径>；
  训练命令：`python …`；评测命令：`python …`；随机种子<n>；预计开销<估算>。"
- En: "To reproduce: code at <commit>; environment <os/python/deps>; data from <url/hash>;
  run `python …` for training and `python …` for evaluation with seed <n>."

## 7 限制条件与适用范围（Limitations）

- 中："本方法在<具体条件>下未验证/失效：<场景>；适用范围为<数据域/规模>。"
- En: "The method has not been validated under <condition>: <scenario>; its applicable scope is <domain/scale>."
- 禁："存在一定局限性""未来还有改进空间"类无场景套话。
