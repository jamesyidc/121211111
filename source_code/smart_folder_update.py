#!/usr/bin/env python3
"""
智能文件夹更新脚本
- 优先查找今天日期的文件夹
- 如果找不到，使用最新可用的日期文件夹
- 记录所有可用文件夹供调试
"""

import os
import sys
import json
import requests
import logging
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# 配置
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "daily_folder_config.json"
LOG_FILE = BASE_DIR / "logs/smart_folder_update.log"

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def get_current_date_beijing():
    """获取北京时间当前日期"""
    now = datetime.now(BEIJING_TZ)
    return now.strftime('%Y-%m-%d')

def load_config():
    """加载配置文件"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载配置文件失败: {e}")
        return None

def save_config(config):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logging.info(f"✅ 配置已保存: {CONFIG_FILE}")
        return True
    except Exception as e:
        logging.error(f"保存配置文件失败: {e}")
        return False

def explore_all_folders(parent_folder_id):
    """
    探索父文件夹，返回所有日期格式的文件夹
    返回: [(date, folder_id), ...] 按日期降序排列
    """
    url = f"https://drive.google.com/embeddedfolderview?id={parent_folder_id}#list"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        html = response.text
        
        # 匹配文件夹项
        pattern = r'<div class="flip-entry"[^>]*id="entry-([^"]+)"[^>]*>.*?<div[^>]*title="([^"]+)"'
        matches = re.findall(pattern, html, re.DOTALL)
        
        date_folders = []
        for folder_id_match, folder_name in matches:
            # 只保留文件夹（通过检查是否有 dir- 前缀）
            if folder_id_match.startswith('dir-'):
                actual_id = folder_id_match.replace('dir-', '')
                # 检查是否是日期格式 (YYYY-MM-DD)
                if re.match(r'^\d{4}-\d{2}-\d{2}$', folder_name):
                    date_folders.append((folder_name, actual_id))
        
        # 按日期降序排序
        date_folders.sort(reverse=True)
        return date_folders
        
    except Exception as e:
        logging.error(f"探索文件夹失败: {e}")
        return []

def smart_update_config():
    """智能更新配置文件"""
    logging.info("="*70)
    logging.info("🔄 开始智能文件夹配置更新")
    logging.info("="*70)
    
    # 1. 获取当前日期（北京时间）
    today_date = get_current_date_beijing()
    logging.info(f"📅 当前日期（北京时间）: {today_date}")
    
    # 2. 加载配置
    config = load_config()
    if not config:
        logging.error("❌ 无法加载配置文件")
        return False
    
    current_date_in_config = config.get('current_date', '')
    parent_folder_id = config.get('parent_folder_id', '')
    
    logging.info(f"📝 配置文件中的日期: {current_date_in_config}")
    logging.info(f"📂 父文件夹ID: {parent_folder_id}")
    
    if not parent_folder_id:
        logging.error("❌ 配置文件中缺少 parent_folder_id")
        return False
    
    # 3. 检查是否需要更新
    if current_date_in_config == today_date:
        logging.info(f"✅ 配置日期已是最新 ({today_date})，无需更新")
        return True
    
    logging.warning(f"⚠️ 配置日期 ({current_date_in_config}) 与当前日期 ({today_date}) 不匹配")
    logging.info(f"🔄 开始查找可用的日期文件夹...")
    
    # 4. 获取所有可用的日期文件夹
    all_folders = explore_all_folders(parent_folder_id)
    
    if not all_folders:
        logging.error(f"❌ 无法获取文件夹列表")
        return False
    
    logging.info(f"📁 找到 {len(all_folders)} 个日期文件夹")
    
    # 显示最新的5个文件夹
    logging.info(f"\n最新的5个文件夹:")
    for idx, (date, fid) in enumerate(all_folders[:5], 1):
        marker = "👉" if date == today_date else "  "
        logging.info(f"{marker} {idx}. {date} (ID: {fid})")
    
    # 5. 选择目标文件夹
    target_folder = None
    target_date = None
    
    # 优先查找今天的文件夹
    for date, fid in all_folders:
        if date == today_date:
            target_folder = fid
            target_date = date
            logging.info(f"\n✅ 找到今天的文件夹: {today_date}")
            break
    
    # 如果找不到今天的，使用最新的
    if not target_folder and all_folders:
        target_date, target_folder = all_folders[0]
        logging.warning(f"\n⚠️ 未找到今天 ({today_date}) 的文件夹")
        logging.info(f"📌 使用最新可用文件夹: {target_date}")
    
    if not target_folder:
        logging.error(f"❌ 无可用的日期文件夹")
        return False
    
    # 6. 更新配置
    old_config = config.copy()
    config['current_date'] = target_date
    config['folder_id'] = target_folder
    config['updated_at'] = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
    config['auto_updated'] = True
    config['file_count'] = 0  # 重置文件计数
    
    # 7. 保存配置
    if save_config(config):
        logging.info("="*70)
        logging.info("✅ 文件夹配置智能更新成功")
        logging.info("="*70)
        logging.info(f"📅 日期: {old_config.get('current_date')} → {config['current_date']}")
        logging.info(f"📁 文件夹ID: {old_config.get('folder_id')} → {config['folder_id']}")
        logging.info(f"🕐 更新时间: {config['updated_at']}")
        
        if target_date != today_date:
            logging.warning(f"⚠️ 注意: 使用的是 {target_date} 的数据，而非今天 ({today_date})")
            logging.info(f"💡 一旦 Google Drive 中出现 {today_date} 文件夹，下次检查时会自动切换")
        
        logging.info("="*70)
        return True
    else:
        logging.error("❌ 保存配置失败")
        return False

if __name__ == "__main__":
    try:
        success = smart_update_config()
        sys.exit(0 if success else 1)
    except Exception as e:
        logging.critical(f"❌ 智能更新失败: {e}", exc_info=True)
        sys.exit(2)
