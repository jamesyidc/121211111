#!/usr/bin/env python3
"""
Telegram消息推送服务
监控支撑/阻力位信号并自动推送到Telegram
"""
import requests
import json
import time
import sqlite3
from datetime import datetime, timedelta
import pytz
from telegram_config import load_config

DB_PATH = "/home/user/webapp/crypto_data.db"
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

class TelegramNotifier:
    def __init__(self):
        self.config = load_config()
        self.bot_token = self.config['bot_token']
        self.chat_id = self.config['chat_id']
        self.api_base = self.config['api_base_url']
        self.last_buy_signal_time = None
        self.last_sell_signal_time = None
        self.last_double_buy_signal_time = None  # 双重抄底信号冷却
        self.last_double_sell_signal_time = None  # 双重逃顶信号冷却
        
    def log(self, message):
        """打印日志"""
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}", flush=True)
    
    def send_message(self, text, retry_count=0):
        """发送Telegram消息"""
        url = f"{self.api_base}/bot{self.bot_token}/sendMessage"
        
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": self.config['message_settings']['parse_mode'],
            "disable_web_page_preview": self.config['message_settings']['disable_web_page_preview'],
            "disable_notification": self.config['message_settings']['disable_notification']
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            response_data = response.json()
            
            if response_data.get('ok'):
                self.log(f"✅ 消息发送成功 (Message ID: {response_data['result']['message_id']})")
                return True
            else:
                error_msg = response_data.get('description', 'Unknown error')
                self.log(f"❌ 消息发送失败: {error_msg}")
                
                # 重试机制
                max_retries = self.config['push_conditions']['max_retries']
                if retry_count < max_retries:
                    retry_delay = self.config['push_conditions']['retry_delay']
                    self.log(f"🔄 {retry_delay}秒后重试 ({retry_count + 1}/{max_retries})...")
                    time.sleep(retry_delay)
                    return self.send_message(text, retry_count + 1)
                
                return False
                
        except Exception as e:
            self.log(f"❌ 发送消息异常: {e}")
            
            # 重试机制
            max_retries = self.config['push_conditions']['max_retries']
            if retry_count < max_retries:
                retry_delay = self.config['push_conditions']['retry_delay']
                self.log(f"🔄 {retry_delay}秒后重试 ({retry_count + 1}/{max_retries})...")
                time.sleep(retry_delay)
                return self.send_message(text, retry_count + 1)
            
            return False
    
    def format_buy_signal(self, signal_data):
        """格式化抄底信号消息（支撑线1+支撑线2总数>=8，强信号！）"""
        # 获取支撑线统计
        s1_count = signal_data.get('support_s1_count', 0)
        s2_count = signal_data.get('support_s2_count', 0)
        total_count = signal_data['count']
        
        # 格式化币种列表
        coins_list = []
        for i, coin in enumerate(signal_data['coins'], 1):
            coins_list.append(f"{i}. {coin['symbol']} - ${coin['price']:.2f} ({coin['position']})")
        
        coins_text = "\n".join(coins_list) if coins_list else "（所有币种均为双重抄底信号）"
        
        message = f"""
✅✅✅ <b>【强势抄底信号！】</b> ✅✅✅
━━━━━━━━━━━━━━━━━━━━━━
💎 <b>市场机会显现！建议关注！</b>
━━━━━━━━━━━━━━━━━━━━━━

⏰ 触发时间: {signal_data['time']}
📊 <b>总触碰数: {total_count}个币种</b>
   ├─ 支撑线1: {s1_count}个币种
   └─ 支撑线2: {s2_count}个币种

🔥 <b>信号强度: 🟢🟢🟢 强势买入 🟢🟢🟢</b>

💰 <b>关键提示</b>:
   • 多个币种同时触碰支撑线
   • 市场可能存在反弹机会
   • 建议关注潜在买入点
   • 注意仓位管理和风控

<b>单独触发币种:</b>
{coins_text}

━━━━━━━━━━━━━━━━━━━━━━
📍 实时监控: https://5000-ilsitop6yown44mau7vd7-c07dda5e.sandbox.novita.ai/support-resistance
━━━━━━━━━━━━━━━━━━━━━━
"""
        return message
    
    def format_sell_signal(self, signal_data):
        """格式化逃顶信号消息（压力线1+压力线2总数>=8，最强信号！）"""
        # 获取压力线统计
        r1_count = signal_data.get('pressure_r1_count', 0)
        r2_count = signal_data.get('pressure_r2_count', 0)
        total_count = signal_data['count']
        
        # 格式化币种列表
        coins_list = []
        for i, coin in enumerate(signal_data['coins'], 1):
            coins_list.append(f"{i}. {coin['symbol']} - ${coin['price']:.2f} ({coin['position']})")
        
        coins_text = "\n".join(coins_list) if coins_list else "（所有币种均为双重逃顶信号）"
        
        message = f"""
🚨🚨🚨 <b>【最强逃顶信号！】</b> 🚨🚨🚨
━━━━━━━━━━━━━━━━━━━━━━
⚠️ <b>市场风险极高！建议立即关注！</b>
━━━━━━━━━━━━━━━━━━━━━━

⏰ 触发时间: {signal_data['time']}
📊 <b>总触碰数: {total_count}个币种</b>
   ├─ 压力线1: {r1_count}个币种
   └─ 压力线2: {r2_count}个币种

🔥 <b>信号强度: 🔴🔴🔴 极度危险 🔴🔴🔴</b>

💥 <b>关键提示</b>:
   • 多个币种同时触碰压力线
   • 市场可能面临重大调整
   • 强烈建议考虑止盈/减仓
   • 避免追高，控制风险

<b>单独触发币种:</b>
{coins_text}

━━━━━━━━━━━━━━━━━━━━━━
📍 实时监控: https://5000-ilsitop6yown44mau7vd7-c07dda5e.sandbox.novita.ai/support-resistance
━━━━━━━━━━━━━━━━━━━━━━
"""
        return message
    
    def format_double_buy_signal(self, signal_data):
        """格式化双重抄底信号消息（同时触发支撑1和支撑2）"""
        # 使用自定义模板
        coins_list = []
        for i, coin in enumerate(signal_data['coins'], 1):
            coins_list.append(f"{i}. {coin['symbol']} - ${coin['price']:.2f}\n   距支撑1: {coin['distance_s1']:.2f}% | 距支撑2: {coin['distance_s2']:.2f}%")
        
        coins_text = "\n".join(coins_list)
        
        message = f"""
🟢🟢 <b>【双重抄底信号】</b> 🟢🟢

⏰ 时间: {signal_data['time']}
📊 触发币种: {signal_data['count']}个
🔥 信号强度: <b>极强（同时触发支撑1+支撑2）</b>

<b>币种列表:</b>
{coins_text}

💡 <b>重要提示</b>: 
   这些币种同时接近两条支撑线，是更强的抄底信号！
   建议重点关注这些机会。

📍 查看详情: https://5000-ilsitop6yown44mau7vd7-c07dda5e.sandbox.novita.ai/support-resistance
"""
        return message
    
    def format_double_sell_signal(self, signal_data):
        """格式化双重逃顶信号消息（同时触发压力1和压力2）"""
        # 使用自定义模板
        coins_list = []
        for i, coin in enumerate(signal_data['coins'], 1):
            coins_list.append(f"{i}. {coin['symbol']} - ${coin['price']:.2f}\n   距压力1: {coin['distance_r1']:.2f}% | 距压力2: {coin['distance_r2']:.2f}%")
        
        coins_text = "\n".join(coins_list)
        
        message = f"""
🔴🔴 <b>【双重逃顶信号】</b> 🔴🔴

⏰ 时间: {signal_data['time']}
📊 触发币种: {signal_data['count']}个
🔥 信号强度: <b>极强（同时触发压力1+压力2）</b>

<b>币种列表:</b>
{coins_text}

⚠️ <b>重要提示</b>: 
   这些币种同时接近两条压力线，是更强的逃顶信号！
   强烈建议考虑止盈或减仓。

📍 查看详情: https://5000-ilsitop6yown44mau7vd7-c07dda5e.sandbox.novita.ai/support-resistance
"""
        return message
    
    def check_cooldown(self, signal_type):
        """检查冷却时间"""
        cooldown_seconds = self.config['push_conditions']['cooldown_seconds']
        current_time = datetime.now(BEIJING_TZ)
        
        if signal_type == 'buy':
            if self.last_buy_signal_time:
                elapsed = (current_time - self.last_buy_signal_time).total_seconds()
                if elapsed < cooldown_seconds:
                    self.log(f"⏳ 抄底信号冷却中 (还需等待 {int(cooldown_seconds - elapsed)}秒)")
                    return False
            return True
        
        elif signal_type == 'sell':
            if self.last_sell_signal_time:
                elapsed = (current_time - self.last_sell_signal_time).total_seconds()
                if elapsed < cooldown_seconds:
                    self.log(f"⏳ 逃顶信号冷却中 (还需等待 {int(cooldown_seconds - elapsed)}秒)")
                    return False
            return True
        
        elif signal_type == 'double_buy':
            if self.last_double_buy_signal_time:
                elapsed = (current_time - self.last_double_buy_signal_time).total_seconds()
                if elapsed < cooldown_seconds:
                    self.log(f"⏳ 双重抄底信号冷却中 (还需等待 {int(cooldown_seconds - elapsed)}秒)")
                    return False
            return True
        
        elif signal_type == 'double_sell':
            if self.last_double_sell_signal_time:
                elapsed = (current_time - self.last_double_sell_signal_time).total_seconds()
                if elapsed < cooldown_seconds:
                    self.log(f"⏳ 双重逃顶信号冷却中 (还需等待 {int(cooldown_seconds - elapsed)}秒)")
                    return False
            return True
        
        return False
    
    def get_latest_signals(self):
        """从数据库获取最新信号"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # 修复：查询每个币种的最新记录，而不是单一时间戳
            # 这样可以避免因数据采集时间不一致导致的信号遗漏
            cursor.execute("""
                SELECT symbol, current_price, 
                       distance_to_support_1, distance_to_support_2,
                       distance_to_resistance_1, distance_to_resistance_2,
                       alert_scenario_1, alert_scenario_2, alert_scenario_3, alert_scenario_4,
                       record_time
                FROM support_resistance_levels srl
                WHERE record_time = (
                    SELECT MAX(record_time) 
                    FROM support_resistance_levels 
                    WHERE symbol = srl.symbol
                )
                AND datetime(record_time) >= datetime('now', '-5 minutes', 'localtime')
                ORDER BY symbol
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                return None, None, None, None
            
            # 分析抄底信号（情景1和情景2：接近支撑线）
            buy_signals = []
            double_buy_signals = []  # 同时触发支撑1和支撑2
            
            # 统计触碰支撑线的总数（用于普通抄底信号）
            support_s1_count = 0  # 触碰支撑1的币种数
            support_s2_count = 0  # 触碰支撑2的币种数
            
            for row in rows:
                symbol, price, dist_s1, dist_s2, dist_r1, dist_r2, s1, s2, s3, s4, record_time = row
                
                # 统计支撑线触碰数
                if s1 == 1:
                    support_s1_count += 1
                if s2 == 1:
                    support_s2_count += 1
                
                # 检查是否同时触发支撑1和支撑2（双重抄底信号 - 更强信号！）
                if s1 == 1 and s2 == 1:
                    double_buy_signals.append({
                        'symbol': symbol,
                        'price': price,
                        'position': '同时接近支撑1+支撑2',
                        'distance_s1': dist_s1,
                        'distance_s2': dist_s2
                    })
                # 单独触发
                elif s1 == 1 or s2 == 1:
                    position = "接近支撑1" if s1 == 1 else "接近支撑2"
                    buy_signals.append({
                        'symbol': symbol,
                        'price': price,
                        'position': position,
                        'distance': dist_s1 if s1 == 1 else dist_s2
                    })
            
            # 分析逃顶信号（情景3和情景4：接近压力线）
            sell_signals = []
            double_sell_signals = []  # 同时触发压力1和压力2
            
            # 统计触碰压力线的总数（用于普通逃顶信号）
            pressure_r1_count = 0  # 触碰压力1的币种数
            pressure_r2_count = 0  # 触碰压力2的币种数
            
            for row in rows:
                symbol, price, dist_s1, dist_s2, dist_r1, dist_r2, s1, s2, s3, s4, record_time = row
                
                # 统计压力线触碰数
                if s3 == 1:
                    pressure_r1_count += 1
                if s4 == 1:
                    pressure_r2_count += 1
                
                # 检查是否同时触发压力1和压力2（双重逃顶信号 - 更强信号！）
                if s3 == 1 and s4 == 1:
                    double_sell_signals.append({
                        'symbol': symbol,
                        'price': price,
                        'position': '同时接近压力1+压力2',
                        'distance_r1': dist_r1,
                        'distance_r2': dist_r2
                    })
                # 单独触发
                elif s3 == 1 or s4 == 1:
                    position = "接近压力1" if s3 == 1 else "接近压力2"
                    sell_signals.append({
                        'symbol': symbol,
                        'price': price,
                        'position': position,
                        'distance': dist_r1 if s3 == 1 else dist_r2
                    })
            
            # 构建信号数据
            # 普通抄底信号：支撑1触碰数 + 支撑2触碰数
            total_support_count = support_s1_count + support_s2_count
            buy_data = None
            if total_support_count > 0:
                buy_data = {
                    'time': record_time,
                    'count': total_support_count,  # 总数 = 支撑1 + 支撑2
                    'coins': buy_signals,  # 具体币种列表（不包括双重抄底）
                    'support_s1_count': support_s1_count,
                    'support_s2_count': support_s2_count
                }
            
            # 普通逃顶信号：压力1触碰数 + 压力2触碰数
            total_pressure_count = pressure_r1_count + pressure_r2_count
            sell_data = None
            if total_pressure_count > 0:
                sell_data = {
                    'time': record_time,
                    'count': total_pressure_count,  # 总数 = 压力1 + 压力2
                    'coins': sell_signals,  # 具体币种列表（不包括双重逃顶）
                    'pressure_r1_count': pressure_r1_count,
                    'pressure_r2_count': pressure_r2_count
                }
            
            # 构建双重信号数据
            double_buy_data = None
            if double_buy_signals:
                double_buy_data = {
                    'time': record_time,
                    'count': len(double_buy_signals),
                    'coins': double_buy_signals
                }
            
            double_sell_data = None
            if double_sell_signals:
                double_sell_data = {
                    'time': record_time,
                    'count': len(double_sell_signals),
                    'coins': double_sell_signals
                }
            
            return buy_data, sell_data, double_buy_data, double_sell_data
            
        except Exception as e:
            self.log(f"❌ 获取信号数据失败: {e}")
            return None, None, None, None
    
    def check_and_notify(self):
        """检查信号并发送通知"""
        self.log("🔍 检查最新信号...")
        
        # 获取最新信号（包括双重信号）
        buy_data, sell_data, double_buy_data, double_sell_data = self.get_latest_signals()
        
        # 优先处理双重抄底信号（更强信号）
        if double_buy_data and self.config['signal_types'].get('double_buy', {}).get('enabled', False):
            min_coins_double_buy = self.config['signal_types'].get('double_buy', {}).get('min_coins', 1)
            if double_buy_data['count'] >= min_coins_double_buy:
                if self.check_cooldown('double_buy'):
                    self.log(f"🟢🟢 检测到双重抄底信号（支撑1+2）: {double_buy_data['count']}个币种")
                    message = self.format_double_buy_signal(double_buy_data)
                    if self.send_message(message):
                        self.last_double_buy_signal_time = datetime.now(BEIJING_TZ)
                else:
                    self.log(f"⏳ 双重抄底信号在冷却期，跳过推送")
            else:
                self.log(f"📊 双重抄底信号币种数不足 ({double_buy_data['count']} < {min_coins_double_buy})，跳过推送")
        
        # 处理普通抄底信号（强势信号！）
        if buy_data and self.config['signal_types']['buy']['enabled']:
            min_coins_buy = self.config['signal_types'].get('buy', {}).get('min_coins', self.config['push_conditions']['min_coins'])
            s1_count = buy_data.get('support_s1_count', 0)
            s2_count = buy_data.get('support_s2_count', 0)
            if buy_data['count'] >= min_coins_buy:
                if self.check_cooldown('buy'):
                    self.log(f"✅✅✅ 检测到强势抄底信号！总数: {buy_data['count']}个币种 (支撑1: {s1_count}个 + 支撑2: {s2_count}个)")
                    message = self.format_buy_signal(buy_data)
                    if self.send_message(message):
                        self.last_buy_signal_time = datetime.now(BEIJING_TZ)
                else:
                    self.log(f"⏳ 抄底信号在冷却期，跳过推送")
            else:
                self.log(f"📊 抄底信号币种数不足 ({buy_data['count']} < {min_coins_buy}，支撑1: {s1_count}个, 支撑2: {s2_count}个)，跳过推送")
        
        # 优先处理双重逃顶信号（更强信号）
        if double_sell_data and self.config['signal_types'].get('double_sell', {}).get('enabled', False):
            min_coins_double_sell = self.config['signal_types'].get('double_sell', {}).get('min_coins', 1)
            if double_sell_data['count'] >= min_coins_double_sell:
                if self.check_cooldown('double_sell'):
                    self.log(f"🔴🔴 检测到双重逃顶信号（压力1+2）: {double_sell_data['count']}个币种")
                    message = self.format_double_sell_signal(double_sell_data)
                    if self.send_message(message):
                        self.last_double_sell_signal_time = datetime.now(BEIJING_TZ)
                else:
                    self.log(f"⏳ 双重逃顶信号在冷却期，跳过推送")
            else:
                self.log(f"📊 双重逃顶信号币种数不足 ({double_sell_data['count']} < {min_coins_double_sell})，跳过推送")
        
        # 处理普通逃顶信号（最强信号！）
        if sell_data and self.config['signal_types']['sell']['enabled']:
            min_coins_sell = self.config['signal_types'].get('sell', {}).get('min_coins', self.config['push_conditions']['min_coins'])
            r1_count = sell_data.get('pressure_r1_count', 0)
            r2_count = sell_data.get('pressure_r2_count', 0)
            if sell_data['count'] >= min_coins_sell:
                if self.check_cooldown('sell'):
                    self.log(f"🚨🚨🚨 检测到最强逃顶信号！总数: {sell_data['count']}个币种 (压力1: {r1_count}个 + 压力2: {r2_count}个)")
                    message = self.format_sell_signal(sell_data)
                    if self.send_message(message):
                        self.last_sell_signal_time = datetime.now(BEIJING_TZ)
                else:
                    self.log(f"⏳ 逃顶信号在冷却期，跳过推送")
            else:
                self.log(f"📊 逃顶信号币种数不足 ({sell_data['count']} < {min_coins_sell}，压力1: {r1_count}个, 压力2: {r2_count}个)，跳过推送")
        
        if not buy_data and not sell_data and not double_buy_data and not double_sell_data:
            self.log("📭 当前没有触发信号")

def main():
    """主函数"""
    notifier = TelegramNotifier()
    
    notifier.log("")
    notifier.log("="*80)
    notifier.log("📱 Telegram消息推送服务启动")
    notifier.log("="*80)
    notifier.log(f"🤖 Bot: {notifier.config['bot_info']['username']}")
    notifier.log(f"💬 Chat ID: {notifier.chat_id}")
    notifier.log(f"⏱️  检查间隔: 30秒")
    notifier.log(f"🔔 冷却时间: {notifier.config['push_conditions']['cooldown_seconds']}秒")
    notifier.log("="*80)
    notifier.log("")
    
    # 主循环
    while True:
        try:
            notifier.check_and_notify()
            time.sleep(30)  # 每30秒检查一次
        except KeyboardInterrupt:
            notifier.log("\n👋 收到停止信号，正在退出...")
            break
        except Exception as e:
            notifier.log(f"❌ 发生错误: {e}")
            time.sleep(30)

if __name__ == '__main__':
    main()
