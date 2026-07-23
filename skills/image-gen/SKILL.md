---
name: image-gen
description: >-
  Generate images from text prompts: illustrations, icons, posters, logos,
  concept art, or article/slide artwork. Use when the user asks to 生成图片,
  画一张图, 配图, 做个 icon/logo/海报/插画, generate/create/draw an image.
  Do NOT use for editing existing images, screenshots, charts from data, or
  HTML/SVG mockups.
---

# Image Gen

通过已登录 ChatGPT 的本机 Chrome 生成图像。生成一张图约 60–120 秒。

## 前置条件

Chrome 以 CDP 调试模式运行且已登录 chatgpt.com。不确定时先探活：

```bash
omp web-operator ensure
```

失败时运行 `omp web-operator up` 启动浏览器；提示未登录时让用户在 Chrome 中登录 chatgpt.com 后重试。

## 单张生成（默认路径）

```bash
omp web-operator generate-image chatgpt "<prompt>" --out <path.png> --json
```

- `--out` 省略时保存到 `~/Downloads/chatgpt-image-<timestamp>.png`
- `--json` 返回结构化结果（path/bytes/width/height），Agent 调用时始终加上
- `--timeout <sec>` 默认 180；`--overwrite` 允许覆盖已有文件
- prompt 用英文描述通常效果更好；把用户的风格要求（扁平/写实/像素风等）写进 prompt

## 批量 / 排队生成（多张图或多个调用方）

先起服务（常驻，起一次即可）：

```bash
omp web-operator image-serve --port 8320
```

再通过 HTTP 提交与跟踪：

```bash
curl -s -X POST localhost:8320/jobs -H 'Content-Type: application/json' \
  -d '{"prompt": "<prompt>"}'                    # → {job_id, position, queue_length}
curl -s localhost:8320/jobs/<job_id>             # 状态与排队位置
curl -s -X DELETE localhost:8320/jobs/<job_id>   # 取消
curl -s localhost:8320/jobs/<job_id>/image -o out.png
```

任务串行执行；`position` 为前面等待的任务数。

## 失败处理

| 错误信息 | 下一步 |
|----------|--------|
| `not signed in` | 让用户在 Chrome 登录 chatgpt.com 后重试 |
| `timed out waiting for ChatGPT image composer` / `Content failed to load` | 页面加载失败，直接重试一次 |
| `timed out waiting for generated image` | 提高 `--timeout` 重试 |
| CDP 连接失败 | `omp web-operator up` 后重试 |
