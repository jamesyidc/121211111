#!/usr/bin/env python3
"""
锚点系统独立计算引擎
功能：脱离浏览器，独立计算和监控锚点持仓数据
数据源：JSONL（已迁移，使用北京时间）
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/user/webapp/logs/anchor_engine.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 北京时区
BEIJING_TZ = timezone(timedelta(hours=8))

class AnchorJSONLManager:
    """JSONL 数据管理器"""
    
    def __init__(self, data_dir: str = '/home/user/webapp/data/anchor_jsonl'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
    def _get_file_path(self, table_name: str) -> str:
        """获取表对应的 JSONL 文件路径"""
        return os.path.join(self.data_dir, f"{table_name}.jsonl")
    
    def append_record(self, table_name: str, record: Dict[str, Any]) -> bool:
        """追加一条记录到 JSONL 文件"""
        try:
            file_path = self._get_file_path(table_name)
            
            # 添加北京时间
            if 'timestamp' in record:
                try:
                    ts = float(record['timestamp'])
                    beijing_time = datetime.fromtimestamp(ts, tz=BEIJING_TZ)
                    record['beijing_time'] = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    pass
            
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            return True
        except Exception as e:
            logger.error(f"追加记录失败 [{table_name}]: {e}")
            return False
    
    def read_records(self, table_name: str, limit: Optional[int] = None, 
                     reverse: bool = True) -> List[Dict[str, Any]]:
        """读取记录（倒序为最新在前）"""
        try:
            file_path = self._get_file_path(table_name)
            if not os.path.exists(file_path):
                return []
            
            records = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            
            if reverse:
                records = list(reversed(records))
            
            if limit:
                records = records[:limit]
            
            return records
        except Exception as e:
            logger.error(f"读取记录失败 [{table_name}]: {e}")
            return []
    
    def get_latest_record(self, table_name: str) -> Optional[Dict[str, Any]]:
        """获取最新的一条记录"""
        records = self.read_records(table_name, limit=1, reverse=True)
        return records[0] if records else None
    
    def count_records(self, table_name: str) -> int:
        """统计记录数"""
        try:
            file_path = self._get_file_path(table_name)
            if not os.path.exists(file_path):
                return 0
            
            count = 0
            with open(file_path, 'r', encoding='utf-8') as f:
                for _ in f:
                    count += 1
            return count
        except Exception as e:
            logger.error(f"统计记录失败 [{table_name}]: {e}")
            return 0


class OKExAPI:
    """OKEx API 封装"""
    
    BASE_URL = "https://www.okx.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_mark_price(self, inst_id: str) -> Optional[float]:
        """获取标记价格"""
        try:
            url = f"{self.BASE_URL}/api/v5/public/mark-price"
            params = {'instType': 'SWAP', 'instId': inst_id}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('code') == '0' and data.get('data'):
                return float(data['data'][0]['markPx'])
            
            return None
        except Exception as e:
            logger.error(f"获取标记价格失败 [{inst_id}]: {e}")
            return None
    
    def get_account_positions(self) -> List[Dict[str, Any]]:
        """获取账户持仓（需要API密钥，这里仅示例）"""
        # 实际使用需要配置 API Key
        logger.warning("get_account_positions 需要配置 API 密钥")
        return []


class AnchorCalculationEngine:
    """锚点计算引擎"""
    
    def __init__(self):
        self.jsonl_manager = AnchorJSONLManager()
        self.okex_api = OKExAPI()
        
    def calculate_profit_rate(self, avg_price: float, mark_price: float, 
                              pos_side: str) -> float:
        """计算收益率"""
        if pos_side == 'long':
            return ((mark_price - avg_price) / avg_price) * 100
        elif pos_side == 'short':
            return ((avg_price - mark_price) / avg_price) * 100
        return 0.0
    
    def calculate_upl(self, pos_size: float, avg_price: float, 
                      mark_price: float, pos_side: str) -> float:
        """计算未实现盈亏"""
        if pos_side == 'long':
            return pos_size * (mark_price - avg_price)
        elif pos_side == 'short':
            return pos_size * (avg_price - mark_price)
        return 0.0
    
    def calculate_upl_ratio(self, upl: float, margin: float) -> float:
        """计算未实现盈亏比率"""
        if margin > 0:
            return (upl / margin) * 100
        return 0.0
    
    def determine_alert_type(self, profit_rate: float) -> Optional[str]:
        """判断告警类型"""
        if profit_rate <= -3.0:
            return 'extreme'
        elif profit_rate <= -2.0:
            return 'critical'
        elif profit_rate <= -1.5:
            return 'high'
        elif profit_rate <= -1.0:
            return 'medium'
        elif profit_rate <= -0.5:
            return 'low'
        return None
    
    def process_position_monitor(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """处理持仓监控"""
        try:
            inst_id = position['inst_id']
            pos_side = position['pos_side']
            pos_size = float(position['pos_size'])
            avg_price = float(position['avg_price'])
            margin = float(position.get('margin', 0))
            leverage = float(position.get('leverage', 1))
            
            # 获取当前标记价格
            mark_price = self.okex_api.get_mark_price(inst_id)
            if not mark_price:
                logger.warning(f"无法获取标记价格: {inst_id}")
                return None
            
            # 计算指标
            profit_rate = self.calculate_profit_rate(avg_price, mark_price, pos_side)
            upl = self.calculate_upl(pos_size, avg_price, mark_price, pos_side)
            upl_ratio = self.calculate_upl_ratio(upl, margin)
            alert_type = self.determine_alert_type(profit_rate)
            
            # 构建监控记录
            beijing_now = datetime.now(BEIJING_TZ)
            monitor_record = {
                'timestamp': int(beijing_now.timestamp()),
                'beijing_time': beijing_now.strftime('%Y-%m-%d %H:%M:%S'),
                'inst_id': inst_id,
                'pos_side': pos_side,
                'pos_size': pos_size,
                'avg_price': avg_price,
                'mark_price': mark_price,
                'upl': round(upl, 4),
                'upl_ratio': round(upl_ratio, 2),
                'margin': margin,
                'leverage': leverage,
                'profit_rate': round(profit_rate, 4),
                'alert_type': alert_type,
                'alert_sent': 0
            }
            
            # 保存到 JSONL
            self.jsonl_manager.append_record('anchor_monitors', monitor_record)
            
            # 如果有告警，记录告警
            if alert_type:
                self.create_alert(monitor_record)
            
            return monitor_record
            
        except Exception as e:
            logger.error(f"处理持仓监控失败: {e}")
            return None
    
    def create_alert(self, monitor: Dict[str, Any]) -> bool:
        """创建告警记录"""
        try:
            beijing_now = datetime.now(BEIJING_TZ)
            alert_record = {
                'timestamp': int(beijing_now.timestamp()),
                'beijing_time': beijing_now.strftime('%Y-%m-%d %H:%M:%S'),
                'inst_id': monitor['inst_id'],
                'pos_side': monitor['pos_side'],
                'profit_rate': monitor['profit_rate'],
                'alert_type': monitor['alert_type'],
                'message': f"{monitor['inst_id']} {monitor['pos_side']} 收益率: {monitor['profit_rate']:.2f}%",
                'sent_status': 0
            }
            
            self.jsonl_manager.append_record('anchor_alerts', alert_record)
            logger.info(f"📢 告警创建: {alert_record['message']}")
            return True
            
        except Exception as e:
            logger.error(f"创建告警失败: {e}")
            return False
    
    def get_monitors_summary(self, limit: int = 10) -> Dict[str, Any]:
        """获取监控汇总"""
        monitors = self.jsonl_manager.read_records('anchor_monitors', limit=limit)
        
        if not monitors:
            return {
                'total_count': 0,
                'latest_time': None,
                'monitors': []
            }
        
        return {
            'total_count': self.jsonl_manager.count_records('anchor_monitors'),
            'latest_time': monitors[0].get('timestamp_beijing') or monitors[0].get('beijing_time'),
            'monitors': monitors
        }
    
    def get_alerts_summary(self, limit: int = 10) -> Dict[str, Any]:
        """获取告警汇总"""
        alerts = self.jsonl_manager.read_records('anchor_alerts', limit=limit)
        
        if not alerts:
            return {
                'total_count': 0,
                'latest_time': None,
                'alerts': []
            }
        
        return {
            'total_count': self.jsonl_manager.count_records('anchor_alerts'),
            'latest_time': alerts[0].get('timestamp_beijing') or alerts[0].get('beijing_time'),
            'alerts': alerts
        }
    
    def run_continuous_monitor(self, interval: int = 60):
        """持续监控模式（独立运行）"""
        logger.info("🚀 锚点计算引擎启动 - 独立监控模式")
        logger.info(f"📊 数据源: JSONL (/home/user/webapp/data/anchor_jsonl)")
        logger.info(f"⏱️  监控间隔: {interval}秒")
        logger.info(f"🕐 时区: 北京时间 (UTC+8)")
        
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                beijing_now = datetime.now(BEIJING_TZ)
                logger.info(f"\n{'='*60}")
                logger.info(f"🔄 监控周期 #{cycle_count} | {beijing_now.strftime('%Y-%m-%d %H:%M:%S')} (北京时间)")
                logger.info(f"{'='*60}")
                
                # 这里需要实际的持仓数据
                # 示例：从配置文件或API获取持仓列表
                positions = self.get_current_positions()
                
                if positions:
                    logger.info(f"📈 发现 {len(positions)} 个持仓需要监控")
                    
                    for idx, position in enumerate(positions, 1):
                        logger.info(f"  处理 {idx}/{len(positions)}: {position['inst_id']} {position['pos_side']}")
                        result = self.process_position_monitor(position)
                        
                        if result:
                            logger.info(f"    ✅ 价格: {result['mark_price']:.4f} | 收益率: {result['profit_rate']:.2f}%")
                        else:
                            logger.warning(f"    ⚠️ 处理失败")
                        
                        time.sleep(0.5)  # 避免请求过快
                else:
                    logger.info("📭 当前无持仓需要监控")
                
                # 显示汇总
                summary = self.get_monitors_summary(limit=5)
                logger.info(f"\n📊 监控汇总:")
                logger.info(f"  总记录数: {summary['total_count']}")
                logger.info(f"  最新时间: {summary['latest_time']}")
                
                alerts_summary = self.get_alerts_summary(limit=3)
                if alerts_summary['total_count'] > 0:
                    logger.info(f"\n⚠️  告警汇总:")
                    logger.info(f"  总告警数: {alerts_summary['total_count']}")
                    logger.info(f"  最新告警: {alerts_summary['latest_time']}")
                
                logger.info(f"\n⏳ 等待 {interval}秒 后进行下一轮监控...\n")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                logger.info("\n\n👋 收到停止信号，正在退出...")
                break
            except Exception as e:
                logger.error(f"❌ 监控周期异常: {e}", exc_info=True)
                time.sleep(interval)
    
    def get_current_positions(self) -> List[Dict[str, Any]]:
        """获取当前持仓列表（示例）"""
        # 实际使用时应该从 OKEx API 获取
        # 这里提供一个示例持仓列表
        
        # 尝试从最新的监控记录中获取持仓
        latest_monitors = self.jsonl_manager.read_records('anchor_monitors', limit=50)
        
        if not latest_monitors:
            logger.warning("无历史监控记录，返回示例持仓")
            return [
                {
                    'inst_id': 'BTC-USDT-SWAP',
                    'pos_side': 'long',
                    'pos_size': 0.01,
                    'avg_price': 95000.0,
                    'margin': 100.0,
                    'leverage': 10
                }
            ]
        
        # 从最近的监控记录中提取唯一持仓
        positions_map = {}
        for monitor in latest_monitors:
            key = f"{monitor['inst_id']}_{monitor['pos_side']}"
            if key not in positions_map:
                positions_map[key] = {
                    'inst_id': monitor['inst_id'],
                    'pos_side': monitor['pos_side'],
                    'pos_size': monitor['pos_size'],
                    'avg_price': monitor['avg_price'],
                    'margin': monitor['margin'],
                    'leverage': monitor['leverage']
                }
        
        return list(positions_map.values())


def main():
    """主函数"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║         🎯 锚点系统独立计算引擎 v1.0                         ║
