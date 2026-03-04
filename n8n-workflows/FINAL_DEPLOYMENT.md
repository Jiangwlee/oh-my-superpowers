# 🎯 n8n 工作流最终部署指南

## 当前状态

- ✅ task-runner 容器运行正常
- ✅ HTTP 端点测试通过 (`http://task_runner:8000/health`)
- ✅ 工作流 JSON 文件准备就绪
- ⚠️ n8n API 认证配置需要手动处理

## 推荐方案：手动导入（最简单可靠）

### 步骤 1: 打开 n8n UI

```bash
open http://localhost:10003
```

### 步骤 2: 导入工作流

1. 点击左上角头像 → **Settings**
2. 左侧菜单选择 **Workflows**
3. 点击右上角 **Import from File**
4. 选择文件：
   ```
   /home/bruce/Projects/oh-my-superpowers/n8n-workflows/ashare-daily-simple.json
   ```
5. 点击 **Import**

### 步骤 3: 激活工作流

1. 在 Workflows 页面找到 "A 股每日数据采集（简化版）"
2. 点击右侧开关按钮切换为 **ON** (绿色)

### 步骤 4: 验证配置

检查工作流中的节点配置：

#### Cron Trigger 节点
- ✅ Days: Mon, Tue, Wed, Thu, Fri
- ✅ Time: 22:00-22:59 (Beijing time)

#### HTTP Request to task-runner 节点
- ✅ Method: POST
- ✅ URL: `http://task_runner:8000/ashare/collect`
- ✅ Timeout: 600000ms (10 分钟)
- ✅ Retry on Fail: ✅ Enabled
- ✅ Max Tries: 3
- ✅ Wait Between Tries: 300000ms (5 分钟)

### 步骤 5: 测试运行

1. 点击顶部 **Execute Workflow** 按钮
2. 查看右侧 Execution panel
3. 确认流程正常执行

### 步骤 6: 监控输出

检查数据是否写入：

```bash
ls -la ~/.ashare-assistant/status/
ls -la ~/.ashare-assistant/logs/
```

成功时应有 `success_YYYY-MM-DD.flag` 文件。

## 自动导入方案（如需）

如果必须使用 API 导入，需要先获取有效的 API Key：

### 方法 A: 创建新的 API Key

1. 打开 n8n UI: `http://localhost:10003`
2. 点击头像 → **Settings**
3. 左侧菜单 **Credentials**
4. 找到 **API Key** 部分
5. 点击 **Create new API key**
6. 命名（如 `task-runner-import`）
7. 复制生成的密钥

### 方法 B: 使用现有 JWT Token

如果环境变量中已有 `N8N_API_KEY`，尝试以下命令：

```bash
export N8N_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-N8N-API-KEY: $N8N_API_KEY" \
  -d @/home/bruce/Projects/oh-my-superpowers/n8n-workflows/ashare-daily-simple.json \
  http://localhost:10003/rest/workflows
```

如果返回 `Unauthorized`，说明该 token 无效，请使用方法 A 创建新的。

## 验证清单

导入并激活后，请确认：

- [ ] 工作流在 Workflows 页面可见
- [ ] 工作流状态为 **ON**（已激活）
- [ ] Cron Trigger 设置为：工作日 22:00-22:59
- [ ] HTTP Request URL: `http://task_runner:8000/ashare/collect`
- [ ] Retry on Fail: Enabled, Max Tries: 3

## 常见问题

### Q: 无法打开 n8n UI？
**解决**:
```bash
docker ps --filter name=n8n_app
docker logs n8n_app --tail 50
```

### Q: HTTP Request 失败？
**解决**:
```bash
# 检查 task-runner
docker ps --filter name=task_runner
docker logs task_runner --tail 50

# 测试连通性
docker exec n8n_app wget -qO- http://task_runner:8000/health
```

### Q: 工作流不触发？
**解决**:
1. 确认工作流已激活（开关 ON）
2. 检查 Cron 时间设置
3. 查看 n8n 执行日志：Settings → Execution Logs

### Q: 数据未写入？
**解决**:
```bash
# 检查 volume 挂载
docker inspect n8n_app | grep ashare-assistant

# 检查权限
ls -la ~/.ashare-assistant/data/$(date +%Y-%m-%d)

# 查看错误日志
cat ~/.ashare-assistant/logs/error_*.log
```

## 下一步

1. **等待定时触发**: 北京时间每天 22:00 自动执行
2. **监控执行**: Settings → Execution Logs
3. **添加告警**: 创建工作流分支发送钉钉/飞书通知
4. **性能优化**: 添加 `/metrics` 端点和 Prometheus 监控

---

**提示**: 对于首次部署，强烈推荐使用**手动导入**方式，最简单且无需担心认证问题。

**祝部署顺利！🚀**
