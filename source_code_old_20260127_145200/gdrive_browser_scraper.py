#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用Playwright浏览器自动化工具从Google Drive公开文件夹获取文件列表
这是唯一能真正解决动态JavaScript内容加载的方法
"""

import asyncio
from playwright.async_api import async_playwright
import re
from datetime import datetime
import pytz

async def get_gdrive_files_with_browser(folder_id: str, date_folder: str):
    """
    使用真实浏览器访问Google Drive并获取文件列表
    
    Args:
        folder_id: 日期文件夹的ID
        date_folder: 日期文件夹名称 (例如: 2025-12-03)
    
    Returns:
        list: 文件列表，按时间倒序排列
    """
    print(f"启动浏览器自动化工具...")
    print(f"目标文件夹: {date_folder}")
    print(f"文件夹ID: {folder_id}")
    
    async with async_playwright() as p:
        # 启动无头浏览器
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            url = f"https://drive.google.com/drive/folders/{folder_id}"
            print(f"\n访问URL: {url}")
            
            # 访问页面
            await page.goto(url, wait_until='networkidle', timeout=30000)
            print("✅ 页面加载完成")
            
            # 等待文件列表加载（等待任何文件项出现）
            print("\n等待文件列表加载...")
            try:
                await page.wait_for_selector('[data-id]', timeout=15000)
                print("✅ 文件列表加载完成")
            except:
                print("⚠️ 未检测到标准文件列表，尝试其他选择器...")
            
            # 额外等待确保所有内容加载
            await asyncio.sleep(2)
            
            # 获取页面内容
            content = await page.content()
            print(f"页面内容大小: {len(content)} bytes")
            
            # 尝试多种方法提取文件名
            files = []
            
            # 方法1: 从页面HTML中提取
            pattern = r'(2025-\d{2}-\d{2}_\d{4}\.txt)'
            matches = re.findall(pattern, content)
            if matches:
                print(f"✅ 从HTML中找到 {len(matches)} 个匹配")
                files.extend(matches)
            
            # 方法2: 执行JavaScript获取文件列表
            try:
                js_files = await page.evaluate('''() => {
                    const items = [];
                    // 尝试多种选择器
                    const selectors = [
                        '[data-id]',
                        '[role="row"]',
                        '.Q5txwe',
                        '[data-target]'
                    ];
                    
                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        elements.forEach(el => {
                            const text = el.textContent || el.innerText || '';
                            const match = text.match(/2025-\\d{2}-\\d{2}_\\d{4}\\.txt/g);
                            if (match) {
                                items.push(...match);
                            }
                        });
                        if (items.length > 0) break;
                    }
                    
                    return Array.from(new Set(items));
                }''')
                
                if js_files:
                    print(f"✅ 通过JavaScript找到 {len(js_files)} 个文件")
                    files.extend(js_files)
            except Exception as e:
                print(f"⚠️ JavaScript执行失败: {str(e)}")
            
            # 去重
            unique_files = list(set(files))
            print(f"\n总共找到 {len(unique_files)} 个唯一文件")
            
            if not unique_files:
                print("\n❌ 未找到任何文件，保存页面快照用于调试...")
                await page.screenshot(path='/home/user/webapp/gdrive_debug.png')
                with open('/home/user/webapp/gdrive_debug.html', 'w', encoding='utf-8') as f:
                    f.write(content)
                print("已保存: gdrive_debug.png, gdrive_debug.html")
                return []
            
            # 解析文件时间并排序
            file_list = []
            for filename in unique_files:
                try:
                    match = re.match(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt', filename)
                    if match:
                        date_str = match.group(1)
                        time_str = match.group(2)
                        file_datetime = datetime.strptime(
                            f"{date_str} {time_str[:2]}:{time_str[2:]}", 
                            "%Y-%m-%d %H:%M"
                        )
                        file_list.append({
                            'filename': filename,
                            'datetime': file_datetime,
                            'time_str': f"{time_str[:2]}:{time_str[2:]}"
                        })
                except Exception as e:
                    print(f"⚠️ 解析文件名失败 {filename}: {str(e)}")
            
            # 按时间倒序排序
            file_list.sort(key=lambda x: x['datetime'], reverse=True)
            
            return file_list
            
        finally:
            await browser.close()
            print("\n浏览器已关闭")

async def main():
    """测试函数"""
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    
    print("="*60)
    print("Google Drive 浏览器自动化抓取")
    print("="*60)
    print(f"当前北京时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 这是2025-12-03文件夹的ID
    folder_id = "1Ej3JlFylpaxRtcLIe1yD_MOxcxNck5mh"
    date_folder = now.strftime('%Y-%m-%d')
    
    try:
        file_list = await get_gdrive_files_with_browser(folder_id, date_folder)
        
        if file_list:
            print(f"\n{'='*60}")
            print(f"找到 {len(file_list)} 个文件")
            print(f"{'='*60}")
            
            # 显示前10个
            print("\n最新的文件（最多10个）:")
            for i, file_info in enumerate(file_list[:10], 1):
                print(f"  {i}. {file_info['filename']} (时间: {file_info['time_str']})")
            
            # 最新文件信息
            latest = file_list[0]
            time_diff = (now.replace(tzinfo=None) - latest['datetime']).total_seconds() / 60
            
            print(f"\n{'='*60}")
            print("最新文件")
            print(f"{'='*60}")
            print(f"文件名: {latest['filename']}")
            print(f"文件时间: {latest['time_str']}")
            print(f"当前时间: {now.strftime('%H:%M')}")
            print(f"时间差: {time_diff:.1f} 分钟")
            
            if time_diff < 15:
                print("✅ 数据新鲜")
            else:
                print("⚠️ 数据较旧")
        else:
            print("\n❌ 未找到任何文件")
            
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
