#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚点单决策日志清理脚本
功能：保留最近5天的决策日志，删除更早的记录
运行频率：每天执行一次
"""

import sqlite3
from datetime import datetime, timedelta
import pytz

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 数据库路径
TRADING_DB = '/home/user/webapp/trading_decision.db'

def clean_old_decisions(keep_days=5):
    """清理旧的决策日志
    
    Args:
        keep_days: 保留最近N天的记录，默认5天
    """
    try:
        conn = sqlite3.connect(TRADING_DB, timeout=10.0)
        cursor = conn.cursor()
        
        # 计算截止日期
        cutoff_date = (datetime.now(BEIJING_TZ) - timedelta(days=keep_days)).strftime('%Y-%m-%d 00:00:00')
        
        print("=" * 60)
        print(f"🗑️  锚点单决策日志清理")
        print("=" * 60)
        print(f"📅 保留天数: {keep_days}天")
        print(f"⏰ 当前时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📆 截止日期: {cutoff_date}")
        print()
        
        # 统计要删除的记录数
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM trading_decisions
            WHERE created_at < ?
        ''', (cutoff_date,))
        to_delete = cursor.fetchone()[0]
        
        if to_delete == 0:
            print("✅ 没有需要清理的旧记录")
            conn.close()
            return
        
        print(f"🔍 找到 {to_delete} 条旧记录需要清理")
        
        # 显示即将删除的记录统计
        cursor.execute('''
            SELECT decision_type, COUNT(*) as count
            FROM trading_decisions
            WHERE created_at < ?
            GROUP BY decision_type
            ORDER BY count DESC
        ''', (cutoff_date,))
        
        print("\n📊 按类型统计:")
        for row in cursor.fetchall():
            decision_type = row[0] or '未分类'
            count = row[1]
            print(f"  - {decision_type}: {count}条")
        
        # 执行删除
        cursor.execute('''
            DELETE FROM trading_decisions
            WHERE created_at < ?
        ''', (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        
        print(f"\n✅ 成功删除 {deleted_count} 条旧记录")
        
        # 统计剩余记录
        cursor.execute('SELECT COUNT(*) FROM trading_decisions')
        remaining = cursor.fetchone()[0]
        print(f"📊 剩余记录数: {remaining}条")
        
        # 优化数据库
        print("\n🔧 优化数据库...")
        cursor.execute('VACUUM')
        print("✅ 数据库优化完成")
        
        conn.close()
        print()
        print("=" * 60)
        print("🎉 清理完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ 清理失败: {e}")
        import traceback
        print(traceback.format_exc())

def main():
    """主函数"""
    clean_old_decisions(keep_days=5)

if __name__ == '__main__':
    main()
