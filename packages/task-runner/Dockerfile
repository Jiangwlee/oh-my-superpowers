FROM python:3.12-slim

WORKDIR /app

# 安装基础依赖
RUN pip install --no-cache-dir fastapi 'uvicorn[standard]'

# 挂载点（通过 docker-compose volumes）:
#   /install/ashare-data   → packages/ashare-data 源码
#   /install/task-runner   → packages/task-runner 源码
#   /home/bruce/.ashare-assistant → 数据目录（与宿主机相同路径）

# entrypoint 脚本：安装挂载的包后启动 uvicorn
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
