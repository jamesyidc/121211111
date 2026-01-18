#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动触发Google Drive文件夹更新和TXT导入
"""

import sys
sys.path.insert(0, '/home/user/webapp')

from gdrive_detector_jsonl import check_and_update_folder, get_txt_files, download_txt_file, parse_txt_content, save_to_jsonl, load_config, get_beijing_time
from source_code.query_jsonl_manager import QueryJSONLManager
import json

def main():
    print("=" * 60)
    print("Google Drive 手动更新工具")
    print("=" * 60)
    
    # 1. 检查并更新文件夹
    print("\n[步骤1] 检查并更新今天的文件夹...")
    folder_result = check_and_update_folder()
    print(f"结果: {json.dumps(folder_result, indent=2, ensure_ascii=False)}")
    
    if not folder_result.get('success'):
        print(f"❌ 文件夹更新失败: {folder_result.get('error')}")
        return
    
    # 2. 加载配置
    config = load_config()
    folder_id = config.get('folder_id')
    today_str = get_beijing_time().strftime('%Y-%m-%d')
    
    print(f"\n[步骤2] 获取今天 ({today_str}) 的TXT文件列表...")
    
    # 3. 获取TXT文件列表
    txt_files = get_txt_files(folder_id, today_str)
    print(f"找到 {len(txt_files)} 个TXT文件")
    
    if not txt_files:
        print(f"❌ 未找到今天的TXT文件")
        return
    
    # 显示最新的3个文件
    print(f"\n最新的文件:")
    for i, filename in enumerate(txt_files[:3], 1):
        print(f"  {i}. {filename}")
    
    # 4. 下载并解析最新的TXT文件
    latest_txt = txt_files[0]
    print(f"\n[步骤3] 下载并解析最新TXT: {latest_txt}")
    
    content = download_txt_file(folder_id, latest_txt)
    
    if content.startswith("下载失败"):
        print(f"❌ {content}")
        return
    
    print(f"✅ 下载成功，内容长度: {len(content)} 字符")
    
    # 5. 解析内容
    # 从文件名提取时间
    time_part = latest_txt.replace(f"{today_str}_", "").replace(".txt", "")
    hour = time_part[:2]
    minute = time_part[2:]
    snapshot_time = f"{today_str} {hour}:{minute}:00"
    
    print(f"\n[步骤4] 解析TXT内容 (快照时间: {snapshot_time})...")
    
    snapshot_data, currency_data = parse_txt_content(content, snapshot_time)
    
    print(f"\n快照数据: {json.dumps(snapshot_data, indent=2, ensure_ascii=False)}")
    print(f"\n币种数量: {len(currency_data)}")
    
    if currency_data:
        print(f"\n前3个币种:")
        for i, coin in enumerate(currency_data[:3], 1):
            print(f"  {i}. {coin['symbol']}: 优先级={coin['priority']}, 等级={coin['priority_level']}, 最高占比={coin['ratio1']:.1f}%, 最低占比={coin['ratio2']:.1f}%")
    
    # 6. 保存到JSONL
    print(f"\n[步骤5] 保存到JSONL...")
    
    manager = QueryJSONLManager()
    
    # 保存快照数据
    manager.upsert_snapshot(snapshot_data)
    
    # 保存币种数据
    for coin in currency_data:
        manager.upsert_coin(coin)
    
    print(f"✅ 已保存到JSONL")
    print(f"  - 快照: 1 条")
    print(f"  - 币种: {len(currency_data)} 条")
    
    # 7. 验证
    print(f"\n[步骤6] 验证数据...")
    
    latest_snapshot = manager.get_latest_snapshot()
    latest_coins = manager.get_coins_by_time(snapshot_time)
    
    print(f"\n最新快照时间: {latest_snapshot.get('snapshot_time')}")
    print(f"币种数量: {len(latest_coins)}")
    
    # 按优先级分组统计
    priority_stats = {}
    for coin in latest_coins:
        level = coin.get('priority_level', '未知')
        priority_stats[level] = priority_stats.get(level, 0) + 1
    
    print(f"\n优先级分布:")
    for level in sorted(priority_stats.keys()):
        print(f"  {level}: {priority_stats[level]} 个")
    
    print("\n" + "=" * 60)
    print("✅ 全部完成！")
    print("=" * 60)

if __name__ == '__main__':
    main()
