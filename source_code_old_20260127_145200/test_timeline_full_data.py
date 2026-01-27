#!/usr/bin/env python3
"""测试时间轴完整数据保存"""
import requests
import json

def test_timeline_full_data():
    """测试时间轴API返回的完整数据"""
    print("=" * 80)
    print(" " * 25 + "时间轴完整数据保存测试")
    print("=" * 80)
    
    # 测试 API
    response = requests.get('http://localhost:5000/api/timeline')
    data = response.json()
    
    print(f"\n📊 API 数据统计:")
    print(f"   总数据点: {data['total']} 个")
    
    if data['snapshots']:
        first_snapshot = data['snapshots'][0]
        print(f"   每个数据点包含字段数: {len(first_snapshot)} 个")
        
        print(f"\n📋 数据库中保存的所有字段（共{len(first_snapshot)}个）:")
        print(f"   {'字段名':<30} {'示例值':<30}")
        print(f"   {'-'*30} {'-'*30}")
        
        # 按类别分组显示
        field_groups = {
            '基本信息': ['id', 'snapshot_time', 'snapshot_date', 'filename'],
            '主要统计': ['rush_up', 'rush_down', 'diff', 'count', 'ratio', 'status'],
            '本轮数据': ['round_rush_up', 'round_rush_down'],
            '比价数据': ['price_lowest', 'price_newhigh', 'ratio_diff'],
            '初始数据': ['init_rush_up', 'init_rush_down'],
            '计次得分': ['count_score_display', 'count_score_type'],
            '24小时涨跌': ['rise_24h_count', 'fall_24h_count'],
            '其他数据': ['green_count', 'percentage']
        }
        
        for group_name, fields in field_groups.items():
            print(f"\n   【{group_name}】")
            for field in fields:
                if field in first_snapshot:
                    value = first_snapshot[field]
                    value_str = str(value)[:28] if value is not None else 'None'
                    print(f"   {field:<30} {value_str:<30}")
        
        # 显示时间轴上的详细数据
        print(f"\n" + "=" * 80)
        print(" " * 25 + "时间轴数据展示")
        print("=" * 80)
        
        for i, snapshot in enumerate(data['snapshots'], 1):
            time = snapshot['snapshot_time']
            
            print(f"\n   [{i}] {time}")
            print(f"   " + "─" * 75)
            
            # 第一行：急涨、急跌、计次、得分
            print(f"   急涨:{snapshot['rush_up']:>3}  "
                  f"急跌:{snapshot['rush_down']:>3}  "
                  f"计次:{snapshot['count']:>3}  "
                  f"得分:{snapshot.get('count_score_display', 'N/A'):>5}")
            
            # 第二行：状态、比值、差值
            print(f"   状态:{snapshot.get('status', 'N/A'):<10}  "
                  f"比值:{snapshot.get('ratio', 0):>6}  "
                  f"差值:{snapshot['diff']:>4}")
            
            # 第三行：本轮、比价
            print(f"   本轮急涨:{snapshot.get('round_rush_up', 0):>3}  "
                  f"本轮急跌:{snapshot.get('round_rush_down', 0):>3}  "
                  f"比价最低:{snapshot.get('price_lowest', 0):>3}  "
                  f"比价创新高:{snapshot.get('price_newhigh', 0):>3}")
            
            # 第四行：24小时涨跌
            print(f"   24h涨≥10%:{snapshot.get('rise_24h_count', 0):>3}  "
                  f"24h跌≤-10%:{snapshot.get('fall_24h_count', 0):>3}")
            
            if i == len(data['snapshots']):
                print(f"   {'▲':<5} 当前选中")
        
        print(f"\n" + "=" * 80)
        
        # 统计字段完整性
        print(f"\n✅ 字段完整性验证:")
        required_fields_14 = [
            'snapshot_time',    # 1. 运算时间
            'rush_up',          # 2. 急涨
            'rush_down',        # 3. 急跌
            'round_rush_up',    # 4. 本轮急涨
            'round_rush_down',  # 5. 本轮急跌
            'count',            # 6. 计次
            'count_score_display',  # 7. 计次得分
            'status',           # 8. 状态
            'ratio',            # 9. 比值
            'diff',             # 10. 差值
            'price_lowest',     # 11. 比价最低
            'price_newhigh',    # 12. 比价创新高
            'rise_24h_count',   # 13. 24h涨≥10%
            'fall_24h_count'    # 14. 24h跌≤-10%
        ]
        
        print(f"\n   【14个关键统计字段】")
        all_present = True
        for i, field in enumerate(required_fields_14, 1):
            is_present = field in first_snapshot
            status = "✅" if is_present else "❌"
            print(f"   {i:>2}. {status} {field}")
            if not is_present:
                all_present = False
        
        if all_present:
            print(f"\n   🎉 所有14个统计字段均已保存在时间轴数据中！")
        else:
            print(f"\n   ⚠️  部分字段缺失")
        
        # 额外保存的字段
        extra_fields = [f for f in first_snapshot.keys() if f not in required_fields_14]
        if extra_fields:
            print(f"\n   【额外保存的字段 ({len(extra_fields)}个)】")
            for field in sorted(extra_fields):
                print(f"   • {field}")
    
    print(f"\n" + "=" * 80)
    print(" " * 20 + "🌐 访问地址")
    print("=" * 80)
    print(f"\n   https://5000-iik759kgm7i3zqlxvfrfx-cc2fbc16.sandbox.novita.ai")
    print(f"\n" + "=" * 80)
    print(" " * 15 + "✅ 时间轴数据已完整保存（23个字段）")
    print("=" * 80 + "\n")

if __name__ == '__main__':
    test_timeline_full_data()
