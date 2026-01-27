#!/usr/bin/env python3
"""
极端市场预警监控
监控27个币种的涨跌幅总和，当>=100%或<=-80%时发送最高优先级TG预警
间隔1小时只标记和通知一次
"""
import requests
import json
import time
import sqlite3
from datetime import datetime, timedelta
import pytz
from telegram_config import load_config

DB_PATH = "/home/user/webapp/databases/crypto_data.db"
JSONL_PATH = "/home/user/webapp/data/okx_trading_jsonl/okx_day_change.jsonl"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 预警阈值
EXTREME_HIGH_THRESHOLD = 100.0  # >=100%
EXTREME_LOW_THRESHOLD = -80.0   # <=-80%
COOLDOWN_SECONDS = 3600  # 1小时冷却

class ExtremeMarketMonitor:
    def __init__(self):
        self.config = load_config()
        self.bot_token = self.config['bot_token']
        self.chat_id = self.config['chat_id']
        self.api_base = self.config['api_base_url']
        self.last_extreme_high_time = None
        self.last_extreme_low_time = None
        self.init_db()
        
    def log(self, message):
        """打印日志"""
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}", flush=True)
    
    def init_db(self):
        """初始化数据库表"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # 创建极端市场预警记录表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS extreme_market_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_time TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    total_change REAL NOT NULL,
                    coin_count INTEGER NOT NULL,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_extreme_alerts_time 
                ON extreme_market_alerts(alert_time)
            """)
            
            conn.commit()
            conn.close()
            self.log("✅ 数据库初始化完成")
        except Exception as e:
            self.log(f"❌ 数据库初始化失败: {e}")
    
    def send_telegram_message(self, text, retry_count=0):
        """发送Telegram消息（最高优先级，启用通知声音）"""
        url = f"{self.api_base}/bot{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "disable_notification": False  # 强制启用通知声音
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response_data = response.json()
            
            if response_data.get('ok'):
                self.log(f"✅ 极端市场预警已发送 (Message ID: {response_data['result']['message_id']})")
                return True
            else:
                error_msg = response_data.get('description', 'Unknown error')
                self.log(f"❌ 消息发送失败: {error_msg}")
                
                # 重试机制
                if retry_count < 3:
                    self.log(f"🔄 5秒后重试 ({retry_count + 1}/3)...")
                    time.sleep(5)
                    return self.send_telegram_message(text, retry_count + 1)
                
                return False
                
        except Exception as e:
            self.log(f"❌ 发送消息异常: {e}")
            
            # 重试机制
            if retry_count < 3:
                self.log(f"🔄 5秒后重试 ({retry_count + 1}/3)...")
                time.sleep(5)
                return self.send_telegram_message(text, retry_count + 1)
            
            return False
    
    def get_latest_okx_data(self):
        """从JSONL文件获取最新的OKX 27币数据"""
        try:
            # 读取最后一行
            with open(JSONL_PATH, 'rb') as f:
                # 快速定位到文件末尾
                f.seek(0, 2)
                file_size = f.tell()
                
                if file_size == 0:
                    return None
                
                # 回退查找最后一行
                buffer_size = min(8192, file_size)
                f.seek(max(0, file_size - buffer_size))
                lines = f.read().decode('utf-8').strip().split('\n')
                
                if not lines:
                    return None
                
                # 解析最后一行
                last_line = lines[-1]
                data = json.loads(last_line)
                
                # 转换day_changes字典为details列表
                day_changes = data.get('day_changes', {})
                details = [
                    {'symbol': symbol.replace('-USDT-SWAP', ''), 'change_24h': change}
                    for symbol, change in day_changes.items()
                ]
                
                return {
                    'record_time': data.get('record_time'),
                    'total_change': data.get('total_change', 0),
                    'coin_count': len(details),
                    'details': details
                }
        except Exception as e:
            self.log(f"❌ 读取OKX数据失败: {e}")
            return None
    
    def check_cooldown(self, alert_type):
        """检查冷却时间"""
        current_time = datetime.now(BEIJING_TZ)
        
        if alert_type == 'extreme_high':
            if self.last_extreme_high_time:
                elapsed = (current_time - self.last_extreme_high_time).total_seconds()
                if elapsed < COOLDOWN_SECONDS:
                    remaining = int(COOLDOWN_SECONDS - elapsed)
                    self.log(f"⏳ 极端上涨预警冷却中 (还需等待 {remaining}秒 / {remaining//60}分钟)")
                    return False
            return True
        
        elif alert_type == 'extreme_low':
            if self.last_extreme_low_time:
                elapsed = (current_time - self.last_extreme_low_time).total_seconds()
                if elapsed < COOLDOWN_SECONDS:
                    remaining = int(COOLDOWN_SECONDS - elapsed)
                    self.log(f"⏳ 极端下跌预警冷却中 (还需等待 {remaining}秒 / {remaining//60}分钟)")
                    return False
            return True
        
        return False
    
    def save_alert_to_db(self, alert_time, alert_type, total_change, coin_count, details):
        """保存预警记录到数据库"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            details_json = json.dumps(details, ensure_ascii=False)
            
            cursor.execute("""
                INSERT INTO extreme_market_alerts 
                (alert_time, alert_type, total_change, coin_count, details)
                VALUES (?, ?, ?, ?, ?)
            """, (alert_time, alert_type, total_change, coin_count, details_json))
            
            conn.commit()
            conn.close()
            self.log(f"✅ 预警记录已保存到数据库")
        except Exception as e:
            self.log(f"❌ 保存预警记录失败: {e}")
    
    def format_extreme_high_alert(self, data):
        """格式化极端上涨预警消息"""
        total_change = data['total_change']
        coin_count = data['coin_count']
        record_time = data['record_time']
        details = data['details']
        
        # 找出涨幅最大的前5个币种
        sorted_coins = sorted(details, key=lambda x: x.get('change_24h', 0), reverse=True)
        top_5 = sorted_coins[:5]
        
        coins_text = "\n".join([
            f"   {i+1}. {coin['symbol']}: <b>+{coin['change_24h']:.2f}%</b>"
            for i, coin in enumerate(top_5)
        ])
        
        message = f"""
