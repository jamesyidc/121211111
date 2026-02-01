#!/usr/bin/env python3
"""
rclone Google Drive 配置助手
用于自动配置 rclone 访问 Google Drive
"""
import os
import subprocess
import json

def check_rclone():
    """检查 rclone 是否安装"""
    try:
        result = subprocess.run(['rclone', 'version'], capture_output=True, text=True)
        print("✅ rclone 已安装")
        print(result.stdout.split('\n')[0])
        return True
    except FileNotFoundError:
        print("❌ rclone 未安装")
        return False

def create_rclone_config():
    """创建 rclone 配置文件（使用公开链接方式）"""
    config_dir = os.path.expanduser('~/.config/rclone')
    config_file = os.path.join(config_dir, 'rclone.conf')
    
    # 确保配置目录存在
    os.makedirs(config_dir, exist_ok=True)
    
    # 使用公开链接访问，不需要认证
    config_content = """[gdrive]
type = drive
scope = drive.readonly
root_folder_id = 1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV
team_drive = 
"""
    
    with open(config_file, 'w') as f:
        f.write(config_content)
    
    print(f"✅ 配置文件已创建: {config_file}")
    return config_file

def test_rclone_access():
    """测试 rclone 访问"""
    print("\n📋 测试 rclone 访问...")
    
    # 测试列出根目录
    try:
        result = subprocess.run(
            ['rclone', 'lsd', 'gdrive:'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ 可以访问 Google Drive")
            print("\n文件夹列表:")
            print(result.stdout)
            return True
        else:
            print("❌ 访问失败")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

def list_date_folders():
    """列出日期文件夹"""
    print("\n📅 查找日期文件夹...")
    
    try:
        result = subprocess.run(
            ['rclone', 'lsf', 'gdrive:', '--dirs-only'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            folders = [line.strip('/') for line in result.stdout.strip().split('\n') if line.strip()]
            date_folders = [f for f in folders if f.count('-') == 2 and len(f) == 10]
            
            print(f"✅ 找到 {len(date_folders)} 个日期文件夹")
            print(f"最新的10个:")
            for folder in sorted(date_folders, reverse=True)[:10]:
                print(f"  📁 {folder}")
            
            return date_folders
        else:
            print("❌ 列出文件夹失败")
            print(result.stderr)
            return []
    except Exception as e:
        print(f"❌ 列出文件夹失败: {e}")
        return []

def list_txt_files(date_folder):
    """列出指定日期文件夹中的TXT文件"""
    print(f"\n📄 列出 {date_folder} 中的TXT文件...")
    
    try:
        result = subprocess.run(
            ['rclone', 'lsf', f'gdrive:{date_folder}', '--include', '*.txt'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            files = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            print(f"✅ 找到 {len(files)} 个TXT文件")
            for f in files[:5]:
                print(f"  📄 {f}")
            if len(files) > 5:
                print(f"  ... 还有 {len(files) - 5} 个文件")
            return files
        else:
            print("❌ 列出文件失败")
            print(result.stderr)
            return []
    except Exception as e:
        print(f"❌ 列出文件失败: {e}")
        return []

def main():
    print("=" * 60)
    print("🚀 rclone Google Drive 配置助手")
    print("=" * 60)
    
    # 1. 检查 rclone
    if not check_rclone():
        print("\n请先安装 rclone:")
        print("  curl https://rclone.org/install.sh | sudo bash")
        return
    
    # 2. 创建配置
    print("\n" + "=" * 60)
    config_file = create_rclone_config()
    
    # 3. 测试访问
    print("\n" + "=" * 60)
    if not test_rclone_access():
        print("\n⚠️  访问失败，可能需要认证")
        print("请运行: rclone config")
        print("然后选择 'n' 创建新的remote，类型选择 'drive'")
        return
    
    # 4. 列出日期文件夹
    print("\n" + "=" * 60)
    date_folders = list_date_folders()
    
    if not date_folders:
        print("\n⚠️  没有找到日期文件夹")
        return
    
    # 5. 测试列出最新日期的文件
    if date_folders:
        latest_date = sorted(date_folders, reverse=True)[0]
        print("\n" + "=" * 60)
        list_txt_files(latest_date)
    
    print("\n" + "=" * 60)
    print("✅ 配置完成！")
    print("\n下一步:")
    print("  1. 运行新的更新器:")
    print("     python3 source_code/auto_gdrive_updater_rclone.py")
    print("\n  2. 更新 PM2 配置:")
    print("     pm2 delete gdrive-updater")
    print("     pm2 start source_code/auto_gdrive_updater_rclone.py --name gdrive-updater")
    print("     pm2 save")
    print("=" * 60)

if __name__ == '__main__':
    main()
