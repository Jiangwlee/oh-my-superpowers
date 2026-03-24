# SOP：标准程序化导出

适用场景：
- 用户说“转成 PDF”
- 用户说“导出 PNG / 图片版”
- 输入是本地 Markdown 文件
- 不强调海报感、卡片感、设计感

## 步骤

1. 检查输入文件存在
2. 运行 `inspect_input.py`
3. 若 `cleanliness=light_dirty`，运行 `normalize_input.py`
4. 若 `cleanliness=semantic_dirty`，停止自动导出，让 Agent 先清理正文
5. 运行 `convert.py`
6. 检查 manifest 的 `files / warnings / errors`
7. 如有需要，保留 HTML 调试

## 推荐命令

```bash
python scripts/convert.py report.md --format pdf --same-dir --stdout-manifest
python scripts/convert.py report.md --format png --same-dir --stdout-manifest
```

## 调试模式

```bash
python scripts/convert.py report.md --format pdf --same-dir --keep-html --keep-clean --stdout-manifest
```