🔥🔥🔥 <b>【极端上涨预警！】</b> 🔥🔥🔥
━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>市场出现极端上涨！立即关注！</b>
━━━━━━━━━━━━━━━━━━━━━━

⏰ 触发时间: {record_time}
📊 <b>27币种总涨跌幅: +{total_change:.2f}%</b>
🔥 <b>预警阈值: ≥{EXTREME_HIGH_THRESHOLD:.0f}%</b>

📈 <b>涨幅最大币种 (Top 5):</b>
{coins_text}

💡 <b>重要提示</b>:
   • 市场出现极端上涨，注意风险
   • 警惕追高，可能面临回调
   • 考虑分批止盈策略
   • 设置止损保护利润

━━━━━━━━━━━━━━━━━━━━━━
📍 实时监控: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/escape-signal-history
━━━━━━━━━━━━━━━━━━━━━━

<b>🚨 这是最高优先级预警！🚨</b>
"""
        return message
    
    def format_extreme_low_alert(self, data):
        """格式化极端下跌预警消息"""
        total_change = data['total_change']
        coin_count = data['coin_count']
        record_time = data['record_time']
        details = data['details']
        
        # 找出跌幅最大的前5个币种
        sorted_coins = sorted(details, key=lambda x: x.get('change_24h', 0))
        bottom_5 = sorted_coins[:5]
        
        coins_text = "\n".join([
            f"   {i+1}. {coin['symbol']}: <b>{coin['change_24h']:.2f}%</b>"
            for i, coin in enumerate(bottom_5)
        ])
        
        message = f"""
💀💀💀 <b>【极端暴跌预警！】</b> 💀💀💀
━━━━━━━━━━━━━━━━━━━━━━
🚨 <b>市场出现极端暴跌！紧急关注！</b>
━━━━━━━━━━━━━━━━━━━━━━

⏰ 触发时间: {record_time}
📉 <b>27币种总涨跌幅: {total_change:.2f}%</b>
💀 <b>预警阈值: ≤{EXTREME_LOW_THRESHOLD:.0f}%</b>

