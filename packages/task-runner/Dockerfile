FROM python:3.12-slim

WORKDIR /app

# 安装基础依赖 + rich（watchlist_monitor 依赖）
RUN pip install --no-cache-dir fastapi 'uvicorn[standard]' rich

# 启动脚本
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
