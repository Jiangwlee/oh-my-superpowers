#!/bin/sh
set -e

echo "=== task-runner entrypoint ==="
echo "TZ: ${TZ:-UTC}"
echo "ASHARE_OUTPUT_DIR: ${ASHARE_OUTPUT_DIR:-/home/bruce/.ashare-assistant}"
echo "LOG_LEVEL: ${LOG_LEVEL:-INFO}"

# 检查 ashare_data volume 是否存在
if [ ! -d /usr/local/lib/python3.12/site-packages/ashare_data ] || [ ! -f /usr/local/lib/python3.12/site-packages/ashare_data/__init__.py ]; then
    echo "ERROR: ashare_data not found at site-packages"
    exit 1
fi

# 检查 task-runner volume 是否存在
if [ ! -d /install/task-runner ] || [ ! -f /install/task-runner/pyproject.toml ]; then
    echo "ERROR: task-runner volume not mounted at /install/task-runner"
    ls -la /install/ 2>/dev/null || echo "  (nothing in /install)"
    exit 1
fi

# 安装 task-runner
echo "Installing task-runner..."
pip install --no-cache-dir -e /install/task-runner
echo "✓ task-runner installed"

# 验证
echo "Verifying..."
python -c "import ashare_data; import task_runner; print('✓ Imports OK')"

# 启动 uvicorn
echo "=== 启动 uvicorn ==="
exec uvicorn task_runner.app:app \
  --host 0.0.0.0 \
  --port "${UVICORN_PORT:-8000}" \
  --log-level "${LOG_LEVEL:-info}"
