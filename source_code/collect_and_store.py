#!/usr/bin/env python3
"""
完整的数据采集和存储脚本
包含计次得分和优先级计算功能
"""
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta
import pytz
import re
import sqlite3

PARENT_FOLDER_ID = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"  # 首页数据 (包含所有日期文件夹)
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def calculate_count_score_display(count, snapshot_time):
    """计算计次得分显示字符串"""
    from calculate_count_score import calculate_count_score as calc_score
    display, _ = calc_score(snapshot_time, count)
    return display

def calculate_count_score_type(count, snapshot_time):
    """计算计次得分类型"""
    from calculate_count_score import calculate_count_score as calc_score
    _, score_type = calc_score(snapshot_time, count)
    return score_type

def calculate_count_score(count_times, current_hour):
    """
    根据计次和当前时间计算得分（旧版兼容函数）
    返回: (星级数量, 星级类型, 描述)
    
    注意：此函数已废弃，保留仅为兼容性
    请使用 calculate_count_score.py 中的统一版本
    
    规则（2026-01-18 修正）：
    - 实心星表示好（计次少）
    - 空心星表示差（计次多）
    """
    # 确定时间段
    if current_hour < 6:
        # 截止6点前
        if count_times <= 1:
            return (3, "实心", "★★★")
        elif 1 < count_times <= 2:
            return (2, "实心", "★★")
        elif 2 < count_times <= 3:
            return (1, "实心", "★")
        elif 3 < count_times <= 4:
            return (1, "空心", "☆")
        elif 4 < count_times <= 5:
            return (2, "空心", "☆☆")
        else:  # count_times > 5
            return (3, "空心", "☆☆☆")
            
    elif 6 <= current_hour < 12:
        # 截止12点前
        if count_times <= 2:
            return (3, "实心", "★★★")
        elif 2 < count_times <= 3:
            return (2, "实心", "★★")
        elif 3 < count_times <= 4:
            return (1, "实心", "★")
        elif 4 < count_times <= 5:
            return (0, "中性", "")  # 无评级
        elif 5 < count_times <= 6:
            return (1, "空心", "☆")
        elif 6 < count_times <= 7:
            return (2, "空心", "☆☆")
        else:  # count_times > 7
            return (3, "空心", "☆☆☆")
            
    elif 12 <= current_hour < 18:
        # 截止18点前
        if count_times <= 3:
            return (3, "实心", "★★★")
        elif 3 < count_times <= 4:
            return (2, "实心", "★★")
        elif 4 < count_times <= 5:
            return (1, "实心", "★")
        elif 5 < count_times <= 7:
            return (0, "中性", "")  # 无评级
        elif 7 < count_times <= 8:
            return (1, "空心", "☆")
        elif 8 < count_times <= 9:
            return (2, "空心", "☆☆")
        else:  # count_times > 9
            return (3, "空心", "☆☆☆")
            
    else:  # 18 <= current_hour < 24
        # 截止24点前
        if count_times <= 4:
            return (3, "实心", "★★★")
        elif 4 < count_times <= 5:
            return (2, "实心", "★★")
        elif 5 < count_times <= 6:
            return (1, "实心", "★")
        elif 6 < count_times <= 9:
            return (0, "中性", "")  # 无评级
        elif 9 < count_times <= 10:
            return (1, "空心", "☆")
        elif 10 < count_times <= 12:
            return (2, "空心", "☆☆")
        else:  # count_times > 12
            return (3, "空心", "☆☆☆")

def calculate_priority_level(high_ratio_str, low_ratio_str):
    """
    根据最高占比和最低占比计算优先级等级
    
    等级1: 最高占比>90   最低占比>120
    等级2: 最高占比>80   最低占比>120
    等级3: 最高占比>90   最低占比>110
    等级4: 最高占比>70   最低占比>120
    等级5: 最高占比>80   最低占比>110
    等级6: 最高占比<80   最低占比<110
    """
    try:
        high_ratio = float(high_ratio_str.replace('%', '')) if high_ratio_str else 0
        low_ratio = float(low_ratio_str.replace('%', '')) if low_ratio_str else 0
        
        if high_ratio > 90 and low_ratio > 120:
            return "等级1"
        elif high_ratio > 80 and low_ratio > 120:
            return "等级2"
        elif high_ratio > 90 and low_ratio > 110:
            return "等级3"
        elif high_ratio > 70 and low_ratio > 120:
            return "等级4"
        elif high_ratio > 80 and low_ratio > 110:
            return "等级5"
        else:
            return "等级6"
    except:
        return "未知"

