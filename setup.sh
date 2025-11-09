#!/bin/bash
# 快速设置脚本

set -e

echo "=========================================="
echo "MuleRun Crawler 设置脚本"
echo "=========================================="

# 检查 Python 版本
echo "检查 Python 版本..."
python3 --version || { echo "错误: 未找到 Python 3"; exit 1; }

# 创建虚拟环境
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source .venv/bin/activate

# 升级 pip
echo "升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "安装 Python 依赖..."
pip install -r requirements.txt

# 安装 Playwright 浏览器
echo "安装 Playwright 浏览器..."
playwright install chromium
echo "浏览器安装完成"

# 安装系统依赖（VPS 环境必需）
echo ""
echo "安装 Playwright 系统依赖..."
echo "注意：这需要 sudo 权限，如果失败请手动运行: sudo $(pwd)/.venv/bin/playwright install-deps chromium"
if command -v sudo &> /dev/null; then
    sudo "$(pwd)/.venv/bin/playwright" install-deps chromium || {
        echo "警告: 系统依赖安装失败，请手动运行以下命令:"
        echo "  sudo $(pwd)/.venv/bin/playwright install-deps chromium"
        echo "  或者使用 apt 安装:"
        echo "  sudo apt-get install -y libatk1.0-0 libatk-bridge2.0-0 libcups2 libatspi2.0-0 libxdamage1 libcairo2 libpango-1.0-0 libasound2t64"
    }
else
    echo "警告: 未找到 sudo，请手动安装系统依赖"
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "创建 .env 文件..."
    if [ -f "env.example" ]; then
        cp env.example .env
    else
        touch .env
        echo "# Neon PostgreSQL 连接字符串" >> .env
        echo "DATABASE_URL=postgresql://username:password@host.neon.tech/database?sslmode=require" >> .env
    fi
    echo "请编辑 .env 文件配置数据库连接信息"
else
    echo ".env 文件已存在"
fi

# 创建日志目录
mkdir -p logs

echo ""
echo "=========================================="
echo "设置完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 编辑 .env 文件配置 Neon 数据库连接字符串"
echo "   DATABASE_URL=postgresql://username:password@host.neon.tech/database?sslmode=require"
echo ""
echo "2. Neon 数据库说明："
echo "   - 在 https://neon.tech 创建项目"
echo "   - 从控制台复制连接字符串（Connection String）"
echo "   - 数据库表会在首次运行时自动创建，无需手动初始化"
echo ""
echo "3. 运行测试: python main.py --mode once"
echo "   或使用 uv: uv run main.py --mode once"
echo ""

