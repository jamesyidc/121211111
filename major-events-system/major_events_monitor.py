#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重大事件监控系统
监控和识别关键的交易信号事件
"""

import json
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MajorEventsMonitor')

class MajorEventsMonitor:
    """重大事件监控器"""
    
    def __init__(self, db_path='/home/user/webapp/coin_price_data.db'):
        self.db_path = db_path
        self.data_dir = Path(__file__).parent / 'data'
        self.data_dir.mkdir(exist_ok=True)
        
        # 事件历史记录文件
        self.events_file = self.data_dir / 'major_events.jsonl'
        
        # 状态持久化文件
        self.state_file = self.data_dir / 'monitor_state.json'
        
        # 27个交易对列表
        self.symbols = [
            'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP', 'BNB-USDT-SWAP',
            'SOL-USDT-SWAP', 'DOGE-USDT-SWAP', 'SUI-USDT-SWAP', 'TRX-USDT-SWAP',
            'LINK-USDT-SWAP', 'DOT-USDT-SWAP', 'UNI-USDT-SWAP', 'LTC-USDT-SWAP',
            'BCH-USDT-SWAP', 'NEAR-USDT-SWAP', 'AAVE-USDT-SWAP', 'APT-USDT-SWAP',
            'FIL-USDT-SWAP', 'TON-USDT-SWAP', 'XLM-USDT-SWAP', 'HBAR-USDT-SWAP',
            'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'CRV-USDT-SWAP', 'CRO-USDT-SWAP',
            'CFX-USDT-SWAP', 'TAO-USDT-SWAP', 'AVAX-USDT-SWAP'
        ]
        
        # 事件状态追踪
        self.event_states = {
            'top_signal_120': None,  # 记录120见顶信号的时间
            'liquidation_high': None,  # 记录爆仓金额新高的时间
            'liquidation_value': 0,  # 当前爆仓金额
            'profit_marks_history': [],  # 多空盈利标记历史
        }
        
        # 加载持久化状态
        self.load_state()
        
        logger.info("重大事件监控系统初始化完成")
    
    def get_db_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def load_state(self):
        """从文件加载状态"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    saved_state = json.load(f)
                    
                    # 恢复时间类型的字段
                    for key in ['top_signal_120', 'liquidation_high', 'event3_triggered_time', 
                                'event3_first_high_time', 'event4_triggered_time', 'event4_start_time']:
                        if key in saved_state and saved_state[key]:
                            saved_state[key] = datetime.fromisoformat(saved_state[key])
                    
                    # 恢复profit_marks_history中的时间
                    if 'profit_marks_history' in saved_state:
                        for mark in saved_state['profit_marks_history']:
                            if 'time' in mark and mark['time']:
                                mark['time'] = datetime.fromisoformat(mark['time'])
                    
                    self.event_states.update(saved_state)
                    logger.info(f"✅ 已加载持久化状态: {len(saved_state)} 个字段")
            else:
                logger.info("📝 首次运行，创建新状态")
        except Exception as e:
            logger.error(f"加载状态失败: {e}")
    
    def save_state(self):
        """保存状态到文件"""
        try:
            # 序列化状态（datetime转为ISO格式）
            serializable_state = {}
            for key, value in self.event_states.items():
                if isinstance(value, datetime):
                    serializable_state[key] = value.isoformat()
                elif isinstance(value, list):
                    # 处理列表中的datetime
                    serializable_list = []
                    for item in value:
                        if isinstance(item, dict):
                            serialized_item = {}
                            for k, v in item.items():
                                if isinstance(v, datetime):
                                    serialized_item[k] = v.isoformat()
                                else:
                                    serialized_item[k] = v
                            serializable_list.append(serialized_item)
                        else:
                            serializable_list.append(item)
                    serializable_state[key] = serializable_list
                else:
                    serializable_state[key] = value
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_state, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存状态失败: {e}")
    
    def get_2h_top_signal_count(self):
        """
        获取2h见顶信号数量（从JSONL读取）
        返回: int, 见顶信号的币种数量
        """
        try:
            jsonl_file = self.data_dir / 'sar_slope_data.jsonl'
            if not jsonl_file.exists():
                logger.warning(f"SAR数据文件不存在: {jsonl_file}")
                return 0
            
            # 读取最后一行（最新数据）
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if not lines:
                    return 0
                
                last_line = lines[-1]
                data = json.loads(last_line)
                count = data.get('count', 0)
                
                logger.info(f"2h见顶信号数量: {count}")
                return count
            
        except Exception as e:
            logger.error(f"获取2h见顶信号失败: {e}")
            return 0
    
    def get_27_coins_change_sum(self):
        """
        获取27个币的涨跌幅总和（从JSONL读取）
        返回: float, 涨跌幅总和（百分比）
        """
        try:
            jsonl_file = self.data_dir / 'coin_prices.jsonl'
            if not jsonl_file.exists():
                logger.warning(f"币种价格数据文件不存在: {jsonl_file}")
                return 0
            
            # 读取最后一行（最新数据）
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if not lines:
                    return 0
                
                last_line = lines[-1]
                data = json.loads(last_line)
                total = data.get('total_change', 0)
                
                logger.info(f"27个币涨跌幅总和: {total:.2f}%")
                return total
            
        except Exception as e:
            logger.error(f"获取涨跌幅总和失败: {e}")
            return 0
    
    def get_1h_liquidation_amount(self):
        """
        获取1h爆仓金额（从API读取）
        返回: float, 爆仓金额（万美元）
        """
        try:
            # 从Flask API读取恐慌指数数据
            import requests
            
            response = requests.get('http://localhost:5000/api/panic/latest', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    panic_data = data.get('data', {})
                    amount = panic_data.get('hour_1_amount', 0)
                    logger.info(f"1h爆仓金额（从API）: {amount:.2f}万美元")
                    return amount
            
            # API失败，尝试从JSONL读取
            jsonl_file = self.data_dir / 'liquidation_data.jsonl'
            if jsonl_file.exists():
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1]
                        data = json.loads(last_line)
                        amount = data.get('liquidation_amount', 0) / 10000  # 转换为万美元
                        logger.info(f"1h爆仓金额（从JSONL）: {amount:.2f}万美元")
                        return amount
            
            logger.warning("无法获取1h爆仓金额数据")
            return 0
            
        except Exception as e:
            logger.error(f"获取爆仓金额失败: {e}")
            return 0
    
    def check_event_1_high_intensity_top(self):
        """
        事件一：高强度见顶诱多
        - 2h见顶信号达到120
        - 10小时内出现第二次2h见顶信号 >= 10 且 < 120
        - 27个币涨跌幅相加为正
        - 操作提示：开空
        """
        current_count = self.get_2h_top_signal_count()
        
        # 第一阶段：检测到120见顶信号
        if current_count >= 120:
            if not self.event_states['top_signal_120']:
                self.event_states['top_signal_120'] = datetime.now()
                logger.info(f"🔴 检测到高强度见顶信号: {current_count}")
                self.save_event({
                    'event_type': 'high_intensity_top_phase1',
                    'signal_count': current_count,
                    'action': 'wait_for_confirmation',
                    'description': f'2h见顶信号达到{current_count}，等待10小时内的确认信号'
                })
            return None
        
        # 第二阶段：检测10小时内的第二次信号
        if self.event_states['top_signal_120']:
            time_diff = datetime.now() - self.event_states['top_signal_120']
            
            if time_diff <= timedelta(hours=10):
                # 检查是否满足第二次信号条件
                if 10 <= current_count < 120:
                    change_sum = self.get_27_coins_change_sum()
                    
                    if change_sum > 0:
                        # 满足所有条件，触发事件
                        event = {
                            'event_type': 'high_intensity_top_confirmed',
                            'event_id': 1,
                            'event_name': '高强度见顶诱多',
                            'phase1_count': 120,
                            'phase2_count': current_count,
                            'coins_change_sum': change_sum,
                            'time_between': str(time_diff),
                            'action': '开空',
                            'confidence': 'high',
                            'description': f'高强度见顶诱多确认：第一次{120}，第二次{current_count}，涨跌幅和{change_sum:.2f}%'
                        }
                        
                        logger.warning(f"🚨 事件一触发：高强度见顶诱多 - 开空！")
                        self.save_event(event)
                        self.event_states['top_signal_120'] = None
                        return event
            else:
                # 超过10小时，重置状态
                logger.info("高强度见顶信号超时（>10小时），重置状态")
                self.event_states['top_signal_120'] = None
        
        return None
    
    def check_event_2_normal_intensity_top(self):
        """
        事件二：一般强度见顶诱多
        - 2h见顶信号 >= 20 但 < 120
        - 10小时内出现第二次2h见顶信号且小于第一次的值
        - 操作提示：开空
        """
        current_count = self.get_2h_top_signal_count()
        
        # 检查是否满足第一次条件
        if 20 <= current_count < 120:
            if not self.event_states.get('normal_top_first'):
                # 记录第一次信号
                self.event_states['normal_top_first'] = {
                    'count': current_count,
                    'time': datetime.now()
                }
                logger.info(f"🟡 检测到一般强度见顶信号: {current_count}")
                self.save_event({
                    'event_type': 'normal_intensity_top_phase1',
                    'signal_count': current_count,
                    'action': 'wait_for_confirmation',
                    'description': f'2h见顶信号{current_count}，等待10小时内的确认信号'
                })
        
        # 检查第二次信号
        if self.event_states.get('normal_top_first'):
            first_signal = self.event_states['normal_top_first']
            time_diff = datetime.now() - first_signal['time']
            
            if time_diff <= timedelta(hours=10):
                # 检查是否满足第二次信号条件（小于第一次）
                if 0 < current_count < first_signal['count']:
                    event = {
                        'event_type': 'normal_intensity_top_confirmed',
                        'event_id': 2,
                        'event_name': '一般强度见顶诱多',
                        'first_count': first_signal['count'],
                        'second_count': current_count,
                        'time_between': str(time_diff),
                        'action': '开空',
                        'confidence': 'medium',
                        'description': f'一般强度见顶诱多确认：第一次{first_signal["count"]}，第二次{current_count}'
                    }
                    
                    logger.warning(f"🚨 事件二触发：一般强度见顶诱多 - 开空！")
                    self.save_event(event)
                    self.event_states['normal_top_first'] = None
                    return event
            else:
                # 超过10小时，重置状态
                logger.info("一般强度见顶信号超时（>10小时），重置状态")
                self.event_states['normal_top_first'] = None
        
        return None
    
    def check_event_3_strong_short_liquidation(self):
        """
        事件三：1h爆仓金额 >= 3000万强空头
        - 1h爆仓金额 >= 3000万
        - 持续10分钟以上创新高
        - 操作提示：开空
        
        逻辑修正：
        1. 当爆仓金额>=3000万时，开始记录
        2. 如果持续创新高，更新最高值和时间
        3. 当持续创新高时间>=10分钟时，触发事件
        4. 一旦触发后，设置冷却期，避免重复触发
        """
        current_amount = self.get_1h_liquidation_amount()
        now = datetime.now()
        
        # 初始化事件3的状态
        if 'event3_triggered_time' not in self.event_states:
            self.event_states['event3_triggered_time'] = None
        if 'event3_first_high_time' not in self.event_states:
            self.event_states['event3_first_high_time'] = None
        if 'event3_max_amount' not in self.event_states:
            self.event_states['event3_max_amount'] = 0
        
        # 冷却期检查（触发后1小时内不再触发）
        if self.event_states['event3_triggered_time']:
            time_since_trigger = now - self.event_states['event3_triggered_time']
            if time_since_trigger < timedelta(hours=1):
                logger.debug(f"事件3冷却中，距离上次触发: {time_since_trigger}")
                return None
        
        if current_amount >= 3000:
            # 检查是否创新高
            if current_amount > self.event_states['event3_max_amount']:
                self.event_states['event3_max_amount'] = current_amount
                
                # 第一次达到3000万以上
                if not self.event_states['event3_first_high_time']:
                    self.event_states['event3_first_high_time'] = now
                    logger.info(f"💰 首次检测到大额爆仓: {current_amount:.2f}万美元")
                else:
                    logger.info(f"💰 爆仓金额创新高: {current_amount:.2f}万美元")
            
            # 检查持续创新高的时间
            if self.event_states['event3_first_high_time']:
                duration = now - self.event_states['event3_first_high_time']
                duration_minutes = duration.total_seconds() / 60
                
                logger.info(f"⏱️  事件3监控中: 持续{duration_minutes:.2f}分钟, 最大{self.event_states['event3_max_amount']:.2f}万")
                
                # 持续10分钟以上创新高，触发事件
                if duration >= timedelta(minutes=10):
                    event = {
                        'event_type': 'strong_short_liquidation',
                        'event_id': 3,
                        'event_name': '强空头爆仓',
                        'liquidation_amount': current_amount,
                        'max_amount': self.event_states['event3_max_amount'],
                        'duration_minutes': int(duration.total_seconds() / 60),
                        'action': '开空',
                        'confidence': '高',
                        'description': f'强空头信号：1h爆仓金额达到{current_amount:.2f}万美元，持续创新高超过{int(duration.total_seconds()/60)}分钟'
                    }
                    
                    logger.warning(f"🚨 事件三触发：强空头爆仓 - 开空！爆仓金额: {current_amount:.2f}万美元")
                    self.save_event(event)
                    
                    # 设置触发时间和冷却
                    self.event_states['event3_triggered_time'] = now
                    self.event_states['event3_first_high_time'] = None
                    self.event_states['event3_max_amount'] = 0
                    
                    return event
        else:
            # 爆仓金额低于3000万
            # 【修改】如果之前有记录峰值，且持续时间>=10分钟，先触发事件再重置
            if self.event_states['event3_max_amount'] >= 3000 and self.event_states['event3_first_high_time']:
                duration = now - self.event_states['event3_first_high_time']
                duration_minutes = duration.total_seconds() / 60
                
                logger.info(f"⚠️  爆仓金额降至{current_amount:.2f}万美元，检查是否满足触发条件...")
                logger.info(f"⏱️  峰值监控时长: {duration_minutes:.2f}分钟, 历史最大值: {self.event_states['event3_max_amount']:.2f}万")
                
                # 如果持续时间>=10分钟，触发事件
                if duration >= timedelta(minutes=10):
                    event = {
                        'event_type': 'strong_short_liquidation',
                        'event_id': 3,
                        'event_name': '强空头爆仓',
                        'liquidation_amount': current_amount,
                        'max_amount': self.event_states['event3_max_amount'],
                        'duration_minutes': int(duration.total_seconds() / 60),
                        'action': '开空',
                        'confidence': '高',
                        'description': f'强空头信号：1h爆仓金额峰值{self.event_states["event3_max_amount"]:.2f}万美元，持续{int(duration.total_seconds()/60)}分钟后开始回落'
                    }
                    
                    logger.warning(f"🚨 事件三触发（回落触发）：强空头爆仓 - 开空！峰值: {self.event_states['event3_max_amount']:.2f}万美元")
                    self.save_event(event)
                    
                    # 设置触发时间和冷却
                    self.event_states['event3_triggered_time'] = now
                    self.event_states['event3_first_high_time'] = None
                    self.event_states['event3_max_amount'] = 0
                    
                    return event
                else:
                    logger.info(f"📉 爆仓金额回落但持续时间不足10分钟({duration_minutes:.2f}分钟)，不触发事件，重置状态")
                
                # 重置状态
                self.event_states['event3_first_high_time'] = None
                self.event_states['event3_max_amount'] = 0
        
        return None
    
    def check_event_4_weak_short_liquidation(self):
        """
        事件四：1h爆仓金额 >= 3000万弱空头
        - 1h爆仓金额 >= 3000万
        - 10分钟内未创新高
        - 操作提示：开空（谨慎）
        
        逻辑修正：
        1. 当爆仓金额>=3000万时，记录初始值和时间
        2. 如果10分钟后，爆仓金额没有显著增长（<5%），触发弱空头事件
        3. 如果创新高超过5%，则重置状态
        """
        current_amount = self.get_1h_liquidation_amount()
        now = datetime.now()
        
        # 初始化事件4的状态
        if 'event4_triggered_time' not in self.event_states:
            self.event_states['event4_triggered_time'] = None
        if 'event4_start_time' not in self.event_states:
            self.event_states['event4_start_time'] = None
        if 'event4_start_amount' not in self.event_states:
            self.event_states['event4_start_amount'] = 0
        if 'event4_max_amount' not in self.event_states:
            self.event_states['event4_max_amount'] = 0
        
        # 冷却期检查（触发后1小时内不再触发）
        if self.event_states['event4_triggered_time']:
            time_since_trigger = now - self.event_states['event4_triggered_time']
            if time_since_trigger < timedelta(hours=1):
                logger.debug(f"事件4冷却中，距离上次触发: {time_since_trigger}")
                return None
        
        if current_amount >= 3000:
            # 第一次检测到>=3000万
            if not self.event_states['event4_start_time']:
                self.event_states['event4_start_time'] = now
                self.event_states['event4_start_amount'] = current_amount
                self.event_states['event4_max_amount'] = current_amount
                logger.info(f"💰 开始监控弱空头：初始爆仓金额 {current_amount:.2f}万美元")
                return None
            
            # 更新最大值
            if current_amount > self.event_states['event4_max_amount']:
                self.event_states['event4_max_amount'] = current_amount
            
            # 检查是否满足触发条件
            duration = now - self.event_states['event4_start_time']
            duration_minutes = duration.total_seconds() / 60
            increase_pct = (self.event_states['event4_max_amount'] - self.event_states['event4_start_amount']) / self.event_states['event4_start_amount']
            
            logger.info(f"⏱️  事件4监控中: 持续{duration_minutes:.2f}分钟, 增幅{increase_pct*100:.2f}%")
            
            if duration >= timedelta(minutes=10):
                # 10分钟内增幅小于5%，触发弱空头
                if increase_pct < 0.05:
                    event = {
                        'event_type': 'weak_short_liquidation',
                        'event_id': 4,
                        'event_name': '弱空头爆仓',
                        'liquidation_amount': current_amount,
                        'start_amount': self.event_states['event4_start_amount'],
                        'max_amount': self.event_states['event4_max_amount'],
                        'increase_pct': f'{increase_pct*100:.2f}%',
                        'duration_minutes': int(duration.total_seconds() / 60),
                        'action': '开空（谨慎）',
                        'confidence': '中',
                        'description': f'弱空头信号：1h爆仓金额{current_amount:.2f}万美元，10分钟内增幅仅{increase_pct*100:.2f}%，未创显著新高'
                    }
                    
                    logger.warning(f"🚨 事件四触发：弱空头爆仓 - 开空（谨慎）！")
                    self.save_event(event)
                    
                    # 设置触发时间和冷却
                    self.event_states['event4_triggered_time'] = now
                    self.event_states['event4_start_time'] = None
                    self.event_states['event4_start_amount'] = 0
                    self.event_states['event4_max_amount'] = 0
                    
                    return event
                else:
                    # 增幅>=5%，说明在创新高，重置为强空头监控
                    logger.info(f"爆仓金额增幅{increase_pct*100:.2f}%>=5%，转为强空头模式")
                    self.event_states['event4_start_time'] = None
                    self.event_states['event4_start_amount'] = 0
                    self.event_states['event4_max_amount'] = 0
        else:
            # 爆仓金额低于3000万
            # 【修改】如果之前有记录，且持续时间>=10分钟，先检查是否触发事件再重置
            if self.event_states['event4_start_amount'] >= 3000 and self.event_states['event4_start_time']:
                duration = now - self.event_states['event4_start_time']
                duration_minutes = duration.total_seconds() / 60
                increase_pct = (self.event_states['event4_max_amount'] - self.event_states['event4_start_amount']) / self.event_states['event4_start_amount']
                
                logger.info(f"⚠️  爆仓金额降至{current_amount:.2f}万美元，检查事件4是否满足触发条件...")
                logger.info(f"⏱️  监控时长: {duration_minutes:.2f}分钟, 增幅: {increase_pct*100:.2f}%")
                
                # 如果持续时间>=10分钟且增幅<5%，触发弱空头事件
                if duration >= timedelta(minutes=10) and increase_pct < 0.05:
                    event = {
                        'event_type': 'weak_short_liquidation',
                        'event_id': 4,
                        'event_name': '弱空头爆仓',
                        'liquidation_amount': current_amount,
                        'start_amount': self.event_states['event4_start_amount'],
                        'max_amount': self.event_states['event4_max_amount'],
                        'increase_pct': f'{increase_pct*100:.2f}%',
                        'duration_minutes': int(duration.total_seconds() / 60),
                        'action': '开空（谨慎）',
                        'confidence': '中',
                        'description': f'弱空头信号：1h爆仓金额峰值{self.event_states["event4_max_amount"]:.2f}万美元，{int(duration.total_seconds()/60)}分钟内增幅仅{increase_pct*100:.2f}%后回落'
                    }
                    
                    logger.warning(f"🚨 事件四触发（回落触发）：弱空头爆仓 - 开空（谨慎）！")
                    self.save_event(event)
                    
                    # 设置触发时间和冷却
                    self.event_states['event4_triggered_time'] = now
                    self.event_states['event4_start_time'] = None
                    self.event_states['event4_start_amount'] = 0
                    self.event_states['event4_max_amount'] = 0
                    
                    return event
                else:
                    logger.info(f"📉 爆仓金额回落但不满足触发条件（时长{duration_minutes:.2f}分钟，增幅{increase_pct*100:.2f}%），重置状态")
                
                # 重置状态
                self.event_states['event4_start_time'] = None
                self.event_states['event4_start_amount'] = 0
                self.event_states['event4_max_amount'] = 0
        
        return None
    
    def get_anchor_profit_stats(self):
        """
        获取锚定系统多空盈利统计（从JSONL文件读取）
        返回: dict, 包含 short_profit_120 和 short_loss 的数量
        """
        try:
            profit_stats_file = self.data_dir / 'anchor_profit_stats.jsonl'
            
            if not profit_stats_file.exists():
                logger.warning("锚定系统盈利统计文件不存在，请先启动数据收集器")
                return None
            
            # 读取最后一行（最新数据）
            with open(profit_stats_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                logger.warning("锚定系统盈利统计文件为空")
                return None
            
            # 解析最新记录
            last_line = lines[-1].strip()
            record = json.loads(last_line)
            
            stats = record.get('stats', {})
            short_stats = stats.get('short', {})
            
            short_profit_120 = short_stats.get('gte_120', 0)
            short_loss = short_stats.get('loss', 0)
            datetime_str = record.get('datetime', '')
            
            logger.info(f"锚定系统盈利统计 - 时间: {datetime_str}, " +
                       f"空单盈利≥120%: {short_profit_120}, 空单亏损: {short_loss}")
            
            return {
                'datetime': datetime_str,
                'short_profit_120': short_profit_120,
                'short_loss': short_loss,
                'stats': stats,
                'timestamp': record.get('timestamp', 0)
            }
            
        except Exception as e:
            logger.error(f"获取锚定系统盈利统计失败: {e}")
            return None
    
    def check_event_5_profit_trend_reversal(self):
        """
        事件五：多空盈利趋势反转
        - 空单亏损 >= 3 标记为绿色
        - 空单盈利≥120%数量 >= 3 标记为红色
        - 如果最近一次标记是红色，检测上一个是绿色，触发多空转换
        - 如果最近一次标记是绿色，检测上一个是红色，触发多空转换
        - 操作提示：多空转换
        """
        profit_stats = self.get_anchor_profit_stats()
        
        if not profit_stats:
            return None
        
        short_profit_120 = profit_stats['short_profit_120']
        short_loss = profit_stats['short_loss']
        datetime_str = profit_stats['datetime']
        
        # 确定当前标记类型
        current_mark = None
        if short_loss >= 3:
            current_mark = 'green'  # 绿色：空单亏损
            logger.info(f"🟢 空单亏损≥3: {short_loss}个")
        elif short_profit_120 >= 3:
            current_mark = 'red'    # 红色：空单盈利
            logger.info(f"🔴 空单盈利≥120%: {short_profit_120}个")
        
        # 如果有标记，添加到历史记录
        if current_mark:
            history = self.event_states['profit_marks_history']
            
            # 检查是否是新的标记（不同的时间点）
            if not history or history[-1]['datetime'] != datetime_str:
                mark_data = {
                    'datetime': datetime_str,
                    'mark': current_mark,
                    'short_profit_120': short_profit_120,
                    'short_loss': short_loss,
                    'time': datetime.now()
                }
                history.append(mark_data)
                
                # 只保留最近10个标记
                if len(history) > 10:
                    history.pop(0)
                
                logger.info(f"📍 添加新标记: {current_mark} at {datetime_str}")
                
                # 检查是否触发趋势反转
                if len(history) >= 2:
                    last_mark = history[-1]['mark']
                    previous_mark = history[-2]['mark']
                    
                    # 检查趋势反转
                    if last_mark != previous_mark:
                        # 从红转绿：多头转空头
                        if last_mark == 'green' and previous_mark == 'red':
                            event = {
                                'event_type': 'profit_trend_reversal',
                                'event_id': 5,
                                'event_name': '多空盈利趋势反转',
                                'reversal_type': 'red_to_green',
                                'previous_mark': {
                                    'color': 'red',
                                    'datetime': history[-2]['datetime'],
                                    'short_profit_120': history[-2]['short_profit_120']
                                },
                                'current_mark': {
                                    'color': 'green',
                                    'datetime': history[-1]['datetime'],
                                    'short_loss': history[-1]['short_loss']
                                },
                                'action': '多空转换 (空头趋势)',
                                'confidence': 'medium',
                                'description': f'多空转换：红色({history[-2]["short_profit_120"]}个盈利) → 绿色({history[-1]["short_loss"]}个亏损)，市场从强势转弱势'
                            }
                            
                            logger.warning(f"🚨 事件五触发：多空趋势反转 (红→绿) - 空头趋势！")
                            self.save_event(event)
                            return event
                        
                        # 从绿转红：空头转多头
                        elif last_mark == 'red' and previous_mark == 'green':
                            event = {
                                'event_type': 'profit_trend_reversal',
                                'event_id': 5,
                                'event_name': '多空盈利趋势反转',
                                'reversal_type': 'green_to_red',
                                'previous_mark': {
                                    'color': 'green',
                                    'datetime': history[-2]['datetime'],
                                    'short_loss': history[-2]['short_loss']
                                },
                                'current_mark': {
                                    'color': 'red',
                                    'datetime': history[-1]['datetime'],
                                    'short_profit_120': history[-1]['short_profit_120']
                                },
                                'action': '多空转换 (多头趋势)',
                                'confidence': 'medium',
                                'description': f'多空转换：绿色({history[-2]["short_loss"]}个亏损) → 红色({history[-1]["short_profit_120"]}个盈利)，市场从弱势转强势'
                            }
                            
                            logger.warning(f"🚨 事件五触发：多空趋势反转 (绿→红) - 多头趋势！")
                            self.save_event(event)
                            return event
        
        return None
    
    def save_event(self, event):
        """保存事件到JSONL文件"""
        event['timestamp'] = datetime.now().isoformat()
        
        with open(self.events_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')
        
        logger.info(f"事件已保存: {event.get('event_type', 'unknown')}")
    
    def get_recent_events(self, hours=24):
        """获取最近的事件"""
        if not self.events_file.exists():
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        events = []
        
        with open(self.events_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    event_time = datetime.fromisoformat(event['timestamp'])
                    
                    if event_time >= cutoff_time:
                        events.append(event)
                except:
                    continue
        
        return events
    
    def monitor_cycle(self):
        """执行一次监控周期"""
        logger.info("=" * 60)
        logger.info("开始监控周期")
        
        try:
            # 检查所有事件
            event1 = self.check_event_1_high_intensity_top()
            event2 = self.check_event_2_normal_intensity_top()
            event3 = self.check_event_3_strong_short_liquidation()
            event4 = self.check_event_4_weak_short_liquidation()
            event5 = self.check_event_5_profit_trend_reversal()
            
            # 收集触发的事件
            triggered_events = [e for e in [event1, event2, event3, event4, event5] if e]
            
            if triggered_events:
                logger.warning(f"本周期触发 {len(triggered_events)} 个事件")
                for event in triggered_events:
                    logger.warning(f"  - {event['event_name']}: {event['action']}")
            else:
                logger.info("本周期无事件触发")
            
            # 保存状态到文件
            self.save_state()
            
            return triggered_events
            
        except Exception as e:
            logger.error(f"监控周期执行失败: {e}", exc_info=True)
            return []
    
    def run(self, interval=60):
        """
        运行监控系统
        interval: 监控间隔（秒）
        """
        logger.info(f"重大事件监控系统启动，监控间隔: {interval}秒")
        
        try:
            while True:
                self.monitor_cycle()
                time.sleep(interval)
                
        except KeyboardInterrupt:
            logger.info("监控系统停止")
        except Exception as e:
            logger.error(f"监控系统异常: {e}", exc_info=True)


if __name__ == '__main__':
    monitor = MajorEventsMonitor()
    monitor.run(interval=60)  # 每60秒检查一次
