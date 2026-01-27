#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TXT文件透明标签数据提取器
从TXT文件顶部提取首页监控所需的数据
"""
import re
from datetime import datetime
from typing import Dict, Optional

def extract_dashboard_data(txt_content: str, snapshot_time: str) -> Optional[Dict]:
    """
    从TXT文件中提取首页监控数据（透明标签部分）
    
    Args:
        txt_content: TXT文件内容
        snapshot_time: 快照时间 (格式: YYYY-MM-DD HH:MM:SS)
    
    Returns:
        Dict: 首页监控数据，如果解析失败返回None
    """
    
    try:
        # 提取透明标签数据
        data = {
            'snapshot_time': snapshot_time,
            'snapshot_date': snapshot_time.split()[0] if ' ' in snapshot_time else snapshot_time[:10],
            'created_at': datetime.now().isoformat()
        }
        
        # 1. 急涨总和
        rush_up_match = re.search(r'透明标签_急涨总和=急涨：(\d+)', txt_content)
        data['rush_up'] = int(rush_up_match.group(1)) if rush_up_match else 0
        
        # 2. 急跌总和
        rush_down_match = re.search(r'透明标签_急跌总和=急跌：(\d+)', txt_content)
        data['rush_down'] = int(rush_down_match.group(1)) if rush_down_match else 0
        
        # 3. 五种状态
        status_match = re.search(r'透明标签_五种状态=状态：(.+?)[\r\n]', txt_content)
        data['status'] = status_match.group(1).strip() if status_match else '未知'
        
        # 4. 急涨急跌比值
        ratio_match = re.search(r'透明标签_急涨急跌比值=比值：([\d.]+)', txt_content)
        if ratio_match:
            data['ratio'] = float(ratio_match.group(1))
        else:
            # 如果没有比值，尝试从文本中提取
            ratio_text_match = re.search(r'透明标签_急涨急跌比值=比值：(.+?)[\r\n]', txt_content)
            if ratio_text_match and '数据不足' in ratio_text_match.group(1):
                data['ratio'] = 0.0
                data['ratio_text'] = '数据不足'
            else:
                data['ratio'] = 0.0
        
        # 5. 绿色数量
        green_count_match = re.search(r'透明标签_绿色数量=(\d+)', txt_content)
        data['green_count'] = int(green_count_match.group(1)) if green_count_match else 0
        
        # 6. 百分比
        percent_match = re.search(r'透明标签_百分比=(\d+)%', txt_content)
        data['green_percent'] = int(percent_match.group(1)) if percent_match else 0
        
        # 7. 计次
        count_match = re.search(r'透明标签_计次=(\d+)', txt_content)
        data['count'] = int(count_match.group(1)) if count_match else 0
        
        # 8. 全绿得分
        all_green_match = re.search(r'透明标签_全绿得分=全绿(\d+)%\s+(\d+)\s+(\d+)', txt_content)
        if all_green_match:
            data['all_green_percent'] = int(all_green_match.group(1))
            data['all_green_score'] = int(all_green_match.group(2))
            data['all_green_count'] = int(all_green_match.group(3))
        else:
            data['all_green_percent'] = 0
            data['all_green_score'] = 0
            data['all_green_count'] = 0
        
        # 9. 比价最低得分
        price_lowest_match = re.search(r'透明标签_比价最低得分=比价最低\s+(\d+)\s+(\d+)', txt_content)
        if price_lowest_match:
            data['price_lowest'] = int(price_lowest_match.group(1))
            data['price_lowest_count'] = int(price_lowest_match.group(2))
        else:
            data['price_lowest'] = 0
            data['price_lowest_count'] = 0
        
        # 10. 仓位得分
        position_match = re.search(r'透明标签_仓位得分=(.+?)\s+(\d+)', txt_content)
        if position_match:
            data['position_text'] = position_match.group(1).strip()
            data['position_count'] = int(position_match.group(2))
        else:
            data['position_text'] = ''
            data['position_count'] = 0
        
        # 11. 急跌数量
        rush_down_count_match = re.search(r'透明标签_急跌数量=急跌数量\s+计次\s+(\d+)\s+(\d+)', txt_content)
        if rush_down_count_match:
            data['rush_down_total'] = int(rush_down_count_match.group(1))
            data['rush_down_count'] = int(rush_down_count_match.group(2))
        else:
            data['rush_down_total'] = 0
            data['rush_down_count'] = 0
        
        # 12. 差值结果
        diff_match = re.search(r'透明标签_差值结果=差值：([+-]?\d+)', txt_content)
        if diff_match:
            data['diff'] = int(diff_match.group(1))
        else:
            # 尝试提取文本
            diff_text_match = re.search(r'透明标签_差值结果=差值：(.+?)[\r\n]', txt_content)
            if diff_text_match and '数据不足' in diff_text_match.group(1):
                data['diff'] = 0
                data['diff_text'] = '数据不足'
            else:
                # 从急涨急跌计算差值
                data['diff'] = data['rush_up'] - data['rush_down']
        
        # 计算比值（如果没有提供）
        if data['ratio'] == 0.0 and data['rush_down'] > 0:
            data['ratio'] = round(data['rush_up'] / data['rush_down'], 2)
        
        return data
        
    except Exception as e:
        print(f"❌ 解析透明标签数据失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    # 测试代码
    test_content = """透明标签_急涨总和=急涨：34
透明标签_急跌总和=急跌：5
透明标签_五种状态=状态：急涨强势
透明标签_急涨急跌比值=比值：6.8
透明标签_绿色数量=3
透明标签_百分比=10%
透明标签_计次=4
透明标签_全绿得分=全绿10% 10 4
透明标签_比价最低得分=比价最低 0 0
透明标签_仓位得分=比价创新高 仓位加10% 1
透明标签_急跌数量=急跌数量 计次 25 5
透明标签_差值结果=差值：29
[超级列表框_首页开始]
"""
    
    result = extract_dashboard_data(test_content, '2026-01-14 18:00:00')
    
    if result:
        print("✅ 解析成功!")
        print(f"急涨: {result['rush_up']}")
        print(f"急跌: {result['rush_down']}")
        print(f"计次: {result['count']}")
        print(f"差值: {result['diff']}")
        print(f"比值: {result['ratio']}")
        print(f"状态: {result['status']}")
    else:
        print("❌ 解析失败")
