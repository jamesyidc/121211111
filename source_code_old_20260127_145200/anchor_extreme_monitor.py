#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
锚定系统极值实时监控
功能：
1. 实时比对主仓位的涨跌幅
2. 更新最大盈利/最大亏损极值
3. 发送Telegram通知
"""

import os
import sys
import time
import json
import requests
from datetime import datetime
from pathlib import Path
import pytz

# 添加项目路径
sys.path.insert(0, '/home/user/webapp/source_code')

from extreme_jsonl_manager import ExtremeJSONLManager

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# API基础URL
API_BASE_URL = 'http://localhost:5000'

# Telegram配置文件路径
TELEGRAM_CONFIG_PATH = '/home/user/webapp/configs/telegram_config.json'

# 极值数据存储
EXTREME_DATA_DIR = Path('/home/user/webapp/data/extreme_jsonl')
EXTREME_DATA_DIR.mkdir(parents=True, exist_ok=True)


class AnchorExtremeMonitor:
    """锚定系统极值监控器"""
    
    def __init__(self):
        self.manager = ExtremeJSONLManager(trade_mode='real')
        self.telegram_config = self.load_telegram_config()
        self.extreme_cache = {}  # 缓存当前极值
        self.load_extreme_cache()
    
    def load_telegram_config(self):
        """加载Telegram配置"""
        try:
            if not os.path.exists(TELEGRAM_CONFIG_PATH):
                self.log("⚠️ Telegram配置文件不存在")
                return None
            
            with open(TELEGRAM_CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.log("✅ Telegram配置已加载")
                return config
        except Exception as e:
            self.log(f"⚠️ 加载Telegram配置失败: {e}")
            return None
    
    def load_extreme_cache(self):
        """加载当前极值缓存"""
        records = self.manager.get_all_records()
        for record in records:
            key = f"{record['inst_id']}_{record['pos_side']}_{record['record_type']}"
            self.extreme_cache[key] = record['profit_rate']
        
        self.log(f"✅ 已加载 {len(self.extreme_cache)} 条极值记录")
    
    def log(self, message):
        """打印日志"""
        timestamp = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}", flush=True)
    
    def get_current_positions(self):
        """获取当前持仓"""
        try:
            url = f'{API_BASE_URL}/api/anchor-system/current-positions?trade_mode=real'
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                self.log(f"❌ API请求失败: {response.status_code}")
                return []
            
            result = response.json()
            
            if not result.get('success', False):
                self.log(f"❌ API返回失败: {result.get('error', '未知错误')}")
                return []
            
            positions = result.get('positions', [])
            self.log(f"📊 获取到持仓总数: {len(positions)}")
            return positions
            
        except Exception as e:
            self.log(f"❌ 获取持仓异常: {e}")
            return []
    
    def check_and_update_extremes(self, positions):
        """检查并更新极值"""
        updated_extremes = []
        
        for pos in positions:
            inst_id = pos.get('symbol', pos.get('inst_id', ''))
            pos_side = pos.get('pos_side', '').lower()
            profit_rate = float(pos.get('profit_rate', 0))
            
            # 检查最大盈利
            max_profit_key = f"{inst_id}_{pos_side}_max_profit"
            current_max_profit = self.extreme_cache.get(max_profit_key, None)
            
            if current_max_profit is None or profit_rate > current_max_profit:
                # 新极值！
                update_info = {
                    'inst_id': inst_id,
                    'pos_side': pos_side,
                    'record_type': 'max_profit',
                    'old_value': current_max_profit,
                    'new_value': profit_rate,
                    'position': pos
                }
                updated_extremes.append(update_info)
                
                # 更新缓存
                self.extreme_cache[max_profit_key] = profit_rate
                
                # 保存到JSONL
                record = {
                    'inst_id': inst_id,
                    'pos_side': pos_side,
                    'record_type': 'max_profit',
                    'profit_rate': profit_rate,
                    'timestamp': int(time.time()),
                    'pos_size': abs(float(pos.get('position', 0))),
                    'avg_price': float(pos.get('avg_price', 0)),
                    'mark_price': float(pos.get('mark_price', 0)),
                    'upl': float(pos.get('unrealized_pnl', 0)),
                    'margin': float(pos.get('margin', 0)),
                    'leverage': float(pos.get('leverage', 0))
                }
                self.manager.add_record(record)
                
                self.log(f"🟢 {inst_id} {pos_side} 最大盈利更新: {current_max_profit}% → {profit_rate:.2f}%")
            
            # 检查最大亏损
            max_loss_key = f"{inst_id}_{pos_side}_max_loss"
            current_max_loss = self.extreme_cache.get(max_loss_key, None)
            
            if current_max_loss is None or profit_rate < current_max_loss:
                # 新极值！
                update_info = {
                    'inst_id': inst_id,
                    'pos_side': pos_side,
                    'record_type': 'max_loss',
                    'old_value': current_max_loss,
                    'new_value': profit_rate,
                    'position': pos
                }
                updated_extremes.append(update_info)
                
                # 更新缓存
                self.extreme_cache[max_loss_key] = profit_rate
                
                # 保存到JSONL
                record = {
                    'inst_id': inst_id,
                    'pos_side': pos_side,
                    'record_type': 'max_loss',
                    'profit_rate': profit_rate,
                    'timestamp': int(time.time()),
                    'pos_size': abs(float(pos.get('position', 0))),
                    'avg_price': float(pos.get('avg_price', 0)),
                    'mark_price': float(pos.get('mark_price', 0)),
                    'upl': float(pos.get('unrealized_pnl', 0)),
                    'margin': float(pos.get('margin', 0)),
                    'leverage': float(pos.get('leverage', 0))
                }
                self.manager.add_record(record)
                
                self.log(f"🔴 {inst_id} {pos_side} 最大亏损更新: {current_max_loss}% → {profit_rate:.2f}%")
        
        return updated_extremes
    
    def send_telegram_notification(self, update_info):
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
            inst_id = update_info['inst_id']
            pos_side = update_info['pos_side']
            record_type = update_info['record_type']
            old_value = update_info['old_value']
            new_value = update_info['new_value']
            position = update_info['position']
            
            # 判断是盈利还是亏损
            if record_type == 'max_profit':
                emoji = "🟢📈"
                type_name = "最大盈利创新高"
                color = "🟢"
            else:
                emoji = "🔴📉"
                type_name = "最大亏损创新低"
                color = "🔴"
            
            # 计算变动
            if old_value is None:
                change_text = "首次记录"
            else:
                change = new_value - old_value
                change_text = f"{change:+.2f}%"
            
            # 方向中文
            side_cn = "做多" if pos_side == 'long' else "做空"
            
            message = f"""
{emoji} <b>锚定系统极值提醒</b> {emoji}

