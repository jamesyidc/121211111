#!/usr/bin/env python3
"""
极值追踪系统
在逃顶信号出现极值预警时，记录27个币的快照，并追踪未来1h、3h、6h、12h、24h的价格变化

极值触发条件：
1. 逃顶信号2h出现预警标记
2. 27种币涨跌幅相加超过100%（27coins_high）
3. 27种币涨跌幅下跌分级：
   - 27coins_low_1: -80% 至 -119%（轻度）
   - 27coins_low_2: -120% 至 -179%（中度）
   - 27coins_low_3: -180% 及以下（重度）
4. 逃顶24h出现极值被标记
5. 1小时爆仓金额超过3000万美元

冷却期机制：
- 同一极值类型触发后，4小时内不再重复触发
- 不同极值类型可以同时触发

快照内容：
- 触发时间
- 触发类型（2h预警/27币涨跌幅极值/24h极值）
- 27个币的当前价格和涨跌幅
- 逃顶信号数据
- 追踪未来价格变化
"""

import json
import os
import sys
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
import pytz

# 添加项目路径
sys.path.insert(0, '/home/user/webapp')

BEIJING_TZ = pytz.timezone('Asia/Shanghai')
DATA_DIR = Path('/home/user/webapp/data/extreme_tracking')
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 数据文件路径
SNAPSHOTS_FILE = DATA_DIR / 'extreme_snapshots.jsonl'
TRACKING_FILE = DATA_DIR / 'extreme_tracking.jsonl'
COOLDOWN_FILE = DATA_DIR / 'trigger_cooldown.jsonl'

# 冷却期配置（秒）
COOLDOWN_PERIOD = 4 * 3600  # 4小时

# Telegram配置文件路径
TELEGRAM_CONFIG_PATH = '/home/user/webapp/configs/telegram_config.json'

