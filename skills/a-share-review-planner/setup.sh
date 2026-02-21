#!/bin/bash
# setup.sh - a-share-review-planner 环境安装脚本
# 支持 Ubuntu 20.04/22.04/24.04（Debian 系）及 macOS
# 用法: bash setup.sh
#
# 依赖摘要：
#   必须：Python 3.10+，Node.js 22+，Google Chrome / Chromium
#   可选：pandoc（有内置 fallback），中文字体（Linux 推荐）
#   零 pip 包：所有 Python 脚本仅使用标准库
#   零 npm 包：screenshot.js 使用 Node.js 内置 WebSocket + fetch
set -e

echo "=== a-share-review-planner 依赖安装 ==="

OS=$(uname -s)

# ── macOS ─────────────────────────────────────────────────────────────────
if [ "$OS" = "Darwin" ]; then
    echo "[macOS] 检查依赖..."

    # Python 3.10+
    if ! command -v python3 >/dev/null 2>&1; then
        echo "❌ 请安装 Python3: brew install python@3.11"; exit 1
    fi
    PY_VER=$(python3 -c "import sys; print(sys.version_info[:2] >= (3,10))")
    if [ "$PY_VER" != "True" ]; then
        echo "❌ Python 3.10+ 是必须的，当前: $(python3 --version)"; exit 1
    fi

    # Node.js 22+（screenshot.js 需要内置 WebSocket，Node 22+ 才稳定支持）
    if ! command -v node >/dev/null 2>&1; then
        echo "❌ 请安装 Node.js 22+: brew install node@22"; exit 1
    fi
    NODE_MAJOR=$(node -e "process.stdout.write(String(process.version.match(/v(\d+)/)[1]))")
    if [ "$NODE_MAJOR" -lt 22 ]; then
        echo "❌ Node.js 22+ 是必须的，当前: $(node -v)（screenshot.js 需要内置 WebSocket）"; exit 1
    fi

    [ -f "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ] || \
        echo "⚠️  未找到 Google Chrome，请从 https://www.google.com/chrome/ 安装"

    echo "✅ macOS 依赖检查完成（字体由系统自带 PingFang SC 提供）"
    echo "  Python: $(python3 --version)"
    echo "  Node.js: $(node -v)"
    exit 0
fi

# ── Linux（Debian/Ubuntu）──────────────────────────────────────────────────
echo "[Linux] 更新包列表..."
sudo apt-get update -qq

echo "[1/4] 安装 Python3 + curl..."
# 注意：不安装 python3-pip，本 skill 零第三方 pip 包
sudo apt-get install -y -qq python3 curl

# Python 版本检查
PY_VER=$(python3 -c "import sys; print(sys.version_info[:2] >= (3,10))")
if [ "$PY_VER" != "True" ]; then
    echo "⚠️  当前 Python $(python3 --version)，建议升级到 3.10+"
fi

echo "[2/4] 安装 Node.js 22（screenshot.js 需要内置 WebSocket + fetch）..."
if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt-get install -y nodejs
else
    NODE_MAJOR=$(node -e "process.stdout.write(String(process.version.match(/v(\d+)/)[1]))")
    if [ "$NODE_MAJOR" -lt 22 ]; then
        echo "  Node.js $(node -v) 版本过低（需要 22+），重新安装..."
        curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
        sudo apt-get install -y nodejs
    else
        echo "  Node.js $(node -v) 已满足要求，跳过"
    fi
fi

echo "[3/4] 安装 Chromium（headless）及 Chrome 运行所需系统库..."
sudo apt-get install -y -qq \
    chromium-browser \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libxkbcommon0 libpango-1.0-0 libpangocairo-1.0-0

# 某些发行版包名不同
if ! command -v chromium-browser >/dev/null 2>&1; then
    sudo apt-get install -y -qq chromium || true
fi

echo "[4/4] 安装中文字体（Noto Sans CJK，替代 Google Fonts CDN）..."
sudo apt-get install -y -qq fonts-noto-cjk
# 刷新字体缓存
fc-cache -fv >/dev/null 2>&1

echo "[可选] 安装 pandoc（Markdown 解析更准确，有内置 fallback）..."
sudo apt-get install -y -qq pandoc 2>/dev/null || echo "  pandoc 安装失败，将使用内置 fallback"

echo "[创建必要目录]"
mkdir -p ~/.openclaw/media/a-share-review
echo "  ~/.openclaw/media/a-share-review 已创建"

echo ""
echo "=== 验证安装 ==="
python3 --version
node --version
chromium-browser --version 2>/dev/null || chromium --version 2>/dev/null || echo "⚠️  chromium 未找到"
fc-list | grep -i "Noto.*CJK" | head -3

echo ""
echo "✅ 安装完成！"
echo ""
echo "⚠️  配置提示："
echo "  1. 发送 Telegram 消息需要配置 ~/.openclaw/openclaw.json（botToken + allowFrom）"
echo "  2. 使用账户持仓数据需配置 ~/.openclaw/jvquant.json（见 references/commands.md）"
echo "  3. Linux Chromium 路径已内置于 screenshot.js CHROME_CANDIDATES 列表"