def get_today_folder_id():
    """根据当前日期自动查找对应的文件夹ID"""
    now = datetime.now(BEIJING_TZ)
    today_folder_name = now.strftime('%Y-%m-%d')
    
    print(f"🔍 查找今天的文件夹: {today_folder_name}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 访问父文件夹
        parent_url = f"https://drive.google.com/drive/folders/{PARENT_FOLDER_ID}"
        page.goto(parent_url, timeout=20000)
        page.wait_for_timeout(3000)
        
        # 查找今天的文件夹
        items = page.query_selector_all('[data-id]')
        
        for item in items:
            try:
                tooltip = item.get_attribute('data-tooltip') or ''
                data_id = item.get_attribute('data-id') or ''
                
                if today_folder_name in tooltip:
                    print(f"✅ 找到今天的文件夹: {tooltip}")
                    print(f"   ID: {data_id}")
                    browser.close()
                    return data_id
            except:
                pass
        
        browser.close()
        print(f"❌ 未找到今天的文件夹: {today_folder_name}")
        return None

def get_latest_file_data():
    """获取最新文件数据"""
    now = datetime.now(BEIJING_TZ)
    current_hour = now.hour
    
    print(f"当前北京时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"当前小时: {current_hour}")
    
    # 自动获取今天的文件夹ID
    folder_id = get_today_folder_id()
    if not folder_id:
        print("❌ 无法获取今天的文件夹ID，采集失败")
        return None
    
    # 生成候选文件名
    candidates = []
    for i in range(0, 4):
        # 使用timedelta来正确处理时间减法，避免分钟数为负
        check_time = now.replace(second=0, microsecond=0)
        # 先对齐到10分钟整点
        aligned_minute = (check_time.minute // 10) * 10
        check_time = check_time.replace(minute=aligned_minute)
        # 然后减去i*10分钟
        check_time = check_time - timedelta(minutes=i * 10)
        filename = check_time.strftime('%Y-%m-%d_%H%M.txt')
        candidates.append(filename)
    
    print(f"候选文件: {candidates}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 使用今天的文件夹ID
        folder_url = f"https://drive.google.com/drive/folders/{folder_id}"
        page.goto(folder_url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        
        # 滚动加载
        print("正在滚动加载文件...")
        for i in range(20):
            page.keyboard.press('End')
            page.wait_for_timeout(300)
        
        html = page.content()
        
        # 查找所有文件（使用当前北京时间日期）
        current_date = now.strftime('%Y-%m-%d')
        pattern = rf'{current_date}_(\d{{4}})\.txt'
        found_files = re.findall(pattern, html)
        found_files = sorted(set(found_files), reverse=True)
        
        if found_files:
            latest_time = found_files[0]
            latest_filename = f"{current_date}_{latest_time}.txt"
            print(f"找到最新文件: {latest_filename}")
            
            # 搜索文件获取ID
            page.goto(folder_url, timeout=30000)
            page.wait_for_timeout(2000)
            
            page.keyboard.press('/')
            page.wait_for_timeout(1000)
            page.keyboard.type(latest_filename)
            page.wait_for_timeout(2000)
            page.keyboard.press('Enter')
            page.wait_for_timeout(3000)
            
            search_html = page.content()
            
            if latest_filename in search_html:
                # 提取文件ID
                pos = search_html.find(latest_filename)
                snippet = search_html[max(0, pos-1000):min(len(search_html), pos+1000)]
                
                id_patterns = [
                    r'data-id="([^"]+)"',
                    r'"id":"([^"]+)"',
                    r'/file/d/([A-Za-z0-9_-]+)/',
                ]
                
                file_id = None
                for pattern in id_patterns:
                    matches = re.findall(pattern, snippet)
                    if matches:
                        file_id = matches[0]
                        break
                
                if file_id:
                    # 访问文件
                    file_url = f"https://drive.google.com/file/d/{file_id}/view"
                    page.goto(file_url, wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(3000)
                    
                    content = page.content()
                    browser.close()
                    
                    return parse_and_store_data(content, latest_filename, current_hour)
        
        browser.close()
        return None

def parse_and_store_data(content, filename, current_hour):
    """解析并存储文件内容到数据库"""
    # 从文件名提取实际数据时间，而不是采集时间
    # 文件名格式: 2025-12-07_1124.txt
    import re
    match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
    if match:
        file_date = match.group(1)
        file_time = match.group(2)
        # 文件时间格式: HHMM -> HH:MM:00
        snapshot_time = f"{file_date} {file_time[:2]}:{file_time[2:]}:00"
        snapshot_date = file_date
    else:
        # 如果无法解析文件名，使用当前时间作为后备
        now = datetime.now(BEIJING_TZ)
        snapshot_time = now.strftime('%Y-%m-%d %H:%M:%S')
        snapshot_date = now.strftime('%Y-%m-%d')
    
    data = {
        '文件名': filename,
        '采集时间': snapshot_time
    }
    
    # 提取基础数据
    patterns = {
        '急涨': r'急涨[：:](\d+)',
        '急跌': r'急跌[：:](\d+)',
        '状态': r'状态[：:]([^\s\|★]+)',
        '比值': r'比值[：:]([\d.]+)',
        '差值': r'差值[：:]([-\d.]+)',
        '比价最低': r'比价最低\s+(\d+)',
        '比价创新高': r'比价创新高\s+(\d+)',
        '计次': r'透明标签_计次=(\d+)',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            data[key] = match.group(1)
    
    # 解析币种数据
    lines = content.split('\n')
    count_rise_10 = 0
    count_fall_10 = 0
    coin_list = []
    
    for line in lines:
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 16:
                try:
                    index_num = int(parts[0].strip())
                    symbol = parts[1].strip()
                    change = float(parts[2].strip()) if parts[2].strip() else 0
                    rush_up = int(parts[3].strip()) if parts[3].strip() else 0
                    rush_down = int(parts[4].strip()) if parts[4].strip() else 0
                    update_time = parts[5].strip()
                    high_price = float(parts[6].strip()) if parts[6].strip() else 0
                    high_time = parts[7].strip()
                    decline = float(parts[8].strip()) if parts[8].strip() else 0
                    change_24h = float(parts[9].strip()) if parts[9].strip() else 0
                    rank = int(parts[12].strip()) if parts[12].strip() else 0
                    current_price = float(parts[13].strip()) if parts[13].strip() else 0
                    ratio1 = parts[14].strip()  # 最高占比
                    ratio2 = parts[15].strip()  # 最低占比
                    
                    # 统计24小时涨跌幅
                    if change_24h >= 10.0:
                        count_rise_10 += 1
                    elif change_24h <= -10.0:
                        count_fall_10 += 1
                    
                    # 计算优先级
                    priority = calculate_priority_level(ratio1, ratio2)
                    
                    coin_list.append({
                        'index_num': index_num,
                        'symbol': symbol,
                        'change': change,
                        'rush_up': rush_up,
                        'rush_down': rush_down,
                        'update_time': update_time,
                        'high_price': high_price,
                        'high_time': high_time,
                        'decline': decline,
                        'change_24h': change_24h,
                        'rank': rank,
                        'current_price': current_price,
                        'ratio1': ratio1,
                        'ratio2': ratio2,
                        'priority': priority
                    })
                except (ValueError, IndexError) as e:
                    pass
    
    data['24h涨幅>=10%'] = count_rise_10
    data['24h跌幅<=-10%'] = count_fall_10
    
    # 计算计次得分
    if '计次' in data:
        count_times = int(data['计次'])
        star_count, star_type, star_display = calculate_count_score(count_times, current_hour)
        data['计次得分_数量'] = star_count
        data['计次得分_类型'] = star_type
        data['计次得分_显示'] = star_display
    
    # 存储到数据库
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    
    # ===== 数据验证：检查急涨/急跌是否合理 =====
    new_rush_up = int(data.get('急涨', 0))
    new_rush_down = int(data.get('急跌', 0))
    
    # 获取最近一条记录
    cursor.execute("""
        SELECT rush_up, rush_down, snapshot_time 
        FROM crypto_snapshots 
        ORDER BY snapshot_time DESC 
        LIMIT 1
    """)
    last_record = cursor.fetchone()
    
    if last_record:
        last_rush_up, last_rush_down, last_time = last_record
        
        # 解析时间，检查是否跨天重置
        last_dt = datetime.strptime(last_time, '%Y-%m-%d %H:%M:%S')
        current_dt = datetime.strptime(snapshot_time, '%Y-%m-%d %H:%M:%S')
        
        # 判断是否跨越了新一天的00:10重置点
        # 规则：如果上一条记录是昨天的，且当前时间是今天00:10之后的第一条，允许重置
        last_date = last_dt.date()
        current_date = current_dt.date()
        is_new_day_reset = False
        
        if current_date > last_date:
            # 跨天了，检查当前时间是否在00:10之后
            if current_dt.hour == 0 and current_dt.minute >= 10:
                is_new_day_reset = True
                print(f"\n🔄 检测到跨天重置点 (北京时间 {current_date} 00:10)")
                print(f"   上一天 ({last_date}): 急涨={last_rush_up}, 急跌={last_rush_down}")
                print(f"   新一天开始: 急涨={new_rush_up}, 急跌={new_rush_down}")
            elif current_dt.hour > 0 or (current_dt.hour == 0 and current_dt.minute >= 10):
                # 当前时间已经过了00:10，这是新一天的数据
                is_new_day_reset = True
                print(f"\n🔄 检测到新一天的数据 (重置计数)")
                print(f"   上一天最终值 ({last_date}): 急涨={last_rush_up}, 急跌={last_rush_down}")
                print(f"   新一天初始值 ({current_date}): 急涨={new_rush_up}, 急跌={new_rush_down}")
        
        # 验证规则：急涨和急跌只能增大或保持不变，不能减小（除非是跨天重置）
        if not is_new_day_reset and (new_rush_up < last_rush_up or new_rush_down < last_rush_down):
            print(f"\n⚠️  数据异常检测！")
            print(f"   上一条记录 ({last_time}): 急涨={last_rush_up}, 急跌={last_rush_down}")
            print(f"   当前数据: 急涨={new_rush_up}, 急跌={new_rush_down}")
            
            if new_rush_up < last_rush_up:
                print(f"   ❌ 急涨数值减小: {last_rush_up} → {new_rush_up}")
            if new_rush_down < last_rush_down:
                print(f"   ❌ 急跌数值减小: {last_rush_down} → {new_rush_down}")
            
            print(f"\n🚫 拒绝存储异常数据！")
            conn.close()
            return None  # 返回None表示数据被拒绝
    
    # 检查是否已经存在相同时间的记录（避免重复采集）
    cursor.execute("""
        SELECT id FROM crypto_snapshots 
        WHERE snapshot_time = ?
    """, (snapshot_time,))
    
    existing = cursor.fetchone()
    if existing:
        print(f"\n⚠️  数据已存在: {snapshot_time} (ID: {existing[0]})")
        print(f"   跳过重复采集")
        conn.close()
        return None
    
    # 插入快照数据
    cursor.execute("""
        INSERT INTO crypto_snapshots (
            snapshot_time, snapshot_date, rush_up, rush_down, diff, count,
            ratio, status, green_count, percentage, filename, created_at,
            count_score_display, count_score_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        snapshot_time,
        snapshot_date,
        int(data.get('急涨', 0)),
        int(data.get('急跌', 0)),
        int(data.get('差值', 0)),
        int(data.get('计次', 0)),
        float(data.get('比值', 0)),
        data.get('状态', ''),
        0,  # green_count (暂时设为0)
        '',  # percentage (暂时为空)
        filename,
        snapshot_time,
        # 计算计次得分
        calculate_count_score_display(int(data.get('计次', 0)), snapshot_time),
        calculate_count_score_type(int(data.get('计次', 0)), snapshot_time)
    ))
    
    snapshot_id = cursor.lastrowid
    
    # 插入币种数据
    for coin in coin_list:
        cursor.execute("""
            INSERT INTO crypto_coin_data (
                snapshot_id, snapshot_time, symbol, index_order,
                change, rush_up, rush_down, update_time,
                high_price, high_time, decline, change_24h,
                rank, current_price, ratio1, ratio2,
                priority_level, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snapshot_id,
            snapshot_time,
            coin['symbol'],
            coin['index_num'],
            coin['change'],
            coin['rush_up'],
            coin['rush_down'],
            coin['update_time'],
            coin['high_price'],
            coin['high_time'],
            coin['decline'],
            coin['change_24h'],
            coin['rank'],
            coin['current_price'],
            coin['ratio1'],
            coin['ratio2'],
            coin['priority'],
            snapshot_time
        ))
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 数据已存储到数据库")
    print(f"   快照ID: {snapshot_id}")
    print(f"   币种数量: {len(coin_list)}")
    
    data['coin_list'] = coin_list
    return data

def main():
    print("="*80)
    print("开始采集数据...")
    print("="*80)
    
    result = get_latest_file_data()
    
    if result:
        print("\n" + "="*80)
        print("✅ 数据采集成功!")
        print("="*80)
        
        # 按顺序显示数据
        display_order = [
            '文件名', '采集时间', 
            '急涨', '急跌', '状态', '比值', '差值',
            '比价最低', '比价创新高', 
            '计次', '计次得分_显示', '计次得分_类型',
            '24h涨幅>=10%', '24h跌幅<=-10%'
        ]
        
        for key in display_order:
            if key in result:
                print(f"{key:15s}: {result[key]}")
        
        # 显示优先级统计
        if 'coin_list' in result:
            priority_stats = {}
            for coin in result['coin_list']:
                level = coin['priority']
                priority_stats[level] = priority_stats.get(level, 0) + 1
            
            print("\n优先级统计:")
            for level in ['等级1', '等级2', '等级3', '等级4', '等级5', '等级6', '未知']:
                count = priority_stats.get(level, 0)
                if count > 0:
                    print(f"  {level}: {count} 个币种")
        
        return result
    else:
        print("\n❌ 数据采集失败")
        return None

if __name__ == '__main__':
    main()
