# 阶段5：生成 PDF 并推送

报告保存后，必须执行以下步骤。

步骤1：生成 PDF

```bash
mkdir -p ~/.openclaw/media/a-share-review/{DATE}
python3 {SKILL_DIR}/scripts/report_to_image.py \
  /tmp/a-share-review/{DATE}/report.md \
  --format pdf \
  --output ~/.openclaw/media/a-share-review/{DATE}/report.pdf
```

步骤2：发送 Telegram 文档

```bash
python3 {SKILL_DIR}/scripts/send_telegram_file.py \
  ~/.openclaw/media/a-share-review/{DATE}/report.pdf \
  --method document \
  --caption "A股复盘报告 {DATE}"
```

说明：使用 `sendDocument` 方式，Telegram 可直接预览并翻页。
脚本会从 `~/.openclaw/openclaw.json` 读取 botToken 与 chat_id。

发送失败 fallback：直接将 `/tmp/a-share-review/{DATE}/report.md` 文本返回给用户。
