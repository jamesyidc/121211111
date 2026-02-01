#!/usr/bin/env python3
"""
🔄 每日自动更新今天的文件夹ID
可以每天00:10自动运行，或手动触发
"""
import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import pytz
import sys
import os

# 配置
PARENT_FOLDER_ID = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"  # "首页数据"文件夹（固定不变）
CONFIG_FILE = "/home/user/webapp/daily_folder_config.json"
LOG_FILE = "/home/user/webapp/auto_update_folder.log"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def log(message, level="INFO"):
    """记录日志并打印"""
    timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    emoji = {
        "INFO": "ℹ️ ",
        "SUCCESS": "✅",
        "WARNING": "⚠️ ",
        "ERROR": "❌",
        "STEP": "📋"
    }.get(level, "")
    
    log_msg = f"[{timestamp}] {emoji} {message}"
    print(log_msg)
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    except:
        pass

def print_banner(text):
    """打印漂亮的标题"""
    width = 70
    print("\n" + "=" * width)
    print(f"{'🔄 ' + text + ' 🔄':^{width}}")
    print("=" * width + "\n")

def get_current_config():
    """读取当前配置"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log(f"无法读取配置文件: {e}", "WARNING")
        return {}

def scan_parent_folder():
    """扫描父文件夹，找到所有日期子文件夹"""
    log(f"扫描父文件夹: {PARENT_FOLDER_ID}", "STEP")
    
    url = f"https://drive.google.com/embeddedfolderview?id={PARENT_FOLDER_ID}"
    
    try:
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            log(f"无法访问父文件夹 (HTTP {response.status_code})", "ERROR")
            return None
        
        log(f"父文件夹访问成功 (HTTP {response.status_code})", "SUCCESS")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        all_links = soup.find_all('a', href=True)
        
        folders = {}
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if '/folders/' in href:
                match = re.search(r'/folders/([a-zA-Z0-9_-]+)', href)
                if match:
                    folder_id = match.group(1)
                    folders[text] = folder_id
        
        log(f"找到 {len(folders)} 个子文件夹", "INFO")
        return folders
        
    except Exception as e:
        log(f"扫描失败: {str(e)}", "ERROR")
        return None

def find_today_folder(folders):
    """从文件夹列表中找到今天的文件夹"""
    today = datetime.now(BEIJING_TZ)
    today_str = today.strftime('%Y-%m-%d')
    
    log(f"查找今天的文件夹: {today_str}", "STEP")
    
    # 尝试多种日期格式
    date_patterns = [
        today.strftime('%Y-%m-%d'),  # 2025-12-14
        today.strftime('%Y%m%d'),    # 20251214
        today.strftime('%m-%d'),     # 12-14
        today.strftime('%m%d'),      # 1214
    ]
    
    log(f"搜索日期模式: {date_patterns}", "INFO")
    
    # 查找匹配的文件夹
    date_folders = {}
    for folder_name, folder_id in folders.items():
        for pattern in [r'(\d{4}-\d{2}-\d{2})', r'(\d{2}-\d{2})', r'(\d{8})']:
            match = re.search(pattern, folder_name)
            if match:
                date_str = match.group(1)
                date_folders[folder_name] = {
                    'id': folder_id,
                    'date_str': date_str
                }
                break
    
    # 按名称排序（最新的在前）
    sorted_folders = sorted(date_folders.items(), reverse=True)
    
    log(f"找到 {len(date_folders)} 个日期文件夹", "INFO")
    if sorted_folders:
        log("最近5个文件夹:", "INFO")
        for i, (name, info) in enumerate(sorted_folders[:5], 1):
            marker = "🎯" if today_str in name else "  "
            log(f"  {marker} {i}. {name} ({info['id'][:20]}...)", "INFO")
    
    # 查找今天的文件夹
    for folder_name, info in date_folders.items():
        if today_str in folder_name:
            log(f"找到今天的文件夹: {folder_name}", "SUCCESS")
            return {
                'name': folder_name,
                'id': info['id'],
                'date': today_str
            }
    
    log("未找到今天的文件夹", "WARNING")
    
    # 如果没找到今天的，返回最近的
    if sorted_folders:
        latest = sorted_folders[0]
        log(f"使用最近的文件夹: {latest[0]}", "WARNING")
        return {
            'name': latest[0],
            'id': latest[1]['id'],
            'date': latest[1]['date_str']
        }
    
    return None

def verify_folder_content(folder_id, expected_date):
    """验证文件夹内容，查找TXT文件"""
    log(f"验证文件夹内容: {folder_id}", "STEP")
    
    url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
    
    try:
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            log(f"无法访问文件夹 (HTTP {response.status_code})", "ERROR")
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        all_links = soup.find_all('a', href=True)
        
        txt_files = []
        for link in all_links:
            text = link.get_text(strip=True)
            if text.endswith('.txt'):
                txt_files.append(text)
        
        log(f"找到 {len(txt_files)} 个TXT文件", "INFO")
        
        if txt_files:
            sorted_txt = sorted(txt_files, reverse=True)
            log(f"最新5个文件:", "INFO")
            for i, filename in enumerate(sorted_txt[:5], 1):
                marker = "🎯" if i == 1 else "  "
                log(f"  {marker} {i}. {filename}", "INFO")
            
            return {
                'txt_count': len(txt_files),
                'latest_txt': sorted_txt[0],
                'txt_files': sorted_txt[:10]  # 保存前10个
            }
        else:
            log("文件夹中没有TXT文件", "WARNING")
            return {
                'txt_count': 0,
                'latest_txt': None,
                'txt_files': []
            }
            
    except Exception as e:
        log(f"验证失败: {str(e)}", "ERROR")
        return None

def update_config(today_folder_info, folder_content):
    """更新配置文件"""
    log("更新配置文件", "STEP")
    
    # 读取现有配置
    config = get_current_config()
    
    # 更新配置
    current_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    
    config.update({
        'root_folder_odd': PARENT_FOLDER_ID,
        'root_folder_even': PARENT_FOLDER_ID,
        'folder_id': today_folder_info['id'],
        'current_date': today_folder_info['date'],
        'last_updated': current_time,
        'parent_folder_url': f'https://drive.google.com/drive/folders/{PARENT_FOLDER_ID}?usp=sharing',
        'folder_name': today_folder_info['name'],
        'auto_update_time': current_time,
        'auto_update_status': 'success'
    })
    
    if folder_content:
        config.update({
            'txt_count': folder_content['txt_count'],
            'latest_txt': folder_content['latest_txt']
        })
    
    # 保存配置
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        log("配置文件更新成功", "SUCCESS")
        log(f"新文件夹ID: {today_folder_info['id']}", "INFO")
        log(f"日期: {today_folder_info['date']}", "INFO")
        
        if folder_content and folder_content['latest_txt']:
            log(f"最新TXT: {folder_content['latest_txt']}", "INFO")
        
        return True
        
    except Exception as e:
        log(f"配置文件保存失败: {str(e)}", "ERROR")
        return False

def restart_detector():
    """重启检测器"""
    log("准备重启检测器", "STEP")
    
    try:
        # 杀死旧进程
        os.system("pkill -f gdrive_final_detector.py")
        log("已停止旧的检测器进程", "INFO")
        
        import time
        time.sleep(2)
        
        # 启动新进程
        os.system("cd /home/user/webapp && nohup python3 gdrive_final_detector.py > gdrive_detector_auto.log 2>&1 &")
        log("检测器已重启", "SUCCESS")
        
        return True
        
    except Exception as e:
        log(f"重启检测器失败: {str(e)}", "ERROR")
        return False

def check_need_update():
    """检查是否需要更新"""
    log("检查是否需要更新", "STEP")
    
    config = get_current_config()
    today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
    
    if not config:
        log("配置文件不存在，需要更新", "WARNING")
        return True
    
    current_date = config.get('current_date', 'unknown')
    
    if current_date != today:
        log(f"配置日期({current_date})与今天({today})不匹配，需要更新", "WARNING")
        return True
    
    log(f"配置日期已是今天({today})，检查文件夹是否有效", "INFO")
    
    folder_id = config.get('folder_id')
    if folder_id:
        # 验证文件夹是否可访问
        content = verify_folder_content(folder_id, today)
        if content and content['txt_count'] > 0:
            log(f"当前文件夹有效，包含 {content['txt_count']} 个文件", "SUCCESS")
            return False
        else:
            log("当前文件夹无效或无文件，需要更新", "WARNING")
            return True
    
    log("配置中无文件夹ID，需要更新", "WARNING")
    return True

def main():
    """主函数"""
    print_banner("每日文件夹自动更新脚本")
    
    log(f"脚本启动", "INFO")
    log(f"当前时间: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
    
    # 步骤1: 检查是否需要更新
    if not check_need_update():
        log("无需更新，脚本退出", "SUCCESS")
        return True
    
    log("开始更新流程", "INFO")
    
    # 步骤2: 扫描父文件夹
    folders = scan_parent_folder()
    if not folders:
        log("扫描父文件夹失败，脚本退出", "ERROR")
        return False
    
    # 步骤3: 找到今天的文件夹
    today_folder = find_today_folder(folders)
    if not today_folder:
        log("未找到今天的文件夹，脚本退出", "ERROR")
        return False
    
    # 步骤4: 验证文件夹内容
    folder_content = verify_folder_content(today_folder['id'], today_folder['date'])
    
    # 步骤5: 更新配置
    if not update_config(today_folder, folder_content):
        log("更新配置失败，脚本退出", "ERROR")
        return False
    
    # 步骤6: 重启检测器
    if not restart_detector():
        log("重启检测器失败", "WARNING")
        log("请手动重启检测器", "WARNING")
    
    # 完成
    print_banner("更新完成")
    log("✅ 所有步骤完成", "SUCCESS")
    log(f"新文件夹: {today_folder['name']}", "SUCCESS")
    log(f"文件夹ID: {today_folder['id']}", "SUCCESS")
    
    if folder_content and folder_content['latest_txt']:
        log(f"最新文件: {folder_content['latest_txt']}", "SUCCESS")
        log(f"文件数量: {folder_content['txt_count']}", "SUCCESS")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("\n脚本被用户中断", "WARNING")
        sys.exit(1)
    except Exception as e:
        log(f"脚本执行出错: {str(e)}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)
