#!/usr/bin/env python3
"""
K线数据导出工具
用于将数据库中的K线数据导出为CSV或SQL格式，方便迁移和备份
"""

import sqlite3
import csv
import sys
from datetime import datetime
import os

def export_to_csv(db_path='crypto_data.db', output_dir='kline_export'):
    """导出K线数据到CSV文件"""
    
    # 创建输出目录
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取所有币种
    cursor.execute('SELECT DISTINCT symbol FROM okex_kline_ohlc ORDER BY symbol')
    symbols = [row[0] for row in cursor.fetchall()]
    
    print(f'🚀 开始导出 {len(symbols)} 个币种的K线数据...')
    print('='*80)
    
    total_rows = 0
    
    for symbol in symbols:
        for timeframe in ['5m', '1H']:
            # 查询数据
            cursor.execute('''
                SELECT timestamp, open, high, low, close, volume, created_at
                FROM okex_kline_ohlc
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp
            ''', (symbol, timeframe))
            
            rows = cursor.fetchall()
            if not rows:
                continue
            
            # 生成文件名
            filename = f'{symbol}_{timeframe}.csv'
            filepath = os.path.join(output_dir, filename)
            
            # 写入CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # 写入表头
                writer.writerow(['timestamp', 'datetime', 'open', 'high', 'low', 'close', 'volume', 'created_at'])
                # 写入数据
                for row in rows:
                    ts = row[0]
                    dt = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S')
                    writer.writerow([ts, dt] + list(row[1:]))
            
            total_rows += len(rows)
            print(f'✅ {symbol:20s} {timeframe:4s}: {len(rows):6d} 条 → {filename}')
    
    conn.close()
    
    print('='*80)
    print(f'✅ 导出完成！')
    print(f'   总记录数: {total_rows:,} 条')
    print(f'   输出目录: {output_dir}/')
    print(f'   文件数量: {len(os.listdir(output_dir))} 个')
    
    # 生成汇总报告
    report_file = os.path.join(output_dir, 'EXPORT_REPORT.txt')
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write('='*80 + '\n')
        f.write('K线数据导出报告\n')
        f.write('='*80 + '\n\n')
        f.write(f'导出时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'数据库文件: {db_path}\n')
        f.write(f'币种数量: {len(symbols)}\n')
        f.write(f'总记录数: {total_rows:,}\n\n')
        f.write('币种列表:\n')
        for i, sym in enumerate(symbols, 1):
            f.write(f'  {i:2d}. {sym}\n')
    
    print(f'\n📄 导出报告已生成: {report_file}')

def export_to_sql(db_path='crypto_data.db', output_file='kline_data.sql'):
    """导出K线数据到SQL文件（包含建表语句和INSERT语句）"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f'🚀 开始导出K线数据到SQL文件...')
    print('='*80)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # 写入建表语句
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='okex_kline_ohlc'")
        create_sql = cursor.fetchone()[0]
        f.write('-- K线OHLC数据表结构\n')
        f.write(create_sql + ';\n\n')
        
        # 写入数据
        f.write('-- K线数据插入语句\n')
        f.write('BEGIN TRANSACTION;\n\n')
        
        cursor.execute('SELECT * FROM okex_kline_ohlc ORDER BY symbol, timeframe, timestamp')
        rows = cursor.fetchall()
        
        batch_size = 100
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            for row in batch:
                values = ', '.join([
                    f"'{v}'" if isinstance(v, str) else str(v) if v is not None else 'NULL'
                    for v in row
                ])
                f.write(f'INSERT INTO okex_kline_ohlc VALUES ({values});\n')
            
            if (i + batch_size) % 1000 == 0:
                print(f'   已导出: {i + batch_size:,}/{len(rows):,} 条记录...')
        
        f.write('\nCOMMIT;\n')
    
    conn.close()
    
    file_size = os.path.getsize(output_file) / 1024 / 1024  # MB
    print('='*80)
    print(f'✅ SQL导出完成！')
    print(f'   输出文件: {output_file}')
    print(f'   文件大小: {file_size:.2f} MB')
    print(f'   记录数量: {len(rows):,} 条')

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='K线数据导出工具')
    parser.add_argument('--format', choices=['csv', 'sql', 'both'], default='csv',
                        help='导出格式: csv, sql, 或 both (默认: csv)')
    parser.add_argument('--db', default='crypto_data.db',
                        help='数据库文件路径 (默认: crypto_data.db)')
    parser.add_argument('--output', default='kline_export',
                        help='CSV输出目录或SQL输出文件名 (默认: kline_export)')
    
    args = parser.parse_args()
    
    if args.format in ['csv', 'both']:
        export_to_csv(args.db, args.output)
    
    if args.format in ['sql', 'both']:
        sql_file = args.output if args.format == 'sql' else 'kline_data.sql'
        export_to_sql(args.db, sql_file)

if __name__ == '__main__':
    main()
