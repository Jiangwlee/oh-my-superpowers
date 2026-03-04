# n8n MCP 配置指南

## 方案一：使用 n8n-mcp 工具（推荐）

### 1. 安装 n8n-mcp

```bash
npm install -g n8n-mcp
```

### 2. 创建 MCP 配置文件

创建 `~/.config/pi/config.json` (或你的 MCP 配置位置):

```json
{
  "mcpServers": {
    "n8n-mcp": {
      "command": "npx",
      "args": ["-y", "n8n-mcp"],
      "env": {
        "MCP_MODE": "stdio",
        "LOG_LEVEL": "error",
        "DISABLE_CONSOLE_OUTPUT": "true",
        "N8N_API_URL": "http://localhost:10003",
        "N8N_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### 3. 获取 n8n API Key

**步骤**:
1. 打开 n8n UI: `open http://localhost:10003`
2. 点击左上角头像 → **Settings**
3. 左侧菜单选择 **Credentials**
4. 找到 **API Key** 部分
5. 点击 **Create new API key**
6. 命名 (如 `task-runner-import`)
7. 复制生成的密钥

### 4. 测试连接

```bash
# 测试 n8n-mcp 是否可用
npx n8n-mcp --test

# 或使用 curl 测试 API
curl -s -X GET \
  -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:10003/rest/workflows | jq '.[] | {name, active}'
```

## 方案二：手动导入（无需 MCP）

如果不想配置 MCP，可以直接在 n8n UI 中导入：

### 步骤

1. **打开 n8n UI**
   ```bash
   open http://localhost:10003
   ```

2. **导入工作流**
   - 点击右上角 **Settings** → **Import from File**
   - 选择文件：`/home/bruce/Projects/oh-my-superpowers/n8n-workflows/ashare-daily-simple.json`
   - 点击 **Import**

3. **激活工作流**
   - 在 Workflows 页面找到 "A 股每日数据采集（简化版）"
   - 点击右侧开关按钮切换为 **ON**

4. **验证配置**
   - 检查工作流中的 HTTP Request 节点 URL: `http://task_runner:8000/ashare/collect`
   - 确认 Cron Trigger 设置：工作日 22:00

## 方案三：使用部署脚本

运行自动部署脚本：

```bash
cd /home/bruce/Projects/oh-my-superpowers

# 设置 API Key
export N8N_API_KEY="your-api-key-here"

# 运行部署脚本
./scripts/deploy-n8n-workflow.sh n8n-workflows/ashare-daily-simple.json
```

## 验证部署成功

```bash
# 1. 检查工作流列表
curl -s -X GET \
  -H "Authorization: Bearer $N8N_API_KEY" \
  http://localhost:10003/rest/workflows | \
  jq '.[] | select(.name | contains("A 股"))'

# 2. 查看执行历史
docker logs n8n_app --tail 50 | grep -i workflow

# 3. 检查输出文件
ls -la ~/.ashare-assistant/status/
ls -la ~/.ashare-assistant/logs/
```

## 常见问题

### Q: MCP 连接失败？
**解决**:
```bash
# 检查 n8n-mcp 是否安装
npx -v

# 测试连接
curl -s http://localhost:10003/health

# 检查环境变量
echo $N8N_API_KEY
echo $N8N_API_URL
```

### Q: API Key 无效？
**解决**:
1. 重新在 n8n UI 创建新的 API Key
2. 确保没有多余的空格
3. 检查 n8n 容器是否正在运行

### Q: 工作流不触发？
**解决**:
1. 确认工作流已激活（开关 ON）
2. 检查 Cron 时间设置
3. 查看 n8n 执行日志：Settings → Execution Logs

---

**建议**: 对于首次部署，推荐使用**方案二（手动导入）**，最简单可靠。
