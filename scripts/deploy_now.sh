#!/bin/bash
# RedInk 一键部署脚本 - 服务器 136.110.80.154
# 直接在服务器上执行: bash deploy_now.sh

set -e

PROJECT_DIR="/root/XHS"
GEMINI_API_KEY="AIzaSyC6hdS0Z5reQE0wMszxOgfTEwYdp6OvdI0"

echo "=========================================="
echo "  RedInk 部署 - 136.110.80.154"
echo "=========================================="

cd "$PROJECT_DIR"
echo "[INFO] 工作目录: $(pwd)"

# 1. 克隆 RedInk
echo "[INFO] Step 1: 克隆 RedInk..."
if [ -d "redink/.git" ]; then
    echo "[INFO] 更新现有仓库..."
    cd redink && git pull origin main 2>/dev/null || true && cd ..
else
    rm -rf redink
    git clone https://github.com/HisMax/RedInk.git redink
fi

# 2. 创建数据目录
echo "[INFO] Step 2: 创建数据目录..."
mkdir -p redink_data/history redink_data/images

# 3. 创建配置文件
echo "[INFO] Step 3: 创建配置文件..."

cat > redink/text_providers.yaml << EOF
active_provider: gemini

providers:
  gemini:
    type: google_genai
    api_key: $GEMINI_API_KEY
    model: gemini-2.0-flash-exp
    temperature: 1.0
    max_output_tokens: 8000
EOF

cat > redink/image_providers.yaml << EOF
active_provider: gemini

providers:
  gemini:
    type: google_genai
    api_key: $GEMINI_API_KEY
    model: gemini-2.0-flash-exp
    high_concurrency: false
EOF

# 4. 更新 .env
echo "[INFO] Step 4: 更新 .env..."
if ! grep -q "GEMINI_API_KEY" .env 2>/dev/null; then
    echo "GEMINI_API_KEY=$GEMINI_API_KEY" >> .env
else
    sed -i "s|GEMINI_API_KEY=.*|GEMINI_API_KEY=$GEMINI_API_KEY|" .env
fi

# 5. 检查 docker-compose.yml
echo "[INFO] Step 5: 检查 docker-compose.yml..."
if ! grep -q "redink:" docker-compose.yml 2>/dev/null; then
    echo "[INFO] 追加 RedInk 服务配置..."

    # 在 networks: 之前插入 redink 服务
    sed -i '/^networks:/i\
  # RedInk 图文生成服务\
  redink:\
    build:\
      context: ./redink\
      dockerfile: Dockerfile\
    image: redink:latest\
    container_name: redink\
    restart: unless-stopped\
    ports:\
      - "12398:5000"\
    environment:\
      - GEMINI_API_KEY=${GEMINI_API_KEY}\
      - FLASK_ENV=production\
      - TZ=Asia/Shanghai\
    volumes:\
      - ./redink/text_providers.yaml:/app/text_providers.yaml:ro\
      - ./redink/image_providers.yaml:/app/image_providers.yaml:ro\
      - ./redink_data/history:/app/history\
      - ./redink_data/images:/app/images\
    networks:\
      - n8n-network\
' docker-compose.yml
fi

# 6. 构建并启动
echo "[INFO] Step 6: 构建并启动 RedInk..."
docker compose build redink
docker compose up -d redink

# 7. 等待启动
echo "[INFO] Step 7: 等待服务启动..."
sleep 15

# 8. 健康检查
echo "[INFO] Step 8: 健康检查..."
for i in 1 2 3 4 5 6; do
    if curl -s http://localhost:12398/ > /dev/null 2>&1; then
        echo "[INFO] RedInk 启动成功! ✓"
        break
    fi
    echo "[INFO] 等待中... ($i/6)"
    sleep 5
done

# 9. 开放防火墙
echo "[INFO] Step 9: 开放防火墙端口 12398..."
if command -v ufw &> /dev/null; then
    ufw allow 12398/tcp 2>/dev/null || true
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=12398/tcp 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
fi

# 完成
echo ""
echo "=========================================="
echo "  部署完成!"
echo "=========================================="
echo ""
echo "  测试: curl http://localhost:12398/"
echo "  外网: http://136.110.80.154:12398/"
echo "  日志: docker logs -f redink"
echo ""

# 立即测试
echo "[INFO] 测试服务..."
curl -s http://localhost:12398/ | head -20 || echo "服务可能还在启动中"
