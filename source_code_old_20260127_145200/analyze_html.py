import re

print("分析父文件夹HTML...")
print("=" * 70)

with open('/tmp/parent_folder.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 查找所有可能的文件夹ID
# Google Drive使用特定格式的ID
all_ids = re.findall(r'([a-zA-Z0-9_-]{28,40})', html)
unique_ids = list(set(all_ids))

print(f"找到 {len(unique_ids)} 个唯一的潜在ID")

# 过滤出看起来像文件夹ID的（通常是33个字符左右）
folder_like_ids = [id for id in unique_ids if 28 <= len(id) <= 40 and not id.startswith('_')]
print(f"其中 {len(folder_like_ids)} 个看起来像文件夹ID")

# 检查HTML中是否有文件夹列表信息
if '2025-12-06' in html:
    print("\n✅ HTML中包含 '2025-12-06'")
    
    # 查找2025-12-06附近的内容
    idx = html.find('2025-12-06')
    context = html[max(0, idx-500):min(len(html), idx+500)]
    
    # 在上下文中查找ID
    context_ids = re.findall(r'([a-zA-Z0-9_-]{28,40})', context)
    print(f"\n在2025-12-06附近找到 {len(set(context_ids))} 个ID:")
    for cid in list(set(context_ids))[:5]:
        print(f"  - {cid}")

# 关键发现
print("\n" + "=" * 70)
print("关键发现:")
print("=" * 70)
print("""
目前测试的文件夹 1JNZKKnZLeoBkxSumjS63SOInCriPfAKX 中只有50个文件。

可能的情况:
1. ❌ 这个文件夹确实只有50个文件（00:06-08:19）
2. ✅ 新文件被上传到了其他位置
3. ✅ 文件上传程序在08:19之后停止工作了

需要确认的问题:
- 文件是否继续上传到了其他文件夹？
- 文件上传程序是否在08:19后停止？
- 是否有其他Google Drive文件夹正在使用？
""")

