#!/usr/bin/env python3
"""
在 Flask 应用中添加支撑压力线 JSONL API 路由
"""

# 要添加到 app_new.py 的代码片段

code_to_add = '''
# 支撑压力线 JSONL API - 添加于 2026-01-13
import sys
sys.path.insert(0, '/home/user/webapp')
from support_resistance_api_adapter import SupportResistanceAPIAdapter

sr_adapter = SupportResistanceAPIAdapter()

@app.route('/api/support-resistance/latest-jsonl')
def api_support_resistance_latest_jsonl():
    """从 JSONL 获取所有币种最新支撑压力线数据"""
    result = sr_adapter.get_all_symbols_latest()
    return jsonify(result)

@app.route('/api/support-resistance/symbol/<symbol>-jsonl')
def api_support_resistance_symbol_jsonl(symbol):
    """从 JSONL 获取单个币种历史数据"""
    limit = request.args.get('limit', 100, type=int)
    result = sr_adapter.get_symbol_detail(symbol, limit=limit)
    return jsonify(result)

@app.route('/api/support-resistance/snapshots-jsonl')
def api_support_resistance_snapshots_jsonl():
    """从 JSONL 获取快照数据"""
    limit = request.args.get('limit', 100, type=int)
    result = sr_adapter.get_snapshots(limit=limit)
    return jsonify(result)

@app.route('/api/support-resistance/statistics-jsonl')
def api_support_resistance_statistics_jsonl():
    """从 JSONL 获取统计信息"""
    result = sr_adapter.get_statistics()
    return jsonify(result)
'''

print("要添加到 app_new.py 的代码：")
print("="*60)
print(code_to_add)
print("="*60)
print("\n建议插入位置：在现有的 api_support_resistance_latest 函数之后")
print("文件路径：/home/user/webapp/source_code/app_new.py")
