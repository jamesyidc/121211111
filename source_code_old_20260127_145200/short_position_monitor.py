#!/usr/bin/env python3
"""
空单盈利/亏损监控器
监控空单盈利≥120%和空单亏损的数量，当达到阈值时发送Telegram通知
阈值：空单盈利≥120%数量≥3，空单亏损数量≥3
每小时最多发送一次通知
"""
import requests
import json
import time
from datetime import datetime, timedelta
import pytz
from telegram_config import load_config

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
API_BASE_URL = "http://localhost:5000"

class ShortPositionMonitor:
    def __init__(self):
        self.config = load_config()
        self.bot_token = self.config['bot_token']
        self.chat_id = self.config['chat_id']
        self.api_base = self.config['api_base_url']
        
        # 记录上次发送通知的时间（按小时）
        self.last_profit_notify_hour = None
        self.last_loss_notify_hour = None
        
        # 阈值配置
        self.profit_threshold = 3  # 空单盈利≥120%数量阈值
        self.loss_threshold = 3    # 空单亏损数量阈值
        
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
            "parse_mode": "Markdown",
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
    
    def get_anchor_profit_data(self):
        """获取锚点系统盈利数据"""
        try:
            url = f"{API_BASE_URL}/api/anchor-profit/latest"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success') and result.get('data'):
                    # 返回最新的数据
                    return result['data'][0]
            
            self.log(f"❌ 获取锚点盈利数据失败: {response.status_code}")
            return None
            
        except Exception as e:
            self.log(f"❌ 获取锚点盈利数据异常: {e}")
            return None
    
    def format_profit_alert(self, data):
        """格式化空单盈利≥120%告警消息"""
        short_profit = data['stats']['short']['gte_120']
        timestamp = data['datetime']
        
        # 获取当前市场状态
        escape_signal_2h = data.get('escape_signal_2h', 0)
        
        message = f"""🟢 *空单盈利≥120%告警*

📊 *核心数据*
• 空单盈利≥120%数量: `{short_profit}` 个
• 2小时逃顶信号: `{escape_signal_2h}` 个

⏰ *触发时间*
{timestamp}

💡 *操作建议*
空单盈利≥120%数量已达到{self.profit_threshold}个，市场可能处于高位，建议关注回调风险。

🔗 [查看实盘锚点系统](https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real)
"""
        return message
    
    def format_loss_alert(self, data):
        """格式化空单亏损告警消息"""
        short_loss = data['stats']['short']['loss']
        timestamp = data['datetime']
        
        # 获取当前市场状态
        escape_signal_2h = data.get('escape_signal_2h', 0)
        
        message = f"""🔴 *空单亏损告警*

📊 *核心数据*
• 空单亏损数量: `{short_loss}` 个
• 2小时逃顶信号: `{escape_signal_2h}` 个

⏰ *触发时间*
{timestamp}

💡 *操作建议*
空单亏损数量已达到{self.loss_threshold}个，市场可能处于上涨趋势，建议关注止损风险。

🔗 [查看实盘锚点系统](https://5000-igsydcyqs9jlcot56rnqk-8f57ffe2.sandbox.novita.ai/anchor-system-real)
"""
        return message
    
    def check_and_notify(self):
        """检查数据并发送通知"""
        data = self.get_anchor_profit_data()
        if not data:
            return
        
        # 获取当前小时
        current_dt = datetime.strptime(data['datetime'], '%Y-%m-%d %H:%M:%S')
        current_hour = current_dt.strftime('%Y-%m-%d %H')
        
        # 检查空单盈利≥120%
        short_profit = data['stats']['short']['gte_120']
        if short_profit >= self.profit_threshold:
            if self.last_profit_notify_hour != current_hour:
                self.log(f"🟢 检测到空单盈利≥120%数量: {short_profit} (阈值: {self.profit_threshold})")
                message = self.format_profit_alert(data)
                if self.send_telegram_message(message):
                    self.last_profit_notify_hour = current_hour
                    self.log(f"✅ 空单盈利告警已发送 (时间: {current_hour})")
            else:
                self.log(f"⏭️ 空单盈利≥120%数量: {short_profit}，本小时已通知，跳过")
        else:
            self.log(f"📊 空单盈利≥120%数量: {short_profit} (未达到阈值 {self.profit_threshold})")
        
        # 检查空单亏损
        short_loss = data['stats']['short']['loss']
        if short_loss >= self.loss_threshold:
            if self.last_loss_notify_hour != current_hour:
                self.log(f"🔴 检测到空单亏损数量: {short_loss} (阈值: {self.loss_threshold})")
                message = self.format_loss_alert(data)
                if self.send_telegram_message(message):
                    self.last_loss_notify_hour = current_hour
                    self.log(f"✅ 空单亏损告警已发送 (时间: {current_hour})")
            else:
                self.log(f"⏭️ 空单亏损数量: {short_loss}，本小时已通知，跳过")
        else:
            self.log(f"📊 空单亏损数量: {short_loss} (未达到阈值 {self.loss_threshold})")
    
    def run(self, interval=60):
        """运行监控器
        
        Args:
            interval: 检查间隔（秒），默认60秒
        """
        self.log(f"🚀 空单盈利/亏损监控器启动")
        self.log(f"📊 监控配置:")
        self.log(f"   - 空单盈利≥120%阈值: {self.profit_threshold}")
        self.log(f"   - 空单亏损阈值: {self.loss_threshold}")
        self.log(f"   - 检查间隔: {interval}秒")
        self.log(f"   - 通知频率: 每小时最多1次")
        
        while True:
            try:
                self.log("=" * 60)
                self.log("🔍 开始检查空单盈利/亏损状态...")
                self.check_and_notify()
                self.log(f"⏳ 等待 {interval} 秒后进行下次检查...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.log("\n👋 监控器停止")
                break
            except Exception as e:
                self.log(f"❌ 监控器异常: {e}")
                import traceback
                self.log(traceback.format_exc())
                self.log(f"⏳ 60秒后重试...")
                time.sleep(60)

if __name__ == '__main__':
    monitor = ShortPositionMonitor()
    monitor.run(interval=60)  # 每60秒检查一次
