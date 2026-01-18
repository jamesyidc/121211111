#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新query API以使用JSONL数据源
"""

import sys
sys.path.insert(0, '/home/user/webapp')

def create_jsonl_api_code():
    """生成使用JSONL的API代码"""
    
    api_code = '''
# ==================== Query JSONL API ====================
# 在app_new.py的最前面添加导入
# from source_code.query_jsonl_manager import QueryJSONLManager

@app.route('/api/query')
def api_query():
    """查询API - 使用JSONL数据源"""
    query_time = request.args.get('time', '')
    if not query_time:
        return jsonify({'error': '请提供查询时间'})
    
    try:
        # 使用JSONL管理器
        manager = QueryJSONLManager()
        
        # 获取快照数据
        snapshot = manager.get_snapshot_by_time(query_time)
        
        if not snapshot:
            return jsonify({'error': f'未找到 {query_time} 的数据'})
        
        # 获取币种数据
        snapshot_time = snapshot.get('snapshot_time')
        coins = manager.get_coins_by_time(snapshot_time)
        
        # 返回完整数据
        return jsonify({
            'snapshot_time': snapshot.get('snapshot_time'),
            'rush_up': snapshot.get('rush_up', 0),
            'rush_down': snapshot.get('rush_down', 0),
            'diff': snapshot.get('diff', 0),
            'count': snapshot.get('count', 0),
            'ratio': snapshot.get('ratio', 0),
            'status': snapshot.get('status', ''),
            'round_rush_up': snapshot.get('round_rush_up', 0),
            'round_rush_down': snapshot.get('round_rush_down', 0),
            'price_lowest': snapshot.get('price_lowest', 0),
            'price_newhigh': snapshot.get('price_newhigh', 0),
            'count_score_display': snapshot.get('count_score_display', ''),
            'count_score_type': snapshot.get('count_score_type', ''),
            'rise_24h_count': snapshot.get('rise_24h_count', 0),
            'fall_24h_count': snapshot.get('fall_24h_count', 0),
            'coins': coins
        })
    
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/latest')
def api_latest():
    """获取最新数据API - 使用JSONL数据源"""
    try:
        # 使用JSONL管理器
        manager = QueryJSONLManager()
        
        # 获取最新快照
        snapshot = manager.get_latest_snapshot()
        
        if not snapshot:
            return jsonify({'error': '未找到任何数据'})
        
        # 获取币种数据
        snapshot_time = snapshot.get('snapshot_time')
        coins = manager.get_coins_by_time(snapshot_time)
        
        # 返回完整数据
        return jsonify({
            'snapshot_time': snapshot.get('snapshot_time'),
            'rush_up': snapshot.get('rush_up', 0),
            'rush_down': snapshot.get('rush_down', 0),
            'diff': snapshot.get('diff', 0),
            'count': snapshot.get('count', 0),
            'ratio': snapshot.get('ratio', 0),
            'status': snapshot.get('status', ''),
            'round_rush_up': snapshot.get('round_rush_up', 0),
            'round_rush_down': snapshot.get('round_rush_down', 0),
            'price_lowest': snapshot.get('price_lowest', 0),
            'price_newhigh': snapshot.get('price_newhigh', 0),
            'count_score_display': snapshot.get('count_score_display', ''),
            'count_score_type': snapshot.get('count_score_type', ''),
            'rise_24h_count': snapshot.get('rise_24h_count', 0),
            'fall_24h_count': snapshot.get('fall_24h_count', 0),
            'coins': coins
        })
    
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/query/latest')
def api_query_latest():
    """获取最新快照数据 - 使用JSONL数据源"""
    try:
        manager = QueryJSONLManager()
        
        # 获取最新快照
        snapshot = manager.get_latest_snapshot()
        
        if not snapshot:
            return jsonify({'error': '未找到任何数据'})
        
        # 获取币种数据
        snapshot_time = snapshot.get('snapshot_time')
        coins = manager.get_coins_by_time(snapshot_time)
        
        return jsonify({
            'success': True,
            'data': {
                'snapshot': snapshot,
                'coins': coins
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/query/batch-import', methods=['POST'])
def api_query_batch_import():
    """批量导入TXT文件 - 使用JSONL数据源"""
    try:
        data = request.get_json()
        txt_content = data.get('txt_content', '')
        snapshot_time = data.get('snapshot_time', '')
        
        if not txt_content or not snapshot_time:
            return jsonify({'success': False, 'error': '缺少必要参数'})
        
        # 导入TXT内容
        from migrate_query_to_jsonl import parse_txt_content
        snapshot_data, currency_data = parse_txt_content(txt_content, snapshot_time)
        
        # 保存到JSONL
        manager = QueryJSONLManager()
        manager.upsert_snapshot(snapshot_data)
        
        for coin in currency_data:
            manager.upsert_coin(coin)
        
        return jsonify({
            'success': True,
            'message': f'成功导入 {len(currency_data)} 个币种的数据',
            'snapshot_time': snapshot_time,
            'coin_count': len(currency_data)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
'''
    
    return api_code

def main():
    print("=" * 60)
    print("Query API JSONL 更新代码生成器")
    print("=" * 60)
    
    code = create_jsonl_api_code()
    
    print("\n以下代码需要手动添加到 app_new.py:")
    print("=" * 60)
    print(code)
    print("=" * 60)
    
    print("\n📝 使用说明:")
    print("1. 在 app_new.py 的导入部分添加:")
    print("   from source_code.query_jsonl_manager import QueryJSONLManager")
    print("\n2. 替换以下路由的函数:")
    print("   - @app.route('/api/query')")
    print("   - @app.route('/api/latest')")
    print("   - @app.route('/api/query/latest')")
    print("   - @app.route('/api/query/batch-import', methods=['POST'])")
    print("\n3. 重启Flask应用:")
    print("   pm2 restart flask-app")
    
    # 保存到文件
    with open('/home/user/webapp/query_api_jsonl_code.txt', 'w', encoding='utf-8') as f:
        f.write(code)
    
    print("\n✅ 代码已保存到: query_api_jsonl_code.txt")

if __name__ == '__main__':
    main()
