#!/usr/bin/env python3
"""
2小时逃顶信号监控脚本
当2小时内逃顶信号数超过80时，发送Telegram警告
"""

import sys
import time
import requests
from datetime import datetime
import pytz

sys.path.insert(0, '/home/user/webapp')
sys.path.insert(0, '/home/user/webapp/source_code')
from telegram_notifier import TelegramNotifier

# 配置
API_URL = 'http://localhost:5000/api/support-resistance/signals-computed'
THRESHOLD = 80  # 2小时信号数阈值
CHECK_INTERVAL = 60  # 检查间隔（秒）
COOLDOWN_MINUTES = 30  # 冷却时间（分钟），避免频繁推送

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class EscapeSignal2hMonitor:
    """2小时逃顶信号监控器"""
    
    def __init__(self):
        self.notifier = TelegramNotifier()
        self.last_alert_time = None
        self.last_signal_count = 0
        
    def log(self, message):
        """打印日志"""
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}", flush=True)
        
    def get_2h_signal_count(self):
        """从API获取2小时逃顶信号数"""
        try:
            response = requests.get(API_URL, timeout=10)
            result = response.json()
            
            if result.get('success'):
                stats = result.get('stats', {})
                count_2h = stats.get('sell_signals_2h', 0)
                count_24h = stats.get('sell_signals_24h', 0)
                return count_2h, count_24h
            else:
                self.log(f"❌ API返回失败: {result.get('message')}")
                return None, None
                
        except Exception as e:
            self.log(f"❌ 获取数据失败: {e}")
            return None, None
    
    def should_send_alert(self, count_2h):
        """判断是否应该发送警告"""
        if count_2h is None or count_2h <= THRESHOLD:
            return False
            
        # 检查冷却时间
        if self.last_alert_time:
            elapsed = (datetime.now(BEIJING_TZ) - self.last_alert_time).total_seconds()
            if elapsed < COOLDOWN_MINUTES * 60:
                remaining = COOLDOWN_MINUTES * 60 - elapsed
                self.log(f"⏳ 冷却中，剩余 {remaining/60:.1f} 分钟")
                return False
        
        return True
    
    def send_alert(self, count_2h, count_24h):
        """发送警告消息"""
        now_str = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        # 构建消息
        message = f"""
🚨 <b>逃顶信号警告</b>

⚠️ 2小时内逃顶信号数已超过阈值！

📊 <b>统计数据:</b>
━━━━━━━━━━━━━━━
⏰ 2小时信号数: <b>{count_2h}</b> 个
📌 阈值: {THRESHOLD} 个
🔺 超出: <b>+{count_2h - THRESHOLD}</b> 个

📅 24小时信号数: {count_24h} 个

⏰ 触发时间: {now_str}

💡 <b>建议:</b>
• 市场可能处于高位震荡或回调阶段
• 建议关注已有仓位的止盈机会
• 避免追高，等待回调机会

📍 查看详情: http://localhost:5000/support-resistance
"""
        
        # 发送消息
        success = self.notifier.send_message(message)
        
        if success:
            self.last_alert_time = datetime.now(BEIJING_TZ)
            self.log(f"✅ 警告消息已发送 (2h信号数: {count_2h})")
        else:
            self.log(f"❌ 警告消息发送失败")
            
        return success
    
    def check_and_alert(self):
        """检查信号数并在必要时发送警告"""
        count_2h, count_24h = self.get_2h_signal_count()
        
        if count_2h is None:
            return
        
        # 记录当前状态
        if count_2h != self.last_signal_count:
            status = "🔺" if count_2h > self.last_signal_count else "🔻"
            self.log(f"{status} 2小时信号数: {count_2h} (24h: {count_24h})")
            self.last_signal_count = count_2h
        
        # 判断是否需要发送警告
        if self.should_send_alert(count_2h):
            self.log(f"🚨 触发警告条件！2h信号数 {count_2h} > 阈值 {THRESHOLD}")
            self.send_alert(count_2h, count_24h)
        elif count_2h > THRESHOLD:
            self.log(f"⚠️  2h信号数 {count_2h} > 阈值 {THRESHOLD}，但在冷却期内")
        else:
            self.log(f"✅ 正常范围内 (2h: {count_2h} <= {THRESHOLD})")
    
    def run(self):
        """运行监控循环"""
        self.log("=" * 60)
        self.log("🚀 2小时逃顶信号监控器启动")
        self.log(f"📊 监控阈值: {THRESHOLD} 个信号")
        self.log(f"⏱️  检查间隔: {CHECK_INTERVAL} 秒")
        self.log(f"🔄 冷却时间: {COOLDOWN_MINUTES} 分钟")
        self.log("=" * 60)
        
        while True:
            try:
                self.check_and_alert()
                time.sleep(CHECK_INTERVAL)
            except KeyboardInterrupt:
                self.log("\n⏹️  监控器已停止")
                break
            except Exception as e:
                self.log(f"❌ 错误: {e}")
                time.sleep(CHECK_INTERVAL)


def main():
    """主函数"""
    monitor = EscapeSignal2hMonitor()
    monitor.run()


if __name__ == '__main__':
    main()
