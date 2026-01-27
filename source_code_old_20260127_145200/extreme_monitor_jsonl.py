#!/usr/bin/env python3
"""
锚点系统实时极值监控（JSONL版本）
功能：
1. 每分钟检查主账号各币种的当前盈亏
2. 与历史极值比较，如果创新高/新低则更新
3. 记录时间戳并发送Telegram通知
4. 所有数据读写完全使用JSONL，不依赖数据库
"""

import json
import os
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
import pytz
from pathlib import Path

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# JSONL文件路径
EXTREME_JSONL_PATH = 'data/extreme_jsonl/extreme_real.jsonl'
OKEX_API_BASE = 'https://www.okx.com'

# Telegram配置（从配置文件加载）
TELEGRAM_CONFIG_PATH = 'configs/telegram_config.json'


class ExtremeMonitorJSONL:
    """基于JSONL的极值监控器"""
    
    def __init__(self):
        self.jsonl_path = EXTREME_JSONL_PATH
        self.data_dir = os.path.dirname(self.jsonl_path)
        
        # 确保目录存在
        os.makedirs(self.data_dir, exist_ok=True)
        
        # 确保JSONL文件存在
        if not os.path.exists(self.jsonl_path):
            open(self.jsonl_path, 'w').close()
        
        # 加载Telegram配置
        self.telegram_config = self._load_telegram_config()
        
        self.log("🚀 极值监控器启动（JSONL模式）")
    
    def log(self, message: str):
        """打印日志"""
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}", flush=True)
    
    def _load_telegram_config(self) -> Dict:
        """加载Telegram配置"""
        try:
            if os.path.exists(TELEGRAM_CONFIG_PATH):
                with open(TELEGRAM_CONFIG_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                self.log(f"⚠️ Telegram配置文件不存在: {TELEGRAM_CONFIG_PATH}")
                return {}
        except Exception as e:
            self.log(f"❌ 加载Telegram配置失败: {e}")
            return {}
    
    def read_all_extremes(self) -> List[Dict]:
        """从JSONL读取所有极值记录"""
        records = []
        try:
            with open(self.jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            records.append(record)
                        except json.JSONDecodeError as e:
                            self.log(f"⚠️ 解析JSONL行失败: {e}")
        except FileNotFoundError:
            self.log(f"⚠️ JSONL文件不存在: {self.jsonl_path}")
        except Exception as e:
            self.log(f"❌ 读取JSONL失败: {e}")
        
        return records
    
    def write_all_extremes(self, records: List[Dict]):
        """将所有极值记录写入JSONL"""
        try:
            # 先备份
            if os.path.exists(self.jsonl_path) and os.path.getsize(self.jsonl_path) > 0:
                backup_path = f"{self.jsonl_path}.backup_{datetime.now(BEIJING_TZ).strftime('%Y%m%d_%H%M%S')}"
                with open(self.jsonl_path, 'r') as src, open(backup_path, 'w') as dst:
                    dst.write(src.read())
                self.log(f"💾 已备份到: {backup_path}")
            
            # 写入新数据
            with open(self.jsonl_path, 'w', encoding='utf-8') as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            
            self.log(f"✅ 已写入 {len(records)} 条记录到JSONL")
        except Exception as e:
            self.log(f"❌ 写入JSONL失败: {e}")
    
    def get_extreme(self, inst_id: str, pos_side: str, record_type: str) -> Optional[Dict]:
        """获取指定币种、方向、类型的极值记录"""
        records = self.read_all_extremes()
        
        for record in reversed(records):  # 从最新往旧找
            if (record.get('inst_id') == inst_id and 
                record.get('pos_side') == pos_side and 
                record.get('record_type') == record_type):
                return record
        
        return None
    
    def update_extreme(self, inst_id: str, pos_side: str, record_type: str, 
                      new_profit_rate: float, current_data: Dict) -> bool:
        """更新极值记录"""
        records = self.read_all_extremes()
        
        # 查找现有记录的索引
        existing_index = -1
        for i, record in enumerate(records):
            if (record.get('inst_id') == inst_id and 
                record.get('pos_side') == pos_side and 
                record.get('record_type') == record_type):
                existing_index = i
                break
        
        # 创建新记录
        now = datetime.now(BEIJING_TZ)
        new_record = {
            'inst_id': inst_id,
            'pos_side': pos_side,
            'record_type': record_type,
            'profit_rate': new_profit_rate,
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'pos_size': current_data.get('pos', 0),
            'avg_price': current_data.get('avgPx', 0),
            'mark_price': current_data.get('markPx', 0),
            'upl': current_data.get('upl', 0),
            'margin': current_data.get('margin', 0),
            'leverage': current_data.get('lever', 10),
            'created_at': now.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': now.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if existing_index >= 0:
            # 更新现有记录
            records[existing_index] = new_record
            self.log(f"🔄 更新极值: {inst_id} {pos_side} {record_type} = {new_profit_rate:.2f}%")
        else:
            # 添加新记录
            records.append(new_record)
            self.log(f"➕ 新增极值: {inst_id} {pos_side} {record_type} = {new_profit_rate:.2f}%")
        
        # 写回JSONL
        self.write_all_extremes(records)
        return True
    
    def get_main_account_positions(self) -> List[Dict]:
        """获取主账号当前持仓（从OKEx API）"""
        try:
            # 导入anchor_system的API调用函数
            import sys
            sys.path.insert(0, '/home/user/webapp/source_code')
            from anchor_system import get_positions_from_okex
            
            positions = get_positions_from_okex()
            return positions if positions else []
        except Exception as e:
            self.log(f"❌ 获取主账号持仓失败: {e}")
            return []
    
    def calculate_profit_rate(self, position: Dict) -> float:
        """计算当前盈亏率"""
        try:
            upl = float(position.get('upl', 0))  # 未实现盈亏
            margin = float(position.get('margin', 1))  # 保证金
            
            if margin > 0:
                profit_rate = (upl / margin) * 100
                return profit_rate
            return 0.0
        except Exception as e:
            self.log(f"❌ 计算盈亏率失败: {e}")
            return 0.0
    
    def write_to_anchor_monitors(self, position: Dict, record_type: str, profit_rate: float):
        """将极值变化写入anchor_monitors表（历史监控记录）"""
        try:
            import sqlite3
            
            db_path = '/home/user/webapp/databases/anchor_system.db'
            conn = sqlite3.connect(db_path, timeout=10.0)
            cursor = conn.cursor()
            
            now = datetime.now(BEIJING_TZ)
            timestamp = now.strftime('%Y-%m-%d %H:%M:%S')
            
            # 设置alert_type为extreme类型
            alert_type = f"extreme_{record_type}"  # extreme_max_profit 或 extreme_max_loss
            
            # 插入记录
            cursor.execute('''
                INSERT INTO anchor_monitors (
                    timestamp, inst_id, pos_side, pos_size, avg_price, mark_price,
                    upl, upl_ratio, margin, leverage, profit_rate, alert_type, alert_sent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp,
                position.get('instId', ''),
                position.get('posSide', 'long'),
                abs(float(position.get('pos', 0))),
                float(position.get('avgPx', 0)),
                float(position.get('markPx', 0)),
                float(position.get('upl', 0)),
                float(position.get('uplRatio', 0)),
                float(position.get('margin', 0)),
                float(position.get('lever', 10)),
                profit_rate,
                alert_type,
                0  # alert_sent默认0
            ))
            
            conn.commit()
            conn.close()
            
            self.log(f"✅ 极值变化已写入anchor_monitors表: {position.get('instId')} {position.get('posSide')} {record_type}")
        except Exception as e:
            self.log(f"❌ 写入anchor_monitors失败: {e}")
            import traceback
            self.log(traceback.format_exc())
    
    def check_and_update_extreme(self, position: Dict) -> Optional[Dict]:
        """检查并更新极值
        
        Returns:
            如果更新了极值，返回更新信息字典，否则返回None
        """
        inst_id = position.get('instId')
        pos_side = position.get('posSide', 'long')
        current_profit_rate = self.calculate_profit_rate(position)
        
        if not inst_id:
            return None
        
        # 获取当前极值
        max_profit_record = self.get_extreme(inst_id, pos_side, 'max_profit')
        max_loss_record = self.get_extreme(inst_id, pos_side, 'max_loss')
        
        current_max_profit = max_profit_record['profit_rate'] if max_profit_record else None
        current_max_loss = max_loss_record['profit_rate'] if max_loss_record else None
        
        update_info = None
        
        # 检查是否创新高（最大盈利）
        # 条件：当前盈利率 > 0 且 (没有历史记录 或 大于历史最大盈利)
        if current_profit_rate > 0:
            if current_max_profit is None or current_profit_rate > current_max_profit:
                self.update_extreme(inst_id, pos_side, 'max_profit', current_profit_rate, position)
                # 写入anchor_monitors表
                self.write_to_anchor_monitors(position, 'max_profit', current_profit_rate)
                
                update_info = {
                    'type': 'new_high',
                    'inst_id': inst_id,
                    'pos_side': pos_side,
                    'old_value': current_max_profit if current_max_profit is not None else 0,
                    'new_value': current_profit_rate,
                    'position': position
                }
                old_str = f"{current_max_profit:.2f}%" if current_max_profit is not None else "无记录"
                self.log(f"🎉 {inst_id} {pos_side} 创新高: {old_str} → {current_profit_rate:.2f}%")
        
        # 检查是否创新低（最大亏损）
        # 条件：当前盈利率 < 0 且 (没有历史记录 或 小于历史最大亏损)
        elif current_profit_rate < 0:
            if current_max_loss is None or current_profit_rate < current_max_loss:
                self.update_extreme(inst_id, pos_side, 'max_loss', current_profit_rate, position)
                # 写入anchor_monitors表
                self.write_to_anchor_monitors(position, 'max_loss', current_profit_rate)
                
                update_info = {
                    'type': 'new_low',
                    'inst_id': inst_id,
                    'pos_side': pos_side,
                    'old_value': current_max_loss if current_max_loss is not None else 0,
                    'new_value': current_profit_rate,
                    'position': position
                }
                old_str = f"{current_max_loss:.2f}%" if current_max_loss is not None else "无记录"
                self.log(f"⚠️ {inst_id} {pos_side} 创新低: {old_str} → {current_profit_rate:.2f}%")
        
        return update_info
    
    def send_telegram_notification(self, update_info: Dict):
        """发送Telegram通知"""
        if not self.telegram_config:
            self.log("⚠️ Telegram配置未加载，跳过通知")
            return
        
        try:
            bot_token = self.telegram_config.get('bot_token')
            chat_id = self.telegram_config.get('chat_id')
            api_base = self.telegram_config.get('api_base_url', 'https://api.telegram.org')
            
            if not bot_token or not chat_id:
                self.log("⚠️ Telegram配置不完整，跳过通知")
                return
            
            # 构建消息
            update_type = update_info['type']
            inst_id = update_info['inst_id']
            pos_side = update_info['pos_side']
            old_value = update_info['old_value']
            new_value = update_info['new_value']
            position = update_info['position']
            
            side_name = "做多" if pos_side == "long" else "做空"
            
            if update_type == 'new_high':
                emoji = "🎉"
                type_name = "最大盈利创新高"
                color = "🟢"
            else:
                emoji = "⚠️"
                type_name = "最大亏损创新低"
                color = "🔴"
            
            old_value_safe = old_value if old_value not in [float('inf'), float('-inf'), None] else 0
            change = new_value - old_value_safe
            
            message = f"""
{emoji} <b>锚点系统极值提醒</b> {emoji}

📊 <b>币种</b>: {inst_id}
{color} <b>方向</b>: {side_name}
🔔 <b>类型</b>: {type_name}

💰 <b>当前盈亏率</b>: {new_value:+.2f}%
📈 <b>变化幅度</b>: {change:+.2f}%

📌 <b>持仓详情</b>:
  • 持仓量: {position.get('pos', 'N/A')}
  • 开仓价: {float(position.get('avgPx', 0)):.4f}
  • 标记价: {float(position.get('markPx', 0)):.4f}
  • 未实现盈亏: {float(position.get('upl', 0)):.2f} USDT
  • 保证金: {float(position.get('margin', 0)):.2f} USDT
  • 杠杆: {position.get('lever', 'N/A')}x

🕐 <b>更新时间</b>: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            url = f"{api_base}/bot{bot_token}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message.strip(),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
                "disable_notification": False
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response_data = response.json()
            
            if response_data.get('ok'):
                self.log(f"✅ Telegram通知发送成功")
            else:
                self.log(f"❌ Telegram通知发送失败: {response_data.get('description', 'Unknown error')}")
        
        except Exception as e:
            self.log(f"❌ 发送Telegram通知失败: {e}")
    
    def monitor_once(self):
        """执行一次监控"""
        self.log("🔍 开始检查极值...")
        
        # 获取主账号持仓
        positions = self.get_main_account_positions()
        
        if not positions:
            self.log("⚠️ 未获取到持仓数据")
            return
        
        self.log(f"📊 获取到 {len(positions)} 个持仓")
        
        # 检查每个持仓
        for position in positions:
            update_info = self.check_and_update_extreme(position)
            
            # 如果有更新，发送通知
            if update_info:
                self.send_telegram_notification(update_info)
        
        self.log("✅ 本次检查完成")
    
    def run(self, interval_seconds: int = 60):
        """运行监控循环"""
        self.log(f"🔄 监控循环启动，检查间隔: {interval_seconds}秒")
        
        while True:
            try:
                self.monitor_once()
            except Exception as e:
                self.log(f"❌ 监控出错: {e}")
            
            # 等待下一次检查
            time.sleep(interval_seconds)


def main():
    """主函数"""
    monitor = ExtremeMonitorJSONL()
    monitor.run(interval_seconds=60)


if __name__ == '__main__':
    main()
