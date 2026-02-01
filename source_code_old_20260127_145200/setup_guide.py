#!/usr/bin/env python3
"""
Google Drive API 设置向导
帮助用户完成Service Account的设置和配置
"""

import os
import sys
import json

def print_header(text):
    """打印标题"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_step(step_num, title):
    """打印步骤标题"""
    print(f"\n📋 步骤 {step_num}: {title}")
    print("-" * 80)

def check_credentials_file():
    """检查凭证文件是否存在"""
    if os.path.exists('credentials.json'):
        print("✅ 找到 credentials.json 文件")
        try:
            with open('credentials.json', 'r') as f:
                creds = json.load(f)
                
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 
                             'client_email', 'client_id']
            
            missing_fields = [field for field in required_fields if field not in creds]
            
            if missing_fields:
                print(f"⚠️  凭证文件缺少必需字段: {', '.join(missing_fields)}")
                return False
            
            if creds.get('type') != 'service_account':
                print("⚠️  凭证类型不正确，应该是 'service_account'")
                return False
            
            print(f"✅ 凭证文件格式正确")
            print(f"📧 Service Account邮箱: {creds['client_email']}")
            print(f"🆔 项目ID: {creds['project_id']}")
            
            return True
            
        except json.JSONDecodeError:
            print("❌ credentials.json 不是有效的JSON文件")
            return False
        except Exception as e:
            print(f"❌ 读取凭证文件时出错: {e}")
            return False
    else:
        print("❌ 未找到 credentials.json 文件")
        return False

def main():
    print_header("Google Drive API 设置向导")
    
    print("\n本向导将帮助您设置Google Drive API访问权限")
    print("完成设置后，您就可以使用脚本自动查找当日文件夹中的最新txt文件")
    
    # 检查凭证文件
    print_step(1, "检查凭证文件")
    
    if check_credentials_file():
        print("\n✅ 凭证文件已正确配置！")
        
        with open('credentials.json', 'r') as f:
            creds = json.load(f)
            service_email = creds['client_email']
        
        print_step(2, "确认Google Drive文件夹共享")
        print(f"\n请确保您已将Google Drive文件夹共享给以下邮箱:")
        print(f"\n    📧 {service_email}")
        print(f"\n共享步骤:")
        print(f"  1. 打开Google Drive文件夹")
        print(f"  2. 右键点击文件夹 > 共享")
        print(f"  3. 添加上述邮箱地址")
        print(f"  4. 权限设置为 '查看者'")
        print(f"  5. 点击 '发送'")
        
        print_step(3, "测试连接")
        print("\n现在您可以运行主程序来测试连接:")
        print("\n    python google_drive_finder.py")
        
    else:
        print("\n❌ 凭证文件未正确配置")
        
        print_step(2, "创建Service Account")
        print("\n请按照以下步骤创建Service Account并下载凭证文件:")
        
        print("\n1️⃣  访问Google Cloud Console")
        print("   🔗 https://console.cloud.google.com/")
        
        print("\n2️⃣  创建或选择项目")
        print("   - 点击顶部的项目选择器")
        print("   - 点击 '新建项目' 或选择现有项目")
        
        print("\n3️⃣  启用Google Drive API")
        print("   - 左侧菜单: APIs & Services > Library")
        print("   - 搜索: 'Google Drive API'")
        print("   - 点击并启用")
        
        print("\n4️⃣  创建Service Account")
        print("   - 左侧菜单: APIs & Services > Credentials")
        print("   - 点击 'Create Credentials' > 'Service Account'")
        print("   - 填写名称 (如: google-drive-finder)")
        print("   - 点击 'Create and Continue'")
        print("   - 跳过可选步骤，点击 'Done'")
        
        print("\n5️⃣  下载Service Account密钥")
        print("   - 在Credentials页面，点击刚创建的Service Account")
        print("   - 切换到 'Keys' 标签")
        print("   - 点击 'Add Key' > 'Create new key'")
        print("   - 选择 'JSON' 格式")
        print("   - 点击 'Create'")
        print("   - 文件会自动下载")
        
        print("\n6️⃣  重命名并移动文件")
        print(f"   - 将下载的JSON文件重命名为: credentials.json")
        print(f"   - 将文件移动到此目录: {os.getcwd()}")
        
        print("\n7️⃣  完成后重新运行此向导")
        print("   python setup_guide.py")
    
    print_header("设置向导完成")
    
    if not check_credentials_file():
        print("\n⚠️  请先完成上述步骤，然后重新运行此向导")
        return 1
    
    print("\n✅ 所有设置已完成！")
    print("\n下一步: 运行主程序")
    print("   python google_drive_finder.py")
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  用户取消操作")
        sys.exit(1)
