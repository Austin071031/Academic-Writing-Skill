# 分句级编辑策略手册（editing playbook）

适用对象：执行逐句润色的 Agent。原则：**先判该不该改，再决定怎么改**。每条策略给出
判定信号、改法、与反例（掩盖式改法）。所有改法以不改变句子承载的信息为限。

## 0. 决策顺序（每句过一遍）

1. 有没有硬错误（语法/句法/搭配/标点/拼写）？→ 有：改，类型记入 types。
2. 有没有术语/缩写不一致？→ 对照术语表改，类型 `terminology`/`abbreviation`。
3. 有没有语域问题（口语化、宣传化、人称误用、绝对化）？→ 按目标文体改，类型 `register`。
4. 有没有冗余或逻辑连接问题？→ 改动是否让信息更清楚而非只是"不同"？是：改，类型
   `redundancy`/`logic`/`clarity`。
5. 以上皆无 → keep，reason 写明保留依据。

**最小编辑原则**：宁可少改。把"作者写得一般但没错"改成"另一种写法"不是润色，是改写，
会破坏作者声音并引入漂移风险。

## 1. grammar 语法

- 主谓一致：*The results of the experiment shows* → *show*（主语是 results）。
- 时态：方法/实验过程用过去时；普遍事实、结论表述用现在时；*has been shown* 类完成时
  按原文时间关系保留。
- 语态：中文"被"字句并非都错；"被广泛研究"改"受到广泛研究"属搭配自然化，类型记
  `collocation` 更贴切。
- 冠词/介词（英文）：a accuracy → an accuracy；depends of → depends on。
- 单复数：achieve a accuracy → achieve an accuracy of 95.2%；data 作复数（依目标期刊惯例）。

## 2. syntax 句法

- 悬垂修饰：*As shown in Fig. 2, we observe that...* → *Figure 2 shows that...* 或
  *As shown in Fig. 2, the curve exhibits...*（让主句主语成为被修饰对象）。
- 中文长定语堆叠：拆为两句或改"的"字链为短句。
- 主语残缺/偷换：补出主语或调整分句顺序。

## 3. collocation 搭配

- 动宾：提高水平（可）/ 提高质量（可）；*raise an improvement*（不可）。
- 形名：*significant improvement*（可）/*obvious enhancement*（视语境）。
- 中文动词冗余："进行了验证"→"完成验证"或"验证"（视文体）；记 `redundancy` 亦可，择一即可。

## 4. punctuation 标点

- 中文正文用全角标点；英文句点后单空格；列举末项前逗号依文体（牛津逗号按目标期刊）。
- 分号连接的两分句必须有独立完整结构，否则改句号或连接词。
- 中英文标点不混用（中文句中夹英文术语仍用中文标点）。

## 5. long-sentence 长句切分

- 触发：一句含 ≥3 个分句且层次不清；关系代词链过长；插入语嵌套。
- 改法：按逻辑单元（背景-方法-结果）切为 2–3 句，保留原连接关系词（because/因此/从而）
  使因果链不变。**切分后数值、引用、限定词必须原样落位**。

## 6. terminology / abbreviation 术语与缩写

- 同一概念只留首选写法；术语表之外的新写法不得在润色中引入（除非在补缩写全称）。
- 缩写首次出现：全称（abbreviation, ABBR）或中文全称（ABBR）；之后一律用缩写。
- 大小写与连字符按术语表（如 *deep learning* 小写、*COVID-19* 连字符），不凭习惯。

## 7. register 语域语气（按文体，详见 style_guides.md）

- 去口语化：但是→然而；比如→例如；做了实验→开展了实验。
- 去宣传化：*very excellent* → *effective*；*completely solves* → *addresses*；
  "国际领先""首次"类绝对化表述若无材料支撑必须降级并记入 reason。
- 人称：期刊论文方法与结果部分少用 *We*，可用 *we*（视期刊）但避免 *I*；中文用"本文/本研究"。

## 8. redundancy / logic / clarity

- 冗余：*in order to* → *to*；*due to the fact that* → *because*；"值得注意的是"类套话
  每段至多一次，无信息则删。
- 逻辑连接词：*therefore/however* 须有真实逻辑关系支撑；删除不改变逻辑的填充词。
- 清晰度：指代不明时重复名词；*this/that* 悬空时补出先行词。

## 9. 中英文表达质量专项

- 中式英语：名词化堆叠（*the realization of the improvement of* → *improving*）；
  弱动词（*make an analysis of* → *analyze*）；*there be* 滥用；主语与信息重心重排
  （中文"本文提出了…并验证了…"英译宜用 *We propose ... and validate ...*，主语落到执行者）。
- 直译腔：按目标语习惯重组语序，不逐字对应；回译校验确认语义未偏。
- 冗余连接词：*Moreover/Furthermore/In addition* 一段一个足够；中文"此外/另外"同理。

## 10. 反例（这些做法违反本 Skill）

- 整段重写后不提供逐句对照（不讲得清）。
- "可能"改"有望"、"相关"改"导致"（改动限定强度或因果性质）。
- 把 *approximately 15%* 顺手写成 *15%*，或把 95.2% 改成 95.5%（改数据）。
- 为"流畅"删掉否定词或条件从句（改变命题真值）。
- 用同义词替换术语表内的受控术语（引入漂移）。
