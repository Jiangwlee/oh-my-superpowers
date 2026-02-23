# 字号规格（参考）

本文件用于需要手调渲染尺寸时参考。默认仍建议使用 `--font-size medium`。

## 报告链（HTML -> PNG/PDF）

- `small`: 24px
- `medium`: 28px
- `large`: 32px

说明：

- 表格/代码字号会按正文缩放（约 0.8x）
- `large` 会略降低行高以控制分页

## LLM SVG 路径（自由 SVG -> PNG）

建议下限（手机可读性）：

- 正文：`>= 40px`
- Meta/Caption：`>= 28px`
- 标题：`60-72px`（可按版式上调）

排版经验值：

- 行间距 `>= 字号 x 1.5`
- 段落间距 `>= 字号 x 0.5`
- CJK 字宽约 `1.0 x 字号`
- ASCII 字宽约 `0.6 x 字号`

## 程序化路径说明

本 skill 已移除程序化 SVG 卡片模板路径；程序化输出统一走 HTML -> PNG/PDF。
