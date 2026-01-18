#!/usr/bin/env python3
"""
批量导入今天所有的TXT文件
"""

import requests
import re
import sys
sys.path.insert(0, '/home/user/webapp')

from import_txt_correct import download_file, parse_txt_content, import_to_database

def get_today_files():
    """获取今天文件夹中的所有TXT文件"""
    folder_id = "1sCHpLo3BdxjXmeW9mo30Gijpzkux0eNm"
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    
    response = requests.get(url, timeout=30)
    html = response.text
    
    # Find all entry IDs
    entry_pattern = r'id="entry-([A-Za-z0-9_-]+)"'
    
    # Build file list by finding filename positions
    files = []
    for filename_match in re.finditer(r'2026-01-05_\d{4}\.txt', html):
        filename = filename_match.group()
        pos = filename_match.start()
        
        # Find the nearest entry ID before this filename
        html_before = html[:pos]
        entry_ids = re.findall(entry_pattern, html_before)
        if entry_ids:
            file_id = entry_ids[-1]
            files.append((file_id, filename))
    
    # Remove duplicates and sort
    files_dict = {}
    for file_id, filename in files:
        if filename not in files_dict:
            files_dict[filename] = file_id
    
    files = [(file_id, filename) for filename, file_id in sorted(files_dict.items())]
    
    return files

def main():
    print("="*100)
    print("开始批量导入今天的TXT文件")
    print("="*100)
    
    # Get all files
    files = get_today_files()
    print(f"\n找到 {len(files)} 个TXT文件")
    
    success_count = 0
    failed_count = 0
    failed_files = []
    
    for i, (file_id, filename) in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] 正在处理: {filename}")
        
        try:
            # Download
            content = download_file(file_id)
            
            # Parse
            summary, coins = parse_txt_content(content)
            
            # Import
            success, error = import_to_database(summary, coins)
            
            if success:
                print(f"  ✅ 成功: {summary.get('snapshot_time')}, {len(coins)}种币")
                success_count += 1
            else:
                print(f"  ❌ 失败: {error}")
                failed_count += 1
                failed_files.append(filename)
                
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            failed_count += 1
            failed_files.append(filename)
            continue
    
    # Summary
    print("\n" + "="*100)
    print("导入完成")
    print("="*100)
    print(f"总文件数: {len(files)}")
    print(f"成功导入: {success_count}")
    print(f"失败: {failed_count}")
    
    if failed_files:
        print(f"\n失败的文件:")
        for f in failed_files:
            print(f"  - {f}")

if __name__ == "__main__":
    main()
