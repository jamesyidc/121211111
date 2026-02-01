@app.route('/api/anchor-system/current-positions')
def get_current_positions():
    """获取当前持仓情况 - 模拟盘直接读取数据库，实盘从 OKEx API 实时获取"""
    try:
        import sys
        import sqlite3
        from datetime import datetime
        sys.path.append('/home/user/webapp/source_code')
        from anchor_system import get_positions_from_okex
        
        # 获取交易模式（默认为 paper 模拟盘）
        trade_mode = request.args.get('trade_mode', 'paper')
        
        # 连接数据库，获取维护后的开仓价格和锚点单标记
        DB_PATH = '/home/user/webapp/databases/trading_decision.db'
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 从数据库读取数据 - 联合查询维护价格表
        cursor.execute('''
            SELECT 
                p.inst_id, 
                p.pos_side, 
                COALESCE(amp.maintenance_price, p.open_price) as open_price,
                p.open_size, 
                p.updated_time, 
                p.mark_price, 
                p.profit_rate, 
                p.upl, 
                p.lever, 
                p.margin,
                amp.original_open_price,
                amp.maintenance_count,
                p.is_anchor
            FROM position_opens p
            LEFT JOIN anchor_maintenance_prices amp 
                ON p.inst_id = amp.inst_id 
                AND p.pos_side = amp.pos_side 
                AND p.trade_mode = amp.trade_mode
            WHERE p.trade_mode = ?
        ''', (trade_mode,))
        
        db_positions = cursor.fetchall()
        conn.close()
        
        # 如果是模拟盘，直接使用数据库数据
        if trade_mode == 'paper':
            position_list = []
            for row in db_positions:
                profit_rate = row['profit_rate'] if row['profit_rate'] is not None else 0.0
                
                # 判断状态
                status = '监控中'
                status_class = 'normal'
                if profit_rate >= 40:
                    status = '接近盈利目标'
                    status_class = 'profit'
                elif profit_rate <= -10:
                    status = '接近止损'
                    status_class = 'loss'
                
                position_list.append({
                    'inst_id': row['inst_id'],
                    'pos_side': row['pos_side'],
                    'pos_size': abs(float(row['open_size'])),
                    'avg_price': float(row['open_price']),
                    'mark_price': float(row['mark_price']) if row['mark_price'] else 0.0,
                    'lever': int(row['lever']) if row['lever'] else 10,
                    'upl': float(row['upl']) if row['upl'] else 0.0,
                    'margin': float(row['margin']) if row['margin'] else 0.0,
                    'profit_rate': profit_rate,
                    'status': status,
                    'status_class': status_class,
                    'is_anchor': int(row['is_anchor']) if row['is_anchor'] else 0
                })
            
            return jsonify({
                'success': True,
                'positions': position_list,
                'total': len(position_list),
                'trade_mode': trade_mode
            })
        
        # 实盘模式：从 OKEx API 获取实时持仓
        okex_positions = get_positions_from_okex()
        
        if not okex_positions or len(okex_positions) == 0:
            return jsonify({
                'success': True,
                'positions': [],
                'total': 0,
                'trade_mode': trade_mode,
                'message': 'OKEx API返回空持仓'
            })
        
        # 将数据库记录转换为字典（用于查找锚点单标记和维护价格）
        db_positions_dict = {(row['inst_id'], row['pos_side']): row for row in db_positions}
        
        position_list = []
        for pos in okex_positions:
            inst_id = pos.get('instId')
            pos_side = pos.get('posSide')
            pos_value = float(pos.get('pos', 0))
            
            # 跳过持仓量为0的
            if pos_value == 0:
                continue
            
            # 查找数据库记录（获取锚点单标记和维护价格）
            db_record = db_positions_dict.get((inst_id, pos_side))
            
            # 从OKEx获取实时数据
            okex_avg_price = float(pos.get('avgPx', 0))
            mark_price = float(pos.get('markPx', 0))
            lever = int(pos.get('lever', 10))
            upl = float(pos.get('upl', 0))
            margin = float(pos.get('margin', 0))
            
            # 如果数据库中有记录，使用数据库的开仓价格（可能是维护后的）
            if db_record:
                avg_price = float(db_record['open_price'])
                is_anchor = int(db_record['is_anchor']) if db_record['is_anchor'] else 0
                # 重新计算收益率（使用维护价格）
                if margin > 0:
                    # 使用实时未实现盈亏除以保证金
                    profit_rate = (upl / margin) * 100
                else:
                    # 备用计算：价格变动率 * 杠杆
                    if pos_side == 'short':
                        profit_rate = ((avg_price - mark_price) / avg_price) * lever * 100
                    else:  # long
                        profit_rate = ((mark_price - avg_price) / avg_price) * lever * 100
            else:
                # 没有数据库记录，使用OKEx返回的价格
                avg_price = okex_avg_price
                is_anchor = 0
                # 计算收益率
                if margin > 0:
                    profit_rate = (upl / margin) * 100
                else:
                    if pos_side == 'short':
                        profit_rate = ((avg_price - mark_price) / avg_price) * lever * 100
                    else:
                        profit_rate = ((mark_price - avg_price) / avg_price) * lever * 100
            
            # 判断状态
            status = '监控中'
            status_class = 'normal'
            if profit_rate >= 40:
                status = '接近盈利目标'
                status_class = 'profit'
            elif profit_rate <= -10:
                status = '接近止损'
                status_class = 'loss'
            
            position_list.append({
                'inst_id': inst_id,
                'pos_side': pos_side,
                'pos_size': abs(pos_value),
                'avg_price': avg_price,
                'mark_price': mark_price,
                'lever': lever,
                'upl': upl,
                'margin': margin,
                'profit_rate': profit_rate,
                'status': status,
                'status_class': status_class,
                'is_anchor': is_anchor
            })
        
        return jsonify({
            'success': True,
            'positions': position_list,
            'total': len(position_list),
            'trade_mode': trade_mode,
            'message': f'从OKEx API获取到{len(position_list)}个仓位'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })
