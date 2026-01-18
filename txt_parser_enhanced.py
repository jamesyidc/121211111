"""
增强版TXT文件解析器
支持提取透明标签聚合数据和完整的币种字段
"""
import re
from datetime import datetime

def parse_transparent_labels(content):
    """
    解析TXT文件中的透明标签聚合数据
    
    返回字典包含:
    - rush_up_total: 急涨总和
    - rush_down_total: 急跌总和
    - status: 五种状态
    - ratio: 急涨急跌比值
    - count_aggregate: 计次
    - diff_total: 差值结果
    - price_lowest: 比价最低得分
    - price_newhigh: 仓位得分(比价创新高)
    """
    aggregate_data = {}
    
    lines = content.strip().split('\n')
    
    # 定义透明标签映射
    label_mappings = {
        '透明标签_急涨总和': 'rush_up_total',
        '透明标签_急跌总和': 'rush_down_total',
        '透明标签_五种状态': 'status',
        '透明标签_急涨急跌比值': 'ratio',
        '透明标签_计次': 'count_aggregate',
        '透明标签_差值结果': 'diff_total',
        '透明标签_比价最低得分': 'price_lowest',
        '透明标签_仓位得分': 'price_newhigh'
    }
    
    for line in lines:
        line = line.strip().strip('\r')
        
        if not line.startswith('透明标签'):
            continue
        
        # 解析格式: 透明标签_字段名=显示文本：值 或 透明标签_字段名=值
        for label_key, field_name in label_mappings.items():
            if line.startswith(label_key):
                # 提取等号后面的内容
                if '=' not in line:
                    continue
                    
                value_part = line.split('=', 1)[1].strip()
                
                # 根据字段类型转换
                if field_name in ['rush_up_total', 'rush_down_total', 'count_aggregate', 'price_lowest', 'price_newhigh']:
                    try:
                        # 提取数字部分（可能在冒号后面）
                        match = re.search(r'-?\d+', value_part)
                        if match:
                            aggregate_data[field_name] = int(match.group())
                        else:
                            aggregate_data[field_name] = 0
                    except (ValueError, AttributeError):
                        aggregate_data[field_name] = 0
                
                elif field_name in ['ratio', 'diff_total']:
                    try:
                        # 提取数字部分（可能是小数或负数）
                        match = re.search(r'-?\d+\.?\d*', value_part)
                        if match:
                            aggregate_data[field_name] = float(match.group())
                        else:
                            aggregate_data[field_name] = 0.0
                    except (ValueError, AttributeError):
                        aggregate_data[field_name] = 0.0
                
                elif field_name == 'status':
                    # 状态是文本，提取冒号后的内容
                    if '：' in value_part:
                        aggregate_data[field_name] = value_part.split('：', 1)[1].strip()
                    elif ':' in value_part:
                        aggregate_data[field_name] = value_part.split(':', 1)[1].strip()
                    else:
                        aggregate_data[field_name] = value_part.strip()
                
                break
    
    return aggregate_data

