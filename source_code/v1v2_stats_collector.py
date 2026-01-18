#!/usr/bin/env python3
"""
V1V2信号统计收集器
每3分钟统计一次各币种的V1和V2信号出现次数
"""
import sqlite3
import time
import logging
from datetime import datetime, timedelta
import pytz

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('v1v2_stats_collector.log'),
        logging.StreamHandler()
    ]
)

DB_FILE = 'v1v2_data.db'
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 27个币种列表
SYMBOLS = [
    'BTC', 'ETH', 'XRP', 'SOL', 'BNB', 'LTC', 'DOGE', 'SUI', 'TRX', 'TON',
    'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'ADA', 'LINK', 'CRO', 'DOT', 'UNI',
    'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO'
]

def collect_statistics():
    """收集当前时刻的V1V2统计"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    beijing_now = datetime.now(BEIJING_TZ)
    stat_date = beijing_now.strftime('%Y-%m-%d')
    current_time = beijing_now.strftime('%Y-%m-%d %H:%M:%S')
    
    logging.info(f"🔍 开始统计 {current_time}")
    
    for symbol in SYMBOLS:
        table_name = f'volume_{symbol.lower()}'
        
        try:
            # 查询最近3分钟内的V1和V2信号
            three_min_ago = (beijing_now - timedelta(minutes=3)).strftime('%Y-%m-%d %H:%M:%S')
            
            # 统计V1信号数量（level='V1'）
            cursor.execute(f'''
                SELECT COUNT(*) FROM {table_name}
                WHERE collect_time >= ? AND collect_time <= ?
                AND level = 'V1'
            ''', (three_min_ago, current_time))
            v1_count = cursor.fetchone()[0]
            
            # 统计V2信号数量（level='V2'）
            cursor.execute(f'''
                SELECT COUNT(*) FROM {table_name}
                WHERE collect_time >= ? AND collect_time <= ?
                AND level = 'V2'
            ''', (three_min_ago, current_time))
            v2_count = cursor.fetchone()[0]
            
            # 如果有信号，则更新统计
            if v1_count > 0 or v2_count > 0:
                cursor.execute('''
                    INSERT INTO v1v2_statistics (symbol, stat_date, v1_count, v2_count, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(symbol, stat_date) DO UPDATE SET
                        v1_count = v1_count + ?,
                        v2_count = v2_count + ?,
                        updated_at = CURRENT_TIMESTAMP
                ''', (symbol, stat_date, v1_count, v2_count, v1_count, v2_count))
                
                if v1_count > 0 or v2_count > 0:
                    logging.info(f"  {symbol}: V1={v1_count}, V2={v2_count}")
        
        except Exception as e:
            logging.error(f"  ❌ {symbol} 统计失败: {str(e)}")
            continue
    
    conn.commit()
    conn.close()
    logging.info("✅ 统计完成\n")

def main():
    """主函数"""
    logging.info("=" * 60)
    logging.info("V1V2统计收集器启动")
    logging.info("统计间隔: 3分钟")
    logging.info("=" * 60)
    
    while True:
        try:
            collect_statistics()
            time.sleep(180)  # 3分钟 = 180秒
        except KeyboardInterrupt:
            logging.info("\n⚠️  收到停止信号，正在退出...")
            break
        except Exception as e:
            logging.error(f"❌ 统计过程出错: {str(e)}")
            time.sleep(60)  # 出错后等待1分钟再继续

if __name__ == '__main__':
    main()