║                                                                ║
║  功能: 脱离浏览器，独立计算和监控锚点持仓                    ║
║  数据: JSONL 格式 (北京时间)                                 ║
║  模式: 独立后台运行                                           ║
╚════════════════════════════════════════════════════════════════╝
    """)
    
    # 创建日志目录
    os.makedirs('/home/user/webapp/logs', exist_ok=True)
    
    # 创建引擎实例
    engine = AnchorCalculationEngine()
    
    # 检查数据
    logger.info("🔍 检查 JSONL 数据...")
    monitors_count = engine.jsonl_manager.count_records('anchor_monitors')
    alerts_count = engine.jsonl_manager.count_records('anchor_alerts')
    
    logger.info(f"  ✅ anchor_monitors: {monitors_count:,} 条记录")
    logger.info(f"  ✅ anchor_alerts: {alerts_count:,} 条记录")
    
    if monitors_count > 0:
        latest = engine.jsonl_manager.get_latest_record('anchor_monitors')
        beijing_time = latest.get('timestamp_beijing') or latest.get('beijing_time') or latest.get('timestamp', 'N/A')
        logger.info(f"  📅 最新记录: {beijing_time} (北京时间)")
    
    # 询问运行模式
    print("\n" + "="*60)
    print("选择运行模式:")
    print("  1. 单次测试 - 运行一次监控测试")
    print("  2. 持续监控 - 后台持续运行（Ctrl+C 停止）")
    print("  3. 仅查看数据 - 查看最新监控数据")
    print("="*60)
    
    try:
        choice = input("\n请输入选择 (1/2/3): ").strip()
        
        if choice == '1':
            logger.info("\n🧪 单次测试模式...")
            positions = engine.get_current_positions()
            logger.info(f"发现 {len(positions)} 个持仓")
            
            for position in positions:
                result = engine.process_position_monitor(position)
                if result:
                    logger.info(f"✅ {result['inst_id']} {result['pos_side']}: 收益率 {result['profit_rate']:.2f}%")
            
            summary = engine.get_monitors_summary(limit=5)
            logger.info(f"\n监控记录总数: {summary['total_count']}")
            
        elif choice == '2':
            interval = input("请输入监控间隔（秒，默认60）: ").strip()
            interval = int(interval) if interval.isdigit() else 60
            engine.run_continuous_monitor(interval=interval)
            
        elif choice == '3':
            logger.info("\n📊 最新监控数据:")
            summary = engine.get_monitors_summary(limit=10)
            
            if summary['monitors']:
                logger.info(f"  总记录数: {summary['total_count']}")
                logger.info(f"  最新时间: {summary['latest_time']}\n")
                
                for idx, monitor in enumerate(summary['monitors'], 1):
                    time_str = monitor.get('timestamp_beijing') or monitor.get('beijing_time') or monitor.get('timestamp', 'N/A')
                    logger.info(f"  {idx}. {time_str} | {monitor['inst_id']} {monitor['pos_side']}")
                    logger.info(f"     价格: {monitor['mark_price']:.4f} | 收益率: {monitor['profit_rate']:.2f}%")
            else:
                logger.info("  暂无数据")
            
            alerts_summary = engine.get_alerts_summary(limit=5)
            if alerts_summary['alerts']:
                logger.info(f"\n⚠️  最新告警:")
                logger.info(f"  总告警数: {alerts_summary['total_count']}\n")
                
                for idx, alert in enumerate(alerts_summary['alerts'], 1):
                    time_str = alert.get('timestamp_beijing') or alert.get('beijing_time') or alert.get('timestamp', 'N/A')
                    logger.info(f"  {idx}. {time_str} | {alert['message']}")
        else:
            logger.warning("无效选择")
            
    except KeyboardInterrupt:
        logger.info("\n👋 再见!")
    except Exception as e:
        logger.error(f"运行异常: {e}", exc_info=True)


if __name__ == '__main__':
    main()
