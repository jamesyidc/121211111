#!/usr/bin/env python3
"""
导入今天从指定时间开始的所有历史数据
"""
import sqlite3
from datetime import datetime
import time
import re
from playwright.sync_api import sync_playwright
from home_data_api_v2 import parse_home_data  # 复用解析函数

def get_file_list_from_gdrive():
    """从 Google Drive 获取今天的所有 TXT 文件列表"""
    print("🔍 正在获取 Google Drive 文件列表...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # 1. 访问根文件夹
            root_url = 'https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV'
            print(f"1. 访问: {root_url}")
            page.goto(root_url, wait_until='networkidle', timeout=30000)
            time.sleep(3)
            
            # 2. 进入今天的日期文件夹
            today = datetime.now().strftime('%Y-%m-%d')
            print(f"2. 寻找今天的文件夹: {today}")
            
            folder_selector = f'div[data-id]:has-text("{today}")'
            page.click(folder_selector, timeout=10000)
            print(f"   ✅ 进入文件夹: {today}")
            time.sleep(2)
            
            # 3. 点击排序按钮
            print("3. 点击排序选项...")
            try:
                sort_button = page.locator('button[aria-label*="Sort"]').first
                if not sort_button.is_visible():
                    sort_button = page.locator('button:has-text("Sort")').first
                sort_button.click(timeout=5000)
                time.sleep(1)
            except Exception as e:
                print(f"   排序按钮未找到，尝试其他方法: {e}")
            
            # 4. 选择按修改时间排序
            print("4. 选择按修改时间排序...")
            try:
                modified_option = page.locator('div[role="menuitem"]:has-text("Modified")').first
                if not modified_option.is_visible():
                    modified_option = page.locator('div[role="menuitem"]:has-text("修改时间")').first
                modified_option.click(timeout=5000)
                time.sleep(2)
            except Exception as e:
                print(f"   排序选项未找到: {e}")
            
            # 5. 获取所有 TXT 文件
            print("5. 获取文件列表...")
            page.wait_for_selector('div[data-id]', timeout=10000)
            
            # 获取所有文件元素
            file_elements = page.locator('div[data-id]').all()
            print(f"   找到 {len(file_elements)} 个项目")
            
            files = []
            for elem in file_elements:
                try:
                    text = elem.text_content()
                    # 匹配 TXT 文件格式: YYYY-MM-DD_HHMM.txt
                    if text and re.match(r'\d{4}-\d{2}-\d{2}_\d{4}\.txt', text):
                        files.append({
                            'name': text.strip(),
                            'element': elem
                        })
                except:
                    continue
            
            print(f"   ✅ 找到 {len(files)} 个 TXT 文件")
            
            # 按文件名排序（时间从早到晚）
            files.sort(key=lambda x: x['name'])
            
            # 返回文件信息
            file_list = []
            for f in files:
                file_list.append({
                    'name': f['name'],
                    'element': f['element'],
                    'page': page  # 保持 page 引用
                })
            
            return file_list, page, browser
            
        except Exception as e:
            print(f"❌ 获取文件列表失败: {e}")
            browser.close()
            return [], None, None

def read_file_content(file_info):
    """读取单个文件的内容"""
    try:
        page = file_info['page']
        filename = file_info['name']
        element = file_info['element']
        
        print(f"\n📄 正在读取: {filename}")
        
        # 点击文件
        element.click()
        print(f"   ✅ 点击了文件")
        time.sleep(2)
        
        # 等待 iframe 加载
        page.wait_for_selector('iframe', timeout=10000)
        frames = page.frames
        
        # 在 iframe 中查找内容
        for i, frame in enumerate(frames):
            try:
                frame_url = frame.url
                if 'drive.google.com/file' in frame_url or 'docs.google.com' in frame_url:
                    content = frame.content()
                    if content and len(content) > 100:
                        print(f"   ✅ Frame {i} 包含数据 (长度: {len(content)})")
                        
                        # 提取纯文本
                        import re
                        text_content = re.sub(r'<[^>]+>', '\n', content)
                        text_content = re.sub(r'\s+', ' ', text_content).strip()
                        
                        if len(text_content) > 500:
                            return text_content
            except:
                continue
        
        print(f"   ❌ 未找到有效内容")
        return None
        
    except Exception as e:
        print(f"   ❌ 读取失败: {e}")
        return None

def import_file_to_db(filename, content):
    """将文件内容解析并导入数据库"""
    try:
        # 从文件名提取时间
        match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})\.txt', filename)
        if not match:
            print(f"   ❌ 无法解析文件名: {filename}")
            return False
        
        date_str = match.group(1)
        hour = match.group(2)
        minute = match.group(3)
        record_time = f"{date_str} {hour}:{minute}:00"
        
        # 检查是否已存在
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM stats_history WHERE record_time = ?', (record_time,))
        if cursor.fetchone():
            print(f"   ⏭️  已存在: {record_time}")
            conn.close()
            return False
        
        # 解析数据
        result = parse_home_data(content)
        if not result['success']:
            print(f"   ❌ 解析失败")
            conn.close()
            return False
        
        data = result['data']
        print(f"   解析结果: 急涨={data['stats']['rush_up']}, 急跌={data['stats']['rush_down']}, 币种={len(data['coins'])}")
        
        # 插入统计数据
        cursor.execute('''
            INSERT INTO stats_history 
            (record_time, rush_up, rush_down, status, percentage, ratio, green_count, filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record_time,
            data['stats']['rush_up'],
            data['stats']['rush_down'],
            data['stats']['status'],
            data['stats']['percentage'],
            data['stats']['ratio'],
            data['stats']['green_count'],
            filename
        ))
        stats_id = cursor.lastrowid
        
        # 插入币种数据
        for coin in data['coins']:
            cursor.execute('''
                INSERT INTO coin_history
                (stats_id, record_time, symbol, index_num, change, rush_up, rush_down,
                 update_time, high_price, high_time, decline, change_24h, rank,
                 current_price, ratio1, ratio2, filename)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                stats_id, record_time, coin['symbol'], coin['index'],
                coin['change'], coin['rush_up'], coin['rush_down'],
                coin['update_time'], coin['high_price'], coin['high_time'],
                coin['decline'], coin['change_24h'], coin['rank'],
                coin['current_price'], coin['ratio1'], coin['ratio2'],
                filename
            ))
        
        conn.commit()
        conn.close()
        
        print(f"   ✅ 成功导入 {len(data['coins'])} 条币种数据")
        return True
        
    except Exception as e:
        print(f"   ❌ 导入失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 80)
    print("📦 开始批量导入今天的历史数据")
    print("=" * 80)
    
    # 获取文件列表
    file_list, page, browser = get_file_list_from_gdrive()
    
    if not file_list:
        print("❌ 未获取到文件列表")
        return
    
    print(f"\n📋 文件列表 (共 {len(file_list)} 个):")
    for f in file_list:
        print(f"   - {f['name']}")
    
    # 逐个导入
    success_count = 0
    skip_count = 0
    fail_count = 0
    
    for i, file_info in enumerate(file_list, 1):
        print(f"\n[{i}/{len(file_list)}] 处理: {file_info['name']}")
        
        # 读取内容
        content = read_file_content(file_info)
        
        if content:
            # 导入数据库
            if import_file_to_db(file_info['name'], content):
                success_count += 1
            else:
                skip_count += 1
            
            # 返回文件列表（按 ESC 键）
            try:
                page.keyboard.press('Escape')
                time.sleep(1)
            except:
                pass
        else:
            fail_count += 1
    
    # 关闭浏览器
    if browser:
        browser.close()
    
    # 统计结果
    print("\n" + "=" * 80)
    print("📊 导入完成")
    print("=" * 80)
    print(f"✅ 成功导入: {success_count} 个文件")
    print(f"⏭️  已存在跳过: {skip_count} 个文件")
    print(f"❌ 失败: {fail_count} 个文件")
    
    # 显示数据库统计
    conn = sqlite3.connect('crypto_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM stats_history')
    total_stats = cursor.fetchone()[0]
    cursor.execute('SELECT MIN(record_time), MAX(record_time) FROM stats_history')
    time_range = cursor.fetchone()
    conn.close()
    
    print(f"\n📈 数据库总计:")
    print(f"   统计记录: {total_stats}")
    print(f"   时间范围: {time_range[0]} ~ {time_range[1]}")
    print("=" * 80)

if __name__ == '__main__':
    main()
