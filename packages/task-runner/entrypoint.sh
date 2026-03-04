#!/bin/sh
set -e

echo "=== task-runner entrypoint ==="

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

echo "=== 启动 uvicorn ==="
exec uvicorn task_runner.app:app --host 0.0.0.0 --port 8000
