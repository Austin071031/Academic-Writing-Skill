# CHANGELOG

## v1.4.0（2026-11-23）— 文体指纹换装（首版）

- 核心机制：style_metrics.py 双向度量——profile 生成目标文体画像（五档预设区间），
  compare 对润色前后按同一把尺出 style_report.md，未达标项必须处置或留证。
- 先守恒后风格：命题内容一字不动，风格只改词形/句式/连接/人称；限定词档位分布
  变化逐条在 change_log 留痕。
- 交付 style_report.md 作为"说得像"的可核验证据，与 change_log、术语表、
  result.json 构成完整闭环。

- 提交：playground attempt 99596（product-arena-02-7051d92d，写作02｜学术语言润色）
