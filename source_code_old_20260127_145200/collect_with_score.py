#!/usr/bin/env python3
"""
完整的数据采集脚本，包含计次得分功能
"""
from playwright.sync_api import sync_playwright
from datetime import datetime
import pytz
import re

FOLDER_ID = "1JNZKKnZLeoBkxSumjS63SOInCriPfAKX"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def calculate_count_score(count_times, current_hour):
    """
    根据计次和当前时间计算得分
    返回: (星级数量, 星级类型, 描述)
    
    规则：
    - 实心星表示好（计次少）
    - 空心星表示差（计次多）
    """
    # 确定时间段
    if current_hour < 6:
        period = "00-06点"
        # 截止6点前规则
        if count_times <= 1:
            return (3, "实心", "★★★")
        elif 1 < count_times <= 2:
            return (2, "实心", "★★☆")
        elif 2 < count_times <= 3:
            return (1, "实心", "★☆☆")
        elif 3 < count_times <= 4:
            return (1, "空心", "☆--")
        elif 4 < count_times <= 5:
            return (2, "空心", "☆☆-")
        else:  # count_times > 5
            return (3, "空心", "☆☆☆")
            
    elif 6 <= current_hour < 12:
        period = "06-12点"
        # 截止12点前规则
        if count_times <= 2:
            return (3, "实心", "★★★")
        elif 2 < count_times <= 3:
            return (2, "实心", "★★☆")
        elif 3 < count_times <= 4:
            return (1, "实心", "★☆☆")
        elif 4 < count_times <= 5:
            return (0, "中性", "---")  # 4-5之间无评分
        elif 5 < count_times <= 6:
            return (1, "空心", "☆--")
        elif 6 < count_times <= 7:
            return (2, "空心", "☆☆-")
        else:  # count_times > 7
            return (3, "空心", "☆☆☆")
            
    elif 12 <= current_hour < 18:
        period = "12-18点"
        # 截止18点前规则
        if count_times <= 3:
            return (3, "实心", "★★★")
        elif 3 < count_times <= 4:
            return (2, "实心", "★★☆")
        elif 4 < count_times <= 5:
            return (1, "实心", "★☆☆")
        elif 5 < count_times <= 7:
            return (0, "中性", "---")  # 5-7之间无评分
        elif 7 < count_times <= 8:
            return (1, "空心", "☆--")
        elif 8 < count_times <= 9:
            return (2, "空心", "☆☆-")
        else:  # count_times > 9
            return (3, "空心", "☆☆☆")
            
    else:  # 18 <= current_hour < 24
        period = "18-22点"
        # 22点前规则
        if count_times <= 4:
            return (3, "实心", "★★★")
        elif 4 < count_times <= 5:
            return (2, "实心", "★★☆")
        elif 5 < count_times <= 6:
            return (1, "实心", "★☆☆")
        elif 6 < count_times <= 9:
            return (0, "中性", "---")  # 6-9之间无评分
        elif 9 < count_times <= 10:
            return (1, "空心", "☆--")
        elif 10 < count_times <= 11:
            return (2, "空心", "☆☆-")
        else:  # count_times > 11
            return (3, "空心", "☆☆☆")

def get_latest_file_data():
    """获取最新文件数据"""
    now = datetime.now(BEIJING_TZ)
    current_hour = now.hour
    
    print(f"当前北京时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"当前小时: {current_hour}")
    
    # 生成候选文件名（向前推30分钟）
    candidates = []
    for i in range(0, 4):  # 检查最近40分钟
        check_time = now.replace(second=0, microsecond=0)
        check_time = check_time.replace(minute=(check_time.minute // 10) * 10 - i * 10)
        filename = check_time.strftime('%Y-%m-%d_%H%M.txt')
        candidates.append(filename)
    
    print(f"候选文件: {candidates}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 先滚动获取所有文件
        folder_url = f"https://drive.google.com/drive/folders/{FOLDER_ID}"
        page.goto(folder_url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        
        # 滚动加载
        print("正在滚动加载文件...")
        for i in range(20):
            page.keyboard.press('End')
            page.wait_for_timeout(300)
        
        html = page.content()
        
        # 查找所有文件
        pattern = r'2025-12-06_(\d{4})\.txt'
        found_files = re.findall(pattern, html)
        found_files = sorted(set(found_files), reverse=True)
        
        if found_files:
            latest_time = found_files[0]
            latest_filename = f"2025-12-06_{latest_time}.txt"
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
                    
                    return parse_data(content, latest_filename, current_hour)
        
        browser.close()
        return None

def parse_data(content, filename, current_hour):
    """解析文件内容"""
    data = {
        '文件名': filename,
        '采集时间': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
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
    
    # 统计24小时涨跌幅
    lines = content.split('\n')
    count_rise_10 = 0
    count_fall_10 = 0
    
    for line in lines:
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 10:
                try:
                    change_24h = float(parts[9].strip())
                    if change_24h >= 10.0:
                        count_rise_10 += 1
                    elif change_24h <= -10.0:
                        count_fall_10 += 1
                except (ValueError, IndexError):
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
        
        return result
    else:
        print("\n❌ 数据采集失败")
        return None

if __name__ == '__main__':
    main()
