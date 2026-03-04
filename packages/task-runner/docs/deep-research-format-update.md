# Deep Research API 格式参数更新

## 修改概述

为 `/ashare/deep-research/data` 接口添加 `format` 参数，支持返回 JSON 或 Markdown 格式的深研数据。

## 修改内容

### 1. ashare-data 模块 (`ashare_data/deep_research.py`)

新增功能：
- `_escape_markdown(text)` - 转义 Markdown 特殊字符（主要是 `|`）
- `format_deep_research_to_markdown(code, name, raw_em, raw_tgb, last_collected_at)` - 将原始 JSON 数据转换为 Markdown 格式

Markdown 输出包含：
- **股票信息**：名称、代码、采集时间
- **股票标签**：淘股吧标签列表（无序列表）
- **东方财富股吧**：最新帖子列表（有序列表，最多 20 条）
- **淘股吧**：讨论贴表格（最多 20 条，内容摘要前 50 字）

### 2. task-runner 模块 (`task_runner/routers/deep_research.py`)

修改内容：
- `_run_load_data()` 函数新增 `format` 参数（默认 `"json"`）
- `get_data()` 端点新增 `format` Query 参数，支持 `json` 和 `markdown`
- 添加格式验证逻辑，无效格式返回错误

### 3. 测试文件 (`tests/test_deep_research_endpoints.py`)

新增测试用例：
- `test_data_found_json` - 测试默认 JSON 格式
- `test_data_found_markdown` - 测试 Markdown 格式
- `test_data_invalid_format` - 测试无效格式参数

### 4. 文档 (`docs/deep-research-api.md`)

新增 API 使用指南，包含：
- 请求参数说明
- 响应格式示例
- 错误响应说明
- cURL 和 Python 使用示例

## API 调用示例

```bash
# JSON 格式（默认）
curl "http://localhost:8000/ashare/deep-research/data?code=002050"

# Markdown 格式
curl "http://localhost:8000/ashare/deep-research/data?code=002050&format=markdown"
```

## 向后兼容性

- 默认 `format=json`，保持向后兼容
- 现有调用无需修改

## 测试状态

✅ 所有单元测试通过（17/17）
✅ 语法检查通过
✅ Markdown 转换功能验证通过

## 注意事项

1. Markdown 格式只保留核心信息，不适用于需要完整数据的场景
2. 内容摘要是前 50 个字符，超过部分用 `...` 截断
3. 特殊字符会自动转义，防止破坏 Markdown 格式
4. 帖子数量限制为最多 20 条，避免响应过大
