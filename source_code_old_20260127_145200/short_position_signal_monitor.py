#!/usr/bin/env python3
"""
空单盈亏信号监控
监控空单盈利≥120%和空单亏损条件，当数量≥3时发送Telegram通知
"""
import requests
import json
import time
from datetime import datetime
import pytz
from telegram_config import load_config

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
API_BASE_URL = "http://localhost:5000"
CHECK_INTERVAL = 60  # 每60秒检查一次

class ShortPositionSignalMonitor:
    def __init__(self):
        self.config = load_config()
        self.bot_token = self.config['bot_token']
        self.chat_id = self.config['chat_id']
        self.api_base = self.config['api_base_url']
        
        # 记录上次触发时间（按小时），避免重复发送
        self.last_profit_trigger_hour = None
        self.last_loss_trigger_hour = None
        
    def log(self, message):
        """打印日志"""
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}", flush=True)
    
    def send_telegram_message(self, text):
        """发送Telegram消息"""
        url = f"{self.api_base}/bot{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
            "disable_notification": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response_data = response.json()
            
            if response_data.get('ok'):
                self.log(f"✅ Telegram消息发送成功")
                return True
            else:
                error_msg = response_data.get('description', 'Unknown error')
                self.log(f"❌ Telegram消息发送失败: {error_msg}")
                return False
                
        except Exception as e:
            self.log(f"❌ 发送Telegram消息异常: {e}")
            return False
    
    def format_profit_signal_message(self, count, datetime_str):
        """格式化空单盈利≥120%信号消息"""
        message = f"""
🟢🟢🟢 <b>【空单高盈利信号】</b> 🟢🟢🟢
━━━━━━━━━━━━━━━━━━━━━━
💰 <b>空单盈利≥120%</b>
━━━━━━━━━━━━━━━━━━━━━━

⏰ 触发时间: {datetime_str}
📊 <b>数量: {count} 个币种</b>

💡 <b>建议:</b>
• 考虑分批止盈
• 继续观察市场走势
• 注意保护利润

━━━━━━━━━━━━━━━━━━━━━━
🔗 查看详情: {API_BASE_URL}/escape-signal-history
"""
        return message
    
    def format_loss_signal_message(self, count, datetime_str):
        """格式化空单亏损信号消息"""
        message = f"""
🔴🔴🔴 <b>【空单亏损预警】</b> 🔴🔴🔴
━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>空单亏损</b>
━━━━━━━━━━━━━━━━━━━━━━

⏰ 触发时间: {datetime_str}
📊 <b>数量: {count} 个币种</b>

💡 <b>建议:</b>
• 评估止损策略
• 关注市场反转信号
• 控制风险敞口

━━━━━━━━━━━━━━━━━━━━━━
🔗 查看详情: {API_BASE_URL}/escape-signal-history
"""
        return message
    
    def check_short_position_signals(self):
        """检查空单盈亏信号"""
        try:
            # 获取最新的空单盈亏数据
            response = requests.get(f"{API_BASE_URL}/api/anchor-profit/latest", timeout=10)
            
            if response.status_code != 200:
                self.log(f"❌ API请求失败: {response.status_code}")
                return
            
            data = response.json()
            
            if not data or 'data' not in data or len(data['data']) == 0:
                self.log("⚠️ 暂无数据")
                return
            
            # 获取最新的一条记录
            latest_record = data['data'][0]
            stats = latest_record.get('stats', {})
            short_stats = stats.get('short', {})
            
            # 获取空单盈利≥120%和空单亏损的数量
            profit_120_count = short_stats.get('gte_120', 0)
            loss_count = short_stats.get('loss', 0)
            
            # 获取当前时间和小时标识
            datetime_str = latest_record.get('datetime', '')
            current_hour = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H')
            
            self.log(f"📊 空单盈利≥120%: {profit_120_count}, 空单亏损: {loss_count}")
            
            # 检查空单盈利≥120%信号（≥3个且该小时未触发过）
            if profit_120_count >= 3 and current_hour != self.last_profit_trigger_hour:
                self.log(f"🟢 触发空单盈利≥120%信号! 数量: {profit_120_count}")
                message = self.format_profit_signal_message(profit_120_count, datetime_str)
                
                if self.send_telegram_message(message):
                    self.last_profit_trigger_hour = current_hour
                    self.log(f"✅ 空单盈利信号已发送并记录小时: {current_hour}")
            
            # 检查空单亏损信号（≥3个且该小时未触发过）
            if loss_count >= 3 and current_hour != self.last_loss_trigger_hour:
                self.log(f"🔴 触发空单亏损信号! 数量: {loss_count}")
                message = self.format_loss_signal_message(loss_count, datetime_str)
                
                if self.send_telegram_message(message):
                    self.last_loss_trigger_hour = current_hour
                    self.log(f"✅ 空单亏损信号已发送并记录小时: {current_hour}")
                    
        except Exception as e:
            self.log(f"❌ 检查空单信号异常: {e}")
    
    def run(self):
        """主运行循环"""
        self.log("=" * 60)
        self.log("🚀 空单盈亏信号监控已启动")
        self.log(f"📊 监控条件: 空单盈利≥120% 或 空单亏损 ≥ 3个")
        self.log(f"⏱️  检查间隔: {CHECK_INTERVAL}秒")
        self.log(f"🔔 每小时只推送一次相同信号")
        self.log("=" * 60)
        
        while True:
            try:
                self.check_short_position_signals()
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                self.log("⚠️ 收到停止信号，正在退出...")
                break
            except Exception as e:
                self.log(f"❌ 运行异常: {e}")
                time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor = ShortPositionSignalMonitor()
    monitor.run()
