#!/bin/bash
# setup.sh - ashare-assistant 环境安装脚本
# 支持：macOS、Ubuntu/Debian（apt）、RHEL/CentOS/Rocky/AlmaLinux/Fedora（dnf/yum）
# 用法: bash setup.sh
#
# 依赖摘要：
#   必须：Python 3.10+
#   可选：Node.js 22+，Google Chrome / Chromium（供其他渲染类技能使用）
#   可选：pandoc（有内置 fallback），中文字体（Linux 推荐）
#   说明：本 skill 本身不负责 PDF/PNG 渲染；Node/Chrome 仅供渲染类技能预装
#         数据采集均使用标准库 urllib，无需额外 pip 包
set -e

echo "=== ashare-assistant 依赖安装 ==="

# ── 检测发行版族 ────────────────────────────────────────────────────────────
detect_distro() {
    if [ "$(uname -s)" = "Darwin" ]; then
        echo "macos"
    elif command -v apt-get >/dev/null 2>&1; then
        echo "debian"
    elif command -v dnf >/dev/null 2>&1; then
        echo "redhat_dnf"
    elif command -v yum >/dev/null 2>&1; then
        echo "redhat_yum"
    else
        echo "unknown"
    fi
}

# ── 共用：Node.js 版本检查与安装 ────────────────────────────────────────────
install_nodejs_22() {
    local mgr="$1"  # "apt" | "dnf" | "yum"
    if command -v node >/dev/null 2>&1; then
        NODE_MAJOR=$(node -e "process.stdout.write(String(process.version.match(/v(\d+)/)[1]))")
        if [ "$NODE_MAJOR" -ge 22 ]; then
            echo "  Node.js $(node -v) 已满足要求，跳过"
            return 0
        fi
        echo "  Node.js $(node -v) 版本过低（需要 22+），重新安装..."
    fi
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    if [ "$mgr" = "apt" ]; then
        sudo apt-get install -y nodejs
    else
        sudo "$mgr" install -y nodejs
    fi
}

# ── 共用：Python 版本检查 ────────────────────────────────────────────────────
check_python() {
    PY_VER=$(python3 -c "import sys; print(sys.version_info[:2] >= (3,10))")
    if [ "$PY_VER" != "True" ]; then
        echo "⚠️  当前 $(python3 --version)，建议升级到 3.10+"
    fi
}

DISTRO=$(detect_distro)
echo "检测到系统：$DISTRO"

