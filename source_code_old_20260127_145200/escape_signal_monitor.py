#!/usr/bin/env python3
"""
逃顶信号监控脚本
监控以下信号并发送TG消息：
1. 空单盈利≥120% 且数量≥3
2. 空单亏损 数量≥3
3. 2h信号极值标记（每日2h信号数的最大值>50）
4. 24h信号极值标记（48小时窗口内的最大值>200）

每小时检查一次，避免重复发送
"""
import requests
import json
import time
import os
import sys
from datetime import datetime, timedelta
import pytz

# 添加项目路径
sys.path.insert(0, '/home/user/webapp')
from source_code.telegram_config import load_config

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class EscapeSignalMonitor:
    def __init__(self):
        """初始化监控器"""
        self.config = load_config()
        self.bot_token = self.config['bot_token']
        self.chat_id = self.config['chat_id']
        self.api_base = self.config['api_base_url']
        
        # 记录上次发送消息的时间（按小时去重）
        self.last_profit_hour = None  # 空单盈利≥120%
        self.last_loss_hour = None    # 空单亏损
        self.last_2h_peak_hour = None # 2h极值
        self.last_24h_peak_hour = None # 24h极值
        
        self.api_escape_signal_url = "http://localhost:5000/api/escape-signal-stats"
        self.api_anchor_profit_url = "http://localhost:5000/api/anchor-profit/latest"
        
        self.log("✅ 逃顶信号监控器初始化完成")
    
    def log(self, message):
        """打印日志"""
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}", flush=True)
    
    def send_telegram_message(self, text, retry_count=0):
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
                self.log(f"✅ TG消息发送成功 (Message ID: {response_data['result']['message_id']})")
                return True
            else:
                error_msg = response_data.get('description', 'Unknown error')
                self.log(f"❌ TG消息发送失败: {error_msg}")
                
                # 重试机制
                if retry_count < 3:
                    self.log(f"🔄 5秒后重试 ({retry_count + 1}/3)...")
                    time.sleep(5)
                    return self.send_telegram_message(text, retry_count + 1)
                
                return False
                
        except Exception as e:
            self.log(f"❌ 发送TG消息异常: {e}")
            
            # 重试机制
            if retry_count < 3:
                self.log(f"🔄 5秒后重试 ({retry_count + 1}/3)...")
                time.sleep(5)
                return self.send_telegram_message(text, retry_count + 1)
            
            return False
    
    def get_escape_signal_data(self):
        """获取逃顶信号数据"""
        try:
            response = requests.get(self.api_escape_signal_url, timeout=10)
            data = response.json()
            
            if data.get('success'):
                return data
            else:
                self.log(f"❌ 获取逃顶信号数据失败: {data.get('message')}")
                return None
        except Exception as e:
            self.log(f"❌ 请求逃顶信号数据异常: {e}")
            return None
    
    def get_anchor_profit_data(self):
        """获取空单盈利/亏损数据"""
        try:
            response = requests.get(self.api_anchor_profit_url, timeout=10)
            data = response.json()
            
            if data.get('success') and len(data.get('data', [])) > 0:
                # 获取最新的一条记录
                latest_record = data['data'][0]
                return latest_record
            else:
                self.log(f"❌ 获取空单盈利数据失败")
                return None
        except Exception as e:
            self.log(f"❌ 请求空单盈利数据异常: {e}")
            return None
    
    def check_short_profit_120(self):
        """检查空单盈利≥120%标记（≥3个时）"""
        profit_data = self.get_anchor_profit_data()
        if not profit_data:
            return
        
        # 获取数据时间和统计
        data_time = profit_data.get('datetime', '')
        stats = profit_data.get('stats', {})
        short_stats = stats.get('short', {})
        profit_120_count = short_stats.get('gte_120', 0)
        
        # 检查是否满足条件
        if profit_120_count >= 3:
            # 检查是否在同一小时内已发送
            current_hour = datetime.strptime(data_time, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H')
            
            if current_hour != self.last_profit_hour:
                # 发送TG消息
                message = f"""
🟢🟢🟢 <b>【空单盈利≥120%信号】</b> 🟢🟢🟢
━━━━━━━━━━━━━━━━━━━━━━
💰 <b>空单盈利达到120%以上！</b>
━━━━━━━━━━━━━━━━━━━━━━

⏰ 触发时间: {data_time}
📊 <b>盈利≥120%数量: {profit_120_count}个</b>

💡 <b>建议操作:</b>
   • 考虑部分止盈
   • 关注市场反转信号
   • 保留核心仓位

━━━━━━━━━━━━━━━━━━━━━━
📈 <b>逃顶信号监控系统</b>
"""
                
                if self.send_telegram_message(message):
                    self.last_profit_hour = current_hour
                    self.log(f"✅ 空单盈利≥120%信号已发送 (数量: {profit_120_count})")
    
    def check_short_loss(self):
        """检查空单亏损标记（≥3个时）"""
        profit_data = self.get_anchor_profit_data()
        if not profit_data:
            return
        
        # 获取数据时间和统计
        data_time = profit_data.get('datetime', '')
        stats = profit_data.get('stats', {})
        short_stats = stats.get('short', {})
        loss_count = short_stats.get('loss', 0)
        
        # 检查是否满足条件
        if loss_count >= 3:
            # 检查是否在同一小时内已发送
            current_hour = datetime.strptime(data_time, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H')
            
            if current_hour != self.last_loss_hour:
                # 发送TG消息
                message = f"""
🔴🔴🔴 <b>【空单亏损预警】</b> 🔴🔴🔴
━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>空单亏损数量超过警戒线！</b>
━━━━━━━━━━━━━━━━━━━━━━

⏰ 触发时间: {data_time}
📊 <b>亏损数量: {loss_count}个</b>

💡 <b>建议操作:</b>
   • 检查止损设置
   • 评估市场趋势
   • 考虑减少空单仓位

━━━━━━━━━━━━━━━━━━━━━━
📈 <b>逃顶信号监控系统</b>
"""
                
                if self.send_telegram_message(message):
                    self.last_loss_hour = current_hour
                    self.log(f"✅ 空单亏损预警已发送 (数量: {loss_count})")
    
    def check_2h_peak(self):
        """检查2h信号极值标记（每日最大值>50）"""
        signal_data = self.get_escape_signal_data()
        if not signal_data:
            return
        
        recent_data = signal_data.get('recent_data', [])
        if not recent_data:
            return
        
        # 按日期分组，找出每天2h信号数的最大值
        daily_peaks = {}
        for record in recent_data:
            stat_time = record.get('stat_time', '')
            signal_2h = record.get('signal_2h_count', 0)
            
            if signal_2h > 50:
                date = stat_time.split(' ')[0]  # 提取日期
                
                if date not in daily_peaks or signal_2h > daily_peaks[date]['value']:
                    daily_peaks[date] = {
                        'value': signal_2h,
                        'time': stat_time
                    }
        
        # 检查最新的日峰值
        if daily_peaks:
            latest_date = max(daily_peaks.keys())
            peak_info = daily_peaks[latest_date]
            peak_time = peak_info['time']
            peak_value = peak_info['value']
            
            # 检查是否在同一小时内已发送
            current_hour = datetime.strptime(peak_time, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H')
            
            if current_hour != self.last_2h_peak_hour:
                # 发送TG消息
                message = f"""
🔥🔥🔥 <b>【2h信号极值标记】</b> 🔥🔥🔥
━━━━━━━━━━━━━━━━━━━━━━
📊 <b>2小时信号数创当日新高！</b>
━━━━━━━━━━━━━━━━━━━━━━

⏰ 触发时间: {peak_time}
📈 <b>2h信号数: {peak_value}</b>
📅 <b>日期: {latest_date}</b>

💡 <b>市场状况:</b>
   • 短期逃顶信号密集
   • 市场可能出现调整
   • 建议谨慎操作

━━━━━━━━━━━━━━━━━━━━━━
📈 <b>逃顶信号监控系统</b>
"""
                
                if self.send_telegram_message(message):
                    self.last_2h_peak_hour = current_hour
                    self.log(f"✅ 2h信号极值标记已发送 (峰值: {peak_value})")
    
    def check_24h_peak(self):
        """检查24h信号极值标记（48小时窗口内最大值>200）"""
        signal_data = self.get_escape_signal_data()
        if not signal_data:
            return
        
        recent_data = signal_data.get('recent_data', [])
        if not recent_data:
            return
        
        # 使用48小时滑动窗口查找峰值
        window_size = 48 * 60  # 假设每分钟一个数据点
        peaks = []
        
        for i in range(len(recent_data)):
            # 定义窗口范围
            start_idx = max(0, i - window_size // 2)
            end_idx = min(len(recent_data), i + window_size // 2 + 1)
            
            # 获取窗口内的最大值
            max_in_window = max(
                (record.get('signal_24h_count', 0) for record in recent_data[start_idx:end_idx]),
                default=0
            )
            
            # 如果当前点是窗口内的最大值且>200
            current_value = recent_data[i].get('signal_24h_count', 0)
            if current_value == max_in_window and current_value > 200:
                # 检查是否已有相近的峰值（避免重复）
                is_duplicate = False
                for peak in peaks:
                    if abs(peak['index'] - i) < window_size // 4:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    peaks.append({
                        'index': i,
                        'value': current_value,
                        'time': recent_data[i].get('stat_time', '')
                    })
        
        # 检查最新的峰值
        if peaks:
            latest_peak = peaks[-1]
            peak_time = latest_peak['time']
            peak_value = latest_peak['value']
            
            # 检查是否在同一小时内已发送
            current_hour = datetime.strptime(peak_time, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H')
            
            if current_hour != self.last_24h_peak_hour:
                # 发送TG消息
                message = f"""
⭐⭐⭐ <b>【24h信号极值标记】</b> ⭐⭐⭐
━━━━━━━━━━━━━━━━━━━━━━
📊 <b>24小时信号数创48h窗口新高！</b>
━━━━━━━━━━━━━━━━━━━━━━

⏰ 触发时间: {peak_time}
📈 <b>24h信号数: {peak_value}</b>

💡 <b>市场状况:</b>
   • 逃顶信号极度密集
   • 市场可能出现大幅调整
   • 强烈建议减仓观望

━━━━━━━━━━━━━━━━━━━━━━
📈 <b>逃顶信号监控系统</b>
"""
                
                if self.send_telegram_message(message):
                    self.last_24h_peak_hour = current_hour
                    self.log(f"✅ 24h信号极值标记已发送 (峰值: {peak_value})")
    
    def run_check(self):
        """执行一次完整检查"""
        self.log("=" * 50)
        self.log("🔍 开始检查逃顶信号...")
        
        try:
            # 检查空单盈利≥120%
            self.check_short_profit_120()
            time.sleep(2)
            
            # 检查空单亏损
            self.check_short_loss()
            time.sleep(2)
            
            # 检查2h信号极值
            self.check_2h_peak()
            time.sleep(2)
            
            # 检查24h信号极值
            self.check_24h_peak()
            
            self.log("✅ 检查完成")
        except Exception as e:
            self.log(f"❌ 检查过程出错: {e}")
        
        self.log("=" * 50)
    
    def run(self, interval=3600):
        """持续运行监控
        
        Args:
            interval: 检查间隔（秒），默认3600秒（1小时）
        """
        self.log(f"🚀 逃顶信号监控器启动，检查间隔: {interval}秒")
        
        while True:
            try:
                self.run_check()
                
                # 等待下次检查
                self.log(f"⏳ 等待 {interval} 秒后进行下次检查...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.log("⚠️ 收到停止信号，退出监控...")
                break
            except Exception as e:
                self.log(f"❌ 运行异常: {e}")
                self.log("⏳ 60秒后重试...")
                time.sleep(60)

if __name__ == "__main__":
    monitor = EscapeSignalMonitor()
    monitor.run(interval=3600)  # 每小时检查一次
