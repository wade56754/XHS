#!/bin/bash
# scripts/health_check.sh
# 健康检查脚本

echo "=== XHS_AutoPublisher 健康检查 ==="

FAILED=0

# 检查Docker
echo -n "[Docker] "
if docker --version &> /dev/null; then
    echo "OK"
else
    echo "FAIL"
    FAILED=$((FAILED+1))
fi

# 检查N8N容器
echo -n "[N8N Container] "
if docker ps | grep -q n8n; then
    echo "OK (Running)"
else
    echo "FAIL (Not Running)"
    FAILED=$((FAILED+1))
fi

# 检查N8N HTTP
echo -n "[N8N HTTP] "
N8N_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5678/healthz 2>/dev/null)
if [ "$N8N_STATUS" = "200" ]; then
    echo "OK (HTTP 200)"
else
    echo "FAIL (HTTP ${N8N_STATUS})"
    FAILED=$((FAILED+1))
fi

# 检查Claude API
echo -n "[Claude API] "
if [ -n "$CLAUDE_API_KEY" ]; then
    CLAUDE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "x-api-key: $CLAUDE_API_KEY" \
        -H "anthropic-version: 2023-06-01" \
        https://api.anthropic.com/v1/messages 2>/dev/null)
    if [ "$CLAUDE_STATUS" = "400" ] || [ "$CLAUDE_STATUS" = "200" ]; then
        echo "OK (API Reachable)"
    else
        echo "WARN (HTTP ${CLAUDE_STATUS})"
    fi
else
    echo "SKIP (CLAUDE_API_KEY not set)"
fi

# 检查飞书API
echo -n "[Lark API] "
if [ -n "$LARK_APP_ID" ] && [ -n "$LARK_APP_SECRET" ]; then
    LARK_RESP=$(curl -s https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal \
        -H "Content-Type: application/json" \
        -d "{\"app_id\":\"$LARK_APP_ID\",\"app_secret\":\"$LARK_APP_SECRET\"}" 2>/dev/null)
    if echo "$LARK_RESP" | grep -q "tenant_access_token"; then
        echo "OK"
    else
        echo "FAIL"
        FAILED=$((FAILED+1))
    fi
else
    echo "SKIP (LARK credentials not set)"
fi

# 检查磁盘空间
echo -n "[Disk Space] "
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 90 ]; then
    echo "OK (${DISK_USAGE}% used)"
else
    echo "WARN (${DISK_USAGE}% used)"
fi

echo ""
echo "=== 检查完成 ==="
if [ $FAILED -eq 0 ]; then
    echo "状态: 所有核心服务正常"
    exit 0
else
    echo "状态: ${FAILED} 项检查失败"
    exit 1
fi
