#!/bin/bash
# scripts/backup.sh
# 数据备份脚本

set -e

BACKUP_DIR="${BACKUP_DIR:-/opt/xhs_auto/xiaohongshu_auto_publisher/backups}"
DATE=$(date +%Y%m%d_%H%M%S)

echo "=== XHS_AutoPublisher 数据备份 ==="
echo "备份目录: ${BACKUP_DIR}"
echo "时间戳: ${DATE}"

# 创建备份目录
mkdir -p ${BACKUP_DIR}

# 备份N8N工作流
echo "[1/3] 备份N8N工作流..."
docker exec n8n n8n export:workflow --all --output=/backups/workflows_${DATE}.json 2>/dev/null || {
    echo "[WARN] N8N工作流备份失败，容器可能未运行"
}

# 备份N8N凭证（仅元数据）
echo "[2/3] 备份N8N凭证..."
docker exec n8n n8n export:credentials --all --output=/backups/credentials_${DATE}.json 2>/dev/null || {
    echo "[WARN] N8N凭证备份失败"
}

# 清理旧备份（保留7天）
echo "[3/3] 清理旧备份..."
find ${BACKUP_DIR} -name "*.json" -mtime +7 -delete
find ${BACKUP_DIR} -name "*.sql" -mtime +7 -delete

echo ""
echo "=== 备份完成 ==="
echo "备份文件: ${BACKUP_DIR}/workflows_${DATE}.json"
