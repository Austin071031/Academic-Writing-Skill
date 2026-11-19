# 保真导出方法说明

## 管线结构

```
修改稿 DOCX
  ├─ font-check   字体清单 + 度量兼容替代建议（显式登记）
  ├─ render       soffice→PDF→PNG（真实渲染，状态留痕）
  ├─ toc-refresh  pdftotext 实测标题页码 → 回填 TOC 域缓存显示值
  │               （域结构保留，Word 可 F9 刷新）
  └─ fidelity     before/after 内容单元级差分（白名单=合法变换）
       → 最终交付 = 回填后 DOCX + 重渲染预览 + 差分报告
```

## 差分维度与判定

- 结构要素（必须零变化）：表格数、图片数、OMML 公式数、脚注/尾注数、
  超链接数、分节数。
- 文本变化：逐段落对比；命中白名单（如术语统一的原词、引用重编号）
  记为 expected_changes，否则记为 changed 供复核。
- `fidelity_breaks` 非空 = 交付阻塞项，必须先修复或如实降级。

## 降级原则

每一步探测依赖（soffice/pdftoppm/pdftotext），缺失即降级并在
render_status.json / toc_report.json 中写明原因。**任何情况下不得生成
声称是预览但实际为占位符的图片**；没有真实渲染就没有预览文件。

## 与其他方向的关系

定点修改纪律（锚定—最小—台账）与诚实 result.json 为通用要求；
本方向聚焦“修改之后，导出不塌”的核验闭环。修订标记（v1）与
引用同步（v2）的产出均可作为本管线的入参。

## 核验清单

1. 最终预览 PDF 由最终 DOCX 渲染产生（时间戳/内容一致）；
2. fidelity_breaks 为空；
3. 字体替换全部显式登记；
4. TOC 页码与 pdftotext 实测一致或在报告中注明降级。
