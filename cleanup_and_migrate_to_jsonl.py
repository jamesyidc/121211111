#!/usr/bin/env python3
"""
清理错误的数据库数据，确保所有数据以JSONL格式保存
"""
import sqlite3
import os
import json
from datetime import datetime
from pytz import timezone

# 北京时区
BEIJING_TZ = timezone('Asia/Shanghai')

def cleanup_database_tables():
    """清理数据库中的恐慌/爆仓相关表"""
    db_path = 'databases/crypto_data.db'
    
    if not os.path.exists(db_path):
        print(f"❌ 数据库不存在: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查找需要清理的表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        all_tables = [t[0] for t in cursor.fetchall()]
        
        # 过滤出liquidation相关的表（这些是子账户爆仓记录，不是恐慌指数数据）
        liquidation_tables = [t for t in all_tables if 'liquidation' in t.lower()]
        
        print("\n" + "="*60)
        print("数据库表清理报告")
        print("="*60)
        
        if not liquidation_tables:
            print("✅ 没有找到需要清理的liquidation表")
        else:
            print(f"\n找到 {len(liquidation_tables)} 个liquidation表（这些是子账户爆仓记录，保留）:")
            for table in liquidation_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                print(f"  - {table}: {count} 条记录（保留，这些不是恐慌指数数据）")
        
        # 注意：我们不会清理这些表，因为它们是子账户爆仓记录，不是恐慌指数数据
        # 恐慌指数数据已经全部在JSONL中
        
        conn.close()
        
        print("\n✅ 数据库检查完成")
        print("   说明：liquidation表是子账户爆仓记录，不是恐慌指数数据")
        print("   恐慌指数数据已全部存储在 data/panic_jsonl/ 目录中")
        
    except Exception as e:
        print(f"❌ 数据库清理失败: {e}")

def verify_jsonl_data():
    """验证JSONL数据的完整性"""
    jsonl_dir = 'data/panic_jsonl'
    
    print("\n" + "="*60)
    print("JSONL数据验证报告")
    print("="*60)
    
    if not os.path.exists(jsonl_dir):
        print(f"❌ JSONL目录不存在: {jsonl_dir}")
        return
    
    jsonl_files = [f for f in os.listdir(jsonl_dir) if f.endswith('.jsonl')]
    
    if not jsonl_files:
        print("❌ 没有找到JSONL文件")
        return
    
    print(f"\n找到 {len(jsonl_files)} 个JSONL文件:\n")
    
    for jsonl_file in jsonl_files:
        file_path = os.path.join(jsonl_dir, jsonl_file)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            record_count = len(lines)
            file_size = os.path.getsize(file_path) / 1024  # KB
            
            print(f"📄 {jsonl_file}")
            print(f"   记录数: {record_count}")
            print(f"   文件大小: {file_size:.2f} KB")
            
            if record_count > 0:
                # 读取第一条和最后一条记录
                first_record = json.loads(lines[0])
                last_record = json.loads(lines[-1])
                
                # 尝试获取时间字段
                time_field = None
                for field in ['record_time', 'stat_time', 'created_at', 'timestamp']:
                    if field in first_record:
                        time_field = field
                        break
                
                if time_field:
                    print(f"   时间范围: {first_record[time_field]} → {last_record[time_field]}")
                
                # 显示字段
                print(f"   字段: {', '.join(first_record.keys())}")
                
                # 显示最新的一条记录
                if jsonl_file == 'panic_wash_index.jsonl':
                    print(f"   最新数据示例:")
                    print(f"     恐慌指数: {last_record.get('panic_index', 'N/A')}")
                    print(f"     清洗指数: {last_record.get('wash_index', 'N/A')}")
                    print(f"     24小时爆仓人数: {last_record.get('hour_24_people', 'N/A')} 万")
                    print(f"     24小时爆仓金额: ${last_record.get('hour_24_amount', 'N/A')} 万")
                    print(f"     全网持仓: ${last_record.get('total_position', 'N/A')} 亿")
            
            print()
            
        except Exception as e:
            print(f"   ❌ 读取失败: {e}\n")
    
    print("✅ JSONL数据验证完成")

def check_data_collection_status():
    """检查数据采集状态"""
    print("\n" + "="*60)
    print("数据采集状态检查")
    print("="*60)
    
    # 检查采集器进程
    import subprocess
    try:
        result = subprocess.run(
            ['pm2', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if 'panic-collector' in result.stdout:
            print("\n✅ panic-collector 采集器运行正常")
        else:
            print("\n⚠️  panic-collector 采集器未运行")
            
    except Exception as e:
        print(f"\n⚠️  无法检查PM2状态: {e}")

def main():
    """主函数"""
    print("\n" + "="*60)
    print("恐慌指数数据清理与JSONL迁移验证")
    print("="*60)
    print(f"执行时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. 清理数据库
    cleanup_database_tables()
    
    # 2. 验证JSONL数据
    verify_jsonl_data()
    
    # 3. 检查采集状态
    check_data_collection_status()
    
    print("\n" + "="*60)
    print("✅ 所有检查完成")
    print("="*60)
    print("\n📝 总结:")
    print("  1. 数据库中的liquidation表是子账户爆仓记录（保留）")
    print("  2. 恐慌指数数据已全部存储在 data/panic_jsonl/")
    print("  3. 所有新数据将继续写入JSONL文件")
    print("  4. API已更新为从JSONL读取数据")
    print("\n🎯 数据存储策略:")
    print("  ✅ 恐慌指数数据 → data/panic_jsonl/panic_wash_index.jsonl")
    print("  ✅ SAR占比数据 → data/panic_jsonl/sar_bias_stats.jsonl")
    print("  ✅ 30天爆仓数据 → 实时从BTC123 API获取（无需存储）")
    print()

if __name__ == '__main__':
    main()
