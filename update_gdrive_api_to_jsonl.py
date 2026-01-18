#!/usr/bin/env python3
"""
更新app_new.py中的gdrive API，将数据库查询替换为JSONL
"""
import re

API_FILE = 'source_code/app_new.py'

# 需要在文件顶部添加的import
IMPORT_GDRIVE_MANAGER = "from gdrive_jsonl_manager import GDriveJSONLManager\n"

# 需要在文件顶部添加的实例化
MANAGER_INSTANCE = "gdrive_jsonl_manager = GDriveJSONLManager()\n"

def add_imports():
    """在app_new.py中添加必要的import"""
    with open(API_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已存在
    if 'from gdrive_jsonl_manager import GDriveJSONLManager' in content:
        print("✅ GDriveJSONLManager import已存在")
        return
    
    # 在其他import之后添加
    # 查找最后一个from ... import的位置
    import_pattern = r'(from [^\n]+ import [^\n]+\n)'
    matches = list(re.finditer(import_pattern, content))
    
    if matches:
        # 在最后一个import之后添加
        last_match = matches[-1]
        insert_pos = last_match.end()
        content = content[:insert_pos] + '\n' + IMPORT_GDRIVE_MANAGER + content[insert_pos:]
        
        # 在创建app之后添加manager实例
        app_pattern = r'(app = Flask\(__name__\)[^\n]*\n)'
        app_match = re.search(app_pattern, content)
        if app_match:
            insert_pos = app_match.end()
            content = content[:insert_pos] + '\n' + MANAGER_INSTANCE + content[insert_pos:]
        
        with open(API_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已添加GDriveJSONLManager import和实例")
    else:
        print("❌ 无法找到合适的插入位置")

if __name__ == '__main__':
    print("=" * 80)
    print("更新gdrive API使用JSONL")
    print("=" * 80)
    add_imports()
    print("\n⚠️ 注意：需要手动修改API端点中的数据库查询代码")
    print("   建议创建辅助函数来封装JSONL查询逻辑")
