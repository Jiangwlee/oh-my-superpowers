# n8n 工作流部署步骤

## 快速部署（推荐新手）

### 1. 打开 n8n UI
```bash
open http://localhost:10003
```

### 2. 获取 API Key（可选，用于自动导入）
- 点击左上角头像 → **Settings**
- 左侧菜单选择 **Credentials**
- 找到 **API Key** 部分
- 点击 **Create new API key**
- 复制生成的密钥（类似 `nsk_xxxxxxxxxxxxxxxx`）

### 3. 导入工作流

#### 方式 A: 手动导入（无需 API Key）
1. 点击右上角 **Settings** → **Import from File**
2. 选择文件：`/home/bruce/Projects/oh-my-superpowers/n8n-workflows/ashare-daily-simple.json`
3. 点击 **Import**
4. 返回 Workflows 页面，找到 "A 股每日数据采集（简化版）"
5. 点击右侧开关按钮激活（ON）

#### 方式 B: 使用 API 导入（需 API Key）
```bash
cd /home/bruce/Projects/oh-my-superpowers

# 设置环境变量
export N8N_API_KEY="你的_api_key_粘贴在这里"

# 执行导入
curl -X POST \
  -H "Authorization: Bearer $N8N_API_KEY" \
  -H "Content-Type: application/json" \
  -d @n8n-workflows/ashare-daily-simple.json \
  http://localhost:10003/rest/workflows
```

### 4. 验证配置

在 n8n 工作流编辑页面检查以下节点：

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

### 5. 测试运行

1. 点击顶部 **Execute Workflow** 按钮
2. 查看右侧 Execution panel
3. 确认流程正常执行

### 6. 监控输出

检查数据是否写入：
```bash
ls -la ~/.ashare-assistant/status/
ls -la ~/.ashare-assistant/logs/
```

成功时应有 `success_YYYY-MM-DD.flag` 文件。

## 常见问题排查

### Q: HTTP Request 失败？
**检查**:
```bash
# 1. task-runner 状态
docker ps --filter name=task_runner

# 2. 网络连通性
docker exec n8n_app wget -qO- http://task_runner:8000/health

# 3. task-runner 日志
docker logs task_runner --tail 50
```

### Q: 工作流不触发？
**检查**:
1. 工作流是否已激活（开关 ON）
2. Cron 时间设置是否正确
3. n8n 容器时区：`docker exec n8n_app env | grep TZ`

### Q: 数据未写入？
**检查**:
```bash
# Volume 挂载
docker inspect n8n_app | grep ashare-assistant

# 权限问题
ls -la ~/.ashare-assistant/data/$(date +%Y-%m-%d)

# 错误日志
cat ~/.ashare-assistant/logs/error_*.log
```

## 下一步

- 参考 `n8n-workflows/README.md` 了解更多最佳实践
- 创建告警通知工作流（钉钉/飞书/Slack）
- 添加性能监控端点

---

**提示**: 建议先使用手动导入方式，确保理解工作流程后再考虑自动化部署。
