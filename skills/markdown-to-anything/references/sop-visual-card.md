# SOP：高质量视觉图

适用场景：
- 高质量图片
- 卡片风格
- 海报风格
- 好看一点
- 设计感

## 步骤

1. Agent 阅读 Markdown
2. Agent 提炼成适合视觉呈现的内容
3. 生成 SVG 或 HTML 视觉稿
4. 调用截图后端输出 PNG
5. 校验产物

## 推荐命令

```bash
node scripts/screenshot.js --png /tmp/card_llm.svg /tmp/card_llm.png 3 1080 0
python scripts/validate_output.py /tmp/card_llm.png --json
```

## 最小约束

- SVG 根元素必须带 `xmlns="http://www.w3.org/2000/svg"`
- 默认画布 `1080x1920`
- 正文字号建议 `>= 40px`
- meta 字号建议 `>= 28px`

## 说明

当前 `convert.py --mode card` 还未实现。
高质量视觉图暂时按 `SKILL.md` 的 Agent + SVG + screenshot SOP 执行。