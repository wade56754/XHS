#!/bin/bash
# scripts/setup.sh
# 环境初始化脚本

set -e

echo "=== XHS_AutoPublisher 环境初始化 ==="

# 1. 系统更新
echo "[1/5] 系统更新..."
sudo apt update && sudo apt upgrade -y

# 2. 安装Docker
echo "[2/5] 安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "Docker安装完成，请重新登录以生效"
else
    echo "Docker已安装"
fi

# 3. 安装Docker Compose
echo "[3/5] 安装Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo apt install docker-compose -y
else
    echo "Docker Compose已安装"
fi

# 4. 创建项目目录
echo "[4/5] 创建项目目录..."
mkdir -p ~/xhs_publisher/{n8n_data,backups}

# 5. 复制环境变量模板
echo "[5/5] 配置环境变量..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "已创建 .env 文件，请编辑填入真实的 API 密钥"
else
    echo ".env 文件已存在"
fi

echo ""
echo "=== 初始化完成 ==="
echo "下一步："
echo "1. 编辑 .env 文件，填入 API 密钥"
echo "2. 运行 docker-compose up -d 启动服务"
