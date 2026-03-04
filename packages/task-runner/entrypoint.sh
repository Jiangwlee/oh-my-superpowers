#!/bin/sh
set -e

echo "=== task-runner entrypoint ==="

# 先安装 ashare-data（从 volume 读取源码）
if [ -d /install/ashare-data ] && [ -f /install/ashare-data/pyproject.toml ]; then
    echo "Installing ashare-data from /install/ashare-data..."
    pip install --no-cache-dir -e /install/ashare-data 2>&1 | tail -5 || true
else
    echo "Warning: ashare-data volume not found or incomplete"
    # 如果体积没挂载，就装官方包（如果有）
    pip install --no-cache-dir ashare-data 2>&1 | tail -5 || true
fi

# 安装 task-runner 自身（从 volume 读取源码）
if [ -d /install/task-runner ] && [ -f /install/task-runner/pyproject.toml ]; then
    echo "Installing task-runner from /install/task-runner..."
    pip install --no-cache-dir -e /install/task-runner 2>&1 | tail -5 || true
else
    echo "Error: task-runner volume not found"
    exit 1
fi

echo "=== 启动 uvicorn ==="
exec uvicorn task_runner.app:app --host 0.0.0.0 --port 8000