{color} <b>币种</b>: {inst_id}
🎯 <b>方向</b>: {side_cn}
📊 <b>类型</b>: {type_name}

💰 <b>当前盈亏率</b>: <code>{new_value:+.2f}%</code>
📈 <b>变动</b>: {change_text}
{f"📉 <b>旧值</b>: {old_value:+.2f}%" if old_value is not None else ""}

💼 <b>持仓信息</b>:
  • 持仓量: {abs(float(position.get('position', 0)))}
  • 开仓价: ${float(position.get('avg_price', 0)):.4f}
  • 标记价: ${float(position.get('mark_price', 0)):.4f}
  • 未实现盈亏: ${float(position.get('unrealized_pnl', 0)):.2f}

⏰ <b>时间</b>: {datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')}
🔗 <b>查看详情</b>: /anchor-system-real
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
                self.log(f"✅ Telegram通知已发送: {inst_id} {pos_side} {type_name}")
                return True
            else:
                self.log(f"⚠️ Telegram通知发送失败: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Telegram通知发送异常: {e}")
            return False
    
    def run_once(self):
        """执行一次检查"""
        self.log("🔍 开始检查极值...")
        
        # 获取当前持仓
        positions = self.get_current_positions()
        
        if not positions:
            self.log("⚠️ 没有持仓数据")
            return
        
        # 检查并更新极值
        updated_extremes = self.check_and_update_extremes(positions)
        
        # 发送通知
        if updated_extremes:
            self.log(f"🚨 发现 {len(updated_extremes)} 个极值更新")
            for update_info in updated_extremes:
                self.send_telegram_notification(update_info)
        else:
            self.log("✅ 没有新的极值")
        
        self.log("✅ 检查完成")
    
    def run_continuous(self):
        """持续监控"""
        self.log("🚀 开始持续监控 (每1分钟检查一次)")
        
        while True:
            try:
                self.run_once()
                
                # 等待60秒
                self.log("⏳ 等待 60 秒后再次检查...")
                time.sleep(60)
                
            except KeyboardInterrupt:
                self.log("⚠️ 收到中断信号，停止监控")
                break
            except Exception as e:
                self.log(f"❌ 监控异常: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)


def main():
    """主函数"""
    monitor = AnchorExtremeMonitor()
    monitor.run_continuous()


if __name__ == '__main__':
    main()
