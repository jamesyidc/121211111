#!/bin/bash
# 系统清理脚本

echo "=========================================="
echo "系统清理脚本"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="
echo ""

CLEANED=0

# 1. 清理PM2日志
echo "[1/8] 清理PM2日志..."
if [ -d ~/.pm2/logs ]; then
    BEFORE=$(du -sh ~/.pm2/logs | cut -f1)
    pm2 flush 2>/dev/null || true
    AFTER=$(du -sh ~/.pm2/logs 2>/dev/null | cut -f1 || echo "0")
    echo "  PM2日志: $BEFORE -> $AFTER"
    CLEANED=$((CLEANED + 1))
fi
echo ""

# 2. 清理应用日志（保留最近100行）
echo "[2/8] 清理应用大日志文件..."
for log in $(find /home/user/webapp -name "*.log" -size +10M 2>/dev/null); do
    if [ -f "$log" ]; then
        SIZE_BEFORE=$(ls -lh "$log" | awk '{print $5}')
        tail -100 "$log" > "$log.tmp" && mv "$log.tmp" "$log"
        SIZE_AFTER=$(ls -lh "$log" | awk '{print $5}')
        echo "  $(basename $log): $SIZE_BEFORE -> $SIZE_AFTER"
    fi
done
echo ""

# 3. 清理logs目录下的旧日志
echo "[3/8] 清理logs目录..."
if [ -d logs ]; then
    BEFORE=$(du -sh logs | cut -f1)
    # 清理旧的PM2日志
    find logs -name "*.log" -size +10M -exec sh -c 'tail -100 "$1" > "$1.tmp" && mv "$1.tmp" "$1"' _ {} \;
    AFTER=$(du -sh logs | cut -f1)
    echo "  logs目录: $BEFORE -> $AFTER"
fi
echo ""

# 4. 清理Python缓存
echo "[4/8] 清理Python缓存..."
BEFORE=$(find . -type d -name __pycache__ -exec du -sh {} \; 2>/dev/null | awk '{sum+=$1} END {print sum}' || echo "0")
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
echo "  Python缓存已清理"
echo ""

# 5. 清理临时文件
echo "[5/8] 清理临时文件..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.bak" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true
echo "  临时文件已清理"
echo ""

# 6. 清理Git临时文件（但保留.git目录）
echo "[6/8] 清理Git临时文件..."
if [ -d .git ]; then
    git gc --prune=now 2>/dev/null || true
    echo "  Git垃圾回收完成"
fi
echo ""

# 7. 清理数据库临时文件
echo "[7/8] 清理数据库临时文件..."
find databases -name "*.db-shm" -delete 2>/dev/null || true
find databases -name "*.db-wal" -delete 2>/dev/null || true
echo "  数据库临时文件已清理"
echo ""

# 8. 显示清理后状态
echo "[8/8] 清理完成，当前状态："
echo ""
df -h / | grep -v Filesystem
echo ""
echo "各目录大小："
du -sh databases logs source_code .git 2>/dev/null | sort -h
echo ""
echo "=========================================="
echo "清理完成！"
echo "=========================================="
