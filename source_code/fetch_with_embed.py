#!/usr/bin/env python3
"""
使用embed view获取文件
"""
import requests
import re

folder_id = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"
target_filename = "2025-12-09_1818.txt"

print(f"📥 正在获取: {target_filename}")
print()

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # 使用embed view
    embed_url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
    print(f"获取文件夹内容: {embed_url}")
    
    response = requests.get(embed_url, headers=headers, timeout=30)
    content = response.text
    
    print(f"✅ 响应大小: {len(content)} 字节")
    
    # 保存HTML用于调试
    with open('/home/user/webapp/gdrive_embed_debug.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("已保存HTML到: gdrive_embed_debug.html")
    print()
    
    # 查找文件ID
    # 尝试多种模式
    patterns = [
        # Pattern 1: 标准格式
        r'"' + re.escape(target_filename) + r'"[^}]*?"([a-zA-Z0-9_-]{33})"',
        # Pattern 2: ID在前
        r'"([a-zA-Z0-9_-]{33})"[^}]*?' + re.escape(target_filename),
        # Pattern 3: 使用entry格式
        r'entry-([a-zA-Z0-9_-]+)[^}]*?' + re.escape(target_filename),
    ]
    
    file_id = None
    for i, pattern in enumerate(patterns, 1):
        matches = re.findall(pattern, content)
        if matches:
            file_id = matches[0]
            print(f"✅ 找到文件ID (Pattern {i}): {file_id}")
            break
    
    if not file_id:
        print("❌ 未找到文件ID")
        print("\n搜索文件名出现次数...")
        count = content.count(target_filename)
        print(f"   '{target_filename}' 出现 {count} 次")
        
        # 查找附近的所有ID
        if count > 0:
            # 找到文件名所在的位置
            pos = content.find(target_filename)
            snippet = content[max(0, pos-200):min(len(content), pos+200)]
            print(f"\n附近内容片段:")
            print(snippet)
            print()
            
            # 从snippet中提取所有可能的ID
            all_ids = re.findall(r'"([a-zA-Z0-9_-]{20,})"', snippet)
            if all_ids:
                print(f"可能的ID候选:")
                for idx, candidate in enumerate(all_ids, 1):
                    print(f"   {idx}. {candidate}")
                file_id = all_ids[0]  # 尝试第一个
                print(f"\n尝试使用第一个ID: {file_id}")
        
        if not file_id:
            exit(1)
    
    # 尝试下载
    download_urls = [
        f"https://drive.google.com/uc?id={file_id}&export=download",
        f"https://drive.google.com/uc?export=download&id={file_id}",
    ]
    
    for url in download_urls:
        print(f"\n🔄 尝试下载: {url[:80]}...")
        dl_response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        
        if dl_response.status_code == 200:
            dl_content = dl_response.text
            
            # 检查是否是HTML错误页
            if '<html' in dl_content[:100].lower() and len(dl_content) < 5000:
                print(f"   ⚠️  返回HTML页面（{len(dl_content)}字节），不是文件内容")
                continue
            
            # 成功下载
            output_path = f"/home/user/webapp/{target_filename}"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(dl_content)
            
            print(f"✅ 文件已保存: {output_path}")
            print(f"   大小: {len(dl_content)} 字节")
            
            # 显示预览
            lines = dl_content.split('\n')
            print(f"\n📄 文件预览（前20行）:")
            print("=" * 70)
            for i, line in enumerate(lines[:20], 1):
                print(f"{i:2d}. {line}")
            print("=" * 70)
            print(f"总行数: {len(lines)}")
            
            exit(0)
        else:
            print(f"   ❌ HTTP {dl_response.status_code}")
    
    print("\n❌ 所有下载尝试均失败")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()