# ═══════════════════════════════════════════════════════════════════════════
# macOS
# ═══════════════════════════════════════════════════════════════════════════
if [ "$DISTRO" = "macos" ]; then
    echo "[macOS] 检查依赖..."

    command -v python3 >/dev/null || { echo "❌ 请安装 Python3: brew install python@3.11"; exit 1; }
    check_python

    if ! command -v node >/dev/null 2>&1; then
        echo "❌ 请安装 Node.js 22+: brew install node@22"; exit 1
    fi
    NODE_MAJOR=$(node -e "process.stdout.write(String(process.version.match(/v(\d+)/)[1]))")
    if [ "$NODE_MAJOR" -lt 22 ]; then
        echo "❌ Node.js 22+ 是必须的，当前: $(node -v)"; exit 1
    fi

    [ -f "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ] || \
        echo "⚠️  未找到 Google Chrome，请从 https://www.google.com/chrome/ 安装"

    echo "✅ macOS 依赖检查完成（字体由系统自带 PingFang SC 提供）"
    echo "  Python: $(python3 --version)  Node.js: $(node -v)"
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════════════
# Debian / Ubuntu（apt）
# ═══════════════════════════════════════════════════════════════════════════
if [ "$DISTRO" = "debian" ]; then
    echo "[Debian/Ubuntu] 更新包列表..."
    sudo apt-get update -qq

    echo "[1/4] 安装 Python3..."
    sudo apt-get install -y -qq python3 curl
    check_python

    echo "[2/4] 安装 Node.js 22..."
    install_nodejs_22 "apt"

    echo "[3/4] 安装 Chromium 及系统库..."
    sudo apt-get install -y -qq \
        chromium-browser \
        libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
        libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
        libxkbcommon0 libpango-1.0-0 libpangocairo-1.0-0 || true
    # 某些发行版包名为 chromium（不带 -browser 后缀）
    command -v chromium-browser >/dev/null 2>&1 || \
        sudo apt-get install -y -qq chromium || true

    echo "[4/4] 安装中文字体..."
    sudo apt-get install -y -qq fonts-noto-cjk
    fc-cache -fv >/dev/null 2>&1

    echo "[可选] pandoc..."
    sudo apt-get install -y -qq pandoc 2>/dev/null || echo "  pandoc 安装失败，将使用内置 fallback"
fi

# ═══════════════════════════════════════════════════════════════════════════
# RHEL / CentOS / Rocky / AlmaLinux / Fedora（dnf / yum）
# ═══════════════════════════════════════════════════════════════════════════
if [ "$DISTRO" = "redhat_dnf" ] || [ "$DISTRO" = "redhat_yum" ]; then
    PKG_MGR="dnf"
    [ "$DISTRO" = "redhat_yum" ] && PKG_MGR="yum"
    echo "[Red Hat 系 / $PKG_MGR] 开始安装..."

    echo "[1/4] 安装 Python3 + curl..."
    sudo "$PKG_MGR" install -y python3 curl
    check_python

    # EPEL 提供 chromium / pandoc 等软件包（Fedora 自带，RHEL/CentOS/Rocky 需要手动启用）
    if ! sudo "$PKG_MGR" list installed epel-release >/dev/null 2>&1; then
        echo "  启用 EPEL（chromium / pandoc 依赖）..."
        sudo "$PKG_MGR" install -y epel-release || \
            echo "  ⚠️  EPEL 安装失败（Fedora 不需要），继续..."
    fi
    # Rocky / AlmaLinux 需要额外启用 CRB（CodeReady Builder）
    if command -v dnf >/dev/null 2>&1; then
        sudo dnf config-manager --set-enabled crb 2>/dev/null || \
        sudo dnf config-manager --set-enabled powertools 2>/dev/null || true
    fi

    echo "[2/4] 安装 Node.js 22..."
    install_nodejs_22 "$PKG_MGR"

    echo "[3/4] 安装 Chromium 及系统库..."
    sudo "$PKG_MGR" install -y \
        chromium \
        nss atk at-spi2-atk cups-libs \
        libXcomposite libXdamage libXrandr \
        mesa-libgbm libxkbcommon pango cairo || true

    echo "[4/4] 安装中文字体..."
    # Fedora/RHEL 9+: google-noto-cjk-fonts；较旧版本用 wqy-zenhei-fonts 兜底
    sudo "$PKG_MGR" install -y google-noto-cjk-fonts 2>/dev/null || \
        sudo "$PKG_MGR" install -y wqy-zenhei-fonts 2>/dev/null || \
        echo "  ⚠️  CJK 字体安装失败，PDF 中文渲染将回退到 Google Fonts CDN"
    fc-cache -fv >/dev/null 2>&1 || true

    echo "[可选] pandoc..."
    sudo "$PKG_MGR" install -y pandoc 2>/dev/null || echo "  pandoc 安装失败，将使用内置 fallback"
fi

# ═══════════════════════════════════════════════════════════════════════════
# 未知系统
# ═══════════════════════════════════════════════════════════════════════════
if [ "$DISTRO" = "unknown" ]; then
    echo "❌ 无法识别系统的包管理器（需要 apt-get / dnf / yum）"
    echo "   请参考 requirements.txt 手动安装依赖"
    exit 1
fi

# ── 共用：创建目录 + 验证安装 ──────────────────────────────────────────────
mkdir -p ~/.openclaw/media/a-share-review

echo ""
echo "=== 验证安装 ==="
python3 --version
node --version
chromium-browser --version 2>/dev/null || chromium --version 2>/dev/null || echo "⚠️  chromium 未找到"
fc-list | grep -iE "Noto.*(CJK|SC)|WenQuanYi" 2>/dev/null | head -3 || true

echo ""
echo "✅ 安装完成！"
echo ""
echo "⚠️  配置提示："
echo "  1. 发送 Telegram 消息需配置 ~/.openclaw/openclaw.json（botToken + allowFrom）"
echo "  2. 使用账户持仓数据需配置 ~/.openclaw/jvquant.json（见 SKILL.md）"
echo "  3. 本 skill 终态为 report.md / candidates.json 落盘，不负责 PDF 推送"