def parse_coin_records(content, snapshot_time):
    """
    解析币种数据行
    
    原格式: 序号|币名|急涨|急跌|更新时间|历史高位|高位时间|距离高位跌幅|24涨幅|+4%|-3%|排行|当前价格|最高占比|最低占比|
    
    新增字段:
    - max_ratio: 最高占比 (用于计算优先级)
    - min_ratio: 最低占比 (用于计算优先级)
    
    返回币种记录列表
    """
    records = []
    lines = content.strip().split('\n')
    
    # 找到数据开始标记
    start_index = -1
    for i, line in enumerate(lines):
        if '[超级列表框_首页开始]' in line or '[超级列表框_首页开始]' in line.strip('\r'):
            start_index = i + 1
            break
    
    if start_index == -1:
        start_index = 0
    
    # 解析每一行
    for line in lines[start_index:]:
        line = line.strip().strip('\r')
        
        # 跳过空行、注释、透明标签、标记行
        if not line or line.startswith('#') or line.startswith('透明标签') or '[' in line:
            continue
        
        parts = line.split('|')
        if len(parts) < 16:  # 至少需要16个字段（包含最高占比和最低占比）
            continue
        
        try:
            inst_id = parts[1].strip()
            if not inst_id:
                continue
            
            # 提取基础数据 (根据实际TXT格式)
            # 格式: 序号|币名|涨速|急涨|急跌|更新时间|当前价格|历史高位日期|距离高位跌幅|24h涨跌幅|?|?|排行|历史高位价格|最高占比|最低占比
            # 索引:  0   1   2   3   4     5           6          7             8          9       10 11  12       13         14      15
            # 重要: parts[2]=涨速(浮点), parts[3]=急涨次数(整数), parts[4]=急跌次数(整数)
            # 字段命名规范:
            # - speed: 涨速 (parts[2])
            # - rush_up: 急涨次数 (parts[3])
            # - rush_down: 急跌次数 (parts[4])
            
            # 涨速 (speed / change rate)
            speed_str = parts[2].strip() if len(parts) > 2 and parts[2] else '0'
            speed = float(speed_str) if speed_str and speed_str != 'NaN' else 0.0
            
            # 急涨次数
            rush_up = int(float(parts[3])) if len(parts) > 3 and parts[3] and parts[3].strip() else 0
            
            # 急跌次数
            rush_down = int(float(parts[4])) if len(parts) > 4 and parts[4] and parts[4].strip() else 0
            
            update_time = parts[5].strip() if len(parts) > 5 and parts[5] else None
            current_price = float(parts[6]) if len(parts) > 6 and parts[6] else 0.0
            high_time = parts[7].strip() if len(parts) > 7 and parts[7] else None
            drop_from_high_str = parts[8].replace('%', '').strip() if len(parts) > 8 and parts[8] else '0'
            drop_from_high = float(drop_from_high_str) if drop_from_high_str and drop_from_high_str != 'NaN' else 0.0
            change_24h_str = parts[9].replace('%', '').strip() if len(parts) > 9 and parts[9] else '0'
            change_24h = float(change_24h_str) if change_24h_str and change_24h_str != 'NaN' else 0.0
            ranking = int(parts[12]) if len(parts) > 12 and parts[12] else 0
            high_price = float(parts[13]) if len(parts) > 13 and parts[13] else 0.0
            count = rush_down  # count字段保存急跌次数，用于向后兼容
            vol_24h = 0.0  # TXT中没有24h交易量字段
            
            # 提取最高占比和最低占比 (去除百分号)
            max_ratio_str = parts[14].replace('%', '').strip() if len(parts) > 14 and parts[14] else '0'
            min_ratio_str = parts[15].replace('%', '').strip() if len(parts) > 15 and parts[15] else '0'
            
            max_ratio = float(max_ratio_str) if max_ratio_str else 0.0
            min_ratio = float(min_ratio_str) if min_ratio_str else 0.0
            
            # 计算diff和status
            diff = rush_up - rush_down
            if diff > 0:
                status = '急涨'
            elif diff < 0:
                status = '急跌'
            else:
                status = '平稳'
            
            # 提取日期 (处理字符串或datetime对象)
            if isinstance(snapshot_time, str):
                snapshot_date = snapshot_time.split()[0] if ' ' in snapshot_time else snapshot_time
            else:
                # datetime对象
                snapshot_date = snapshot_time.strftime('%Y-%m-%d')
                snapshot_time = snapshot_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # 创建记录
            record = {
                'snapshot_date': snapshot_date,
                'snapshot_time': snapshot_time,
                'inst_id': inst_id,
                'symbol': inst_id,  # 添加 symbol 字段
                'current_price': current_price,  # 当前价格
                'last_price': current_price,  # 兼容旧字段名
                'high_price': high_price,  # 历史高位价格
                'high_time': high_time,  # 历史高位时间
                'drop_from_high': drop_from_high,  # 距离高位跌幅
                'update_time': update_time,  # 更新时间
                'ranking': ranking,  # 排行
                'speed': speed,  # 涨速 (parts[2])
                'rush_up': rush_up,  # 急涨次数 (parts[3])
                'rush_down': rush_down,  # 急跌次数 (parts[4])
                'diff': diff,
                'status': status,
                'change_24h': change_24h,
                'max_ratio': max_ratio,
                'min_ratio': min_ratio,
                'count': count,
                'vol_24h': vol_24h,
                'high_24h': None,
                'low_24h': None,
                'created_at': datetime.now().isoformat()
            }
            
            records.append(record)
            
        except (ValueError, IndexError) as e:
            # 记录解析失败的行，但继续处理其他行
            print(f"⚠️  解析失败 (行被跳过): {e}")
            print(f"    问题行: {line[:100]}...")  # 只打印前100个字符
            continue
    
    return records

def parse_txt_file_enhanced(content, snapshot_time):
    """
    增强版TXT文件解析
    
    返回:
    - aggregate_data: 透明标签聚合数据
    - coin_records: 币种记录列表
    - error: 错误信息（如果有）
    """
    try:
        # 解析透明标签聚合数据
        aggregate_data = parse_transparent_labels(content)
        
        # 解析币种记录
        coin_records = parse_coin_records(content, snapshot_time)
        
        return aggregate_data, coin_records, None
        
    except Exception as e:
        return {}, [], f"解析TXT文件失败: {e}"

if __name__ == "__main__":
    # 测试代码
    sample_content = """
透明标签_急涨总和=急涨：14
透明标签_急跌总和=急跌：18
透明标签_五种状态=状态：震荡无序
透明标签_急涨急跌比值=比值：0.29
透明标签_计次=3
透明标签_差值结果=差值：-4
透明标签_比价最低得分=比价最低 0 0
透明标签_仓位得分=比价创新高 仓位加10% 1

[超级列表框_首页开始]
1|BTC|1|0|2026-01-14 22:00:00|150000|2025-10-10|15.5|-2.5|5.0|-3.0|1|126259.48|85.5%|125.3%
2|ETH|1|0|2026-01-14 22:00:00|5000|2025-11-15|8.2|-3.3|4.2|-2.8|2|4954.59|78.2%|118.5%
"""
    
    aggregate, coins, error = parse_txt_file_enhanced(sample_content, '2026-01-14 22:00:00')
    
    print("=== 聚合数据 ===")
    for key, value in aggregate.items():
        print(f"{key}: {value}")
    
    print(f"\n=== 币种记录 ({len(coins)}条) ===")
    for coin in coins:
        print(f"{coin['inst_id']}: 急涨={coin['rush_up']}, 急跌={coin['rush_down']}, "
              f"最高占比={coin['max_ratio']}%, 最低占比={coin['min_ratio']}%")
    
    if error:
        print(f"\n❌ 错误: {error}")
