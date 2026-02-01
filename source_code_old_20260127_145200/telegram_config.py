#!/usr/bin/env python3
"""
Telegram消息通知系统配置
用于支撑/阻力位系统的抄底信号和逃顶信号推送
"""
import json
import os

# Telegram Bot配置
TELEGRAM_CONFIG = {
    # Bot Token
    "bot_token": "8437045462:AAFePnwdC21cqeWhZISMQHGGgjmroVqE2H0",
    
    # Chat ID（频道或群组ID）
    "chat_id": "-1003227444260",
    
    # API基础URL
    "api_base_url": "https://api.telegram.org",
    
    # Bot信息
    "bot_info": {
        "id": 8437045462,
        "name": "jamesyi9999",
        "username": "jamesyi9999_bot"
    },
    
    # 消息配置
    "message_settings": {
        "parse_mode": "HTML",  # 消息格式：HTML 或 Markdown
        "disable_web_page_preview": True,  # 禁用链接预览
        "disable_notification": False  # 是否静音推送
    },
    
    # 信号类型配置
    "signal_types": {
        "buy": {
            "enabled": True,
            "name": "抄底信号",
            "emoji": "🟢",
            "color": "green"
        },
        "sell": {
            "enabled": True,
            "name": "逃顶信号",
            "emoji": "🔴",
            "color": "red"
        }
    },
    
    # 推送条件配置
    "push_conditions": {
        "min_coins": 1,  # 最少触发币种数（小于此数量不推送）
        "cooldown_seconds": 300,  # 冷却时间（秒），避免频繁推送
        "max_retries": 3,  # 发送失败最大重试次数
        "retry_delay": 5  # 重试延迟（秒）
    },
    
    # 消息模板配置
    "templates": {
        "buy_signal": """
🟢 <b>抄底信号触发</b>

⏰ 时间: {time}
📊 触发币种: {count}个

<b>币种列表:</b>
{coins}

💡 提示: 价格接近支撑线，可能是抄底机会
📍 查看详情: {url}
""",
        "sell_signal": """
🔴 <b>逃顶信号触发</b>

⏰ 时间: {time}
📊 触发币种: {count}个

<b>币种列表:</b>
{coins}

⚠️ 提示: 价格接近压力线，建议考虑止盈
📍 查看详情: {url}
"""
    }
}

def save_config(config_path="/home/user/webapp/telegram_config.json"):
    """保存配置到文件"""
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(TELEGRAM_CONFIG, f, indent=2, ensure_ascii=False)
    print(f"✅ Telegram配置已保存到: {config_path}")

def load_config(config_path="/home/user/webapp/telegram_config.json"):
    """从文件加载配置"""
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return TELEGRAM_CONFIG

if __name__ == '__main__':
    # 保存配置
    save_config()
    
    # 显示配置信息
    print("\n" + "="*60)
    print("📱 Telegram消息系统配置")
    print("="*60)
    print(f"\n🤖 Bot名称: {TELEGRAM_CONFIG['bot_info']['username']}")
    print(f"🆔 Bot ID: {TELEGRAM_CONFIG['bot_info']['id']}")
    print(f"💬 Chat ID: {TELEGRAM_CONFIG['chat_id']}")
    print(f"\n✅ 抄底信号推送: {'开启' if TELEGRAM_CONFIG['signal_types']['buy']['enabled'] else '关闭'}")
    print(f"✅ 逃顶信号推送: {'开启' if TELEGRAM_CONFIG['signal_types']['sell']['enabled'] else '关闭'}")
    print(f"\n⏱️  冷却时间: {TELEGRAM_CONFIG['push_conditions']['cooldown_seconds']}秒")
    print(f"📊 最少触发币种: {TELEGRAM_CONFIG['push_conditions']['min_coins']}个")
    print("\n" + "="*60)
