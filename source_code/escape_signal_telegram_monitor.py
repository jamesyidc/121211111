#!/usr/bin/env python3
"""
逃顶信号Telegram监控系统
监控以下信号并发送Telegram通知：
1. 空单盈利≥120% 数量≥3
2. 空单亏损 数量≥3
3. 2h极值标记
4. 24h极值标记
"""
import requests
import json
import time
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pytz

# 添加项目路径
sys.path.append('/home/user/webapp/source_code')
from telegram_config import TELEGRAM_CONFIG

class EscapeSignalTelegramMonitor:
    def __init__(self):
        self.bot_token = TELEGRAM_CONFIG['bot_token']
        self.chat_id = TELEGRAM_CONFIG['chat_id']
        self.api_base = TELEGRAM_CONFIG['api_base_url']
        
        # API端点
        self.escape_api = "http://localhost:5000/api/escape-signal-stats"
        self.profit_api = "http://localhost:5000/api/anchor-profit/latest"
        
        # 冷却时间（秒）- 避免重复推送
        self.cooldown = 3600  # 1小时
        
        # 记录上次推送时间
        self.last_push_times = {
            'short_profit_120': None,
            'short_loss': None,
            'peak_2h': None,
            'peak_24h': None
        }
        
        # 记录已推送的标记（避免重复）
        self.pushed_marks = {
            'peak_2h': set(),
            'peak_24h': set()
        }
        
        # 北京时区
        self.tz = pytz.timezone('Asia/Shanghai')
        
        print("✅ 逃顶信号Telegram监控系统已启动")
        print(f"📱 Bot: {TELEGRAM_CONFIG['bot_info']['username']}")
        print(f"💬 Chat ID: {self.chat_id}")
        print(f"⏱️  冷却时间: {self.cooldown}秒 ({self.cooldown/60:.0f}分钟)")
        
    def send_telegram(self, message):
        """发送Telegram消息"""
        try:
            url = f"{self.api_base}/bot{self.bot_token}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=data, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                print(f"✅ Telegram消息已发送")
                return True
            else:
                print(f"❌ Telegram发送失败: {result}")
                return False
                
        except Exception as e:
            print(f"❌ 发送Telegram消息异常: {e}")
            return False
    
    def can_push(self, signal_type):
        """检查是否可以推送（冷却时间）"""
        last_time = self.last_push_times.get(signal_type)
        if last_time is None:
            return True
        
        elapsed = time.time() - last_time
        return elapsed >= self.cooldown
    
    def get_beijing_time(self):
        """获取北京时间"""
        return datetime.now(self.tz).strftime('%Y-%m-%d %H:%M:%S')
    
    def check_short_positions(self):
        """检查空单盈亏状态"""
        try:
            response = requests.get(self.profit_api, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('data'):
                return
            
            latest = data['data'][0]
            stats = latest.get('stats', {})
            short_stats = stats.get('short', {})
            
            # 检查空单盈利≥120%
            profit_120 = short_stats.get('gte_120', 0)
            if profit_120 >= 3 and self.can_push('short_profit_120'):
                message = f"""
🟢 <b>空单盈利≥120%信号</b>

⏰ 时间: {self.get_beijing_time()}
📊 数量: {profit_120}个
📈 当前状态: 空单大幅盈利

💡 提示: 空单盈利超过120%，市场可能处于深度下跌
⚠️ 建议: 考虑部分止盈或持有

📍 查看详情: https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/escape-signal-history
"""
                if self.send_telegram(message):
                    self.last_push_times['short_profit_120'] = time.time()
                    print(f"📢 空单盈利≥120%通知已发送 (数量: {profit_120})")
            
            # 检查空单亏损
            loss_count = short_stats.get('loss', 0)
            if loss_count >= 3 and self.can_push('short_loss'):
                message = f"""
🔴 <b>空单亏损警报</b>

⏰ 时间: {self.get_beijing_time()}
📊 数量: {loss_count}个
📉 当前状态: 多个空单亏损

⚠️ 警告: {loss_count}个空单出现亏损，市场可能反转上涨
💡 建议: 密切关注仓位，考虑止损或调整策略

📍 查看详情: https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/escape-signal-history
"""
                if self.send_telegram(message):
                    self.last_push_times['short_loss'] = time.time()
                    print(f"📢 空单亏损通知已发送 (数量: {loss_count})")
                    
        except Exception as e:
            print(f"❌ 检查空单状态异常: {e}")
    
    def check_escape_peaks(self):
        """检查2h和24h极值标记"""
        try:
            response = requests.get(self.escape_api, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success') or not data.get('recent_data'):
                return
            
            recent_data = data['recent_data']
            
            # 检测2h每日极值
            self._check_2h_peaks(recent_data)
            
            # 检测24h 48小时窗口极值
            self._check_24h_peaks(recent_data)
            
        except Exception as e:
            print(f"❌ 检查逃顶极值异常: {e}")
    
    def _check_2h_peaks(self, recent_data):
        """检测2h每日极值"""
        # 按日期分组
        daily_data = {}
        for item in recent_data:
            stat_time = item.get('stat_time', '')
            if not stat_time:
                continue
            
            date = stat_time.split()[0]  # 提取日期部分
            signal_2h = item.get('signal_2h_count', 0)
            
            if signal_2h > 50:  # 阈值
                if date not in daily_data or signal_2h > daily_data[date]['value']:
                    daily_data[date] = {
                        'value': signal_2h,
                        'time': stat_time
                    }
        
        # 检查最近的极值点
        for date, peak in daily_data.items():
            mark_key = f"2h_{date}_{peak['value']}"
            
            # 如果这个标记已经推送过，跳过
            if mark_key in self.pushed_marks['peak_2h']:
                continue
            
            # 检查冷却时间
            if not self.can_push('peak_2h'):
                continue
            
            message = f"""
🔥 <b>2小时逃顶信号 - 每日极值</b>

⏰ 时间: {peak['time']}
📊 信号强度: {peak['value']}
📅 日期: {date}

💡 提示: 这是{date}的2小时逃顶信号最高值
⚠️ 建议: 市场可能接近短期顶部，注意风险

📍 查看详情: https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/escape-signal-history
"""
            if self.send_telegram(message):
                self.last_push_times['peak_2h'] = time.time()
                self.pushed_marks['peak_2h'].add(mark_key)
                print(f"📢 2h极值通知已发送 ({date}: {peak['value']})")
                
                # 限制缓存大小
                if len(self.pushed_marks['peak_2h']) > 100:
                    # 清理旧数据
                    self.pushed_marks['peak_2h'] = set(list(self.pushed_marks['peak_2h'])[-50:])
    
    def _check_24h_peaks(self, recent_data):
        """检测24h 48小时窗口极值"""
        if len(recent_data) < 2:
            return
        
        # 只检查最近100条数据，避免性能问题
        check_data = recent_data[-100:] if len(recent_data) > 100 else recent_data
        
        # 48小时窗口（分钟）
        window_size = 48 * 60
        
        # 只检查最新的几条数据（最多10条）
        for i in range(max(0, len(check_data) - 10), len(check_data)):
            current = check_data[i]
            signal_24h = current.get('signal_24h_count', 0)
            if signal_24h <= 200:  # 阈值
                continue
            
            current_time = current.get('stat_time', '')
            if not current_time:
                continue
            
            # 检查48小时窗口内是否是最大值
            try:
                current_dt = datetime.strptime(current_time, '%Y-%m-%d %H:%M:%S')
            except:
                continue
            
            # 计算窗口范围
            start_dt = current_dt - timedelta(hours=24)
            end_dt = current_dt + timedelta(hours=24)
            
            is_peak = True
            for other in check_data:
                other_time = other.get('stat_time', '')
                if not other_time:
                    continue
                
                try:
                    other_dt = datetime.strptime(other_time, '%Y-%m-%d %H:%M:%S')
                except:
                    continue
                
                # 在窗口内且值更大
                if start_dt <= other_dt <= end_dt:
                    if other.get('signal_24h_count', 0) > signal_24h:
                        is_peak = False
                        break
            
            if not is_peak:
                continue
            
            # 生成唯一标记
            mark_key = f"24h_{current_time}_{signal_24h}"
            
            # 如果已推送，跳过
            if mark_key in self.pushed_marks['peak_24h']:
                continue
            
            # 检查冷却时间
            if not self.can_push('peak_24h'):
                continue
            
            message = f"""
⭐ <b>24小时逃顶信号 - 48小时极值</b>

⏰ 时间: {current_time}
📊 信号强度: {signal_24h}
🔍 窗口: 48小时内最大值

💡 提示: 这是48小时窗口内的24小时逃顶信号极值
⚠️ 警告: 市场可能接近重要顶部，高度警惕

📍 查看详情: https://5000-igsydcyqs9jlcot56rnqk-18e660f9.sandbox.novita.ai/escape-signal-history
"""
            if self.send_telegram(message):
                self.last_push_times['peak_24h'] = time.time()
                self.pushed_marks['peak_24h'].add(mark_key)
                print(f"📢 24h极值通知已发送 ({current_time}: {signal_24h})")
                
                # 限制缓存大小
                if len(self.pushed_marks['peak_24h']) > 100:
                    self.pushed_marks['peak_24h'] = set(list(self.pushed_marks['peak_24h'])[-50:])
    
    def run(self, interval=60):
        """运行监控循环"""
        print(f"\n🚀 开始监控，检查间隔: {interval}秒")
        print("="*60)
        
        while True:
            try:
                print(f"\n⏰ {self.get_beijing_time()} - 开始检查...")
                
                # 检查空单盈亏
                self.check_short_positions()
                
                # 检查极值标记
                self.check_escape_peaks()
                
                print(f"✅ 检查完成，等待{interval}秒...")
                
            except KeyboardInterrupt:
                print("\n\n⚠️  收到中断信号，正在退出...")
                break
            except Exception as e:
                print(f"❌ 监控循环异常: {e}")
            
            time.sleep(interval)
        
        print("\n👋 监控系统已停止")

def main():
    """主函数"""
    print("="*60)
    print("🎯 逃顶信号Telegram监控系统")
    print("="*60)
    
    monitor = EscapeSignalTelegramMonitor()
    
    # 运行监控（每60秒检查一次）
    monitor.run(interval=60)

if __name__ == '__main__':
    main()
