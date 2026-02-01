#!/usr/bin/env python3
"""
27个币种价格追踪器（优化版）
- 每30分钟采集一次，以当天UTC+8 00:00的价格作为基准（0%）
- 计算每个币种相对于基准的涨跌幅
- 失败记录保存到队列，下次优先重试
"""
import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
import pytz
import logging
from collections import deque

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, '/home/user/webapp/source_code')

# OKX API配置
OKX_API_BASE = "https://www.okx.com/api/v5"

# 27个币种列表
SYMBOLS = [
    "BTC", "ETH", "XRP", "BNB", "SOL", "LTC", "DOGE", "SUI", "TRX", "TON",
    "ETC", "BCH", "HBAR", "XLM", "FIL", "LINK", "CRO", "DOT", "UNI", "NEAR",
    "APT", "CFX", "CRV", "STX", "LDO", "TAO", "AAVE"
]

# 数据存储路径
DATA_DIR = '/home/user/webapp/data/coin_price_tracker'
JSONL_FILE = os.path.join(DATA_DIR, 'coin_prices_30min.jsonl')
FAILED_QUEUE_FILE = os.path.join(DATA_DIR, 'failed_queue.json')

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 时区
TZ = pytz.timezone('Asia/Shanghai')

class FailedTaskQueue:
    """失败任务队列管理器"""
    
    def __init__(self, queue_file):
        self.queue_file = queue_file
        self.queue = deque()
        self.load_queue()
    
    def load_queue(self):
        """从文件加载失败队列"""
        if os.path.exists(self.queue_file):
            try:
                with open(self.queue_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.queue = deque(data)
                logger.info(f"📋 加载失败队列: {len(self.queue)} 个任务")
            except Exception as e:
                logger.error(f"加载失败队列出错: {e}")
                self.queue = deque()
    
    def save_queue(self):
        """保存失败队列到文件"""
        try:
            with open(self.queue_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.queue), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存失败队列出错: {e}")
    
    def add_failed_task(self, symbol, collect_time, reason):
        """添加失败任务"""
        task = {
            "symbol": symbol,
            "collect_time": collect_time,
            "failed_at": datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S"),
            "reason": reason,
            "retry_count": 0
        }
        
        # 检查是否已存在
        for existing_task in self.queue:
            if existing_task["symbol"] == symbol and existing_task["collect_time"] == collect_time:
                existing_task["retry_count"] += 1
                existing_task["reason"] = reason
                existing_task["failed_at"] = task["failed_at"]
                self.save_queue()
                return
        
        # 新任务添加到队列头部（优先处理）
        self.queue.appendleft(task)
        self.save_queue()
        logger.warning(f"  ⚠️  添加到失败队列: {symbol} @ {collect_time}")
    
    def get_priority_tasks(self, limit=10):
        """获取优先重试的任务"""
        tasks = []
        for _ in range(min(limit, len(self.queue))):
            if self.queue:
                tasks.append(self.queue.popleft())
        return tasks
    
    def remove_task(self, symbol, collect_time):
        """移除成功的任务"""
        self.queue = deque([
            task for task in self.queue 
            if not (task["symbol"] == symbol and task["collect_time"] == collect_time)
        ])
        self.save_queue()
    
    def get_stats(self):
        """获取队列统计"""
        if not self.queue:
            return {"total": 0, "by_symbol": {}}
        
        stats = {"total": len(self.queue), "by_symbol": {}}
        for task in self.queue:
            symbol = task["symbol"]
            stats["by_symbol"][symbol] = stats["by_symbol"].get(symbol, 0) + 1
        
        return stats

class CoinPriceTracker:
    """币种价格追踪器（优化版）"""
    
    def __init__(self):
        self.base_prices = {}  # 存储当天0点的基准价格
        self.current_date = None  # 当前日期
        self.failed_queue = FailedTaskQueue(FAILED_QUEUE_FILE)
    
    def get_today_start(self):
        """获取今天UTC+8的0点时间"""
        now = datetime.now(TZ)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return today_start
    
    def fetch_okx_price(self, symbol, max_retries=3):
        """从OKX获取永续合约价格（带重试）"""
        inst_id = f"{symbol}-USDT-SWAP"
        
        for attempt in range(max_retries):
            try:
                # 使用ticker接口获取最新价格
                url = f"{OKX_API_BASE}/market/ticker"
                params = {"instId": inst_id}
                
                response = requests.get(url, params=params, timeout=10)
                
                if response.status_code != 200:
                    logger.debug(f"  {symbol} HTTP错误 {response.status_code} (尝试 {attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    continue
                
                data = response.json()
                
                if data.get("code") != "0":
                    logger.debug(f"  {symbol} API错误: {data.get('msg')} (尝试 {attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    continue
                
                if not data.get("data"):
                    logger.debug(f"  {symbol} 无数据 (尝试 {attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    continue
                
                # 获取最新价格
                ticker = data["data"][0]
                last_price = float(ticker.get("last", 0))
                
                if last_price > 0:
                    return last_price, None
                else:
                    logger.debug(f"  {symbol} 价格为0 (尝试 {attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    
            except requests.exceptions.Timeout:
                logger.debug(f"  {symbol} 超时 (尝试 {attempt+1}/{max_retries})")
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"  {symbol} 异常: {e} (尝试 {attempt+1}/{max_retries})")
                time.sleep(0.5)
        
        return None, f"获取失败（{max_retries}次尝试）"
    
    def fetch_base_prices(self, force_realtime=False):
        """获取今天0点的基准价格
        
        Args:
            force_realtime: 是否强制使用实时价格（仅在首次采集时使用）
        
        Returns:
            dict: 基准价格字典
        """
        today_start = self.get_today_start()
        now = datetime.now(TZ)
        
        # 检查是否在00:00-00:30时间段
        is_early_morning = now.hour == 0 and now.minute < 30
        
        # 优先从历史记录读取（即使在凌晨时段）
        if not force_realtime:
            logger.info(f"⏰ 当前时间 {now.strftime('%H:%M')}，尝试从历史记录读取基准价格...")
            base_prices_from_history = self.load_base_prices_from_history(today_start)
            
            if base_prices_from_history:
                logger.info(f"✅ 从历史记录加载了 {len(base_prices_from_history)} 个币种的基准价格")
                return base_prices_from_history
            else:
                if is_early_morning:
                    logger.info("⚠️  凌晨时段且历史记录中没有今天的基准价格，获取实时价格作为基准")
                else:
                    logger.warning("⚠️  历史记录中没有今天的基准价格，使用实时价格")
        
        # 获取实时价格作为基准
        logger.info(f"📊 获取实时价格作为基准（{today_start.strftime('%Y-%m-%d')}）")
        
        base_prices = {}
        success_count = 0
        failed_symbols = []
        
        for symbol in SYMBOLS:
            price, error = self.fetch_okx_price(symbol)
            
            if price:
                base_prices[symbol] = price
                success_count += 1
                logger.info(f"  ✅ {symbol}: ${price:.8f}")
            else:
                logger.warning(f"  ❌ {symbol}: {error}")
                failed_symbols.append(symbol)
                # 添加到失败队列
                self.failed_queue.add_failed_task(
                    symbol, 
                    today_start.strftime("%Y-%m-%d %H:%M:%S"),
                    error or "未知错误"
                )
            
            time.sleep(0.05)  # 避免请求过快
        
        logger.info(f"✅ 基准价格获取完成: {success_count}/{len(SYMBOLS)}")
        
        if failed_symbols:
            logger.warning(f"⚠️  失败的币种: {', '.join(failed_symbols)}")
        
        return base_prices
    
    def load_base_prices_from_history(self, target_date):
        """从历史JSONL文件中加载指定日期00:00的基准价格
        
        Args:
            target_date: datetime对象，表示目标日期
        
        Returns:
            dict: 基准价格字典，如果找不到则返回None
        """
        if not os.path.exists(JSONL_FILE):
            return None
        
        target_date_str = target_date.strftime("%Y-%m-%d")
        
        try:
            with open(JSONL_FILE, 'r', encoding='utf-8') as f:
                # 从前往后查找，找到第一条该日期的记录（即00:00附近的记录）
                lines = f.readlines()
                
                # 从后往前检查最近200条，但找到后要选第一条
                recent_lines = lines[-200:] if len(lines) > 200 else lines
                
                for line in recent_lines:  # 顺序查找，找第一条
                    try:
                        record = json.loads(line)
                        
                        # 检查是否是目标日期的记录
                        if record.get('base_date') == target_date_str:
                            # 提取base_price作为基准价格
                            base_prices = {}
                            for symbol, data in record.get('day_changes', {}).items():
                                base_prices[symbol] = data.get('base_price', 0)
                            
                            if base_prices:
                                logger.info(f"  📖 找到历史基准价格记录: {record.get('collect_time')}")
                                return base_prices
                    except:
                        continue
            
            return None
            
        except Exception as e:
            logger.error(f"读取历史记录出错: {e}")
            return None
    
    def retry_failed_tasks(self):
        """重试失败队列中的任务"""
        priority_tasks = self.failed_queue.get_priority_tasks(limit=10)
        
        if not priority_tasks:
            return
        
        logger.info(f"🔄 重试失败队列: {len(priority_tasks)} 个任务")
        
        for task in priority_tasks:
            symbol = task["symbol"]
            collect_time = task["collect_time"]
            retry_count = task.get("retry_count", 0)
            
            logger.info(f"  🔄 重试 {symbol} @ {collect_time} (第{retry_count+1}次)")
            
            price, error = self.fetch_okx_price(symbol)
            
            if price:
                logger.info(f"    ✅ 成功: ${price:.8f}")
                self.failed_queue.remove_task(symbol, collect_time)
                # TODO: 更新历史记录
            else:
                logger.warning(f"    ❌ 仍然失败: {error}")
                # 重新加入队列（会自动增加retry_count）
                self.failed_queue.add_failed_task(symbol, collect_time, error or "重试失败")
            
            time.sleep(0.1)
    
    def fetch_current_prices(self):
        """获取当前价格"""
        logger.info("📊 获取当前价格...")
        
        current_prices = {}
        success_count = 0
        failed_symbols = []
        
        now = datetime.now(TZ)
        collect_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        for symbol in SYMBOLS:
            price, error = self.fetch_okx_price(symbol)
            
            if price:
                current_prices[symbol] = price
                success_count += 1
                logger.info(f"  ✅ {symbol}: ${price:.8f}")
            else:
                logger.warning(f"  ❌ {symbol}: {error}")
                failed_symbols.append(symbol)
                # 添加到失败队列
                self.failed_queue.add_failed_task(symbol, collect_time_str, error or "未知错误")
            
            time.sleep(0.05)
        
        logger.info(f"✅ 当前价格获取完成: {success_count}/{len(SYMBOLS)}")
        
        if failed_symbols:
            logger.warning(f"⚠️  失败的币种: {', '.join(failed_symbols)}")
        
        return current_prices
    
    def calculate_changes(self, base_prices, current_prices):
        """计算涨跌幅"""
        changes = {}
        
        for symbol in SYMBOLS:
            if symbol in base_prices and symbol in current_prices:
                base_price = base_prices[symbol]
                current_price = current_prices[symbol]
                
                if base_price > 0:
                    change_pct = ((current_price - base_price) / base_price) * 100
                    changes[symbol] = {
                        "base_price": base_price,
                        "current_price": current_price,
                        "change_pct": round(change_pct, 4)
                    }
                else:
                    changes[symbol] = {
                        "base_price": 0,
                        "current_price": current_price,
                        "change_pct": 0
                    }
            else:
                changes[symbol] = {
                    "base_price": base_prices.get(symbol, 0),
                    "current_price": current_prices.get(symbol, 0),
                    "change_pct": 0
                }
        
        return changes
    
    def save_to_jsonl(self, record):
        """保存数据到JSONL文件"""
        try:
            with open(JSONL_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            return True
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False
    
    def collect_once(self):
        """执行一次采集"""
        now = datetime.now(TZ)
        today_start = self.get_today_start()
        
        # 先尝试重试失败的任务
        if len(self.failed_queue.queue) > 0:
            stats = self.failed_queue.get_stats()
            logger.info(f"📋 失败队列统计: 总计 {stats['total']} 个任务")
            for symbol, count in sorted(stats['by_symbol'].items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  - {symbol}: {count} 个失败任务")
            self.retry_failed_tasks()
        
        # 检查是否需要更新基准价格（新的一天）
        if self.current_date != today_start.date():
            logger.info(f"🔄 新的一天，更新基准价格: {today_start.date()}")
            self.base_prices = self.fetch_base_prices()
            self.current_date = today_start.date()
        
        # 如果没有基准价格，先获取
        if not self.base_prices:
            logger.info("📊 首次运行，获取基准价格...")
            self.base_prices = self.fetch_base_prices()
            self.current_date = today_start.date()
        
        # 获取当前价格
        current_prices = self.fetch_current_prices()
        
        # 特殊处理：如果是00:00采集，使用当前价格作为基准价格（确保涨跌幅为0%）
        if now.hour == 0 and now.minute == 0:
            logger.info("🎯 00:00采集，将当前价格设为基准价格（涨跌幅=0%）")
            self.base_prices = current_prices.copy()
        
        # 计算涨跌幅
        changes = self.calculate_changes(self.base_prices, current_prices)
        
        # 统计
        valid_count = sum(1 for v in changes.values() if v['current_price'] > 0)
        
        # 计算总和和平均值
        total_change = sum(v['change_pct'] for v in changes.values())
        average_change = total_change / len(SYMBOLS) if len(SYMBOLS) > 0 else 0
        success_count = sum(1 for v in changes.values() if v['current_price'] > 0)
        failed_count = len(SYMBOLS) - success_count
        
        # 构建记录（使用day_changes字段名以保持一致）
        record = {
            "collect_time": now.strftime("%Y-%m-%d %H:%M:%S"),
            "timestamp": int(now.timestamp()),
            "base_date": today_start.strftime("%Y-%m-%d"),
            "day_changes": changes,
            "total_change": round(total_change, 4),
            "average_change": round(average_change, 4),
            "total_coins": len(SYMBOLS),
            "valid_coins": valid_count,
            "success_count": success_count,
            "failed_count": failed_count
        }
        
        # 保存
        if self.save_to_jsonl(record):
            logger.info(f"✅ 数据已保存: {valid_count}/{len(SYMBOLS)} 个币种")
            
            # 显示涨跌TOP5
            sorted_changes = sorted(
                [(k, v['change_pct']) for k, v in changes.items() if v['current_price'] > 0],
                key=lambda x: x[1],
                reverse=True
            )
            
            if sorted_changes:
                logger.info("📈 涨幅TOP5:")
                for symbol, change in sorted_changes[:5]:
                    logger.info(f"  {symbol}: {change:+.2f}%")
                
                logger.info("📉 跌幅TOP5:")
                for symbol, change in sorted_changes[-5:]:
                    logger.info(f"  {symbol}: {change:+.2f}%")
        else:
            logger.error("❌ 数据保存失败")
        
        return record

def main():
    """主函数"""
    logger.info("""
╔═══════════════════════════════════════════════════════════════════╗
║            27币种价格追踪器 - 30分钟间隔（优化版）                ║
║                 数据源: OKX永续合约                               ║
║                 失败任务自动重试                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    tracker = CoinPriceTracker()
    
    # 首次采集
    logger.info("🚀 开始首次采集...")
    tracker.collect_once()
    
    # 定时采集（只在0分和30分）
    logger.info("⏰ 采集策略: 只在每小时的0分和30分采集数据")
    
    while True:
        try:
            now = datetime.now(TZ)
            current_minute = now.minute
            
            # 计算下次采集时间（只在0分和30分）
            if current_minute < 30:
                # 等到30分
                next_minute = 30
            else:
                # 等到下一个小时的0分
                next_minute = 0
                now = now + timedelta(hours=1)
            
            next_run = now.replace(minute=next_minute, second=0, microsecond=0)
            wait_seconds = (next_run - datetime.now(TZ)).total_seconds()
            
            logger.info(f"\n⏰ 下次采集时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')} (0分或30分)")
            logger.info(f"💤 等待 {int(wait_seconds)} 秒...\n")
            
            time.sleep(wait_seconds)
            
            # 执行采集
            logger.info(f"\n{'='*70}")
            logger.info(f"🔄 开始采集: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'='*70}")
            
            tracker.collect_once()
            
        except KeyboardInterrupt:
            logger.info("\n\n⚠️  收到中断信号，正在退出...")
            break
        except Exception as e:
            logger.error(f"❌ 采集出错: {e}", exc_info=True)
            logger.info("⏰ 60秒后重试...")
            time.sleep(60)

if __name__ == "__main__":
    main()
