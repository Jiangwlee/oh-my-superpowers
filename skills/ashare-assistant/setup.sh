#!/bin/bash
# setup.sh - ashare-assistant 环境安装脚本
# 支持：macOS、Ubuntu/Debian（apt）、RHEL/CentOS/Rocky/AlmaLinux/Fedora（dnf/yum）
# 用法: bash setup.sh
#
# 依赖摘要：
#   必须：Python 3.10+
#   说明：本 skill 纯 Python + LLM 工作流，数据采集均使用标准库 urllib
#         无需 Node.js / Chromium / pandoc
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

    echo "✅ macOS 依赖检查完成（字体由系统自带 PingFang SC 提供）"
    echo "  Python: $(python3 --version)"
    exit 0
fi

# ═══════════════════════════════════════════════════════════════════════════
# Debian / Ubuntu（apt）
# ═══════════════════════════════════════════════════════════════════════════
if [ "$DISTRO" = "debian" ]; then
    echo "[Debian/Ubuntu] 更新包列表..."
    sudo apt-get update -qq

    echo "[1/2] 安装 Python3..."
    sudo apt-get install -y -qq python3 curl
    check_python

    echo "[2/2] 安装中文字体..."
    sudo apt-get install -y -qq fonts-noto-cjk
    fc-cache -fv >/dev/null 2>&1
fi

# ═══════════════════════════════════════════════════════════════════════════
# RHEL / CentOS / Rocky / AlmaLinux / Fedora（dnf / yum）
# ═══════════════════════════════════════════════════════════════════════════
if [ "$DISTRO" = "redhat_dnf" ] || [ "$DISTRO" = "redhat_yum" ]; then
    PKG_MGR="dnf"
    [ "$DISTRO" = "redhat_yum" ] && PKG_MGR="yum"
    echo "[Red Hat 系 / $PKG_MGR] 开始安装..."

    echo "[1/2] 安装 Python3 + curl..."
    sudo "$PKG_MGR" install -y python3 curl
    check_python

    echo "[2/2] 安装中文字体..."
    # Fedora/RHEL 9+: google-noto-cjk-fonts；较旧版本用 wqy-zenhei-fonts 兜底
    sudo "$PKG_MGR" install -y google-noto-cjk-fonts 2>/dev/null || \
        sudo "$PKG_MGR" install -y wqy-zenhei-fonts 2>/dev/null || \
        echo "  ⚠️  CJK 字体安装失败"
    fc-cache -fv >/dev/null 2>&1 || true
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
mkdir -p ~/.ashare-assistant/data

echo ""
echo "=== 验证安装 ==="
python3 --version
fc-list | grep -iE "Noto.*(CJK|SC)|WenQuanYi" 2>/dev/null | head -3 || true

echo ""
echo "✅ 安装完成！"
echo ""
echo "⚠️  配置提示："
echo "  1. 运行前需先执行 ashare-collect 采集当日数据"
echo "  2. 账户持仓数据路径：~/.ashare-assistant/data/{DATE}/broker_account.json"
echo "  3. 产物路径：~/.ashare-assistant/data/{DATE}/"
echo "     - market_review.md（复盘）"
echo "     - analysis/candidates.json（选股）"
echo "     - trading_plan.md（交易计划）"
