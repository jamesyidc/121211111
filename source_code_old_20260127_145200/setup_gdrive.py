#!/usr/bin/env python3
"""
Google Drive API 配置向导
帮助用户快速配置 Google Drive 访问
"""

import os
import json
import sys

def print_header(text):
    """打印标题"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")

def print_step(step_num, title):
    """打印步骤标题"""
    print(f"\n{'='*80}")
    print(f"步骤 {step_num}: {title}")
    print('='*80)

def main():
    print_header("🚀 Google Drive API 配置向导")
    
    print("""
这个向导将帮助你配置 Google Drive API，以便系统自动读取你的 TXT 文件。

配置完成后，系统将能够：
✅ 自动读取 Google Drive 中当天文件夹的最新 TXT 文件
✅ 每 10 分钟自动更新数据
✅ 无需手动上传或更新数据

让我们开始吧！
    """)
    
    input("按 Enter 继续...")
    
    # 步骤 1: 检查凭据文件
    print_step(1, "检查 Google Drive 凭据文件")
    
    creds_path = '/home/user/webapp/gdrive_credentials.json'
    
    if os.path.exists(creds_path):
        print(f"✅ 找到凭据文件: {creds_path}")
        
        # 验证文件格式
        try:
            with open(creds_path, 'r') as f:
                creds_data = json.load(f)
            
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 
                             'client_email', 'client_id']
            missing_fields = [field for field in required_fields if field not in creds_data]
            
            if missing_fields:
                print(f"⚠️  凭据文件缺少必需字段: {', '.join(missing_fields)}")
                print("请确保使用正确的服务账号 JSON 密钥文件")
                sys.exit(1)
            
            print(f"✅ 凭据文件格式正确")
            print(f"📧 服务账号邮箱: {creds_data['client_email']}")
            
            service_email = creds_data['client_email']
            
        except json.JSONDecodeError:
            print("❌ 凭据文件格式错误，不是有效的 JSON 文件")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 读取凭据文件失败: {e}")
            sys.exit(1)
    else:
        print(f"❌ 未找到凭据文件: {creds_path}")
        print("\n你需要：")
        print("1. 访问 https://console.cloud.google.com/")
        print("2. 创建或选择一个项目")
        print("3. 启用 Google Drive API")
        print("4. 创建服务账号")
        print("5. 下载 JSON 密钥文件")
        print("6. 将文件重命名为 gdrive_credentials.json")
        print("7. 上传到 /home/user/webapp/ 目录")
        print("\n详细步骤请查看: /home/user/webapp/GDRIVE_SETUP.md")
        sys.exit(1)
    
    # 步骤 2: 检查共享权限
    print_step(2, "配置 Google Drive 共享权限")
    
    print(f"""
现在你需要将服务账号添加到你的 Google Drive 文件夹：

1. 打开你的 Google Drive 共享文件夹:
   https://drive.google.com/drive/folders/1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV

2. 点击文件夹右上角的 "共享" 按钮（或右键 > 共享）

3. 在 "添加用户和组" 输入框中，粘贴以下邮箱地址：
   
   📧 {service_email}

4. 确保权限设置为 "查看者" (Viewer)

5. 点击 "发送" 或 "完成"

⚠️  重要：服务账号需要访问：
   - 主文件夹：1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV
   - 子文件夹：2025-12-02（按日期命名的文件夹）
   - TXT 文件：文件夹内的所有 .txt 文件
    """)
    
    response = input("\n已完成共享设置？(y/n): ").strip().lower()
    if response != 'y':
        print("请完成共享设置后重新运行此脚本")
        sys.exit(0)
    
    # 步骤 3: 测试连接
    print_step(3, "测试 Google Drive 连接")
    
    print("正在测试连接...")
    
    try:
        from gdrive_reader import GDriveReader
        from datetime import datetime
        import pytz
        
        reader = GDriveReader(folder_id='1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV')
        
        if not reader.service:
            print("❌ Google Drive API 初始化失败")
            print("请检查 gdrive_credentials.json 文件是否正确")
            sys.exit(1)
        
        print("✅ Google Drive API 连接成功")
        
        # 测试查找今天的文件夹
        beijing_tz = pytz.timezone('Asia/Shanghai')
        today = datetime.now(beijing_tz).strftime('%Y-%m-%d')
        
        print(f"\n正在查找今天的文件夹: {today}")
        folder_id = reader.find_folder_by_name(reader.folder_id, today)
        
        if folder_id:
            print(f"✅ 找到今天的文件夹: {folder_id}")
            
            # 查找最新的 TXT 文件
            print("\n正在查找最新的 TXT 文件...")
            file_info = reader.find_latest_txt_file(folder_id)
            
            if file_info:
                file_id, file_name = file_info
                print(f"✅ 找到最新 TXT 文件: {file_name}")
                
                # 尝试读取内容
                print("\n正在读取文件内容...")
                content = reader.download_file_content(file_id)
                
                if content:
                    print(f"✅ 成功读取文件内容（{len(content)} 字节）")
                    print(f"\n文件内容预览:")
                    print("-" * 60)
                    print(content[:200] if len(content) > 200 else content)
                    print("-" * 60)
                else:
                    print("❌ 读取文件内容失败")
                    sys.exit(1)
            else:
                print("❌ 未找到 TXT 文件")
                print("\n请检查：")
                print(f"1. 文件夹 {today} 中是否有 .txt 文件")
                print("2. 文件扩展名是否正确（.txt）")
                sys.exit(1)
        else:
            print(f"❌ 未找到今天的文件夹: {today}")
            print("\n请检查：")
            print(f"1. Google Drive 中是否存在名为 '{today}' 的文件夹")
            print(f"2. 服务账号是否有权限访问该文件夹")
            sys.exit(1)
        
    except ImportError as e:
        print(f"❌ 导入模块失败: {e}")
        print("请确保已安装所需的 Python 包：")
        print("pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client pytz")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 步骤 4: 完成配置
    print_step(4, "配置完成")
    
    print("""
🎉 恭喜！Google Drive API 配置成功！

系统现在可以：
✅ 自动连接到你的 Google Drive
✅ 读取今天文件夹中的最新 TXT 文件
✅ 每 10 分钟自动更新数据

接下来：
1. 重启服务器以应用配置
2. 访问主页查看实时数据

运行以下命令重启服务器：
    cd /home/user/webapp && pkill -f crypto_server_demo && python3 crypto_server_demo.py
    """)
    
    response = input("\n是否现在重启服务器？(y/n): ").strip().lower()
    if response == 'y':
        print("\n正在重启服务器...")
        os.system("cd /home/user/webapp && pkill -f crypto_server_demo")
        print("旧服务器已停止")
        print("请手动运行: python3 crypto_server_demo.py")

if __name__ == '__main__':
    main()
