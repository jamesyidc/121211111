#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爆仓金额监控与Telegram告警
当1小时爆仓金额超过3000万美元时发送Telegram通知
"""

import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path

# 添加路径
sys.path.insert(0, '/home/user/webapp')
sys.path.insert(0, '/home/user/webapp/source_code')

from panic_jsonl_manager import PanicJSONLManager

# Telegram配置文件路径
TELEGRAM_CONFIG_PATH = '/home/user/webapp/configs/telegram_config.json'

# 告警阈值（万美元）
ALERT_THRESHOLD = 3000  # 3000万美元

# 记录文件（避免重复告警）
ALERT_RECORD_FILE = '/home/user/webapp/data/liquidation_alert_records.json'

def load_telegram_config():
    """加载Telegram配置"""
    try:
        if os.path.exists(TELEGRAM_CONFIG_PATH):
            with open(TELEGRAM_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config
        else:
            print(f"⚠️ Telegram配置文件不存在: {TELEGRAM_CONFIG_PATH}")
            return None
    except Exception as e:
        print(f"❌ 加载Telegram配置失败: {e}")
        return None

def send_telegram_message(bot_token, chat_id, message):
    """发送Telegram消息"""
    try:
        import requests
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, data=data, timeout=10)
        result = response.json()
        
        if result.get('ok'):
            print(f"✅ Telegram消息发送成功")
            return True
        else:
            print(f"❌ Telegram消息发送失败: {result}")
            return False
            
    except Exception as e:
        print(f"❌ 发送Telegram消息异常: {e}")
        return False

def load_alert_records():
    """加载告警记录"""
    try:
        if os.path.exists(ALERT_RECORD_FILE):
            with open(ALERT_RECORD_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'last_alert_time': None, 'alert_count': 0, 'alerts': []}
    except Exception as e:
        print(f"⚠️ 加载告警记录失败: {e}")
        return {'last_alert_time': None, 'alert_count': 0, 'alerts': []}

def save_alert_record(record):
    """保存告警记录"""
    try:
        os.makedirs(os.path.dirname(ALERT_RECORD_FILE), exist_ok=True)
        with open(ALERT_RECORD_FILE, 'w', encoding='utf-8') as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ 保存告警记录失败: {e}")
        return False

def should_send_alert(current_time, last_alert_time, cooldown_minutes=30):
    """
    判断是否应该发送告警
    使用冷却时间机制，避免短时间内重复告警
    """
    if last_alert_time is None:
        return True
    
    try:
        last_time = datetime.fromisoformat(last_alert_time)
        current = datetime.fromisoformat(current_time)
        time_diff = (current - last_time).total_seconds() / 60  # 转换为分钟
        
        return time_diff >= cooldown_minutes
    except Exception as e:
        print(f"⚠️ 判断告警冷却时间失败: {e}")
        return True

def check_liquidation_and_alert():
    """检查爆仓金额并发送告警"""
    try:
        print("=" * 60)
        print("🔍 开始检查爆仓金额...")
        print(f"⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. 获取最新的爆仓数据
        manager = PanicJSONLManager()
        latest_record = manager.get_latest('panic_wash_index')
        
        if not latest_record:
            print("⚠️ 无法获取最新爆仓数据")
            return
        
        hour_1_amount = latest_record.get('hour_1_amount', 0)
        record_time = latest_record.get('record_time', '')
        
        print(f"📊 1小时爆仓金额: {hour_1_amount:.2f} 万美元")
        print(f"📅 数据时间: {record_time}")
        
        # 2. 检查是否超过阈值
        if hour_1_amount < ALERT_THRESHOLD:
            print(f"✅ 爆仓金额未超过阈值 ({ALERT_THRESHOLD}万美元)")
            return
        
        print(f"🚨 警告！爆仓金额超过阈值: {hour_1_amount:.2f} > {ALERT_THRESHOLD}")
        
        # 3. 检查告警冷却时间
        alert_records = load_alert_records()
        last_alert_time = alert_records.get('last_alert_time')
        
        if not should_send_alert(record_time, last_alert_time, cooldown_minutes=30):
            print(f"⏳ 告警冷却中，上次告警时间: {last_alert_time}")
            return
        
        # 4. 加载Telegram配置
        tg_config = load_telegram_config()
        if not tg_config:
            print("❌ 无法加载Telegram配置，跳过发送")
            return
        
        bot_token = tg_config.get('bot_token')
        chat_id = tg_config.get('chat_id')
        
        if not bot_token or not chat_id:
            print("❌ Telegram配置不完整")
            return
        
        # 5. 构造告警消息
        message = f"""
🚨 *爆仓金额告警* 🚨

💥 *1小时爆仓金额*: `{hour_1_amount:.2f}` 万美元
⚠️ *告警阈值*: `{ALERT_THRESHOLD}` 万美元
📈 *超出比例*: `{((hour_1_amount - ALERT_THRESHOLD) / ALERT_THRESHOLD * 100):.1f}%`

⏰ *数据时间*: {record_time}
📍 *告警时间*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔗 *查看详情*: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/panic

---
_系统自动监控告警_
        """.strip()
        
        # 6. 发送Telegram消息
        print("📤 发送Telegram告警...")
        success = send_telegram_message(bot_token, chat_id, message)
        
        if success:
            # 7. 更新告警记录
            alert_records['last_alert_time'] = record_time
            alert_records['alert_count'] = alert_records.get('alert_count', 0) + 1
            alert_records.setdefault('alerts', []).append({
                'time': record_time,
                'amount': hour_1_amount,
                'threshold': ALERT_THRESHOLD,
                'sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # 只保留最近100条告警记录
            if len(alert_records['alerts']) > 100:
                alert_records['alerts'] = alert_records['alerts'][-100:]
            
            save_alert_record(alert_records)
            print(f"✅ 告警发送成功！累计告警次数: {alert_records['alert_count']}")
        else:
            print("❌ 告警发送失败")
        
    except Exception as e:
        print(f"❌ 检查爆仓金额异常: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数 - 持续监控"""
    print("=" * 60)
    print("🚀 爆仓金额监控服务启动")
    print(f"⚙️ 告警阈值: {ALERT_THRESHOLD} 万美元")
    print(f"⏱️ 检查间隔: 1 分钟")
    print(f"🕐 启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 首次检查
    check_liquidation_and_alert()
    
    # 持续监控
    while True:
        try:
            time.sleep(60)  # 每1分钟检查一次
            check_liquidation_and_alert()
        except KeyboardInterrupt:
            print("\n⚠️ 收到停止信号，退出监控...")
            break
        except Exception as e:
            print(f"❌ 监控循环异常: {e}")
            time.sleep(60)  # 出错后等待1分钟再继续

if __name__ == '__main__':
    main()