📉 <b>跌幅最大币种 (Top 5):</b>
{coins_text}

⚠️ <b>重要提示</b>:
   • 市场出现极端暴跌，高度警惕
   • 避免盲目抄底，可能继续下跌
   • 检查仓位和保证金充足性
   • 考虑止损或减仓策略
   • 等待市场企稳信号

━━━━━━━━━━━━━━━━━━━━━━
📍 实时监控: https://5000-i4rq388xy9v1hw2uaz7ln-8f57ffe2.sandbox.novita.ai/escape-signal-history
━━━━━━━━━━━━━━━━━━━━━━

<b>🚨 这是最高优先级预警！🚨</b>
"""
        return message
    
    def check_and_alert(self):
        """检查市场数据并发送预警"""
        self.log("🔍 检查27币种市场数据...")
        
        # 获取最新数据
        data = self.get_latest_okx_data()
        
        if not data:
            self.log("❌ 无法获取OKX数据")
            return
        
        total_change = data['total_change']
        record_time = data['record_time']
        
        self.log(f"📊 当前27币种总涨跌幅: {total_change:.2f}% (记录时间: {record_time})")
        
        # 检查极端上涨
        if total_change >= EXTREME_HIGH_THRESHOLD:
            if self.check_cooldown('extreme_high'):
                self.log(f"🔥🔥🔥 触发极端上涨预警！总涨跌幅: +{total_change:.2f}%")
                message = self.format_extreme_high_alert(data)
                if self.send_telegram_message(message):
                    self.last_extreme_high_time = datetime.now(BEIJING_TZ)
                    self.save_alert_to_db(
                        record_time, 'extreme_high', 
                        total_change, data['coin_count'], data['details']
                    )
            else:
                self.log(f"⏳ 极端上涨预警在冷却期，跳过推送")
        
        # 检查极端下跌
        elif total_change <= EXTREME_LOW_THRESHOLD:
            if self.check_cooldown('extreme_low'):
                self.log(f"💀💀💀 触发极端暴跌预警！总涨跌幅: {total_change:.2f}%")
                message = self.format_extreme_low_alert(data)
                if self.send_telegram_message(message):
                    self.last_extreme_low_time = datetime.now(BEIJING_TZ)
                    self.save_alert_to_db(
                        record_time, 'extreme_low',
                        total_change, data['coin_count'], data['details']
                    )
            else:
                self.log(f"⏳ 极端下跌预警在冷却期，跳过推送")
        
        else:
            self.log(f"✅ 市场正常，总涨跌幅: {total_change:.2f}% (阈值范围: {EXTREME_LOW_THRESHOLD:.0f}% ~ +{EXTREME_HIGH_THRESHOLD:.0f}%)")

def main():
    """主函数"""
    monitor = ExtremeMarketMonitor()
    
    monitor.log("")
    monitor.log("="*80)
    monitor.log("🚨 极端市场预警监控服务启动")
    monitor.log("="*80)
    monitor.log(f"🤖 Bot: {monitor.config['bot_info']['username']}")
    monitor.log(f"💬 Chat ID: {monitor.chat_id}")
    monitor.log(f"📊 监控币种: 27个")
    monitor.log(f"📈 上涨预警阈值: ≥{EXTREME_HIGH_THRESHOLD:.0f}%")
    monitor.log(f"📉 下跌预警阈值: ≤{EXTREME_LOW_THRESHOLD:.0f}%")
    monitor.log(f"⏱️  检查间隔: 60秒")
    monitor.log(f"🔔 冷却时间: {COOLDOWN_SECONDS}秒 (1小时)")
    monitor.log(f"📍 优先级: 最高")
    monitor.log("="*80)
    monitor.log("")
    
    # 主循环
    while True:
        try:
            monitor.check_and_alert()
            time.sleep(60)  # 每60秒检查一次
        except KeyboardInterrupt:
            monitor.log("\n👋 收到停止信号，正在退出...")
            break
        except Exception as e:
            monitor.log(f"❌ 发生错误: {e}")
            import traceback
            monitor.log(traceback.format_exc())
            time.sleep(60)

if __name__ == '__main__':
    main()