class ExtremeValueTracker:
    """极值追踪器"""
    
    def __init__(self):
        """初始化追踪器"""
        self.api_base = "http://localhost:5000"
        self.last_triggers = self.load_cooldown_state()  # 加载冷却期状态
        self.telegram_config = self.load_telegram_config()  # 加载TG配置
        self.log("✅ 极值追踪器初始化完成")
    
    def load_cooldown_state(self):
        """加载冷却期状态"""
        if not COOLDOWN_FILE.exists():
            return {}
        
        try:
            with open(COOLDOWN_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    # 读取最后一行（最新状态）
                    return json.loads(lines[-1])
        except Exception as e:
            self.log(f"⚠️ 加载冷却期状态失败: {e}")
        
        return {}
    
    def save_cooldown_state(self):
        """保存冷却期状态"""
        try:
            with open(COOLDOWN_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(self.last_triggers, ensure_ascii=False) + '\n')
        except Exception as e:
            self.log(f"⚠️ 保存冷却期状态失败: {e}")
    
    def load_telegram_config(self):
        """加载Telegram配置"""
        try:
            if os.path.exists(TELEGRAM_CONFIG_PATH):
                with open(TELEGRAM_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.log(f"✅ Telegram配置已加载")
                    return config
            else:
                self.log(f"⚠️ Telegram配置文件不存在: {TELEGRAM_CONFIG_PATH}")
                return None
        except Exception as e:
            self.log(f"⚠️ 加载Telegram配置失败: {e}")
            return None
    
    def send_telegram_notification(self, snapshot_id, extreme_event):
        """发送Telegram通知"""
        if not self.telegram_config:
            self.log("⚠️ Telegram配置未加载，跳过通知")
            return False
        
        try:
            bot_token = self.telegram_config.get('bot_token')
            chat_id = self.telegram_config.get('chat_id')
            api_base = self.telegram_config.get('api_base_url', 'https://api.telegram.org')
            
            if not bot_token or not chat_id:
                self.log("⚠️ Telegram配置不完整，跳过通知")
                return False
            
            # 构建消息
            triggers = extreme_event.get('triggers', [])
            trigger_types = [t.get('type') for t in triggers]
            trigger_descriptions = [t.get('description') for t in triggers]
            
            total_change = extreme_event.get('total_change', 0)
            
            # 判断消息类型和emoji
            has_27coins_low = any('27coins_low' in t for t in trigger_types)
            has_27coins_high = '27coins_high' in trigger_types
            
            if has_27coins_low or has_27coins_high:
                if total_change < 0:
                    # 根据跌幅等级设置不同的emoji和描述
                    if total_change <= -180:
                        emoji = "🚨💀"
                        type_name = "极端严重跌幅"
                        color = "🔴🔴🔴"
                    elif total_change <= -120:
                        emoji = "⚠️📉"
                        type_name = "中度跌幅"
                        color = "🔴🔴"
                    else:
                        emoji = "📉"
                        type_name = "轻度跌幅"
                        color = "🔴"
                else:
                    emoji = "📈"
                    type_name = "极端涨幅"
                    color = "🟢"
            else:
                emoji = "⚠️"
                type_name = "极值预警"
                color = "🟡"
            
            # 获取爆仓数据
            liquidation_data = extreme_event.get('liquidation_data', {})
            liquidation_info = ""
            if liquidation_data:
                amount_wan = liquidation_data.get('amount_wan', 0)
                if amount_wan > 3000:
                    liquidation_info = f"\n💥 <b>1h爆仓</b>: {amount_wan:.2f}万美元"
            
            # 获取逃顶信号
            escape_data = extreme_event.get('escape_data', {})
            escape_info = ""
            if escape_data:
                if escape_data.get('has_2h_peak'):
                    signal_2h = escape_data.get('today_2h_max', 0)
                    escape_info += f"\n🚨 <b>2h逃顶</b>: {signal_2h}"
                if escape_data.get('has_24h_peak'):
                    signal_24h = escape_data.get('max_24h_value', 0)
                    escape_info += f"\n⚡ <b>24h逃顶</b>: {signal_24h}"
            
            message = f"""
{emoji} <b>极值追踪系统提醒</b> {emoji}

{color} <b>类型</b>: {type_name}
🔔 <b>触发条件</b>:
"""
            for desc in trigger_descriptions:
                message += f"  • {desc}\n"
            
            message += f"""
📊 <b>27币总涨跌</b>: <code>{total_change:+.2f}%</code>{liquidation_info}{escape_info}

🆔 <b>快照ID</b>: {snapshot_id}
⏰ <b>时间</b>: {extreme_event.get('datetime')}

📈 <b>追踪计划</b>: 1h / 3h / 6h / 12h / 24h
🔗 <b>查看详情</b>: /extreme-tracking
"""
            
            # 发送消息
            url = f"{api_base}/bot{bot_token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                self.log(f"✅ Telegram通知已发送: {snapshot_id}")
                return True
            else:
                self.log(f"⚠️ Telegram通知发送失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Telegram通知发送异常: {e}")
            return False
    
    
    def is_in_cooldown(self, trigger_type):
        """检查是否在冷却期内"""
        if trigger_type not in self.last_triggers:
            return False
        
        last_trigger_time = self.last_triggers[trigger_type]
        current_time = int(time.time())
        time_diff = current_time - last_trigger_time
        
        if time_diff < COOLDOWN_PERIOD:
            remaining = COOLDOWN_PERIOD - time_diff
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            self.log(f"⏳ {trigger_type} 在冷却期内，剩余 {hours}小时{minutes}分钟")
            return True
        
        return False
    
    def update_trigger_time(self, trigger_type):
        """更新触发时间"""
        self.last_triggers[trigger_type] = int(time.time())
        self.save_cooldown_state()
    
    def log(self, message):
        """打印日志"""
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}", flush=True)
    
    def get_escape_signal_stats(self):
        """获取逃顶信号统计数据"""
        try:
            url = f"{self.api_base}/api/escape-signal-stats"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('success'):
                return data
            else:
                self.log(f"❌ 获取逃顶信号数据失败: {data.get('message')}")
                return None
                
        except Exception as e:
            self.log(f"❌ 获取逃顶信号数据异常: {e}")
            return None
    
    def get_27_coins_data(self):
        """获取27个币的最新涨跌数据（包含价格）"""
        try:
            url = f"{self.api_base}/api/coin-price-tracker/latest?limit=1"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('success') and data.get('count') > 0:
                return data['data'][0]  # 返回最新一条记录
            else:
                self.log(f"❌ 获取27币数据失败: {data.get('message')}")
                return None
                
        except Exception as e:
            self.log(f"❌ 获取27币数据异常: {e}")
            return None
    
    def get_1h_liquidation_data(self):
        """获取1小时爆仓数据"""
        try:
            url = f"{self.api_base}/api/panic/latest"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if data.get('success') and data.get('data'):
                latest = data['data']
                # hour_1_amount 单位是万美元，需要转换
                amount_wan = latest.get('hour_1_amount', 0)
                amount_usd = amount_wan * 10000  # 转换为美元
                return {
                    'amount_wan': amount_wan,
                    'amount_usd': amount_usd,
                    'timestamp': latest.get('timestamp', 0),
                    'datetime': latest.get('datetime', ''),
                    'hour_24_amount': latest.get('hour_24_amount', 0),
                    'panic_index': latest.get('panic_index', 0)
                }
            else:
                self.log(f"❌ 获取1小时爆仓数据失败: {data.get('message')}")
                return None
                
        except Exception as e:
            self.log(f"❌ 获取1小时爆仓数据异常: {e}")
            return None
    
    def calculate_total_change(self, coins_data):
        """计算27个币的涨跌幅总和"""
        if not coins_data or 'day_changes' not in coins_data:
            return 0
        
        total = 0
        for symbol, coin_info in coins_data['day_changes'].items():
            if isinstance(coin_info, dict):
                change = coin_info.get('change_pct', 0)
            else:
                # 兼容旧格式（直接是数字）
                change = coin_info
            
            if isinstance(change, (int, float)):
                total += change
        
        return total
    
    def check_extreme_conditions(self):
        """检查是否满足极值条件（带冷却期检查）"""
        # 获取逃顶信号数据
        escape_data = self.get_escape_signal_stats()
        if not escape_data:
            return None
        
        # 获取27币数据
        coins_data = self.get_27_coins_data()
        if not coins_data:
            return None
        
        # 获取1小时爆仓数据
        liquidation_data = self.get_1h_liquidation_data()
        if not liquidation_data:
            return None
        
        # 计算27币涨跌幅总和
        total_change = self.calculate_total_change(coins_data)
        
        # 检查触发条件（只添加不在冷却期的触发器）
        triggers = []
        
        # 条件1: 2h信号极值标记
        if escape_data.get('has_2h_peak') and not self.is_in_cooldown('2h_peak'):
            triggers.append({
                'type': '2h_peak',
                'description': '2h逃顶信号极值',
                'value': escape_data.get('today_2h_max', 0),
                'data': escape_data.get('peak_2h_info')
            })
        
        # 条件2: 27币涨跌幅极值（上涨）
        if total_change > 100 and not self.is_in_cooldown('27coins_high'):
            triggers.append({
                'type': '27coins_high',
                'description': '27币涨跌幅总和超过100%',
                'value': total_change,
                'data': coins_data
            })
        
        # 条件2b: 27币涨跌幅极值（下跌）- 分3个等级
        # 优先检查最严重的等级
        if total_change <= -180:
            if not self.is_in_cooldown('27coins_low_3'):
                triggers.append({
                    'type': '27coins_low_3',
                    'description': '27币涨跌幅总和 ≤ -180%（重度下跌）',
                    'value': total_change,
                    'level': 3,
                    'data': coins_data
                })
        elif total_change <= -120:
            if not self.is_in_cooldown('27coins_low_2'):
                triggers.append({
                    'type': '27coins_low_2',
                    'description': '27币涨跌幅总和 -120% 至 -179%（中度下跌）',
                    'value': total_change,
                    'level': 2,
                    'data': coins_data
                })
        elif total_change <= -80:
            if not self.is_in_cooldown('27coins_low_1'):
                triggers.append({
                    'type': '27coins_low_1',
                    'description': '27币涨跌幅总和 -80% 至 -119%（轻度下跌）',
                    'value': total_change,
                    'level': 1,
                    'data': coins_data
                })
        
        # 条件3: 24h信号极值标记
        if escape_data.get('has_24h_peak') and not self.is_in_cooldown('24h_peak'):
            triggers.append({
                'type': '24h_peak',
                'description': '24h逃顶信号极值',
                'value': escape_data.get('max_24h_value', 0),
                'data': escape_data.get('peak_24h_info')
            })
        
        # 条件4: 1小时爆仓金额超过3000万美元
        self.log(f"🔍 检查爆仓条件: 金额={liquidation_data['amount_usd']:.2f}美元 ({liquidation_data['amount_wan']:.2f}万)")
        if liquidation_data['amount_usd'] > 30000000:
            if not self.is_in_cooldown('1h_liquidation_high'):
                self.log(f"🚨 触发爆仓极值! 金额={liquidation_data['amount_wan']:.2f}万美元")
                triggers.append({
                    'type': '1h_liquidation_high',
                    'description': '1小时爆仓金额超过3000万美元',
                    'value': liquidation_data['amount_usd'],
                    'value_wan': liquidation_data['amount_wan'],
                    'data': liquidation_data
                })
            else:
                self.log(f"⏳ 爆仓极值在冷却期内")
        
        if not triggers:
            return None
        
        # 更新触发时间（为所有触发的类型）
        for trigger in triggers:
            self.update_trigger_time(trigger['type'])
        
        return {
            'timestamp': int(time.time()),
            'datetime': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
            'triggers': triggers,
            'escape_data': escape_data,
            'coins_data': coins_data,
            'liquidation_data': liquidation_data,
            'total_change': total_change
        }
    
    def create_snapshot(self, extreme_event):
        """创建极值快照"""
        snapshot = {
            'snapshot_id': f"EXT_{int(time.time())}",
            'trigger_time': extreme_event['timestamp'],
            'trigger_datetime': extreme_event['datetime'],
            'triggers': extreme_event['triggers'],
            
            # 27个币的快照
            'coins_snapshot': {
                'timestamp': extreme_event['coins_data'].get('timestamp', int(time.time())),
                'datetime': extreme_event['coins_data'].get('collect_time', extreme_event['coins_data'].get('record_time', datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'))),
                'total_change': extreme_event['total_change'],
                'coins': []
            },
            
            # 逃顶信号快照
            'escape_snapshot': {
                'signal_2h_count': extreme_event['escape_data'].get('signal_2h_count', 0),
                'signal_24h_count': extreme_event['escape_data'].get('signal_24h_count', 0),
                'has_2h_peak': extreme_event['escape_data'].get('has_2h_peak', False),
                'has_24h_peak': extreme_event['escape_data'].get('has_24h_peak', False),
                'today_2h_max': extreme_event['escape_data'].get('today_2h_max', 0),
                'max_24h_value': extreme_event['escape_data'].get('max_24h_value', 0)
            },
            
            # 1小时爆仓快照
            'liquidation_snapshot': {
                'hour_1_amount_wan': extreme_event['liquidation_data'].get('amount_wan', 0),
                'hour_1_amount_usd': extreme_event['liquidation_data'].get('amount_usd', 0),
                'hour_24_amount': extreme_event['liquidation_data'].get('hour_24_amount', 0),
                'panic_index': extreme_event['liquidation_data'].get('panic_index', 0),
                'timestamp': extreme_event['liquidation_data'].get('timestamp', 0),
                'datetime': extreme_event['liquidation_data'].get('datetime', '')
            },
            
            # 追踪记录（初始为空，后续更新）
            'tracking': {
                '1h': None,
                '3h': None,
                '6h': None,
                '12h': None,
                '24h': None
            },
            
            # 状态
            'status': 'active',  # active: 追踪中, completed: 已完成
            'created_at': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 填充27个币的详细数据
        if 'day_changes' in extreme_event['coins_data']:
            for symbol, coin_info in extreme_event['coins_data']['day_changes'].items():
                if isinstance(coin_info, dict):
                    # 新格式：包含价格信息
                    snapshot['coins_snapshot']['coins'].append({
                        'symbol': symbol,
                        'current_price': coin_info.get('current_price', 0),
                        'base_price': coin_info.get('base_price', 0),
                        'day_change_percent': coin_info.get('change_pct', 0)
                    })
                else:
                    # 旧格式：只有涨跌幅
                    snapshot['coins_snapshot']['coins'].append({
                        'symbol': symbol,
                        'day_change_percent': coin_info
                    })
        
        return snapshot
    
    def save_snapshot(self, snapshot):
        """保存快照到JSONL文件"""
        try:
            with open(SNAPSHOTS_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(snapshot, ensure_ascii=False) + '\n')
            
            self.log(f"✅ 快照已保存: {snapshot['snapshot_id']}")
            return True
            
        except Exception as e:
            self.log(f"❌ 保存快照失败: {e}")
            return False
    
    def load_active_snapshots(self):
        """加载所有活跃的快照（追踪中）"""
        if not SNAPSHOTS_FILE.exists():
            return []
        
        active_snapshots = []
        try:
            with open(SNAPSHOTS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        snapshot = json.loads(line)
                        if snapshot.get('status') == 'active':
                            active_snapshots.append(snapshot)
            
            return active_snapshots
            
        except Exception as e:
            self.log(f"❌ 加载活跃快照失败: {e}")
            return []
    
    def update_tracking(self, snapshot_id, period, coins_data):
        """更新追踪数据"""
        try:
            # 读取所有快照
            snapshots = []
            with open(SNAPSHOTS_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        snapshots.append(json.loads(line))
            
            # 找到对应的快照并更新
            updated = False
            for snapshot in snapshots:
                if snapshot['snapshot_id'] == snapshot_id:
                    # 计算价格变化
                    tracking_data = {
                        'timestamp': int(time.time()),
                        'datetime': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S'),
                        'period': period,
                        'total_change': self.calculate_total_change(coins_data),
                        'coins': []
                    }
                    
                    # 计算每个币的价格变化
                    original_coins = {c['symbol']: c for c in snapshot['coins_snapshot']['coins']}
                    
                    if 'coin_changes' in coins_data:
                        for coin in coins_data['coin_changes']:
                            symbol = coin.get('symbol', '')
                            if symbol in original_coins:
                                original_price = original_coins[symbol]['price']
                                current_price = coin.get('price', 0)
                                price_change = ((current_price - original_price) / original_price * 100) if original_price > 0 else 0
                                
                                tracking_data['coins'].append({
                                    'symbol': symbol,
                                    'name': coin.get('name', ''),
                                    'original_price': original_price,
                                    'current_price': current_price,
                                    'price_change_percent': round(price_change, 2),
                                    'original_day_change': original_coins[symbol]['day_change_percent'],
                                    'current_day_change': coin.get('day_change_percent', 0)
                                })
                    
                    # 更新追踪数据
                    snapshot['tracking'][period] = tracking_data
                    
                    # 检查是否所有追踪都完成
                    all_completed = all(snapshot['tracking'][p] is not None for p in ['1h', '3h', '6h', '12h', '24h'])
                    if all_completed:
                        snapshot['status'] = 'completed'
                        snapshot['completed_at'] = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
                    
                    updated = True
                    break
            
            if updated:
                # 重写文件
                with open(SNAPSHOTS_FILE, 'w', encoding='utf-8') as f:
                    for snapshot in snapshots:
                        f.write(json.dumps(snapshot, ensure_ascii=False) + '\n')
                
                self.log(f"✅ 追踪数据已更新: {snapshot_id} - {period}")
                return True
            else:
                self.log(f"⚠️ 未找到快照: {snapshot_id}")
                return False
                
        except Exception as e:
            self.log(f"❌ 更新追踪数据失败: {e}")
            return False
    
    def check_and_update_tracking(self):
        """检查并更新所有活跃快照的追踪数据"""
        active_snapshots = self.load_active_snapshots()
        
        if not active_snapshots:
            self.log("ℹ️ 没有需要追踪的快照")
            return
        
        self.log(f"📊 发现 {len(active_snapshots)} 个活跃快照需要追踪")
        
        current_time = int(time.time())
        
        for snapshot in active_snapshots:
            trigger_time = snapshot['trigger_time']
            snapshot_id = snapshot['snapshot_id']
            
            # 计算时间差（小时）
            hours_passed = (current_time - trigger_time) / 3600
            
            # 获取最新的27币数据
            coins_data = self.get_27_coins_data()
            if not coins_data:
                continue
            
            # 检查需要更新哪些追踪点
            tracking_periods = [
                ('1h', 1),
                ('3h', 3),
                ('6h', 6),
                ('12h', 12),
                ('24h', 24)
            ]
            
            for period, hours in tracking_periods:
                # 如果已经记录过，跳过
                if snapshot['tracking'][period] is not None:
                    continue
                
                # 如果时间已到，记录追踪数据
                if hours_passed >= hours:
                    self.update_tracking(snapshot_id, period, coins_data)
    
    def run_once(self):
        """执行一次检查"""
        self.log("🔍 开始检查极值条件...")
        
        # 检查是否满足极值条件
        extreme_event = self.check_extreme_conditions()
        
        if extreme_event:
            self.log(f"🚨 检测到极值事件! 触发器数量: {len(extreme_event['triggers'])}")
            
            # 创建快照
            snapshot = self.create_snapshot(extreme_event)
            
            # 保存快照
            if self.save_snapshot(snapshot):
                # 发送Telegram通知
                self.send_telegram_notification(snapshot['snapshot_id'], extreme_event)
                
                # 日志输出
                trigger_desc = ', '.join([t['description'] for t in extreme_event['triggers']])
                self.log(f"📸 已创建快照: {snapshot['snapshot_id']}")
                self.log(f"   触发条件: {trigger_desc}")
                self.log(f"   27币总涨跌: {extreme_event['total_change']:.2f}%")
        else:
            self.log("✅ 当前无极值事件")
        
        # 更新活跃快照的追踪数据
        self.check_and_update_tracking()
        
        self.log("✅ 检查完成")
    
    def run_continuous(self, interval_minutes=10):
        """持续运行（每N分钟检查一次）"""
        self.log(f"🚀 开始持续监控 (每{interval_minutes}分钟检查一次)")
        
        while True:
            try:
                self.run_once()
                
                # 等待下一次检查
                self.log(f"⏳ 等待 {interval_minutes} 分钟后再次检查...")
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                self.log("⚠️ 收到中断信号，停止监控")
                break
            except Exception as e:
                self.log(f"❌ 运行异常: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)  # 出错后等待1分钟

def main():
    """主函数"""
    tracker = ExtremeValueTracker()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--once':
        # 单次运行模式
        tracker.run_once()
    else:
        # 持续运行模式
        interval = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        tracker.run_continuous(interval_minutes=interval)

if __name__ == '__main__':
    main()
