#!/bin/bash
# setup.sh - a-share-review-planner 服务器环境安装脚本
# 支持 Ubuntu 20.04/22.04/24.04（Debian 系）
# 用法: bash setup.sh
set -e

echo "=== a-share-review-planner 依赖安装 ==="

OS=$(uname -s)

if [ "$OS" = "Darwin" ]; then
    echo "[macOS] 检查依赖..."
    # macOS 通常已有 Python3、Node.js（通过 Homebrew），Chrome 需手动安装
    command -v python3 >/dev/null || { echo "❌ 请安装 Python3"; exit 1; }
    command -v node >/dev/null || { echo "❌ 请安装 Node.js 18+: brew install node"; exit 1; }
    command -v curl >/dev/null || { echo "❌ 请安装 curl"; exit 1; }
    [ -f "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ] || \
        echo "⚠️  未找到 Google Chrome，请从 https://www.google.com/chrome/ 安装"
    echo "✅ macOS 依赖检查完成（字体由系统自带 PingFang SC 提供）"
    exit 0
fi

# ── Linux（Debian/Ubuntu）──────────────────────────────────────────────────
echo "[Linux] 更新包列表..."
sudo apt-get update -qq

echo "[1/4] 安装 Python3 + curl..."
sudo apt-get install -y -qq python3 python3-pip curl

echo "[2/4] 安装 Node.js 20..."
if ! command -v node >/dev/null 2>&1; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
else
    echo "  Node.js $(node -v) 已安装，跳过"
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

echo "[可选] 安装 pandoc（Markdown 解析更准确）..."
sudo apt-get install -y -qq pandoc 2>/dev/null || echo "  pandoc 安装失败，将使用内置 fallback"

echo ""
echo "=== 验证安装 ==="
python3 --version
node --version
chromium-browser --version 2>/dev/null || chromium --version 2>/dev/null || echo "⚠️  chromium 未找到"
curl --version | head -1
fc-list | grep -i "Noto.*CJK" | head -3

echo "[创建必要目录]"
mkdir -p ~/.openclaw/media/a-share-review
echo "  ~/.openclaw/media/a-share-review 已创建"

echo ""
echo "✅ 安装完成！"
echo ""
echo "⚠️  注意事项："
echo "  1. Linux 上 Chromium 路径为 /usr/bin/chromium-browser 或 /usr/bin/chromium"
echo "     需要将其加入 screenshot.js 的 CHROME_CANDIDATES 列表"
echo "  2. PDF 生成时 Google Fonts CDN 可替换为本地 Noto CJK 字体（见下方说明）"
echo "  3. 发送 Telegram 消息需要配置 ~/.openclaw/openclaw.json"
