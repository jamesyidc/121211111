#!/usr/bin/env python3
"""
🕐 设置每日00:10自动更新的定时任务
"""
import os
import subprocess
from datetime import datetime
import pytz

def setup_cron():
    """设置cron任务"""
    print("=" * 70)
    print("🕐 设置每日自动更新定时任务")
    print("=" * 70)
    
    # cron表达式: 每天00:10运行
    cron_expression = "10 0 * * *"
    script_path = "/home/user/webapp/auto_update_today_folder.py"
    log_path = "/home/user/webapp/cron_auto_update.log"
    
    # 确保脚本有执行权限
    try:
        os.chmod(script_path, 0o755)
        print(f"✅ 脚本已设置为可执行: {script_path}")
    except Exception as e:
        print(f"❌ 设置权限失败: {e}")
        return False
    
    # 构建cron任务
    cron_command = f"{cron_expression} /usr/bin/python3 {script_path} >> {log_path} 2>&1"
    
    print(f"\n📋 Cron任务配置:")
    print(f"   时间: 每天 00:10 (北京时间)")
    print(f"   脚本: {script_path}")
    print(f"   日志: {log_path}")
    print(f"   命令: {cron_command}")
    
    # 检查当前cron任务
    try:
        result = subprocess.run(['crontab', '-l'], 
                              capture_output=True, 
                              text=True,
                              timeout=5)
        current_cron = result.stdout if result.returncode == 0 else ""
        
        # 检查是否已存在
        if 'auto_update_today_folder.py' in current_cron:
            print(f"\n⚠️  定时任务已存在")
            print(f"\n当前的crontab:")
            print(current_cron)
            
            response = input("\n是否要更新定时任务? (y/n): ")
            if response.lower() != 'y':
                print("❌ 取消操作")
                return False
            
            # 移除旧任务
            lines = current_cron.split('\n')
            new_lines = [line for line in lines if 'auto_update_today_folder.py' not in line]
            new_cron = '\n'.join(new_lines)
        else:
            new_cron = current_cron
        
        # 添加新任务
        if new_cron and not new_cron.endswith('\n'):
            new_cron += '\n'
        new_cron += cron_command + '\n'
        
        # 写入crontab
        process = subprocess.Popen(['crontab', '-'], 
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True)
        stdout, stderr = process.communicate(input=new_cron, timeout=5)
        
        if process.returncode == 0:
            print(f"\n✅ 定时任务设置成功！")
            print(f"\n新的crontab:")
            
            # 显示新的crontab
            result = subprocess.run(['crontab', '-l'], 
                                  capture_output=True, 
                                  text=True,
                                  timeout=5)
            print(result.stdout)
            
            return True
        else:
            print(f"\n❌ 设置失败: {stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ 命令执行超时")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {str(e)}")
        return False

def show_manual_setup():
    """显示手动设置说明"""
    print("\n" + "=" * 70)
    print("📖 手动设置说明")
    print("=" * 70)
    
    print("""
如果自动设置失败，可以手动添加定时任务:

1️⃣ 编辑crontab:
   crontab -e

2️⃣ 添加以下行:
   10 0 * * * /usr/bin/python3 /home/user/webapp/auto_update_today_folder.py >> /home/user/webapp/cron_auto_update.log 2>&1

3️⃣ 保存并退出 (Ctrl+O, Enter, Ctrl+X)

4️⃣ 验证:
   crontab -l

说明:
- 10 0 * * * = 每天00:10运行
- 脚本会自动扫描并更新文件夹ID
- 日志保存在 cron_auto_update.log
""")

def test_script():
    """测试脚本执行"""
    print("\n" + "=" * 70)
    print("🧪 测试脚本执行")
    print("=" * 70)
    
    script_path = "/home/user/webapp/auto_update_today_folder.py"
    
    print(f"\n执行: python3 {script_path}")
    print("-" * 70)
    
    try:
        result = subprocess.run(['python3', script_path], 
                              capture_output=True,
                              text=True,
                              timeout=30)
        
        print(result.stdout)
        
        if result.stderr:
            print("\n错误输出:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n✅ 脚本执行成功！")
            return True
        else:
            print(f"\n❌ 脚本执行失败 (退出码: {result.returncode})")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n❌ 脚本执行超时（30秒）")
        return False
    except Exception as e:
        print(f"\n❌ 执行错误: {str(e)}")
        return False

def main():
    print("\n" + "=" * 70)
    print("🔄 每日文件夹自动更新 - 定时任务设置")
    print("=" * 70)
    
    beijing_tz = pytz.timezone('Asia/Shanghai')
    current_time = datetime.now(beijing_tz)
    print(f"\n当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
    
    print("\n选择操作:")
    print("1. 设置定时任务 (每天00:10自动运行)")
    print("2. 立即测试运行")
    print("3. 查看手动设置说明")
    print("4. 查看当前定时任务")
    print("5. 删除定时任务")
    
    choice = input("\n请选择 (1-5): ").strip()
    
    if choice == '1':
        setup_cron()
    elif choice == '2':
        test_script()
    elif choice == '3':
        show_manual_setup()
    elif choice == '4':
        print("\n当前的crontab:")
        try:
            result = subprocess.run(['crontab', '-l'], 
                                  capture_output=True,
                                  text=True,
                                  timeout=5)
            if result.returncode == 0:
                print(result.stdout)
            else:
                print("没有设置定时任务")
        except Exception as e:
            print(f"❌ 查看失败: {e}")
    elif choice == '5':
        print("\n删除定时任务...")
        try:
            result = subprocess.run(['crontab', '-l'], 
                                  capture_output=True,
                                  text=True,
                                  timeout=5)
            if result.returncode == 0:
                current_cron = result.stdout
                lines = current_cron.split('\n')
                new_lines = [line for line in lines if 'auto_update_today_folder.py' not in line]
                new_cron = '\n'.join(new_lines)
                
                process = subprocess.Popen(['crontab', '-'], 
                                          stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          text=True)
                stdout, stderr = process.communicate(input=new_cron, timeout=5)
                
                if process.returncode == 0:
                    print("✅ 定时任务已删除")
                else:
                    print(f"❌ 删除失败: {stderr}")
            else:
                print("没有设置定时任务")
        except Exception as e:
            print(f"❌ 删除失败: {e}")
    else:
        print("❌ 无效的选择")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n操作取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
