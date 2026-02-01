#!/usr/bin/env python3
"""
服务健康监控 - 检查各个数据采集服务的运行状态
"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

class ServiceHealthMonitor:
    def __init__(self):
        self.data_dir = Path('/home/user/webapp/data')
        self.services = {
            'anchor_profit': {
                'name': '锚点盈利统计',
                'file': self.data_dir / 'anchor_profit_stats' / 'anchor_profit_stats.jsonl',
                'interval': 60,  # 采集间隔（秒）
                'alert_threshold': 300  # 超过5分钟未更新就告警
            },
            'escape_signal': {
                'name': '逃顶信号计算',
                'file': self.data_dir / 'escape_signal_jsonl' / 'escape_signal_stats.jsonl',
                'interval': 60,
                'alert_threshold': 300,
                'datetime_field': 'timestamp'  # 特殊：使用timestamp字段
            },
            'liquidation_1h': {
                'name': '1小时爆仓数据',
                'file': self.data_dir / 'liquidation_1h' / 'liquidation_1h.jsonl',
                'interval': 60,
                'alert_threshold': 300
            },
            'sar_slope': {
                'name': 'SAR斜率数据',
                'file': self.data_dir / 'sar_slope_jsonl' / 'sar_slope_data.jsonl',
                'interval': 60,
                'alert_threshold': 300
            }
        }
    
    def check_service(self, service_config):
        """检查单个服务的健康状态"""
        result = {
            'name': service_config['name'],
            'status': 'unknown',
            'last_update': None,
            'minutes_ago': None,
            'message': ''
        }
        
        file_path = service_config['file']
        
        # 检查文件是否存在
        if not file_path.exists():
            result['status'] = 'error'
            result['message'] = f'数据文件不存在: {file_path}'
            return result
        
        try:
            # 读取最后一行
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if not lines:
                    result['status'] = 'error'
                    result['message'] = '数据文件为空'
                    return result
                
                last_line = lines[-1].strip()
                if not last_line:
                    result['status'] = 'error'
                    result['message'] = '最后一行为空'
                    return result
                
                data = json.loads(last_line)
                
                # 获取时间戳 - 支持不同的字段名
                datetime_field = service_config.get('datetime_field', 'datetime')
                
                if datetime_field == 'timestamp' and 'timestamp' in data:
                    # timestamp字段（Unix时间戳）
                    last_update = datetime.fromtimestamp(data['timestamp'])
                    last_update_str = last_update.strftime('%Y-%m-%d %H:%M:%S')
                elif 'datetime' in data:
                    # datetime字段（字符串）
                    last_update_str = data['datetime']
                    last_update = datetime.strptime(last_update_str, '%Y-%m-%d %H:%M:%S')
                elif 'timestamp' in data:
                    # 兜底：如果有timestamp就用timestamp
                    last_update = datetime.fromtimestamp(data['timestamp'])
                    last_update_str = last_update.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    result['status'] = 'error'
                    result['message'] = f'数据中没有时间字段（需要 datetime 或 timestamp）'
                    return result
                now = datetime.now()
                time_diff = (now - last_update).total_seconds()
                minutes_ago = time_diff / 60
                
                result['last_update'] = last_update_str
                result['minutes_ago'] = round(minutes_ago, 1)
                
                # 判断状态
                if time_diff > service_config['alert_threshold']:
                    result['status'] = 'warning'
                    result['message'] = f'数据已停止更新 {minutes_ago:.1f} 分钟'
                else:
                    result['status'] = 'healthy'
                    result['message'] = f'运行正常，{minutes_ago:.1f} 分钟前更新'
                
        except Exception as e:
            result['status'] = 'error'
            result['message'] = f'检查失败: {str(e)}'
        
        return result
    
    def check_all(self):
        """检查所有服务"""
        results = {}
        for service_id, service_config in self.services.items():
            results[service_id] = self.check_service(service_config)
        
        # 统计
        total = len(results)
        healthy = sum(1 for r in results.values() if r['status'] == 'healthy')
        warning = sum(1 for r in results.values() if r['status'] == 'warning')
        error = sum(1 for r in results.values() if r['status'] == 'error')
        
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total': total,
                'healthy': healthy,
                'warning': warning,
                'error': error
            },
            'services': results
        }

def get_health_status():
    """获取健康状态（供Flask调用）"""
    monitor = ServiceHealthMonitor()
    return monitor.check_all()

if __name__ == '__main__':
    monitor = ServiceHealthMonitor()
    result = monitor.check_all()
    print(json.dumps(result, indent=2, ensure_ascii=False))
