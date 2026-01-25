#!/usr/bin/env python3
"""
加密货币数据分析系统 - 完全仿照参考页面风格
"""
from flask import Flask, render_template_string, render_template, request, jsonify, send_from_directory, send_file, make_response, redirect
from flask_compress import Compress
import sqlite3
from datetime import datetime, timedelta
import json
import pytz
import os
from functools import wraps
import time
import traceback

app = Flask(__name__)
# 启用gzip压缩 - 减少74KB到约15-20KB
Compress(app)

# 导入JSONL管理器
from gdrive_jsonl_manager import GDriveJSONLManager
from query_jsonl_manager import QueryJSONLManager

gdrive_jsonl_manager = GDriveJSONLManager()
# 使用GDrive数据目录作为Query数据源（包含最新数据）
query_jsonl_manager = QueryJSONLManager(data_dir='/home/user/webapp/data/gdrive_jsonl')

# OKX交易日志管理器
class OKXTradingLogger:
    """OKX交易日志记录器 - 所有操作记录到JSONL文件（只写不改）"""
    def __init__(self, log_dir='/home/user/webapp/data/okx_trading_logs'):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
    def _get_log_file(self, date_str=None):
        """获取当天的日志文件路径"""
        if date_str is None:
            date_str = datetime.now(BEIJING_TZ).strftime('%Y%m%d')
        return os.path.join(self.log_dir, f'trading_log_{date_str}.jsonl')
    
    def log(self, action, account_id, details=None, result=None):
        """
        记录交易操作日志
        
        参数：
        - action: 操作类型（open_position, close_position, cancel_order, batch_open, batch_close等）
        - account_id: 账户ID
        - details: 操作详情（交易对、方向、数量等）
        - result: 操作结果（成功/失败、错误信息等）
        """
        try:
            log_entry = {
                'timestamp': datetime.now(BEIJING_TZ).isoformat(),
                'timestamp_unix': int(time.time()),
                'action': action,
                'account_id': account_id,
                'details': details or {},
                'result': result or {}
            }
            
            log_file = self._get_log_file()
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            
            print(f"[OKX日志] {action} - {account_id} - {result.get('status', 'unknown')}")
            
        except Exception as e:
            print(f"[OKX日志] 记录失败: {str(e)}")
    
    def get_logs(self, date_str=None, limit=100):
        """
        读取日志（不修改）
        
        参数：
        - date_str: 日期字符串（YYYYMMDD），None=今天
        - limit: 返回最近N条
        """
        try:
            log_file = self._get_log_file(date_str)
            if not os.path.exists(log_file):
                return []
            
            logs = []
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        logs.append(json.loads(line))
            
            # 返回最近的N条
            return logs[-limit:] if limit else logs
            
        except Exception as e:
            print(f"[OKX日志] 读取失败: {str(e)}")
            return []

# 初始化交易日志记录器
okx_trading_logger = OKXTradingLogger()

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 导入交易API Blueprint
from trading_api import trading_bp
app.register_blueprint(trading_bp)

# 导入SAR JSONL API
from sar_api_jsonl import get_sar_current_cycle

# 导入Extreme JSONL Manager
from extreme_jsonl_manager import ExtremeJSONLManager

# 导入Price Speed和V1V2 JSONL Manager
from price_speed_jsonl_manager import PriceSpeedJSONLManager
from v1v2_jsonl_manager import V1V2JSONLManager
from crypto_index_jsonl_manager import CryptoIndexJSONLManager

price_speed_manager = PriceSpeedJSONLManager()
v1v2_manager = V1V2JSONLManager(data_dir='/home/user/webapp/data/v1v2_jsonl')
crypto_index_manager = CryptoIndexJSONLManager()

# K线图服务URL配置
CHART_BASE_URL = "https://5000-iz6uddj6rs3xe48ilsyqq-2e1b9533.sandbox.novita.ai"

# ============================================
# 服务器端缓存系统
# ============================================
class ServerCache:
    """服务器端内存缓存，存储计算结果"""
    def __init__(self):
        self.cache = {}
        self.timestamps = {}
        
    def get(self, key, max_age=60):
        """
        获取缓存数据
        key: 缓存键
        max_age: 最大缓存时间（秒），默认60秒
        """
        if key not in self.cache:
            return None
        
        # 检查是否过期
        if time.time() - self.timestamps.get(key, 0) > max_age:
            # 过期，删除缓存
            del self.cache[key]
            del self.timestamps[key]
            return None
        
        return self.cache[key]
    
    def set(self, key, value):
        """设置缓存数据"""
        self.cache[key] = value
        self.timestamps[key] = time.time()
    
    def clear(self, key=None):
        """清除缓存"""
        if key:
            if key in self.cache:
                del self.cache[key]
            if key in self.timestamps:
                del self.timestamps[key]
        else:
            self.cache.clear()
            self.timestamps.clear()
    
    def get_stats(self):
        """获取缓存统计信息"""
        return {
            'total_keys': len(self.cache),
            'keys': list(self.cache.keys())
        }

# 创建全局缓存实例
server_cache = ServerCache()

def cached_response(max_age=60):
    """
    缓存装饰器 - 在服务器端缓存API响应
    max_age: 缓存有效期（秒）
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{f.__name__}:{':'.join(map(str, args))}"
            
            # 尝试从缓存获取
            cached_data = server_cache.get(cache_key, max_age=max_age)
            if cached_data is not None:
                # 创建响应副本并添加缓存标记
                response_data = cached_data.copy()
                response_data['_from_server_cache'] = True
                response_data['_cache_age_seconds'] = int(time.time() - server_cache.timestamps.get(cache_key, 0))
                return jsonify(response_data)
            
            # 执行原函数获取结果
            result = f(*args, **kwargs)
            
            # 提取并缓存JSON数据
            if hasattr(result, 'json') and callable(result.json):
                try:
                    data = result.json
                    if isinstance(data, dict) and data.get('success'):
                        server_cache.set(cache_key, data)
                except:
                    pass
            
            return result
        
        return decorated_function
    return decorator

# 主页面HTML - 完全仿照参考设计
MAIN_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>加密货币数据历史回看</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: #1e2139;
            color: #fff;
            overflow-x: hidden;
        }
        
        .container {
            max-width: 100%;
            margin: 0 auto;
            padding: 0;
        }
        
        /* 顶部导航栏 */
        .top-nav {
            background: #2a2d47;
            padding: 12px 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            justify-content: space-between;
        }
        
        .nav-left {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .nav-right {
            display: flex;
            gap: 10px;
        }
        
        /* 系统导航栏 */
        .systems-nav {
            background: linear-gradient(135deg, #2a2d47 0%, #3a3d5c 100%);
            padding: 15px 20px;
            border-bottom: 2px solid #3b7dff;
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .systems-nav-title {
            font-size: 14px;
            font-weight: 600;
            color: #8b92b8;
            margin-right: 10px;
        }
        
        .system-link {
            background: rgba(59, 125, 255, 0.1);
            border: 1px solid rgba(59, 125, 255, 0.3);
            color: #00d4ff;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        
        .system-link:hover {
            background: rgba(59, 125, 255, 0.2);
            border-color: #3b7dff;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(59, 125, 255, 0.3);
        }
        
        .system-link.featured {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: #fff;
        }
        
        .system-link.featured:hover {
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        }
        
        .home-btn {
            background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
            color: #fff;
            border: none;
            padding: 8px 20px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .home-btn:hover {
            background: linear-gradient(135deg, #0099ff 0%, #00d4ff 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 212, 255, 0.4);
        }
        
        .nav-brand {
            display: flex;
            align-items: center;
            gap: 8px;
            background: #3b7dff;
            padding: 6px 15px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
        }
        
        .nav-title {
            font-size: 18px;
            font-weight: 500;
            color: #fff;
            margin-left: 10px;
        }
        
        /* 控制栏 */
        .control-bar {
            background: #2a2d47;
            padding: 15px 20px;
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
            border-bottom: 1px solid #3a3d5c;
        }
        
        .control-group {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .control-label {
            color: #8b92b8;
            font-size: 13px;
        }
        
        .control-input {
            background: #1e2139;
            border: 1px solid #3a3d5c;
            color: #fff;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 13px;
            outline: none;
        }
        
        .control-input:focus {
            border-color: #3b7dff;
        }
        
        .control-btn {
            background: #3b7dff;
            border: none;
            color: white;
            padding: 7px 18px;
            border-radius: 4px;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .control-btn:hover {
            background: #2563eb;
        }
        
        .control-btn.secondary {
            background: #4a5178;
        }
        
        .control-btn.secondary:hover {
            background: #5a6188;
        }
        
        /* 数据统计栏 */
        .stats-bar {
            background: #2a2d47;
            padding: 12px 20px;
            display: flex;
            gap: 25px;
            flex-wrap: wrap;
            border-bottom: 1px solid #3a3d5c;
            font-size: 13px;
        }
        
        .stat-item {
            display: flex;
            gap: 5px;
        }
        
        .stat-label {
            color: #8b92b8;
        }
        
        .stat-value {
            color: #fff;
            font-weight: 500;
            margin-left: 8px;
        }
        
        .stat-value.rise {
            color: #10b981;
        }
        
        .stat-value.fall {
            color: #ef4444;
        }
        
        /* 次级统计栏 */
        .secondary-stats {
            background: #1e2139;
            padding: 10px 20px;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            font-size: 13px;
        }
        
        /* 时间轴容器 - 竖直布局 */
        .timeline-container {
            background: #2a2d47;
            padding: 15px 20px;
            border-top: 1px solid #3a3d5c;
            max-height: 500px;  /* 增加高度以显示更多信息 */
            overflow-y: auto;
        }
        
        .timeline-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            position: sticky;
            top: 0;
            background: #2a2d47;
            padding-bottom: 10px;
            border-bottom: 1px solid #3a3d5c;
        }
        
        .timeline-title {
            color: #8b92b8;
            font-size: 13px;
            font-weight: 500;
        }
        
        .timeline-info {
            color: #3b7dff;
            font-size: 12px;
        }
        
        /* 竖直时间轴轨道 */
        .timeline-track {
            position: relative;
            padding-left: 30px;
            margin-top: 10px;
        }
        
        /* 竖直线 */
        .timeline-line {
            position: absolute;
            left: 15px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #3a3d5c;
        }
        
        /* 竖直排列的时间点容器 */
        .timeline-points {
            display: flex;
            flex-direction: column;
            gap: 20px;  /* 增加间距以容纳更多信息 */
        }
        
        /* 时间点项 */
        .timeline-point {
            position: relative;
            display: flex;
            align-items: flex-start;  /* 改为顶部对齐，适应多行内容 */
            cursor: pointer;
            padding: 10px 12px;  /* 增加padding */
            border-radius: 4px;
            transition: all 0.3s;
            min-height: 80px;  /* 最小高度确保显示多行信息 */
        }
        
        .timeline-point:hover {
            background: rgba(59, 125, 255, 0.1);
        }
        
        /* 时间点圆圈 */
        .timeline-point::before {
            content: '';
            position: absolute;
            left: -22px;
            width: 12px;
            height: 12px;
            background: #3b7dff;
            border: 2px solid #2a2d47;
            border-radius: 50%;
            transition: all 0.3s;
            z-index: 2;
        }
        
        .timeline-point:hover::before {
            width: 16px;
            height: 16px;
            left: -24px;
            background: #2563eb;
            box-shadow: 0 0 10px rgba(59, 125, 255, 0.5);
        }
        
        .timeline-point.active::before {
            background: #10b981;
            width: 16px;
            height: 16px;
            left: -24px;
            box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
        }
        
        /* 时间标签 */
        .timeline-label {
            color: #8b92b8;
            font-size: 12px;
            display: flex;
            flex-direction: column;
            gap: 2px;
        }
        
        .timeline-point:hover .timeline-label {
            color: #fff;
        }
        
        .timeline-point.active .timeline-label {
            color: #10b981;
            font-weight: 500;
        }
        
        .timeline-label-time {
            font-size: 13px;
            font-weight: 500;
        }
        
        .timeline-label-stats {
            font-size: 11px;
            opacity: 0.85;
            line-height: 1.5;
            color: #a0aec0;
            max-width: 600px;  /* 限制最大宽度 */
        }
        
        .timeline-label-stats div {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        /* 图表区域 */
        .chart-section {
            background: #2a2d47;
            margin: 0;
            padding: 20px;
        }
        
        .chart-title {
            color: #8b92b8;
            font-size: 14px;
            margin-bottom: 15px;
            text-align: center;
        }
        
        #mainChart {
            width: 100%;
            height: 450px;  /* 增加高度，让图表更清晰 */
        }
        
        /* 数据列表标题 */
        .data-list-header {
            background: #2a2d47;
            padding: 12px 20px;
            color: #3b7dff;
            font-size: 14px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        /* 表格容器 */
        .table-container {
            background: #1e2139;
            overflow-x: auto;
        }
        
        /* 数据表格 */
        .data-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
        }
        
        .data-table thead {
            background: #ef4444;
            position: sticky;
            top: 0;
            z-index: 10;
        }
        
        .data-table th {
            padding: 10px 8px;
            text-align: center;
            font-weight: 500;
            color: #fff;
            border-right: 1px solid #dc2626;
            white-space: nowrap;
        }
        
        .data-table tbody tr {
            border-bottom: 1px solid #2a2d47;
        }
        
        .data-table tbody tr:hover {
            background: #2a2d47;
        }
        
        .data-table td {
            padding: 8px 6px;
            text-align: center;
            border-right: 1px solid #2a2d47;
            white-space: nowrap;
        }
        
        /* 操作列 */
        .action-btn {
            background: #ef4444;
            border: none;
            color: white;
            padding: 4px 10px;
            border-radius: 3px;
            font-size: 11px;
            cursor: pointer;
            font-weight: 500;
        }
        
        .action-btn:hover {
            background: #dc2626;
        }
        
        /* 币种名称 */
        .coin-symbol {
            font-weight: 600;
            color: #fff;
        }
        
        /* 数值颜色 */
        .value-positive {
            color: #ef4444;
        }
        
        .value-negative {
            color: #10b981;
        }
        
        .value-neutral {
            color: #8b92b8;
        }
        
        /* 状态标签 */
        .status-tag {
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
        }
        
        .status-tag.rise {
            background: #dc2626;
            color: white;
        }
        
        .status-tag.fall {
            background: #10b981;
            color: white;
        }
        
        /* 优先级颜色 */
        .priority-1 { color: #ff0000; font-weight: bold; }
        .priority-2 { color: #ff6600; font-weight: bold; }
        .priority-3 { color: #ff9900; }
        .priority-4 { color: #ffcc00; }
        .priority-5 { color: #99cc00; }
        .priority-6 { color: #8b92b8; }
        
        /* 加载状态 */
        .loading {
            text-align: center;
            padding: 40px;
            color: #8b92b8;
            font-size: 14px;
        }
        
        /* 响应式 */
        @media (max-width: 768px) {
            .control-bar {
                flex-direction: column;
                align-items: stretch;
            }
            
            .stats-bar {
                flex-direction: column;
                gap: 10px;
            }
            
            .data-table {
                font-size: 11px;
            }
            
            .data-table th,
            .data-table td {
                padding: 6px 4px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 顶部导航 -->
        <div class="top-nav">
            <div class="nav-left">
                <div class="nav-brand">
                    <span>📊</span> 数据回看
                </div>
                <div class="nav-title">加密货币数据历史回看</div>
            </div>
            <div class="nav-right">
                <button class="home-btn" onclick="window.location.href='/'">
                    <span>🏠</span> 返回首页
                </button>
            </div>
        </div>
        
        <!-- 系统导航栏 -->
        <div class="systems-nav">
            <div class="systems-nav-title">快速访问:</div>
            <a href="/sar-slope" class="system-link featured">
                <span>📈</span> SAR斜率系统
            </a>
            <a href="/kline-indicators" class="system-link">
                <span>📊</span> K线指标系统
            </a>
            <a href="/support-resistance" class="system-link">
                <span>📉</span> 支撑阻力系统
            </a>
            <a href="/position-system" class="system-link">
                <span>💼</span> 仓位系统
            </a>
            <a href="/gdrive-monitor-status" class="system-link">
                <span>☁️</span> Google Drive监控
            </a>
            <a href="/crypto-index" class="system-link">
                <span>📈</span> 指数系统
            </a>
            <a href="/coin-pool" class="system-link">
                <span>🏊</span> 币池系统
            </a>
            <a href="/price-comparison" class="system-link">
                <span>💱</span> 比价系统
            </a>
            <a href="/fund-monitor" class="system-link featured">
                <span>💰</span> 资金监控系统
            </a>
        </div>
        
        <!-- 控制栏 -->
        <div class="control-bar">
            <div class="control-group">
                <span class="control-label">选项日期:</span>
                <input type="date" id="queryDate" class="control-input">
            </div>
            
            <div class="control-group">
                <span class="control-label">时间选择:</span>
                <input type="time" id="queryTime" class="control-input" value="00:00">
            </div>
            
            <div class="control-group">
                <span class="control-label">至</span>
                <input type="time" id="endTime" class="control-input" value="23:59">
            </div>
            
            <button class="control-btn" onclick="queryData()">🔍 查询</button>
            <button class="control-btn secondary" onclick="loadToday()">📊 今天</button>
            <button class="control-btn secondary" onclick="loadLatest()">📡 立即加载</button>
            <button class="control-btn secondary" onclick="batchImportData()" id="batchImportBtn">📥 批量导入今日数据</button>
        </div>
        
        <!-- 主要统计栏 -->
        <div class="stats-bar">
            <div class="stat-item">
                <span class="stat-label">运算时间:</span>
                <span class="stat-value" id="calcTime">2025-12-06 13:42:42</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">急涨:</span>
                <span class="stat-value rise" id="rushUp">1</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">急跌:</span>
                <span class="stat-value fall" id="rushDown">22</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">本轮急涨:</span>
                <span class="stat-value" id="roundRushUp">1</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">本轮急跌:</span>
                <span class="stat-value" id="roundRushDown">22</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">计次:</span>
                <span class="stat-value" id="countTimes">10</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">计次得分:</span>
                <span class="stat-value" id="countScore">☆☆☆</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">状态:</span>
                <span class="stat-value" id="status">震荡无序</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">比值:</span>
                <span class="stat-value" id="ratio">10</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">差值:</span>
                <span class="stat-value" id="diff">-21</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">比价最低:</span>
                <span class="stat-value" id="priceLowest">0</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">比价创新高:</span>
                <span class="stat-value" id="priceNewhigh">0</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">24h涨≥10%:</span>
                <span class="stat-value rise" id="rise24hCount">0</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">24h跌≤-10%:</span>
                <span class="stat-value fall" id="fall24hCount">0</span>
            </div>

        </div>
        
        <!-- 次级统计栏 -->
        <div class="secondary-stats">
            <div class="stat-item">
                <span class="stat-label">已回调历史: 无</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">回调天数: 168 秒/0次</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">时间偏限: 2025-12-04 10:22:00 ~ 2025-12-04 18:32:00</span>
            </div>
        </div>
        
        <!-- 图表区域 -->
        <div class="chart-section">
            <div class="chart-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div class="chart-title">急涨/急跌历史趋势图</div>
                <div class="chart-pagination" style="display: flex; gap: 10px; align-items: center;">
                    <span id="chartTimeRange" style="color: #8b92b8; font-size: 12px;"></span>
                    <button id="btnPrevPage" class="page-btn" style="padding: 5px 12px; background: #3a3d5c; color: #8b92b8; border: 1px solid #4a4d6c; border-radius: 4px; cursor: pointer;" disabled>
                        ◀ 上一页
                    </button>
                    <span id="chartPageInfo" style="color: #8b92b8; font-size: 12px;">第1页</span>
                    <button id="btnNextPage" class="page-btn" style="padding: 5px 12px; background: #3a3d5c; color: #8b92b8; border: 1px solid #4a4d6c; border-radius: 4px; cursor: pointer;" disabled>
                        下一页 ▶
                    </button>
                </div>
            </div>
            <div id="mainChart"></div>
        </div>
        
        <!-- 时间轴 - 放在图表下方 -->
        <div class="timeline-container">
            <div class="timeline-header">
                <span class="timeline-title">历史数据时间轴</span>
                <span class="timeline-info" id="timelineInfo">加载中...</span>
            </div>
            <div class="timeline-track">
                <div class="timeline-line"></div>
                <div id="timelinePoints" class="timeline-points"></div>
            </div>
        </div>
        
        <!-- 数据列表标题 -->
        <div class="data-list-header">
            <span>📋</span> 币列表
        </div>
        
        <!-- 数据表格 -->
        <div class="table-container">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>优先级</th>
                        <th>序号</th>
                        <th>币名</th>
                        <th>涨速</th>
                        <th>急涨</th>
                        <th>急跌</th>
                        <th>更新时间</th>
                        <th>历史高点</th>
                        <th>高点时间</th>
                        <th>跌幅</th>
                        <th>24h%</th>
                        <th>排行</th>
                        <th>当前价格</th>
                        <th>最高占比</th>
                        <th>最低占比</th>
                    </tr>
                </thead>
                <tbody id="dataTableBody">
                    <tr>
                        <td colspan="15" class="loading">正在加载数据...</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // 初始化图表
        const chart = echarts.init(document.getElementById('mainChart'));
        
        // 初始化日期
        const today = new Date();
        document.getElementById('queryDate').valueAsDate = today;
        
        // 图表配置
        function updateChart(data) {
            const option = {
                backgroundColor: 'transparent',
                grid: {
                    left: '50px',
                    right: '50px',
                    bottom: '120px',  // 增加底部空间给旋转的横轴标签
                    top: '50px',
                    containLabel: true
                },
                tooltip: {
                    trigger: 'axis',  // 改为axis触发，显示同一时间点所有数据
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    borderColor: '#3a3d5c',
                    borderWidth: 1,
                    textStyle: { color: '#fff', fontSize: 12 },
                    axisPointer: {
                        type: 'cross',
                        crossStyle: {
                            color: '#8b92b8'
                        }
                    },
                    formatter: function(params) {
                        if (!params || params.length === 0) return '';
                        const time = params[0].axisValue;
                        let html = `<div style="padding: 8px;">
                            <div style="font-weight: bold; margin-bottom: 8px; font-size: 13px; border-bottom: 1px solid #3a3d5c; padding-bottom: 5px;">${time}</div>`;
                        
                        params.forEach(item => {
                            html += `<div style="margin-top: 5px; display: flex; align-items: center; justify-content: space-between; gap: 15px;">
                                <span style="display: flex; align-items: center;">
                                    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background-color: ${item.color}; margin-right: 8px;"></span>
                                    ${item.seriesName}
                                </span>
                                <span style="color: ${item.color}; font-weight: bold;">${item.value}</span>
                            </div>`;
                        });
                        
                        html += '</div>';
                        return html;
                    }
                },
                legend: {
                    data: ['急涨', '急跌', '差值(急涨-急跌)', '计次'],
                    top: 10,
                    left: 'center',
                    textStyle: { color: '#8b92b8', fontSize: 13 },
                    itemWidth: 30,
                    itemHeight: 14,
                    itemGap: 20
                },
                xAxis: {
                    type: 'category',
                    data: data.times || [],
                    axisLine: { 
                        lineStyle: { color: '#3a3d5c', width: 1 }
                    },
                    axisLabel: { 
                        color: '#8b92b8',
                        fontSize: 10,
                        rotate: 45,  // 旋转45度，避免重叠
                        interval: 0,  // 显示所有标签
                        margin: 12,
                        align: 'right',  // 右对齐
                        verticalAlign: 'middle'
                    },
                    axisTick: {
                        show: true,
                        lineStyle: { color: '#3a3d5c' }
                    },
                    splitLine: { 
                        show: true,  // 显示分隔线
                        lineStyle: {
                            color: '#3a3d5c',
                            type: 'solid',  // 实线
                            width: 1,
                            opacity: 0.3
                        }
                    }
                },
                yAxis: [
                    {
                        type: 'value',
                        name: '数量',
                        nameTextStyle: { 
                            color: '#8b92b8', 
                            fontSize: 12,
                            padding: [0, 0, 0, 10]
                        },
                        axisLine: { 
                            show: true,
                            lineStyle: { color: '#3a3d5c' } 
                        },
                        axisLabel: { 
                            color: '#8b92b8', 
                            fontSize: 11 
                        },
                        splitLine: { 
                            lineStyle: { 
                                color: '#3a3d5c', 
                                type: 'dashed',
                                opacity: 0.5
                            } 
                        }
                    },
                    {
                        type: 'value',
                        name: '计次',
                        nameTextStyle: { 
                            color: '#3b7dff', 
                            fontSize: 12,
                            padding: [0, 10, 0, 0]
                        },
                        axisLine: { 
                            show: true,
                            lineStyle: { color: '#3a3d5c' } 
                        },
                        axisLabel: { 
                            color: '#3b7dff', 
                            fontSize: 11 
                        },
                        splitLine: { show: false }
                    }
                ],
                series: [
                    {
                        name: '急涨',
                        type: 'line',
                        data: data.rush_up || [],
                        smooth: true,
                        connectNulls: true,  // 连接所有数据点，形成连续线段
                        lineStyle: {
                            width: 3,
                            color: '#ef4444'
                        },
                        itemStyle: { 
                            color: '#ef4444',
                            borderColor: '#fff',
                            borderWidth: 2
                        },
                        symbolSize: 8,
                        emphasis: {
                            scale: true,
                            scaleSize: 12
                        },
                        // 添加日期分隔线
                        markLine: {
                            silent: true,
                            symbol: 'none',
                            label: {
                                show: false
                            },
                            lineStyle: {
                                color: '#6366f1',
                                type: 'solid',
                                width: 2,
                                opacity: 0.6
                            },
                            data: (data.date_separators || []).map(sep => ({
                                xAxis: sep.index,
                                label: {
                                    show: true,
                                    position: 'insideEndTop',
                                    formatter: sep.date,
                                    color: '#6366f1',
                                    fontSize: 10,
                                    fontWeight: 'bold',
                                    backgroundColor: 'rgba(30, 31, 46, 0.8)',
                                    padding: [2, 6],
                                    borderRadius: 3
                                }
                            }))
                        }
                    },
                    {
                        name: '急跌',
                        type: 'line',
                        data: data.rush_down || [],
                        smooth: true,
                        connectNulls: true,  // 连接所有数据点，形成连续线段
                        lineStyle: {
                            width: 3,
                            color: '#10b981'
                        },
                        itemStyle: { 
                            color: '#10b981',
                            borderColor: '#fff',
                            borderWidth: 2
                        },
                        symbolSize: 8,
                        emphasis: {
                            scale: true,
                            scaleSize: 12
                        }
                    },
                    {
                        name: '差值(急涨-急跌)',
                        type: 'line',
                        data: data.diff || [],
                        smooth: true,
                        connectNulls: true,  // 连接所有数据点，形成连续线段
                        lineStyle: {
                            width: 3,
                            color: '#fbbf24'
                        },
                        itemStyle: { 
                            color: '#fbbf24',
                            borderColor: '#fff',
                            borderWidth: 2
                        },
                        symbolSize: 8,
                        emphasis: {
                            scale: true,
                            scaleSize: 12
                        }
                    },
                    {
                        name: '计次',
                        type: 'line',
                        yAxisIndex: 1,
                        data: data.count || [],
                        smooth: true,
                        connectNulls: true,  // 连接所有数据点，形成连续线段
                        lineStyle: {
                            width: 3,
                            color: '#3b7dff'
                        },
                        itemStyle: { 
                            color: '#3b7dff',
                            borderColor: '#fff',
                            borderWidth: 2
                        },
                        symbolSize: 8,
                        emphasis: {
                            scale: true,
                            scaleSize: 12
                        }
                    }
                ]
            };
            
            chart.setOption(option);
        }
        
        // 查询数据
        function queryData() {
            const date = document.getElementById('queryDate').value;
            const time = document.getElementById('queryTime').value;
            const datetime = date + ' ' + time;
            
            fetch('/api/query?time=' + encodeURIComponent(datetime))
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('❌ ' + data.error);
                        return;
                    }
                    updateUI(data);
                    loadChartData();  // 加载所有历史数据趋势图
                })
                .catch(error => {
                    alert('查询失败: ' + error);
                });
        }
        
        // 加载今天
        function loadToday() {
            const today = new Date();
            document.getElementById('queryDate').valueAsDate = today;
            queryData();
        }
        
        // 加载最新
        function loadLatest() {
            fetch('/api/latest')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('❌ ' + data.error);
                        return;
                    }
                    updateUI(data);
                    loadChartData();  // 加载所有历史数据趋势图
                })
                .catch(error => {
                    alert('加载失败: ' + error);
                });
        }
        
        // 批量导入今日数据
        function batchImportData() {
            const btn = document.getElementById('batchImportBtn');
            const originalText = btn.innerHTML;
            
            // 禁用按钮并显示加载状态
            btn.disabled = true;
            btn.innerHTML = '⏳ 正在批量导入...';
            btn.style.opacity = '0.6';
            btn.style.cursor = 'not-allowed';
            
            fetch('/api/query/batch-import', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const stats = data.stats;
                    let message = `✅ 批量导入完成！\n\n`;
                    message += `📊 统计结果：\n`;
                    message += `   总文件数: ${stats.total}\n`;
                    message += `   ✅ 成功导入: ${stats.success}\n`;
                    message += `   ℹ️  已存在: ${stats.exists}\n`;
                    if (stats.invalid > 0) {
                        message += `   ⚠️  无效数据: ${stats.invalid}\n`;
                    }
                    if (stats.error > 0) {
                        message += `   ❌ 失败: ${stats.error}\n`;
                    }
                    
                    alert(message);
                    
                    // 如果有新数据导入，则刷新页面数据
                    if (stats.success > 0) {
                        loadToday();
                    }
                } else {
                    alert('❌ 批量导入失败: ' + data.error);
                }
            })
            .catch(error => {
                alert('❌ 批量导入失败: ' + error);
            })
            .finally(() => {
                // 恢复按钮状态
                btn.disabled = false;
                btn.innerHTML = originalText;
                btn.style.opacity = '1';
                btn.style.cursor = 'pointer';
            });
        }
        
        // 更新次级统计栏
        function updateSecondaryStats() {
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    if (!data.error) {
                        // 更新次级统计栏内容
                        const secondaryStats = document.querySelector('.secondary-stats');
                        if (secondaryStats) {
                            // 计算数据时间范围（从data_days推算）
                            const today = new Date();
                            const startDate = new Date(today);
                            startDate.setDate(startDate.getDate() - (data.data_days - 1));
                            
                            const dateRangeStr = `${startDate.toISOString().split('T')[0]} ~ ${today.toISOString().split('T')[0]}`;
                            
                            secondaryStats.innerHTML = `
                                <div class="stat-item">
                                    <span class="stat-label">数据时间范围: ${dateRangeStr}</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">总记录: ${data.total_records} 条</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">今日数据: ${data.today_records} 条 | 数据天数: ${data.data_days} 天</span>
                                </div>
                                <div class="stat-item">
                                    <span class="stat-label">最后更新: ${data.last_update_time}</span>
                                </div>
                            `;
                        }
                    }
                })
                .catch(err => {
                    console.error('更新次级统计栏失败:', err);
                });
        }
        
        // 加载涨跌速数据
        function loadPriceSpeedData() {
            fetch('/api/price-speed/latest')
                .then(response => response.json())
                .then(response => {
                    if (response.success && response.data) {
                        const data = response.data;
                        
                        // 统计各级别数量
                        const upCount = data.filter(coin => 
                            coin.alert_level && coin.alert_level.includes('up') && coin.alert_level !== 'normal'
                        ).length;
                        
                        const downCount = data.filter(coin => 
                            coin.alert_level && coin.alert_level.includes('down') && coin.alert_level !== 'normal'
                        ).length;
                        
                        const normalCount = data.filter(coin => 
                            coin.alert_level === 'normal'
                        ).length;
                        
                        // 更新UI (已移除急涨速、急跌速、正常统计)
                    }
                })
                .catch(err => {
                    console.error('加载涨跌速数据失败:', err);
                    // 如果失败，显示默认值 (已移除急涨速、急跌速、正常统计)
                });
        }
        
        // 更新UI
        function updateUI(data) {
            document.getElementById('calcTime').textContent = data.snapshot_time;
            document.getElementById('rushUp').textContent = data.rush_up;
            document.getElementById('rushDown').textContent = data.rush_down;
            document.getElementById('roundRushUp').textContent = data.round_rush_up || data.rush_up;
            document.getElementById('roundRushDown').textContent = data.round_rush_down || data.rush_down;
            // 使用透明标签的计次值（从TXT文件提取的）
            document.getElementById('countTimes').textContent = data.count_aggregate || data.count;
            document.getElementById('countScore').textContent = data.count_score_display || '---';
            document.getElementById('status').textContent = data.status;
            document.getElementById('ratio').textContent = data.ratio;
            document.getElementById('diff').textContent = data.diff;
            document.getElementById('priceLowest').textContent = data.price_lowest || 0;
            document.getElementById('priceNewhigh').textContent = data.price_newhigh || 0;
            document.getElementById('rise24hCount').textContent = data.rise_24h_count || 0;
            document.getElementById('fall24hCount').textContent = data.fall_24h_count || 0;
            
            // 更新次级统计栏
            updateSecondaryStats();
            
            // 加载涨跌速数据
            loadPriceSpeedData();
            
            // 更新表格
            const tbody = document.getElementById('dataTableBody');
            if (data.coins && data.coins.length > 0) {
                let html = '';
                data.coins.forEach((coin, idx) => {
                    const speedClass = coin.speed > 0 ? 'value-positive' : (coin.speed < 0 ? 'value-negative' : 'value-neutral');
                    const change24Class = coin.change_24h > 0 ? 'value-positive' : (coin.change_24h < 0 ? 'value-negative' : 'value-neutral');
                    // priority是数字1-6，priority_name是字符串"等级1"-"等级6"
                    const priority = coin.priority || 999;
                    const priorityName = coin.priority_name || '未知';
                    const priorityClass = 'priority-' + priority;
                    
                    const rushUpTag = coin.rush_up > 0 ? '<span class="status-tag rise">' + coin.rush_up + '</span>' : coin.rush_up;
                    const rushDownTag = coin.rush_down > 0 ? '<span class="status-tag fall">' + coin.rush_down + '</span>' : coin.rush_down;
                    
                    html += '<tr>';
                    html += '<td class="' + priorityClass + '">' + priority + '</td>';
                    html += '<td>' + (idx + 1) + '</td>';
                    html += '<td class="coin-symbol">' + coin.symbol + '</td>';
                    html += '<td class="' + speedClass + '">' + coin.speed.toFixed(2) + '</td>';
                    html += '<td>' + rushUpTag + '</td>';
                    html += '<td>' + rushDownTag + '</td>';
                    html += '<td>' + coin.update_time + '</td>';
                    html += '<td>' + coin.high_price.toFixed(2) + '</td>';
                    html += '<td>' + coin.high_time + '</td>';
                    html += '<td class="value-negative">' + coin.decline.toFixed(2) + '</td>';
                    html += '<td class="' + change24Class + '">' + coin.change_24h.toFixed(2) + '</td>';
                    html += '<td>' + coin.rank + '</td>';
                    html += '<td>' + coin.current_price.toFixed(4) + '</td>';
                    html += '<td>' + (coin.max_ratio ? coin.max_ratio.toFixed(2) + '%' : 'N/A') + '</td>';
                    html += '<td>' + (coin.min_ratio ? coin.min_ratio.toFixed(2) + '%' : 'N/A') + '</td>';
                    html += '</tr>';
                });
                tbody.innerHTML = html;
            } else {
                tbody.innerHTML = '<tr><td colspan="15" class="loading">暂无数据</td></tr>';
            }
        }
        
        // 加载图表数据
        // 当前页码（全局变量）
        let currentPage = 0;
        
        function loadChartData(page = 0) {
            // 加载指定页的历史数据点（12小时/页，显示所有数据点）
            currentPage = page;
            fetch(`/api/chart?page=${page}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error(data.error);
                        return;
                    }
                    updateChart(data);
                    
                    // 更新分页信息
                    document.getElementById('chartPageInfo').textContent = 
                        `第${page + 1}/${data.total_pages}页`;
                    document.getElementById('chartTimeRange').textContent = 
                        `${data.time_range.start} - ${data.time_range.end}`;
                    
                    // 更新按钮状态
                    document.getElementById('btnPrevPage').disabled = !data.has_prev;
                    document.getElementById('btnNextPage').disabled = !data.has_next;
                })
                .catch(error => {
                    console.error('图表加载失败:', error);
                });
        }
        
        // 翻页按钮事件
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('btnPrevPage').addEventListener('click', function() {
                loadChartData(currentPage + 1);  // 上一页（更早的数据）
            });
            
            document.getElementById('btnNextPage').addEventListener('click', function() {
                loadChartData(currentPage - 1);  // 下一页（更新的数据）
            });
        });
        
        // 页面加载时自动加载最新数据
        // 加载时间轴数据 - 竖直布局
        function loadTimeline() {
            fetch('/api/timeline')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        document.getElementById('timelineInfo').textContent = data.error;
                        return;
                    }
                    
                    document.getElementById('timelineInfo').textContent = 
                        `共 ${data.snapshots.length} 个数据点`;
                    
                    const pointsContainer = document.getElementById('timelinePoints');
                    pointsContainer.innerHTML = '';
                    
                    // 时间从上到下：最早的在上面，最新的在下面
                    data.snapshots.forEach((snapshot, index) => {
                        const point = document.createElement('div');
                        point.className = 'timeline-point';
                        point.setAttribute('data-time', snapshot.snapshot_time);
                        
                        // 最后一个（最新的）标记为激活
                        if (index === data.snapshots.length - 1) {
                            point.classList.add('active');
                        }
                        
                        const label = document.createElement('div');
                        label.className = 'timeline-label';
                        
                        // 时间显示
                        const timeSpan = document.createElement('div');
                        timeSpan.className = 'timeline-label-time';
                        timeSpan.textContent = snapshot.snapshot_time;
                        
                        // 统计信息显示 - 显示所有关键字段
                        const statsSpan = document.createElement('div');
                        statsSpan.className = 'timeline-label-stats';
                        
                        // 第一行：急涨、急跌、计次、得分
                        const line1 = `急涨:${snapshot.rush_up} 急跌:${snapshot.rush_down} 计次:${snapshot.count} ${snapshot.count_score_display || ''}`;
                        
                        // 第二行：状态、比值、差值
                        const line2 = `状态:${snapshot.status || ''} 比值:${snapshot.ratio || 0} 差值:${snapshot.diff}`;
                        
                        // 第三行：本轮、比价、24h
                        const line3 = `本轮急涨:${snapshot.round_rush_up || 0} 本轮急跌:${snapshot.round_rush_down || 0} 24h涨≥10%:${snapshot.rise_24h_count || 0} 24h跌≤-10%:${snapshot.fall_24h_count || 0}`;
                        
                        statsSpan.innerHTML = `
                            <div style="margin-bottom: 2px;">${line1}</div>
                            <div style="margin-bottom: 2px;">${line2}</div>
                            <div>${line3}</div>
                        `;
                        
                        label.appendChild(timeSpan);
                        label.appendChild(statsSpan);
                        point.appendChild(label);
                        
                        point.onclick = function() {
                            // 移除所有激活状态
                            document.querySelectorAll('.timeline-point').forEach(p => {
                                p.classList.remove('active');
                            });
                            // 激活当前点
                            this.classList.add('active');
                            // 加载数据
                            loadSnapshotData(snapshot.snapshot_time);
                        };
                        
                        pointsContainer.appendChild(point);
                    });
                })
                .catch(error => {
                    console.error('加载时间轴失败:', error);
                    document.getElementById('timelineInfo').textContent = '加载失败';
                });
        }
        
        // 加载指定快照的数据
        function loadSnapshotData(snapshotTime) {
            fetch('/api/query?time=' + encodeURIComponent(snapshotTime))
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert(data.error);
                        return;
                    }
                    updateUI(data);
                    updateChart(data);
                    
                    // 更新时间轴激活状态
                    document.querySelectorAll('.timeline-point').forEach(point => {
                        point.classList.remove('active');
                    });
                    event.target.classList.add('active');
                })
                .catch(error => console.error('加载数据失败:', error));
        }
        
        window.onload = function() {
            loadLatest();
            loadTimeline();
        };
        
        // 响应式调整
        window.addEventListener('resize', function() {
            chart.resize();
        });
    </script>
</body>
</html>
"""

# API路由保持不变，使用之前的代码
@app.route('/')
def index():
    """首页 - 功能导航"""
    return render_template('index.html')

@app.route('/coin-change-tracker')
def coin_change_tracker_page():
    """27币涨跌幅追踪系统页面"""
    return render_template('coin_change_tracker.html')

@app.route('/query')
def query_page():
    """历史数据查询页面"""
    return render_template_string(MAIN_HTML)

@app.route('/chart')
def chart_page():
    """趋势图表页面"""
    return render_template_string(MAIN_HTML)

@app.route('/query-test')
def query_test():
    """Query页面诊断工具"""
    from flask import send_file
    return send_file('/home/user/webapp/query_test.html')

@app.route('/test-profit-chart')
def test_profit_chart():
    """Profit Chart调试页面"""
    from flask import send_file
    return send_file('/home/user/webapp/test_profit_chart.html')

@app.route('/simple-test')
def simple_test():
    """Simple测试页面"""
    from flask import send_file
    return send_file('/home/user/webapp/simple_test.html')

@app.route('/timeline')
def timeline_page():
    """时间轴页面"""
    return render_template_string(MAIN_HTML)

@app.route('/status')
def status_page():
    """系统状态页面"""
    return render_template('status.html')

@app.route('/panic')
def panic_page():
    """恐慌清洗指数页面"""
    return render_template('panic_new.html')

@app.route('/extreme-tracking')
def extreme_tracking_page():
    """极值追踪系统页面"""
    return render_template('extreme_tracking.html')

@app.route('/api/panic/latest')
def api_panic_latest():
    """恐慌清洗指数最新数据API - 从JSONL读取"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from panic_jsonl_manager import PanicJSONLManager
        
        manager = PanicJSONLManager()
        latest = manager.get_latest('panic_wash_index')
        
        if latest:
            panic_index_percentage = latest.get('panic_index', 0)
            hour_24_people = latest.get('hour_24_people', 0)
            total_position = latest.get('total_position', 0)
            hour_1_amount_usd = latest.get('hour_1_amount', 0)
            hour_24_amount_usd = latest.get('hour_24_amount', 0)
            wash_index = latest.get('wash_index', 0)
            
            # 保留恐慌指数的原始精度（不四舍五入）
            panic_index = panic_index_percentage
            
            # JSONL中的数据已经是标准单位（采集器已转换）：
            # hour_1_amount: 万美元
            # hour_24_amount: 万美元（注意：现在也是万美元，不是亿美元）
            # hour_24_people: 万人
            # total_position: 亿美元
            # 直接使用，只需四舍五入到2位小数
            
            people_wan = round(hour_24_people, 2)
            position_yi = round(total_position, 2)
            hour_1_amount_wan = round(hour_1_amount_usd, 2)
            hour_24_amount_wan = round(hour_24_amount_usd, 2)  # 现在是万美元
            
            # 根据恐慌指数确定等级
            if panic_index_percentage < 5:
                panic_level = '低恐慌'
                level_color = 'green'
            elif panic_index_percentage < 10:
                panic_level = '中度恐慌'
                level_color = 'yellow'
            else:
                panic_level = '高度恐慌'
                level_color = 'red'
            
            return jsonify({
                'success': True,
                'data': {
                    'record_time': latest.get('record_time'),
                    'panic_index': panic_index,
                    'wash_index': wash_index,
                    'panic_level': panic_level,
                    'level_color': level_color,
                    'hour_24_people': people_wan,
                    'total_position': position_yi,
                    'hour_1_amount': hour_1_amount_wan,
                    'hour_24_amount': hour_24_amount_wan,  # 现在是万美元
                    'market_zone': f'{people_wan}万人/{position_yi}亿美元'
                }
            })
        else:
            return jsonify({'success': False, 'error': '暂无数据'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/liquidation-1h/history')
def api_liquidation_1h_history():
    """1小时爆仓金额历史数据API
    
    参数:
        limit: 返回最近N条记录，默认1440（24小时）
        start_time: 开始时间（可选，格式: YYYY-MM-DD HH:MM:SS）
        end_time: 结束时间（可选，格式: YYYY-MM-DD HH:MM:SS）
    """
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from liquidation_1h_manager import Liquidation1HManager
        
        manager = Liquidation1HManager()
        
        # 获取参数
        limit = request.args.get('limit', type=int, default=1440)  # 默认24小时
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        # 获取数据
        if start_time or end_time:
            data = manager.get_range(start_time=start_time, end_time=end_time, limit=limit)
        else:
            # 获取最新N条
            all_data = manager.get_range(limit=limit)
            data = all_data
        
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/liquidation-1h/latest')
def api_liquidation_1h_latest():
    """1小时爆仓金额最新数据API"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from liquidation_1h_manager import Liquidation1HManager
        
        manager = Liquidation1HManager()
        data = manager.get_latest(limit=1)
        
        if data:
            return jsonify({
                'success': True,
                'data': data[0]
            })
        else:
            return jsonify({'success': False, 'error': '暂无数据'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stats')
def api_stats():
    """统计数据API - 从JSONL读取"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        sys.path.insert(0, '/home/user/webapp')
        from gdrive_jsonl_manager import GDriveJSONLManager
        from aggregate_jsonl_manager import AggregateJSONLManager
        
        manager = GDriveJSONLManager()
        agg_manager = AggregateJSONLManager('/home/user/webapp/data/gdrive_jsonl')
        
        # 获取所有快照
        all_snapshots = manager.read_all_snapshots()
        all_aggregates = agg_manager.load_all_aggregates()
        
        # 总记录数
        total_records = len(all_snapshots)
        
        # 今日记录数
        today = datetime.now(BEIJING_TZ).date().strftime('%Y-%m-%d')
        today_records = len([s for s in all_snapshots if s.get('snapshot_date', '') == today])
        
        # 数据天数（从快照中统计唯一日期）
        unique_dates = set(s.get('snapshot_date', '') for s in all_snapshots if s.get('snapshot_date'))
        data_days = len(unique_dates)
        
        # 获取最新聚合数据
        latest_aggregate = agg_manager.get_latest_aggregate()
        
        # 获取最新两条聚合记录用于计算本轮差值
        if len(all_aggregates) >= 2:
            sorted_aggregates = sorted(all_aggregates, key=lambda x: x.get('snapshot_time', ''), reverse=True)
            latest_records = sorted_aggregates[:2]
        else:
            latest_records = all_aggregates
        
        last_update_time = '-'
        current_round_rush_up = 0
        current_round_rush_down = 0
        
        if latest_aggregate:
            # 从最新聚合数据获取时间
            time_str = latest_aggregate.get('snapshot_time', '')
            if time_str and ' ' in time_str:
                last_update_time = time_str.split(' ')[1][:5]  # 提取 HH:MM
            
            # 计算本轮差值（如果有两条记录）
            if len(latest_records) >= 2:
                current_rush_up = latest_records[0].get('rush_up_total', 0)
                current_rush_down = latest_records[0].get('rush_down_total', 0)
                prev_rush_up = latest_records[1].get('rush_up_total', 0)
                prev_rush_down = latest_records[1].get('rush_down_total', 0)
                
                current_round_rush_up = current_rush_up - prev_rush_up
                current_round_rush_down = current_rush_down - prev_rush_down
        
        # 获取恐慌清洗指数（从JSONL读取）
        try:
            from panic_jsonl_manager import PanicJSONLManager
            panic_manager = PanicJSONLManager()
            panic_latest = panic_manager.get_latest('panic_wash_index')
        except:
            panic_latest = None
        
        panic_indicator = '-'
        panic_color = 'gray'
        panic_trend_rating = 0
        panic_market_zone = '-'
        panic_people_wan = 0
        panic_position_yi = 0
        
        if panic_latest:
            panic_indicator = panic_latest.get('panic_index', 0)
            panic_people_wan = round(panic_latest.get('hour_24_people', 0) / 10000, 2)
            panic_position_yi = round(panic_latest.get('total_position', 0) / 100000000, 2)
            
            # 根据恐慌指数设置颜色
            if panic_indicator < 5:
                panic_color = '绿'  # 低恐慌（<5%）
            elif panic_indicator < 10:
                panic_color = '黄'  # 中恐慌（5-10%）
            else:
                panic_color = '红'  # 高恐慌（>10%）
            
            # 市场区间描述
            panic_market_zone = f"{panic_people_wan}万人/{panic_position_yi}亿美元"
        
        return jsonify({
            'total_records': total_records,
            'today_records': today_records,
            'data_days': data_days,
            'last_update_time': last_update_time,
            'current_round_rush_up': current_round_rush_up,
            'current_round_rush_down': current_round_rush_down,
            'panic_indicator': panic_indicator,
            'panic_color': panic_color,
            'panic_trend_rating': panic_trend_rating,
            'panic_market_zone': panic_market_zone
        })
    except Exception as e:
        return jsonify({
            'total_records': 0,
            'today_records': 0,
            'data_days': 0,
            'last_update_time': '-',
            'current_round_rush_up': 0,
            'current_round_rush_down': 0,
            'panic_indicator': '-',
            'panic_color': 'gray',
            'panic_trend_rating': 0,
            'panic_market_zone': '-',
            'error': str(e)
        })

@app.route('/api/homepage/summary')
def api_homepage_summary():
    """首页聚合数据API - 一次返回所有首页需要的数据"""
    try:
        result = {
            'success': True,
            'timestamp': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 1. 统计栏数据（本轮急涨急跌和恐慌指数）
        cursor.execute("SELECT COUNT(*) FROM crypto_snapshots")
        total_records = cursor.fetchone()[0]
        
        today = datetime.now(BEIJING_TZ).date().strftime('%Y-%m-%d')
        cursor.execute("SELECT COUNT(*) FROM crypto_snapshots WHERE snapshot_date = ?", (today,))
        today_records = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT snapshot_time, rush_up, rush_down
            FROM crypto_snapshots
            ORDER BY snapshot_date DESC, snapshot_time DESC
            LIMIT 2
        """)
        latest_records = cursor.fetchall()
        
        last_update_time = '-'
        current_round_rush_up = 0
        current_round_rush_down = 0
        
        if latest_records and len(latest_records) >= 1:
            time_str = latest_records[0][0]
            if time_str and ' ' in time_str:
                last_update_time = time_str.split(' ')[1][:5]
            current_rush_up = latest_records[0][1]
            current_rush_down = latest_records[0][2]
            
            if len(latest_records) >= 2:
                prev_rush_up = latest_records[1][1]
                prev_rush_down = latest_records[1][2]
                current_round_rush_up = current_rush_up - prev_rush_up
                current_round_rush_down = current_rush_down - prev_rush_down
        
        cursor.execute("""
            SELECT panic_index, hour_24_people, total_position
            FROM panic_wash_index
            ORDER BY record_time DESC
            LIMIT 1
        """)
        panic_data = cursor.fetchone()
        
        panic_indicator = '-'
        panic_color = 'gray'
        panic_market_zone = '-'
        
        if panic_data:
            panic_indicator = panic_data[0]
            panic_people_wan = round(panic_data[1] / 10000, 2)
            panic_position_yi = round(panic_data[2] / 100000000, 2)
            
            if panic_indicator < 5:
                panic_color = '绿'
            elif panic_indicator < 10:
                panic_color = '黄'
            else:
                panic_color = '红'
            
            panic_market_zone = f"{panic_people_wan}万人/{panic_position_yi}亿美元"
        
        result['stats'] = {
            'total_records': total_records,
            'today_records': today_records,
            'last_update_time': last_update_time,
            'current_round_rush_up': current_round_rush_up,
            'current_round_rush_down': current_round_rush_down,
            'panic_indicator': panic_indicator,
            'panic_color': panic_color,
            'panic_market_zone': panic_market_zone
        }
        
        # 2. 模块统计数据
        cursor.execute("SELECT MIN(snapshot_date), MAX(snapshot_date) FROM crypto_snapshots")
        date_range = cursor.fetchone()
        data_days = 0
        if date_range and date_range[0] and date_range[1]:
            data_days = (datetime.strptime(date_range[1], '%Y-%m-%d') - 
                        datetime.strptime(date_range[0], '%Y-%m-%d')).days + 1
        
        cursor.execute("SELECT MAX(snapshot_time) FROM crypto_snapshots")
        last_snapshot = cursor.fetchone()
        last_update = last_snapshot[0] if last_snapshot else '-'
        
        result['modules_stats'] = {
            'query_module': {
                'total_records': total_records,
                'data_days': data_days,
                'last_update': last_update
            }
        }
        
        # 3. 价格突破统计（创新高/创新低）
        cursor.execute("""
            SELECT event_type, COUNT(*) 
            FROM price_breakthrough_events 
            WHERE DATE(event_time) = ?
            GROUP BY event_type
        """, (today,))
        breakthrough_today = dict(cursor.fetchall())
        
        result['price_breakthrough'] = {
            'today': {
                'new_high': breakthrough_today.get('new_high', 0),
                'new_low': breakthrough_today.get('new_low', 0)
            }
        }
        
        # 4. V1V2成交系统数据（从实际API获取或占位）
        # 暂时使用占位数据，后续可以调用原有的v1v2 API
        result['v1v2_system'] = {
            'v1_count': 0,
            'v2_count': 0,
            'update_time': last_update
        }
        
        # 5. 支撑压力线系统数据
        cursor.execute("""
            SELECT 
                symbol, 
                alert_scenario_1, alert_scenario_2, alert_scenario_3, alert_scenario_4,
                position_s2_r1, position_s1_r2, position_s1_r1
            FROM support_resistance_levels
            WHERE record_time = (SELECT MAX(record_time) FROM support_resistance_levels)
        """)
        sr_data = cursor.fetchall()
        
        scenario1_coins = []
        scenario2_coins = []
        scenario3_coins = []
        scenario4_coins = []
        
        for row in sr_data:
            symbol, s1, s2, s3, s4, pos_s2_r1, pos_s1_r2, pos_s1_r1 = row
            coin_symbol = symbol.replace('USDT', '')
            
            if s1:
                scenario1_coins.append({'symbol': coin_symbol, 'position': pos_s2_r1})
            if s2:
                scenario2_coins.append({'symbol': coin_symbol, 'position': pos_s1_r2})
            if s3:
                scenario3_coins.append({'symbol': coin_symbol, 'position': pos_s1_r2})
            if s4:
                scenario4_coins.append({'symbol': coin_symbol, 'position': pos_s1_r1})
        
        result['support_resistance'] = {
            'total_count': len(sr_data),
            'scenario1_coins': scenario1_coins,
            'scenario2_coins': scenario2_coins,
            'scenario3_coins': scenario3_coins,
            'scenario4_coins': scenario4_coins,
            'update_time': last_update
        }
        
        # 6. 交易信号系统数据
        # 简化版本，返回基本计数
        result['trading_signals'] = {
            'buy_point_1_count': 0,
            'buy_point_2_count': 0,
            'total_coins': 27,
            'update_time': last_update
        }
        
        # 7. 1分钟涨跌速数据（占位，需要实际数据源）
        result['price_speed'] = {
            'up_count': 0,
            'down_count': 0,
            'update_time': last_update
        }
        
        # 8. 监控状态
        cursor.execute("""
            SELECT snapshot_time 
            FROM crypto_snapshots 
            ORDER BY snapshot_date DESC, snapshot_time DESC 
            LIMIT 1
        """)
        latest_snapshot_row = cursor.fetchone()
        latest_snapshot_time = latest_snapshot_row[0] if latest_snapshot_row else None
        
        need_collection = False
        minutes_since_last = None
        
        if latest_snapshot_time:
            latest_dt = datetime.strptime(latest_snapshot_time, '%Y-%m-%d %H:%M:%S')
            latest_dt = BEIJING_TZ.localize(latest_dt)
            now = datetime.now(BEIJING_TZ)
            minutes_since_last = (now - latest_dt).total_seconds() / 60
            
            if minutes_since_last > 15:
                need_collection = True
        
        result['monitor_status'] = {
            'need_collection': need_collection,
            'latest_snapshot': latest_snapshot_time,
            'minutes_since_last': round(minutes_since_last, 1) if minutes_since_last else None
        }
        
        # 9. Google Drive检测器状态（占位）
        result['gdrive_detector'] = {
            'detector_running': False,
            'file_timestamp': None,
            'delay_minutes': None,
            'latest_file': None
        }
        
        conn.close()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        })

@app.route('/api/query')
def api_query():
    """查询API - 使用GDrive JSONL数据源"""
    query_time = request.args.get('time', '')
    if not query_time:
        return jsonify({'error': '请提供查询时间'})
    
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        sys.path.insert(0, '/home/user/webapp')
        from gdrive_jsonl_manager import GDriveJSONLManager
        from aggregate_jsonl_manager import AggregateJSONLManager
        
        # 使用GDrive JSONL管理器
        manager = GDriveJSONLManager()
        agg_manager = AggregateJSONLManager('/home/user/webapp/data/gdrive_jsonl')
        
        # 获取该时间点的所有币种数据
        all_snapshots = manager.read_all_snapshots()
        coins = [s for s in all_snapshots if s.get('snapshot_time') == query_time]
        
        if not coins:
            return jsonify({'error': f'未找到 {query_time} 的数据'})
        
        # 尝试获取聚合数据
        aggregate_data = agg_manager.get_aggregate_by_time(query_time)
        
        if aggregate_data:
            # 使用聚合数据
            rush_up = aggregate_data.get('rush_up_total', 0)
            rush_down = aggregate_data.get('rush_down_total', 0)
            diff = aggregate_data.get('diff_total', 0)
            ratio = aggregate_data.get('ratio', 0)
            status = aggregate_data.get('status', '')
            count_aggregate = aggregate_data.get('count_aggregate', 0)
            count_score_display = aggregate_data.get('count_score_display', '')
            count_score_type = aggregate_data.get('count_score_type', '')
            price_lowest = aggregate_data.get('price_lowest', 0)
            price_newhigh = aggregate_data.get('price_newhigh', 0)
        else:
            # 回退到累加计算
            rush_up = sum(c.get('rush_up', 0) or 0 for c in coins)
            rush_down = sum(c.get('rush_down', 0) or 0 for c in coins)
            diff = rush_up - rush_down
            ratio = round(rush_up / rush_down, 1) if rush_down > 0 else 0
            count_aggregate = 0
            count_score_display = ''
            count_score_type = ''
            price_lowest = 0
            price_newhigh = 0
            
            if diff >= 5:
                status = '强势上涨'
            elif diff >= 2:
                status = '温和上涨'
            elif diff <= -5:
                status = '强势下跌'
            elif diff <= -2:
                status = '温和下跌'
            else:
                status = '震荡无序'
        
        # 格式化币种数据
        formatted_coins = []
        for coin in coins:
            inst_id = coin.get('inst_id', '')
            formatted_coins.append({
                'inst_id': inst_id,
                'symbol': inst_id,  # 添加symbol字段
                'rush_up': coin.get('rush_up', 0),
                'rush_down': coin.get('rush_down', 0),
                'last_price': coin.get('last_price', 0),
                'change_24h': coin.get('change_24h', 0),
                'vol_24h': coin.get('vol_24h', 0),
                'count': coin.get('count', 0),
                'status': coin.get('status', ''),
                'priority': coin.get('priority', 999),
                'priority_name': coin.get('priority_name', ''),
                'count_score_display': coin.get('count_score_display', ''),
                'max_ratio': coin.get('max_ratio', 0),
                'min_ratio': coin.get('min_ratio', 0),
                'snapshot_time': coin.get('snapshot_time', query_time)
            })
        
        # 按优先级排序
        formatted_coins.sort(key=lambda x: (x.get('priority', 999), x.get('inst_id', '')))
        
        # 返回完整数据
        return jsonify({
            'snapshot_time': query_time,
            'rush_up': rush_up,
            'rush_down': rush_down,
            'diff': diff,
            'count': len(coins),
            'count_aggregate': count_aggregate,
            'ratio': ratio,
            'status': status,
            'round_rush_up': 0,
            'round_rush_down': 0,
            'price_lowest': price_lowest,
            'price_newhigh': price_newhigh,
            'count_score_display': count_score_display,
            'count_score_type': count_score_type,
            'rise_24h_count': 0,
            'fall_24h_count': 0,
            'data': formatted_coins,
            'total': len(coins)
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/count/am2')
def api_count_am2():
    """获取每天凌晨2点之后第一个数据点的计次"""
    try:
        import sys
        from datetime import datetime, timedelta
        import pytz
        sys.path.insert(0, '/home/user/webapp/source_code')
        sys.path.insert(0, '/home/user/webapp')
        from gdrive_jsonl_manager import GDriveJSONLManager
        from aggregate_jsonl_manager import AggregateJSONLManager
        
        manager = GDriveJSONLManager()
        agg_manager = AggregateJSONLManager('/home/user/webapp/data/gdrive_jsonl')
        
        # 获取北京时区
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now_beijing = datetime.now(beijing_tz)
        
        # 计算今天凌晨2点的时间
        today_2am = now_beijing.replace(hour=2, minute=0, second=0, microsecond=0)
        
        # 如果当前时间在凌晨2点之前，则获取昨天凌晨2点之后的第一个数据
        if now_beijing.hour < 2:
            target_2am = today_2am - timedelta(days=1)
        else:
            target_2am = today_2am
        
        # 查找凌晨2点之后的第一个数据点（时间范围：2:00 - 4:00）
        start_time = target_2am
        end_time = target_2am + timedelta(hours=2)
        
        all_snapshots = manager.read_all_snapshots()
        if all_snapshots:
            # 筛选凌晨2点之后的数据
            filtered = []
            for snap in all_snapshots:
                snap_time_str = snap.get('snapshot_time', '')
                try:
                    snap_time = datetime.strptime(snap_time_str, '%Y-%m-%d %H:%M:%S')
                    snap_time = beijing_tz.localize(snap_time)
                    if start_time <= snap_time <= end_time:
                        filtered.append((snap_time, snap_time_str, snap))
                except:
                    continue
            
            if filtered:
                # 按时间升序排序，取第一个（最早的）
                filtered.sort(key=lambda x: x[0])
                first_time_str = filtered[0][1]
                
                # 获取该时间点所有币种的快照
                same_time_snaps = [s for s in all_snapshots if s.get('snapshot_time') == first_time_str]
                
                # 尝试从聚合数据获取
                aggregate_data = agg_manager.get_aggregate_by_time(first_time_str)
                if aggregate_data:
                    count = aggregate_data.get('count', 0)  # 使用透明标签_计次的值
                    source = 'aggregate'
                else:
                    # 没有聚合数据，返回默认值
                    count = 0
                    source = 'no_data'
                
                return jsonify({
                    'success': True,
                    'count': count,
                    'time': first_time_str,
                    'date': target_2am.strftime('%m-%d'),
                    'source': source
                })
        
        # 没有找到数据
        return jsonify({
            'success': False,
            'count': 0,
            'time': '--',
            'date': target_2am.strftime('%m-%d'),
            'message': '暂无数据'
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/latest')
def api_latest():
    """获取最新数据API - 从JSONL读取"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        sys.path.insert(0, '/home/user/webapp')
        from gdrive_jsonl_manager import GDriveJSONLManager
        from aggregate_jsonl_manager import AggregateJSONLManager
        
        manager = GDriveJSONLManager()
        agg_manager = AggregateJSONLManager('/home/user/webapp/data/gdrive_jsonl')
        
        # 获取最新的聚合数据
        aggregate_data = agg_manager.get_latest_aggregate()
        
        # 获取最新的币种快照
        all_snapshots = manager.read_all_snapshots()
        
        if not all_snapshots and not aggregate_data:
            return jsonify({'error': '暂无数据'})
        
        # 确定显示的时间（优先使用聚合数据的时间）
        if aggregate_data:
            display_time = aggregate_data.get('snapshot_time', '')
        else:
            all_snapshots.sort(key=lambda x: x.get('snapshot_time', ''), reverse=True)
            display_time = all_snapshots[0].get('snapshot_time', '')
        
        # 获取币种快照（使用最新的币种数据时间）
        if all_snapshots:
            all_snapshots.sort(key=lambda x: x.get('snapshot_time', ''), reverse=True)
            latest_coin_time = all_snapshots[0].get('snapshot_time')
            same_time_snaps = [s for s in all_snapshots if s.get('snapshot_time') == latest_coin_time]
        else:
            same_time_snaps = []
            latest_coin_time = display_time
        
        # 尝试从聚合数据文件读取透明标签数据
        try:
            if aggregate_data:
                # 使用透明标签的聚合数据
                rush_up_total = aggregate_data.get('rush_up_total', 0)
                rush_down_total = aggregate_data.get('rush_down_total', 0)
                diff = aggregate_data.get('diff_total', 0)
                ratio = aggregate_data.get('ratio', 0)
                status = aggregate_data.get('status', '未知')
                count_value = aggregate_data.get('count', 0)  # 来自"透明标签_计次"
                price_lowest = aggregate_data.get('price_lowest', 0)
                price_newhigh = aggregate_data.get('price_newhigh', 0)
                count_score_display = aggregate_data.get('count_score_display', '')
                count_score_type = aggregate_data.get('count_score_type', '')
                count_score_value = aggregate_data.get('count_score_value', 0)
            else:
                # 回退到累加计算（兼容旧数据）
                rush_up_total = 0
                rush_down_total = 0
                for snap in same_time_snaps:
                    rush_up_total += snap.get('rush_up', 0) or 0
                    rush_down_total += snap.get('rush_down', 0) or 0
                diff = rush_up_total - rush_down_total
                ratio = round(rush_up_total / rush_down_total, 1) if rush_down_total > 0 else 0
                count_value = 0
                price_lowest = 0
                price_newhigh = 0
                count_score_display = ''
                count_score_type = ''
                count_score_value = 0
                
                # 判断状态
                if diff >= 5:
                    status = '强势上涨'
                elif diff >= 2:
                    status = '温和上涨'
                elif diff <= -5:
                    status = '强势下跌'
                elif diff <= -2:
                    status = '温和下跌'
                else:
                    status = '震荡无序'
        except Exception as e:
            # 如果聚合数据读取失败，使用累加计算
            rush_up_total = 0
            rush_down_total = 0
            for snap in same_time_snaps:
                rush_up_total += snap.get('rush_up', 0) or 0
                rush_down_total += snap.get('rush_down', 0) or 0
            diff = rush_up_total - rush_down_total
            ratio = round(rush_up_total / rush_down_total, 1) if rush_down_total > 0 else 0
            count_value = 0
            price_lowest = 0
            price_newhigh = 0
            count_score_display = ''
            count_score_type = ''
            count_score_value = 0
            
            if diff >= 5:
                status = '强势上涨'
            elif diff >= 2:
                status = '温和上涨'
            elif diff <= -5:
                status = '强势下跌'
            elif diff <= -2:
                status = '温和下跌'
            else:
                status = '震荡无序'
        
        # 构建币种数据（添加优先级和计次得分）
        coins = []
        for snap in same_time_snaps:
            inst_id = snap.get('inst_id', '')
            
            # 字段说明：
            # - speed: 涨速 (parts[2]) - 浮点数
            # - rush_up: 急涨次数 (parts[3]) - 整数  
            # - rush_down: 急跌次数 (parts[4]) - 整数
            speed = snap.get('speed', 0) or 0
            rush_up = snap.get('rush_up', 0) or 0
            rush_down = snap.get('rush_down', 0) or 0
            
            # 构建币种数据（标准字段）
            coins.append({
                'symbol': inst_id,
                'change': snap.get('change_24h') or 0,
                'speed': speed,  # 涨速 (float)
                'rush_up': rush_up,  # 急涨次数 (int)
                'rush_down': rush_down,  # 急跌次数 (int)
                'update_time': snap.get('update_time') or latest_coin_time,
                'high_price': snap.get('high_price') or 0,
                'high_time': snap.get('high_time') or '',
                'decline': snap.get('drop_from_high') or 0,
                'change_24h': snap.get('change_24h') or 0,
                'rank': snap.get('ranking') or 0,
                'current_price': snap.get('current_price') or snap.get('last_price') or 0,
                'last_price': snap.get('last_price') or 0,
                'vol_24h': snap.get('vol_24h') or 0,
                'count': snap.get('count') or 0,
                'status': snap.get('status', ''),
                'priority': snap.get('priority', 999),
                'priority_name': snap.get('priority_name', ''),
                'count_score_display': snap.get('count_score_display', ''),
                'count_score_value': snap.get('count_score_value', 0),
                'count_score_type': snap.get('count_score_type', ''),
                'max_ratio': snap.get('max_ratio', 0),
                'min_ratio': snap.get('min_ratio', 0)
            })
        
        # 按优先级排序（优先级小的在前，优先级相同按symbol排序）
        coins.sort(key=lambda x: (x.get('priority', 999), x.get('symbol', '')))
        
        return jsonify({
            'snapshot_time': display_time,
            'rush_up': rush_up_total,
            'rush_down': rush_down_total,
            'diff': diff,
            'count': count_value,  # 来自"透明标签_计次"
            'ratio': ratio,
            'status': status,
            'price_lowest': price_lowest,
            'price_newhigh': price_newhigh,
            'round_rush_up': 0,  # 暂时设为0，需要单独计算
            'round_rush_down': 0,
            'count_score_display': count_score_display,  # 透明标签的计次得分
            'count_score_type': count_score_type,
            'count_score_value': count_score_value,
            'rise_24h_count': 0,
            'fall_24h_count': 0,
            'coins': coins,
            'data_source': 'JSONL'
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/chart')
def api_chart():
    """图表数据API - 支持分页的12小时趋势图数据（显示所有数据点）- 从JSONL读取"""
    try:
        from datetime import datetime, timedelta
        import sys
        sys.path.insert(0, '/home/user/webapp')
        sys.path.insert(0, '/home/user/webapp/source_code')
        from gdrive_jsonl_manager import GDriveJSONLManager
        from aggregate_jsonl_manager import AggregateJSONLManager
        
        # 获取分页参数
        page = request.args.get('page', '0')  # 默认第0页（最新）
        page = int(page)
        
        # 从JSONL读取所有快照数据
        jsonl_manager = GDriveJSONLManager()
        all_snapshots = jsonl_manager.read_all_snapshots()
        
        if not all_snapshots:
            return jsonify({'error': '无数据'})
        
        # 读取聚合数据（包含正确的计次）
        agg_manager = AggregateJSONLManager('/home/user/webapp/data/gdrive_jsonl')
        all_aggregates = agg_manager.load_all_aggregates()
        
        # 创建聚合数据的时间索引
        aggregate_by_time = {}
        for agg in all_aggregates:
            time_key = agg.get('snapshot_time')
            if time_key:
                aggregate_by_time[time_key] = agg
        
        # 按时间分组聚合（相同时间的快照合并）
        time_groups = {}
        for snap in all_snapshots:
            time_key = snap.get('snapshot_time')
            if not time_key:
                continue
            
            if time_key not in time_groups:
                time_groups[time_key] = {
                    'snapshot_time': time_key,
                    'rush_up': 0,
                    'rush_down': 0,
                    'count': 0,
                    'diff': 0
                }
            
            # 累加急涨急跌数据
            group = time_groups[time_key]
            group['rush_up'] += snap.get('rush_up', 0) or 0
            group['rush_down'] += snap.get('rush_down', 0) or 0
            
            # 计次应该从聚合数据获取，而不是累加
            if time_key in aggregate_by_time:
                group['count'] = aggregate_by_time[time_key].get('count_aggregate', 0) or 0
        
        # 计算diff和转换为列表
        all_points = []
        for time_key, data in sorted(time_groups.items()):
            try:
                dt = datetime.strptime(time_key, '%Y-%m-%d %H:%M:%S')
                data['diff'] = data['rush_up'] - data['rush_down']
                all_points.append({
                    'time': dt,
                    'formatted_time': dt.strftime('%m-%d | %H:%M'),
                    'rush_up': data['rush_up'],
                    'rush_down': data['rush_down'],
                    'diff': data['diff'],
                    'count': data['count']
                })
            except:
                continue
        
        if not all_points:
            return jsonify({'error': '无有效数据'})
        
        # 计算总页数（每页12小时）
        earliest = all_points[0]['time']
        latest = all_points[-1]['time']
        total_hours = (latest - earliest).total_seconds() / 3600
        total_pages = max(1, int(total_hours / 12) + 1)
        
        # 确保page在有效范围内
        if page < 0:
            page = 0
        if page >= total_pages:
            page = total_pages - 1
        
        # 计算当前页的时间范围（从最新往前推）
        # page=0 是最新的12小时，page=1 是之前的12小时，以此类推
        page_end_time = latest - timedelta(hours=12 * page)
        page_start_time = page_end_time - timedelta(hours=12)
        
        # 筛选当前页的数据点
        page_points = [
            p for p in all_points 
            if page_start_time <= p['time'] <= page_end_time
        ]
        
        # 如果当前页没有数据，返回空数组
        if not page_points:
            return jsonify({
                'times': [],
                'rush_up': [],
                'rush_down': [],
                'diff': [],
                'count': [],
                'page': page,
                'total_pages': total_pages,
                'has_prev': page < total_pages - 1,
                'has_next': page > 0,
                'time_range': {
                    'start': page_start_time.strftime('%Y-%m-%d %H:%M'),
                    'end': page_end_time.strftime('%Y-%m-%d %H:%M')
                },
                'data_count': 0
            })
        
        # 提取数据
        times = [p['formatted_time'] for p in page_points]
        rush_up = [p['rush_up'] for p in page_points]
        rush_down = [p['rush_down'] for p in page_points]
        diff = [p['diff'] for p in page_points]
        count = [p['count'] for p in page_points]
        
        # 检测日期变化，标记分隔线位置
        date_separators = []
        prev_date = None
        for idx, p in enumerate(page_points):
            current_date = p['time'].strftime('%Y-%m-%d')
            if prev_date is not None and current_date != prev_date:
                # 日期变化，记录分隔线位置（在两个数据点之间）
                date_separators.append({
                    'index': idx,  # 新日期开始的位置
                    'date': current_date,
                    'prev_date': prev_date
                })
            prev_date = current_date
        
        return jsonify({
            'times': times,
            'rush_up': rush_up,
            'rush_down': rush_down,
            'diff': diff,
            'count': count,
            'date_separators': date_separators,  # 新增：日期分隔线位置
            'page': page,
            'total_pages': total_pages,
            'has_prev': page < total_pages - 1,  # 有上一页（更早的数据）
            'has_next': page > 0,  # 有下一页（更新的数据）
            'time_range': {
                'start': page_start_time.strftime('%Y-%m-%d %H:%M'),
                'end': page_end_time.strftime('%Y-%m-%d %H:%M')
            },
            'data_count': len(page_points)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/timeline')
def api_timeline():
    """获取所有历史数据点API - 从JSONL读取"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        sys.path.insert(0, '/home/user/webapp/source_code')
        from gdrive_jsonl_manager import GDriveJSONLManager
        
        # 从JSONL读取所有聚合数据
        jsonl_manager = GDriveJSONLManager()
        all_snapshots = jsonl_manager.read_all_snapshots()
        
        # 按时间分组聚合
        time_groups = {}
        for snap in all_snapshots:
            time_key = snap.get('snapshot_time')
            if not time_key:
                continue
            
            if time_key not in time_groups:
                time_groups[time_key] = {
                    'snapshot_time': time_key,
                    'snapshot_date': snap.get('snapshot_date', time_key.split()[0] if time_key else ''),
                    'rush_up': 0,
                    'rush_down': 0,
                    'count': 0,
                    'count_score_display': '',
                    'count_score_type': '',
                    'status': '',
                    'price_lowest': 0,
                    'price_newhigh': 0
                }
            
            # 累加急涨急跌
            group = time_groups[time_key]
            group['rush_up'] += snap.get('rush_up', 0) or 0
            group['rush_down'] += snap.get('rush_down', 0) or 0
            group['count'] = snap.get('count', 0) or 0
            group['count_score_display'] = snap.get('count_score_display', '') or ''
            group['count_score_type'] = snap.get('count_score_type', '') or ''
            group['status'] = snap.get('status', '') or ''
        
        # 转换为列表并计算diff和ratio
        snapshots = []
        for time_key in sorted(time_groups.keys(), reverse=True):  # 时间倒序
            group = time_groups[time_key]
            diff = group['rush_up'] - group['rush_down']
            ratio = round(group['rush_up'] / group['rush_down'], 1) if group['rush_down'] > 0 else 0
            
            snapshots.append({
                'snapshot_time': group['snapshot_time'],
                'snapshot_date': group['snapshot_date'],
                'rush_up': group['rush_up'],
                'rush_down': group['rush_down'],
                'diff': diff,
                'count': group['count'],
                'ratio': ratio,
                'status': group['status'],
                'round_rush_up': 0,  # 暂不计算
                'round_rush_down': 0,
                'price_lowest': group['price_lowest'],
                'price_newhigh': group['price_newhigh'],
                'count_score_display': group['count_score_display'],
                'count_score_type': group['count_score_type'],
                'rise_24h_count': 0,
                'fall_24h_count': 0
            })
        
        return jsonify({
            'snapshots': snapshots,
            'total': len(snapshots)
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)})

# ==================== 交易信号监控 API ====================

@app.route('/signals')
def signals_page():
    """交易信号监控页面"""
    return render_template('signals.html')

@app.route('/popup-demo')
def popup_demo():
    """弹窗效果演示页面"""
    with open('popup_demo.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/signals/stats')
def api_signals_stats():
    """获取信号统计数据"""
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 获取最新记录
        cursor.execute('''
            SELECT record_time, long_signals, short_signals, 
                   total_signals, long_ratio, short_ratio
            FROM trading_signals
            ORDER BY record_time DESC
            LIMIT 1
        ''')
        latest = cursor.fetchone()
        
        # 获取总记录数
        cursor.execute('SELECT COUNT(*) FROM trading_signals')
        total_records = cursor.fetchone()[0]
        
        conn.close()
        
        if latest:
            return jsonify({
                'success': True,
                'data': {
                    'latest_time': latest[0],
                    'latest_long': latest[1],
                    'latest_short': latest[2],
                    'latest_total': latest[3],
                    'long_ratio': latest[4],
                    'short_ratio': latest[5],
                    'total_records': total_records
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': '暂无数据'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/signals/chart')
def api_signals_chart():
    """获取图表数据（支持分页和时间范围）"""
    try:
        page = int(request.args.get('page', 0))
        time_range = request.args.get('range', '12h')
        
        # 计算时间范围对应的数据点数量（每3分钟一个点）
        range_minutes = {
            '1h': 60,
            '6h': 360,
            '12h': 720,
            '24h': 1440
        }
        
        minutes = range_minutes.get(time_range, 720)
        points_per_page = minutes // 3  # 每3分钟一个数据点
        offset = page * points_per_page
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 获取总记录数
        cursor.execute('SELECT COUNT(*) FROM trading_signals')
        total = cursor.fetchone()[0]
        total_pages = (total + points_per_page - 1) // points_per_page
        
        # 获取分页数据
        cursor.execute('''
            SELECT record_time, long_signals, short_signals, total_signals
            FROM trading_signals
            ORDER BY record_time DESC
            LIMIT ? OFFSET ?
        ''', (points_per_page, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        # 反转顺序，使时间从早到晚
        rows.reverse()
        
        data = [{
            'time': row[0].split(' ')[1][:5],  # 只取时分
            'long_signals': row[1],
            'short_signals': row[2],
            'total_signals': row[3]
        } for row in rows]
        
        return jsonify({
            'success': True,
            'data': data,
            'page': page,
            'total_pages': total_pages,
            'range': time_range
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/signals/history')
def api_signals_history():
    """获取历史记录列表"""
    try:
        limit = int(request.args.get('limit', 50))
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT record_time, long_signals, short_signals,
                   total_signals, long_ratio, short_ratio
            FROM trading_signals
            ORDER BY record_time DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        data = [{
            'record_time': row[0],
            'long_signals': row[1],
            'short_signals': row[2],
            'total_signals': row[3],
            'long_ratio': row[4],
            'short_ratio': row[5]
        } for row in rows]
        
        return jsonify({
            'success': True,
            'data': data
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/liquidation/30days')
def api_liquidation_30days():
    """30日爆仓数据API - 从BTC123 API读取"""
    try:
        import requests
        
        # 调用BTC123的30天爆仓API
        url = "https://api.btc123.fans/bicoin.php?from=30daybaocang"
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return jsonify({
                'success': False,
                'error': f'API请求失败: HTTP {response.status_code}'
            })
        
        data = response.json()
        
        if data.get('code') != 0:
            return jsonify({
                'success': False,
                'error': f'API返回错误: {data}'
            })
        
        if not data.get('data') or not data['data'].get('list'):
            return jsonify({
                'success': True,
                'data': [],
                'count': 0,
                'summary': {
                    'total_amount': 0,
                    'long_short_ratio': 0
                }
            })
        
        # 解析数据
        raw_data = data['data']
        result = []
        
        for item in raw_data['list']:
            date = item.get('dateStr', '')
            buy_amount = item.get('buyAmount', 0)  # 多单爆仓（美元）
            sell_amount = item.get('sellAmount', 0)  # 空单爆仓（美元）
            total_amount = buy_amount + sell_amount
            
            result.append({
                'date': date,
                'long_amount': round(buy_amount / 100000000, 2),  # 转为亿美元
                'short_amount': round(sell_amount / 100000000, 2),
                'total_amount': round(total_amount / 100000000, 2),
                'updated_at': f'{date} 00:00:00'
            })
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result),
            'summary': {
                'total_amount': round(raw_data.get('totalAmount', 0) / 100000000, 2),
                'long_short_ratio': round(raw_data.get('totalRate', 0), 2)
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取30天数据失败: {str(e)}',
            'traceback': traceback.format_exc()
        })


@app.route('/api/panic/hour1-curve')
def api_panic_hour1_curve():
    """获取1小时爆仓金额曲线数据 (1分钟一个点)"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from panic_jsonl_manager import PanicJSONLManager
        
        # 获取小时数参数,默认1小时(60个点)
        hours = int(request.args.get('hours', 1))
        limit = hours * 60  # 每分钟一个点
        
        manager = PanicJSONLManager()
        records = manager.read_records('panic_wash_index', limit=limit, reverse=False)
        
        if not records:
            return jsonify({
                'success': False,
                'message': '暂无数据'
            })
        
        # 提取需要的字段
        curve_data = []
        for record in records:
            curve_data.append({
                'record_time': record.get('record_time'),
                'timestamp': record.get('timestamp', 0),
                'hour_1_amount': round(record.get('hour_1_amount', 0), 2),  # 单位: 万美元
                'hour_24_amount': round(record.get('hour_24_amount', 0), 2),  # 单位: 万美元
                'panic_index': round(record.get('panic_index', 0), 6),
                'wash_index': round(record.get('wash_index', 0), 6)
            })
        
        return jsonify({
            'success': True,
            'data': curve_data,
            'count': len(curve_data),
            'hours': hours,
            'data_source': 'JSONL'
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/panic/history')
def api_panic_history():
    """恐慌清洗指数历史数据API（支持时间查询）- 从JSONL读取"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from panic_jsonl_manager import PanicJSONLManager
        
        limit = int(request.args.get('limit', 50))
        query_time = request.args.get('time', None)
        
        manager = PanicJSONLManager()
        
        # 读取所有记录（reverse=True表示最新的在前）
        all_records = manager.read_records('panic_wash_index', limit=None, reverse=True)
        
        if not all_records:
            return jsonify({
                'success': False,
                'message': '暂无历史数据'
            })
        
        # 过滤有效数据（兼容新旧数据格式）
        def is_valid_record(r):
            panic_index = r.get('panic_index', 0)
            hour_24_people = r.get('hour_24_people', 0)
            total_position = r.get('total_position', 0)
            hour_1_amount = r.get('hour_1_amount', 0)
            hour_24_amount = r.get('hour_24_amount', 0)
            
            # 基本条件：恐慌指数必须大于0
            if panic_index <= 0:
                return False
            
            # 兼容新旧格式：检查是否为有效的非零值
            # 旧格式：hour_24_people > 100000, total_position > 1000000000
            # 新格式：hour_24_people > 0, total_position > 0
            if hour_24_people <= 0 or total_position <= 0:
                return False
            if hour_1_amount <= 0 or hour_24_amount <= 0:
                return False
                
            return True
        
        valid_records = [r for r in all_records if is_valid_record(r)]
        
        # 如果指定了时间查询
        if query_time:
            # 找到查询时间前后的数据
            half_limit = limit // 2
            before = []
            after = []
            
            for record in valid_records:
                record_time = record.get('record_time', '')
                if record_time <= query_time:
                    before.append(record)
                    if len(before) >= half_limit:
                        break
            
            for record in reversed(valid_records):
                record_time = record.get('record_time', '')
                if record_time > query_time:
                    after.append(record)
                    if len(after) >= half_limit:
                        break
            
            selected_records = before + list(reversed(after))
        else:
            # 默认返回最新的N条
            selected_records = valid_records[:limit]
        
        # JSONL数据已经是标准单位（采集器已转换），直接使用
        def format_record(record):
            return {
                'record_time': record.get('record_time'),
                'panic_index': record.get('panic_index', 0),
                'hour_24_people': round(record.get('hour_24_people', 0), 2),
                'total_position': round(record.get('total_position', 0), 2),
                'hour_1_amount': round(record.get('hour_1_amount', 0), 2),
                'hour_24_amount': round(record.get('hour_24_amount', 0), 2)
            }
        
        data = [format_record(record) for record in selected_records]
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'获取历史数据失败: {str(e)}',
            'traceback': traceback.format_exc()
        })

@app.route('/api/panic/30d-stats')
def get_panic_30d_stats():
    """获取30天爆仓统计数据"""
    try:
        from panic_jsonl_manager import PanicJSONLManager
        from datetime import datetime, timedelta
        import pytz
        
        manager = PanicJSONLManager()
        
        # 获取历史数据（最多取30天）
        history = manager.read_records('panic_wash_index', limit=10000)
        
        if not history:
            return jsonify({
                'success': True,
                'data': {
                    'total_people': 0,
                    'total_amount': 0,
                    'days_count': 0,
                    'message': '暂无历史数据'
                }
            })
        
        # 计算30天前的时间
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz).replace(tzinfo=None)
        thirty_days_ago = now - timedelta(days=30)
        
        # 筛选30天内的数据
        recent_30d = [
            h for h in history 
            if datetime.strptime(h['record_time'], '%Y-%m-%d %H:%M:%S') >= thirty_days_ago
        ]
        
        if not recent_30d:
            return jsonify({
                'success': True,
                'data': {
                    'total_people': 0,
                    'total_amount': 0,
                    'days_count': 0,
                    'message': '30天内无数据'
                }
            })
        
        # 按日期分组统计
        daily_stats = {}
        for record in recent_30d:
            date = record['record_time'].split(' ')[0]
            if date not in daily_stats:
                daily_stats[date] = {
                    'people': 0,
                    'amount': 0
                }
            
            # 取每天的最大值（因为24h数据是累计的）
            people = record.get('hour_24_people', 0)
            amount = record.get('hour_24_amount_usd', 0)
            
            if people > daily_stats[date]['people']:
                daily_stats[date]['people'] = people
            if amount > daily_stats[date]['amount']:
                daily_stats[date]['amount'] = amount
        
        # 计算总和
        total_people = sum(day['people'] for day in daily_stats.values())
        total_amount = sum(day['amount'] for day in daily_stats.values())
        
        return jsonify({
            'success': True,
            'data': {
                'total_people': round(total_people / 10000, 2),  # 转为万人
                'total_amount': round(total_amount / 100000000, 2),  # 转为亿美元
                'days_count': len(daily_stats),
                'message': f'统计了最近{len(daily_stats)}天的数据'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取30天统计失败: {str(e)}',
            'traceback': traceback.format_exc()
        })


# ============================================
# 恐惧贪婪指数 API
# ============================================

@app.route('/api/fear-greed/latest')
def api_fear_greed_latest():
    """恐惧贪婪指数最新数据API"""
    try:
        from fear_greed_jsonl_manager import FearGreedJSONLManager
        manager = FearGreedJSONLManager()
        
        latest = manager.get_latest_record()
        if not latest:
            return jsonify({
                'success': False,
                'error': '暂无数据'
            })
        
        return jsonify({
            'success': True,
            'data': {
                'datetime': latest.get('datetime'),
                'value': latest.get('value'),
                'result': latest.get('result'),
                'source': latest.get('source', 'btc123.fans'),
                'updated_at': latest.get('updated_at')
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取恐惧贪婪指数失败: {str(e)}'
        })


@app.route('/api/fear-greed/history')
def api_fear_greed_history():
    """恐惧贪婪指数历史数据API"""
    try:
        from fear_greed_jsonl_manager import FearGreedJSONLManager
        manager = FearGreedJSONLManager()
        
        # 获取参数
        limit = request.args.get('limit', 30, type=int)
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        if start_date and end_date:
            # 按日期范围查询
            records = manager.get_records_by_date_range(start_date, end_date)
        else:
            # 查询最近N条
            records = manager.get_latest_n_records(limit)
        
        return jsonify({
            'success': True,
            'total': len(records),
            'data': records
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取历史数据失败: {str(e)}'
        })


@app.route('/api/fear-greed/statistics')
def api_fear_greed_statistics():
    """恐惧贪婪指数统计API"""
    try:
        from fear_greed_jsonl_manager import FearGreedJSONLManager
        manager = FearGreedJSONLManager()
        
        stats = manager.get_statistics()
        
        return jsonify({
            'success': True,
            'data': stats
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'获取统计信息失败: {str(e)}'
        })


@app.route('/api/modules/stats')
def api_modules_stats():
    """获取所有模块的统计信息"""
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 1. 历史数据查询模块统计
        cursor.execute("SELECT COUNT(*) FROM crypto_snapshots")
        query_total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT snapshot_date) FROM crypto_snapshots")
        query_days = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(snapshot_time) FROM crypto_snapshots")
        query_last_time = cursor.fetchone()[0] or '-'
        if query_last_time != '-':
            # 处理时间格式：可能是 "HH:MM:SS" 或 "YYYY-MM-DD HH:MM:SS"
            if ' ' in query_last_time:
                query_last_time = query_last_time.split(' ')[1][:5]  # 取HH:MM
            else:
                query_last_time = query_last_time[:5]  # 已经是HH:MM:SS，取HH:MM
        
        # 2. 交易信号监控模块统计
        cursor.execute("SELECT COUNT(*) FROM trading_signal_history")
        signal_total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT DATE(created_at)) FROM trading_signal_history")
        signal_days = cursor.fetchone()[0]
        
        cursor.execute("SELECT MAX(created_at) FROM trading_signal_history")
        signal_last_time = cursor.fetchone()[0] or '-'
        if signal_last_time != '-':
            # 处理时间格式：可能是 "HH:MM:SS" 或 "YYYY-MM-DD HH:MM:SS"
            if ' ' in signal_last_time:
                signal_last_time = signal_last_time.split(' ')[1][:5]  # 取HH:MM
            else:
                signal_last_time = signal_last_time[:5]  # 已经是HH:MM:SS，取HH:MM
        
        # 3. 恐慌清洗指数模块统计（从JSONL文件读取）
        try:
            import os
            panic_jsonl_file = '/home/user/webapp/data/panic_jsonl/panic_wash_index.jsonl'
            if os.path.exists(panic_jsonl_file):
                with open(panic_jsonl_file, 'r') as f:
                    lines = f.readlines()
                    panic_total = len(lines)
                    
                    # 统计天数
                    dates = set()
                    last_time = '-'
                    for line in lines:
                        try:
                            import json
                            data = json.loads(line.strip())
                            record_time = data.get('record_time', '')
                            if record_time:
                                dates.add(record_time.split(' ')[0])
                                last_time = record_time
                        except:
                            pass
                    
                    panic_days = len(dates)
                    if last_time != '-' and ' ' in last_time:
                        panic_last_time = last_time.split(' ')[1][:5]  # 取HH:MM
                    else:
                        panic_last_time = '-'
            else:
                panic_total = 0
                panic_days = 0
                panic_last_time = '-'
        except Exception as e:
            logging.error(f"读取恐慌指数JSONL失败: {e}")
            panic_total = 0
            panic_days = 0
            panic_last_time = '-'
        
        conn.close()
        
        return jsonify({
            'success': True,
            'query_module': {
                'total_records': query_total,
                'data_days': query_days,
                'last_update': query_last_time
            },
            'signal_module': {
                'total_records': signal_total,
                'data_days': signal_days,
                'last_update': signal_last_time
            },
            'panic_module': {
                'total_records': panic_total,
                'data_days': panic_days,
                'last_update': panic_last_time
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/price-comparison')
def price_comparison_page():
    """比价系统页面"""
    return render_template('price_comparison.html')

@app.route('/api/price-comparison/list')
def api_price_comparison_list():
    """获取比价系统所有币种数据 - 从JSONL读取"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from price_comparison_jsonl_manager import PriceComparisonJSONLManager
        
        manager = PriceComparisonJSONLManager()
        data = manager.get_all_coins()
        
        return jsonify({
            'success': True,
            'data': data,
            'total': len(data),
            'data_source': 'JSONL'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/price-comparison/update', methods=['POST'])
def api_price_comparison_update():
    """更新币种价格并进行比价判断
    
    逻辑:
    - 新价格 > 最高价: 更新最高价，最高计次清零
    - 新价格 < 最低价: 更新最低价，最低计次清零  
    - 最低价 <= 新价格 <= 最高价: 两个计次都+1
    """
    try:
        data = request.get_json()
        coin_name = data.get('coin_name')
        new_price = float(data.get('price'))
        
        if not coin_name or new_price is None:
            return jsonify({
                'success': False,
                'error': '缺少必要参数: coin_name 或 price'
            })
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 获取当前币种的最高价和最低价
        cursor.execute('''
            SELECT highest_price, highest_count, lowest_price, lowest_count
            FROM price_baseline
            WHERE symbol = ?
        ''', (coin_name,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({
                'success': False,
                'error': f'币种 {coin_name} 不存在'
            })
        
        highest_price, highest_count, lowest_price, lowest_count = row
        old_highest_price = highest_price
        old_lowest_price = lowest_price
        
        # 价格比较逻辑
        action = ''
        if new_price > highest_price:
            # 新价格创新高
            old_highest_price = highest_price
            highest_price = new_price
            highest_count = 0
            action = 'new_high'
        elif new_price < lowest_price:
            # 新价格创新低
            old_lowest_price = lowest_price
            lowest_price = new_price
            lowest_count = 0
            action = 'new_low'
        else:
            # 价格在区间内
            highest_count += 1
            lowest_count += 1
            action = 'in_range'
        
        # 计算占比
        # 最高价占比 = (当前价 / 最高价) × 100
        highest_ratio = round((new_price / highest_price) * 100, 2) if highest_price > 0 else 0
        # 最低价占比 = (当前价 / 最低价) × 100
        lowest_ratio = round((new_price / lowest_price) * 100, 2) if lowest_price > 0 else 0
        
        # 更新数据库 - 使用北京时间
        from datetime import datetime
        import pytz
        beijing_tz = pytz.timezone('Asia/Shanghai')
        beijing_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            UPDATE price_baseline
            SET highest_price = ?,
                highest_count = ?,
                lowest_price = ?,
                lowest_count = ?,
                highest_ratio = ?,
                lowest_ratio = ?,
                last_update_time = ?
            WHERE symbol = ?
        ''', (highest_price, highest_count, lowest_price, lowest_count, 
              highest_ratio, lowest_ratio, beijing_time, coin_name))
        
        # 如果发生创新高或创新低，记录事件
        if action in ['new_high', 'new_low']:
            cursor.execute('''
                INSERT INTO price_breakthrough_events 
                (symbol, event_type, price, event_time)
                VALUES (?, ?, ?, ?)
            ''', (coin_name, action, new_price, beijing_time))
            
            # 更新统计表缓存（清除今天的缓存，下次查询时会重新计算）
            today_date = beijing_tz.localize(datetime.now()).strftime('%Y-%m-%d')
            cursor.execute('''
                DELETE FROM price_comparison_stats
                WHERE stat_date = ?
            ''', (today_date,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'action': action,
            'data': {
                'coin_name': coin_name,
                'new_price': new_price,
                'highest_price': highest_price,
                'highest_count': highest_count,
                'lowest_price': lowest_price,
                'lowest_count': lowest_count
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/price-comparison/breakthrough-stats')
def api_breakthrough_stats():
    """获取创新高/低统计 - 从JSONL读取"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from price_comparison_jsonl_manager import PriceComparisonJSONLManager
        
        manager = PriceComparisonJSONLManager()
        stats = manager.get_breakthrough_stats()
        
        return jsonify({
            'success': True,
            'data': stats,
            'data_source': 'JSONL'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/price-comparison/breakthrough-logs')
def api_breakthrough_logs():
    """获取创新高/低详细日志 - 从JSONL读取
    
    参数:
    - limit: 返回记录数量，默认50
    - days: 查询最近N天的记录，默认7天
    - coin: 筛选特定币种
    - type: 筛选类型 (new_high/new_low)
    
    返回:
    - 时间、币名、事件类型(创新高/创新低)、价格、之前极值价格
    """
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from price_comparison_jsonl_manager import PriceComparisonJSONLManager
        
        # 获取参数
        limit = request.args.get('limit', 50, type=int)
        days = request.args.get('days', 7, type=int)
        coin_filter = request.args.get('coin', None)
        type_filter = request.args.get('type', None)
        
        manager = PriceComparisonJSONLManager()
        logs = manager.get_breakthrough_events(
            limit=limit,
            days=days,
            coin_filter=coin_filter,
            type_filter=type_filter
        )
        
        return jsonify({
            'success': True,
            'data': logs,
            'count': len(logs),
            'filters': {
                'days': days,
                'coin': coin_filter,
                'type': type_filter,
                'limit': limit
            },
            'data_source': 'JSONL'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/price-comparison/update-ratios')
def api_update_price_ratios():
    """批量更新所有币种的价格占比
    
    从最新快照数据获取当前价格，计算并更新占比:
    - 最高价占比 = (当前价 / 最高价) × 100%
    - 最低价占比 = (当前价 / 最低价) × 100%
    """
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 获取最新快照时间
        cursor.execute('SELECT MAX(snapshot_time) FROM crypto_coin_data')
        latest_time = cursor.fetchone()[0]
        
        if not latest_time:
            return jsonify({
                'success': False,
                'error': '没有找到快照数据'
            })
        
        # 获取最新快照的所有币种价格
        cursor.execute('''
            SELECT symbol, current_price
            FROM crypto_coin_data
            WHERE snapshot_time = ?
        ''', (latest_time,))
        
        current_prices = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 获取所有币种的最高价和最低价
        cursor.execute('''
            SELECT symbol, highest_price, lowest_price
            FROM price_baseline
        ''')
        
        from datetime import datetime
        import pytz
        beijing_tz = pytz.timezone('Asia/Shanghai')
        current_time = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        
        updated_count = 0
        update_details = []
        
        for row in cursor.fetchall():
            coin_name, highest_price, lowest_price = row
            
            # 查找当前价格
            current_price = current_prices.get(coin_name)
            
            if current_price is not None and current_price > 0:
                # 计算占比
                highest_ratio = round((current_price / highest_price) * 100, 2) if highest_price > 0 else 0
                lowest_ratio = round((current_price / lowest_price) * 100, 2) if lowest_price > 0 else 0
                
                # 更新数据库
                cursor.execute('''
                    UPDATE price_baseline
                    SET highest_ratio = ?,
                        lowest_ratio = ?,
                        last_update_time = ?
                    WHERE symbol = ?
                ''', (highest_ratio, lowest_ratio, current_time, coin_name))
                
                updated_count += 1
                update_details.append({
                    'coin_name': coin_name,
                    'current_price': current_price,
                    'highest_ratio': highest_ratio,
                    'lowest_ratio': lowest_ratio
                })
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'成功更新 {updated_count} 个币种的占比',
            'snapshot_time': latest_time,
            'updated_count': updated_count,
            'details': update_details[:10]  # 只返回前10个作为示例
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/monitor/data-collection')
def api_monitor_data_collection():
    """监控数据采集状态"""
    try:
        from datetime import datetime, timedelta
        import pytz
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        
        # 获取最新快照时间
        cursor.execute('SELECT MAX(snapshot_time) FROM crypto_snapshots')
        latest_snapshot = cursor.fetchone()[0]
        
        if not latest_snapshot:
            return jsonify({
                'success': False,
                'error': '数据库中没有任何快照数据',
                'status': 'no_data'
            })
        
        # 计算时间差
        latest_time = datetime.strptime(latest_snapshot, '%Y-%m-%d %H:%M:%S')
        latest_time = beijing_tz.localize(latest_time)
        time_diff_minutes = (now - latest_time).total_seconds() / 60
        
        # 获取今天的采集次数
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_str = today_start.strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            SELECT COUNT(*) FROM crypto_snapshots 
            WHERE snapshot_time >= ?
        ''', (today_start_str,))
        today_count = cursor.fetchone()[0]
        
        conn.close()
        
        # 判断状态
        status = 'normal'
        message = '数据采集正常'
        alert_level = 'success'
        
        if time_diff_minutes > 20:
            status = 'critical'
            message = f'严重: 已经 {time_diff_minutes:.1f} 分钟没有新数据'
            alert_level = 'danger'
        elif time_diff_minutes > 15:
            status = 'warning'
            message = f'警告: 已经 {time_diff_minutes:.1f} 分钟没有新数据'
            alert_level = 'warning'
        
        # 计算预期采集次数（每10分钟一次）
        expected_count = int((now.hour * 60 + now.minute) / 10)
        
        return jsonify({
            'success': True,
            'status': status,
            'message': message,
            'alert_level': alert_level,
            'data': {
                'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'latest_snapshot': latest_snapshot,
                'time_diff_minutes': round(time_diff_minutes, 1),
                'today_count': today_count,
                'expected_count': expected_count,
                'collection_rate': round((today_count / expected_count * 100) if expected_count > 0 else 0, 1)
            }
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/monitor')
def monitor_page():
    """数据采集监控页面（增强版）- 支持执行日志、开关控制、刷新间隔"""
    return render_template('unified_monitor_enhanced.html')

@app.route('/monitor-old')
def monitor_page_old():
    """原始监控页面（旧版）"""
    return render_template('monitor.html')

@app.route('/star-system')
def star_system_page():
    """星星系统页面"""
    return render_template('star_system.html')

@app.route('/api/star-system/data')
def api_star_system_data():
    """获取星星系统所有指标数据"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from star_system import calculate_star_system
        from datetime import datetime, timedelta
        import pytz
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        beijing_tz = pytz.timezone('Asia/Shanghai')
        
        # 获取最新快照数据
        cursor.execute('''
            SELECT rush_up, rush_down, diff, count, snapshot_time
            FROM crypto_snapshots
            ORDER BY snapshot_date DESC, snapshot_time DESC
            LIMIT 1
        ''')
        snapshot = cursor.fetchone()
        
        if not snapshot:
            return jsonify({'success': False, 'error': '暂无快照数据'})
        
        rush_up, rush_down, diff, count, snapshot_time = snapshot
        
        # 确保数值不为None
        rush_up = rush_up if rush_up is not None else 0
        rush_down = rush_down if rush_down is not None else 0
        diff = diff if diff is not None else 0
        count = count if count is not None else 0
        
        # 获取全网持仓量（从恐慌清洗指数表）
        cursor.execute('''
            SELECT total_position
            FROM panic_wash_index
            ORDER BY record_time DESC
            LIMIT 1
        ''')
        holdings_row = cursor.fetchone()
        holdings = holdings_row[0] if holdings_row and holdings_row[0] is not None else 10000000000  # 默认100亿（元）
        
        # 获取做多做空信号（从交易信号表）
        cursor.execute('''
            SELECT long_signals, short_signals
            FROM trading_signals
            ORDER BY record_time DESC
            LIMIT 1
        ''')
        signals_row = cursor.fetchone()
        long_signals = signals_row[0] if signals_row and signals_row[0] is not None else 0
        short_signals = signals_row[1] if signals_row and signals_row[1] is not None else 0
        
        # 获取今日创新高新低次数
        today_start = datetime.now(beijing_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        today_start_str = today_start.strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            SELECT event_type, COUNT(*) 
            FROM price_breakthrough_events 
            WHERE event_time >= ?
            GROUP BY event_type
        ''', (today_start_str,))
        today_breakthrough = dict(cursor.fetchall())
        new_high_today = today_breakthrough.get('new_high', 0)
        new_low_today = today_breakthrough.get('new_low', 0)
        
        # 获取币种统计数据（从最新快照的详细数据）
        cursor.execute('''
            SELECT symbol, rush_up, rush_down, priority_level
            FROM crypto_coin_data
            WHERE snapshot_time = ?
        ''', (snapshot_time,))
        coin_data = cursor.fetchall()
        
        # 统计特殊情况并记录具体币种
        only_rush_up_coins = [c[0] for c in coin_data if c[1] > 0 and c[2] == 0]
        only_rush_up_count = len(only_rush_up_coins)
        
        rush_up_gt_down_coins = [c[0] for c in coin_data if c[1] > c[2]]
        rush_up_gt_down_count = len(rush_up_gt_down_coins)
        
        only_rush_down_coins = [c[0] for c in coin_data if c[1] == 0 and c[2] > 0]
        only_rush_down_count = len(only_rush_down_coins)
        
        rush_down_gt_up_coins = [c[0] for c in coin_data if c[2] > c[1]]
        rush_down_gt_up_count = len(rush_down_gt_up_coins)
        
        # 优先级≥4 means 等级1,2,3,4 (priority_level values: '等级1', '等级2', etc.)
        priority_high_coins = [c[0] for c in coin_data if c[3] in ['等级1', '等级2', '等级3', '等级4']]
        priority_high_count = len(priority_high_coins)
        
        # ========== 新增功能3: 位置系统平均位置（在conn.close()之前查询） ==========
        try:
            # 计算48小时前的北京时间
            hours_ago_48 = datetime.now(beijing_tz) - timedelta(hours=48)
            hours_ago_48_str = hours_ago_48.strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute("""
                SELECT 
                    AVG(position_4h) as avg_4h,
                    AVG(position_12h) as avg_12h,
                    AVG(position_24h) as avg_24h,
                    AVG(position_48h) as avg_48h
                FROM position_system
                WHERE record_time >= ?
            """, (hours_ago_48_str,))
            pos_row = cursor.fetchone()
            
            position_avg = {
                '4h': round(pos_row[0], 2) if pos_row and pos_row[0] else 0,
                '12h': round(pos_row[1], 2) if pos_row and pos_row[1] else 0,
                '24h': round(pos_row[2], 2) if pos_row and pos_row[2] else 0,
                '48h': round(pos_row[3], 2) if pos_row and pos_row[3] else 0
            }
        except Exception as e:
            position_avg = {'4h': 0, '12h': 0, '24h': 0, '48h': 0}
            print(f"位置系统平均位置查询错误: {e}")
        
        # ========== 新增功能4: 创新高/创新低统计（在conn.close()之前查询） ==========
        try:
            # 当天统计（今天0点到现在）
            today_start = datetime.now(beijing_tz).replace(hour=0, minute=0, second=0, microsecond=0)
            today_start_str = today_start.strftime('%Y-%m-%d %H:%M:%S')
            
            # 3天统计
            three_days_ago = datetime.now(beijing_tz) - timedelta(days=3)
            three_days_ago_str = three_days_ago.strftime('%Y-%m-%d %H:%M:%S')
            
            # 7天统计
            seven_days_ago = datetime.now(beijing_tz) - timedelta(days=7)
            seven_days_ago_str = seven_days_ago.strftime('%Y-%m-%d %H:%M:%S')
            
            # 查询当天创新高/创新低
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN event_type = 'new_high' THEN 1 ELSE 0 END) as today_high,
                    SUM(CASE WHEN event_type = 'new_low' THEN 1 ELSE 0 END) as today_low
                FROM price_breakthrough_events
                WHERE event_time >= ?
            """, (today_start_str,))
            today_bt = cursor.fetchone()
            
            # 查询3天创新高/创新低
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN event_type = 'new_high' THEN 1 ELSE 0 END) as three_days_high,
                    SUM(CASE WHEN event_type = 'new_low' THEN 1 ELSE 0 END) as three_days_low
                FROM price_breakthrough_events
                WHERE event_time >= ?
            """, (three_days_ago_str,))
            three_days_bt = cursor.fetchone()
            
            # 查询7天创新高/创新低
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN event_type = 'new_high' THEN 1 ELSE 0 END) as seven_days_high,
                    SUM(CASE WHEN event_type = 'new_low' THEN 1 ELSE 0 END) as seven_days_low
                FROM price_breakthrough_events
                WHERE event_time >= ?
            """, (seven_days_ago_str,))
            seven_days_bt = cursor.fetchone()
            
            breakthrough_stats = {
                'today': {
                    'new_high': today_bt[0] if today_bt and today_bt[0] else 0,
                    'new_low': today_bt[1] if today_bt and today_bt[1] else 0
                },
                'three_days': {
                    'new_high': three_days_bt[0] if three_days_bt and three_days_bt[0] else 0,
                    'new_low': three_days_bt[1] if three_days_bt and three_days_bt[1] else 0
                },
                'seven_days': {
                    'new_high': seven_days_bt[0] if seven_days_bt and seven_days_bt[0] else 0,
                    'new_low': seven_days_bt[1] if seven_days_bt and seven_days_bt[1] else 0
                }
            }
        except Exception as e:
            breakthrough_stats = {
                'today': {'new_high': 0, 'new_low': 0},
                'three_days': {'new_high': 0, 'new_low': 0},
                'seven_days': {'new_high': 0, 'new_low': 0}
            }
            print(f"创新高/创新低统计查询错误: {e}")
        
        conn.close()
        
        # 准备数据给星星系统计算
        data = {
            'rush_up': rush_up,
            'rush_down': rush_down,
            'diff': diff,
            'holdings': holdings,
            'long_signals': long_signals,
            'short_signals': short_signals,
            'only_rush_up_count': only_rush_up_count,
            'rush_up_gt_down_count': rush_up_gt_down_count,
            'priority_high_count': priority_high_count,
            'only_rush_down_count': only_rush_down_count,
            'rush_down_gt_up_count': rush_down_gt_up_count,
            'new_low_today': new_low_today,
            'new_high_today': new_high_today,
            'count': count,
            'snapshot_time': snapshot_time
        }
        
        # 计算星星系统
        results = calculate_star_system(data)
        
        # 保存到历史记录表（每次调用API时保存）
        try:
            import json as json_lib
            cursor.execute('''
                INSERT INTO star_system_history 
                (timestamp, total_stars, solid_stars, hollow_stars, solid_percentage, hollow_percentage, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                snapshot_time,
                results.get('total_stars', 0),
                results.get('solid_stars', 0),
                results.get('hollow_stars', 0),
                results.get('solid_percentage', 0),
                results.get('hollow_percentage', 0),
                json_lib.dumps(results, ensure_ascii=False)
            ))
            conn.commit()
        except Exception as save_err:
            print(f"保存历史数据失败: {save_err}")
        
        # 添加币种列表到结果中
        coin_lists = {
            'only_rush_up_coins': only_rush_up_coins,
            'rush_up_gt_down_coins': rush_up_gt_down_coins,
            'priority_high_coins': priority_high_coins,
            'only_rush_down_coins': only_rush_down_coins,
            'rush_down_gt_up_coins': rush_down_gt_up_coins
        }
        
        # ========== 新增功能1: V1/V2币种统计 ==========
        try:
            conn_v1v2 = sqlite3.connect('v1v2_data.db')
            cursor_v1v2 = conn_v1v2.cursor()
            
            coins_list = ['BTC', 'ETH', 'XRP', 'SOL', 'BNB', 'LTC', 'DOGE', 'SUI', 'TRX', 'TON', 
                         'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'ADA', 'LINK', 'CRO', 'DOT', 'UNI',
                         'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO', 'AAVE']
            
            v1_coins_list = []
            v2_coins_list = []
            
            for coin in coins_list:
                try:
                    cursor_v1v2.execute(f"""
                        SELECT level FROM volume_{coin.lower()}
                        ORDER BY id DESC LIMIT 1
                    """)
                    row = cursor_v1v2.fetchone()
                    if row and row[0] == 'V1':
                        v1_coins_list.append(coin)
                    elif row and row[0] == 'V2':
                        v2_coins_list.append(coin)
                except:
                    pass
            
            conn_v1v2.close()
        except:
            v1_coins_list = []
            v2_coins_list = []
        
        # ========== 新增功能2: 1分钟涨跌速预警统计 ==========
        try:
            conn_ps = sqlite3.connect('price_speed_data.db')
            cursor_ps = conn_ps.cursor()
            
            # 获取各类型预警的币种
            cursor_ps.execute("""
                SELECT alert_type, symbol
                FROM latest_price_speed
                WHERE alert_type != 'NORMAL'
            """)
            
            alert_coins = {
                'super_strong_up': [],
                'very_strong_up': [],
                'strong_up': [],
                'general_up': [],
                'super_strong_down': [],
                'very_strong_down': [],
                'strong_down': [],
                'general_down': []
            }
            
            for alert_type, symbol in cursor_ps.fetchall():
                if alert_type == 'SUPER_STRONG_UP':
                    alert_coins['super_strong_up'].append(symbol)
                elif alert_type == 'VERY_STRONG_UP':
                    alert_coins['very_strong_up'].append(symbol)
                elif alert_type == 'STRONG_UP':
                    alert_coins['strong_up'].append(symbol)
                elif alert_type == 'GENERAL_UP':
                    alert_coins['general_up'].append(symbol)
                elif alert_type == 'SUPER_STRONG_DOWN':
                    alert_coins['super_strong_down'].append(symbol)
                elif alert_type == 'VERY_STRONG_DOWN':
                    alert_coins['very_strong_down'].append(symbol)
                elif alert_type == 'STRONG_DOWN':
                    alert_coins['strong_down'].append(symbol)
                elif alert_type == 'GENERAL_DOWN':
                    alert_coins['general_down'].append(symbol)
            
            conn_ps.close()
        except:
            alert_coins = {
                'super_strong_up': [],
                'very_strong_up': [],
                'strong_up': [],
                'general_up': [],
                'super_strong_down': [],
                'very_strong_down': [],
                'strong_down': [],
                'general_down': []
            }
        
        return jsonify({
            'success': True,
            'data': results,
            'raw_data': data,
            'coin_lists': coin_lists,
            'update_time': snapshot_time,
            # 新增数据
            'v1v2_data': {
                'v1_coins': v1_coins_list,
                'v1_count': len(v1_coins_list),
                'v2_coins': v2_coins_list,
                'v2_count': len(v2_coins_list)
            },
            'price_speed_alerts': {
                'up': {
                    'super_strong': {'count': len(alert_coins['super_strong_up']), 'coins': alert_coins['super_strong_up']},
                    'very_strong': {'count': len(alert_coins['very_strong_up']), 'coins': alert_coins['very_strong_up']},
                    'strong': {'count': len(alert_coins['strong_up']), 'coins': alert_coins['strong_up']},
                    'general': {'count': len(alert_coins['general_up']), 'coins': alert_coins['general_up']}
                },
                'down': {
                    'super_strong': {'count': len(alert_coins['super_strong_down']), 'coins': alert_coins['super_strong_down']},
                    'very_strong': {'count': len(alert_coins['very_strong_down']), 'coins': alert_coins['very_strong_down']},
                    'strong': {'count': len(alert_coins['strong_down']), 'coins': alert_coins['strong_down']},
                    'general': {'count': len(alert_coins['general_down']), 'coins': alert_coins['general_down']}
                }
            },
            'position_avg': position_avg,
            'breakthrough_stats': breakthrough_stats
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

# ==================== 星星系统历史数据 API ====================
@app.route('/api/star-system/history')
def api_star_system_history():
    """获取星星系统历史数据"""
    try:
        date = request.args.get('date')  # 格式: YYYY-MM-DD
        limit = int(request.args.get('limit', 100))
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        if date:
            # 查询指定日期的数据
            start_time = f"{date} 00:00:00"
            end_time = f"{date} 23:59:59"
            cursor.execute('''
                SELECT id, timestamp, total_stars, solid_stars, hollow_stars, 
                       solid_percentage, hollow_percentage, raw_data
                FROM star_system_history
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (start_time, end_time, limit))
        else:
            # 查询最近的记录
            cursor.execute('''
                SELECT id, timestamp, total_stars, solid_stars, hollow_stars, 
                       solid_percentage, hollow_percentage, raw_data
                FROM star_system_history
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        
        history_data = []
        for row in rows:
            try:
                import json as json_lib
                raw_data = json_lib.loads(row[7]) if row[7] else {}
            except:
                raw_data = {}
            
            history_data.append({
                'id': row[0],
                'timestamp': row[1],
                'total_stars': row[2],
                'solid_stars': row[3],
                'hollow_stars': row[4],
                'solid_percentage': row[5],
                'hollow_percentage': row[6],
                'details': raw_data
            })
        
        # 获取可用日期列表
        cursor.execute('''
            SELECT DISTINCT DATE(timestamp) as date
            FROM star_system_history
            ORDER BY date DESC
            LIMIT 30
        ''')
        available_dates = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': history_data,
            'available_dates': available_dates,
            'total_records': len(history_data)
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

# ==================== 数据采集监控 API ====================
@app.route('/api/monitor/status')
def api_monitor_status():
    """获取数据采集监控状态"""
    import subprocess
    try:
        result = subprocess.run(
            ['python3', 'monitor_data_collection.py', 'status'],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=10
        )
        status = json.loads(result.stdout)
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/monitor/history')
def api_monitor_history():
    """获取采集历史"""
    import subprocess
    try:
        hours = request.args.get('hours', '2')
        result = subprocess.run(
            ['python3', 'monitor_data_collection.py', 'history', hours],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=10
        )
        history = json.loads(result.stdout)
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/monitor/trigger', methods=['POST'])
def api_monitor_trigger():
    """手动触发数据采集"""
    import subprocess
    try:
        result = subprocess.run(
            ['python3', 'monitor_data_collection.py', 'force'],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        collection_result = json.loads(result.stdout) if result.stdout else {}
        return jsonify({
            'success': result.returncode == 0,
            'result': collection_result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/monitor/check', methods=['POST'])
def api_monitor_check():
    """检查并自动恢复数据采集"""
    import subprocess
    try:
        result = subprocess.run(
            ['python3', 'monitor_data_collection.py', 'check'],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        check_result = json.loads(result.stdout) if result.stdout else {}
        return jsonify({
            'success': True,
            'result': check_result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# ==================== 多模块监控 API ====================
@app.route('/api/monitor/all-modules')
def api_monitor_all_modules():
    """获取所有模块监控状态"""
    import subprocess
    try:
        result = subprocess.run(
            ['python3', 'multi_module_monitor.py', 'status'],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=10
        )
        # 从stdout提取JSON部分（跳过前面的文本输出）
        output = result.stdout
        # 找到JSON开始的位置
        json_start = output.find('{')
        if json_start >= 0:
            json_str = output[json_start:]
            statuses = json.loads(json_str)
            return jsonify({
                'success': True,
                'modules': statuses
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No JSON output found'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/monitor/check-all', methods=['POST'])
def api_monitor_check_all():
    """检查并自动恢复所有模块"""
    import subprocess
    try:
        result = subprocess.run(
            ['python3', 'multi_module_monitor.py', 'check', '--silent'],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=600  # 10分钟超时（多个模块可能需要更长时间）
        )
        check_result = json.loads(result.stdout) if result.stdout else {}
        return jsonify({
            'success': True,
            'result': check_result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/monitor/force-update/<module_key>', methods=['POST'])
def api_monitor_force_update(module_key):
    """强制更新指定模块"""
    import subprocess
    try:
        result = subprocess.run(
            ['python3', 'multi_module_monitor.py', 'force', module_key],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        update_result = json.loads(result.stdout) if result.stdout else {}
        return jsonify({
            'success': result.returncode == 0,
            'result': update_result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# ==================== 得分系统 API ====================
from score_calculator import ScoreCalculator

@app.route('/control-center')
def control_center_page():
    """深度图得分页面（控制中心）"""
    return render_template('control_center.html')

@app.route('/depth-score')
def depth_score_page():
    """深度图得分页面"""
    return render_template('depth_score.html')

@app.route('/depth-chart')
def depth_chart_page():
    """深度图可视化页面"""
    return render_template('depth_chart.html')

@app.route('/score-overview')
def score_overview_page():
    """平均分页面"""
    return render_template('score_overview.html')

@app.route('/crypto-index')
def crypto_index_page():
    """OKEX加密指数页面"""
    return render_template('crypto_index.html')

@app.route('/api/depth-scores')
def api_depth_scores():
    """获取深度得分数据"""
    try:
        timeframe = int(request.args.get('timeframe', 24))
        limit = int(request.args.get('limit', 50))
        
        calculator = ScoreCalculator()
        scores = calculator.calculate_all_coins_depth_scores(timeframe, limit)
        
        # 计算平均分
        avg_score = sum(s['score'] for s in scores) / len(scores) if scores else 0
        
        return jsonify({
            'success': True,
            'data': {
                'scores': scores,
                'total_coins': len(scores),
                'average_score': round(avg_score, 2),
                'timeframe': f'{timeframe}h'
            }
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/depth-chart-data')
def api_depth_chart_data():
    """获取深度图表数据"""
    try:
        timeframe = int(request.args.get('timeframe', 24))
        top_n = int(request.args.get('top_n', 20))
        
        calculator = ScoreCalculator()
        chart_data = calculator.get_depth_chart_data(timeframe, top_n)
        
        return jsonify({
            'success': True,
            'data': chart_data
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/market-average-score')
def api_market_average_score():
    """获取市场平均得分"""
    try:
        timeframe = int(request.args.get('timeframe', 24))
        
        calculator = ScoreCalculator()
        market_score = calculator.calculate_average_market_score(timeframe)
        
        return jsonify({
            'success': True,
            'data': market_score
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/okex-crypto-index')
def api_okex_crypto_index():
    """获取OKEX加密货币指数"""
    try:
        calculator = ScoreCalculator()
        index_data = calculator.calculate_okex_crypto_index()
        
        return jsonify({
            'success': True,
            'data': index_data
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

# ============================================================================
# OKEX加密指数页面专用API端点
# ============================================================================

@app.route('/api/index/start', methods=['POST'])
def api_index_start():
    """启动指数监控"""
    return jsonify({
        'success': True,
        'message': '指数监控已启动'
    })

@app.route('/api/index/current')
def api_index_current():
    """获取当前指数值 - 从JSONL读取最新数据（含4/12/24/48小时平均位置）"""
    try:
        # 获取最新K线数据
        latest = crypto_index_manager.get_latest()
        
        if not latest:
            return jsonify({
                'success': False,
                'message': '暂无数据'
            })
        
        # 提取数据
        timestamp = latest.get('timestamp', '')
        index_value = latest.get('index_value', 1000.0)
        open_price = latest.get('open_price', index_value)
        high_price = latest.get('high_price', index_value)
        low_price = latest.get('low_price', index_value)
        close_price = latest.get('close_price', index_value)
        
        # 平均位置
        position_4h = latest.get('position_4h', 50.0)
        position_12h = latest.get('position_12h', 50.0)
        position_24h = latest.get('position_24h', 50.0)
        position_48h = latest.get('position_48h', 50.0)
        
        # 计算涨跌
        base_value = 1000.0
        change = close_price - base_value
        change_percent = (change / base_value) * 100
        
        return jsonify({
            'success': True,
            'data': {
                'value': round(close_price, 2),
                'base_value': base_value,
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
                'timestamp': timestamp,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'position_4h': round(position_4h, 2),
                'position_12h': round(position_12h, 2),
                'position_24h': round(position_24h, 2),
                'position_48h': round(position_48h, 2),
                'data_source': 'CoinGecko API (JSONL)',
                'valid_components': 27
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/index/klines')
def api_index_klines():
    """获取K线历史数据"""
    try:
        limit = int(request.args.get('limit', 100))
        
        # 从JSONL获取K线数据
        klines = crypto_index_manager.get_klines(limit=limit)
        
        if not klines:
            return jsonify({
                'success': False,
                'message': '暂无K线数据'
            })
        
        return jsonify({
            'success': True,
            'count': len(klines),
            'data': klines
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/index/components')
def api_index_components():
    """获取成分详情 - 27币种权重明细（从JSONL和CoinGecko）"""
    try:
        # 币种权重配置
        COIN_WEIGHTS = {
            'bitcoin': 0.10,      # BTC 10%
            'ethereum': 0.07,     # ETH 7%
            'ripple': 0.0332,     # XRP 3.32%
            'binancecoin': 0.0332,  # BNB 3.32%
            'solana': 0.0332,     # SOL 3.32%
            'litecoin': 0.0332,   # LTC 3.32%
            'dogecoin': 0.0332,   # DOGE 3.32%
            'sui': 0.0332,        # SUI 3.32%
            'tron': 0.0332,       # TRX 3.32%
            'the-open-network': 0.0332,  # TON 3.32%
            'ethereum-classic': 0.0332,  # ETC 3.32%
            'bitcoin-cash': 0.0332,      # BCH 3.32%
            'hedera-hashgraph': 0.0332,  # HBAR 3.32%
            'stellar': 0.0332,    # XLM 3.32%
            'filecoin': 0.0332,   # FIL 3.32%
            'chainlink': 0.0332,  # LINK 3.32%
            'crypto-com-chain': 0.0332,  # CRO 3.32%
            'polkadot': 0.0332,   # DOT 3.32%
            'aave': 0.0332,       # AAVE 3.32%
            'uniswap': 0.0332,    # UNI 3.32%
            'near': 0.0332,       # NEAR 3.32%
            'aptos': 0.0332,      # APT 3.32%
            'conflux-token': 0.0332,     # CFX 3.32%
            'curve-dao-token': 0.0332,   # CRV 3.32%
            'stacks': 0.0332,     # STX 3.32%
            'lido-dao': 0.0332,   # LDO 3.32%
            'bittensor': 0.0332   # TAO 3.32%
        }
        
        # 币种名称映射
        coin_name_map = {
            'bitcoin': 'BTC', 'ethereum': 'ETH', 'ripple': 'XRP',
            'binancecoin': 'BNB', 'solana': 'SOL', 'litecoin': 'LTC',
            'dogecoin': 'DOGE', 'sui': 'SUI', 'tron': 'TRX',
            'the-open-network': 'TON', 'ethereum-classic': 'ETC',
            'bitcoin-cash': 'BCH', 'hedera-hashgraph': 'HBAR',
            'stellar': 'XLM', 'filecoin': 'FIL', 'chainlink': 'LINK',
            'crypto-com-chain': 'CRO', 'polkadot': 'DOT', 'aave': 'AAVE',
            'uniswap': 'UNI', 'near': 'NEAR', 'aptos': 'APT',
            'conflux-token': 'CFX', 'curve-dao-token': 'CRV',
            'stacks': 'STX', 'lido-dao': 'LDO', 'bittensor': 'TAO'
        }
        
        # 获取基准价格（从JSONL）
        base_prices = crypto_index_manager.get_base_prices()
        
        # 获取当前价格（从CoinGecko）
        import requests
        current_prices = {}
        try:
            coin_ids = ','.join(COIN_WEIGHTS.keys())
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={'ids': coin_ids, 'vs_currencies': 'usd', 'precision': '8'},
                timeout=10
            )
            if response.status_code == 200:
                current_prices = response.json()
        except Exception as e:
            print(f"获取CoinGecko价格失败: {e}")
        
        # 构建成分数据
        components = []
        for coin_id, weight in COIN_WEIGHTS.items():
            symbol = coin_name_map.get(coin_id, coin_id.upper())
            base_price = base_prices.get(coin_id, 0)
            current_price = current_prices.get(coin_id, {}).get('usd', base_price)
            
            # 计算涨跌幅
            if base_price > 0:
                price_change = ((current_price - base_price) / base_price * 100)
            else:
                price_change = 0
            
            # 加权贡献
            weighted_contribution = price_change * weight
            
            components.append({
                'symbol': symbol,
                'name': symbol,
                'coin_id': coin_id,
                'price': round(current_price, 8),
                'base_price': round(base_price, 8),
                'weight': weight,
                'weight_percent': f"{weight*100:.2f}%",
                'change_percent': round(price_change, 2),
                'weighted_contribution': round(weighted_contribution, 4)
            })
        
        # 按权重降序排序
        components.sort(key=lambda x: x['weight'], reverse=True)
        
        return jsonify({
            'success': True,
            'total_coins': len(components),
            'data': components,
            'data_source': 'CoinGecko API + JSONL'
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'获取成分失败: {str(e)}',
            'traceback': traceback.format_exc()
        })

@app.route('/test-refresh')
def test_refresh():
    """测试刷新页面 - 用于验证缓存问题"""
    return render_template('test_refresh.html')

@app.route('/test-btc-eth')
def test_btc_eth():
    """测试BTC和ETH数据显示"""
    return render_template('test_btc_eth.html')

@app.route('/api/index/history')
def api_index_history():
    """获取历史数据 - 从crypto_index JSONL读取K线历史数据"""
    try:
        page = int(request.args.get('page', 1))  # 当前页，默认第1页
        page_size = 144  # 每页144条（12小时数据，每5分钟1条）
        
        # 从crypto_index_manager获取K线数据
        all_klines = crypto_index_manager.get_klines(limit=1000)  # 获取最近1000根K线
        
        if not all_klines:
            return jsonify({
                'success': False,
                'message': '暂无历史数据'
            })
        
        # K线数据已经是按时间倒序排序的，需要反转为正序（从旧到新）
        all_klines.reverse()
        
        # 计算分页
        total_records = len(all_klines)
        total_pages = max(1, (total_records + page_size - 1) // page_size)
        
        # 确保页码有效
        if page < 1:
            page = 1
        if page > total_pages:
            page = total_pages
        
        # 倒序分页：page=1显示最新数据
        reverse_page = total_pages - page + 1
        start_idx = (reverse_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_records)
        page_klines = all_klines[start_idx:end_idx]
        
        # 转换为历史数据格式
        history = []
        base_value = 1000.00
        
        for kline in page_klines:
            close_price = kline.get('close_price', kline.get('index_value', base_value))
            change_percent = ((close_price - base_value) / base_value * 100)
            
            history.append({
                'time': kline.get('timestamp', ''),
                'value': round(close_price, 2),
                'close': round(close_price, 2),
                'change_percent': round(change_percent, 2),
                'open': round(kline.get('open_price', close_price), 2),
                'high': round(kline.get('high_price', close_price), 2),
                'low': round(kline.get('low_price', close_price), 2),
                'position_4h': kline.get('position_4h', 50.0),
                'position_12h': kline.get('position_12h', 50.0),
                'position_24h': kline.get('position_24h', 50.0),
                'position_48h': kline.get('position_48h', 50.0)
            })
        
        return jsonify({
            'success': True,
            'total': len(history),
            'total_records': total_records,
            'total_pages': total_pages,
            'current_page': page,
            'page_size': page_size,
            'interval': '5min',
            'data': history,
            'data_source': 'Crypto Index JSONL'
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': f'获取历史数据失败: {str(e)}',
            'traceback': traceback.format_exc()
        })

# ==================== 位置系统 API ====================

@app.route('/position-system')
def position_system():
    """位置系统页面"""
    return render_template('position_system.html')

@app.route('/api/position/latest')
def api_position_latest():
    """获取最新位置数据"""
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 获取最新的记录时间
        cursor.execute('SELECT MAX(record_time) FROM position_system')
        latest_time = cursor.fetchone()[0]
        
        if not latest_time:
            return jsonify({
                'success': False,
                'message': '暂无数据'
            })
        
        # 获取该时间的所有币种数据
        cursor.execute('''
            SELECT symbol, current_price,
                   position_4h, position_12h, position_24h, position_48h,
                   high_4h, low_4h, high_12h, low_12h, high_24h, low_24h, high_48h, low_48h
            FROM position_system
            WHERE record_time = ?
            ORDER BY symbol
        ''', (latest_time,))
        
        rows = cursor.fetchall()
        
        # 构造返回数据
        data_list = []
        symbol_set = set()
        for row in rows:
            symbol_set.add(row[0])
            data_list.append({
                'symbol': row[0],
                'current_price': row[1],
                'position_4h': row[2],
                'position_12h': row[3],
                'position_24h': row[4],
                'position_48h': row[5],
                'high_4h': row[6],
                'low_4h': row[7],
                'high_12h': row[8],
                'low_12h': row[9],
                'high_24h': row[10],
                'low_24h': row[11],
                'high_48h': row[12],
                'low_48h': row[13]
            })
        
        # 检查BTC和ETH是否存在，如果不存在则从最近记录中补充
        missing_coins = []
        if 'BTC-USDT-SWAP' not in symbol_set:
            missing_coins.append('BTC-USDT-SWAP')
        if 'ETH-USDT-SWAP' not in symbol_set:
            missing_coins.append('ETH-USDT-SWAP')
        
        if missing_coins:
            for coin in missing_coins:
                cursor.execute('''
                    SELECT symbol, current_price,
                           position_4h, position_12h, position_24h, position_48h,
                           high_4h, low_4h, high_12h, low_12h, high_24h, low_24h, high_48h, low_48h
                    FROM position_system
                    WHERE symbol = ?
                    ORDER BY record_time DESC
                    LIMIT 1
                ''', (coin,))
                coin_row = cursor.fetchone()
                if coin_row:
                    data_list.append({
                        'symbol': coin_row[0],
                        'current_price': coin_row[1],
                        'position_4h': coin_row[2],
                        'position_12h': coin_row[3],
                        'position_24h': coin_row[4],
                        'position_48h': coin_row[5],
                        'high_4h': coin_row[6],
                        'low_4h': coin_row[7],
                        'high_12h': coin_row[8],
                        'low_12h': coin_row[9],
                        'high_24h': coin_row[10],
                        'low_24h': coin_row[11],
                        'high_48h': coin_row[12],
                        'low_48h': coin_row[13]
                    })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'record_time': latest_time,
            'total_count': len(data_list),
            'data': data_list
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取数据失败: {str(e)}'
        })

@app.route('/api/position/summary')
def api_position_summary():
    """获取位置统计摘要"""
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 获取最新的记录时间
        cursor.execute('SELECT MAX(record_time) FROM position_system')
        latest_time = cursor.fetchone()[0]
        
        if not latest_time:
            return jsonify({
                'success': False,
                'message': '暂无数据'
            })
        
        # 统计各周期的平均位置
        cursor.execute('''
            SELECT 
                AVG(position_4h) as avg_4h,
                AVG(position_12h) as avg_12h,
                AVG(position_24h) as avg_24h,
                AVG(position_48h) as avg_48h,
                COUNT(*) as total_count
            FROM position_system
            WHERE record_time = ?
        ''', (latest_time,))
        
        row = cursor.fetchone()
        
        # 统计各区间的币种数量（以24h为例）
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN position_24h >= 80 THEN 1 ELSE 0 END) as high_zone,
                SUM(CASE WHEN position_24h >= 50 AND position_24h < 80 THEN 1 ELSE 0 END) as mid_high_zone,
                SUM(CASE WHEN position_24h >= 20 AND position_24h < 50 THEN 1 ELSE 0 END) as mid_low_zone,
                SUM(CASE WHEN position_24h < 20 THEN 1 ELSE 0 END) as low_zone
            FROM position_system
            WHERE record_time = ?
        ''', (latest_time,))
        
        zone_counts = cursor.fetchone()
        
        # 新增：统计各周期>=95%的币种数量
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN position_4h >= 95 THEN 1 ELSE 0 END) as count_4h_ge95,
                SUM(CASE WHEN position_12h >= 95 THEN 1 ELSE 0 END) as count_12h_ge95,
                SUM(CASE WHEN position_24h >= 95 THEN 1 ELSE 0 END) as count_24h_ge95,
                SUM(CASE WHEN position_48h >= 95 THEN 1 ELSE 0 END) as count_48h_ge95
            FROM position_system
            WHERE record_time = ?
        ''', (latest_time,))
        
        ge95_counts = cursor.fetchone()
        conn.close()
        
        return jsonify({
            'success': True,
            'record_time': latest_time,
            'averages': {
                '4h': round(row[0], 2) if row[0] else 0,
                '12h': round(row[1], 2) if row[1] else 0,
                '24h': round(row[2], 2) if row[2] else 0,
                '48h': round(row[3], 2) if row[3] else 0
            },
            'total_count': row[4],
            'zone_distribution_24h': {
                'high': zone_counts[0] or 0,      # 80-100%
                'mid_high': zone_counts[1] or 0,  # 50-80%
                'mid_low': zone_counts[2] or 0,   # 20-50%
                'low': zone_counts[3] or 0        # 0-20%
            },
            'high_position_counts': {
                '4h': ge95_counts[0] or 0,   # 4小时>=95%
                '12h': ge95_counts[1] or 0,  # 12小时>=95%
                '24h': ge95_counts[2] or 0,  # 24小时>=95%
                '48h': ge95_counts[3] or 0   # 48小时>=95%
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取统计失败: {str(e)}'
        })

@app.route('/api/position/history/<symbol>')
def api_position_history(symbol):
    """获取指定币种的历史位置数据"""
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 获取最近24小时的数据
        cursor.execute('''
            SELECT record_time, current_price,
                   position_4h, position_12h, position_24h, position_48h
            FROM position_system
            WHERE symbol = ?
            ORDER BY record_time DESC
            LIMIT 288
        ''', (symbol,))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'time': row[0],
                'price': row[1],
                '4h': row[2],
                '12h': row[3],
                '24h': row[4],
                '48h': row[5]
            })
        
        history.reverse()  # 时间正序
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'data': history
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取历史失败: {str(e)}'
        })

@app.route('/api/position/stats/latest')
def api_position_stats_latest():
    """获取最新的位置统计数据（低于1%的币种数量）"""
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 获取最新的统计数据
        cursor.execute('''
            SELECT record_time, count_below_1_4h, count_below_1_12h, 
                   count_below_1_24h, count_below_1_48h, total_coins
            FROM position_system_stats
            ORDER BY record_time DESC
            LIMIT 1
        ''')
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({
                'success': False,
                'message': '暂无统计数据'
            })
        
        return jsonify({
            'success': True,
            'record_time': row[0],
            'stats': {
                '4h': {'below_1': row[1], 'total': row[5]},
                '12h': {'below_1': row[2], 'total': row[5]},
                '24h': {'below_1': row[3], 'total': row[5]},
                '48h': {'below_1': row[4], 'total': row[5]}
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取统计数据失败: {str(e)}'
        })

@app.route('/api/position/stats/history')
def api_position_stats_history():
    """获取统计数据历史记录"""
    try:
        # 获取查询参数
        limit = request.args.get('limit', default=100, type=int)
        start_time = request.args.get('start_time', default=None, type=str)
        end_time = request.args.get('end_time', default=None, type=str)
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 构建查询条件
        query = '''
            SELECT record_time, count_below_1_4h, count_below_1_12h, 
                   count_below_1_24h, count_below_1_48h, total_coins
            FROM position_system_stats
            WHERE 1=1
        '''
        params = []
        
        if start_time:
            query += ' AND record_time >= ?'
            params.append(start_time)
        
        if end_time:
            query += ' AND record_time <= ?'
            params.append(end_time)
        
        query += ' ORDER BY record_time DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'time': row[0],
                '4h': {'below_1': row[1], 'total': row[5]},
                '12h': {'below_1': row[2], 'total': row[5]},
                '24h': {'below_1': row[3], 'total': row[5]},
                '48h': {'below_1': row[4], 'total': row[5]}
            })
        
        history.reverse()  # 时间正序
        
        return jsonify({
            'success': True,
            'count': len(history),
            'data': history
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取历史统计失败: {str(e)}'
        })

@app.route('/v1v2-volume')
def v1v2_volume():
    """V1V2成交量系统页面"""
    return render_template('v1v2_volume.html')

@app.route('/v1v2-monitor')
def v1v2_monitor():
    """V1V2成交额监控页面"""
    return render_template('v1v2_monitor.html')

@app.route('/api/v1v2/latest')
def api_v1v2_latest():
    """获取所有币种的最新V1V2数据 - 使用JSONL"""
    try:
        # 从JSONL获取最新数据
        result = v1v2_manager.get_latest_all()
        
        # 按级别排序: V1 > V2 > NONE
        level_order = {'V1': 0, 'V2': 1, 'NONE': 2}
        result.sort(key=lambda x: (level_order.get(x['level'], 3), -x.get('volume', 0)))
        
        # 获取统计信息
        stats = v1v2_manager.get_statistics()
        
        return jsonify({
            'success': True,
            'count': stats['total_count'],
            'data': result,
            'update_time': stats['update_time'],
            'total': stats['total_count'],
            'v1_count': stats['v1_count'],
            'v2_count': stats['v2_count']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'data': [],
            'message': f'获取V1V2数据失败: {str(e)}'
        })

@app.route('/v1v2-settings')
def v1v2_settings():
    """V1V2阈值设置页面"""
    return render_template('v1v2_settings.html')

@app.route('/api/v1v2/settings', methods=['GET', 'POST'])
def api_v1v2_settings():
    """获取或更新V1V2阈值设置"""
    import json
    import os
    
    SETTINGS_FILE = 'v1v2_settings.json'
    
    # 默认配置
    DEFAULT_SETTINGS = {
        'BTC': {'v1': 200000, 'v2': 100000},
        'ETH': {'v1': 1300000, 'v2': 500000},
        'XRP': {'v1': 200000, 'v2': 87000},
        'SOL': {'v1': 351620, 'v2': 246380},
        'BNB': {'v1': 2388300, 'v2': 1737500},
        'LTC': {'v1': 50000, 'v2': 15000},
        'DOGE': {'v1': 150000, 'v2': 60000},
        'SUI': {'v1': 2000000, 'v2': 800000},
        'TRX': {'v1': 13280, 'v2': 6022},
        'TON': {'v1': 350000, 'v2': 200000},
        'ETC': {'v1': 12000, 'v2': 2000},
        'BCH': {'v1': 103500, 'v2': 50000},
        'HBAR': {'v1': 103500, 'v2': 40000},
        'XLM': {'v1': 103500, 'v2': 30000},
        'FIL': {'v1': 5003500, 'v2': 3700000},
        'ADA': {'v1': 67210, 'v2': 44230},
        'LINK': {'v1': 280000, 'v2': 200000},
        'CRO': {'v1': 100000, 'v2': 40000},
        'DOT': {'v1': 300000, 'v2': 250000},
        'UNI': {'v1': 140000, 'v2': 100000},
        'NEAR': {'v1': 100000, 'v2': 50000},
        'APT': {'v1': 300000, 'v2': 200000},
        'CFX': {'v1': 300000, 'v2': 250000},
        'CRV': {'v1': 1500000, 'v2': 1000000},
        'STX': {'v1': 50000, 'v2': 30000},
        'LDO': {'v1': 1000000, 'v2': 600000},
        'TAO': {'v1': 300000, 'v2': 180000}
    }
    
    if request.method == 'GET':
        # 读取设置
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            else:
                settings = DEFAULT_SETTINGS
                # 保存默认设置
                with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
            
            return jsonify({
                'success': True,
                'settings': settings
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'读取设置失败: {str(e)}'
            })
    
    elif request.method == 'POST':
        # 更新设置
        try:
            data = request.get_json()
            new_settings = data.get('settings', {})
            
            # 验证数据
            for symbol, config in new_settings.items():
                if 'v1' not in config or 'v2' not in config:
                    return jsonify({
                        'success': False,
                        'message': f'币种 {symbol} 配置不完整'
                    })
                
                # 确保V1 > V2
                if config['v1'] <= config['v2']:
                    return jsonify({
                        'success': False,
                        'message': f'币种 {symbol}: V1阈值必须大于V2阈值'
                    })
            
            # 保存设置
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(new_settings, f, indent=2, ensure_ascii=False)
            
            # 触发采集器重新加载配置（通过创建标记文件）
            with open('.v1v2_settings_updated', 'w') as f:
                f.write(str(int(time.time())))
            
            return jsonify({
                'success': True,
                'message': '设置已保存，采集器将在下次采集时使用新配置'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'保存设置失败: {str(e)}'
            })

@app.route('/api/v1v2/statistics')
def api_v1v2_statistics():
    """获取V1V2信号统计数据（1h/3h/12h/1day/3day/7day）"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        conn = sqlite3.connect('v1v2_data.db', timeout=30.0)
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        cursor = conn.cursor()
        
        # 获取所有币种表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'volume_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # 定义时间范围
        now = datetime.now()
        time_ranges = {
            '1h': now - timedelta(hours=1),
            '3h': now - timedelta(hours=3),
            '12h': now - timedelta(hours=12),
            '1day': now - timedelta(days=1),
            '3day': now - timedelta(days=3),
            '7day': now - timedelta(days=7)
        }
        
        statistics = []
        
        for table_name in tables:
            symbol = table_name.replace('volume_', '').upper()
            
            try:
                coin_stats = {
                    'symbol': symbol,
                    '1h': {'v1': 0, 'v2': 0, 'total': 0},
                    '3h': {'v1': 0, 'v2': 0, 'total': 0},
                    '12h': {'v1': 0, 'v2': 0, 'total': 0},
                    '1day': {'v1': 0, 'v2': 0, 'total': 0},
                    '3day': {'v1': 0, 'v2': 0, 'total': 0},
                    '7day': {'v1': 0, 'v2': 0, 'total': 0}
                }
                
                # 对每个时间范围进行统计
                for period, start_time in time_ranges.items():
                    start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 统计V1和V2的次数（只统计V1和V2）
                    cursor.execute(f"""
                        SELECT level, COUNT(*) 
                        FROM {table_name} 
                        WHERE collect_time >= ? AND level IN ('V1', 'V2')
                        GROUP BY level
                    """, (start_time_str,))
                    
                    counts = dict(cursor.fetchall())
                    v1_count = counts.get('V1', 0)
                    v2_count = counts.get('V2', 0)
                    
                    coin_stats[period]['v1'] = v1_count
                    coin_stats[period]['v2'] = v2_count
                    coin_stats[period]['total'] = v1_count + v2_count
                
                statistics.append(coin_stats)
                
            except sqlite3.OperationalError:
                # 表不存在或出错，跳过
                continue
        
        conn.close()
        
        # 按7天总信号数排序
        statistics.sort(key=lambda x: x['7day']['total'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': {
                'statistics': statistics,
                'update_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'total_coins': len(statistics)
            }
        })
        
    except Exception as e:
        import traceback
        print(f"❌ V1V2统计API错误: {str(e)}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'获取统计数据失败: {str(e)}'
        }), 500

@app.route('/price-speed-monitor')
def price_speed_monitor():
    """1分钟涨跌速监控页面"""
    return render_template('price_speed_monitor.html')

@app.route('/api/price-speed/latest')
def api_price_speed_latest():
    """获取所有币种的最新涨跌速数据 - 使用JSONL"""
    try:
        # 从JSONL获取最新数据
        data = price_speed_manager.get_latest_all()
        
        # 获取统计信息
        stats = price_speed_manager.get_statistics()
        
        return jsonify({
            'success': True,
            'count': len(data),
            'data': data,
            'update_time': stats['update_time']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取涨跌速数据失败: {str(e)}',
            'data': []
        })

@app.route('/api/price-speed/history/<symbol>')
def api_price_speed_history(symbol):
    """获取指定币种的历史涨跌速数据 - 使用JSONL"""
    try:
        # 获取查询参数
        limit = request.args.get('limit', 100, type=int)
        
        # 从JSONL获取历史数据
        data = price_speed_manager.get_history(symbol=symbol, limit=limit)
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取历史数据失败: {str(e)}',
            'data': []
        })

# ============================================================================
# Google Drive TXT检测器 API
# ============================================================================

@app.route('/gdrive-detector')
def gdrive_detector_page():
    """Google Drive检测器页面"""
    return render_template('gdrive_detector.html')

@app.route('/test-gdrive-status')
def test_gdrive_status():
    """Google Drive状态测试页面"""
    return render_template('test_gdrive_status.html')

@app.route('/gdrive-detector-fresh')
def gdrive_detector_fresh():
    """Google Drive检测器页面（无缓存版本）"""
    import time
    return render_template('gdrive_detector_fresh.html', timestamp=int(time.time()))

@app.route('/opening-logic')
def opening_logic_page():
    """开仓逻辑系统页面"""
    from flask import make_response
    response = make_response(render_template('opening_logic.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/opening-logic/suggestion')
def opening_logic_suggestion():
    """获取开仓建议API"""
    try:
        from opening_logic import get_opening_suggestion
        result = get_opening_suggestion()
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/gdrive-detector/status')
def gdrive_detector_status():
    """获取Google Drive检测器状态"""
    try:
        import subprocess
        import re
        import requests
        from datetime import datetime
        import pytz
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        
        # 检查检测器进程是否运行
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        detector_running = ('gdrive_txt_detector.py' in result.stdout or 
                          'gdrive_final_detector.py' in result.stdout or
                          'gdrive_smart_detector.py' in result.stdout)
        
        # 从数据库读取最新数据时间戳
        file_timestamp = None
        delay_minutes = None
        
        try:
            import sqlite3
            db_path = '/home/user/webapp/databases/crypto_data.db'
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT snapshot_time FROM crypto_snapshots ORDER BY created_at DESC LIMIT 1")
            result = cursor.fetchone()
            conn.close()
            
            if result:
                file_timestamp = result[0]
                # 计算延迟 - 数据库时间是北京时间
                try:
                    last_time = datetime.strptime(file_timestamp, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    last_time = datetime.strptime(file_timestamp, '%Y-%m-%d %H:%M:%S.%f')
                
                # 数据库存储的是北京时间，直接与北京时间比较
                last_time_beijing = beijing_tz.localize(last_time)
                delay_seconds = (now - last_time_beijing).total_seconds()
                delay_minutes = delay_seconds / 60
        except:
            pass
        
        # 读取日志获取检查次数
        check_count = 0
        last_check_time = None
        try:
            with open('/home/user/webapp/gdrive_final_detector.log', 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if '检查 #' in line:
                        match = re.search(r'检查 #(\d+)', line)
                        if match:
                            check_count = int(match.group(1))
                    if re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line):
                        # 提取时间戳
                        match = re.search(r'(2025-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                        if match:
                            last_check_time = match.group(1)
        except:
            pass
        
        # 从配置文件读取所有文件夹ID
        root_folder_odd = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"  # 默认值
        root_folder_even = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"  # 默认值
        folder_id = None  # 子账号文件夹ID（今日文件夹）
        
        try:
            import json
            config_file = '/home/user/webapp/daily_folder_config.json'
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 读取单数/双数父文件夹ID
                if 'root_folder_odd' in config:
                    root_folder_odd = config['root_folder_odd']
                if 'root_folder_even' in config:
                    root_folder_even = config['root_folder_even']
                # 🆕 读取子账号文件夹ID（今日文件夹）
                if 'folder_id' in config:
                    folder_id = config['folder_id']
        except:
            pass
        
        # 如果配置文件中没有子账号文件夹ID，尝试从日志读取
        if not folder_id:
            try:
                with open('/home/user/webapp/gdrive_final_detector.log', 'r') as f:
                    lines = f.readlines()
                    for line in reversed(lines[-100:]):  # 只看最近100行
                        # 提取文件夹ID（子账号）
                        if '今日文件夹' in line or '子文件夹' in line:
                            match = re.search(r'([A-Za-z0-9_-]{20,})', line)
                            if match and match.group(1) != root_folder_odd and match.group(1) != root_folder_even:
                                folder_id = match.group(1)
                                break
            except:
                pass
        
        return jsonify({
            'success': True,
            'data': {
                'detector_running': detector_running,
                'file_timestamp': file_timestamp,
                'delay_minutes': delay_minutes,
                'check_count': check_count,
                'last_check_time': last_check_time,
                'current_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'folder_id': folder_id,
                'root_folder_odd': root_folder_odd,
                'root_folder_even': root_folder_even,
                'today_date': now.strftime('%Y年%m月%d日')
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'data': None
        })

@app.route('/api/gdrive-detector/txt-files')
def gdrive_detector_txt_files():
    """获取今天的TXT文件列表（带缓存优化）"""
    try:
        import requests
        import re
        from datetime import datetime
        import pytz
        import json
        import time
        
        # 缓存机制：5分钟内返回缓存数据
        cache_file = '/tmp/gdrive_txt_files_cache.json'
        cache_duration = 300  # 5分钟
        
        # 尝试读取缓存
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    cache_time = cache_data.get('timestamp', 0)
                    if time.time() - cache_time < cache_duration:
                        # 返回缓存数据
                        return jsonify(cache_data.get('data', {}))
        except:
            pass
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        today = datetime.now(beijing_tz).strftime('%Y-%m-%d')
        
        # 从配置文件读取今天的文件夹ID
        folder_id = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"  # 默认值
        try:
            config_file = '/home/user/webapp/daily_folder_config.json'
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if config.get('current_date') == today and 'folder_id' in config:
                    folder_id = config['folder_id']
        except:
            pass
        
        url = f"https://drive.google.com/embeddedfolderview?id={folder_id}"
        
        response = requests.get(url, timeout=10)
        content = response.text
        
        # 查找今天所有的TXT文件
        pattern = rf'>{today}_(\d{{4}})\.txt<'
        matches = re.findall(pattern, content)
        
        # 排序（从新到旧）
        times_sorted = sorted(matches, reverse=True)
        filenames = [f"{today}_{time}.txt" for time in times_sorted]
        
        result = {
            'success': True,
            'files': filenames,
            'count': len(filenames),
            'date': today,
            'folder_id': folder_id
        }
        
        # 保存到缓存
        try:
            cache_content = {
                'timestamp': time.time(),
                'data': result
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_content, f, ensure_ascii=False, indent=2)
        except:
            pass
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'files': [],
            'count': 0
        })

@app.route('/api/gdrive-detector/logs')
def gdrive_detector_logs():
    """获取检测器日志"""
    try:
        lines = request.args.get('lines', 50, type=int)
        
        # 尝试多个日志文件
        log_files = [
            '/home/user/webapp/gdrive_final_detector.log',
            '/home/user/webapp/gdrive_txt_detector.log',
            '/home/user/webapp/gdrive_smart_detector.log'
        ]
        
        log_content = None
        total_lines = 0
        
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    all_lines = f.readlines()
                    log_content = ''.join(all_lines[-lines:] if len(all_lines) > lines else all_lines)
                    total_lines = len(all_lines)
                    break
            except FileNotFoundError:
                continue
        
        if log_content is not None:
            return jsonify({
                'success': True,
                'logs': log_content,
                'total_lines': total_lines
            })
        else:
            return jsonify({
                'success': True,
                'logs': '日志文件不存在',
                'total_lines': 0
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'logs': ''
        })

@app.route('/api/gdrive-detector/config', methods=['GET'])
def gdrive_detector_get_config():
    """获取Google Drive配置"""
    try:
        import json
        config_file = '/home/user/webapp/daily_folder_config.json'
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/gdrive-detector/config', methods=['POST'])
def gdrive_detector_update_config():
    """更新Google Drive配置（父文件夹共享链接）"""
    try:
        import json
        import re
        import requests
        from datetime import datetime
        import pytz
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        
        data = request.get_json()
        parent_folder_url = data.get('parent_folder_url', '')
        
        # 从URL中提取文件夹ID
        match = re.search(r'folders/([A-Za-z0-9_-]+)', parent_folder_url)
        if not match:
            return jsonify({
                'success': False,
                'message': '无效的Google Drive文件夹链接'
            })
        
        parent_folder_id = match.group(1)
        
        # 获取父文件夹内的今日文件夹
        today_str = now.strftime('%Y-%m-%d')
        url = f"https://drive.google.com/embeddedfolderview?id={parent_folder_id}"
        response = requests.get(url, timeout=10)
        content = response.text
        
        # 查找今日日期文件夹
        folder_pattern = rf'>{today_str}<'
        if today_str not in content:
            return jsonify({
                'success': False,
                'message': f'父文件夹中未找到今日文件夹: {today_str}'
            })
        
        # 提取今日文件夹ID
        # 查找包含今日日期的文件夹链接
        folder_id_pattern = rf'"([A-Za-z0-9_-]{{20,}})"[^>]*>{today_str}<'
        folder_match = re.search(folder_id_pattern, content)
        
        if not folder_match:
            # 尝试另一种模式
            folder_id_pattern = rf'https://drive\.google\.com/drive/folders/([A-Za-z0-9_-]+)[^>]*>{today_str}<'
            folder_match = re.search(folder_id_pattern, content)
        
        if not folder_match:
            return jsonify({
                'success': False,
                'message': f'无法从父文件夹中提取今日文件夹ID: {today_str}'
            })
        
        today_folder_id = folder_match.group(1)
        
        # 验证今日文件夹是否包含TXT文件
        txt_url = f"https://drive.google.com/embeddedfolderview?id={today_folder_id}"
        txt_response = requests.get(txt_url, timeout=10)
        txt_content = txt_response.text
        
        # 查找TXT文件
        txt_pattern = rf'>{today_str}_(\d{{4}})\.txt<'
        txt_matches = re.findall(txt_pattern, txt_content)
        
        if not txt_matches:
            return jsonify({
                'success': False,
                'message': f'今日文件夹中未找到TXT文件'
            })
        
        # 获取最新的TXT文件
        latest_txt_time = sorted(txt_matches, reverse=True)[0]
        latest_txt = f"{today_str}_{latest_txt_time}.txt"
        
        # 更新配置文件
        config_file = '/home/user/webapp/daily_folder_config.json'
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            config = {}
        
        # 判断今天是单数还是双数日期
        day_of_month = now.day
        is_odd_day = day_of_month % 2 == 1
        
        # 更新配置
        config['parent_folder_url'] = parent_folder_url
        config['parent_folder_id'] = parent_folder_id
        config['current_date'] = today_str
        config['data_date'] = today_str
        config['folder_id'] = today_folder_id
        config['folder_name'] = today_str
        config['latest_txt'] = latest_txt
        config['txt_count'] = len(txt_matches)
        config['last_update'] = now.strftime('%Y-%m-%d %H:%M:%S')
        config['update_reason'] = '通过配置页面更新父文件夹'
        config['last_manual_update'] = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # 根据单双数更新对应的父文件夹ID
        if is_odd_day:
            config['root_folder_odd'] = parent_folder_id
        else:
            config['root_folder_even'] = parent_folder_id
        
        # 保存配置
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': '配置更新成功',
            'data': {
                'parent_folder_id': parent_folder_id,
                'today_folder_id': today_folder_id,
                'today_date': today_str,
                'txt_count': len(txt_matches),
                'latest_txt': latest_txt,
                'is_odd_day': is_odd_day
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/gdrive-detector/trigger-update', methods=['POST'])
def gdrive_detector_trigger_update():
    """触发手动更新检测"""
    try:
        import subprocess
        import time
        
        # 运行检测脚本一次
        result = subprocess.run(
            ['python3', '/home/user/webapp/gdrive_final_detector.py'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return jsonify({
            'success': True,
            'message': '检测已执行',
            'output': result.stdout[:500] if result.stdout else '',
            'error': result.stderr[:500] if result.stderr else ''
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': '检测超时（30秒）'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/gdrive-config')
def gdrive_config_page():
    """Google Drive配置页面"""
    return render_template('gdrive_config.html')

# ==================== 统一监控页面 ====================
@app.route('/unified-monitor')
def unified_monitor():
    """统一采集监控页面"""
    return render_template('unified_monitor.html')

@app.route('/unified-monitor-enhanced')
def monitor_enhanced():
    """统一采集监控页面（增强版）- 带执行日志和开关控制"""
    return render_template('unified_monitor_enhanced.html')

# ==================== 综合采集器监控 API ====================
@app.route('/api/collectors/status')
def api_collectors_status():
    """获取所有采集器的运行状态"""
    try:
        import subprocess
        result = subprocess.run(
            ['python3', 'get_all_collectors_status.py'],
            cwd='/home/user/webapp',
            capture_output=True,
            text=True,
            timeout=10
        )
        status_list = json.loads(result.stdout)
        
        # 统计状态
        total = len(status_list)
        normal = sum(1 for s in status_list if s['status'] == 'normal')
        warning = sum(1 for s in status_list if s['status'] == 'warning')
        error = sum(1 for s in status_list if s['status'] in ['error', 'stopped', 'no_data'])
        
        return jsonify({
            'success': True,
            'collectors': status_list,
            'summary': {
                'total': total,
                'normal': normal,
                'warning': warning,
                'error': error
            },
            'timestamp': datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/favicon.ico')
def favicon():
    """处理favicon请求，避免404错误"""
    return '', 204  # 返回无内容状态码

# ============================================================================
# 币种选择和评分系统
# ============================================================================

@app.route('/coin-pool')
def coin_pool_page():
    """币种池页面 - 从星星系统筛选的优质币种池"""
    response = make_response(render_template('coin_pool.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# ============================================================================
# 支撑压力线系统
# ============================================================================

@app.route('/support-resistance')
def support_resistance_page():
    """支撑压力线系统页面（旧版）"""
    response = make_response(render_template('support_resistance.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/test-chart')
def test_chart():
    """图表测试页面"""
    with open('/home/user/webapp/test_chart_simple.html', 'r', encoding='utf-8') as f:
        content = f.read()
    response = make_response(content)
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response

@app.route('/test-simple')
def test_simple():
    """极简测试页面 - 最小化图表显示测试"""
    response = make_response(render_template('test_simple.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/test-inline')
def test_inline():
    """内联测试页面 - 完全不依赖CDN"""
    response = make_response(render_template('test_inline.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers.pop('ETag', None)
    response.headers.pop('Last-Modified', None)
    return response

@app.route('/clear-cache')
def clear_cache_redirect():
    """清除缓存并跳转 - 终极方案"""
    response = make_response(render_template('clear_cache_redirect.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/force-refresh')
def force_refresh_page():
    """强制刷新页面 - 清除所有浏览器缓存"""
    response = make_response(render_template('force_refresh.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/escape-signal-history')
@app.route('/clear-cache-guide')
def clear_cache_guide():
    """清除缓存引导页面"""
    import time
    response = make_response(render_template('clear_cache.html', timestamp=int(time.time())))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/escape-signal-history-v2')  # v2路由，绕过CDN缓存
def escape_signal_history_page():
    """逃顶信号系统统计 - 历史数据明细页面"""
    import time
    response = make_response(render_template('escape_signal_history.html'))
    # 🔥 强制禁用所有缓存
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, no-transform'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    # 🔥 禁用ETag防止304响应
    response.headers['ETag'] = str(time.time())  # 每次都不同
    response.headers['Last-Modified'] = ''
    # 🔥 添加版本标识
    response.headers['X-Version'] = 'v3.0-final-' + str(int(time.time()))
    return response

# 添加缓存机制
_escape_signal_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 60  # 缓存60秒
}

@app.route('/api/escape-signal-stats/keypoints')
def api_escape_signal_stats_keypoints():
    """获取逃顶信号关键点数据（用于图表快速渲染）- 后端智能采样 + 缓存"""
    import time
    
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from escape_signal_jsonl_manager import EscapeSignalJSONLManager
        
        # 🔥 支持快速模式：只返回最新N个点
        fast_mode = request.args.get('fast', type=str, default='false').lower() == 'true'
        fast_limit = request.args.get('limit', type=int, default=100)
        
        # 检查缓存（只有非快速模式才使用缓存）
        if not fast_mode:
            current_time = time.time()
            if (_escape_signal_cache['data'] is not None and 
                current_time - _escape_signal_cache['timestamp'] < _escape_signal_cache['ttl']):
                # 缓存命中，直接返回
                return jsonify(_escape_signal_cache['data'])
        
        manager = EscapeSignalJSONLManager()
        
        # 读取所有记录
        all_records = manager.read_records(reverse=False)
        
        # 过滤出1月3日之后的数据
        since_date = '2026-01-03 00:00:00'
        filtered_records = [r for r in all_records if r.get('stat_time', '') >= since_date]
        filtered_records = sorted(filtered_records, key=lambda x: x.get('stat_time', ''))
        
        if not filtered_records:
            return jsonify({'success': False, 'message': 'No data available'})
        
        # 🔥 快速模式：只返回最新N个点
        if fast_mode:
            latest_records = filtered_records[-fast_limit:]
            result = {
                'success': True,
                'fast_mode': True,
                'keypoint_count': len(latest_records),
                'total_records': len(filtered_records),
                'data_range': f"{latest_records[0].get('stat_time', '')} ~ {latest_records[-1].get('stat_time', '')}",
                'keypoints': [
                    {
                        'stat_time': r.get('stat_time', ''),
                        'signal_24h_count': r.get('signal_24h_count', 0),
                        'signal_2h_count': r.get('signal_2h_count', 0),
                        'rise_strength_level': r.get('rise_strength_level', 0),
                        'decline_strength_level': r.get('decline_strength_level', 0)
                    }
                    for r in latest_records
                ],
                'max_signal_24h': max(r.get('signal_24h_count', 0) for r in latest_records)
            }
            # Flask会自动处理JSON响应
            return jsonify(result)
        
        total_count = len(filtered_records)
        
        # 智能关键点采样算法
        def extract_keypoints(data, target_points=2000):
            """提取关键点（后端版本）"""
            if len(data) <= target_points:
                return list(range(len(data)))
            
            keypoints = set()
            
            # 1. 计算P99.9阈值
            signal24h_values = [d.get('signal_24h_count', 0) for d in data if d.get('signal_24h_count', 0) > 0]
            if not signal24h_values:
                return list(range(len(data)))
            
            sorted_signals = sorted(signal24h_values)
            p999_idx = int(len(sorted_signals) * 0.999)
            p999 = sorted_signals[p999_idx] if p999_idx < len(sorted_signals) else sorted_signals[-1]
            p95_idx = int(len(sorted_signals) * 0.95)
            p95 = sorted_signals[p95_idx] if p95_idx < len(sorted_signals) else sorted_signals[-1]
            
            # 2. 极端峰值（P99.9以上）
            for i, d in enumerate(data):
                if d.get('signal_24h_count', 0) >= p999:
                    keypoints.add(i)
            
            # 3. 全局极值
            max_val = max(d.get('signal_24h_count', 0) for d in data)
            min_vals = [d.get('signal_24h_count', 0) for d in data if d.get('signal_24h_count', 0) > 0]
            min_val = min(min_vals) if min_vals else 0
            
            for i, d in enumerate(data):
                val = d.get('signal_24h_count', 0)
                if val == max_val or (val == min_val and val > 0):
                    keypoints.add(i)
            
            # 4. 局部峰值（每6小时窗口保留1个显著峰值）
            window_size = 360  # 6小时
            for i in range(0, len(data), window_size):
                window_end = min(i + window_size, len(data))
                window_max = max(
                    (d.get('signal_24h_count', 0), idx) 
                    for idx, d in enumerate(data[i:window_end], start=i)
                )
                if window_max[0] >= p95:  # 只保留超过P95的局部峰值
                    keypoints.add(window_max[1])
            
            # 5. 首尾点
            keypoints.add(0)
            keypoints.add(len(data) - 1)
            
            # 6. 均匀填充到目标点数
            current_count = len(keypoints)
            if current_count < target_points:
                needed = target_points - current_count
                step = max(1, len(data) // needed)
                for i in range(0, len(data), step):
                    if i not in keypoints:
                        keypoints.add(i)
                    if len(keypoints) >= target_points:
                        break
            
            return sorted(list(keypoints))
        
        # 提取关键点索引
        # 支持limit参数控制返回的关键点数量
        target_points = request.args.get('limit', type=int, default=2000)
        target_points = min(target_points, 2000)  # 最多2000个
        target_points = max(target_points, 50)    # 最少50个
        keypoint_indices = extract_keypoints(filtered_records, target_points=target_points)
        
        # 构建关键点数据
        keypoints_data = [
            {
                'stat_time': filtered_records[i].get('stat_time'),
                'signal_24h_count': filtered_records[i].get('signal_24h_count', 0),
                'signal_2h_count': filtered_records[i].get('signal_2h_count', 0),
                'decline_strength_level': filtered_records[i].get('decline_strength_level', 0),
                'rise_strength_level': filtered_records[i].get('rise_strength_level', 0)
            }
            for i in keypoint_indices
        ]
        
        # 计算统计信息
        max_signal_24h = max((r.get('signal_24h_count', 0) or 0) for r in filtered_records)
        max_signal_2h = max((r.get('signal_2h_count', 0) or 0) for r in filtered_records)
        
        result = {
            'success': True,
            'keypoints': keypoints_data,
            'total_records': total_count,
            'keypoint_count': len(keypoints_data),
            'compression_rate': f'{len(keypoints_data) / total_count * 100:.1f}%',
            'max_signal_24h': max_signal_24h,
            'max_signal_2h': max_signal_2h,
            'data_range': f'{filtered_records[0].get("stat_time")} ~ {filtered_records[-1].get("stat_time")}'
        }
        
        # 更新缓存
        _escape_signal_cache['data'] = result
        _escape_signal_cache['timestamp'] = current_time
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/escape-signal-stats/incremental')
def api_escape_signal_stats_incremental():
    """增量更新API - 只返回最新的N条数据（默认10条）"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from escape_signal_jsonl_manager import EscapeSignalJSONLManager
        
        manager = EscapeSignalJSONLManager()
        
        # 获取参数
        limit = request.args.get('limit', type=int, default=10)  # 默认只返回最新10条
        since_time = request.args.get('since', type=str, default=None)  # 可选：从某个时间点之后的数据
        
        # 读取所有记录（正序）
        all_records = manager.read_records(reverse=False)
        
        # 过滤出1月3日之后的数据
        since_date = '2026-01-03 00:00:00'
        filtered_records = [r for r in all_records if r.get('stat_time', '') >= since_date]
        
        # 如果指定了since_time，只返回该时间之后的数据
        if since_time:
            filtered_records = [r for r in filtered_records if r.get('stat_time', '') > since_time]
        
        # 按时间倒序排序，取最新的limit条
        filtered_records = sorted(filtered_records, key=lambda x: x.get('stat_time', ''), reverse=True)[:limit]
        
        # 再按时间正序排序（方便前端追加）
        filtered_records = sorted(filtered_records, key=lambda x: x.get('stat_time', ''))
        
        if not filtered_records:
            return jsonify({
                'success': True,
                'data': [],
                'count': 0,
                'message': 'No new data'
            })
        
        # 构建返回数据
        incremental_data = [
            {
                'stat_time': r.get('stat_time'),
                'signal_24h_count': r.get('signal_24h_count', 0),
                'signal_2h_count': r.get('signal_2h_count', 0),
                'decline_strength_level': r.get('decline_strength_level', 0),
                'rise_strength_level': r.get('rise_strength_level', 0)
            }
            for r in filtered_records
        ]
        
        return jsonify({
            'success': True,
            'data': incremental_data,
            'count': len(incremental_data),
            'latest_time': filtered_records[-1].get('stat_time') if filtered_records else None
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/escape-signal-stats')
def api_escape_signal_stats():
    """获取逃顶信号统计数据（从JSONL读取）- 优化版本"""
    try:
        from datetime import datetime, timedelta
        import numpy as np
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from escape_signal_jsonl_manager import EscapeSignalJSONLManager
        
        manager = EscapeSignalJSONLManager()
        
        # 获取请求参数
        limit = request.args.get('limit', type=int, default=1000)  # 默认限制1000条
        
        # 获取统计信息
        stats_info = manager.get_statistics()
        total_count = stats_info['total_records']
        
        # 读取所有记录
        all_records = manager.read_records(reverse=False)  # 正序读取所有数据
        
        # 过滤出1月3日之后的数据
        since_date = '2026-01-03 00:00:00'
        filtered_records = [r for r in all_records if r.get('stat_time', '') >= since_date]
        
        # 如果指定了limit，只取最近的limit条
        if limit:
            filtered_records = sorted(filtered_records, key=lambda x: x.get('stat_time', ''), reverse=True)[:limit]
        else:
            # 不限制数量，按时间正序排序
            filtered_records = sorted(filtered_records, key=lambda x: x.get('stat_time', ''))
        
        if not filtered_records:
            return jsonify({
                'success': False,
                'message': 'No data available'
            })
        
        # 计算历史最大值（只在这段时间内）
        max_signal_24h = max((r.get('max_signal_24h', 0) or 0) for r in filtered_records)
        max_signal_2h = max((r.get('max_signal_2h', 0) or 0) for r in filtered_records)
        
        # 获取最近24小时的数据用于计算样本数和中位数
        time_24h_ago = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        recent_24h_samples = [
            r.get('signal_24h_count', 0) 
            for r in filtered_records 
            if r.get('stat_time', '') >= time_24h_ago
        ]
        sample_24h_count = len(recent_24h_samples)
        median_24h = int(np.median(recent_24h_samples)) if recent_24h_samples else 0
        
        # 准备图表数据（已经是1月3日之后的了）
        recent_data = [
            {
                'stat_time': r.get('stat_time'),
                'signal_24h_count': r.get('signal_24h_count', 0),
                'signal_2h_count': r.get('signal_2h_count', 0),
                'decline_strength_level': r.get('decline_strength_level', 0),
                'rise_strength_level': r.get('rise_strength_level', 0)
            }
            for r in filtered_records
        ]
        
        # 已经按时间正序排序了（因为reverse后再reverse）
        
        # 获取完整历史记录用于表格（最新的在前）
        history_data = [
            {
                'stat_time': r.get('stat_time'),
                'signal_24h_count': r.get('signal_24h_count', 0),
                'signal_2h_count': r.get('signal_2h_count', 0),
                'decline_strength_level': r.get('decline_strength_level', 0),
                'rise_strength_level': r.get('rise_strength_level', 0)
            }
            for r in filtered_records
        ]
        # 如果有limit，只返回最近的记录
        if limit and len(history_data) > limit:
            history_data = history_data[-limit:]
        history_data.reverse()  # 反转顺序，最新的在前
        
        return jsonify({
            'success': True,
            'total_count': total_count,
            'max_signal_24h': max_signal_24h,
            'max_signal_2h': max_signal_2h,
            'sample_24h_count': sample_24h_count,
            'median_24h': median_24h,
            'recent_data': recent_data,
            'history_data': history_data,
            'data_source': 'JSONL (Full data since 2026-01-03)',
            'timezone': 'Beijing Time (UTC+8)',
            'data_range': f'{filtered_records[0].get("stat_time")} ~ {filtered_records[-1].get("stat_time")}'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/escape-signal-simple')
def escape_signal_simple_page():
    """逃顶信号简洁版页面"""
    response = make_response(render_template('escape_signal_simple.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/escape-signal-simple')
def api_escape_signal_simple():
    """获取逃顶信号数据 - 极简API"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from escape_signal_jsonl_manager import EscapeSignalJSONLManager
        
        manager = EscapeSignalJSONLManager()
        
        # 获取limit参数
        limit = request.args.get('limit', type=int, default=1000)
        
        # 读取最近的记录
        records = manager.read_records(limit=limit, reverse=True)  # 倒序（最新在前）
        
        # 过滤1月3日之后的数据
        since_date = '2026-01-03 00:00:00'
        filtered_records = [r for r in records if r.get('stat_time', '') >= since_date]
        
        # 计算统计信息
        stats_info = manager.get_statistics()
        
        max_24h = max([r.get('signal_24h_count', 0) for r in filtered_records]) if filtered_records else 0
        max_2h = max([r.get('signal_2h_count', 0) for r in filtered_records]) if filtered_records else 0
        
        return jsonify({
            'success': True,
            'total_count': stats_info['total_records'],
            'records': filtered_records,
            'max_signal_24h': max_24h,
            'max_signal_2h': max_2h,
            'data_source': 'JSONL',
            'timezone': 'Beijing Time (UTC+8)'
        })
        
    except Exception as e:
        print(f"❌ API错误: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/escape-signal-stats/dates')
def get_escape_signal_dates():
    """获取逃顶信号可用的日期列表"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from escape_signal_daily_reader import EscapeSignalDailyReader
        
        reader = EscapeSignalDailyReader()
        dates = reader.get_available_dates()
        
        return jsonify({
            'success': True,
            'dates': dates,
            'count': len(dates)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/escape-signal-stats/keypoints-monthly')
def get_escape_signal_keypoints_monthly():
    """获取逃顶信号关键点数据（用于月度总图）"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from escape_signal_daily_reader import EscapeSignalDailyReader
        
        reader = EscapeSignalDailyReader()
        keypoints = reader.get_keypoints()
        
        return jsonify({
            'success': True,
            'data': keypoints,
            'count': len(keypoints)
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/escape-signal-stats/by-date')
def get_escape_signal_by_date():
    """按日期获取逃顶信号数据（用于日线图）"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from escape_signal_daily_reader import EscapeSignalDailyReader
        from datetime import datetime
        
        # 获取日期参数（默认今天）
        date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        
        reader = EscapeSignalDailyReader()
        data = reader.get_date_data(date)
        stats = reader.get_date_statistics(date)
        
        return jsonify({
            'success': True,
            'date': date,
            'data': data,
            'count': len(data),
            'statistics': stats
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/escape-signal-stats/summary')
def get_escape_signal_summary():
    """获取逃顶信号数据总览"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from escape_signal_daily_reader import EscapeSignalDailyReader
        
        reader = EscapeSignalDailyReader()
        summary = reader.get_summary()
        
        return jsonify({
            'success': True,
            'summary': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/trading-signals')
def trading_signals_page():
    """决策-交易信号系统页面"""
    response = make_response(render_template('trading_signals.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def track_trading_signal(symbol, buy_point_type, suggested_position):
    """跟踪交易信号的首次触发时间"""
    from datetime import datetime
    import pytz
    import sqlite3
    
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    
    signal_key = f"{symbol}_{buy_point_type}"
    
    # 使用独立的数据库连接
    conn_track = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
    conn_track.row_factory = sqlite3.Row
    cursor_track = conn_track.cursor()
    
    try:
        # 检查该信号是否已存在
        cursor_track.execute('''
            SELECT id, first_triggered_at, suggested_position 
            FROM trading_signal_history 
            WHERE signal_key = ? AND is_active = 1
        ''', (signal_key,))
        
        existing = cursor_track.fetchone()
        
        if existing:
            # 更新最后更新时间
            cursor_track.execute('''
                UPDATE trading_signal_history 
                SET last_updated_at = ?, suggested_position = ?
                WHERE id = ?
            ''', (now.strftime('%Y-%m-%d %H:%M:%S'), suggested_position, existing['id']))
            conn_track.commit()
            return {
                'first_triggered_at': existing['first_triggered_at'],
                'initial_position': str(int(float(existing['suggested_position'].replace('%', '')) * 0.3)) + '%'
            }
        else:
            # 插入新信号
            cursor_track.execute('''
                INSERT INTO trading_signal_history 
                (signal_key, symbol, buy_point_type, suggested_position, 
                 first_triggered_at, last_updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            ''', (signal_key, symbol, buy_point_type, suggested_position,
                  now.strftime('%Y-%m-%d %H:%M:%S'), 
                  now.strftime('%Y-%m-%d %H:%M:%S')))
            conn_track.commit()
            return {
                'first_triggered_at': now.strftime('%Y-%m-%d %H:%M:%S'),
                'initial_position': str(int(float(suggested_position.replace('%', '')) * 0.3)) + '%'
            }
    finally:
        conn_track.close()

def check_no_new_low_5min(symbol):
    """检查创新低后连续5个5分钟K线不创新低"""
    import sqlite3
    from datetime import datetime, timedelta
    
    conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
    cursor = conn.cursor()
    
    try:
        # 统一格式：FIL -> FIL-USDT-SWAP
        symbol_full = f"{symbol}-USDT-SWAP" if not symbol.endswith('-USDT-SWAP') else symbol
        symbol_short = symbol.replace('-USDT-SWAP', '')
        
        # 获取最近的创新低事件
        cursor.execute('''
            SELECT event_time, price
            FROM price_breakthrough_events
            WHERE symbol = ? AND event_type = 'new_low'
            ORDER BY event_time DESC
            LIMIT 1
        ''', (symbol_short,))
        
        last_new_low = cursor.fetchone()
        if not last_new_low:
            return False
        
        new_low_time = datetime.strptime(last_new_low[0], '%Y-%m-%d %H:%M:%S')
        new_low_price = last_new_low[1]
        
        # 获取创新低之后的5个5分钟K线
        cursor.execute('''
            SELECT low, timestamp
            FROM okex_kline_ohlc
            WHERE symbol = ?
              AND timeframe = '5m'
              AND datetime(timestamp/1000, 'unixepoch') > datetime(?)
            ORDER BY timestamp ASC
            LIMIT 5
        ''', (symbol_full, new_low_time.strftime('%Y-%m-%d %H:%M:%S')))
        
        klines_after = cursor.fetchall()
        
        # 需要有5根K线
        if len(klines_after) < 5:
            return False
        
        # 检查这5根K线是否都没有创新低
        for low, ts in klines_after:
            if low < new_low_price:
                return False
        
        return True
    finally:
        conn.close()

def get_1h_rsi(symbol):
    """获取1小时RSI"""
    import sqlite3
    
    conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
    cursor = conn.cursor()
    
    try:
        # 统一格式
        symbol_full = f"{symbol}-USDT-SWAP" if not symbol.endswith('-USDT-SWAP') else symbol
        
        cursor.execute('''
            SELECT rsi_14
            FROM okex_technical_indicators
            WHERE symbol = ? AND timeframe IN ('1h', '1H')
            ORDER BY record_time DESC
            LIMIT 1
        ''', (symbol_full,))
        
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

def check_consecutive_oscillation_5min(symbol):
    """检查5分钟周期连续3个震荡≤0.5% 且涨跌在0%到+0.25%之间（不包括负涨跌）"""
    import sqlite3
    
    conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
    cursor = conn.cursor()
    
    try:
        # 统一格式
        symbol_full = f"{symbol}-USDT-SWAP" if not symbol.endswith('-USDT-SWAP') else symbol
        
        # 获取最近3根5分钟K线
        cursor.execute('''
            SELECT open, high, low, close
            FROM okex_kline_ohlc
            WHERE symbol = ?
              AND timeframe = '5m'
            ORDER BY timestamp DESC
            LIMIT 3
        ''', (symbol_full,))
        
        klines = cursor.fetchall()
        
        if len(klines) < 3:
            return False
        
        # 检查每根K线
        for open_price, high, low, close in klines:
            if open_price == 0:
                return False
            
            # 震荡幅度 = (最高-最低) / 开盘 * 100
            oscillation = ((high - low) / open_price) * 100 if open_price > 0 else 999
            
            # 涨跌幅 = (收盘-开盘) / 开盘 * 100（保留正负，不取绝对值）
            change = ((close - open_price) / open_price) * 100
            
            # 任何一根不满足条件就返回False
            # 涨跌幅必须在 0% 到 +0.25% 之间，震荡幅度 <= 0.50%
            if change < 0 or change > 0.25 or oscillation > 0.5:
                return False
        
        return True
    finally:
        conn.close()

def deactivate_missing_signals(active_signal_keys):
    """将不再满足条件的信号标记为失效"""
    from datetime import datetime
    import pytz
    import sqlite3
    
    beijing_tz = pytz.timezone('Asia/Shanghai')
    now = datetime.now(beijing_tz)
    
    conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
    cursor = conn.cursor()
    
    try:
        # 获取所有当前活跃的信号
        cursor.execute('SELECT signal_key FROM trading_signal_history WHERE is_active = 1')
        all_active = [row[0] for row in cursor.fetchall()]
        
        # 找出不在当前信号列表中的信号（即条件不再满足的信号）
        signals_to_deactivate = [sig for sig in all_active if sig not in active_signal_keys]
        
        # 标记这些信号为失效
        for signal_key in signals_to_deactivate:
            cursor.execute('''
                UPDATE trading_signal_history 
                SET is_active = 0, last_updated_at = ?
                WHERE signal_key = ? AND is_active = 1
            ''', (now.strftime('%Y-%m-%d %H:%M:%S'), signal_key))
        
        conn.commit()
        return len(signals_to_deactivate)
    finally:
        conn.close()

@app.route('/api/trading-signals/analyze')
def api_trading_signals_analyze():
    """分析交易信号 - 做多买点1/2/3"""
    try:
        from datetime import datetime, timedelta
        import pytz
        from opening_logic import get_opening_suggestion
        
        # 连接crypto_data数据库（用于其他系统数据）
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        
        # 0. 获取开仓逻辑建议（用于买点3仓位计算）
        try:
            opening_logic_data = get_opening_suggestion()
            opening_position = opening_logic_data.get('position_info', {})
            opening_can_long = opening_logic_data.get('can_long', False)
            opening_position_percent = opening_position.get('position_percent', 0)
        except Exception as e:
            print(f"获取开仓逻辑失败: {e}")
            opening_can_long = False
            opening_position_percent = 0
        
        # 1. 获取支撑压力线数据（从JSONL）
        import sys
        sys.path.insert(0, '/home/user/webapp')
        sys.path.insert(0, '/home/user/webapp/source_code')
        from support_resistance_api_adapter import SupportResistanceAPIAdapter
        
        adapter = SupportResistanceAPIAdapter()
        sr_result = adapter.get_all_symbols_latest()
        
        sr_data = {}
        if sr_result['success'] and sr_result['data']:
            for item in sr_result['data']:
                symbol = item.get('symbol', '')
                # 计算距离支撑线的距离百分比
                current_price = item.get('current_price', 0)
                support_1 = item.get('support_line_1', 0)
                support_2 = item.get('support_line_2', 0)
                resistance_1 = item.get('resistance_line_1', 0)
                
                distance_to_support_1 = None
                distance_to_support_2 = None
                distance_to_resistance_1 = None
                position_s2_r1 = item.get('position_7d', 0)  # 使用position_7d作为s2_r1位置
                
                if support_1 and current_price:
                    distance_to_support_1 = ((current_price - support_1) / support_1) * 100
                if support_2 and current_price:
                    distance_to_support_2 = ((current_price - support_2) / support_2) * 100
                if resistance_1 and current_price:
                    distance_to_resistance_1 = ((resistance_1 - current_price) / current_price) * 100
                
                sr_data[symbol] = {
                    'symbol': symbol,
                    'current_price': current_price,
                    'support_line_1': support_1,
                    'support_line_2': support_2,
                    'resistance_line_1': resistance_1,
                    'distance_to_support_1': distance_to_support_1,
                    'distance_to_support_2': distance_to_support_2,
                    'distance_to_resistance_1': distance_to_resistance_1,
                    'position_s2_r1': position_s2_r1,
                    'record_time': item.get('record_time', '')
                }
        
        # 2. 获取价格突破数据(创新低统计 - 最近7天)
        seven_days_ago = now - timedelta(days=7)
        cursor.execute('''
            SELECT symbol, COUNT(*) as count
            FROM price_breakthrough_events
            WHERE event_type = 'new_low'
              AND event_time >= ?
            GROUP BY symbol
        ''', (seven_days_ago.strftime('%Y-%m-%d %H:%M:%S'),))
        breakthrough_data = {row['symbol']: row['count'] for row in cursor.fetchall()}
        
        # 3. 获取最新快照数据(急涨急跌、计次得分)
        cursor.execute('''
            SELECT c.symbol, c.rush_up, c.rush_down, c.current_price,
                   s.count_score_display, s.count_score_type
            FROM crypto_coin_data c
            JOIN crypto_snapshots s ON c.snapshot_id = s.id
            WHERE c.id IN (
                SELECT MAX(id) 
                FROM crypto_coin_data 
                GROUP BY symbol
            )
        ''')
        coin_data = {row['symbol']: dict(row) for row in cursor.fetchall()}
        
        # 3.5 获取K线指标数据 (5分钟RSI、SAR位置、SAR象限)
        cursor.execute('''
            SELECT symbol, rsi_14, sar_position, sar_quadrant, sar_count_label
            FROM okex_technical_indicators
            WHERE timeframe = '5m'
              AND (symbol, record_time) IN (
                SELECT symbol, MAX(record_time)
                FROM okex_technical_indicators
                WHERE timeframe = '5m'
                GROUP BY symbol
            )
        ''')
        kline_indicators = {}
        for row in cursor.fetchall():
            # 统一格式：FIL-USDT-SWAP -> FIL
            symbol_short = row['symbol'].replace('-USDT-SWAP', '')
            kline_indicators[symbol_short] = {
                'rsi_5m': row['rsi_14'],
                'sar_position': row['sar_position'],  # 'bullish' 或 'bearish'
                'sar_quadrant': row['sar_quadrant'],  # 1-4象限
                'sar_count_label': row['sar_count_label']  # 例如 "多头12"
            }
        
        # 4. 获取位置系统数据（BTC/ETH的4h/12h/24h/48h周期位置）
        cursor.execute('''
            SELECT symbol, position_4h, position_12h, position_24h, position_48h
            FROM position_system
            WHERE symbol IN ('BTC', 'ETH')
              AND id IN (
                SELECT MAX(id) 
                FROM position_system 
                GROUP BY symbol
            )
        ''')
        position_data = {}
        for row in cursor.fetchall():
            symbol = row['symbol']
            positions = [
                row['position_4h'], row['position_12h'], 
                row['position_24h'], row['position_48h']
            ]
            # 统计有多少个周期位置 < 10%
            low_position_count = sum(1 for p in positions if p is not None and p < 10)
            position_data[symbol] = low_position_count
        
        conn.close()
        
        # 检查BTC和ETH是否至少有5个周期 < 10%
        # 由于只有4个周期，我们改为检查BTC和ETH加起来是否有5个以上
        btc_low = position_data.get('BTC', 0)
        eth_low = position_data.get('ETH', 0)
        total_low_positions = btc_low + eth_low
        condition6_pass = total_low_positions >= 5
        
        # 5. 统计接近支撑线的币种数量（用于买点3条件6）
        # 接近支撑1：距离支撑线1 <= 某个阈值（例如10%）
        # 接近支撑2：距离支撑线2 <= 某个阈值（例如10%）
        near_support_1_count = 0
        near_support_2_count = 0
        
        for symbol, sr in sr_data.items():
            dist_s1 = sr.get('distance_to_support_1')
            dist_s2 = sr.get('distance_to_support_2')
            
            # 统计接近支撑1的币种（距离 <= 10%）
            if dist_s1 is not None and dist_s1 <= 10:
                near_support_1_count += 1
            
            # 统计接近支撑2的币种（距离 <= 10%）
            if dist_s2 is not None and dist_s2 <= 10:
                near_support_2_count += 1
        
        # 买点3条件6：接近支撑1的币种数 >= 8 或 接近支撑2的币种数 >= 8
        condition6_support_system = near_support_1_count >= 8 or near_support_2_count >= 8
        
        # 6. 分析信号
        signals = []
        buy_point_1_count = 0
        buy_point_2_count = 0
        buy_point_3_count = 0
        
        for symbol, sr in sr_data.items():
            coin_name = symbol.replace('USDT', '')
            coin = coin_data.get(coin_name, {})
            kline = kline_indicators.get(coin_name, {})
            
            # 获取创新低次数
            new_lows = breakthrough_data.get(coin_name, 0)
            
            # 获取计次得分
            score_display = coin.get('count_score_display', '---')
            score_type = coin.get('count_score_type', '中性')
            
            # 获取急涨急跌
            rush_up = coin.get('rush_up', 0) or 0
            rush_down = coin.get('rush_down', 0) or 0
            rush_diff = rush_up - rush_down
            
            # 获取K线指标数据
            rsi_5m = kline.get('rsi_5m')
            sar_position = kline.get('sar_position')  # 'bullish' / 'bearish'
            sar_quadrant = kline.get('sar_quadrant')  # 1-4
            sar_count_label = kline.get('sar_count_label', '')
            
            # 解析空头/多头数量（从 "空头20" 或 "多头12" 中提取数字）
            sar_count = 0
            if sar_count_label:
                import re
                match = re.search(r'(\d+)', sar_count_label)
                if match:
                    sar_count = int(match.group(1))
            
            # 通用条件判断
            condition1 = new_lows < 3  # 创新低 < 3 【买点1/2/3适用】
            condition2 = '★' in score_display or '⭐' in score_display  # 计次得分是星星 【买点1/2适用】
            condition3 = rush_diff > 0  # 急涨 - 急跌 > 0 【买点1/2适用】
            condition4 = rsi_5m is not None and rsi_5m < 20  # 5分钟RSI < 20 【买点1适用】（修改为使用5分钟RSI）
            condition5 = rush_diff > -15  # 急涨 - 急跌 > -15 【买点3适用】
            condition6 = condition6_pass  # BTC/ETH至少5个周期 < 10% 【买点3适用】
            
            # 新增条件（基于K线指标）
            condition_sar_bearish = sar_position == 'bearish'  # 空头趋势
            condition_sar_count = sar_count > 20  # 空头数量>20
            condition_sar_quadrant3 = sar_quadrant == 3  # SAR第三象限
            condition_rsi_low = rsi_5m is not None and rsi_5m < 30  # 5分钟RSI<30 【买点2适用】
            
            # 买点3专用条件检查
            condition_no_new_low_5m = check_no_new_low_5min(coin_name)  # 创新低后连续5个5分钟K线不创新低
            rsi_1h = get_1h_rsi(coin_name)  # 获取1小时RSI
            condition_rsi_1h_low = rsi_1h is not None and rsi_1h < 15  # 1小时RSI<15
            condition_oscillation_3 = check_consecutive_oscillation_5min(coin_name)  # 连续3个震荡
            
            # 获取距离支撑线1的距离（用于买点1）
            distance = sr.get('distance_to_support_1')
            
            # 判断各个买点
            buy_point_1 = False
            buy_point_2 = False
            buy_point_3 = False
            
            # 买点1: 达到支撑线1 (距离 < 5%) + 条件1234
            if (distance is not None and distance <= 5 and 
                condition1 and condition2 and condition3 and condition4):
                buy_point_1 = True
                buy_point_1_count += 1
            
            # 买点2: 回调买入
            # 条件：条件123 + 空头>20 + 5分钟SAR第三象限 + 5分钟RSI<30
            if (condition1 and condition2 and condition3 and 
                condition_sar_count and condition_sar_quadrant3 and condition_rsi_low):
                buy_point_2 = True
                buy_point_2_count += 1
            
            # 买点3: 空转多买入（重新定义条件）
            # 6个必须条件：
            # 1. 创新低后连续5个5分钟K线不创新低
            # 2. 1小时RSI < 15
            # 3. 5分钟周期连续3个震荡≤0.5% 且涨跌<0.25%
            # 4. SAR空头数量 > 20
            # 5. 5分钟SAR在第三象限
            # 6. 支撑压力线系统：接近支撑1的币种数 >= 8 或 接近支撑2的币种数 >= 8
            if (condition_no_new_low_5m and 
                condition_rsi_1h_low and 
                condition_oscillation_3 and 
                condition_sar_count and 
                condition_sar_quadrant3 and 
                condition6_support_system):  # 使用全局条件
                buy_point_3 = True
                buy_point_3_count += 1
            
            # 只保留有信号的币种
            if buy_point_1 or buy_point_2 or buy_point_3:
                # 详细的条件判断结果 - 用于透明化显示
                detailed_conditions = {
                    'buy_point_1_conditions': {
                        'distance_to_support': {'value': distance, 'threshold': '≤ 5%', 'pass': distance is not None and distance <= 5, 'desc': '距离支撑线1'},
                        'condition1': {'value': new_lows, 'threshold': '< 3', 'pass': condition1, 'desc': '7天创新低次数'},
                        'condition2': {'value': score_display, 'threshold': '包含★或⭐', 'pass': condition2, 'desc': '计次得分显示'},
                        'condition3': {'value': round(rush_diff, 2), 'threshold': '> 0', 'pass': condition3, 'desc': '急涨-急跌'},
                        'condition4': {'value': round(rsi_5m, 2) if rsi_5m else None, 'threshold': '< 20', 'pass': condition4, 'desc': '5分钟RSI'}
                    },
                    'buy_point_2_conditions': {
                        'condition1': {'value': new_lows, 'threshold': '< 3', 'pass': condition1, 'desc': '7天创新低次数'},
                        'condition2': {'value': score_display, 'threshold': '包含★或⭐', 'pass': condition2, 'desc': '计次得分显示'},
                        'condition3': {'value': round(rush_diff, 2), 'threshold': '> 0', 'pass': condition3, 'desc': '急涨-急跌'},
                        'sar_count': {'value': sar_count, 'threshold': '> 20', 'pass': condition_sar_count, 'desc': 'SAR空头数量'},
                        'sar_quadrant': {'value': sar_quadrant, 'threshold': '= 3', 'pass': condition_sar_quadrant3, 'desc': 'SAR第三象限'},
                        'rsi_5m': {'value': round(rsi_5m, 2) if rsi_5m else None, 'threshold': '< 30', 'pass': condition_rsi_low, 'desc': '5分钟RSI'}
                    },
                    'buy_point_3_conditions': {
                        'no_new_low_5m': {'value': '是' if condition_no_new_low_5m else '否', 'threshold': '是', 'pass': condition_no_new_low_5m, 'desc': '创新低后连续5个5分钟K线不创新低'},
                        'rsi_1h': {'value': round(rsi_1h, 2) if rsi_1h else None, 'threshold': '< 15', 'pass': condition_rsi_1h_low, 'desc': '1小时RSI'},
                        'oscillation_3': {'value': '是' if condition_oscillation_3 else '否', 'threshold': '是', 'pass': condition_oscillation_3, 'desc': '连续3个震荡≤0.5% 且涨跌<0.25%'},
                        'sar_count': {'value': sar_count, 'threshold': '> 20', 'pass': condition_sar_count, 'desc': 'SAR空头数量'},
                        'sar_quadrant': {'value': sar_quadrant, 'threshold': '= 3', 'pass': condition_sar_quadrant3, 'desc': '5分钟SAR第三象限'},
                        'support_system': {'value': f'接近支撑1: {near_support_1_count}个, 接近支撑2: {near_support_2_count}个', 'threshold': '接近支撑1 ≥ 8个 或 接近支撑2 ≥ 8个', 'pass': condition6_support_system, 'desc': '支撑压力线系统'}
                    }
                }
                
                # 确定买点类型和建议仓位
                buy_point_type = None
                suggested_position = None
                position_calculation_note = None
                buy_times = None  # 分批买入次数
                
                if buy_point_1:
                    buy_point_type = 'buy_point_1'
                    suggested_position = '30%'
                    buy_times = 3  # 买点1分3次买入
                    position_calculation_note = '买点1固定仓位，分3次买入'
                    
                elif buy_point_3:
                    buy_point_type = 'buy_point_3'
                    buy_times = 2  # 买点3分2次买入
                    # 买点3特殊仓位逻辑
                    if opening_can_long and opening_position_percent > 0:
                        # 情况2：开仓逻辑允许开仓
                        # 买点3仓位 = 开仓逻辑建议 + 20%，最高70%
                        bp3_position = min(opening_position_percent + 20, 70)
                        suggested_position = f'{int(bp3_position)}%'
                        position_calculation_note = f'开仓逻辑{int(opening_position_percent)}% + 买点3加成20% = {int(bp3_position)}% (上限70%)，分2次买入'
                    else:
                        # 情况1：开仓逻辑不允许开仓
                        # 买点3可额外开20%
                        suggested_position = '20%'
                        position_calculation_note = '开仓逻辑不允许，买点3可额外开20%，分2次买入'
                        
                elif buy_point_2:
                    buy_point_type = 'buy_point_2'
                    suggested_position = '20%'
                    buy_times = 2  # 买点2分2次买入
                    position_calculation_note = '买点2固定仓位，分2次买入'
                
                # 跟踪信号历史，获取首次触发时间和首次开仓建议
                tracking_info = track_trading_signal(coin_name, buy_point_type, suggested_position)
                
                signals.append({
                    'symbol': coin_name,
                    'current_price': sr.get('current_price', 0),
                    'support_line_1': sr.get('support_line_1'),
                    'distance_to_support_1': distance,
                    'buy_point_1': buy_point_1,
                    'buy_point_2': buy_point_2,
                    'buy_point_3': buy_point_3,
                    'suggested_position': suggested_position,
                    'buy_times': buy_times,  # 新增：分批买入次数
                    'position_calculation_note': position_calculation_note,  # 新增：仓位计算说明
                    'opening_logic_position': f'{int(opening_position_percent)}%' if opening_can_long else '不允许',  # 新增：开仓逻辑建议
                    'first_triggered_at': tracking_info['first_triggered_at'],  # 新增：首次触发时间
                    'initial_position': tracking_info['initial_position'],  # 新增：首次开仓建议(总仓位的30%)
                    'conditions': {
                        'condition1_pass': condition1,
                        'condition2_pass': condition2,
                        'condition3_pass': condition3,
                        'new_lows': new_lows,
                        'score_display': score_display,
                        'rush_diff': round(rush_diff, 2)
                    },
                    'kline_indicators': {
                        'rsi_5m': round(rsi_5m, 2) if rsi_5m else None,
                        'sar_position': sar_position,
                        'sar_quadrant': sar_quadrant,
                        'sar_count': sar_count,
                        'sar_count_label': sar_count_label
                    },
                    'detailed_conditions': detailed_conditions  # 新增：详细条件判断结果
                })
        
        # 按买点1 > 买点3 > 买点2 优先级排序，同优先级按距支撑线距离排序
        def sort_key(x):
            priority = 0
            if x['buy_point_1']:
                priority = 3
            elif x['buy_point_3']:
                priority = 2
            elif x['buy_point_2']:
                priority = 1
            distance = x['distance_to_support_1'] if x['distance_to_support_1'] is not None else 999
            return (-priority, distance)
        
        signals.sort(key=sort_key)
        
        # 收集当前所有活跃信号的signal_key
        active_signal_keys = []
        for signal in signals:
            coin_name = signal['symbol']
            if signal['buy_point_1']:
                active_signal_keys.append(f"{coin_name}_buy_point_1")
            elif signal['buy_point_3']:
                active_signal_keys.append(f"{coin_name}_buy_point_3")
            elif signal['buy_point_2']:
                active_signal_keys.append(f"{coin_name}_buy_point_2")
        
        # 将不再满足条件的信号标记为失效
        deactivated_count = deactivate_missing_signals(active_signal_keys)
        
        # 买点规则说明 - 透明化展示
        buy_point_rules = {
            'buy_point_1': {
                'name': '买点1 - 支撑线买入',
                'suggested_position': '30%',
                'buy_times': 3,  # 分3次买入
                'conditions': [
                    {'id': '距离支撑线', 'rule': '距离支撑线1 ≤ 5%', 'priority': 'high'},
                    {'id': '创新低', 'rule': '7天创新低次数 < 3', 'priority': 'high'},
                    {'id': '计次得分', 'rule': '计次得分显示包含★或⭐', 'priority': 'medium'},
                    {'id': '急涨急跌', 'rule': '急涨 - 急跌 > 0', 'priority': 'medium'},
                    {'id': 'RSI 5m', 'rule': '5分钟RSI < 20', 'priority': 'high'}
                ],
                'description': '价格接近支撑线时的买入机会，风险较低，建议分3次买入'
            },
            'buy_point_2': {
                'name': '买点2 - 回调买入',
                'suggested_position': '20%',
                'buy_times': 2,  # 分2次买入
                'conditions': [
                    {'id': '创新低', 'rule': '7天创新低次数 < 3', 'priority': 'high'},
                    {'id': '计次得分', 'rule': '计次得分显示包含★或⭐', 'priority': 'medium'},
                    {'id': '急涨急跌', 'rule': '急涨 - 急跌 > 0', 'priority': 'medium'},
                    {'id': 'SAR空头数', 'rule': 'SAR空头数量 > 20', 'priority': 'high'},
                    {'id': 'SAR象限', 'rule': 'SAR在第三象限', 'priority': 'high'},
                    {'id': 'RSI 5m', 'rule': '5分钟RSI < 30', 'priority': 'high'}
                ],
                'description': '市场回调时的买入机会，需要技术指标确认，建议分2次买入'
            },
            'buy_point_3': {
                'name': '买点3 - 空转多买入',
                'suggested_position': '最多20% (如无开仓逻辑建议)',
                'buy_times': 2,  # 分2次买入
                'conditions': [
                    {'id': '5分钟不创新低', 'rule': '创新低后连续5个5分钟K线不创新低', 'priority': 'high'},
                    {'id': '1h RSI', 'rule': '1小时RSI < 15', 'priority': 'high'},
                    {'id': '连续震荡', 'rule': '5分钟周期连续3个震荡≤0.5% 且涨跌<0.25%', 'priority': 'high'},
                    {'id': 'SAR空头数', 'rule': 'SAR空头持续数量 > 20', 'priority': 'high'},
                    {'id': 'SAR象限', 'rule': '5分钟SAR在第三象限', 'priority': 'high'},
                    {'id': '支撑压力线', 'rule': '接近支撑1的币种数 ≥ 8个 或 接近支撑2的币种数 ≥ 8个', 'priority': 'high'}
                ],
                'description': '极度超卖后的空转多买入机会，严格条件筛选（需市场整体接近支撑线），建议分2次买入'
            }
        }
        
        return jsonify({
            'success': True,
            'data': {
                'signals': signals,
                'buy_point_1_count': buy_point_1_count,
                'buy_point_2_count': buy_point_2_count,
                'buy_point_3_count': buy_point_3_count,
                'total_coins': len(sr_data),
                'update_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                'buy_point_rules': buy_point_rules,  # 新增：买点规则说明
                'opening_logic_info': {  # 新增：开仓逻辑信息
                    'can_long': opening_can_long,
                    'position_percent': opening_position_percent,
                    'suggestion': f'{int(opening_position_percent)}%' if opening_can_long else '不允许开仓'
                },
                'notes': {
                    'buy_point_1': '✅ 支撑线买入 (距离<5%) + 创新低<3 + 计次得分⭐/★ + 急涨>急跌 + 5分钟RSI<20 - 已更新使用5分钟RSI',
                    'buy_point_2': '✅ 回调买入 (条件1-3 + 空头>20 + 5分钟SAR第三象限 + 5分钟RSI<30) - 已集成K线指标',
                    'buy_point_3': '✅ 空转多买入 (5个5分钟不创新低 + 1h RSI<15 + 连续3个震荡 + SAR空头>20 + SAR第3象限) - 严格条件',
                    'buy_point_3_position': '📊 买点3仓位规则：若开仓逻辑允许，则为 开仓逻辑仓位+20% (上限70%)；若开仓逻辑不允许，则额外开20%',
                    'data_integration': '✅ 已集成kline-indicators数据：5分钟RSI、SAR位置、SAR象限、SAR计数',
                    'data_limitation': '⚠️ 仍需补充：连续5个5分钟K线不创新低、连续3个震荡条件'
                }
            }
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/trading-signals/buy-points')
def api_trading_signals_buy_points():
    """获取当前所有买点信号（简化版API）"""
    try:
        import sqlite3
        from datetime import datetime
        import pytz
        
        # 调用现有的分析函数
        response = api_trading_signals_analyze()
        
        # 如果返回的是Response对象，获取其JSON数据
        if hasattr(response, 'get_json'):
            data = response.get_json()
        else:
            import json
            data = json.loads(response[0])
        
        if not data.get('success'):
            return jsonify({
                'success': False,
                'message': '获取买点数据失败',
                'error': data.get('error', 'Unknown error')
            }), 500
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        
        # 提取买点信号
        signals_data = data.get('data', {})
        buy_signals = signals_data.get('signals', [])
        
        # 按买点类型分组
        buy_point_1 = [s for s in buy_signals if s.get('buy_point') == 1]
        buy_point_2 = [s for s in buy_signals if s.get('buy_point') == 2]
        buy_point_3 = [s for s in buy_signals if s.get('buy_point') == 3]
        
        # 简化信号数据
        def simplify_signal(signal):
            return {
                'symbol': signal.get('symbol'),
                'buy_point': signal.get('buy_point'),
                'current_price': signal.get('current_price'),
                'suggested_position': signal.get('suggested_position'),
                'buy_times': signal.get('buy_times'),
                'distance_to_support': signal.get('distance_to_support_1'),
                'conditions_met': signal.get('conditions_met'),
                'score_display': signal.get('score_display'),
                'sar_position': signal.get('sar_position'),
                'rsi_5m': signal.get('rsi_5m'),
                'rsi_1h': signal.get('rsi_1h'),
                'recommended': signal.get('recommended', False)
            }
        
        result = {
            'success': True,
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': {
                'total_signals': len(buy_signals),
                'buy_point_1_count': len(buy_point_1),
                'buy_point_2_count': len(buy_point_2),
                'buy_point_3_count': len(buy_point_3)
            },
            'buy_points': {
                'buy_point_1': [simplify_signal(s) for s in buy_point_1],
                'buy_point_2': [simplify_signal(s) for s in buy_point_2],
                'buy_point_3': [simplify_signal(s) for s in buy_point_3]
            },
            'all_signals': [simplify_signal(s) for s in buy_signals],
            'rules': signals_data.get('buy_point_rules', {})
        }
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        print(f"获取买点信号失败: {e}")
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': '获取买点信号失败',
            'error': str(e)
        }), 500

@app.route('/api/trading-signals/history')
def api_trading_signals_history():
    """获取历史信号（已失效的信号）"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        import pytz
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        
        # 获取最近7天内失效的信号
        seven_days_ago = now - timedelta(days=7)
        
        cursor.execute('''
            SELECT signal_key, symbol, buy_point_type, suggested_position,
                   first_triggered_at, last_updated_at
            FROM trading_signal_history
            WHERE is_active = 0
              AND last_updated_at >= ?
            ORDER BY last_updated_at DESC
            LIMIT 50
        ''', (seven_days_ago.strftime('%Y-%m-%d %H:%M:%S'),))
        
        history_signals = []
        for row in cursor.fetchall():
            # 计算信号持续时间
            first_time = datetime.strptime(row['first_triggered_at'], '%Y-%m-%d %H:%M:%S')
            last_time = datetime.strptime(row['last_updated_at'], '%Y-%m-%d %H:%M:%S')
            duration_minutes = int((last_time - first_time).total_seconds() / 60)
            
            buy_point_name = {
                'buy_point_1': '买点1',
                'buy_point_2': '买点2',
                'buy_point_3': '买点3'
            }.get(row['buy_point_type'], '未知')
            
            history_signals.append({
                'symbol': row['symbol'],
                'buy_point_type': buy_point_name,
                'suggested_position': row['suggested_position'],
                'initial_position': str(int(float(row['suggested_position'].replace('%', '')) * 0.3)) + '%',
                'first_triggered_at': row['first_triggered_at'],
                'last_updated_at': row['last_updated_at'],
                'duration_minutes': duration_minutes
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'history_signals': history_signals,
                'total_count': len(history_signals),
                'update_time': now.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/support-resistance/latest')
def api_support_resistance_latest():
    """获取最新的支撑压力线数据（从按日期存储的JSONL）"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        sys.path.insert(0, '/home/user/webapp/source_code')
        from support_resistance_daily_manager import SupportResistanceDailyManager
        
        manager = SupportResistanceDailyManager()
        
        # 获取所有币种的最新数据（今日）
        latest_levels = manager.get_latest_levels()
        
        if not latest_levels:
            return jsonify({
                'success': False,
                'message': 'No data available'
            })
        
        # 获取最新时间（用于显示"最后更新"）
        update_time = None
        for level in latest_levels:
            data = level.get('data', level)  # 提取data字段
            time_str = data.get('record_time_beijing') or data.get('record_time')
            if time_str:
                update_time = time_str
                break
        
        # 格式化数据
        coins_data = []
        scenario_1_coins = []
        scenario_2_coins = []
        
        for level in latest_levels:
            # 提取data字段（新JSONL格式）
            data = level.get('data', level)  # 兼容新旧格式
            
            symbol = data.get('symbol', '')
            
            # 转换为 OKX 格式（BTCUSDT -> BTC-USDT-SWAP）
            if symbol.endswith('USDT'):
                okx_symbol = f"{symbol[:-4]}-USDT-SWAP"
            else:
                okx_symbol = symbol
            
            current_price = data.get('current_price', 0)
            support_1 = data.get('support_line_1', 0)
            support_2 = data.get('support_line_2', 0)
            resistance_1 = data.get('resistance_line_1', 0)
            resistance_2 = data.get('resistance_line_2', 0)
            position_7d = data.get('position_7d', 0)
            position_48h = data.get('position_48h', 0)
            
            # 判断告警场景
            alert_7d_low = data.get('alert_7d_low', 0) or (1 if position_7d <= 10 else 0)
            alert_7d_high = data.get('alert_7d_high', 0) or (1 if position_7d >= 90 else 0)
            alert_48h_low = data.get('alert_48h_low', 0) or (1 if position_48h <= 10 else 0)
            alert_48h_high = data.get('alert_48h_high', 0) or (1 if position_48h >= 90 else 0)
            
            coin_info = {
                'symbol': okx_symbol,
                'current_price': current_price,
                # 前端期望的字段名
                'support_line_1': support_1,
                'support_line_2': support_2,
                'resistance_line_1': resistance_1,
                'resistance_line_2': resistance_2,
                # 天数和小时数
                'support_1_days': data.get('support_1_days', 0),
                'support_2_hours': data.get('support_2_hours', 0),
                'resistance_1_days': data.get('resistance_1_days', 0),
                'resistance_2_hours': data.get('resistance_2_hours', 0),
                # 位置字段
                'position_7d': position_7d,
                'position_48h': position_48h,
                # 向后兼容字段
                'support_1': support_1,
                'support_2': support_2,
                'resistance_1': resistance_1,
                'resistance_2': resistance_2,
                'position_s2_r1': position_7d,
                'position_s1_r2': position_48h,
                'position_s1_r2_upper': position_48h,
                'position_s1_r1': position_7d,
                # 告警字段（旧格式，用于scenario统计）
                'alert_scenario_1': alert_7d_low,
                'alert_scenario_2': alert_7d_high,
                'alert_scenario_3': alert_48h_low,
                'alert_scenario_4': alert_48h_high,
                # 告警字段（新格式，用于前端统计卡片）
                'alert_7d_low': bool(alert_7d_low),
                'alert_7d_high': bool(alert_7d_high),
                'alert_48h_low': bool(alert_48h_low),
                'alert_48h_high': bool(alert_48h_high)
            }
            
            coins_data.append(coin_info)
            
            # 添加到场景列表
            if alert_7d_low:
                scenario_1_coins.append(coin_info)
            if alert_7d_high:
                scenario_2_coins.append(coin_info)
        
        # 预计算4种告警场景（服务器端完成筛选，避免前端计算）
        scenario_1_list = []  # 7d位置<=10% (低位支撑)
        scenario_2_list = []  # 7d位置>=90% (高位压力)
        scenario_3_list = []  # 48h位置<=10% (短期支撑)
        scenario_4_list = []  # 48h位置>=90% (短期压力)
        
        for coin in coins_data:
            if coin.get('alert_scenario_1'):
                scenario_1_list.append({
                    'symbol': coin['symbol'],
                    'position': coin.get('position_s2_r1', 0)
                })
            if coin.get('alert_scenario_2'):
                scenario_2_list.append({
                    'symbol': coin['symbol'],
                    'position': coin.get('position_s1_r2', 0)
                })
            if coin.get('alert_scenario_3'):
                scenario_3_list.append({
                    'symbol': coin['symbol'],
                    'position': coin.get('position_s1_r2', 0)
                })
            if coin.get('alert_scenario_4'):
                scenario_4_list.append({
                    'symbol': coin['symbol'],
                    'position': coin.get('position_s1_r1', 0)
                })
        
        return jsonify({
            'success': True,
            'update_time': update_time or '未知',
            'coins': len(coins_data),
            'data': coins_data,
            'scenario_1_coins': len(scenario_1_coins),
            'scenario_2_coins': len(scenario_2_coins),
            'data_source': 'JSONL',
            'timezone': 'Beijing Time (UTC+8)',
            # 新增：预计算的告警场景详情（避免前端filter计算）
            'alerts_summary': {
                'scenario_1': {
                    'count': len(scenario_1_list),
                    'description': '7天位置<=10% (低位支撑)',
                    'coins': scenario_1_list
                },
                'scenario_2': {
                    'count': len(scenario_2_list),
                    'description': '7天位置>=90% (高位压力)',
                    'coins': scenario_2_list
                },
                'scenario_3': {
                    'count': len(scenario_3_list),
                    'description': '48小时位置<=10% (短期支撑)',
                    'coins': scenario_3_list
                },
                'scenario_4': {
                    'count': len(scenario_4_list),
                    'description': '48小时位置>=90% (短期压力)',
                    'coins': scenario_4_list
                }
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/support-resistance/snapshots')
def api_support_resistance_snapshots():
    """获取快照数据（从 JSONL）"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from support_resistance_api_adapter import SupportResistanceAPIAdapter
        
        adapter = SupportResistanceAPIAdapter()
        
        # 获取查询参数
        all_data = request.args.get('all', 'false').lower() == 'true'
        date_filter = request.args.get('date', None)
        limit = int(request.args.get('limit', 100))
        
        # 如果指定了日期，直接获取该日期的所有数据
        if date_filter:
            result = adapter.get_snapshots(date=date_filter, limit=None)
        else:
            # 获取快照数据
            # all=true时返回所有历史数据（从2025-12-25开始的完整数据，约30000条）
            result = adapter.get_snapshots(limit=None if all_data else limit)
        
        if not result['success']:
            return jsonify(result)
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/support-resistance/signals-computed')
def api_support_resistance_signals_computed():
    """
    获取已计算好的信号数据（后端计算，前端直接展示）
    包含：信号标记点、24小时信号列表、统计数据等
    """
    try:
        from datetime import datetime, timedelta
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from support_resistance_api_adapter import SupportResistanceAPIAdapter
        
        adapter = SupportResistanceAPIAdapter()
        
        # 获取所有快照数据
        result = adapter.get_snapshots(limit=None)
        
        if not result['success']:
            return jsonify(result)
        
        data = result['data']
        
        if not data:
            return jsonify({
                'success': False,
                'message': 'No snapshot data available'
            })
        
        # 计算信号标记点
        signal_mark_points = []
        buy_signals = []  # 抄底信号列表
        sell_signals = []  # 逃顶信号列表
        
        for index, d in enumerate(data):
            scenario1 = d.get('scenario_1_count', 0) or 0
            scenario2 = d.get('scenario_2_count', 0) or 0
            scenario3 = d.get('scenario_3_count', 0) or 0
            scenario4 = d.get('scenario_4_count', 0) or 0
            
            support_total = scenario1 + scenario2
            resistance_total = scenario3 + scenario4
            snapshot_time = d.get('snapshot_time', '')
            
            # 抄底信号：情况1 ≥ 8 且 情况2 ≥ 8
            if scenario1 >= 8 and scenario2 >= 8:
                signal_mark_points.append({
                    'type': 'buy',
                    'name': '抄底',
                    'index': index,
                    'time': snapshot_time,
                    'count': support_total,
                    'scenario1': scenario1,
                    'scenario2': scenario2,
                    'y_value': max(scenario1, scenario2)
                })
                buy_signals.append({
                    'time': snapshot_time,
                    'count': support_total,
                    'scenario1': scenario1,
                    'scenario2': scenario2
                })
            
            # 逃顶信号：压力线币种 ≥ 8
            if resistance_total >= 8:
                signal_mark_points.append({
                    'type': 'sell',
                    'name': '逃顶',
                    'index': index,
                    'time': snapshot_time,
                    'count': resistance_total,
                    'scenario3': scenario3,
                    'scenario4': scenario4,
                    'y_value': max(scenario3, scenario4)
                })
                sell_signals.append({
                    'time': snapshot_time,
                    'count': resistance_total,
                    'scenario3': scenario3,
                    'scenario4': scenario4
                })
        
        # 计算24小时内的信号（使用北京时间）
        import pytz
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        time_24h_ago = (now - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        time_2h_ago = (now - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        buy_signals_24h = [s for s in buy_signals if s['time'] >= time_24h_ago]
        sell_signals_24h = [s for s in sell_signals if s['time'] >= time_24h_ago]
        sell_signals_2h = [s for s in sell_signals if s['time'] >= time_2h_ago]
        
        # 统计数据
        stats = {
            'total_signals': len(signal_mark_points),
            'buy_signals_total': len(buy_signals),
            'sell_signals_total': len(sell_signals),
            'buy_signals_count': len(buy_signals),  # 前端期望的字段名
            'sell_signals_count': len(sell_signals),  # 前端期望的字段名
            'buy_signals_24h': len(buy_signals_24h),
            'sell_signals_24h': len(sell_signals_24h),
            'sell_signals_2h': len(sell_signals_2h),
            'latest_buy_signal': buy_signals[-1] if buy_signals else None,
            'latest_sell_signal': sell_signals[-1] if sell_signals else None
        }
        
        return jsonify({
            'success': True,
            'data': data,  # 添加完整的快照数据
            'signal_mark_points': signal_mark_points,
            'buy_signals_24h': buy_signals_24h,
            'sell_signals_24h': sell_signals_24h,
            'sell_signals_2h': sell_signals_2h,
            'stats': stats,
            'data_count': len(data),
            'time_range': {
                'start': data[0].get('snapshot_time') if data else None,
                'end': data[-1].get('snapshot_time') if data else None
            },
            'computed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_source': 'JSONL',
            'timezone': 'Beijing Time (UTC+8)'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/support-resistance/chart-data')
def api_support_resistance_chart_data():
    """获取图表数据（后端计算好的）"""
    try:
        from support_resistance_api_adapter import SupportResistanceAPIAdapter
        from datetime import datetime
        
        # 获取查询参数
        all_data = request.args.get('all', 'false').lower() == 'true'
        date_filter = request.args.get('date', None)
        page = int(request.args.get('page', 1))
        items_per_page = int(request.args.get('items_per_page', 40))
        
        # 从JSONL获取数据
        adapter = SupportResistanceAPIAdapter()
        
        if all_data:
            # 获取所有历史数据
            result = adapter.get_snapshots(limit=None)
            data = result.get('data', []) if isinstance(result, dict) else []
            # 反转数据，使时间从早到晚排列
            data = list(reversed(data))
        elif date_filter:
            # 按日期过滤
            result = adapter.get_snapshots(limit=None)
            all_data_list = result.get('data', []) if isinstance(result, dict) else []
            data = [d for d in all_data_list if d.get('snapshot_time', '').startswith(date_filter)]
            # 反转数据，使时间从早到晚排列
            data = list(reversed(data))
        else:
            # 获取最近的数据用于分页
            result = adapter.get_snapshots(limit=None)
            data = result.get('data', []) if isinstance(result, dict) else []
            # 反转数据，使时间从早到晚排列
            data = list(reversed(data))
        
        if not data:
            return jsonify({
                'success': True,
                'chart_data': {
                    'categories': [],
                    'scenario_1': [],
                    'scenario_2': [],
                    'scenario_3': [],
                    'scenario_4': []
                },
                'signal_points': {
                    'buy_signals': [],
                    'sell_signals': []
                },
                'pagination': {
                    'current_page': 1,
                    'total_pages': 0,
                    'total_records': 0
                }
            })
        
        # 后端计算图表数据
        categories = []
        scenario_1_data = []
        scenario_2_data = []
        scenario_3_data = []
        scenario_4_data = []
        buy_signals = []
        sell_signals = []
        
        # 如果是分页模式，计算当前页的数据范围
        start_idx = 0
        end_idx = len(data)
        if not all_data and not date_filter:
            total_pages = (len(data) + items_per_page - 1) // items_per_page
            start_idx = (page - 1) * items_per_page
            end_idx = min(start_idx + items_per_page, len(data))
            page_data = data[start_idx:end_idx]
        else:
            page_data = data
            total_pages = 1
        
        # 处理数据
        for idx, snapshot in enumerate(page_data):
            snapshot_time = snapshot.get('snapshot_time', '')
            # 提取时间标签 (MM-DD HH:MM)
            if snapshot_time:
                try:
                    dt = datetime.strptime(snapshot_time, '%Y-%m-%d %H:%M:%S')
                    time_label = dt.strftime('%m-%d %H:%M')
                except:
                    time_label = snapshot_time[-14:]  # 取最后14个字符
            else:
                time_label = f'Point {idx}'
            
            categories.append(time_label)
            
            # 四种场景的计数
            s1 = snapshot.get('scenario_1_count', 0)
            s2 = snapshot.get('scenario_2_count', 0)
            s3 = snapshot.get('scenario_3_count', 0)
            s4 = snapshot.get('scenario_4_count', 0)
            
            scenario_1_data.append(s1)
            scenario_2_data.append(s2)
            scenario_3_data.append(s3)
            scenario_4_data.append(s4)
            
            # 信号检测
            # 抄底信号：scenario_1 >= 8 且 scenario_2 >= 8
            if s1 >= 8 and s2 >= 8:
                buy_signals.append({
                    'index': idx,
                    'time': snapshot_time,
                    'time_label': time_label,
                    'scenario_1': s1,
                    'scenario_2': s2,
                    'type': 'buy'
                })
            
            # 逃顶信号：scenario_3 + scenario_4 >= 8
            resistance_total = s3 + s4
            if resistance_total >= 8:
                sell_signals.append({
                    'index': idx,
                    'time': snapshot_time,
                    'time_label': time_label,
                    'scenario_3': s3,
                    'scenario_4': s4,
                    'total': resistance_total,
                    'type': 'sell'
                })
        
        return jsonify({
            'success': True,
            'chart_data': {
                'categories': categories,
                'scenario_1': scenario_1_data,
                'scenario_2': scenario_2_data,
                'scenario_3': scenario_3_data,
                'scenario_4': scenario_4_data
            },
            'signal_points': {
                'buy_signals': buy_signals,
                'sell_signals': sell_signals
            },
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_records': len(data),
                'items_per_page': items_per_page,
                'start_index': start_idx if not all_data and not date_filter else 0,
                'end_index': end_idx if not all_data and not date_filter else len(data)
            },
            'stats': {
                'buy_signals_count': len(buy_signals),
                'sell_signals_count': len(sell_signals)
            },
            'data_source': 'JSONL',
            'timezone': 'Beijing Time (UTC+8)',
            'computed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/support-resistance/latest-signal')
def api_support_resistance_latest_signal():
    """获取最新快照数据并检测是否触发信号（从按日期存储的JSONL）"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        sys.path.insert(0, '/home/user/webapp/source_code')
        from support_resistance_api_adapter import SupportResistanceAPIAdapter
        
        adapter = SupportResistanceAPIAdapter()
        
        # 从API适配器获取最新快照
        result = adapter.get_snapshots(limit=1)
        
        if not result['success'] or not result['data']:
            return jsonify({
                'success': False,
                'message': '暂无快照数据'
            })
        
        row = result['data'][0]
        
        scenario_1 = row.get('scenario_1_count', 0) or 0
        scenario_2 = row.get('scenario_2_count', 0) or 0
        scenario_3 = row.get('scenario_3_count', 0) or 0
        scenario_4 = row.get('scenario_4_count', 0) or 0
        
        # 检测信号
        # 抄底信号：情况1 >= 8 AND 情况2 >= 8（两个条件都要满足）
        buy_signal = scenario_1 >= 8 and scenario_2 >= 8
        
        # 逃顶信号：(情况3 + 情况4) >= 8（总和满足即可）
        sell_signal = (scenario_3 + scenario_4) >= 8
        
        result_data = {
            'success': True,
            'snapshot_time': row.get('snapshot_time'),
            'snapshot_date': row.get('snapshot_date'),
            'scenario_1_count': scenario_1,
            'scenario_2_count': scenario_2,
            'scenario_3_count': scenario_3,
            'scenario_4_count': scenario_4,
            'scenario_1_coins': row.get('scenario_1_coins', []),
            'scenario_2_coins': row.get('scenario_2_coins', []),
            'scenario_3_coins': row.get('scenario_3_coins', []),
            'scenario_4_coins': row.get('scenario_4_coins', []),
            'total_coins': row.get('total_coins', 27),
            'signals': {
                'buy': buy_signal,
                'sell': sell_signal,
                'buy_count': scenario_1 + scenario_2 if buy_signal else 0,
                'sell_count': scenario_3 + scenario_4 if sell_signal else 0
            },
            'data_source': 'JSONL (按日期存储)',
            'timezone': 'Beijing Time (UTC+8)'
        }
        
        return jsonify(result_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/support-resistance/dates')
def api_support_resistance_dates():
    """获取有快照数据的所有日期列表（从按日期存储的JSONL）"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        sys.path.insert(0, '/home/user/webapp/source_code')
        from support_resistance_daily_manager import SupportResistanceDailyManager
        
        manager = SupportResistanceDailyManager()
        
        # 获取所有可用日期
        available_dates = manager.get_available_dates()
        
        # 转换格式：YYYYMMDD -> YYYY-MM-DD
        formatted_dates = []
        for date_str in reversed(available_dates):  # 倒序，最新的在前
            if len(date_str) == 8:
                formatted_dates.append(f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}")
            else:
                formatted_dates.append(date_str)
        
        return jsonify({
            'success': True,
            'dates': formatted_dates,
            'count': len(formatted_dates),
            'data_source': 'JSONL (按日期存储)'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/api/support-resistance/escape-max-stats')
def api_support_resistance_escape_max_stats():
    """获取逃顶快照数的历史最大值统计（从按日期存储的JSONL）"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        sys.path.insert(0, '/home/user/webapp/source_code')
        from support_resistance_api_adapter import SupportResistanceAPIAdapter
        from datetime import datetime, timedelta
        
        adapter = SupportResistanceAPIAdapter()
        
        # 计算24小时前的时间
        now = datetime.now()
        time_24h_ago = now - timedelta(hours=24)
        time_2h_ago = now - timedelta(hours=2)
        
        # 获取最近2天的所有快照（确保覆盖24小时）
        today = now.strftime('%Y-%m-%d')
        yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 获取今日和昨日的快照
        snapshots_today = adapter.get_snapshots(date=today, limit=None)
        snapshots_yesterday = adapter.get_snapshots(date=yesterday, limit=None)
        
        all_snapshots = []
        if snapshots_today['success'] and snapshots_today['data']:
            all_snapshots.extend(snapshots_today['data'])
        if snapshots_yesterday['success'] and snapshots_yesterday['data']:
            all_snapshots.extend(snapshots_yesterday['data'])
        
        # 筛选24小时内和2小时内的快照
        rows_24h = []
        rows_2h = []
        
        for snapshot in all_snapshots:
            snapshot_time_str = snapshot.get('snapshot_time', '')
            if not snapshot_time_str:
                continue
                
            try:
                snapshot_time = datetime.strptime(snapshot_time_str, '%Y-%m-%d %H:%M:%S')
            except:
                continue
            
            scenario_3 = snapshot.get('scenario_3_count', 0) or 0
            scenario_4 = snapshot.get('scenario_4_count', 0) or 0
            escape_count = scenario_3 + scenario_4
            
            if snapshot_time >= time_24h_ago:
                rows_24h.append(escape_count)
                
                if snapshot_time >= time_2h_ago:
                    rows_2h.append(escape_count)
        
        # 计算24小时内的逃顶快照数和最大的逃顶信号数
        escape_snapshot_count_24h = sum(1 for count in rows_24h if count >= 5)
        max_escape_count_24h = max(rows_24h, default=0)
        
        # 计算2小时内的逃顶快照数和最大的逃顶信号数
        escape_snapshot_count_2h = sum(1 for count in rows_2h if count >= 5)
        max_escape_count_2h = max(rows_2h, default=0)
        
        return jsonify({
            'success': True,
            'stats_24h': {
                'escape_snapshot_count': escape_snapshot_count_24h,  # 逃顶快照数
                'max_escape_count': max_escape_count_24h  # 最大的逃顶信号数（S3+S4）
            },
            'stats_2h': {
                'escape_snapshot_count': escape_snapshot_count_2h,
                'max_escape_count': max_escape_count_2h
            },
            'data_source': 'JSONL (按日期存储)',
            'timezone': 'Beijing Time (UTC+8)'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'message': str(e),
            'traceback': traceback.format_exc()
        })

# =====================================================
# 支撑压力线全局趋势 API
# =====================================================

@app.route('/api/support-resistance/trend')
def api_support_resistance_trend():
    """获取全局趋势数据（支持分层加载：全局15分钟采样，放大后1分钟完整数据）"""
    try:
        import os
        import json
        from datetime import datetime, timedelta
        
        # 获取参数
        days = request.args.get('days', 30, type=int)  # 默认30天
        month = request.args.get('month', None)  # 可选：指定月份 YYYYMM
        sample = request.args.get('sample', 15, type=int)  # 采样间隔（分钟），默认15分钟
        start_time = request.args.get('start', None)  # 可选：开始时间（放大查看时使用）
        end_time = request.args.get('end', None)  # 可选：结束时间（放大查看时使用）
        
        trend_dir = '/home/user/webapp/data/support_resistance_trend'
        
        if month:
            # 指定月份
            trend_file = os.path.join(trend_dir, f'support_resistance_trend_{month}.jsonl')
            files_to_read = [trend_file] if os.path.exists(trend_file) else []
        else:
            # 读取最近N天的数据（可能跨月）
            now = datetime.now()
            months_to_check = set()
            for i in range(days + 1):
                date = now - timedelta(days=i)
                months_to_check.add(date.strftime('%Y%m'))
            
            files_to_read = []
            for m in sorted(months_to_check):
                trend_file = os.path.join(trend_dir, f'support_resistance_trend_{m}.jsonl')
                if os.path.exists(trend_file):
                    files_to_read.append(trend_file)
        
        # 读取数据
        trend_data = []
        cutoff_time = datetime.now() - timedelta(days=days) if not month else None
        
        # 时间范围过滤（放大查看时使用）
        filter_start = datetime.fromisoformat(start_time.replace('+08:00', '')) if start_time else None
        filter_end = datetime.fromisoformat(end_time.replace('+08:00', '')) if end_time else None
        
        for file_path in files_to_read:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            point = json.loads(line)
                            
                            # 时间过滤
                            point_time = datetime.fromisoformat(point['timestamp'].replace('+08:00', ''))
                            
                            # 过滤天数范围
                            if cutoff_time and point_time < cutoff_time:
                                continue
                            
                            # 过滤放大时间范围
                            if filter_start and point_time < filter_start:
                                continue
                            if filter_end and point_time > filter_end:
                                continue
                            
                            trend_data.append(point)
                        except:
                            continue
        
        # 按时间排序
        trend_data.sort(key=lambda x: x['timestamp'])
        
        # 数据采样（全局视图时降采样，放大后返回完整数据）
        sampled_data = trend_data
        actual_interval = '1 minute'
        
        if sample > 1 and not (start_time and end_time):
            # 全局视图：进行采样（每N分钟取一个点）
            sampled_data = []
            for i, point in enumerate(trend_data):
                try:
                    point_time = datetime.fromisoformat(point['timestamp'].replace('+08:00', ''))
                    # 每N分钟取一个点：分钟数能被N整除
                    if point_time.minute % sample == 0:
                        sampled_data.append(point)
                except:
                    continue
            actual_interval = f'{sample} minutes'
        else:
            # 放大视图或sample=1：返回完整数据
            actual_interval = '1 minute'
        
        return jsonify({
            'success': True,
            'data': sampled_data,
            'count': len(sampled_data),
            'total_count': len(trend_data),
            'days': days,
            'sample': sample,
            'data_source': 'JSONL Trend Data',
            'interval': actual_interval,
            'description': f'采集频率1分钟，返回间隔{actual_interval}',
            'is_sampled': len(sampled_data) < len(trend_data),
            'zoom_range': {
                'start': start_time,
                'end': end_time
            } if (start_time and end_time) else None
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# =====================================================
# OKEx K线指标系统 API路由
# =====================================================

@app.route('/kline-indicators')
def kline_indicators_page():
    """K线指标系统监控页面"""
    return render_template('kline_indicators.html')

@app.route('/api/kline-indicators/latest')
def api_kline_indicators_latest():
    """
    获取最新的技术指标数据
    
    参数：
        - symbol: 币种（可选，如BTC-USDT-SWAP）
        - timeframe: 时间周期（可选，5m或1h）
    """
    try:
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe')
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if symbol:
            conditions.append('symbol = ?')
            params.append(symbol)
        if timeframe:
            conditions.append('timeframe = ?')
            params.append(timeframe)
        
        # 构建WHERE子句
        if conditions:
            where_clause = f"WHERE {' AND '.join(conditions)} AND"
        else:
            where_clause = "WHERE"
        
        # 获取每个币种+时间周期的最新数据
        cursor.execute(f'''
            SELECT 
                symbol, timeframe, current_price, rsi_14, 
                sar, sar_position, sar_quadrant, sar_count_label,
                bb_upper, bb_middle, bb_lower, record_time
            FROM okex_technical_indicators
            {where_clause} id IN (
                SELECT MAX(id)
                FROM okex_technical_indicators
                GROUP BY symbol, timeframe
            )
            ORDER BY symbol, timeframe
        ''', params)
        
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            data.append({
                'symbol': row['symbol'],
                'timeframe': row['timeframe'],
                'current_price': row['current_price'],
                'rsi_14': row['rsi_14'],
                'sar': row['sar'],
                'sar_position': row['sar_position'],
                'sar_quadrant': row['sar_quadrant'],
                'sar_count_label': row['sar_count_label'],
                'bb_upper': row['bb_upper'],
                'bb_middle': row['bb_middle'],
                'bb_lower': row['bb_lower'],
                'record_time': row['record_time']
            })
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'timestamp': datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/kline-indicators/collector-status')
def api_kline_indicators_status():
    """获取采集器运行状态"""
    try:
        conn = sqlite3.connect('crypto_data.db', timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 获取最新采集时间
        cursor.execute('''
            SELECT MAX(record_time) as last_collection
            FROM okex_technical_indicators
        ''')
        row = cursor.fetchone()
        last_collection = row['last_collection'] if row else None
        
        # 统计数据量
        cursor.execute('SELECT COUNT(*) as count_indicators FROM okex_technical_indicators')
        count_indicators = cursor.fetchone()['count_indicators']
        
        # 统计不同时间周期的数量
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN timeframe = '5m' THEN 1 ELSE 0 END) as count_5m,
                SUM(CASE WHEN timeframe = '1H' THEN 1 ELSE 0 END) as count_1h
            FROM okex_technical_indicators
        ''')
        row = cursor.fetchone()
        count_5m = row['count_5m'] or 0
        count_1h = row['count_1h'] or 0
        
        conn.close()
        
        # 计算状态（数据库存储的是北京时间）
        if last_collection:
            # 数据库中的时间是北京时间，需要与北京时间比较
            import pytz
            beijing_tz = pytz.timezone('Asia/Shanghai')
            last_time = datetime.strptime(last_collection, '%Y-%m-%d %H:%M:%S')
            now_beijing = datetime.now(beijing_tz).replace(tzinfo=None)
            delta_minutes = (now_beijing - last_time).total_seconds() / 60
            status = 'running' if delta_minutes < 10 else 'stopped'
        else:
            status = 'not_started'
            delta_minutes = None
        
        return jsonify({
            'success': True,
            'status': status,
            'last_collection_time': last_collection,
            'minutes_since_last': round(delta_minutes, 1) if delta_minutes else None,
            'data_counts': {
                'kline_5m': count_5m,
                'kline_1h': count_1h,
                'indicators': count_indicators
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def cleanup_expired_signals():
    """
    清理2小时之前的过期信号
    将 is_valid 设置为 0
    """
    try:
        conn = sqlite3.connect('crypto_data.db', timeout=5.0)
        cursor = conn.cursor()
        
        from datetime import datetime, timedelta
        cutoff_time = (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 清理买点4过期信号
        cursor.execute('''
            UPDATE buy_point_4_signals
            SET is_valid = 0
            WHERE is_valid = 1 AND confirm_time < ?
        ''', (cutoff_time,))
        buy_point_4_cleaned = cursor.rowcount
        
        # 清理卖点1过期信号
        cursor.execute('''
            UPDATE sell_point_1_signals
            SET is_valid = 0
            WHERE is_valid = 1 AND mark_time < ?
        ''', (cutoff_time,))
        sell_point_1_cleaned = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return {
            'buy_point_4_cleaned': buy_point_4_cleaned,
            'sell_point_1_cleaned': sell_point_1_cleaned
        }
    except Exception as e:
        return {'error': str(e)}

@app.route('/api/kline-indicators/signals')
def api_kline_indicators_signals():
    """
    返回K线指标信号（2小时时间窗口）
    数据完全从数据库读取，不进行实时检测
    - 买点4: 从 buy_point_4_signals 表读取（RSI < 20）
    - 卖点1: 从 sell_point_1_signals 表读取（RSI >= 60）
    """
    try:
        conn = sqlite3.connect('crypto_data.db', timeout=10.0)
        cursor = conn.cursor()
        
        from datetime import datetime, timedelta
        now = datetime.now()
        cutoff_time = (now - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 初始化信号容器
        signals = {
            'buy_point_4': [],      # 买点4（从数据库读取）
            'sell_point_1': []      # 卖点1（从数据库读取）
        }
        
        # 1. 读取买点4信号（不查询当前价格，使用信号时的价格）
        cursor.execute('''
            SELECT symbol, low_price, low_time, confirm_time, 
                   signal_generated_at, confirm_rsi
            FROM buy_point_4_signals
            WHERE is_valid = 1 
              AND confirm_rsi IS NOT NULL 
              AND confirm_rsi < 20
              AND confirm_time >= ?
            ORDER BY confirm_time DESC
            LIMIT 100
        ''', (cutoff_time,))
        
        for row in cursor.fetchall():
            signals['buy_point_4'].append({
                'symbol': row[0],
                'price': row[1],
                'low_7d': row[1],
                'low_time': row[2],
                'confirm_time': row[3],
                'signal_generated_at': row[4],
                'confirm_rsi': row[5],
                'current_price': row[1],  # 使用确认时的价格
                'distance': 0.0  # 信号时刻距离为0
            })
        
        # 2. 读取卖点1信号（不查询当前价格）
        cursor.execute('''
            SELECT symbol, high_price, high_time, mark_price, 
                   mark_time, mark_rsi, signal_generated_at
            FROM sell_point_1_signals
            WHERE is_valid = 1 
              AND mark_rsi IS NOT NULL 
              AND mark_rsi >= 60
              AND mark_time >= ?
            ORDER BY mark_time DESC
            LIMIT 100
        ''', (cutoff_time,))
        
        for row in cursor.fetchall():
            signals['sell_point_1'].append({
                'symbol': row[0],
                'high_price': row[1],
                'high_time': row[2],
                'mark_price': row[3],
                'mark_time': row[4],
                'mark_rsi': row[5],
                'signal_generated_at': row[6],
                'current_price': row[3],  # 使用标记时的价格
                'distance': 0.0  # 信号时刻距离为0
            })
        
        conn.close()
        
        # 统计信号数量
        signal_counts = {k: len(v) for k, v in signals.items()}
        
        # 异步清理过期信号（不阻塞响应）
        import threading
        threading.Thread(target=cleanup_expired_signals, daemon=True).start()
        
        return jsonify({
            'success': True,
            'data': {
                'signals': signals,
                'counts': signal_counts,
                'update_time': now.strftime('%Y-%m-%d %H:%M:%S')
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/kline-indicators-tv/latest')
def api_kline_indicators_tv_latest():
    """
    获取TradingView直接获取的K线指标数据（不计算）
    支持参数: symbol, timeframe
    数据源: TradingView (OKX交易所)
    """
    try:
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe')
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if symbol:
            conditions.append('symbol = ?')
            params.append(symbol)
        if timeframe:
            conditions.append('timeframe = ?')
            params.append(timeframe)
        
        # 构建WHERE子句
        if conditions:
            where_clause = f"WHERE {' AND '.join(conditions)}"
        else:
            where_clause = ""
        
        # 获取每个币种+时间周期的最新数据
        query = f'''
            SELECT 
                symbol, timeframe, current_price, rsi_14, 
                sar, bb_upper, bb_middle, bb_lower,
                ema_10, ema_20, recommendation,
                buy_signals, sell_signals, neutral_signals,
                record_time
            FROM okex_tv_indicators
            {where_clause}
            ORDER BY symbol, timeframe
        '''
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        data = []
        for row in rows:
            # Calculate SAR position
            sar_position = None
            if row['sar'] and row['current_price']:
                sar_position = 'bullish' if row['current_price'] > row['sar'] else 'bearish'
            
            # Calculate BB middle if not provided
            bb_middle = row['bb_middle']
            if not bb_middle and row['bb_upper'] and row['bb_lower']:
                bb_middle = (row['bb_upper'] + row['bb_lower']) / 2
            
            data.append({
                'symbol': row['symbol'],
                'timeframe': row['timeframe'],
                'current_price': row['current_price'],
                'rsi_14': row['rsi_14'],
                'sar': row['sar'],
                'sar_position': sar_position,
                'bb_upper': row['bb_upper'],
                'bb_middle': bb_middle,
                'bb_lower': row['bb_lower'],
                'ema_10': row['ema_10'],
                'ema_20': row['ema_20'],
                'recommendation': row['recommendation'],
                'buy_signals': row['buy_signals'],
                'sell_signals': row['sell_signals'],
                'neutral_signals': row['neutral_signals'],
                'record_time': row['record_time'],
                'data_source': 'TradingView (直接获取, 不计算)'
            })
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'data_source': 'TradingView API (OKX Exchange)',
            'note': '所有技术指标均直接从TradingView获取，不进行本地计算',
            'timestamp': datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/kline-indicators-tv/collector-status')
def api_kline_indicators_tv_status():
    """获取TradingView指标采集器运行状态"""
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='okex_tv_collector_status'
        ''')
        
        if not cursor.fetchone():
            conn.close()
            return jsonify({
                'success': True,
                'status': 'not_initialized',
                'message': 'TradingView collector not initialized yet'
            })
        
        # 获取采集状态
        cursor.execute('''
            SELECT last_collect_time, total_indicators_count, status
            FROM okex_tv_collector_status
            WHERE id = 1
        ''')
        
        row = cursor.fetchone()
        
        # 统计数据量
        cursor.execute('SELECT COUNT(*) FROM okex_tv_indicators')
        count_indicators = cursor.fetchone()[0]
        
        conn.close()
        
        status = row['status'] if row else 'stopped'
        last_collection = row['last_collect_time'] if row else None
        
        return jsonify({
            'success': True,
            'status': status,
            'last_collection_time': last_collection,
            'total_indicators': count_indicators,
            'data_source': 'TradingView (直接获取)',
            'note': 'RSI, SAR, 布林带均直接从TradingView获取，不计算'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 币种详情页面 ====================

@app.route('/symbol/<symbol>')
def symbol_detail(symbol):
    """币种详情页面 - 自动重定向到v6以避开浏览器缓存"""
    from flask import redirect, url_for
    return redirect(url_for('symbol_detail_v6', symbol=symbol), code=302)

@app.route('/api/symbol/<symbol>/kline')
def api_symbol_kline(symbol):
    """获取币种K线数据（10天）- 使用okex_technical_indicators表"""
    try:
        timeframe = request.args.get('timeframe', '5m')  # 5m 或 1H
        
        # 将symbol转换为标准格式
        if not symbol.endswith('-USDT-SWAP'):
            symbol = f"{symbol}-USDT-SWAP"
        
        # 转换timeframe格式: 5m -> 5m, 1h -> 1H (数据库中使用大写H)
        db_timeframe = timeframe.upper() if timeframe == '1h' else timeframe
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 根据时间周期设置limit
        if timeframe == '5m':
            # 10天的5分钟K线 = 10 * 24 * 12 = 2880根
            limit = 2880
        else:  # 1h
            # 10天的1小时K线 = 10 * 24 = 240根
            limit = 240
        
        # 从okex_kline_ohlc表获取真实的OHLC K线数据
        # 先按时间降序取最新的N条，然后反转为升序
        cursor.execute('''
            SELECT timestamp, open, high, low, close, volume
            FROM (
                SELECT timestamp, open, high, low, close, volume
                FROM okex_kline_ohlc
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            )
            ORDER BY timestamp ASC
        ''', (symbol, db_timeframe, limit))
        
        rows = cursor.fetchall()
        
        # 如果OHLC表没有数据，回退到indicators_history表
        if not rows:
            cursor.execute('''
                SELECT timestamp, current_price
                FROM (
                    SELECT timestamp, current_price
                    FROM okex_indicators_history
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                )
                ORDER BY timestamp ASC
            ''', (symbol, db_timeframe, limit))
            
            rows_indicators = cursor.fetchall()
            kline_data = []
            
            for i, row in enumerate(rows_indicators):
                timestamp = int(row[0]) if row[0] else 0
                close_price = float(row[1]) if row[1] else 0
                
                # 模拟OHLC
                open_price = close_price * (1 + 0.001 * (i % 3 - 1))
                high_price = close_price * 1.002
                low_price = close_price * 0.998
                volume = close_price * 10
                
                kline_data.append({
                    'timestamp': timestamp,
                    'data': [open_price, high_price, low_price, close_price],  # 标准K线格式: OHLC
                    'volume': volume
                })
        else:
            # 使用真实OHLC数据
            kline_data = []
            for row in rows:
                timestamp = int(row[0]) if row[0] else 0
                open_price = float(row[1]) if row[1] else 0
                high_price = float(row[2]) if row[2] else 0
                low_price = float(row[3]) if row[3] else 0
                close_price = float(row[4]) if row[4] else 0
                volume = float(row[5]) if row[5] else 0
                
                kline_data.append({
                    'timestamp': timestamp,
                    'data': [open_price, high_price, low_price, close_price],  # 标准K线格式: OHLC
                    'volume': volume
                })
        
        # 查询技术标记数据（窄幅震荡、高低点、SAR、RSI、布林带等）
        cursor.execute('''
            SELECT timestamp, is_narrow_range, change_percent, range_percent, consecutive_count,
                   is_7d_high, is_7d_low, is_48h_high, is_48h_low,
                   rsi_14, sar, sar_position, sar_quadrant, sar_count_label,
                   bb_upper, bb_middle, bb_lower, is_buy_point_4
            FROM kline_technical_markers
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp ASC
        ''', (symbol, db_timeframe))
        
        marker_rows = cursor.fetchall()
        markers_dict = {}
        for marker_row in marker_rows:
            ts = int(marker_row[0]) if marker_row[0] else 0
            markers_dict[ts] = {
                'is_narrow_range': bool(marker_row[1]),
                'change_percent': float(marker_row[2]) if marker_row[2] else 0,
                'range_percent': float(marker_row[3]) if marker_row[3] else 0,
                'consecutive_count': int(marker_row[4]) if marker_row[4] else 0,
                'is_7d_high': bool(marker_row[5]),
                'is_7d_low': bool(marker_row[6]),
                'is_48h_high': bool(marker_row[7]),
                'is_48h_low': bool(marker_row[8]),
                'rsi_14': float(marker_row[9]) if marker_row[9] else None,
                'sar': float(marker_row[10]) if marker_row[10] else None,
                'sar_position': marker_row[11],
                'sar_quadrant': int(marker_row[12]) if marker_row[12] else None,
                'sar_count_label': marker_row[13],
                'bb_upper': float(marker_row[14]) if marker_row[14] else None,
                'bb_middle': float(marker_row[15]) if marker_row[15] else None,
                'bb_lower': float(marker_row[16]) if marker_row[16] else None,
                'is_buy_point_4': bool(marker_row[17])
            }
        
        # 将标记数据合并到K线数据中
        for item in kline_data:
            ts = item['timestamp']
            if ts in markers_dict:
                item['markers'] = markers_dict[ts]
        
        conn.close()
        
        # 创建响应对象并添加缓存头
        response = jsonify({
            'success': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'data': kline_data,
            'count': len(kline_data)
        })
        
        # 添加HTTP缓存头（缓存60秒，因为数据每60秒更新一次）
        response.headers['Cache-Control'] = 'public, max-age=60'
        response.headers['Vary'] = 'Accept-Encoding'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/symbol/<symbol>/indicators')
def api_symbol_indicators(symbol):
    """获取币种技术指标数据 - 使用okex_technical_indicators表"""
    try:
        timeframe = request.args.get('timeframe', '5m')
        
        # 将symbol转换为标准格式
        if not symbol.endswith('-USDT-SWAP'):
            symbol = f"{symbol}-USDT-SWAP"
        
        # 转换timeframe格式: 5m -> 5m, 1h -> 1H
        db_timeframe = timeframe.upper() if timeframe == '1h' else timeframe
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 设置limit
        limit = 2880 if timeframe == '5m' else 240
        
        # 从okex_indicators_history表获取历史指标数据
        cursor.execute('''
            SELECT created_at, current_price, rsi_14, sar, sar_position, sar_count_label,
                   bb_upper, bb_middle, bb_lower, timestamp
            FROM okex_indicators_history
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp ASC
            LIMIT ?
        ''', (symbol, db_timeframe, limit))
        
        rows = cursor.fetchall()
        
        indicators = []
        for row in rows:
            # 使用数据库中的timestamp字段（毫秒）
            timestamp = int(row[9]) if row[9] else 0
            
            indicators.append({
                'timestamp': timestamp,
                'price': float(row[1]) if row[1] else None,
                'rsi': float(row[2]) if row[2] else None,
                'sar': float(row[3]) if row[3] else None,
                'sar_position': row[4],
                'sar_label': row[5],
                'bb_upper': float(row[6]) if row[6] else None,
                'bb_middle': float(row[7]) if row[7] else None,
                'bb_lower': float(row[8]) if row[8] else None,
                'time_str': row[0]  # 保留时间字符串用于调试
            })
        
        conn.close()
        
        # 创建响应对象并添加缓存头
        response = jsonify({
            'success': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'data': indicators,
            'count': len(indicators)
        })
        
        # 添加HTTP缓存头（缓存60秒，因为数据每60秒更新一次）
        response.headers['Cache-Control'] = 'public, max-age=60'
        response.headers['Vary'] = 'Accept-Encoding'
        
        return response
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/signals/recent')
def api_signals_recent():
    """获取最近2小时内的交易信号，按类型分类"""
    try:
        from datetime import datetime, timedelta
        import json
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 计算2小时前的时间
        two_hours_ago = (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        # 获取2小时内的信号
        cursor.execute('''
            SELECT record_time, long_signals, short_signals, 
                   today_new_high, today_new_low, raw_data
            FROM trading_signals
            WHERE record_time >= ?
            ORDER BY record_time DESC
        ''', (two_hours_ago,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # 分类统计
        signals_by_type = {
            'long': [],  # 做多信号
            'short': [],  # 做空信号
            'new_high': [],  # 新高信号
            'new_low': []  # 新低信号
        }
        
        for row in rows:
            record_time = row[0]
            long_count = row[1] or 0
            short_count = row[2] or 0
            new_high = row[3] or 0
            new_low = row[4] or 0
            raw_data = json.loads(row[5]) if row[5] else {}
            
            if long_count > 0:
                signals_by_type['long'].append({
                    'time': record_time,
                    'count': long_count,
                    'detail': raw_data.get('breakdown', {})
                })
            
            if short_count > 0:
                signals_by_type['short'].append({
                    'time': record_time,
                    'count': short_count,
                    'detail': raw_data.get('breakdown', {})
                })
            
            if new_high > 0:
                signals_by_type['new_high'].append({
                    'time': record_time,
                    'count': new_high
                })
            
            if new_low > 0:
                signals_by_type['new_low'].append({
                    'time': record_time,
                    'count': new_low
                })
        
        # 计算汇总
        summary = {
            'long_total': sum(s['count'] for s in signals_by_type['long']),
            'short_total': sum(s['count'] for s in signals_by_type['short']),
            'new_high_total': sum(s['count'] for s in signals_by_type['new_high']),
            'new_low_total': sum(s['count'] for s in signals_by_type['new_low']),
            'time_range': two_hours_ago
        }
        
        return jsonify({
            'success': True,
            'signals': signals_by_type,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/symbol/<symbol>/extremes')
def api_symbol_extremes(symbol):
    """获取币种的48小时和7天高低点"""
    try:
        from datetime import datetime, timedelta
        
        timeframe = request.args.get('timeframe', '5m')
        
        # 将symbol转换为标准格式
        if not symbol.endswith('-USDT-SWAP'):
            symbol = f"{symbol}-USDT-SWAP"
        
        # 转换timeframe格式
        db_timeframe = timeframe.upper() if timeframe == '1h' else timeframe
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 计算时间范围（毫秒时间戳）
        now_ms = int(datetime.now().timestamp() * 1000)
        hours_48_ago_ms = int((datetime.now() - timedelta(hours=48)).timestamp() * 1000)
        days_7_ago_ms = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
        
        # 获取48小时内的高低点
        cursor.execute('''
            SELECT timestamp, open, high, low, close
            FROM okex_kline_ohlc
            WHERE symbol = ? AND timeframe = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (symbol, db_timeframe, hours_48_ago_ms))
        
        rows_48h = cursor.fetchall()
        
        # 获取7天内的高低点
        cursor.execute('''
            SELECT timestamp, open, high, low, close
            FROM okex_kline_ohlc
            WHERE symbol = ? AND timeframe = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (symbol, db_timeframe, days_7_ago_ms))
        
        rows_7d = cursor.fetchall()
        conn.close()
        
        # 计算48小时高低点
        extremes_48h = {'high': None, 'low': None, 'high_time': None, 'low_time': None}
        if rows_48h:
            max_price = max(row[2] for row in rows_48h)  # high
            min_price = min(row[3] for row in rows_48h)  # low
            
            for row in rows_48h:
                if row[2] == max_price:
                    extremes_48h['high'] = max_price
                    extremes_48h['high_time'] = row[0]
                if row[3] == min_price:
                    extremes_48h['low'] = min_price
                    extremes_48h['low_time'] = row[0]
        
        # 计算7天高低点
        extremes_7d = {'high': None, 'low': None, 'high_time': None, 'low_time': None}
        if rows_7d:
            max_price = max(row[2] for row in rows_7d)  # high
            min_price = min(row[3] for row in rows_7d)  # low
            
            for row in rows_7d:
                if row[2] == max_price:
                    extremes_7d['high'] = max_price
                    extremes_7d['high_time'] = row[0]
                if row[3] == min_price:
                    extremes_7d['low'] = min_price
                    extremes_7d['low_time'] = row[0]
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'extremes_48h': extremes_48h,
            'extremes_7d': extremes_7d
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 新版本路由 - 强制刷新 ====================

@app.route('/symbol/<symbol>/v6')
def symbol_detail_v6(symbol):
    """币种详情页面 v6.0 - 全新路由避开缓存"""
    from datetime import datetime
    from flask import make_response
    
    cache_buster = datetime.now().strftime('%Y%m%d%H%M%S')
    response = make_response(render_template('symbol_detail_v6.html', symbol=symbol, cache_buster=cache_buster))
    
    # 禁用HTML页面缓存，确保每次都加载最新代码
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/symbol/<symbol>/v7')
def symbol_detail_v7(symbol):
    """币种详情页面 v7.0 - 全新路由避开缓存，简化调试"""
    from datetime import datetime
    from flask import make_response
    
    cache_buster = datetime.now().strftime('%Y%m%d%H%M%S')
    response = make_response(render_template('symbol_detail_v7.html', symbol=symbol, cache_buster=cache_buster))
    
    # 禁用HTML页面缓存，确保每次都加载最新代码
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/symbol/<symbol>/v8')
def symbol_detail_v8(symbol):
    """币种详情页面 v8.0 - 彻底避开所有浏览器缓存"""
    from datetime import datetime
    from flask import make_response
    
    cache_buster = datetime.now().strftime('%Y%m%d%H%M%S')
    response = make_response(render_template('symbol_detail_v8.html', symbol=symbol, cache_buster=cache_buster))
    
    # 最强缓存禁用策略
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    return response

@app.route('/kline/<symbol>')
def kline_chart(symbol):
    """全新的K线图路由 - 完全独立的地址"""
    from datetime import datetime
    from flask import make_response
    
    cache_buster = datetime.now().strftime('%Y%m%d%H%M%S')
    response = make_response(render_template('kline_chart.html', symbol=symbol, cache_buster=cache_buster))
    
    # 强制禁用所有缓存
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    
    return response

@app.route('/test-xlm-data')
def test_xlm_data():
    """XLM数据诊断测试页"""
    return render_template('test_xlm_data.html')

@app.route('/chart/<symbol>')
def chart_new(symbol):
    """全新K线图 - 从零开始，简单清晰"""
    from datetime import datetime
    from flask import make_response
    
    cache_buster = datetime.now().strftime('%Y%m%d%H%M%S')
    response = make_response(render_template('chart_new.html', symbol=symbol, cache_buster=cache_buster))
    
    # 强制禁用所有缓存
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

# ==================== Google Drive 监控状态 API ====================

@app.route('/gdrive-monitor-status')
def gdrive_monitor_status_page():
    """Google Drive 监控状态页面 - 11分钟超时保险机制可视化"""
    return render_template('gdrive_monitor_status.html')

@app.route('/api/gdrive-monitor/status')
def api_gdrive_monitor_status():
    """获取 Google Drive 监控状态的实时数据"""
    import os
    import json
    from datetime import datetime
    import pytz
    import re
    import requests
    from bs4 import BeautifulSoup
    
    try:
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        
        # 读取配置文件
        config_file = '/home/user/webapp/daily_folder_config.json'
        config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        # 🆕 扫描 Google Drive 中的实际文件
        gdrive_dates = {}
        gdrive_scan_error = None
        try:
            ROOT_FOLDER_ID = "1jFGGlGP5KEVhAxpCNxFIYEFI5-cDOBjM"
            url = f"https://drive.google.com/embeddedfolderview?id={ROOT_FOLDER_ID}"
            response = requests.get(url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            all_links = soup.find_all('a', href=True)
            pattern = re.compile(r'(\d{4}-\d{2}-\d{2})_(\d{4})\.txt')
            
            for link in all_links:
                text = link.get_text(strip=True)
                match = pattern.match(text)
                if match:
                    date = match.group(1)
                    if date not in gdrive_dates:
                        gdrive_dates[date] = 0
                    gdrive_dates[date] += 1
        except Exception as e:
            gdrive_scan_error = str(e)
        
        # 读取日志文件获取最新状态
        log_file = '/home/user/webapp/gdrive_final_detector.log'
        latest_file = None
        latest_file_time = None
        check_count = 0
        last_file_found_time = None
        recovery_count = 0
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # 分析日志
                for line in reversed(lines[-500:]):  # 只看最近500行
                    # 查找最新文件
                    if '最新文件名 =' in line and not latest_file:
                        match = re.search(r'最新文件名 = (.+\.txt)', line)
                        if match:
                            latest_file = match.group(1)
                            # 提取时间戳
                            time_match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                            if time_match:
                                latest_file_time = time_match.group(1)
                    
                    # 查找检查次数
                    if '检查 #' in line:
                        match = re.search(r'检查 #(\d+)', line)
                        if match:
                            check_count = max(check_count, int(match.group(1)))
                    
                    # 查找恢复触发
                    if '触发11分钟超时恢复机制' in line:
                        recovery_count += 1
                    
                    # 查找最后找到文件的时间
                    if '找到' in line and 'TXT文件' in line and not last_file_found_time:
                        match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
                        if match:
                            last_file_found_time = match.group(1)
        
        # 计算距上次找到文件的时间
        time_since_last_file = 0
        if last_file_found_time:
            try:
                last_time = datetime.strptime(last_file_found_time, '%Y-%m-%d %H:%M:%S')
                last_time = beijing_tz.localize(last_time)
                time_since_last_file = (now - last_time).total_seconds()
            except:
                pass
        
        # 获取数据库记录数
        db_records = 0
        try:
            import sqlite3
            conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM crypto_snapshots WHERE snapshot_date = ?", (now.strftime('%Y-%m-%d'),))
            db_records = cursor.fetchone()[0]
            conn.close()
        except:
            pass
        
        # 计算系统运行时长 (从最早的日志时间戳开始)
        uptime_seconds = 0
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                match = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', first_line)
                if match:
                    start_time = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                    start_time = beijing_tz.localize(start_time)
                    uptime_seconds = (now - start_time).total_seconds()
        
        # 🆕 判断数据源状态
        today_str = now.strftime('%Y-%m-%d')
        data_source_status = 'unknown'
        data_source_message = ''
        
        if gdrive_dates:
            latest_gdrive_date = max(gdrive_dates.keys())
            if latest_gdrive_date == today_str:
                data_source_status = 'active'
                data_source_message = f'✅ 数据源正常，今天有 {gdrive_dates[today_str]} 个文件'
            else:
                days_old = (datetime.strptime(today_str, '%Y-%m-%d') - datetime.strptime(latest_gdrive_date, '%Y-%m-%d')).days
                data_source_status = 'stale'
                data_source_message = f'⚠️  数据源已停更 {days_old} 天，最新数据：{latest_gdrive_date}'
        elif gdrive_scan_error:
            data_source_status = 'error'
            data_source_message = f'❌ 无法访问 Google Drive: {gdrive_scan_error}'
        else:
            data_source_status = 'empty'
            data_source_message = '❌ Google Drive 中没有任何数据文件'
        
        return jsonify({
            'success': True,
            'time_since_last_file': time_since_last_file,
            'current_folder_id': config.get('folder_id', 'N/A'),
            'folder_date': config.get('current_date', '--'),
            'latest_file': latest_file or '--',
            'file_time': latest_file_time or '--',
            'gdrive_dates': gdrive_dates,  # 🆕 Google Drive 中的日期分布
            'data_source_status': data_source_status,  # 🆕 数据源状态
            'data_source_message': data_source_message,  # 🆕 数据源状态消息
            'today_date': today_str,  # 🆕 当前日期
            'root_folder_odd': config.get('root_folder_odd', 'N/A'),  # 🆕 单数日期父文件夹
            'root_folder_even': config.get('root_folder_even', 'N/A'),  # 🆕 双数日期父文件夹
            'recovery_count': recovery_count,
            'check_count': check_count,
            'files_found': check_count,  # 简化处理
            'db_records': db_records,
            'last_update': now.strftime('%H:%M:%S'),
            'uptime_seconds': uptime_seconds,
            'current_time': now.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 每日00:10任务状态 API ====================

@app.route('/daily-tasks-status')
def daily_tasks_status_page():
    """每日00:10任务执行状态页面"""
    return render_template('daily_tasks_status.html')

@app.route('/api/daily-tasks/status')
def api_daily_tasks_status():
    """获取每日00:10任务的执行状态"""
    import os
    import json
    from datetime import datetime
    import pytz
    
    try:
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        today_str = now.strftime('%Y-%m-%d')
        
        # 读取配置文件
        config_file = '/home/user/webapp/daily_folder_config.json'
        config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        # 父文件夹更新任务状态
        parent_folder_update = {
            'status': config.get('auto_update_status', 'pending'),
            'last_update': config.get('last_auto_update', '--'),
            'parent_folder_id': config.get('root_folder_odd') or config.get('root_folder_even', '--'),
            'child_folder_id': config.get('folder_id', '--'),
            'url': config.get('parent_folder_url', '--')
        }
        
        # 清理任务状态
        cleanup = {
            'last_cleanup': config.get('last_cleanup', None),
            'cleanup_reason': config.get('cleanup_reason', '--'),
            'root_folder_odd': config.get('root_folder_odd'),
            'root_folder_even': config.get('root_folder_even')
        }
        
        return jsonify({
            'success': True,
            'today_date': today_str,
            'parent_folder_update': parent_folder_update,
            'cleanup': cleanup
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/daily-tasks/logs')
def api_daily_tasks_logs():
    """获取每日任务的执行日志"""
    import os
    
    try:
        log_file = '/home/user/webapp/parent_folder_update.log'
        logs = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 只返回最近100行
                logs = [line.rstrip() for line in lines[-100:]]
        
        return jsonify({
            'success': True,
            'logs': logs
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==================== 文件夹更新监控 API ====================

@app.route('/folder-update-monitor')
def folder_update_monitor():
    """文件夹更新监控页面"""
    return render_template('folder_update_monitor.html')

@app.route('/api/folder-update-status')
def api_folder_update_status():
    """获取文件夹更新状态"""
    import os
    import json
    
    try:
        beijing_tz = pytz.timezone('Asia/Shanghai')
        now = datetime.now(beijing_tz)
        today_str = now.strftime('%Y-%m-%d')
        
        # 读取配置文件
        config_file = '/home/user/webapp/daily_folder_config.json'
        config = {}
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        
        config_date = config.get('current_date', 'unknown')
        need_update = config_date != today_str
        
        return jsonify({
            'success': True,
            'data': {
                'config_date': config_date,
                'today_date': today_str,
                'folder_id': config.get('folder_id', 'N/A'),
                'latest_txt': config.get('latest_txt', 'N/A'),
                'txt_count': config.get('txt_count', 0),
                'last_updated': config.get('last_updated', 'N/A'),
                'need_update': need_update,
                'message': '配置日期与今天不匹配' if need_update else '配置正常'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/trigger-folder-update', methods=['POST'])
def api_trigger_folder_update():
    """触发文件夹更新"""
    import subprocess
    import os
    
    try:
        script_path = '/home/user/webapp/auto_update_today_folder.py'
        
        if not os.path.exists(script_path):
            return jsonify({
                'success': False,
                'message': '更新脚本不存在'
            }), 404
        
        # 执行更新脚本
        result = subprocess.run(
            ['python3', script_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            # 读取更新后的配置
            config_file = '/home/user/webapp/daily_folder_config.json'
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return jsonify({
                'success': True,
                'data': {
                    'folder_id': config.get('folder_id'),
                    'date': config.get('current_date'),
                    'latest_txt': config.get('latest_txt'),
                    'txt_count': config.get('txt_count', 0)
                },
                'message': '更新成功'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'更新失败: {result.stderr}'
            }), 500
            
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': '更新超时（60秒）'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/list-recent-folders')
def api_list_recent_folders():
    """列出最近的文件夹"""
    import requests
    from bs4 import BeautifulSoup
    import re
    
    try:
        parent_folder_id = "1j8YV6KysUCmgcmASFOxztWWIE1Vq-kYV"
        url = f"https://drive.google.com/embeddedfolderview?id={parent_folder_id}"
        
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        folders = []
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if '/folders/' in href:
                match = re.search(r'/folders/([a-zA-Z0-9_-]+)', href)
                if match:
                    folder_id = match.group(1)
                    # 检查是否是日期文件夹
                    if re.search(r'\d{4}-\d{2}-\d{2}', text):
                        folders.append({
                            'name': text,
                            'id': folder_id
                        })
        
        # 排序（最新的在前）
        folders.sort(key=lambda x: x['name'], reverse=True)
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        today = datetime.now(beijing_tz).strftime('%Y-%m-%d')
        
        return jsonify({
            'success': True,
            'data': {
                'folders': folders[:10],  # 只返回最近10个
                'today': today
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/api/get-update-log')
def api_get_update_log():
    """获取更新日志"""
    import os
    
    try:
        log_file = '/home/user/webapp/auto_update_folder.log'
        log_content = ''
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 只返回最近200行
                log_content = ''.join(lines[-200:])
        
        return jsonify({
            'success': True,
            'data': {
                'log': log_content or '暂无日志'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# 旧的telegram-dashboard路由已废弃，使用下方新版本
# @app.route('/telegram-dashboard')
# def telegram_dashboard():
#     """Telegram信号推送系统监控面板"""
#     import time
#     cache_buster = int(time.time())
#     return render_template('telegram_dashboard.html', cache_buster=cache_buster)

@app.route('/api/telegram/status')
def telegram_status():
    """获取Telegram监控系统状态"""
    try:
        import subprocess
        import os
        
        # 检查进程是否运行（检查telegram_signal_system.py而不是tg_signal_monitor.py）
        result = subprocess.run(
            ['pgrep', '-f', 'telegram_signal_system.py'],
            capture_output=True,
            text=True
        )
        
        is_running = bool(result.stdout.strip())
        pid = result.stdout.strip() if is_running else None
        
        # 获取数据库统计
        db_stats = {}
        signal_counts = {}  # 初始化为空字典
        db_path = '/home/user/webapp/databases/tg_signals.db'
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path, timeout=5.0)
            cursor = conn.cursor()
            
            # 获取总发送数
            cursor.execute("SELECT COUNT(*) FROM signal_history")
            total_sent = cursor.fetchone()[0]
            
            # 获取最近1小时发送数
            cursor.execute("""
                SELECT COUNT(*) FROM signal_history 
                WHERE sent_time >= datetime('now', '-1 hour', 'localtime')
            """)
            sent_1h = cursor.fetchone()[0]
            
            # 获取今天发送数
            cursor.execute("""
                SELECT COUNT(*) FROM signal_history 
                WHERE date(sent_time) = date('now', 'localtime')
            """)
            sent_today = cursor.fetchone()[0]
            
            # 获取各类信号统计
            cursor.execute("""
                SELECT signal_type, COUNT(*) as count
                FROM signal_history
                GROUP BY signal_type
            """)
            signal_counts = dict(cursor.fetchall())
            
            # 获取最新发送时间
            cursor.execute("""
                SELECT sent_time FROM signal_history 
                ORDER BY created_at DESC LIMIT 1
            """)
            last_sent = cursor.fetchone()
            last_sent_time = last_sent[0] if last_sent else None
            
            conn.close()
            
            db_stats = {
                'total_sent': total_sent,
                'sent_1h': sent_1h,
                'sent_today': sent_today,
                'signal_counts': signal_counts,
                'last_sent_time': last_sent_time
            }
        
        # 返回扁平化的数据结构，符合前端期待的格式
        return jsonify({
            'success': True,
            'is_running': is_running,
            'pid': pid,
            'status': '运行中' if is_running else '未运行',
            'total_sent': db_stats.get('total_sent', 0),
            'sent_1h': db_stats.get('sent_1h', 0),
            'sent_today': db_stats.get('sent_today', 0),
            'last_sent_time': db_stats.get('last_sent_time'),
            'last_update': db_stats.get('last_sent_time', '未知'),
            'signal_counts': signal_counts,
            'last_messages': [],  # 前端需要的字段
            # 同时保留嵌套格式以兼容其他可能的调用
            'data': {
                'is_running': is_running,
                'pid': pid,
                'database_stats': db_stats
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/telegram/history')
def telegram_history():
    """获取Telegram信号发送历史"""
    try:
        import os
        
        if not os.path.exists('tg_signals.db'):
            return jsonify({
                'success': False,
                'error': '数据库不存在'
            }), 404
        
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 50, type=int)
        signal_type = request.args.get('type', '')
        
        conn = sqlite3.connect('tg_signals.db', timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 构建查询
        where_clause = ""
        params = []
        if signal_type:
            where_clause = "WHERE signal_type = ?"
            params.append(signal_type)
        
        # 获取总数
        cursor.execute(f"SELECT COUNT(*) FROM signal_history {where_clause}", params)
        total = cursor.fetchone()[0]
        
        # 获取分页数据
        offset = (page - 1) * limit
        cursor.execute(f"""
            SELECT id, signal_type, symbol, signal_name, signal_data, sent_time, created_at
            FROM signal_history
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, params + [limit, offset])
        
        records = []
        for row in cursor.fetchall():
            records.append({
                'id': row['id'],
                'signal_type': row['signal_type'],
                'symbol': row['symbol'],
                'signal_name': row['signal_name'],
                'signal_data': row['signal_data'],
                'sent_time': row['sent_time'],
                'created_at': row['created_at']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'records': records,
                'total': total,
                'page': page,
                'limit': limit,
                'pages': (total + limit - 1) // limit
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/coins/realtime-status')
def api_coins_realtime_status():
    """
    获取所有币种的实时状态
    包括：当前价格（来自最新K线）、7天高低点、涨跌幅、交易信号及发生时间
    """
    try:
        import pytz
        conn = sqlite3.connect('crypto_data.db', timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        beijing_tz = pytz.timezone('Asia/Shanghai')
        
        # 定义27个币种
        symbols = [
            'AAVE', 'APT', 'BCH', 'BNB', 'BTC', 'CRV', 'DOGE', 'DOT', 'ETC', 'ETH', 'FIL',
            'HBAR', 'LDO', 'LINK', 'LTC', 'NEAR', 'SOL', 'SUI', 'TAO', 'TON', 'TRX',
            'XLM', 'XRP', 'CFX', 'CRO', 'STX', 'UNI'
        ]
        
        results = []
        
        for symbol_short in symbols:
            symbol = f"{symbol_short}-USDT-SWAP"
            
            # 1. 获取最新K线数据（当前价格）
            cursor.execute('''
                SELECT timestamp, close, open
                FROM okex_kline_ohlc
                WHERE symbol = ? AND timeframe = '5m'
                ORDER BY timestamp DESC
                LIMIT 1
            ''', (symbol,))
            latest_kline = cursor.fetchone()
            
            if not latest_kline:
                continue
            
            current_price = latest_kline['close']
            open_price = latest_kline['open']
            latest_time = datetime.fromtimestamp(latest_kline['timestamp'] / 1000, tz=beijing_tz)
            
            # 计算涨跌幅
            change_pct = ((current_price - open_price) / open_price * 100) if open_price > 0 else 0
            
            # 2. 获取7天高低点
            cursor.execute('''
                SELECT MAX(high) as high_7d, MIN(low) as low_7d
                FROM okex_kline_ohlc
                WHERE symbol = ? AND timeframe = '5m'
                AND timestamp >= ?
            ''', (symbol, int((datetime.now() - timedelta(days=7)).timestamp() * 1000)))
            extremes = cursor.fetchone()
            
            high_7d = extremes['high_7d'] if extremes and extremes['high_7d'] else current_price
            low_7d = extremes['low_7d'] if extremes and extremes['low_7d'] else current_price
            
            # 3. 检查最近2小时的交易信号
            two_hours_ago = datetime.now(beijing_tz) - timedelta(hours=2)
            
            cursor.execute('''
                SELECT record_time, long_signals, short_signals, today_new_high, today_new_low
                FROM trading_signals
                WHERE record_time >= ?
                ORDER BY record_time DESC
                LIMIT 1
            ''', (two_hours_ago.strftime('%Y-%m-%d %H:%M:%S'),))
            signal_row = cursor.fetchone()
            
            signal_type = None
            signal_time = None
            
            if signal_row:
                signal_time_dt = datetime.strptime(signal_row['record_time'], '%Y-%m-%d %H:%M:%S')
                signal_time_dt = beijing_tz.localize(signal_time_dt)
                signal_time = signal_time_dt.strftime('%m-%d %H:%M')
                
                # 判断信号类型
                if signal_row['long_signals'] > 0 or signal_row['today_new_low'] > 0:
                    signal_type = 'buy'
                elif signal_row['short_signals'] > 0 or signal_row['today_new_high'] > 0:
                    signal_type = 'sell'
            
            results.append({
                'symbol': symbol_short,
                'current_price': current_price,
                'high_7d': high_7d,
                'low_7d': low_7d,
                'change_pct': change_pct,
                'signal_type': signal_type,  # 'buy' or 'sell' or None
                'signal_time': signal_time,  # K线时间，格式：'MM-DD HH:MM'
                'latest_update': latest_time.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results),
            'timestamp': datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sell-point-1/save', methods=['POST'])
def api_sell_point_1_save():
    """
    保存卖点1信号到数据库
    
    请求体格式:
    {
        "symbol": "BTC",
        "high_price": 90000.0,
        "high_time": "2025-12-15 14:30:00",
        "high_index": 1000,
        "mark_price": 89500.0,
        "mark_time": "2025-12-15 15:00:00",
        "mark_index": 1006,
        "mark_rsi": 65.5
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400
        
        # 验证必需字段
        required_fields = ['symbol', 'high_price', 'high_time', 'high_index', 
                          'mark_price', 'mark_time', 'mark_index', 'mark_rsi']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必需字段: {field}'
                }), 400
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 检查是否已存在相同的信号（避免重复插入）
        cursor.execute('''
            SELECT id FROM sell_point_1_signals
            WHERE symbol = ? AND mark_time = ? AND is_valid = 1
        ''', (data['symbol'], data['mark_time']))
        
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return jsonify({
                'success': True,
                'message': '信号已存在',
                'signal_id': existing[0]
            })
        
        # 插入新信号
        now = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO sell_point_1_signals (
                symbol, high_price, high_time, high_index,
                mark_price, mark_time, mark_index, mark_rsi,
                signal_generated_at, is_valid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            data['symbol'],
            data['high_price'],
            data['high_time'],
            data['high_index'],
            data['mark_price'],
            data['mark_time'],
            data['mark_index'],
            data['mark_rsi'],
            now
        ))
        
        signal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '卖点1信号保存成功',
            'signal_id': signal_id
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/sell-point-1/latest')
def api_sell_point_1_latest():
    """
    获取最新的卖点1信号
    
    参数:
        - symbol: 币种（可选，如BTC）
        - hours: 时间范围（可选，默认24小时）
    """
    try:
        symbol = request.args.get('symbol')
        hours = int(request.args.get('hours', 24))
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 构建查询
        beijing_tz = pytz.timezone('Asia/Shanghai')
        cutoff_time = (datetime.now(beijing_tz) - timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
        
        if symbol:
            cursor.execute('''
                SELECT * FROM sell_point_1_signals
                WHERE symbol = ? AND mark_time >= ? AND is_valid = 1
                ORDER BY mark_time DESC
            ''', (symbol, cutoff_time))
        else:
            cursor.execute('''
                SELECT * FROM sell_point_1_signals
                WHERE mark_time >= ? AND is_valid = 1
                ORDER BY mark_time DESC
            ''', (cutoff_time,))
        
        rows = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in rows:
            signals.append({
                'id': row['id'],
                'symbol': row['symbol'],
                'high_price': row['high_price'],
                'high_time': row['high_time'],
                'high_index': row['high_index'],
                'mark_price': row['mark_price'],
                'mark_time': row['mark_time'],
                'mark_index': row['mark_index'],
                'mark_rsi': row['mark_rsi'],
                'signal_generated_at': row['signal_generated_at'],
                'created_at': row['created_at']
            })
        
        return jsonify({
            'success': True,
            'data': signals,
            'count': len(signals),
            'timestamp': datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/telegram-dashboard')
def telegram_dashboard():
    """Telegram信号推送系统仪表板"""
    return render_template('telegram_signal_dashboard.html')

@app.route('/cache-help')
def cache_help():
    """缓存清除帮助页面"""
    return render_template('cache_clear_guide.html')

@app.route('/api/telegram/signals/support-resistance')
def api_telegram_support_resistance():
    """获取支撑压力线信号（2小时内）"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        conn = sqlite3.connect('telegram_signals.db')
        cursor = conn.cursor()
        
        # 获取2小时内的信号
        two_hours_ago = (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            SELECT signal_type, symbol, price, signal_time, sent_at
            FROM support_resistance_signals
            WHERE sent_at >= ?
            ORDER BY sent_at DESC
        ''', (two_hours_ago,))
        
        signals = []
        for row in cursor.fetchall():
            signals.append({
                'signal_type': row[0],
                'symbol': row[1],
                'price': row[2],
                'signal_time': row[3],
                'sent_at': row[4]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'signals': signals,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/telegram/signals/count-alerts')
def api_telegram_count_alerts():
    """获取计次预警（2小时内）"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        conn = sqlite3.connect('telegram_signals.db')
        cursor = conn.cursor()
        
        two_hours_ago = (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            SELECT record_time, count_value, threshold, full_data, sent_at
            FROM count_alerts
            WHERE sent_at >= ?
            ORDER BY sent_at DESC
        ''', (two_hours_ago,))
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'record_time': row[0],
                'count_value': row[1],
                'threshold': row[2],
                'full_data': row[3],
                'sent_at': row[4]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/telegram/signals/trading')
def api_telegram_trading():
    """获取交易信号（2小时内）"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        conn = sqlite3.connect('telegram_signals.db')
        cursor = conn.cursor()
        
        two_hours_ago = (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            SELECT signal_type, symbol, price, signal_time, rsi, sent_at
            FROM trading_signals
            WHERE sent_at >= ?
            ORDER BY sent_at DESC
        ''', (two_hours_ago,))
        
        signals = []
        for row in cursor.fetchall():
            signals.append({
                'signal_type': row[0],
                'symbol': row[1],
                'price': row[2],
                'signal_time': row[3],
                'rsi': row[4],
                'sent_at': row[5]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'signals': signals,
            'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/telegram/signals/stats')
def api_telegram_stats():
    """获取发送统计"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        conn = sqlite3.connect('telegram_signals.db')
        cursor = conn.cursor()
        
        # 总发送数
        cursor.execute('SELECT COUNT(*) FROM support_resistance_signals')
        support_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM count_alerts')
        alert_count = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM trading_signals')
        trade_count = cursor.fetchone()[0]
        total = support_count + alert_count + trade_count
        
        # 最近1小时
        one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('SELECT COUNT(*) FROM support_resistance_signals WHERE sent_at >= ?', (one_hour_ago,))
        support_1h = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM count_alerts WHERE sent_at >= ?', (one_hour_ago,))
        alert_1h = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM trading_signals WHERE sent_at >= ?', (one_hour_ago,))
        trade_1h = cursor.fetchone()[0]
        last_hour = support_1h + alert_1h + trade_1h
        
        # 今日发送
        today_start = datetime.now().strftime('%Y-%m-%d 00:00:00')
        cursor.execute('SELECT COUNT(*) FROM support_resistance_signals WHERE sent_at >= ?', (today_start,))
        support_today = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM count_alerts WHERE sent_at >= ?', (today_start,))
        alert_today = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM trading_signals WHERE sent_at >= ?', (today_start,))
        trade_today = cursor.fetchone()[0]
        today = support_today + alert_today + trade_today
        
        # 最后推送时间
        cursor.execute('''
            SELECT MAX(sent_at) FROM (
                SELECT sent_at FROM support_resistance_signals
                UNION ALL
                SELECT sent_at FROM count_alerts
                UNION ALL
                SELECT sent_at FROM trading_signals
            )
        ''')
        last_time = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total': total,
            'last_hour': last_hour,
            'today': today,
            'last_time': last_time
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/telegram/system/status')
def api_telegram_system_status():
    """获取Telegram推送系统状态"""
    try:
        import subprocess
        # 检查进程是否运行
        result = subprocess.run(['pgrep', '-f', 'telegram_signal_system.py'], 
                               capture_output=True, text=True)
        is_running = bool(result.stdout.strip())
        pid = result.stdout.strip() if is_running else None
        
        return jsonify({
            'success': True,
            'running': is_running,
            'pid': pid,
            'message': '系统运行中' if is_running else '系统未运行'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/telegram/start', methods=['POST'])
def api_telegram_start():
    """启动Telegram推送系统"""
    try:
        import subprocess
        result = subprocess.run(['./start_telegram_signal_system.sh'], 
                               capture_output=True, text=True, cwd='/home/user/webapp')
        return jsonify({
            'success': True,
            'message': '系统已启动',
            'output': result.stdout
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/telegram/stop', methods=['POST'])
def api_telegram_stop():
    """停止Telegram推送系统"""
    try:
        import subprocess
        result = subprocess.run(['./stop_telegram_signal_system.sh'], 
                               capture_output=True, text=True, cwd='/home/user/webapp')
        return jsonify({
            'success': True,
            'message': '系统已停止',
            'output': result.stdout
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/query/latest')
def api_query_latest():
    """获取最新查询数据API（用于计次预警）- 使用JSONL数据源"""
    try:
        manager = query_jsonl_manager
        
        # 获取最新快照
        snapshot = manager.get_latest_snapshot()
        
        if not snapshot:
            return jsonify({'success': False, 'error': '暂无数据'})
        
        return jsonify({
            'success': True,
            'data': {
                '运算时间': snapshot.get('snapshot_time'),
                '急涨': snapshot.get('rush_up_total', 0),  # GDrive使用rush_up_total
                '急跌': snapshot.get('rush_down_total', 0),  # GDrive使用rush_down_total
                '差值': snapshot.get('diff', 0),
                '计次': snapshot.get('count', 0),
                '比值': snapshot.get('ratio', 0),
                '状态': snapshot.get('status', ''),
                '本轮急涨': snapshot.get('round_rush_up', 0),
                '本轮急跌': snapshot.get('round_rush_down', 0),
                '比价最低': snapshot.get('price_lowest', 0),
                '比价创新高': snapshot.get('price_newhigh', 0),
                '计次得分': snapshot.get('count_score_display', ''),
                '24h涨≥10%': snapshot.get('rise_24h_count', 0),
                '24h跌≤-10%': snapshot.get('fall_24h_count', 0)
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/support-resistance/export', methods=['POST'])
def api_support_resistance_export():
    """导出支撑阻力位数据"""
    try:
        import subprocess
        import os
        
        script_path = '/home/user/webapp/export_support_resistance_data.py'
        
        if not os.path.exists(script_path):
            return jsonify({
                'success': False,
                'error': '导出脚本不存在'
            })
        
        # 执行导出脚本
        result = subprocess.run(
            ['python3', script_path],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': '导出失败',
                'output': result.stderr
            })
        
        # 从输出中提取导出文件路径
        export_file = None
        for line in result.stdout.split('\n'):
            if '导出文件:' in line:
                export_file = line.split('导出文件:')[-1].strip()
                break
        
        if not export_file or not os.path.exists(export_file):
            return jsonify({
                'success': False,
                'error': '找不到导出文件'
            })
        
        # 获取文件信息
        file_size = os.path.getsize(export_file)
        file_size_mb = file_size / (1024 * 1024)
        filename = os.path.basename(export_file)
        
        return jsonify({
            'success': True,
            'message': '导出成功',
            'file_path': export_file,
            'filename': filename,
            'file_size': file_size,
            'file_size_mb': round(file_size_mb, 2),
            'download_url': f'/api/support-resistance/download/{filename}'
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': '导出超时'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/support-resistance/download/<filename>')
def api_support_resistance_download(filename):
    """下载导出的数据文件"""
    try:
        export_dir = '/home/user/webapp/exports'
        file_path = os.path.join(export_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '文件不存在'
            }), 404
        
        return send_from_directory(export_dir, filename, as_attachment=True)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/support-resistance/import', methods=['POST'])
def api_support_resistance_import():
    """导入支撑阻力位数据"""
    try:
        import subprocess
        import os
        from werkzeug.utils import secure_filename
        
        # 检查是否有上传的文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            })
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': '文件名为空'
            })
        
        # 检查是否清空现有数据
        clear_existing = request.form.get('clear_existing', 'false').lower() == 'true'
        
        # 保存上传的文件
        filename = secure_filename(file.filename)
        upload_dir = '/home/user/webapp/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # 执行导入脚本
        script_path = '/home/user/webapp/import_support_resistance_data.py'
        
        if not os.path.exists(script_path):
            return jsonify({
                'success': False,
                'error': '导入脚本不存在'
            })
        
        # 构建命令
        cmd = ['python3', script_path, file_path]
        if clear_existing:
            cmd.append('--clear')
        
        # 执行导入
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # 删除上传的临时文件
        try:
            os.remove(file_path)
        except:
            pass
        
        if result.returncode != 0:
            return jsonify({
                'success': False,
                'error': '导入失败',
                'output': result.stderr or result.stdout
            })
        
        # 从输出中提取统计信息
        stats = {
            'tables': 0,
            'records': 0
        }
        
        for line in result.stdout.split('\n'):
            if '表数量:' in line:
                try:
                    stats['tables'] = int(line.split(':')[-1].strip())
                except:
                    pass
            elif '总记录数:' in line:
                try:
                    stats['records'] = int(line.split(':')[-1].strip().replace(',', ''))
                except:
                    pass
        
        return jsonify({
            'success': True,
            'message': '导入成功',
            'stats': stats,
            'output': result.stdout
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': '导入超时'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/query/batch-import', methods=['POST'])
def api_query_batch_import():
    """批量导入当天所有TXT文件数据"""
    try:
        import subprocess
        import os
        
        # 执行批量导入脚本
        script_path = '/home/user/webapp/batch_import_daily_txt.py'
        
        if not os.path.exists(script_path):
            return jsonify({
                'success': False,
                'error': '批量导入脚本不存在'
            })
        
        # 使用subprocess运行脚本
        result = subprocess.run(
            ['python3', script_path],
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        # 解析输出结果
        output_lines = result.stdout.split('\n')
        
        # 提取统计信息
        stats = {
            'total': 0,
            'success': 0,
            'exists': 0,
            'invalid': 0,
            'error': 0
        }
        
        for line in output_lines:
            if '总文件数:' in line:
                stats['total'] = int(line.split(':')[-1].strip())
            elif '成功导入:' in line:
                stats['success'] = int(line.split(':')[-1].strip())
            elif '已存在:' in line:
                stats['exists'] = int(line.split(':')[-1].strip())
            elif '无效数据:' in line:
                stats['invalid'] = int(line.split(':')[-1].strip())
            elif '失败:' in line and '❌' in line:
                stats['error'] = int(line.split(':')[-1].strip())
        
        return jsonify({
            'success': True,
            'message': '批量导入完成',
            'stats': stats,
            'output': result.stdout
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': '批量导入超时（超过5分钟）'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/chart-config')
def chart_config():
    """获取K线图配置URL"""
    return jsonify({
        'success': True,
        'chart_base_url': CHART_BASE_URL,
        'example': f"{CHART_BASE_URL}/chart/BTC"
    })

@app.route('/gdrive-config')
def gdrive_config():
    """Google Drive配置管理页面"""
    return render_template('gdrive_config.html')

@app.route('/api/gdrive-config/get')
def gdrive_config_get():
    """获取当前Google Drive配置"""
    try:
        import json
        config_file = '/home/user/webapp/daily_folder_config.json'
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/gdrive-config/update', methods=['POST'])
def gdrive_config_update():
    """更新Google Drive文件夹配置"""
    try:
        import json
        from datetime import datetime
        
        data = request.get_json()
        parent_folder_url = data.get('parent_folder_url', '')
        
        if not parent_folder_url:
            return jsonify({
                'success': False,
                'error': '请提供Google Drive文件夹链接'
            }), 400
        
        # 提取文件夹ID
        import re
        folder_id_match = re.search(r'/folders/([a-zA-Z0-9_-]+)', parent_folder_url)
        if not folder_id_match:
            return jsonify({
                'success': False,
                'error': '无法从链接中提取文件夹ID，请检查链接格式'
            }), 400
        
        root_folder_id = folder_id_match.group(1)
        
        # 读取现有配置
        config_file = '/home/user/webapp/daily_folder_config.json'
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            config = {}
        
        # 更新配置
        beijing_time = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
        
        # 根据日期判断是单数还是双数
        day_of_month = datetime.now(BEIJING_TZ).day
        is_odd_day = day_of_month % 2 == 1
        
        if is_odd_day:
            config['root_folder_odd'] = root_folder_id
        else:
            config['root_folder_even'] = root_folder_id
        
        config['parent_folder_url'] = parent_folder_url
        config['last_manual_update'] = beijing_time
        config['last_updated'] = beijing_time
        config['update_reason'] = f'手动更新{"单数" if is_odd_day else "双数"}日期父文件夹'
        
        # 保存配置
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': f'配置已更新 ({"单数" if is_odd_day else "双数"}日期父文件夹)',
            'config': config
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/gdrive-config/manual-trigger', methods=['POST'])
def gdrive_manual_trigger():
    """手动触发数据采集"""
    try:
        import subprocess
        import os
        
        # 运行gdrive_final_detector.py一次
        script_path = '/home/user/webapp/gdrive_final_detector.py'
        
        if not os.path.exists(script_path):
            return jsonify({
                'success': False,
                'error': f'脚本不存在: {script_path}'
            }), 404
        
        # 在后台运行一次检测
        process = subprocess.Popen(
            ['python3', script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd='/home/user/webapp'
        )
        
        # 等待最多5秒
        try:
            stdout, stderr = process.communicate(timeout=5)
            return jsonify({
                'success': True,
                'message': '手动触发成功，数据采集已开始',
                'output': stdout.decode('utf-8', errors='ignore')[:500]
            })
        except subprocess.TimeoutExpired:
            return jsonify({
                'success': True,
                'message': '手动触发成功，数据采集正在后台运行'
            })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/gdrive-config/latest-data')
def gdrive_latest_data():
    """获取最新数据时间和状态"""
    try:
        import sqlite3
        from datetime import datetime
        
        db_path = '/home/user/webapp/databases/crypto_data.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取最新数据
        cursor.execute("""
            SELECT snapshot_time, rush_up, rush_down, count, status, created_at
            FROM crypto_snapshots
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return jsonify({
                'success': True,
                'has_data': False,
                'message': '暂无数据'
            })
        
        snapshot_time = result[0]
        created_at = result[5]
        
        # 计算延迟（分钟）
        now = datetime.now(BEIJING_TZ)
        try:
            snapshot_dt = datetime.strptime(snapshot_time, '%Y-%m-%d %H:%M:%S')
            snapshot_dt = BEIJING_TZ.localize(snapshot_dt)
        except:
            snapshot_dt = datetime.strptime(snapshot_time, '%Y-%m-%d %H:%M:%S.%f')
            snapshot_dt = BEIJING_TZ.localize(snapshot_dt)
        
        delay_minutes = (now - snapshot_dt).total_seconds() / 60
        
        return jsonify({
            'success': True,
            'has_data': True,
            'data': {
                'snapshot_time': snapshot_time,
                'rush_up': result[1],
                'rush_down': result[2],
                'count': result[3],
                'status': result[4],
                'created_at': created_at,
                'delay_minutes': round(delay_minutes, 1)
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# ==================== SAR斜率系统 API ====================

@app.route('/sar-slope')
def sar_slope_page():
    """SAR斜率系统页面"""
    return render_template('sar_slope.html')

@app.route('/api/sar-slope/latest')
def api_sar_slope_latest():
    """获取所有币种的最新SAR斜率数据 - 从JSONL读取"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from sar_slope_jsonl_manager import SARSlopeJSONLManager
        
        symbol_filter = request.args.get('symbol', '').upper()
        position_filter = request.args.get('position', '')  # bullish/bearish
        
        manager = SARSlopeJSONLManager()
        results = manager.get_all_sar_slopes(position_filter=position_filter)
        
        # 应用symbol过滤
        if symbol_filter:
            results = [r for r in results if symbol_filter in r['symbol']]
        
        # 获取统计信息
        stats = manager.get_position_stats(results)
        
        return jsonify({
            'success': True,
            'data': results,
            'stats': stats,
            'data_source': 'JSONL'
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/sar-slope/latest-jsonl')
def sar_slope_latest_jsonl():
    """从JSONL直接读取最新的SAR斜率数据"""
    try:
        jsonl_file = '/home/user/webapp/data/sar_slope_jsonl/latest_sar_slope.jsonl'
        
        if not os.path.exists(jsonl_file):
            return jsonify({
                'success': False,
                'error': 'SAR斜率JSONL文件不存在',
                'data': []
            })
        
        # 读取所有币种的最新数据
        latest_data = {}
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    symbol = record.get('symbol')
                    if symbol:
                        # 保存最新的记录（后面的会覆盖前面的）
                        latest_data[symbol] = record
                except json.JSONDecodeError:
                    continue
        
        # 转换为列表
        data_list = list(latest_data.values())
        
        # 计算统计信息
        bullish_count = sum(1 for d in data_list if d.get('sar_position') == 'bullish')
        bearish_count = sum(1 for d in data_list if d.get('sar_position') == 'bearish')
        
        # 计算平均持续时间
        durations = [d.get('position_duration', 0) for d in data_list if d.get('position_duration')]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return jsonify({
            'success': True,
            'data': data_list,
            'data_source': 'JSONL',
            'stats': {
                'total_symbols': len(data_list),
                'bullish_count': bullish_count,
                'bearish_count': bearish_count,
                'avg_duration': round(avg_duration, 1)
            }
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/okx-day-change/latest')
def api_okx_day_change_latest():
    """获取OKX 27币种涨跌最新数据 - 使用 Coin Price Tracker 数据"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from coin_price_tracker_adapter import CoinPriceTrackerAdapter
        
        limit = int(request.args.get('limit', 60))  # 默认最近60分钟
        
        # 使用新的适配器替代旧的 OKXTradingJSONLManager
        adapter = CoinPriceTrackerAdapter()
        records = adapter.get_latest_records(limit=limit)
        
        if not records:
            return jsonify({
                'success': True,
                'data': [],
                'message': '暂无数据'
            })
        
        return jsonify({
            'success': True,
            'data': records,
            'count': len(records),
            'data_source': 'CoinPriceTracker'  # 标记数据来源
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/okx-day-change/history')
def api_okx_day_change_history():
    """获取OKX 27币种涨跌历史数据 - 使用 Coin Price Tracker 数据"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from coin_price_tracker_adapter import CoinPriceTrackerAdapter
        from datetime import datetime, timedelta
        
        # 获取时间范围参数
        hours = int(request.args.get('hours', 24))  # 默认24小时
        
        end_time = int(datetime.now().timestamp())
        start_time = end_time - (hours * 3600)
        
        # 使用新的适配器替代旧的 OKXTradingJSONLManager
        adapter = CoinPriceTrackerAdapter()
        records = adapter.get_records_by_time_range(start_time, end_time)
        
        return jsonify({
            'success': True,
            'data': records,
            'count': len(records),
            'hours': hours,
            'data_source': 'CoinPriceTracker'  # 标记数据来源
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/coin-price-tracker/latest')
def api_coin_price_tracker_latest():
    """币价追踪器 - 获取最新N条数据（30分钟间隔）"""
    try:
        # 获取参数
        limit = request.args.get('limit', 48, type=int)  # 默认48条 = 24小时
        
        # 读取JSONL文件
        jsonl_file = '/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl'
        
        if not os.path.exists(jsonl_file):
            return jsonify({
                'success': False,
                'error': '数据文件不存在'
            })
        
        # 读取最后N条记录
        records = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                if line.strip():
                    records.append(json.loads(line))
        
        return jsonify({
            'success': True,
            'count': len(records),
            'data': records
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/coin-price-tracker/history')
def api_coin_price_tracker_history():
    """币价追踪器 - 查询指定时间范围的数据（不指定时间则返回最近7天）"""
    try:
        from datetime import datetime, timedelta
        
        # 获取参数
        start_time = request.args.get('start_time', '')
        end_time = request.args.get('end_time', '')
        days = request.args.get('days', type=int, default=7)  # 默认返回最近7天
        all_data = request.args.get('all', 'false').lower() == 'true'  # 是否返回全部数据
        
        # 读取JSONL文件
        jsonl_file = '/home/user/webapp/data/coin_price_tracker/coin_prices_30min.jsonl'
        
        if not os.path.exists(jsonl_file):
            return jsonify({
                'success': False,
                'error': '数据文件不存在'
            })
        
        # 如果请求全部数据，不做时间过滤
        if all_data:
            records = []
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
            
            return jsonify({
                'success': True,
                'count': len(records),
                'data': records
            })
        
        # 如果没有指定时间范围，计算默认时间范围（最近N天）
        if not start_time and not end_time:
            now = datetime.now()
            end_dt = now
            start_dt = now - timedelta(days=days)
            start_time = start_dt.strftime('%Y-%m-%d 00:00:00')
            end_time = end_dt.strftime('%Y-%m-%d 23:59:59')
        
        records = []
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    collect_time = record.get('collect_time', '')
                    
                    # 过滤时间范围
                    if start_time <= collect_time <= end_time:
                        records.append(record)
        
        response_data = {
            'success': True,
            'count': len(records),
            'data': records,
            'start_time': start_time,
            'end_time': end_time
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/aligned-data/history')
def api_aligned_data_history():
    """获取对齐后的Coin Tracker + Escape Signal数据"""
    try:
        # 获取参数
        start_time = request.args.get('start_time', '')
        end_time = request.args.get('end_time', '')
        limit = request.args.get('limit', type=int)
        
        # 读取对齐数据文件
        aligned_file = '/home/user/webapp/data/aligned_data_30min.jsonl'
        
        if not os.path.exists(aligned_file):
            return jsonify({
                'success': False,
                'error': '对齐数据文件不存在，请先运行 align_data_sources.py'
            })
        
        records = []
        with open(aligned_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    time_str = record.get('time', '')
                    
                    # 时间过滤
                    if start_time and end_time:
                        if start_time <= time_str <= end_time:
                            records.append(record)
                    else:
                        records.append(record)
        
        # 按时间排序
        records.sort(key=lambda x: x['timestamp'])
        
        # 限制数量
        if limit and limit > 0:
            records = records[-limit:]
        
        response_data = {
            'success': True,
            'count': len(records),
            'data': records
        }
        
        if start_time and end_time:
            response_data['start_time'] = start_time
            response_data['end_time'] = end_time
        
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/sar-slope/history/<symbol>')
def api_sar_slope_history(symbol):
    """获取指定币种的SAR斜率历史数据（默认48小时）"""
    try:
        days = int(request.args.get('days', 2))
        limit = int(request.args.get('limit', 600))
        
        # 计算起始时间戳
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                timestamp,
                datetime_beijing,
                sar_value,
                sar_position,
                sar_quadrant,
                position_duration,
                slope_value,
                slope_direction,
                price_open,
                price_close
            FROM sar_slope_data
            WHERE symbol = ? AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (symbol, start_time, limit))
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                'timestamp': row[0],
                'datetime': row[1],
                'sar_value': round(row[2], 6) if row[2] else None,
                'sar_position': row[3],
                'sar_quadrant': row[4],
                'position_duration': row[5],
                'slope_value': round(row[6], 4) if row[6] else None,
                'slope_direction': row[7],
                'price_open': round(row[8], 6) if row[8] else None,
                'price': round(row[9], 6) if row[9] else None
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'days': days,
            'data': results,
            'count': len(results)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/sar-slope/position-changes/<symbol>')
def api_sar_slope_position_changes(symbol):
    """获取指定币种的SAR位置变化历史"""
    try:
        days = int(request.args.get('days', 7))
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 查找位置变化点
        cursor.execute("""
            WITH position_changes AS (
                SELECT 
                    timestamp,
                    datetime_beijing,
                    sar_value,
                    sar_position,
                    position_duration,
                    price_close,
                    LAG(sar_position) OVER (ORDER BY timestamp) as prev_position
                FROM sar_slope_data
                WHERE symbol = ? AND timestamp >= ?
            )
            SELECT 
                timestamp,
                datetime_beijing,
                sar_value,
                sar_position,
                position_duration,
                price_close
            FROM position_changes
            WHERE prev_position IS NULL OR sar_position != prev_position
            ORDER BY timestamp DESC
            LIMIT 100
        """, (symbol, start_time))
        
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            results.append({
                'timestamp': row[0],
                'datetime': row[1],
                'sar_value': round(row[2], 6) if row[2] else None,
                'position': row[3],
                'duration': row[4],
                'price': round(row[5], 6) if row[5] else None
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'days': days,
            'data': results,
            'count': len(results)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/sar-slope/collector-status')
def api_sar_slope_collector_status():
    """获取SAR斜率采集器状态"""
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/crypto_data.db')
        cursor = conn.cursor()
        
        # 获取最新数据时间
        cursor.execute("""
            SELECT MAX(timestamp) FROM sar_slope_data
        """)
        
        latest_timestamp = cursor.fetchone()[0]
        
        if latest_timestamp:
            latest_dt = datetime.utcfromtimestamp(latest_timestamp / 1000)
            latest_dt_beijing = latest_dt.replace(tzinfo=pytz.UTC).astimezone(BEIJING_TZ)
            latest_time = latest_dt_beijing.strftime('%Y-%m-%d %H:%M:%S')
            
            # 计算延迟
            now = datetime.now(BEIJING_TZ)
            delay_minutes = (now - latest_dt_beijing).total_seconds() / 60
        else:
            latest_time = None
            delay_minutes = None
        
        # 获取数据统计
        cursor.execute("""
            SELECT COUNT(*) FROM sar_slope_data
        """)
        total_records = cursor.fetchone()[0]
        
        # 获取各币种数据量
        cursor.execute("""
            SELECT symbol, COUNT(*) as count
            FROM sar_slope_data
            GROUP BY symbol
            ORDER BY count DESC
        """)
        
        symbol_counts = [{'symbol': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'status': {
                'latest_time': latest_time,
                'delay_minutes': round(delay_minutes, 1) if delay_minutes else None,
                'is_delayed': delay_minutes > 10 if delay_minutes else True,
                'total_records': total_records,
                'symbol_counts': symbol_counts
            }
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# ==================== Telegram 配置管理 API ====================

@app.route('/api/telegram/config', methods=['GET', 'POST'])
def telegram_config_api():
    """
    获取或更新 Telegram 配置
    GET: 返回当前配置
    POST: 更新配置
    """
    config_file = 'telegram_config.json'
    
    try:
        if request.method == 'GET':
            # 读取当前配置
            if not os.path.exists(config_file):
                return jsonify({
                    'success': False,
                    'error': '配置文件不存在'
                }), 404
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return jsonify({
                'success': True,
                'config': config
            })
        
        elif request.method == 'POST':
            # 更新配置
            data = request.json
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': '请提供配置数据'
                }), 400
            
            # 读取现有配置
            if not os.path.exists(config_file):
                return jsonify({
                    'success': False,
                    'error': '配置文件不存在'
                }), 404
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 更新信号类型的启用状态
            if 'buy' in data:
                config['signal_types']['buy']['enabled'] = data['buy']
            if 'sell' in data:
                config['signal_types']['sell']['enabled'] = data['sell']
            if 'double_buy' in data:
                config['signal_types']['double_buy']['enabled'] = data['double_buy']
            if 'double_sell' in data:
                config['signal_types']['double_sell']['enabled'] = data['double_sell']
            
            # 备份原配置
            backup_file = f'telegram_config_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 保存新配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return jsonify({
                'success': True,
                'message': '配置已更新',
                'config': config,
                'backup_file': backup_file
            })
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# ==================== 资金监控系统 API ====================

@app.route('/api/fund-monitor/latest', methods=['GET'])
def fund_monitor_latest():
    """获取最新的资金监控数据（所有币种，所有时间周期）"""
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/fund_monitor.db')
        cursor = conn.cursor()
        
        # 获取每个币种、每个时间周期的最新数据
        cursor.execute('''
            SELECT symbol, interval_type, timestamp, collect_time, volume, 
                   avg_3day, deviation_percent, is_abnormal
            FROM fund_monitor_aggregated
            WHERE (symbol, interval_type, timestamp) IN (
                SELECT symbol, interval_type, MAX(timestamp)
                FROM fund_monitor_aggregated
                GROUP BY symbol, interval_type
            )
            ORDER BY symbol, interval_type
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        # 按币种组织数据
        data_by_symbol = {}
        for row in rows:
            symbol = row[0]
            if symbol not in data_by_symbol:
                data_by_symbol[symbol] = {
                    '15min': None,
                    '30min': None,
                    '60min': None
                }
            
            interval_type = row[1]
            data_by_symbol[symbol][interval_type] = {
                'timestamp': row[2],
                'collect_time': row[3],
                'volume': round(row[4], 2),
                'avg_3day': round(row[5], 2) if row[5] is not None else None,
                'deviation_percent': round(row[6], 2) if row[6] is not None else None,
                'is_abnormal': bool(row[7])
            }
        
        return jsonify({
            'success': True,
            'data': data_by_symbol,
            'update_time': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/fund-monitor/history/<symbol>', methods=['GET'])
def fund_monitor_history(symbol):
    """获取指定币种的历史数据"""
    try:
        interval_type = request.args.get('interval', '15min')  # 默认15分钟
        hours = int(request.args.get('hours', 24))  # 默认24小时
        
        conn = sqlite3.connect('/home/user/webapp/databases/fund_monitor.db')
        cursor = conn.cursor()
        
        # 计算时间范围
        end_time = int(datetime.now(BEIJING_TZ).timestamp() * 1000)
        start_time = end_time - (hours * 60 * 60 * 1000)
        
        cursor.execute('''
            SELECT timestamp, collect_time, volume, avg_3day, 
                   deviation_percent, is_abnormal
            FROM fund_monitor_aggregated
            WHERE symbol = ?
            AND interval_type = ?
            AND timestamp >= ?
            ORDER BY timestamp ASC
        ''', (symbol.upper(), interval_type, start_time))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = []
        for row in rows:
            history.append({
                'timestamp': row[0],
                'collect_time': row[1],
                'volume': round(row[2], 2),
                'avg_3day': round(row[3], 2) if row[3] is not None else None,
                'deviation_percent': round(row[4], 2) if row[4] is not None else None,
                'is_abnormal': bool(row[5])
            })
        
        return jsonify({
            'success': True,
            'symbol': symbol.upper(),
            'interval_type': interval_type,
            'hours': hours,
            'data': history
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/fund-monitor/abnormal', methods=['GET'])
def fund_monitor_abnormal():
    """获取当前所有异常数据"""
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/fund_monitor.db')
        cursor = conn.cursor()
        
        # 获取最新异常数据
        cursor.execute('''
            SELECT symbol, interval_type, timestamp, collect_time, 
                   volume, avg_3day, deviation_percent
            FROM fund_monitor_aggregated
            WHERE is_abnormal = 1
            AND (symbol, interval_type, timestamp) IN (
                SELECT symbol, interval_type, MAX(timestamp)
                FROM fund_monitor_aggregated
                WHERE is_abnormal = 1
                GROUP BY symbol, interval_type
            )
            ORDER BY ABS(deviation_percent) DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        abnormal_list = []
        for row in rows:
            abnormal_list.append({
                'symbol': row[0],
                'interval_type': row[1],
                'timestamp': row[2],
                'collect_time': row[3],
                'volume': round(row[4], 2),
                'avg_3day': round(row[5], 2) if row[5] is not None else None,
                'deviation_percent': round(row[6], 2)
            })
        
        return jsonify({
            'success': True,
            'count': len(abnormal_list),
            'data': abnormal_list,
            'update_time': datetime.now(BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/fund-monitor/config', methods=['GET', 'POST'])
def fund_monitor_config():
    """获取或更新资金监控配置"""
    config_file = 'fund_monitor_config.json'
    
    try:
        if request.method == 'GET':
            # 读取配置
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {
                    'threshold_percentage': 20.0,
                    'lookback_days': 3,
                    'collection_interval': 300
                }
            
            return jsonify({
                'success': True,
                'config': config
            })
        
        elif request.method == 'POST':
            # 更新配置
            data = request.json
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': '请提供配置数据'
                }), 400
            
            # 读取现有配置或使用默认值
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {
                    'threshold_percentage': 20.0,
                    'lookback_days': 3,
                    'collection_interval': 300
                }
            
            # 更新配置
            if 'threshold_percentage' in data:
                config['threshold_percentage'] = float(data['threshold_percentage'])
            if 'lookback_days' in data:
                config['lookback_days'] = int(data['lookback_days'])
            if 'collection_interval' in data:
                config['collection_interval'] = int(data['collection_interval'])
            
            # 保存配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return jsonify({
                'success': True,
                'message': '配置已更新',
                'config': config
            })
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/fund-monitor/abnormal-history', methods=['GET'])
def fund_monitor_abnormal_history():
    """查询异常数据历史记录"""
    try:
        # 获取查询参数
        date = request.args.get('date')  # 格式：YYYY-MM-DD
        start_date = request.args.get('start_date')  # 格式：YYYY-MM-DD
        end_date = request.args.get('end_date')  # 格式：YYYY-MM-DD
        symbol = request.args.get('symbol')  # 币种
        interval = request.args.get('interval')  # 时间周期
        severity = request.args.get('severity')  # 严重程度
        deviation_type = request.args.get('type')  # surge或drop
        limit = int(request.args.get('limit', 100))  # 返回记录数
        
        conn = sqlite3.connect('/home/user/webapp/databases/fund_monitor.db')
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if date:
            conditions.append('collect_date = ?')
            params.append(date)
        elif start_date and end_date:
            conditions.append('collect_date BETWEEN ? AND ?')
            params.extend([start_date, end_date])
        elif start_date:
            conditions.append('collect_date >= ?')
            params.append(start_date)
        elif end_date:
            conditions.append('collect_date <= ?')
            params.append(end_date)
        
        if symbol:
            conditions.append('symbol = ?')
            params.append(symbol.upper())
        
        if interval:
            conditions.append('interval_type = ?')
            params.append(interval)
        
        if severity:
            conditions.append('severity = ?')
            params.append(severity)
        
        if deviation_type:
            conditions.append('deviation_type = ?')
            params.append(deviation_type)
        
        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        
        # 执行查询
        query = f'''
            SELECT id, symbol, interval_type, timestamp, collect_time, collect_date,
                   volume, avg_3day, deviation_percent, deviation_type, severity
            FROM fund_monitor_abnormal_history
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        '''
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 格式化结果
        history = []
        for row in rows:
            history.append({
                'id': row[0],
                'symbol': row[1],
                'interval_type': row[2],
                'timestamp': row[3],
                'collect_time': row[4],
                'collect_date': row[5],
                'volume': round(row[6], 2),
                'avg_3day': round(row[7], 2),
                'deviation_percent': round(row[8], 2),
                'deviation_type': row[9],
                'severity': row[10]
            })
        
        # 统计信息
        cursor.execute(f'''
            SELECT COUNT(*) FROM fund_monitor_abnormal_history
            WHERE {where_clause}
        ''', params[:-1])  # 去掉limit参数
        total_count = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_count': total_count,
            'returned_count': len(history),
            'data': history
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/fund-monitor/abnormal-dates', methods=['GET'])
def fund_monitor_abnormal_dates():
    """获取有异常数据的日期列表"""
    try:
        conn = sqlite3.connect('/home/user/webapp/databases/fund_monitor.db')
        cursor = conn.cursor()
        
        # 查询所有有异常数据的日期及其统计
        cursor.execute('''
            SELECT collect_date, 
                   COUNT(*) as count,
                   COUNT(DISTINCT symbol) as affected_coins,
                   AVG(ABS(deviation_percent)) as avg_deviation
            FROM fund_monitor_abnormal_history
            GROUP BY collect_date
            ORDER BY collect_date DESC
        ''')
        
        rows = cursor.fetchall()
        
        dates = []
        for row in rows:
            dates.append({
                'date': row[0],
                'count': row[1],
                'affected_coins': row[2],
                'avg_deviation': round(row[3], 2)
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'dates': dates
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/fund-monitor/abnormal-timeline', methods=['GET'])
def fund_monitor_abnormal_timeline():
    """获取异常数据时间轴（按小时聚合）"""
    try:
        date = request.args.get('date')  # YYYY-MM-DD
        
        if not date:
            return jsonify({
                'success': False,
                'error': '请提供date参数'
            }), 400
        
        conn = sqlite3.connect('/home/user/webapp/databases/fund_monitor.db')
        cursor = conn.cursor()
        
        # 查询指定日期的所有异常数据
        cursor.execute('''
            SELECT symbol, interval_type, collect_time, volume, 
                   avg_3day, deviation_percent, deviation_type, severity
            FROM fund_monitor_abnormal_history
            WHERE collect_date = ?
            ORDER BY collect_time ASC
        ''', (date,))
        
        rows = cursor.fetchall()
        
        # 按小时分组
        timeline = {}
        for row in rows:
            collect_time = row[2]
            hour = collect_time[:13]  # YYYY-MM-DD HH
            
            if hour not in timeline:
                timeline[hour] = []
            
            timeline[hour].append({
                'symbol': row[0],
                'interval_type': row[1],
                'time': collect_time,
                'volume': round(row[3], 2),
                'avg_3day': round(row[4], 2),
                'deviation_percent': round(row[5], 2),
                'deviation_type': row[6],
                'severity': row[7]
            })
        
        # 转换为列表格式
        timeline_list = []
        for hour, events in sorted(timeline.items()):
            timeline_list.append({
                'hour': hour,
                'count': len(events),
                'events': events
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'date': date,
            'timeline': timeline_list
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/fund-monitor', methods=['GET'])
def fund_monitor_page():
    """资金监控系统前端页面"""
    return render_template('fund_monitor.html')

@app.route('/fund-monitor-history', methods=['GET'])
def fund_monitor_history_page():
    """资金监控异常历史查询页面"""
    return render_template('fund_monitor_history.html')

# ==================== SAR斜率系统路由 ====================
@app.route('/sar-slope')
def sar_slope():
    """SAR斜率系统主页面"""
    return render_template('sar_slope.html')

@app.route('/sar-slope/<symbol>')
def sar_slope_detail(symbol):
    """SAR斜率单币详细追踪页面"""
    return render_template('sar_slope_detail.html', symbol=symbol.upper())

@app.route('/api/sar-slope/status')
def sar_slope_status():
    """获取所有币种的SAR状态 - 从JSONL读取"""
    # 检查服务器端缓存
    cache_key = "sar_slope_status:all"
    cached_data = server_cache.get(cache_key, max_age=30)
    if cached_data:
        cached_data['_from_server_cache'] = True
        cached_data['_cache_age'] = int(time.time() - server_cache.timestamps.get(cache_key, 0))
        return jsonify(cached_data)
    
    try:
        import json
        
        # 读取latest_sar_slope.jsonl文件
        latest_file = '/home/user/webapp/data/sar_slope_jsonl/latest_sar_slope.jsonl'
        
        if not os.path.exists(latest_file):
            return jsonify({
                'success': False,
                'error': '数据文件不存在'
            })
        
        status_list = []
        with open(latest_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    
                    # 转换为API期望的格式
                    status_list.append({
                        'symbol': record.get('symbol'),
                        'current_position': record.get('sar_position'),  # bearish/bullish
                        'current_sequence': record.get('position_duration', 0),
                        'last_kline_time': record.get('datetime'),
                        'updated_at': record.get('datetime'),
                        'total_klines': record.get('position_duration', 0)
                    })
        
        result = {
            'success': True,
            'count': len(status_list),
            'data': status_list,
            '_from_server_cache': False
        }
        
        # 缓存30秒
        server_cache.set(cache_key, result)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })
        
        status_list = []
        for jsonl_file in sorted(jsonl_files):
            # 从文件名提取币种符号
            symbol = jsonl_file.split('/')[-1].replace('.jsonl', '')
            
            try:
                manager = SARJSONLManager(symbol)
                latest_status = manager.get_latest_status()
                
                if latest_status:
                    # 获取总记录数
                    all_records = manager.read_records(limit=None)
                    total_klines = len(all_records) if all_records else 0
                    
                    status_list.append({
                        'symbol': symbol,
                        'last_kline_time': latest_status.get('last_update_time', ''),
                        'total_klines': total_klines,
                        'current_position': latest_status.get('current_position', ''),
                        'current_sequence': latest_status.get('current_sequence', 0),
                        'updated_at': latest_status.get('last_update_time', '')
                    })
            except Exception as e:
                # 跳过有问题的文件
                continue
        
        result = {
            'success': True,
            'data': status_list,
            'count': len(status_list)
        }
        
        # 保存到服务器端缓存
        server_cache.set(cache_key, result)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sar-slope/symbol/<symbol>')
def sar_slope_symbol_data(symbol):
    """获取单个币种的详细SAR数据"""
    try:
        limit = request.args.get('limit', 500, type=int)
        
        conn = sqlite3.connect('/home/user/webapp/databases/sar_slope_data.db', timeout=10.0)
        cursor = conn.cursor()
        
        # 获取原始SAR数据
        cursor.execute('''
            SELECT timestamp, kline_time, open_price, high_price, low_price, 
                   close_price, sar_value, position, position_sequence, duration_minutes
            FROM sar_raw_data
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (symbol, limit))
        
        sar_data = []
        for row in cursor.fetchall():
            sar_data.append({
                'timestamp': row[0],
                'kline_time': row[1],
                'open': row[2],
                'high': row[3],
                'low': row[4],
                'close': row[5],
                'sar': row[6],
                'position': row[7],
                'sequence': row[8],
                'duration': row[9]
            })
        
        # 获取变化率数据
        cursor.execute('''
            SELECT sequence_num, prev_sar, current_sar, change_value, 
                   change_percent, kline_time, position
            FROM sar_consecutive_changes
            WHERE symbol = ?
            ORDER BY id DESC
            LIMIT ?
        ''', (symbol, limit))
        
        changes = []
        for row in cursor.fetchall():
            changes.append({
                'sequence': row[0],
                'prev_sar': row[1],
                'current_sar': row[2],
                'change_value': row[3],
                'change_percent': row[4],
                'time': row[5],
                'position': row[6]
            })
        
        # 获取平均值
        cursor.execute('''
            SELECT position, period_type, avg_change_percent, sample_count
            FROM sar_period_averages
            WHERE symbol = ?
        ''', (symbol,))
        
        averages = {}
        for row in cursor.fetchall():
            pos = row[0]
            if pos not in averages:
                averages[pos] = {}
            averages[pos][row[1]] = {
                'avg': row[2],
                'samples': row[3]
            }
        
        # 获取最近异常
        cursor.execute('''
            SELECT position, sequence_num, sar_value, change_percent,
                   deviation_percent, alert_level, is_extreme_point, kline_time
            FROM sar_anomaly_alerts
            WHERE symbol = ?
            ORDER BY created_at DESC
            LIMIT 100
        ''', (symbol,))
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'position': row[0],
                'sequence': row[1],
                'sar': row[2],
                'change_percent': row[3],
                'deviation': row[4],
                'level': row[5],
                'is_extreme': row[6],
                'time': row[7]
            })
        
        # 获取转换点
        cursor.execute('''
            SELECT timestamp, kline_time, from_position, to_position,
                   conversion_sar, conversion_price, previous_duration
            FROM sar_conversion_points
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 50
        ''', (symbol,))
        
        conversions = []
        for row in cursor.fetchall():
            conversions.append({
                'timestamp': row[0],
                'time': row[1],
                'from_position': row[2],
                'to_position': row[3],
                'sar': row[4],
                'price': row[5],
                'prev_duration': row[6]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'symbol': symbol,
            'sar_data': sar_data,
            'changes': changes,
            'averages': averages,
            'alerts': alerts,
            'conversions': conversions
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sar-slope/alerts')
def sar_slope_alerts():
    """获取所有异常告警"""
    try:
        limit = request.args.get('limit', 50, type=int)
        symbol = request.args.get('symbol', None)
        
        conn = sqlite3.connect('/home/user/webapp/databases/sar_slope_data.db', timeout=10.0)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT symbol, position, sequence_num, sar_value,
                       change_percent, deviation_percent, alert_level,
                       is_extreme_point, extreme_type, kline_time
                FROM sar_anomaly_alerts
                WHERE symbol = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (symbol, limit))
        else:
            cursor.execute('''
                SELECT symbol, position, sequence_num, sar_value,
                       change_percent, deviation_percent, alert_level,
                       is_extreme_point, extreme_type, kline_time
                FROM sar_anomaly_alerts
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'symbol': row[0],
                'position': row[1],
                'sequence': row[2],
                'sar': row[3],
                'change_percent': row[4],
                'deviation': row[5],
                'level': row[6],
                'is_extreme': row[7],
                'extreme_type': row[8],
                'time': row[9]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': alerts,
            'count': len(alerts)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sar-slope/conversions')
def sar_slope_conversions():
    """获取多空转换点"""
    try:
        limit = request.args.get('limit', 50, type=int)
        symbol = request.args.get('symbol', None)
        
        conn = sqlite3.connect('/home/user/webapp/databases/sar_slope_data.db', timeout=10.0)
        cursor = conn.cursor()
        
        if symbol:
            cursor.execute('''
                SELECT symbol, timestamp, kline_time, from_position, to_position,
                       conversion_sar, conversion_price, previous_duration
                FROM sar_conversion_points
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (symbol, limit))
        else:
            cursor.execute('''
                SELECT symbol, timestamp, kline_time, from_position, to_position,
                       conversion_sar, conversion_price, previous_duration
                FROM sar_conversion_points
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (limit,))
        
        conversions = []
        for row in cursor.fetchall():
            conversions.append({
                'symbol': row[0],
                'timestamp': row[1],
                'time': row[2],
                'from_position': row[3],
                'to_position': row[4],
                'sar': row[5],
                'price': row[6],
                'prev_duration': row[7]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': conversions,
            'count': len(conversions)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sar-slope/query/<symbol>')
def sar_slope_query_symbol(symbol):
    """
    完整的单币查询接口
    查询参数:
    - start_time: 开始时间 (格式: YYYY-MM-DD HH:MM:SS)
    - end_time: 结束时间 (格式: YYYY-MM-DD HH:MM:SS)
    - limit: 返回数量限制 (默认: 1000)
    - position: 筛选多空状态 (long/short)
    - include_changes: 是否包含变化率 (true/false, 默认: true)
    - include_alerts: 是否包含异常告警 (true/false, 默认: true)
    - include_conversions: 是否包含多空转换 (true/false, 默认: true)
    - include_averages: 是否包含周期平均值 (true/false, 默认: true)
    """
    try:
        # 获取查询参数
        start_time = request.args.get('start_time', None)
        end_time = request.args.get('end_time', None)
        limit = request.args.get('limit', 1000, type=int)
        position = request.args.get('position', None)  # long/short
        
        include_changes = request.args.get('include_changes', 'true').lower() == 'true'
        include_alerts = request.args.get('include_alerts', 'true').lower() == 'true'
        include_conversions = request.args.get('include_conversions', 'true').lower() == 'true'
        include_averages = request.args.get('include_averages', 'true').lower() == 'true'
        
        conn = sqlite3.connect('/home/user/webapp/databases/sar_slope_data.db', timeout=10.0)
        cursor = conn.cursor()
        
        result = {
            'success': True,
            'symbol': symbol.upper(),
            'query_params': {
                'start_time': start_time,
                'end_time': end_time,
                'limit': limit,
                'position': position
            }
        }
        
        # 1. 获取系统状态
        cursor.execute('''
            SELECT last_update_time, last_kline_time, total_klines,
                   current_position, current_sequence, status, updated_at
            FROM system_status
            WHERE symbol = ?
        ''', (symbol.upper(),))
        
        status_row = cursor.fetchone()
        if status_row:
            result['system_status'] = {
                'last_update_time': status_row[0],
                'last_kline_time': status_row[1],
                'total_klines': status_row[2],
                'current_position': status_row[3],
                'current_sequence': status_row[4],
                'status': status_row[5],
                'updated_at': status_row[6]
            }
        else:
            return jsonify({
                'success': False,
                'error': f'Symbol {symbol.upper()} not found in system'
            })
        
        # 2. 构建原始数据查询SQL
        sql_conditions = ["symbol = ?"]
        sql_params = [symbol.upper()]
        
        if start_time:
            # 转换时间字符串为时间戳
            from datetime import datetime
            import pytz
            beijing_tz = pytz.timezone('Asia/Shanghai')
            dt = beijing_tz.localize(datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S'))
            timestamp = int(dt.timestamp() * 1000)
            sql_conditions.append("timestamp >= ?")
            sql_params.append(timestamp)
        
        if end_time:
            from datetime import datetime
            import pytz
            beijing_tz = pytz.timezone('Asia/Shanghai')
            dt = beijing_tz.localize(datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S'))
            timestamp = int(dt.timestamp() * 1000)
            sql_conditions.append("timestamp <= ?")
            sql_params.append(timestamp)
        
        if position:
            sql_conditions.append("position = ?")
            sql_params.append(position)
        
        # 获取原始SAR数据
        cursor.execute(f'''
            SELECT timestamp, kline_time, open_price, high_price, low_price,
                   close_price, sar_value, position, position_sequence, duration_minutes
            FROM sar_raw_data
            WHERE {' AND '.join(sql_conditions)}
            ORDER BY timestamp DESC
            LIMIT ?
        ''', sql_params + [limit])
        
        sar_data = []
        for row in cursor.fetchall():
            sar_data.append({
                'timestamp': row[0],
                'kline_time': row[1],
                'open': row[2],
                'high': row[3],
                'low': row[4],
                'close': row[5],
                'sar': row[6],
                'position': row[7],
                'sequence': row[8],
                'duration': row[9]
            })
        
        result['sar_data'] = {
            'count': len(sar_data),
            'data': sar_data
        }
        
        # 3. 获取变化率数据（如果需要）
        if include_changes:
            change_conditions = ["symbol = ?"]
            change_params = [symbol.upper()]
            
            if position:
                change_conditions.append("position = ?")
                change_params.append(position)
            
            cursor.execute(f'''
                SELECT sequence_num, prev_sar, current_sar, change_value,
                       change_percent, kline_time, position
                FROM sar_consecutive_changes
                WHERE {' AND '.join(change_conditions)}
                ORDER BY id DESC
                LIMIT ?
            ''', change_params + [limit])
            
            changes = []
            for row in cursor.fetchall():
                changes.append({
                    'sequence': row[0],
                    'prev_sar': row[1],
                    'current_sar': row[2],
                    'change_value': row[3],
                    'change_percent': row[4],
                    'time': row[5],
                    'position': row[6]
                })
            
            result['changes'] = {
                'count': len(changes),
                'data': changes
            }
        
        # 4. 获取周期平均值（如果需要）
        if include_averages:
            cursor.execute('''
                SELECT position, period_type, avg_change_percent, 
                       sample_count, calculated_at
                FROM sar_period_averages
                WHERE symbol = ?
                ORDER BY position, period_type
            ''', (symbol.upper(),))
            
            averages = {
                'long': {},
                'short': {}
            }
            
            for row in cursor.fetchall():
                pos = row[0]
                period = row[1]
                averages[pos][period] = {
                    'avg_change_percent': row[2],
                    'sample_count': row[3],
                    'calculated_at': row[4]
                }
            
            result['averages'] = averages
        
        # 5. 获取异常告警（如果需要）
        if include_alerts:
            alert_conditions = ["symbol = ?"]
            alert_params = [symbol.upper()]
            
            if position:
                alert_conditions.append("position = ?")
                alert_params.append(position)
            
            cursor.execute(f'''
                SELECT position, sequence_num, sar_value, change_percent,
                       period_avg, deviation_percent, alert_level,
                       is_extreme_point, extreme_type, kline_time, created_at
                FROM sar_anomaly_alerts
                WHERE {' AND '.join(alert_conditions)}
                ORDER BY created_at DESC
                LIMIT ?
            ''', alert_params + [min(limit, 200)])
            
            alerts = []
            for row in cursor.fetchall():
                alerts.append({
                    'position': row[0],
                    'sequence': row[1],
                    'sar': row[2],
                    'change_percent': row[3],
                    'period_avg': row[4],
                    'deviation': row[5],
                    'level': row[6],
                    'is_extreme': row[7],
                    'extreme_type': row[8],
                    'time': row[9],
                    'created_at': row[10]
                })
            
            result['alerts'] = {
                'count': len(alerts),
                'data': alerts
            }
        
        # 6. 获取多空转换点（如果需要）
        if include_conversions:
            cursor.execute('''
                SELECT timestamp, kline_time, from_position, to_position,
                       conversion_sar, conversion_price, previous_duration, created_at
                FROM sar_conversion_points
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (symbol.upper(), min(limit, 100)))
            
            conversions = []
            for row in cursor.fetchall():
                conversions.append({
                    'timestamp': row[0],
                    'time': row[1],
                    'from_position': row[2],
                    'to_position': row[3],
                    'sar': row[4],
                    'price': row[5],
                    'prev_duration': row[6],
                    'created_at': row[7]
                })
            
            result['conversions'] = {
                'count': len(conversions),
                'data': conversions
            }
        
        # 7. 统计信息
        result['statistics'] = {
            'total_records': len(sar_data),
            'date_range': {
                'earliest': sar_data[-1]['kline_time'] if sar_data else None,
                'latest': sar_data[0]['kline_time'] if sar_data else None
            }
        }
        
        # 计算多空分布
        if sar_data:
            long_count = sum(1 for d in sar_data if d['position'] == 'long')
            short_count = sum(1 for d in sar_data if d['position'] == 'short')
            result['statistics']['position_distribution'] = {
                'long': long_count,
                'short': short_count,
                'long_percent': round(long_count / len(sar_data) * 100, 2),
                'short_percent': round(short_count / len(sar_data) * 100, 2)
            }
        
        conn.close()
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/sar-slope/sequence-compare/<symbol>')
def sar_slope_sequence_compare(symbol):
    """
    序列号对比接口 - 用户需求
    对比当前序列号的变化率与该序列号的历史平均值
    
    例如：当前是空头02→空头03，变化率是0.05%
    查询所有历史上"空头02→空头03"这一步的平均变化率是0.04%
    得出结论：当前比平均值增加了0.01%
    
    参数:
    - position: long/short (可选，不填则返回两个方向)
    - sequence: 序列号 (可选，不填则返回所有序列号)
    """
    try:
        position_filter = request.args.get('position', None)
        sequence_filter = request.args.get('sequence', None, type=int)
        
        conn = sqlite3.connect('/home/user/webapp/databases/sar_slope_data.db', timeout=10.0)
        cursor = conn.cursor()
        
        result = {
            'success': True,
            'symbol': symbol.upper(),
            'comparisons': []
        }
        
        # 获取当前状态
        cursor.execute('''
            SELECT current_position, current_sequence
            FROM system_status
            WHERE symbol = ?
        ''', (symbol.upper(),))
        
        status = cursor.fetchone()
        if not status:
            return jsonify({'success': False, 'error': 'Symbol not found'})
        
        result['current_status'] = {
            'position': status[0],
            'sequence': status[1]
        }
        
        # 获取当前最新的变化率
        cursor.execute('''
            SELECT sequence_num, change_percent, kline_time, position
            FROM sar_consecutive_changes
            WHERE symbol = ?
            ORDER BY id DESC
            LIMIT 50
        ''', (symbol.upper(),))
        
        recent_changes = cursor.fetchall()
        
        # 获取序列号平均值
        cursor.execute('''
            SELECT position, period_type, avg_change_percent, sample_count
            FROM sar_period_averages
            WHERE symbol = ? AND period_type LIKE 'seq_%'
            ORDER BY position, period_type
        ''', (symbol.upper(),))
        
        seq_averages = {}
        for row in cursor.fetchall():
            pos = row[0]
            period = row[1]  # 格式: seq_01, seq_02, seq_03
            seq_num = int(period.split('_')[1])
            
            if pos not in seq_averages:
                seq_averages[pos] = {}
            
            seq_averages[pos][seq_num] = {
                'avg': row[2],
                'samples': row[3]
            }
        
        # 对比分析
        for change in recent_changes:
            seq_num = change[0]
            current_change = change[1]
            kline_time = change[2]
            pos = change[3]
            
            # 过滤条件
            if position_filter and pos != position_filter:
                continue
            if sequence_filter and seq_num != sequence_filter:
                continue
            
            # 获取该序列号的历史平均值
            if pos in seq_averages and seq_num in seq_averages[pos]:
                avg_data = seq_averages[pos][seq_num]
                avg_change = avg_data['avg']
                samples = avg_data['samples']
                
                # 计算差异
                difference = current_change - avg_change
                difference_percent = (difference / avg_change * 100) if avg_change != 0 else 0
                
                # 判断增加还是减小
                trend = 'increase' if difference > 0 else 'decrease' if difference < 0 else 'equal'
                
                result['comparisons'].append({
                    'position': pos,
                    'sequence': seq_num,
                    'time': kline_time,
                    'current_change': round(current_change, 6),
                    'average_change': round(avg_change, 6),
                    'difference': round(difference, 6),
                    'difference_percent': round(difference_percent, 2),
                    'trend': trend,
                    'sample_count': samples,
                    'description': f'{"多头" if pos == "long" else "空头"}{seq_num:02d}→{seq_num+1:02d}'
                })
        
        result['total_comparisons'] = len(result['comparisons'])
        
        conn.close()
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/sar-slope/duration-signal/<symbol>')
def sar_slope_duration_signal(symbol):
    """
    按持续时间段分析信号 - 用户最新需求
    
    对比逻辑：
    - 多头区间：
      * 1天平均 < 3天平均（比值减小）→ 强势多头信号（偏多）
      * 1天平均 > 3天平均（比值增大）→ 加速赶顶信号（偏空）
    - 空头区间：
      * 1天平均 < 3天平均（比值减小）→ 强势空头信号（偏空）
      * 1天平均 > 3天平均（比值增大）→ 加速赶底信号（偏多）
    
    参数:
    - position: long/short (可选，不填则返回两个方向)
    - duration: 持续时间（分钟，可选）
    """
    try:
        position_filter = request.args.get('position', None)
        duration_filter = request.args.get('duration', None, type=int)
        
        conn = sqlite3.connect('/home/user/webapp/databases/sar_slope_data.db', timeout=10.0)
        cursor = conn.cursor()
        
        result = {
            'success': True,
            'symbol': symbol.upper(),
            'signals': []
        }
        
        # 获取当前状态
        cursor.execute('''
            SELECT current_position, current_sequence
            FROM system_status
            WHERE symbol = ?
        ''', (symbol.upper(),))
        
        status = cursor.fetchone()
        if not status:
            return jsonify({'success': False, 'error': 'Symbol not found'})
        
        result['current_status'] = {
            'position': status[0],
            'sequence': status[1]
        }
        
        # 构建查询条件
        conditions = ["symbol = ?", "period_type LIKE 'dur_%'"]
        params = [symbol.upper()]
        
        if position_filter:
            conditions.append("position = ?")
            params.append(position_filter)
        
        # 获取所有 duration 的平均值数据
        cursor.execute(f'''
            SELECT position, period_type, avg_change_percent, sample_count
            FROM sar_period_averages
            WHERE {' AND '.join(conditions)}
            ORDER BY position, period_type
        ''', params)
        
        # 组织数据结构: {position: {duration: {period: avg}}}
        duration_data = {}
        for row in cursor.fetchall():
            pos = row[0]
            period_type = row[1]  # 格式: dur_15_1day
            avg_pct = row[2]
            sample_count = row[3]
            
            # 解析 period_type
            parts = period_type.split('_')
            if len(parts) != 3:
                continue
            
            duration = int(parts[1])
            period = parts[2]  # 1day, 3day, 7day, 15day
            
            # 过滤 duration
            if duration_filter and duration != duration_filter:
                continue
            
            if pos not in duration_data:
                duration_data[pos] = {}
            if duration not in duration_data[pos]:
                duration_data[pos][duration] = {}
            
            duration_data[pos][duration][period] = {
                'avg': avg_pct,
                'samples': sample_count
            }
        
        # 分析每个 position 和 duration 的信号
        for pos in duration_data:
            for duration in sorted(duration_data[pos].keys()):
                periods = duration_data[pos][duration]
                
                # 必须有 1day 和 3day 数据才能对比
                if '1day' not in periods or '3day' not in periods:
                    continue
                
                avg_1day = periods['1day']['avg']
                avg_3day = periods['3day']['avg']
                avg_7day = periods.get('7day', {}).get('avg', None)
                avg_15day = periods.get('15day', {}).get('avg', None)
                
                # 计算比值
                ratio = (avg_1day / avg_3day) if avg_3day != 0 else 1.0
                ratio_change = avg_1day - avg_3day
                ratio_change_percent = ((avg_1day - avg_3day) / avg_3day * 100) if avg_3day != 0 else 0
                
                # 根据用户逻辑判断信号
                if pos == 'long':
                    if avg_1day < avg_3day:  # 比值减小
                        signal_type = 'strong_long'
                        signal_desc = '强势多头'
                        bias = 'bullish'  # 偏多
                        interpretation = '当天平均 < 3天平均，变化率减小，趋势强劲'
                    else:  # 比值增大
                        signal_type = 'top_acceleration'
                        signal_desc = '加速赶顶'
                        bias = 'bearish'  # 偏空
                        interpretation = '当天平均 > 3天平均，变化率增大，可能见顶'
                else:  # short
                    if avg_1day < avg_3day:  # 比值减小
                        signal_type = 'strong_short'
                        signal_desc = '强势空头'
                        bias = 'bearish'  # 偏空
                        interpretation = '当天平均 < 3天平均，变化率减小，趋势强劲'
                    else:  # 比值增大
                        signal_type = 'bottom_acceleration'
                        signal_desc = '加速赶底'
                        bias = 'bullish'  # 偏多
                        interpretation = '当天平均 > 3天平均，变化率增大，可能见底'
                
                signal = {
                    'position': pos,
                    'duration_minutes': duration,
                    'averages': {
                        '1day': round(avg_1day, 6),
                        '3day': round(avg_3day, 6),
                        '7day': round(avg_7day, 6) if avg_7day else None,
                        '15day': round(avg_15day, 6) if avg_15day else None
                    },
                    'comparison': {
                        'ratio': round(ratio, 4),
                        'change': round(ratio_change, 6),
                        'change_percent': round(ratio_change_percent, 2)
                    },
                    'signal': {
                        'type': signal_type,
                        'description': signal_desc,
                        'bias': bias,
                        'interpretation': interpretation
                    },
                    'sample_counts': {
                        '1day': periods['1day']['samples'],
                        '3day': periods['3day']['samples'],
                        '7day': periods.get('7day', {}).get('samples', None),
                        '15day': periods.get('15day', {}).get('samples', None)
                    }
                }
                
                result['signals'].append(signal)
        
        result['total_signals'] = len(result['signals'])
        
        conn.close()
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/sar-slope/transition-analysis/<symbol>')
def sar_slope_transition_analysis(symbol):
    """
    多空转换分析接口 - 用户最新需求
    
    核心逻辑:
    1. 记录每个5分钟的多空转换点（保留16天数据）
    2. 多头关注 sequence_num=2 (01→02，相当于03→02的变化)
    3. 空头关注 sequence_num=2 (01→02，相当于02→03的变化)
    4. 计算 当天/3天/7天/15天 平均值
    5. 对比当前值与平均值的差值百分比
    6. 判断偏多/偏空状态
    
    参数:
    - position: long/short (可选)
    """
    try:
        position_filter = request.args.get('position', None)
        
        conn = sqlite3.connect('/home/user/webapp/databases/sar_slope_data.db', timeout=10.0)
        cursor = conn.cursor()
        
        result = {
            'success': True,
            'symbol': symbol.upper(),
            'analysis': {}
        }
        
        # 获取当前状态
        cursor.execute('''
            SELECT current_position, current_sequence, last_kline_time
            FROM system_status
            WHERE symbol = ?
        ''', (symbol.upper(),))
        
        status = cursor.fetchone()
        if not status:
            return jsonify({'success': False, 'error': 'Symbol not found'})
        
        # 获取当前价格和持续时间
        cursor.execute('''
            SELECT close_price, duration_minutes
            FROM sar_raw_data
            WHERE symbol = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (symbol.upper(),))
        
        price_data = cursor.fetchone()
        current_price = price_data[0] if price_data else None
        current_duration = price_data[1] if price_data else None
        
        result['current_status'] = {
            'position': status[0],
            'sequence': status[1],
            'last_update': status[2],
            'current_price': round(current_price, 2) if current_price else None,
            'duration_minutes': current_duration
        }
        
        # 对每个方向进行分析
        positions = [position_filter] if position_filter else ['long', 'short']
        
        for pos in positions:
            # 获取该方向 sequence_num=2 的所有变化率数据（按时间降序）
            cursor.execute('''
                SELECT change_percent, kline_time, id
                FROM sar_consecutive_changes
                WHERE symbol = ? AND position = ? AND sequence_num = 2
                ORDER BY id DESC
            ''', (symbol.upper(), pos))
            
            changes = cursor.fetchall()
            
            if not changes:
                continue
            
            # 当前最新值
            current_value = changes[0][0]
            current_time = changes[0][1]
            
            # 提取所有变化率（从旧到新）
            all_changes = [c[0] for c in reversed(changes)]
            
            # 计算各周期平均值
            periods = {
                '1day': 288,   # 24小时 * 12个5分钟
                '3day': 864,   # 3 * 24 * 12
                '7day': 2016,  # 7 * 24 * 12
                '15day': 4320  # 15 * 24 * 12
            }
            
            period_averages = {}
            for period_name, period_count in periods.items():
                if len(all_changes) >= period_count:
                    period_changes = all_changes[-period_count:]
                else:
                    period_changes = all_changes
                
                if period_changes:
                    avg = sum(period_changes) / len(period_changes)
                    period_averages[period_name] = {
                        'average': avg,
                        'sample_count': len(period_changes)
                    }
            
            # 对比当前值与各周期平均值
            comparisons = {}
            for period_name, period_data in period_averages.items():
                avg = period_data['average']
                diff = current_value - avg
                diff_percent = (diff / avg * 100) if avg != 0 else 0
                
                # 判断趋势
                if diff > 0:
                    trend = 'increased'  # 增加
                    trend_cn = '增加'
                elif diff < 0:
                    trend = 'decreased'  # 减少
                    trend_cn = '减少'
                else:
                    trend = 'unchanged'
                    trend_cn = '持平'
                
                comparisons[period_name] = {
                    'period_average': round(avg, 6),
                    'current_value': round(current_value, 6),
                    'difference': round(diff, 6),
                    'difference_percent': round(diff_percent, 2),
                    'trend': trend,
                    'trend_cn': trend_cn,
                    'sample_count': period_data['sample_count']
                }
            
            # 综合判断偏多/偏空状态
            # 使用 1天 和 3天 的对比结果
            bias = None
            bias_reason = []
            
            if '1day' in comparisons and '3day' in comparisons:
                day1_diff = comparisons['1day']['difference_percent']
                day3_diff = comparisons['3day']['difference_percent']
                
                # 如果当前值高于平均值，说明变化率在增大
                # 如果当前值低于平均值，说明变化率在减小
                
                if pos == 'long':
                    # 多头区间：变化率增大 → 偏空（可能赶顶）
                    #          变化率减小 → 偏多（趋势稳健）
                    if day1_diff > 0 and day3_diff > 0:
                        bias = 'bearish'
                        bias_cn = '偏空'
                        bias_reason.append('多头变化率增大，可能加速赶顶')
                    elif day1_diff < 0 and day3_diff < 0:
                        bias = 'bullish'
                        bias_cn = '偏多'
                        bias_reason.append('多头变化率减小，趋势稳健')
                    else:
                        bias = 'neutral'
                        bias_cn = '中性'
                        bias_reason.append('多头信号不明确')
                else:  # short
                    # 空头区间：变化率增大 → 偏多（可能赶底）
                    #          变化率减小 → 偏空（趋势稳健）
                    if day1_diff > 0 and day3_diff > 0:
                        bias = 'bullish'
                        bias_cn = '偏多'
                        bias_reason.append('空头变化率增大，可能加速赶底')
                    elif day1_diff < 0 and day3_diff < 0:
                        bias = 'bearish'
                        bias_cn = '偏空'
                        bias_reason.append('空头变化率减小，趋势稳健')
                    else:
                        bias = 'neutral'
                        bias_cn = '中性'
                        bias_reason.append('空头信号不明确')
            
            result['analysis'][pos] = {
                'position': pos,
                'position_cn': '多头' if pos == 'long' else '空头',
                'sequence_info': '01→02 (序列2)',
                'current_value': round(current_value, 6),
                'current_time': current_time,
                'total_samples': len(all_changes),
                'period_comparisons': comparisons,
                'bias': {
                    'type': bias,
                    'type_cn': bias_cn,
                    'reason': bias_reason
                }
            }
        
        conn.close()
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/sar-slope/current-cycle/<symbol>')
def sar_slope_current_cycle_jsonl(symbol):
    """
    获取当前完整周期的所有序列数据 (JSONL版本)
    
    用户需求:
    - 空头01开始显示，一直到空头转多头
    - 多头01开始显示，一直到多头转空头
    - 不显示持续时间字段
    
    返回当前周期从序列01到当前序列的完整数据
    
    Query参数:
    - limit: 最多返回多少条记录，默认500（约1.7天）
    """
    try:
        # 获取limit参数
        limit = request.args.get('limit', 500, type=int)
        
        # 直接调用JSONL API
        result = get_sar_current_cycle(symbol, limit=limit)
        
        if result['success']:
            # 缓存结果
            cache_key = f"sar_slope_current_cycle:{symbol.upper()}:limit{limit}"
            server_cache.set(cache_key, result)
        
        # 添加防缓存头
        response = jsonify(result)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


# ============================================
# SAR偏向趋势API
# ============================================
@app.route('/sar-bias-trend')
def sar_bias_trend_page():
    """SAR偏向趋势图页面"""
    return render_template('sar_bias_trend.html')

@app.route('/api/sar-slope/bias-trend')
def sar_slope_bias_trend():
    """获取SAR偏向趋势数据（12小时分页）"""
    try:
        from datetime import datetime, timezone, timedelta
        import json
        
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        
        conn = sqlite3.connect('/home/user/webapp/databases/sar_slope_data.db', timeout=10.0)
        cursor = conn.cursor()
        
        # 北京时区
        beijing_tz = timezone(timedelta(hours=8))
        
        # 计算时间范围（每页12小时）
        # page=1: 最近12小时
        # page=2: 12-24小时前
        # page=3: 24-36小时前
        hours_end = (page - 1) * 12
        hours_start = page * 12
        
        # 获取指定页的12小时数据（数据库存储的是北京时间，需要+8小时来匹配）
        cursor.execute('''
        SELECT 
            timestamp,
            bullish_count,
            bearish_count,
            total_symbols,
            bullish_symbols,
            bearish_symbols
        FROM sar_bias_trend
        WHERE datetime(timestamp) >= datetime('now', '+8 hours', '-' || ? || ' hours')
          AND datetime(timestamp) < datetime('now', '+8 hours', '-' || ? || ' hours')
        ORDER BY timestamp ASC
        ''', (hours_start, hours_end))
        
        rows = cursor.fetchall()
        
        # 获取总页数（基于所有数据）
        cursor.execute('SELECT MIN(timestamp) FROM sar_bias_trend')
        min_timestamp = cursor.fetchone()[0]
        
        total_pages = 1
        if min_timestamp:
            # 计算最早数据距今的小时数（使用北京时间）
            cursor.execute("SELECT (julianday('now', '+8 hours') - julianday(?)) * 24", (min_timestamp,))
            hours_diff = cursor.fetchone()[0]
            total_pages = max(1, int(hours_diff / 12) + 1)
        
        conn.close()
        
        data = []
        for row in rows:
            # 将时间戳转换为北京时间（如果需要）
            timestamp_str = row[0]
            data.append({
                'timestamp': timestamp_str,
                'bullish_count': row[1],
                'bearish_count': row[2],
                'total_symbols': row[3],
                'bullish_symbols': json.loads(row[4]) if row[4] else [],
                'bearish_symbols': json.loads(row[5]) if row[5] else []
            })
        
        # 获取当前页的时间范围（用于显示）
        time_range = {
            'start': '',
            'end': ''
        }
        if data:
            time_range['start'] = data[0]['timestamp']
            time_range['end'] = data[-1]['timestamp']
        
        return jsonify({
            'success': True,
            'data': data,
            'total': len(data),
            'page': page,
            'total_pages': total_pages,
            'time_range': time_range,
            'has_prev': page < total_pages,
            'has_next': page > 1
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/sar-slope/bias-stats/latest')
def api_sar_bias_stats_latest():
    """获取最新的SAR多空占比统计 - 从JSONL读取"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from panic_jsonl_manager import PanicJSONLManager
        
        manager = PanicJSONLManager()
        latest = manager.get_latest('sar_bias_stats')
        
        if latest:
            return jsonify({
                'success': True,
                'data': {
                    'record_time': latest.get('record_time'),
                    'bullish_over_80_count': latest.get('bullish_over_80_count', 0),
                    'bearish_over_80_count': latest.get('bearish_over_80_count', 0),
                    'bullish_over_80_symbols': latest.get('bullish_over_80_symbols', '').split(',') if latest.get('bullish_over_80_symbols') else [],
                    'bearish_over_80_symbols': latest.get('bearish_over_80_symbols', '').split(',') if latest.get('bearish_over_80_symbols') else [],
                    'total_symbols': latest.get('total_symbols', 0)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': '暂无数据'
            })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/sar-slope/bias-stats/history')
def api_sar_bias_stats_history():
    """获取SAR多空占比统计历史数据 - 从JSONL读取"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from panic_jsonl_manager import PanicJSONLManager
        
        manager = PanicJSONLManager()
        limit = request.args.get('limit', 100, type=int)
        
        records = manager.read_records('sar_bias_stats', limit=limit, reverse=True)
        
        # 格式化数据
        history_data = []
        for record in records:
            history_data.append({
                'record_time': record.get('record_time'),
                'bullish_over_80_count': record.get('bullish_over_80_count', 0),
                'bearish_over_80_count': record.get('bearish_over_80_count', 0),
                'total_symbols': record.get('total_symbols', 0)
            })
        
        return jsonify({
            'success': True,
            'data': history_data,
            'count': len(history_data)
        })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


# ============================================
# 缓存管理API
# ============================================
@app.route('/api/cache/stats')
def cache_stats():
    """获取缓存统计信息"""
    stats = server_cache.get_stats()
    return jsonify({
        'success': True,
        'cache_stats': stats,
        'message': '服务器端缓存统计信息'
    })

@app.route('/api/cache/clear', methods=['POST'])
def cache_clear():
    """清除服务器端缓存"""
    try:
        key = request.json.get('key') if request.json else None
        server_cache.clear(key)
        return jsonify({
            'success': True,
            'message': f'缓存已清除{"（键: " + key + "）" if key else "（全部）"}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# ========== 锚点系统（OKEx持仓监控） ==========

@app.route('/warning-test')
def warning_test():
    """预警模块测试页面"""
    return render_template('warning_test.html')

@app.route('/anchor-system')
def anchor_system():
    """锚点系统主页 - 重定向到实盘"""
    return redirect('/anchor-system-real')

@app.route('/anchor-test')
def anchor_test():
    """Anchor System 诊断页面"""
    from flask import send_file
    return send_file('/home/user/webapp/anchor_test.html')

@app.route('/test-anchor-chart')
def test_anchor_chart():
    """锚点图表测试页面"""
    response = make_response(render_template('test_anchor_chart.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@app.route('/test-anchor-markpoint')
def test_anchor_markpoint():
    """锚点图表标记点测试页面"""
    response = make_response(render_template('test_anchor_markpoint.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@app.route('/anchor-system-real')
def anchor_system_real():
    """实盘锚点系统"""
    import time
    version = int(time.time())  # 使用时间戳作为版本号强制刷新
    response = make_response(render_template('anchor_system_real.html', cache_bust=version))
    # 禁用所有缓存
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    response.headers['ETag'] = f'"{version}"'  # 添加ETag
    response.headers['Last-Modified'] = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
    return response

@app.route('/okx-trading')
def okx_trading():
    """OKX实盘交易系统"""
    response = make_response(render_template('okx_trading.html'))
    # 禁用所有缓存
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/coin-price-tracker')
def coin_price_tracker():
    """27币涨跌幅总和追踪器 - 实时数据"""
    import time
    timestamp = int(time.time())
    response = make_response(render_template('coin_sum_tracker.html', cache_bust=timestamp))
    # 禁用所有缓存
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/coin-tracker-v2')
def coin_price_tracker_v2():
    """27币涨跌幅总和追踪器 - 新版本（绕过缓存）"""
    import time
    timestamp = int(time.time())
    response = make_response(render_template('coin_sum_tracker.html', cache_bust=timestamp))
    # 禁用所有缓存
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/coin-tracker-simple')
def coin_tracker_simple():
    """27币涨跌幅追踪器 - 简化版（完全重写）"""
    response = make_response(render_template('coin_tracker_simple.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/diagnostic')
def diagnostic():
    """系统诊断页面"""
    response = make_response(render_template('diagnostic.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/coin-price-history')
def coin_price_history():
    """27币种历史数据查询 - 实时数据"""
    response = make_response(render_template('coin_price_history.html'))
    # 禁用所有缓存
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/system-status')
def system_status():
    """系统运行状态监控"""
    response = make_response(render_template('system_status.html'))
    # 禁用所有缓存
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/aligned-data-view')
def aligned_data_view():
    """对齐数据可视化 - Coin Tracker + Escape Signal"""
    response = make_response(render_template('aligned_data_view.html'))
    # 禁用所有缓存
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.route('/anchor-system-paper')
def anchor_system_paper():
    """模拟盘锚点系统"""
    response = make_response(render_template('anchor_system_paper.html'))
    # 禁用所有缓存
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response


@app.route('/anchor-system-v2')
def anchor_system_v2():
    """锚点系统主页 v2 (新URL避免缓存)"""
    response = make_response(render_template('anchor_system.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/api/anchor-system/monitors')
def get_anchor_monitors():
    """获取持仓监控记录"""
    try:
        limit = request.args.get('limit', 100, type=int)
        db_path = '/home/user/webapp/databases/anchor_system.db'
        
        conn = sqlite3.connect(db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM anchor_monitors 
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        monitors = []
        for row in rows:
            monitors.append({
                'id': row['id'],
                'timestamp': row['timestamp'],
                'inst_id': row['inst_id'],
                'pos_side': row['pos_side'],
                'pos_size': row['pos_size'],
                'avg_price': row['avg_price'],
                'mark_price': row['mark_price'],
                'upl': row['upl'],
                'upl_ratio': row['upl_ratio'],
                'margin': row['margin'],
                'leverage': row['leverage'],
                'profit_rate': row['profit_rate'],
                'alert_type': row['alert_type'],
                'alert_sent': row['alert_sent']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': monitors,
            'total': len(monitors)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/anchor-system/alerts')
def get_anchor_alerts():
    """获取告警历史"""
    try:
        limit = request.args.get('limit', 50, type=int)
        db_path = '/home/user/webapp/databases/anchor_system.db'
        
        conn = sqlite3.connect(db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM anchor_alerts 
        ORDER BY timestamp DESC 
        LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        alerts = []
        for row in rows:
            alerts.append({
                'id': row['id'],
                'timestamp': row['timestamp'],
                'inst_id': row['inst_id'],
                'pos_side': row['pos_side'],
                'profit_rate': row['profit_rate'],
                'alert_type': row['alert_type'],
                'message': row['message'],
                'sent_status': row['sent_status']
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': alerts,
            'total': len(alerts)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/sub-account/config')
def get_sub_account_config():
    """获取子账户配置"""
    try:
        import json
        import os
        
        config_path = '/home/user/webapp/sub_account_config.json'
        
        # 如果配置文件不存在，返回默认配置
        if not os.path.exists(config_path):
            default_config = {
                'follow_short_loss_enabled': False,
                'follow_long_loss_enabled': False,
                'super_maintain_long_enabled': False,
                'super_maintain_short_enabled': False
            }
            return jsonify({
                'success': True,
                'config': default_config
            })
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/sub-account/config', methods=['POST'])
def update_sub_account_config():
    """更新子账户配置"""
    try:
        import json
        
        config_path = '/home/user/webapp/sub_account_config.json'
        data = request.get_json()
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': '子账户配置已更新'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/okx-trading/account-balance', methods=['POST'])
def get_okx_account_balance():
    """获取OKX账户余额"""
    try:
        import hmac
        import base64
        from datetime import datetime, timezone
        import requests
        
        data = request.get_json()
        api_key = data.get('apiKey', '')
        secret_key = data.get('apiSecret', '')
        passphrase = data.get('passphrase', '')
        
        if not api_key or not secret_key or not passphrase:
            return jsonify({
                'success': False,
                'error': 'API凭证不完整'
            })
        
        # OKX API配置
        base_url = 'https://www.okx.com'
        request_path = '/api/v5/account/balance'
        method = 'GET'
        
        # 生成签名
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        message = timestamp + method + request_path
        mac = hmac.new(
            bytes(secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        signature = base64.b64encode(mac.digest()).decode()
        
        # 请求头
        headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        # 发送请求
        response = requests.get(base_url + request_path, headers=headers, timeout=10)
        result = response.json()
        
        if result.get('code') == '0' and result.get('data'):
            # 获取USDT余额
            balances = result['data']
            usdt_balance = 0.0
            
            for account in balances:
                details = account.get('details', [])
                for detail in details:
                    if detail.get('ccy') == 'USDT':
                        # 可用余额 + 冻结余额
                        available = float(detail.get('availBal', 0))
                        frozen = float(detail.get('frozenBal', 0))
                        usdt_balance += (available + frozen)
            
            return jsonify({
                'success': True,
                'balance': round(usdt_balance, 2),
                'currency': 'USDT',
                'raw_data': result['data']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('msg', '获取余额失败'),
                'code': result.get('code', 'unknown')
            })
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'API请求超时'
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'网络请求失败: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/okx-trading/account-info', methods=['POST'])
def get_okx_account_info():
    """获取OKX账户详细信息（权益、保证金、盈亏等）"""
    try:
        import hmac
        import base64
        from datetime import datetime, timezone
        import requests
        
        data = request.get_json()
        api_key = data.get('apiKey', '')
        secret_key = data.get('apiSecret', '')
        passphrase = data.get('passphrase', '')
        
        if not api_key or not secret_key or not passphrase:
            return jsonify({
                'success': False,
                'error': 'API凭证不完整'
            })
        
        # OKX API配置
        base_url = 'https://www.okx.com'
        request_path = '/api/v5/account/balance'
        method = 'GET'
        
        # 生成签名
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        message = timestamp + method + request_path
        mac = hmac.new(
            bytes(secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        signature = base64.b64encode(mac.digest()).decode()
        
        # 请求头
        headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        # 发送请求
        response = requests.get(base_url + request_path, headers=headers, timeout=10)
        result = response.json()
        
        if result.get('code') == '0' and result.get('data'):
            # 解析账户信息
            account_data = result['data'][0]
            details = account_data.get('details', [])
            
            # 汇总信息
            total_equity = float(account_data.get('totalEq', 0))  # 总权益（美元）
            available_balance = 0.0  # 可用余额
            frozen_balance = 0.0  # 冻结余额
            margin_used = 0.0  # 已用保证金
            unrealized_pnl = 0.0  # 未实现盈亏
            
            # 统计各币种
            for detail in details:
                if detail.get('ccy') == 'USDT':
                    available_balance = float(detail.get('availBal', 0))
                    frozen_balance = float(detail.get('frozenBal', 0))
                    unrealized_pnl = float(detail.get('upl', 0))
            
            # 计算已用保证金（从账户余额API无法直接获取，需要从持仓API获取）
            # 这里先返回基础信息
            
            return jsonify({
                'success': True,
                'data': {
                    'totalEquity': total_equity,  # 总权益（USD）
                    'availableBalance': available_balance,  # 可用余额（USDT）
                    'frozenBalance': frozen_balance,  # 冻结余额（USDT）
                    'usedMargin': margin_used,  # 已用保证金
                    'unrealizedPnl': unrealized_pnl,  # 未实现盈亏
                    'currency': 'USDT'
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('msg', '获取账户信息失败'),
                'code': result.get('code', 'unknown')
            })
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'API请求超时'
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'网络请求失败: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/okx-trading/positions', methods=['POST'])
def get_okx_positions():
    """获取OKX持仓列表"""
    try:
        import hmac
        import base64
        from datetime import datetime, timezone
        import requests
        
        data = request.get_json()
        api_key = data.get('apiKey', '')
        secret_key = data.get('apiSecret', '')
        passphrase = data.get('passphrase', '')
        
        if not api_key or not secret_key or not passphrase:
            return jsonify({
                'success': False,
                'error': 'API凭证不完整'
            })
        
        # OKX API配置
        base_url = 'https://www.okx.com'
        request_path = '/api/v5/account/positions'
        method = 'GET'
        
        # 生成签名
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        message = timestamp + method + request_path
        mac = hmac.new(
            bytes(secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        signature = base64.b64encode(mac.digest()).decode()
        
        # 请求头
        headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        # 发送请求
        response = requests.get(base_url + request_path, headers=headers, timeout=10)
        result = response.json()
        
        if result.get('code') == '0':
            positions_data = result.get('data', [])
            
            # 过滤和格式化持仓数据
            positions = []
            total_margin = 0.0
            total_unrealized_pnl = 0.0
            
            for pos in positions_data:
                pos_size = float(pos.get('pos', 0))
                if pos_size != 0:  # 只返回有持仓的
                    inst_id = pos.get('instId', '')
                    pos_side = pos.get('posSide', '')
                    leverage = float(pos.get('lever', 0))
                    avg_price = float(pos.get('avgPx', 0))
                    mark_price = float(pos.get('markPx', 0))
                    upl = float(pos.get('upl', 0))
                    upl_ratio = float(pos.get('uplRatio', 0))
                    margin = float(pos.get('margin', 0))
                    
                    total_margin += margin
                    total_unrealized_pnl += upl
                    
                    positions.append({
                        'instId': inst_id,
                        'posSide': pos_side,
                        'posSize': abs(pos_size),
                        'leverage': leverage,
                        'avgPrice': avg_price,
                        'markPrice': mark_price,
                        'unrealizedPnl': upl,
                        'unrealizedPnlRatio': upl_ratio * 100,  # 转换为百分比
                        'margin': margin
                    })
            
            return jsonify({
                'success': True,
                'data': positions,
                'summary': {
                    'totalPositions': len(positions),
                    'totalMargin': total_margin,
                    'totalUnrealizedPnl': total_unrealized_pnl
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('msg', '获取持仓失败'),
                'code': result.get('code', 'unknown')
            })
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'API请求超时'
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'网络请求失败: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/okx-trading/logs', methods=['GET'])
def get_okx_trading_logs():
    """获取OKX交易日志"""
    try:
        date_str = request.args.get('date', None)  # YYYYMMDD格式
        limit = int(request.args.get('limit', 100))
        
        logs = okx_trading_logger.get_logs(date_str=date_str, limit=limit)
        
        return jsonify({
            'success': True,
            'count': len(logs),
            'logs': logs
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/okx-trading/favorite-symbols', methods=['GET'])
def get_favorite_symbols():
    """获取常用币列表（全局共享）"""
    try:
        import json
        import os
        
        file_path = 'data/favorite_symbols.jsonl'
        
        # 如果文件不存在，创建默认配置
        if not os.path.exists(file_path):
            default_symbols = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", 
                             "BNB-USDT-SWAP", "XRP-USDT-SWAP", "DOGE-USDT-SWAP"]
            with open(file_path, 'w') as f:
                from datetime import datetime
                json.dump({
                    'symbols': default_symbols,
                    'updated_at': datetime.utcnow().isoformat() + 'Z'
                }, f)
        
        # 读取最后一行
        with open(file_path, 'r') as f:
            lines = f.readlines()
            if lines:
                data = json.loads(lines[-1].strip())
                return jsonify({
                    'success': True,
                    'symbols': data.get('symbols', []),
                    'updated_at': data.get('updated_at', '')
                })
        
        return jsonify({
            'success': True,
            'symbols': [],
            'updated_at': ''
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/okx-trading/favorite-symbols', methods=['POST'])
def update_favorite_symbols():
    """更新常用币列表（全局共享）"""
    try:
        import json
        from datetime import datetime
        
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        file_path = 'data/favorite_symbols.jsonl'
        
        # 追加新的配置到文件
        with open(file_path, 'a') as f:
            json.dump({
                'symbols': symbols,
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            }, f)
            f.write('\n')
        
        return jsonify({
            'success': True,
            'symbols': symbols
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


@app.route('/api/okx-trading/place-order', methods=['POST'])
def place_okx_order():
    """OKX下单接口"""
    try:
        import hmac
        import base64
        from datetime import datetime, timezone
        import requests
        
        data = request.get_json()
        api_key = data.get('apiKey', '')
        secret_key = data.get('apiSecret', '')
        passphrase = data.get('passphrase', '')
        
        # 订单参数
        inst_id = data.get('instId', '')  # 交易对，如 BTC-USDT-SWAP
        side = data.get('side', '')  # buy/sell
        pos_side = data.get('posSide', '')  # long/short
        order_type = data.get('ordType', 'market')  # market/limit
        size = data.get('sz', '')  # USDT金额
        price = data.get('px', '')  # 限价单价格
        leverage = data.get('lever', '10')  # 杠杆倍数，默认10
        
        if not api_key or not secret_key or not passphrase:
            return jsonify({
                'success': False,
                'error': 'API凭证不完整'
            })
        
        if not inst_id or not side or not size:
            return jsonify({
                'success': False,
                'error': '订单参数不完整'
            })
        
        # OKX API配置
        base_url = 'https://www.okx.com'
        
        # 步骤1: 设置杠杆倍数（重要！）
        try:
            set_leverage_path = '/api/v5/account/set-leverage'
            leverage_body = json.dumps({
                'instId': inst_id,
                'lever': str(leverage),
                'mgnMode': 'isolated',  # 逐仓模式
                'posSide': pos_side if pos_side else 'long'
            })
            
            leverage_timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
            leverage_message = leverage_timestamp + 'POST' + set_leverage_path + leverage_body
            leverage_mac = hmac.new(
                bytes(secret_key, encoding='utf8'),
                bytes(leverage_message, encoding='utf-8'),
                digestmod='sha256'
            )
            leverage_signature = base64.b64encode(leverage_mac.digest()).decode()
            
            leverage_headers = {
                'OK-ACCESS-KEY': api_key,
                'OK-ACCESS-SIGN': leverage_signature,
                'OK-ACCESS-TIMESTAMP': leverage_timestamp,
                'OK-ACCESS-PASSPHRASE': passphrase,
                'Content-Type': 'application/json'
            }
            
            leverage_response = requests.post(base_url + set_leverage_path, headers=leverage_headers, data=leverage_body, timeout=10)
            leverage_result = leverage_response.json()
            
            # 杠杆设置失败不一定是致命错误（可能已经设置过）
            if leverage_result.get('code') != '0':
                print(f"设置杠杆失败（可能已设置）: {leverage_result.get('msg')}")
        except Exception as e:
            print(f"设置杠杆异常（继续下单）: {str(e)}")
        
        # 步骤2: 下单
        request_path = '/api/v5/trade/order'
        method = 'POST'
        
        # 将USDT金额转换为合约张数（永续合约，面值为1USD）
        # sz单位：合约永续是币的数量（如BTC数量）
        # 对于USDT计价合约，sz = USDT金额 / 当前价格
        current_price = float(price) if price else None
        
        # 如果没有价格，需要先获取当前市价
        if not current_price:
            try:
                ticker_path = f'/api/v5/market/ticker?instId={inst_id}'
                ticker_response = requests.get(base_url + ticker_path, timeout=5)
                ticker_data = ticker_response.json()
                if ticker_data.get('code') == '0' and ticker_data.get('data'):
                    current_price = float(ticker_data['data'][0].get('last', 0))
            except:
                pass
        
        if not current_price or current_price == 0:
            return jsonify({
                'success': False,
                'error': '无法获取当前价格，请使用限价单并指定价格'
            })
        
        # 用户输入的是合约价值（USDT），不是保证金！
        # 重要：用户输入7.5 USDT，就是想开7.5 USDT的仓位
        # 保证金 = 合约价值 / 杠杆倍数
        
        user_usdt = float(size)  # 用户输入的USDT金额（合约价值）
        leverage_value = float(leverage)  # 杠杆倍数
        
        # 合约价值就是用户输入的金额
        contract_value_usdt = user_usdt
        
        # 🔥 动态获取合约面值（ctVal）- 每张合约代表多少币
        # 不同币种的合约面值不同，必须从 API 获取，不能硬编码！
        coin_per_contract = None
        try:
            instruments_path = f'/api/v5/public/instruments?instType=SWAP&instId={inst_id}'
            instruments_response = requests.get(base_url + instruments_path, timeout=5)
            instruments_data = instruments_response.json()
            
            if instruments_data.get('code') == '0' and instruments_data.get('data'):
                ct_val = instruments_data['data'][0].get('ctVal', '')
                if ct_val:
                    coin_per_contract = float(ct_val)
                    print(f"[合约规格] {inst_id} 每张合约面值: {coin_per_contract} 币")
        except Exception as e:
            print(f"[合约规格] 获取失败，使用回退逻辑: {str(e)}")
        
        # 如果 API 获取失败，使用回退逻辑（保留原有逻辑作为备份）
        if coin_per_contract is None:
            if 'BTC' in inst_id:
                coin_per_contract = 0.01
            elif 'ETH' in inst_id:
                coin_per_contract = 0.1
            elif 'SOL' in inst_id or 'DOGE' in inst_id or 'XRP' in inst_id or 'ADA' in inst_id or 'TRX' in inst_id:
                coin_per_contract = 1.0
            else:
                coin_per_contract = 0.1
            print(f"[合约规格] 使用回退值: {coin_per_contract} 币")
        
        # 每张合约的USDT价值 = 每张合约的币数量 * 当前币价
        usdt_per_contract = coin_per_contract * current_price
        
        # 需要的合约张数 = 合约价值 / 每张合约价值
        contracts_count = contract_value_usdt / usdt_per_contract
        
        # OKX要求sz必须是整数张数，四舍五入
        contracts_count = max(1, round(contracts_count))
        contracts_str = str(int(contracts_count))
        
        # 计算实际使用的USDT金额
        actual_contract_value = contracts_count * usdt_per_contract
        actual_margin_used = actual_contract_value / leverage_value
        
        print(f"[下单计算] 用户输入合约价值: {user_usdt} USDT")
        print(f"[下单计算] 杠杆倍数: {leverage_value}x")
        print(f"[下单计算] 每张合约: {coin_per_contract} 币 = {usdt_per_contract:.4f} USDT")
        print(f"[下单计算] 所需张数: {contracts_count} 张")
        print(f"[下单计算] 实际合约价值: {actual_contract_value:.4f} USDT")
        print(f"[下单计算] 实际占用保证金: {actual_margin_used:.4f} USDT")
        
        # 构建请求体
        order_params = {
            'instId': inst_id,
            'tdMode': 'isolated',  # 逐仓模式（只使用指定的保证金，不会占用全部余额）
            'side': side,
            'ordType': order_type,
            'sz': contracts_str  # 合约张数（币的数量）
        }
        
        # 合约需要指定持仓方向
        if pos_side:
            order_params['posSide'] = pos_side
        
        # 限价单需要价格
        if order_type == 'limit' and price:
            order_params['px'] = str(price)
        
        body = json.dumps(order_params)
        
        # 生成签名
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        signature = base64.b64encode(mac.digest()).decode()
        
        # 请求头
        headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        # 发送请求
        response = requests.post(base_url + request_path, headers=headers, data=body, timeout=10)
        result = response.json()
        
        # 记录详细日志
        print(f"[OKX下单] 请求参数: {order_params}")
        print(f"[OKX下单] 响应结果: {result}")
        
        if result.get('code') == '0':
            order_data = result.get('data', [])
            if order_data:
                order = order_data[0]
                
                # 记录成功日志
                okx_trading_logger.log(
                    action='open_position',
                    account_id='user_account',  # 可以从前端传入
                    details={
                        'instId': inst_id,
                        'side': side,
                        'posSide': pos_side,
                        'ordType': order_type,
                        'contracts': contracts_str,
                        'inputUsdt': user_usdt,
                        'leverage': leverage_value,
                        'price': current_price
                    },
                    result={
                        'status': 'success',
                        'ordId': order.get('ordId', ''),
                        'actualUsdt': round(actual_margin_used, 2),
                        'contractValue': round(actual_contract_value, 2)
                    }
                )
                
                return jsonify({
                    'success': True,
                    'data': {
                        'ordId': order.get('ordId', ''),
                        'clOrdId': order.get('clOrdId', ''),
                        'sCode': order.get('sCode', '0'),
                        'sMsg': order.get('sMsg', '订单提交成功'),
                        'contracts': contracts_str,
                        'inputUsdt': user_usdt,  # 用户输入的开仓金额
                        'actualUsdt': round(actual_margin_used, 2),  # 实际占用的保证金
                        'contractValue': round(actual_contract_value, 2),  # 实际合约价值
                        'leverage': leverage_value,  # 杠杆倍数
                        'price': current_price
                    },
                    'message': f'下单成功！开仓 {round(actual_contract_value, 2)} USDT，占用保证金 {round(actual_margin_used, 2)} USDT（{leverage_value}x杠杆）'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '订单响应数据为空'
                })
        else:
            # 记录失败日志
            error_msg = result.get('msg', '下单失败')
            error_code = result.get('code', 'unknown')
            
            okx_trading_logger.log(
                action='open_position',
                account_id='user_account',
                details={
                    'instId': inst_id,
                    'side': side,
                    'posSide': pos_side,
                    'ordType': order_type,
                    'contracts': contracts_str,
                    'inputUsdt': user_usdt,
                    'leverage': leverage_value
                },
                result={
                    'status': 'failed',
                    'error': error_msg,
                    'code': error_code
                }
            )
            
            # 返回更详细的错误信息
            error_msg = result.get('msg', '下单失败')
            error_code = result.get('code', 'unknown')
            
            # 常见错误代码解释
            error_hints = {
                '1': '操作失败，请检查API权限、账户状态和订单参数',
                '50004': 'API Key无效',
                '50005': 'API签名错误',
                '50006': 'API Passphrase错误',
                '50007': 'API权限不足',
                '50011': '余额不足',
                '51000': '参数错误',
                '51001': '交易对不存在或已下架',
                '51008': '订单数量太小',
                '51009': '订单数量太大',
                '51010': '订单金额太小',
                '51020': '账户状态异常',
            }
            
            hint = error_hints.get(error_code, '')
            full_error = f"{error_msg} (代码:{error_code})"
            if hint:
                full_error += f"\n提示: {hint}"
            
            return jsonify({
                'success': False,
                'error': full_error,
                'code': error_code,
                'details': {
                    'instId': inst_id,
                    'contracts': contracts_str,
                    'usdtAmount': size,
                    'price': current_price
                }
            })
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'API请求超时'
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'网络请求失败: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/okx-trading/market-tickers', methods=['GET'])
def get_okx_market_tickers():
    """获取OKX市场行情数据"""
    try:
        import requests
        
        # 获取所有SWAP合约的行情
        base_url = 'https://www.okx.com'
        ticker_path = '/api/v5/market/tickers?instType=SWAP'
        
        response = requests.get(base_url + ticker_path, timeout=10)
        result = response.json()
        
        if result.get('code') == '0':
            tickers_data = result.get('data', [])
            
            # 指定要显示的27个币种
            allowed_symbols = [
                'BTC', 'ETH', 'XRP', 'BNB', 'SOL', 'LTC', 'DOGE', 'SUI', 'TRX',
                'TON', 'ETC', 'BCH', 'HBAR', 'XLM', 'FIL', 'LINK', 'CRO', 'DOT',
                'AAVE', 'UNI', 'NEAR', 'APT', 'CFX', 'CRV', 'STX', 'LDO', 'TAO'
            ]
            
            # 只返回指定的USDT-SWAP交易对
            usdt_tickers = []
            for ticker in tickers_data:
                inst_id = ticker.get('instId', '')
                if 'USDT-SWAP' in inst_id:
                    # 提取币种名称
                    symbol = inst_id.replace('-USDT-SWAP', '')
                    
                    # 只处理允许的币种
                    if symbol not in allowed_symbols:
                        continue
                    
                    # 计算UTC+8 0点开始的涨跌幅
                    current_price = float(ticker.get('last', 0))
                    open_price_utc8 = float(ticker.get('sodUtc8', 0))  # UTC+8 0点（北京时间0点）的开盘价
                    
                    # 计算涨跌幅百分比
                    if open_price_utc8 > 0:
                        change_percent = ((current_price - open_price_utc8) / open_price_utc8) * 100
                    else:
                        change_percent = 0
                    
                    usdt_tickers.append({
                        'symbol': inst_id,
                        'name': symbol,
                        'price': current_price,
                        'change24h': round(change_percent, 2),  # 24h涨跌幅（UTC+8 0点开始）
                        'high24h': float(ticker.get('high24h', 0)),
                        'low24h': float(ticker.get('low24h', 0)),
                        'vol24h': float(ticker.get('vol24h', 0)),
                        'volCcy24h': float(ticker.get('volCcy24h', 0)),
                        'timestamp': ticker.get('ts', '')
                    })
            
            # 按照指定顺序排序
            sorted_tickers = []
            for symbol in allowed_symbols:
                ticker = next((t for t in usdt_tickers if t['name'] == symbol), None)
                if ticker:
                    sorted_tickers.append(ticker)
            
            return jsonify({
                'success': True,
                'data': sorted_tickers,
                'count': len(sorted_tickers)
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('msg', '获取行情失败')
            })
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'API请求超时'
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'网络请求失败: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/okx-trading/pending-orders', methods=['POST'])
def get_okx_pending_orders():
    """获取当前委托（未成交订单）"""
    try:
        import hmac
        import base64
        from datetime import datetime, timezone
        import requests
        
        data = request.get_json()
        api_key = data.get('apiKey', '')
        secret_key = data.get('apiSecret', '')
        passphrase = data.get('passphrase', '')
        
        if not api_key or not secret_key or not passphrase:
            return jsonify({
                'success': False,
                'error': 'API凭证不完整'
            })
        
        # OKX API配置
        base_url = 'https://www.okx.com'
        request_path = '/api/v5/trade/orders-pending?instType=SWAP'
        method = 'GET'
        
        # 生成签名
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        message = timestamp + method + request_path
        mac = hmac.new(
            bytes(secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        signature = base64.b64encode(mac.digest()).decode()
        
        # 请求头
        headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        # 发送请求
        response = requests.get(base_url + request_path, headers=headers, timeout=10)
        result = response.json()
        
        if result.get('code') == '0':
            orders_data = result.get('data', [])
            
            # 格式化订单数据
            orders = []
            for order in orders_data:
                orders.append({
                    'ordId': order.get('ordId'),
                    'instId': order.get('instId'),
                    'side': order.get('side'),  # buy/sell
                    'posSide': order.get('posSide'),  # long/short
                    'ordType': order.get('ordType'),  # market/limit
                    'px': order.get('px', ''),  # 委托价格
                    'sz': order.get('sz'),  # 委托数量
                    'fillSz': order.get('fillSz', '0'),  # 已成交数量
                    'avgPx': order.get('avgPx', '0'),  # 成交均价
                    'state': order.get('state'),  # live/partially_filled
                    'cTime': order.get('cTime'),  # 创建时间
                    'uTime': order.get('uTime')  # 更新时间
                })
            
            return jsonify({
                'success': True,
                'data': orders,
                'count': len(orders)
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('msg', '获取委托失败'),
                'code': result.get('code', '')
            })
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'API请求超时'
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'网络请求失败: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/okx-trading/cancel-order', methods=['POST'])
def cancel_okx_order():
    """撤销订单"""
    try:
        import hmac
        import base64
        from datetime import datetime, timezone
        import requests
        
        data = request.get_json()
        api_key = data.get('apiKey', '')
        secret_key = data.get('apiSecret', '')
        passphrase = data.get('passphrase', '')
        order_id = data.get('ordId', '')
        inst_id = data.get('instId', '')
        
        if not api_key or not secret_key or not passphrase:
            return jsonify({
                'success': False,
                'error': 'API凭证不完整'
            })
        
        if not order_id or not inst_id:
            return jsonify({
                'success': False,
                'error': '订单ID或交易对不能为空'
            })
        
        # OKX API配置
        base_url = 'https://www.okx.com'
        request_path = '/api/v5/trade/cancel-order'
        method = 'POST'
        
        # 构建请求体
        order_params = {
            'instId': inst_id,
            'ordId': order_id
        }
        
        body = json.dumps(order_params)
        
        # 生成签名
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        signature = base64.b64encode(mac.digest()).decode()
        
        # 请求头
        headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        # 发送请求
        response = requests.post(base_url + request_path, headers=headers, data=body, timeout=10)
        result = response.json()
        
        print(f"[OKX撤单] 请求参数: {order_params}")
        print(f"[OKX撤单] 响应结果: {result}")
        
        if result.get('code') == '0':
            # 记录撤单成功日志
            okx_trading_logger.log(
                action='cancel_order',
                account_id='user_account',
                details={
                    'instId': inst_id,
                    'ordId': ord_id
                },
                result={
                    'status': 'success'
                }
            )
            
            return jsonify({
                'success': True,
                'message': '撤单成功'
            })
        else:
            # 记录撤单失败日志
            okx_trading_logger.log(
                action='cancel_order',
                account_id='user_account',
                details={
                    'instId': inst_id,
                    'ordId': ord_id
                },
                result={
                    'status': 'failed',
                    'error': result.get('msg', '撤单失败'),
                    'code': result.get('code', '')
                }
            )
            
            return jsonify({
                'success': False,
                'error': result.get('msg', '撤单失败'),
                'code': result.get('code', '')
            })
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'API请求超时'
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'网络请求失败: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/okx-trading/order-detail', methods=['POST'])
def get_okx_order_detail():
    """查询OKX订单详情"""
    try:
        import hmac
        import base64
        from datetime import datetime, timezone
        import requests
        
        data = request.get_json()
        api_key = data.get('apiKey', '')
        secret_key = data.get('apiSecret', '')
        passphrase = data.get('passphrase', '')
        order_id = data.get('ordId', '')
        inst_id = data.get('instId', '')
        
        if not api_key or not secret_key or not passphrase:
            return jsonify({
                'success': False,
                'error': 'API凭证不完整'
            })
        
        if not order_id or not inst_id:
            return jsonify({
                'success': False,
                'error': '订单ID或交易对不能为空'
            })
        
        # OKX API配置
        base_url = 'https://www.okx.com'
        request_path = f'/api/v5/trade/order?instId={inst_id}&ordId={order_id}'
        method = 'GET'
        
        # 生成签名
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        message = timestamp + method + request_path
        mac = hmac.new(
            bytes(secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        signature = base64.b64encode(mac.digest()).decode()
        
        # 请求头
        headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        # 发送请求
        response = requests.get(base_url + request_path, headers=headers, timeout=10)
        result = response.json()
        
        print(f"[OKX订单查询] 订单ID: {order_id}, 响应: {result}")
        
        if result.get('code') == '0':
            order_data = result.get('data', [])
            if order_data:
                order = order_data[0]
                
                # 订单状态映射
                state_map = {
                    'live': '等待成交',
                    'partially_filled': '部分成交',
                    'filled': '完全成交',
                    'canceled': '已撤销',
                    'mmp_canceled': '做市商保护撤单',
                    'partially_canceled': '部分成交已撤销'
                }
                
                state = order.get('state', '')
                state_text = state_map.get(state, state)
                
                return jsonify({
                    'success': True,
                    'data': {
                        'ordId': order.get('ordId'),
                        'instId': order.get('instId'),
                        'state': state,
                        'stateText': state_text,
                        'px': order.get('px', ''),  # 委托价格
                        'sz': order.get('sz', ''),  # 委托数量
                        'fillSz': order.get('fillSz', '0'),  # 成交数量
                        'avgPx': order.get('avgPx', '0'),  # 成交均价
                        'side': order.get('side', ''),  # buy/sell
                        'posSide': order.get('posSide', ''),  # long/short
                        'ordType': order.get('ordType', ''),  # market/limit
                        'fee': order.get('fee', '0'),  # 手续费
                        'rebate': order.get('rebate', '0'),  # 返佣
                        'pnl': order.get('pnl', '0'),  # 收益
                        'uTime': order.get('uTime', ''),  # 更新时间
                        'cTime': order.get('cTime', ''),  # 创建时间
                        'cancelSource': order.get('cancelSource', ''),  # 撤单来源
                        'code': order.get('code', ''),  # 错误码
                        'msg': order.get('msg', '')  # 错误信息
                    }
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '订单不存在或已过期'
                })
        else:
            return jsonify({
                'success': False,
                'error': result.get('msg', '查询失败'),
                'code': result.get('code', '')
            })
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'API请求超时'
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'网络请求失败: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/okx-trading/close-position', methods=['POST'])
def close_okx_position():
    """平仓接口 - 支持全部平仓或部分平仓"""
    try:
        import hmac
        import base64
        from datetime import datetime, timezone
        import requests
        
        data = request.get_json()
        api_key = data.get('apiKey', '')
        secret_key = data.get('apiSecret', '')
        passphrase = data.get('passphrase', '')
        inst_id = data.get('instId', '')
        pos_side = data.get('posSide', '')  # long/short
        close_size = data.get('closeSize', None)  # 平仓数量（张数），None=全部平仓
        
        if not api_key or not secret_key or not passphrase:
            return jsonify({
                'success': False,
                'error': 'API凭证不完整'
            })
        
        if not inst_id or not pos_side:
            return jsonify({
                'success': False,
                'error': '交易对和持仓方向不能为空'
            })
        
        # OKX API配置
        base_url = 'https://www.okx.com'
        method = 'POST'
        
        # 判断是全部平仓还是部分平仓
        if close_size is None or close_size == 0:
            # 全部平仓：使用 close-position 接口
            request_path = '/api/v5/trade/close-position'
            order_params = {
                'instId': inst_id,
                'posSide': pos_side,
                'mgnMode': 'isolated'  # 逐仓模式
            }
            print(f"[OKX平仓] 全部平仓: {inst_id} {pos_side}")
        else:
            # 部分平仓：使用下单接口，通过反向开仓来平仓
            request_path = '/api/v5/trade/order'
            
            # 平多单 -> sell，平空单 -> buy
            side = 'sell' if pos_side == 'long' else 'buy'
            
            order_params = {
                'instId': inst_id,
                'tdMode': 'isolated',
                'side': side,
                'posSide': pos_side,
                'ordType': 'market',  # 市价单
                'sz': str(int(close_size)),  # 平仓数量（张数）
                'reduceOnly': 'true'  # 只减仓，不开新仓
            }
            print(f"[OKX平仓] 部分平仓: {inst_id} {pos_side} {close_size}张")
        
        body = json.dumps(order_params)
        
        # 生成签名
        timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        signature = base64.b64encode(mac.digest()).decode()
        
        # 请求头
        headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': signature,
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        # 发送请求
        response = requests.post(base_url + request_path, headers=headers, data=body, timeout=10)
        result = response.json()
        
        print(f"[OKX平仓] 请求参数: {order_params}")
        print(f"[OKX平仓] 响应结果: {result}")
        
        if result.get('code') == '0':
            # 记录平仓成功日志
            okx_trading_logger.log(
                action='close_position',
                account_id='user_account',
                details={
                    'instId': inst_id,
                    'posSide': pos_side,
                    'closeSize': close_size,
                    'closeType': 'full' if close_size is None else 'partial'
                },
                result={
                    'status': 'success'
                }
            )
            
            return jsonify({
                'success': True,
                'message': '平仓成功'
            })
        else:
            # 记录平仓失败日志
            okx_trading_logger.log(
                action='close_position',
                account_id='user_account',
                details={
                    'instId': inst_id,
                    'posSide': pos_side,
                    'closeSize': close_size
                },
                result={
                    'status': 'failed',
                    'error': result.get('msg', '平仓失败'),
                    'code': result.get('code', '')
                }
            )
            
            return jsonify({
                'success': False,
                'error': result.get('msg', '平仓失败'),
                'code': result.get('code', '')
            })
            
    except requests.exceptions.Timeout:
        return jsonify({
            'success': False,
            'error': 'API请求超时'
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'网络请求失败: {str(e)}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/anchor-system/auto-maintenance-config')
def get_auto_maintenance_config():
    """获取自动维护配置"""
    try:
        import json
        import os
        
        config_path = '/home/user/webapp/auto_maintenance_config.json'
        
        # 如果配置文件不存在，返回默认配置
        if not os.path.exists(config_path):
            default_config = {
                'auto_maintain_long_enabled': False,
                'auto_maintain_short_enabled': False,
                'super_maintain_long_enabled': False,
                'super_maintain_short_enabled': False
            }
            return jsonify({
                'success': True,
                'config': default_config
            })
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/anchor-system/auto-maintenance-config', methods=['POST'])
def update_auto_maintenance_config():
    """更新自动维护配置"""
    try:
        import json
        
        config_path = '/home/user/webapp/auto_maintenance_config.json'
        data = request.get_json()
        
        # 保存配置
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            'success': True,
            'message': '自动维护配置已更新'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/anchor-system/status')
def get_anchor_status():
    """获取系统状态"""
    try:
        import json
        
        # 读取配置
        config_path = '/home/user/webapp/anchor_config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 获取最新监控记录
        db_path = '/home/user/webapp/databases/anchor_system.db'
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM anchor_monitors')
        total_monitors = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM anchor_alerts')
        total_alerts = cursor.fetchone()[0]
        
        cursor.execute('''
        SELECT * FROM anchor_monitors 
        ORDER BY timestamp DESC 
        LIMIT 1
        ''')
        latest = cursor.fetchone()
        
        conn.close()
        
        # 使用默认配置值（因为 anchor_config.json 没有 monitor 键）
        return jsonify({
            'success': True,
            'status': {
                'total_monitors': total_monitors,
                'total_alerts': total_alerts,
                'latest_check': latest[1] if latest else None,
                'config': {
                    'profit_target': 40.0,  # 默认盈利目标 40%
                    'loss_limit': -10.0,     # 默认止损限制 -10%
                    'check_interval': 30,    # 默认检查间隔 30秒
                    'only_short': False      # 默认支持多空
                }
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/anchor-system/profit-records')
def get_anchor_profit_records():
    """获取历史极值记录 - 使用JSONL存储，实盘和模拟盘使用不同的文件"""
    try:
        inst_id = request.args.get('inst_id')
        pos_side = request.args.get('pos_side')
        trade_mode = request.args.get('trade_mode', 'real')  # 默认实盘
        
        # 创建JSONL管理器
        manager = ExtremeJSONLManager(trade_mode=trade_mode)
        
        if inst_id or pos_side:
            # 查询特定币种/方向的记录
            all_records = manager.get_all_records()
            filtered_records = []
            for r in all_records:
                # 根据提供的参数进行过滤
                if inst_id and r.get('inst_id') != inst_id:
                    continue
                if pos_side and r.get('pos_side') != pos_side:
                    continue
                filtered_records.append(r)
            
            # 按 inst_id, pos_side, record_type 排序
            filtered_records.sort(key=lambda x: (
                x.get('inst_id', ''),
                x.get('pos_side', ''),
                x.get('record_type', '')
            ))
            
            records = []
            for r in filtered_records:
                records.append({
                    'inst_id': r.get('inst_id'),
                    'pos_side': r.get('pos_side'),
                    'record_type': r.get('record_type'),
                    'profit_rate': r.get('profit_rate'),
                    'timestamp': r.get('timestamp'),
                    'pos_size': r.get('pos_size'),
                    'avg_price': r.get('avg_price'),
                    'mark_price': r.get('mark_price'),
                    'upl': r.get('upl'),
                    'margin': r.get('margin'),
                    'leverage': r.get('leverage')
                })
        else:
            # 查询所有记录
            all_records = manager.get_all_records()
            
            # 只保留每个(inst_id, pos_side, record_type)组合的最新记录
            latest_records = {}
            for r in all_records:
                key = (r.get('inst_id'), r.get('pos_side'), r.get('record_type'))
                # 比较updated_at或created_at，保留最新的
                existing = latest_records.get(key)
                if existing is None:
                    latest_records[key] = r
                else:
                    # 比较时间戳，保留更新的
                    existing_time = existing.get('updated_at') or existing.get('created_at') or ''
                    new_time = r.get('updated_at') or r.get('created_at') or ''
                    if new_time > existing_time:
                        latest_records[key] = r
            
            # 转换为列表并排序
            unique_records = list(latest_records.values())
            unique_records.sort(key=lambda x: (
                x.get('inst_id', ''),
                x.get('pos_side', ''),
                x.get('record_type', '')
            ))
            
            records = []
            for r in unique_records:
                records.append({
                    'inst_id': r.get('inst_id'),
                    'pos_side': r.get('pos_side'),
                    'record_type': r.get('record_type'),
                    'profit_rate': r.get('profit_rate'),
                    'timestamp': r.get('updated_at') or r.get('created_at'),
                    'pos_size': r.get('pos_size'),
                    'avg_price': r.get('avg_price'),
                    'mark_price': r.get('mark_price')
                })
        
        return jsonify({
            'success': True,
            'records': records,
            'total': len(records),
            'trade_mode': trade_mode,
            'data_source': 'JSONL'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/anchor-system/profit-records-with-coins')
def get_profit_records_with_coins():
    """获取历史极值记录 + 27个币的实时涨跌幅和价格"""
    try:
        trade_mode = request.args.get('trade_mode', 'real')
        
        # 1. 获取极值记录
        manager = ExtremeJSONLManager(trade_mode=trade_mode)
        all_records = manager.get_deduplicated_records()
        
        # 转换为API格式
        records = []
        for r in all_records:
            records.append({
                'inst_id': r.get('inst_id'),
                'pos_side': r.get('pos_side'),
                'record_type': r.get('record_type'),
                'profit_rate': r.get('profit_rate'),
                'timestamp': r.get('updated_at') or r.get('created_at'),
                'pos_size': r.get('pos_size'),
                'avg_price': r.get('avg_price'),
                'mark_price': r.get('mark_price')
            })
        
        # 2. 获取27个币的实时涨跌幅和价格
        coins_data = None
        try:
            # 读取最新的27币数据
            import os
            import json as json_module
            
            coin_prices_file = 'data/coin_price_tracker/coin_prices_30min.jsonl'
            if os.path.exists(coin_prices_file):
                with open(coin_prices_file, 'r', encoding='utf-8') as f:
                    # 读取最后一行（最新数据）
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        if last_line:
                            latest_data = json_module.loads(last_line)
                            
                            # 提取27个币的数据
                            coins_list = []
                            day_changes = latest_data.get('day_changes', {})
                            
                            for symbol, data in day_changes.items():
                                if isinstance(data, dict):
                                    coins_list.append({
                                        'symbol': symbol,
                                        'name': symbol,  # 简化处理
                                        'current_price': data.get('current_price', 0),
                                        'base_price': data.get('base_price', 0),
                                        'day_change_percent': data.get('change_pct', 0),  # 使用 change_pct 字段
                                    })
                            
                            if coins_list:
                                coins_data = {
                                    'timestamp': latest_data.get('timestamp'),
                                    'datetime': latest_data.get('collect_time', latest_data.get('datetime')),  # 使用 collect_time
                                    'total_change': latest_data.get('total_change', 0),  # 使用 total_change
                                    'coins': coins_list
                                }
        except Exception as e:
            print(f"❌ 获取27币数据失败: {e}")
        
        return jsonify({
            'success': True,
            'records': records,
            'total': len(records),
            'trade_mode': trade_mode,
            'data_source': 'JSONL',
            'coins_data': coins_data  # 新增：27个币的实时数据
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/anchor-system/cleanup-extremes', methods=['POST'])
def cleanup_extreme_records():
    """清理错误的极值记录（删除所有亏损记录）"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from extreme_correction_system import (
            init_correction_system, backup_current_data,
            detect_error_records, delete_error_records, get_statistics
        )
        
        # 初始化
        from anchor_system import init_database
        init_database()
        init_correction_system()
        
        # 备份
        backup_count = backup_current_data()
        
        # 检测错误记录
        error_records = detect_error_records()
        
        if not error_records:
            return jsonify({
                'success': True,
                'message': '没有发现错误记录',
                'backup_count': backup_count,
                'deleted_count': 0
            })
        
        # 删除错误记录
        deleted_count = delete_error_records(error_records, "Web端手动清理")
        
        # 获取统计
        stats = get_statistics()
        
        return jsonify({
            'success': True,
            'message': f'已清理 {deleted_count} 条错误记录',
            'backup_count': backup_count,
            'deleted_count': deleted_count,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/anchor-system/extreme-stats')
def get_extreme_stats():
    """获取极值记录统计信息"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp')
        from extreme_correction_system import get_statistics, detect_error_records
        
        # 获取统计
        stats = get_statistics()
        
        # 检测错误记录
        error_records = detect_error_records()
        
        return jsonify({
            'success': True,
            'statistics': stats,
            'error_count': len(error_records),
            'has_errors': len(error_records) > 0
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/anchor-system/correction-log')
def get_correction_log():
    """获取纠错日志"""
    try:
        limit = int(request.args.get('limit', 20))
        
        db_path = '/home/user/webapp/databases/anchor_system.db'
        conn = sqlite3.connect(db_path, timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, correction_type, inst_id, pos_side, record_type,
               old_profit_rate, new_profit_rate, reason, created_at
        FROM extreme_corrections_log
        ORDER BY created_at DESC
        LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            logs.append({
                'id': row[0],
                'correction_type': row[1],
                'inst_id': row[2],
                'pos_side': row[3],
                'record_type': row[4],
                'old_profit_rate': row[5],
                'new_profit_rate': row[6],
                'reason': row[7],
                'created_at': row[8]
            })
        
        return jsonify({
            'success': True,
            'logs': logs,
            'total': len(logs)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/anchor-system/current-positions')
def get_current_positions():
    """获取当前持仓情况 - 模拟盘直接读取数据库，实盘从 OKEx API 实时获取"""
    try:
        import sys
        import sqlite3
        from datetime import datetime
        sys.path.append('/home/user/webapp')
        from anchor_system import get_positions, calculate_profit_rate
        
        # 获取交易模式（默认为 paper 模拟盘）
        trade_mode = request.args.get('trade_mode', 'paper')
        
        # 连接数据库，获取维护后的开仓价格
        DB_PATH = '/home/user/webapp/databases/trading_decision.db'
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 从数据库读取模拟盘数据 - 联合查询维护价格表
        cursor.execute('''
            SELECT 
                p.inst_id, 
                p.pos_side, 
                COALESCE(amp.maintenance_price, p.open_price) as open_price,
                p.open_size, 
                p.updated_time, 
                p.mark_price, 
                p.profit_rate, 
                p.upl, 
                p.lever, 
                p.margin,
                amp.original_open_price,
                amp.maintenance_count,
                p.is_anchor
            FROM position_opens p
            LEFT JOIN anchor_maintenance_prices amp 
                ON p.inst_id = amp.inst_id 
                AND p.pos_side = amp.pos_side 
                AND p.trade_mode = amp.trade_mode
            WHERE p.trade_mode = ?
        ''', (trade_mode,))
        
        db_positions = cursor.fetchall()
        conn.close()
        
        # 如果是模拟盘，直接使用数据库数据
        if trade_mode == 'paper':
            position_list = []
            for row in db_positions:
                profit_rate = row['profit_rate'] if row['profit_rate'] is not None else 0.0
                
                # 判断状态
                status = '监控中'
                status_class = 'normal'
                if profit_rate >= 40:
                    status = '接近盈利目标'
                    status_class = 'profit'
                elif profit_rate <= -10:
                    status = '接近止损'
                    status_class = 'loss'
                
                position_list.append({
                    'inst_id': row['inst_id'],
                    'pos_side': row['pos_side'],
                    'pos_size': abs(float(row['open_size'])),
                    'avg_price': float(row['open_price']),  # 现在使用维护价格
                    'mark_price': float(row['mark_price']) if row['mark_price'] else 0.0,
                    'lever': int(row['lever']) if row['lever'] else 10,
                    'upl': float(row['upl']) if row['upl'] else 0.0,
                    'margin': float(row['margin']) if row['margin'] else 0.0,
                    'profit_rate': profit_rate,
                    'status': status,
                    'status_class': status_class,
                    'is_anchor': int(row['is_anchor']) if row['is_anchor'] else 0
                })
            
            return jsonify({
                'success': True,
                'positions': position_list,
                'total': len(position_list),
                'trade_mode': trade_mode
            })
        
        # 如果是实盘，从 OKEx API 获取实时持仓
        okex_positions = get_positions()
        
        if not okex_positions or len(okex_positions) == 0:
            return jsonify({
                'success': True,
                'positions': [],
                'total': 0,
                'trade_mode': trade_mode,
                'message': '从OKEx API获取到0个仓位'
            })
        
        # 将数据库记录转换为字典（只用于判断是否为锚点单）
        db_positions_dict = {(row['inst_id'], row['pos_side']): row for row in db_positions}
        
        position_list = []
        for pos in okex_positions:
            inst_id = pos.get('instId')
            pos_side = pos.get('posSide')
            pos_value = float(pos.get('pos', 0))
            
            # 跳过持仓量为0的
            if pos_value == 0:
                continue
            
            # 查找数据库记录（只用于标记是否为锚点单）
            db_record = db_positions_dict.get((inst_id, pos_side))
            
            # ✅ 实盘模式：完全使用 OKEx API 的实时数据
            avg_price = float(pos.get('avgPx', 0) or 0)
            mark_price = float(pos.get('markPx', 0) or 0)
            lever = int(pos.get('lever', 10) or 10)
            upl = float(pos.get('upl', 0) or 0)
            margin = float(pos.get('margin', 0) or 0)
            
            # 判断是否为锚点单（从数据库标记）
            is_anchor = 0
            if db_record and db_record['is_anchor']:
                is_anchor = int(db_record['is_anchor'])
            
            # 计算收益率：使用 margin 计算（更准确）
            if margin > 0:
                profit_rate = (upl / margin) * 100
            else:
                # 备用计算：价格变动率 * 杠杆
                if avg_price > 0:
                    if pos_side == 'short':
                        profit_rate = ((avg_price - mark_price) / avg_price) * lever * 100
                    else:  # long
                        profit_rate = ((mark_price - avg_price) / avg_price) * lever * 100
                else:
                    profit_rate = 0.0
            
            # 判断状态
            status = '监控中'
            status_class = 'normal'
            if profit_rate >= 40:
                status = '接近盈利目标'
                status_class = 'profit'
            elif profit_rate <= -10:
                status = '接近止损'
                status_class = 'loss'
            
            position_list.append({
                'inst_id': inst_id,
                'pos_side': pos_side,
                'pos_size': abs(pos_value),
                'avg_price': avg_price,
                'mark_price': mark_price,
                'lever': lever,
                'upl': upl,
                'margin': margin,
                'profit_rate': profit_rate,
                'status': status,
                'status_class': status_class,
                'is_anchor': is_anchor
            })
        
        return jsonify({
            'success': True,
            'positions': position_list,
            'total': len(position_list),
            'trade_mode': trade_mode
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

# ====================交易决策系统路由 ====================

@app.route('/trading-decision')
def trading_decision_page():
    """交易决策系统管理页面 - 重定向到统一管理页面"""
    return redirect('/trading-manager')

@app.route('/api/trading/anchor-maintenance/logs')
def anchor_maintenance_logs_api():
    """获取锚点单维护日志"""
    try:
        limit = request.args.get('limit', 10, type=int)
        
        conn = sqlite3.connect('/home/user/webapp/databases/trading_decision.db', timeout=10.0)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, inst_id, pos_side, original_size, original_price, 
               original_margin, current_price, profit_rate, step, action,
               trade_size, trade_price, remaining_size, remaining_margin,
               trigger_reason, decision_log, status, executed_at, created_at
        FROM anchor_maintenance_logs
        ORDER BY created_at DESC
        LIMIT ?
        ''', (limit,))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'id': row[0],
                'inst_id': row[1],
                'pos_side': row[2],
                'original_size': float(row[3]),
                'original_price': float(row[4]),
                'original_margin': float(row[5]),
                'current_price': float(row[6]),
                'profit_rate': float(row[7]),
                'step': row[8],
                'action': row[9],
                'trade_size': float(row[10]),
                'trade_price': float(row[11]),
                'remaining_size': float(row[12]),
                'remaining_margin': float(row[13]),
                'trigger_reason': row[14],
                'decision_log': row[15],
                'status': row[16],
                'executed_at': row[17],
                'created_at': row[18]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'count': len(logs),
            'logs': logs
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/trading/config', methods=['GET', 'POST'])
def trading_config_api():
    """交易配置API"""
    config_file = '/home/user/webapp/trading_config.json'
    
    if request.method == 'GET':
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            return jsonify({'success': True, 'config': config})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        try:
            new_config = request.json
            
            # 更新数据库中的配置
            conn = sqlite3.connect('/home/user/webapp/databases/trading_decision.db', timeout=10.0)
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE market_config SET
                market_mode = ?,
                market_trend = ?,
                total_capital = ?,
                position_limit_percent = ?,
                anchor_capital_limit = ?,
                allow_long = ?,
                enabled = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            ''', (
                new_config.get('market_mode'),
                new_config.get('market_trend'),
                new_config.get('total_capital'),
                new_config.get('position_limit_percent'),
                new_config.get('anchor_capital_limit'),
                1 if new_config.get('allow_long') else 0,
                1 if new_config.get('enabled') else 0
            ))
            conn.commit()
            conn.close()
            
            # 更新JSON文件
            with open(config_file, 'w') as f:
                json.dump(new_config, f, indent=2)
            
            return jsonify({'success': True, 'message': '配置更新成功'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/trading/decisions')
def trading_decisions_api():
    """获取交易决策记录"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        conn = sqlite3.connect('/home/user/webapp/databases/trading_decision.db', timeout=10.0)
        cursor = conn.cursor()
        cursor.execute(f'''
        SELECT id, inst_id, pos_side, action, decision_type, current_size,
               target_size, close_size, close_percent, profit_rate,
               current_price, reason, executed, timestamp
        FROM trading_decisions
        ORDER BY id DESC
        LIMIT {limit}
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        decisions = []
        for row in rows:
            decisions.append({
                'id': row[0],
                'inst_id': row[1],
                'pos_side': row[2],
                'action': row[3],
                'decision_type': row[4],
                'current_size': row[5],
                'target_size': row[6],
                'close_size': row[7],
                'close_percent': row[8],
                'profit_rate': row[9],
                'current_price': row[10],
                'reason': row[11],
                'executed': bool(row[12]),
                'timestamp': row[13]
            })
        
        return jsonify({'success': True, 'decisions': decisions, 'total': len(decisions)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/trading/signals')
def trading_signals_api():
    """获取交易信号（供其他账号使用）"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        conn = sqlite3.connect('/home/user/webapp/databases/trading_decision.db', timeout=10.0)
        cursor = conn.cursor()
        cursor.execute(f'''
        SELECT id, inst_id, signal_type, action, price, size,
               profit_rate, reason, timestamp
        FROM trading_signals
        ORDER BY id DESC
        LIMIT {limit}
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in rows:
            signals.append({
                'id': row[0],
                'inst_id': row[1],
                'signal_type': row[2],
                'action': row[3],
                'price': row[4],
                'size': row[5],
                'profit_rate': row[6],
                'reason': row[7],
                'timestamp': row[8]
            })
        
        return jsonify({'success': True, 'signals': signals, 'total': len(signals)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/trading/maintenance')
def trading_maintenance_api():
    """获取锚点单维护记录"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        conn = sqlite3.connect('/home/user/webapp/databases/trading_decision.db', timeout=10.0)
        cursor = conn.cursor()
        cursor.execute(f'''
        SELECT id, inst_id, pos_side, original_size, original_price,
               maintenance_price, maintenance_size, profit_rate,
               action, status, timestamp
        FROM anchor_maintenance
        ORDER BY id DESC
        LIMIT {limit}
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        records = []
        for row in rows:
            records.append({
                'id': row[0],
                'inst_id': row[1],
                'pos_side': row[2],
                'original_size': row[3],
                'original_price': row[4],
                'maintenance_price': row[5],
                'maintenance_size': row[6],
                'profit_rate': row[7],
                'action': row[8],
                'status': row[9],
                'timestamp': row[10]
            })
        
        return jsonify({'success': True, 'records': records, 'total': len(records)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# 已移除 trading-manager 功能（用户需求 2026-01-14）
# @app.route('/dashboard')
# def dashboard():
#     """实时监控仪表板 - 重定向到统一管理页面"""
#     return redirect('/trading-manager')
# 
# @app.route('/trading-manager')
# def trading_manager():
#     """交易管理界面 - 模拟交易系统"""
#     try:
#         with open('/home/user/webapp/templates/trading_manager.html', 'r', encoding='utf-8') as f:
#             content = f.read()
#         
#         # 添加缓存控制头，强制浏览器刷新
#         response = make_response(content)
#         response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
#         response.headers['Pragma'] = 'no-cache'
#         response.headers['Expires'] = '0'
#         return response
#     except FileNotFoundError:
#         return "Trading manager template not found", 404
#     except Exception as e:
#         return f"Error loading trading manager: {str(e)}", 500
# 
# @app.route('/simulated-trades')
# def simulated_trades():
#     """模拟交易详情界面"""
#     try:
#         with open('/home/user/webapp/templates/simulated_trades.html', 'r', encoding='utf-8') as f:
#             return f.read()
#     except FileNotFoundError:
#         return "Simulated trades template not found", 404
#     except Exception as e:
#         return f"Error loading simulated trades: {str(e)}", 500

@app.route('/api/anchor-system/warnings')
def get_anchor_warnings():
    """获取当前活跃的锚点预警"""
    try:
        import sqlite3
        
        # 获取交易模式
        trade_mode = request.args.get('trade_mode', 'paper')
        
        DB_PATH = '/home/user/webapp/databases/trading_decision.db'
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询活跃预警
        cursor.execute('''
            SELECT inst_id, pos_side, open_price, current_price, profit_rate, 
                   open_size, warning_level, alert_message, status, created_at, trade_mode
            FROM anchor_warning_monitor
            WHERE status = 'active' AND trade_mode = ?
            ORDER BY profit_rate ASC
        ''', (trade_mode,))
        
        warnings = cursor.fetchall()
        conn.close()
        
        warning_list = []
        for row in warnings:
            warning_list.append({
                'inst_id': row['inst_id'],
                'pos_side': row['pos_side'],
                'open_price': float(row['open_price']),
                'current_price': float(row['current_price']) if row['current_price'] else 0.0,
                'profit_rate': float(row['profit_rate']),
                'open_size': float(row['open_size']),
                'warning_level': row['warning_level'],
                'alert_message': row['alert_message'],
                'status': row['status'],
                'created_at': row['created_at'],
                'trade_mode': row['trade_mode']
            })
        
        return jsonify({
            'success': True,
            'warnings': warning_list,
            'total': len(warning_list),
            'trade_mode': trade_mode
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/anchor-system/sub-account-positions')
def get_sub_account_positions():
    """获取子账户持仓情况"""
    try:
        import sys
        import hmac
        import base64
        import hashlib
        import requests
        from datetime import datetime
        
        sys.path.append('/home/user/webapp/source_code')
        from okex_api_config_subaccount import (
            OKEX_API_KEY, 
            OKEX_SECRET_KEY, 
            OKEX_PASSPHRASE,
            OKEX_REST_URL
        )
        
        # 获取交易模式
        trade_mode = request.args.get('trade_mode', 'paper')
        
        # 如果是模拟盘，返回空数据
        if trade_mode == 'paper':
            return jsonify({
                'success': True,
                'positions': [],
                'total': 0,
                'trade_mode': trade_mode,
                'account_name': '子账户（模拟盘）'
            })
        
        # 生成签名
        def get_signature(secret_key, timestamp, method, request_path, body=''):
            message = timestamp + method + request_path + body
            mac = hmac.new(
                bytes(secret_key, encoding='utf8'),
                bytes(message, encoding='utf8'),
                digestmod=hashlib.sha256
            )
            return base64.b64encode(mac.digest()).decode()
        
        # 获取请求头
        def get_headers(method, request_path, body=''):
            timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
            signature = get_signature(OKEX_SECRET_KEY, timestamp, method, request_path, body)
            
            return {
                'OK-ACCESS-KEY': OKEX_API_KEY,
                'OK-ACCESS-SIGN': signature,
                'OK-ACCESS-TIMESTAMP': timestamp,
                'OK-ACCESS-PASSPHRASE': OKEX_PASSPHRASE,
                'Content-Type': 'application/json'
            }
        
        # 获取子账户持仓
        method = 'GET'
        request_path = '/api/v5/account/positions'
        headers = get_headers(method, request_path)
        
        response = requests.get(OKEX_REST_URL + request_path, headers=headers, timeout=10)
        data = response.json()
        
        if data.get('code') != '0':
            return jsonify({
                'success': False,
                'error': f"OKEx API错误: {data.get('msg')}",
                'positions': [],
                'total': 0
            })
        
        positions = data.get('data', [])
        
        # 过滤并格式化持仓数据
        position_list = []
        for pos in positions:
            try:
                pos_size = float(pos.get('pos', 0))
                if pos_size == 0:
                    continue
                
                inst_id = pos.get('instId', '')
                pos_side = pos.get('posSide', '').lower()
                
                # 安全地转换数值，处理空字符串
                def safe_float(value, default=0.0):
                    if value == '' or value is None:
                        return default
                    try:
                        return float(value)
                    except (ValueError, TypeError):
                        return default
                
                avg_price = safe_float(pos.get('avgPx', 0))
                mark_price = safe_float(pos.get('markPx', 0))
                lever = int(safe_float(pos.get('lever', 10)))
                upl = safe_float(pos.get('upl', 0))
                margin = safe_float(pos.get('margin', 0))
                
                # 计算收益率
                profit_rate = 0.0
                upl_ratio = pos.get('uplRatio')
                if upl_ratio and upl_ratio != '':
                    profit_rate = safe_float(upl_ratio) * 100
                elif margin > 0:
                    profit_rate = (upl / margin) * 100
                
                position_list.append({
                    'account_name': '子账户',
                    'inst_id': inst_id,
                    'pos_side': pos_side,
                    'pos_size': abs(pos_size),
                    'avg_price': avg_price,
                    'mark_price': mark_price,
                    'leverage': lever,
                    'upl': upl,
                    'margin': margin,
                    'profit_rate': profit_rate
                })
            except Exception as e:
                print(f"处理持仓数据错误: {e}, pos: {pos}")
                continue
        
        return jsonify({
            'success': True,
            'positions': position_list,
            'total': len(position_list),
            'trade_mode': trade_mode,
            'account_name': '子账户'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc(),
            'positions': [],
            'total': 0
        })

@app.route('/api/trading/positions/opens')
def get_trading_positions_opens():
    """获取开仓持仓 - Trading Manager专用，支持维护价格表"""
    try:
        import sqlite3
        
        # 获取参数
        is_anchor = request.args.get('is_anchor', type=int)
        limit = request.args.get('limit', 50, type=int)
        trade_mode = request.args.get('trade_mode', 'paper')
        
        DB_PATH = '/home/user/webapp/databases/trading_decision.db'
        conn = sqlite3.connect(DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 如果是锚点单，使用维护价格表
        if is_anchor == 1:
            # 联合查询：position_opens 和 anchor_maintenance_prices
            cursor.execute('''
                SELECT 
                    p.id,
                    p.inst_id,
                    p.pos_side,
                    p.open_size,
                    p.mark_price,
                    p.profit_rate,
                    p.lever,
                    p.upl,
                    p.margin,
                    p.created_at,
                    p.updated_time,
                    p.trade_mode,
                    p.is_anchor,
                    p.granularity,
                    p.open_percent,
                    p.total_adds,
                    p.total_positions,
                    COALESCE(amp.maintenance_price, p.open_price) as open_price,
                    amp.original_open_price,
                    amp.maintenance_count,
                    amp.last_maintenance_time,
                    p.mark_price as current_price
                FROM position_opens p
                LEFT JOIN anchor_maintenance_prices amp 
                    ON p.inst_id = amp.inst_id 
                    AND p.pos_side = amp.pos_side 
                    AND p.trade_mode = amp.trade_mode
                WHERE p.is_anchor = 1 AND p.trade_mode = ?
                ORDER BY p.id DESC
                LIMIT ?
            ''', (trade_mode, limit))
            
            rows = cursor.fetchall()
            
            # 获取最新价格更新时间
            cursor.execute('''
                SELECT MAX(updated_time) FROM position_opens WHERE is_anchor = 1 AND trade_mode = ?
            ''', (trade_mode,))
            
            price_update_time = cursor.fetchone()[0] or ''
            
            records = []
            for row in rows:
                records.append({
                    'id': row['id'],
                    'inst_id': row['inst_id'],
                    'pos_side': row['pos_side'],
                    'open_price': float(row['open_price']),  # 使用维护价格
                    'original_open_price': float(row['original_open_price']) if row['original_open_price'] else None,
                    'open_size': float(row['open_size']),
                    'current_price': float(row['current_price']) if row['current_price'] else 0.0,
                    'mark_price': float(row['mark_price']) if row['mark_price'] else 0.0,
                    'profit_rate': float(row['profit_rate']) if row['profit_rate'] else 0.0,
                    'lever': int(row['lever']) if row['lever'] else 10,
                    'upl': float(row['upl']) if row['upl'] else 0.0,
                    'margin': float(row['margin']) if row['margin'] else 0.0,
                    'is_anchor': bool(row['is_anchor']),
                    'granularity': float(row['granularity']) if row['granularity'] else 0.0,
                    'open_percent': float(row['open_percent']) if row['open_percent'] else 0.0,
                    'total_adds': int(row['total_adds']) if row['total_adds'] else 0,
                    'total_positions': int(row['total_positions']) if row['total_positions'] else 0,
                    'maintenance_count': int(row['maintenance_count']) if row['maintenance_count'] else 0,
                    'last_maintenance_time': row['last_maintenance_time'] or '',
                    'created_at': row['created_at'],
                    'price_update_time': row['updated_time'] or '',
                    'trade_mode': row['trade_mode']
                })
            
            conn.close()
            
            return jsonify({
                'success': True,
                'records': records,
                'total': len(records),
                'price_update_time': price_update_time,
                'trade_mode': trade_mode
            })
        
        # 非锚点单，直接查询
        else:
            cursor.execute('''
                SELECT 
                    id, inst_id, pos_side, open_price, open_size, mark_price, 
                    profit_rate, lever, upl, margin, created_at, updated_time,
                    trade_mode, is_anchor, granularity, open_percent, 
                    total_adds, total_positions
                FROM position_opens
                WHERE (? IS NULL OR is_anchor = ?) AND trade_mode = ?
                ORDER BY id DESC
                LIMIT ?
            ''', (is_anchor, is_anchor, trade_mode, limit))
            
            rows = cursor.fetchall()
            conn.close()
            
            records = []
            for row in rows:
                records.append({
                    'id': row['id'],
                    'inst_id': row['inst_id'],
                    'pos_side': row['pos_side'],
                    'open_price': float(row['open_price']),
                    'open_size': float(row['open_size']),
                    'current_price': float(row['mark_price']) if row['mark_price'] else 0.0,
                    'mark_price': float(row['mark_price']) if row['mark_price'] else 0.0,
                    'profit_rate': float(row['profit_rate']) if row['profit_rate'] else 0.0,
                    'lever': int(row['lever']) if row['lever'] else 10,
                    'upl': float(row['upl']) if row['upl'] else 0.0,
                    'margin': float(row['margin']) if row['margin'] else 0.0,
                    'is_anchor': bool(row['is_anchor']),
                    'granularity': float(row['granularity']) if row['granularity'] else 0.0,
                    'open_percent': float(row['open_percent']) if row['open_percent'] else 0.0,
                    'total_adds': int(row['total_adds']) if row['total_adds'] else 0,
                    'total_positions': int(row['total_positions']) if row['total_positions'] else 0,
                    'created_at': row['created_at'],
                    'price_update_time': row['updated_time'] or '',
                    'trade_mode': row['trade_mode']
                })
            
            return jsonify({
                'success': True,
                'records': records,
                'total': len(records),
                'trade_mode': trade_mode
            })
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

# 测试页面路由
@app.route('/test-positions')
def test_positions_page():
    """持仓数据测试页面"""
    return render_template('test_positions.html')

# ==================== 交易对保护系统 API ====================

# 导入保护系统模块
import sys
sys.path.append('/home/user/webapp/source_code')

from gdrive_jsonl_manager import GDriveJSONLManager

from trading_pair_protector import (
    start_protection, 
    stop_protection, 
    get_protection_status,
    check_and_protect,
    get_protected_pairs
)

@app.route('/api/pair-protection/start', methods=['POST'])
def start_pair_protection():
    """启动交易对保护"""
    try:
        success = start_protection()
        status = get_protection_status()
        
        return jsonify({
            'success': success,
            'protected_count': status.get('protected_count', 0),
            'current_count': status.get('current_count', 0),
            'message': '保护系统已启动' if success else '启动失败'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/pair-protection/stop', methods=['POST'])
def stop_pair_protection():
    """停止交易对保护"""
    try:
        stop_protection()
        
        return jsonify({
            'success': True,
            'message': '保护系统已停止'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/pair-protection/status')
def get_pair_protection_status():
    """获取保护状态"""
    try:
        status = get_protection_status()
        protected = get_protected_pairs()
        
        return jsonify({
            'success': True,
            'is_running': status.get('is_running', False),
            'protected_count': status.get('protected_count', 0),
            'current_count': status.get('current_count', 0),
            'last_check': status.get('last_check'),
            'fill_count': status.get('fill_count', 0),
            'missing_pairs': status.get('missing_pairs', []),
            'protected_pairs': list(protected)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/pair-protection/check', methods=['POST'])
def manual_check_protection():
    """手动检查一次"""
    try:
        check_and_protect()
        status = get_protection_status()
        
        return jsonify({
            'success': True,
            'status': status,
            'message': '检查完成'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# ==================== 锚定系统盈利指标监控 API ====================

@app.route('/api/anchor-profit/latest')
def get_anchor_profit_latest():
    """获取最近的盈利指标数据"""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, '/home/user/webapp/source_code')
        from anchor_profit_monitor import get_recent_data
        
        # 获取时间范围参数（分钟）
        minutes = request.args.get('minutes', 60, type=int)
        
        # 获取最近数据
        data = get_recent_data(minutes)
        
        return jsonify({
            'success': True,
            'data': data,
            'count': len(data),
            'minutes': minutes
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/anchor-profit/collect', methods=['POST'])
def trigger_anchor_profit_collect():
    """手动触发一次数据收集"""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, '/home/user/webapp/source_code')
        from anchor_profit_monitor import collect_and_save
        
        # 收集并保存数据
        data = collect_and_save()
        
        return jsonify({
            'success': True,
            'data': data,
            'message': '数据收集完成'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/anchor-profit/history')
def get_anchor_profit_history():
    """获取历史数据（优化版：支持压缩）"""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, '/home/user/webapp/source_code')
        from anchor_profit_monitor import get_recent_data
        
        # 获取limit参数（默认60条，即最近1小时）
        limit = request.args.get('limit', 60, type=int)
        
        # 限制最大请求量，避免性能问题
        max_limit = 4320  # 最多3天的数据
        if limit > max_limit:
            limit = max_limit
        
        # 获取最近数据
        data = get_recent_data(limit)
        
        response_data = {
            'success': True,
            'data': data,
            'count': len(data)
        }
        
        # 创建响应
        response = jsonify(response_data)
        
        # 添加缓存头（缓存60秒）
        response.headers['Cache-Control'] = 'public, max-age=60'
        
        return response
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/anchor-profit/dates')
def get_anchor_profit_dates():
    """获取可用的日期列表"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from anchor_daily_reader import AnchorDailyReader
        
        reader = AnchorDailyReader()
        dates = reader.get_available_dates()
        
        return jsonify({
            'success': True,
            'dates': dates,
            'count': len(dates)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/anchor-profit/by-date')
def get_anchor_profit_by_date():
    """按日期获取锚点盈利数据"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from anchor_daily_reader import AnchorDailyReader
        from datetime import datetime
        
        # 获取日期参数（默认今天）
        date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        data_type = request.args.get('type', 'profit_stats')  # 默认只返回盈利统计
        
        reader = AnchorDailyReader()
        data = reader.get_date_data(date, data_type)
        
        # 获取统计信息
        stats = reader.get_date_statistics(date)
        
        return jsonify({
            'success': True,
            'date': date,
            'data': data,
            'count': len(data),
            'statistics': stats
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/anchor-profit/summary')
def get_anchor_profit_summary():
    """获取盈利统计摘要"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/source_code')
        from anchor_daily_reader import AnchorDailyReader
        from datetime import datetime
        
        # 获取日期参数（默认今天）
        date = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
        
        reader = AnchorDailyReader()
        summary = reader.get_profit_stats_summary(date)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/backfill-monitor')
def backfill_monitor():
    """数据回填监控页面"""
    response = make_response(render_template('backfill_monitor.html'))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/api/backfill-monitor/logs')
def backfill_monitor_logs():
    """获取回填日志"""
    try:
        log_file = '/home/user/webapp/logs/coin_price_backfill.log'
        if os.path.exists(log_file):
            # 读取最后500行
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-500:] if len(lines) > 500 else lines
                logs = ''.join(recent_lines)
        else:
            logs = '日志文件不存在'
        
        return jsonify({
            'success': True,
            'logs': logs
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/backfill-monitor/stop', methods=['POST'])
def backfill_monitor_stop():
    """停止回填进程"""
    try:
        import subprocess
        # 查找回填进程并终止
        result = subprocess.run(['pkill', '-f', 'coin_price_backfill_history.py'], capture_output=True)
        return jsonify({
            'success': True,
            'message': '已发送停止信号'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/extreme-market-alerts/latest')
def api_extreme_market_alerts_latest():
    """获取最新的极端市场预警记录"""
    try:
        db_path = '/home/user/webapp/databases/crypto_data.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        limit = request.args.get('limit', 50, type=int)
        
        cursor.execute("""
            SELECT alert_time, alert_type, total_change, coin_count, details, created_at
            FROM extreme_market_alerts
            ORDER BY alert_time DESC
            LIMIT ?
        """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        alerts = []
        for row in rows:
            alert_time, alert_type, total_change, coin_count, details, created_at = row
            alerts.append({
                'alert_time': alert_time,
                'alert_type': alert_type,
                'alert_type_name': '极端上涨' if alert_type == 'extreme_high' else '极端暴跌',
                'total_change': total_change,
                'coin_count': coin_count,
                'details': json.loads(details) if details else [],
                'created_at': created_at
            })
        
        return jsonify({
            'success': True,
            'count': len(alerts),
            'data': alerts
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/extreme-market-alerts/stats')
def api_extreme_market_alerts_stats():
    """获取极端市场预警统计"""
    try:
        db_path = '/home/user/webapp/databases/crypto_data.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 统计总数
        cursor.execute("SELECT COUNT(*) FROM extreme_market_alerts")
        total_count = cursor.fetchone()[0]
        
        # 统计极端上涨次数
        cursor.execute("SELECT COUNT(*) FROM extreme_market_alerts WHERE alert_type = 'extreme_high'")
        high_count = cursor.fetchone()[0]
        
        # 统计极端暴跌次数
        cursor.execute("SELECT COUNT(*) FROM extreme_market_alerts WHERE alert_type = 'extreme_low'")
        low_count = cursor.fetchone()[0]
        
        # 获取最新预警
        cursor.execute("""
            SELECT alert_time, alert_type, total_change
            FROM extreme_market_alerts
            ORDER BY alert_time DESC
            LIMIT 1
        """)
        latest = cursor.fetchone()
        
        conn.close()
        
        stats = {
            'total_count': total_count,
            'extreme_high_count': high_count,
            'extreme_low_count': low_count,
            'latest_alert': {
                'alert_time': latest[0],
                'alert_type': latest[1],
                'alert_type_name': '极端上涨' if latest[1] == 'extreme_high' else '极端暴跌',
                'total_change': latest[2]
            } if latest else None
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })


# ==================== 极值追踪系统 API ====================

@app.route('/api/extreme-tracking/snapshots')
def api_extreme_tracking_snapshots():
    """获取极值追踪快照列表"""
    try:
        import json
        from pathlib import Path
        
        snapshots_file = Path('/home/user/webapp/data/extreme_tracking/extreme_snapshots.jsonl')
        
        if not snapshots_file.exists():
            return jsonify({
                'success': True,
                'data': [],
                'message': '暂无快照数据'
            })
        
        # 读取所有快照
        snapshots = []
        with open(snapshots_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    snapshots.append(json.loads(line))
        
        # 按时间倒序排序
        snapshots.sort(key=lambda x: x.get('trigger_time', 0), reverse=True)
        
        # 获取查询参数
        limit = request.args.get('limit', type=int, default=None)
        status = request.args.get('status', type=str, default=None)  # active/completed
        
        # 过滤状态
        if status:
            snapshots = [s for s in snapshots if s.get('status') == status]
        
        # 限制数量
        if limit:
            snapshots = snapshots[:limit]
        
        return jsonify({
            'success': True,
            'data': snapshots,
            'count': len(snapshots)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/extreme-tracking/snapshot/<snapshot_id>')
def api_extreme_tracking_snapshot_detail(snapshot_id):
    """获取单个快照的详细信息"""
    try:
        import json
        from pathlib import Path
        
        snapshots_file = Path('/home/user/webapp/data/extreme_tracking/extreme_snapshots.jsonl')
        
        if not snapshots_file.exists():
            return jsonify({
                'success': False,
                'message': '快照文件不存在'
            })
        
        # 查找指定快照
        with open(snapshots_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    snapshot = json.loads(line)
                    if snapshot.get('snapshot_id') == snapshot_id:
                        return jsonify({
                            'success': True,
                            'data': snapshot
                        })
        
        return jsonify({
            'success': False,
            'message': f'未找到快照: {snapshot_id}'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/extreme-tracking/stats')
def api_extreme_tracking_stats():
    """获取极值追踪统计信息"""
    try:
        import json
        from pathlib import Path
        from collections import Counter
        
        snapshots_file = Path('/home/user/webapp/data/extreme_tracking/extreme_snapshots.jsonl')
        
        if not snapshots_file.exists():
            return jsonify({
                'success': True,
                'stats': {
                    'total_snapshots': 0,
                    'active_snapshots': 0,
                    'completed_snapshots': 0,
                    'trigger_types': {}
                }
            })
        
        # 读取所有快照
        snapshots = []
        with open(snapshots_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    snapshots.append(json.loads(line))
        
        # 统计信息
        total_count = len(snapshots)
        active_count = len([s for s in snapshots if s.get('status') == 'active'])
        completed_count = len([s for s in snapshots if s.get('status') == 'completed'])
        
        # 统计触发类型
        trigger_types = Counter()
        for snapshot in snapshots:
            for trigger in snapshot.get('triggers', []):
                trigger_types[trigger.get('type', 'unknown')] += 1
        
        # 计算平均价格变化（已完成的快照）
        completed_snapshots = [s for s in snapshots if s.get('status') == 'completed']
        avg_changes = {
            '1h': 0, '3h': 0, '6h': 0, '12h': 0, '24h': 0
        }
        
        if completed_snapshots:
            for period in avg_changes.keys():
                changes = [
                    s['tracking'][period]['total_change']
                    for s in completed_snapshots
                    if s.get('tracking', {}).get(period)
                ]
                if changes:
                    avg_changes[period] = sum(changes) / len(changes)
        
        stats = {
            'total_snapshots': total_count,
            'active_snapshots': active_count,
            'completed_snapshots': completed_count,
            'trigger_types': dict(trigger_types),
            'average_price_changes': avg_changes
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


# ==================== 实盘交易系统路由 ====================

@app.route('/live-trading')
def live_trading():
    """实盘交易系统主页"""
    try:
        with open('/home/user/webapp/live-trading-system/public/live-trading-v2.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "实盘交易系统文件未找到", 404
    except Exception as e:
        return f"加载实盘交易系统失败: {str(e)}", 500

@app.route('/live-trading/<path:filename>')
def live_trading_static(filename):
    """实盘交易系统静态文件服务"""
    try:
        # 尝试从public目录加载
        file_path = f'/home/user/webapp/live-trading-system/public/{filename}'
        if os.path.exists(file_path):
            # 根据文件扩展名设置mimetype
            if filename.endswith('.js'):
                return send_file(file_path, mimetype='application/javascript')
            elif filename.endswith('.css'):
                return send_file(file_path, mimetype='text/css')
            elif filename.endswith('.html'):
                return send_file(file_path, mimetype='text/html')
            else:
                return send_file(file_path)
        
        # 尝试从根目录加载
        file_path = f'/home/user/webapp/live-trading-system/{filename}'
        if os.path.exists(file_path):
            if filename.endswith('.js'):
                return send_file(file_path, mimetype='application/javascript')
            elif filename.endswith('.css'):
                return send_file(file_path, mimetype='text/css')
            else:
                return send_file(file_path)
        
        return f"文件未找到: {filename}", 404
    except Exception as e:
        import traceback
        print(f"静态文件加载错误: {str(e)}")
        print(traceback.format_exc())
        return f"加载文件失败: {str(e)}", 500

# 实盘交易API端点
@app.route('/api/live-trading/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def live_trading_api(endpoint):
    """实盘交易API代理"""
    try:
        import json
        
        # 这里应该调用实际的交易API
        # 暂时返回模拟数据
        return jsonify({
            'success': True,
            'message': f'API endpoint: {endpoint}',
            'method': request.method,
            'data': request.get_json() if request.is_json else None
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

# ==================== 服务健康监控 API ====================
@app.route('/api/service-health')
def service_health():
    """获取所有数据采集服务的健康状态"""
    try:
        from service_health_monitor import get_health_status
        result = get_health_status()
        return jsonify({
            'success': True,
            **result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

# ==================== 重大事件系统 API ====================
@app.route('/major-events-test')
def major_events_test():
    """重大事件按钮测试页面"""
    try:
        html_file = '/home/user/webapp/test_buttons.html'
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 添加no-cache头
        response = make_response(html_content)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    except FileNotFoundError:
        return "测试页面未找到", 404
    except Exception as e:
        return f"加载测试页面失败: {str(e)}", 500

@app.route('/major-events')
def major_events_page():
    """重大事件系统主页"""
    try:
        html_file = '/home/user/webapp/major-events-system/major_events.html'
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 添加no-cache头，防止浏览器缓存
        response = make_response(html_content)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    except FileNotFoundError:
        return "重大事件系统页面未找到", 404
    except Exception as e:
        return f"加载重大事件系统失败: {str(e)}", 500

@app.route('/major-events/<path:filename>')
def major_events_static(filename):
    """重大事件系统静态文件"""
    try:
        file_path = f'/home/user/webapp/major-events-system/{filename}'
        if os.path.exists(file_path):
            if filename.endswith('.js'):
                return send_file(file_path, mimetype='application/javascript')
            elif filename.endswith('.css'):
                return send_file(file_path, mimetype='text/css')
            else:
                return send_file(file_path)
        return f"文件未找到: {filename}", 404
    except Exception as e:
        return f"加载文件失败: {str(e)}", 500

@app.route('/api/major-events/current-status', methods=['GET'])
def get_major_events_status():
    """获取当前事件监控状态"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/major-events-system')
        from major_events_monitor import MajorEventsMonitor
        
        monitor = MajorEventsMonitor()
        
        # 获取当前数据
        top_signal_count = monitor.get_2h_top_signal_count()
        coins_change_sum = monitor.get_27_coins_change_sum()
        liquidation_amount = monitor.get_1h_liquidation_amount()
        
        # 获取最近24小时的事件
        recent_events = monitor.get_recent_events(hours=24)
        
        return jsonify({
            'success': True,
            'timestamp': datetime.now().isoformat(),
            'current_data': {
                'top_signal_2h': top_signal_count,
                'coins_change_sum': coins_change_sum,
                'liquidation_1h': liquidation_amount
            },
            'event_states': monitor.event_states,
            'recent_events': list(reversed(recent_events[-10:])),  # 最近10个事件，倒序排列（最新的在前）
            'total_events_24h': len(recent_events)
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/major-events/recent', methods=['GET'])
def get_recent_major_events():
    """获取最近的重大事件"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/major-events-system')
        from major_events_monitor import MajorEventsMonitor
        
        monitor = MajorEventsMonitor()
        
        # 获取时间参数
        hours = int(request.args.get('hours', 24))
        
        events = monitor.get_recent_events(hours=hours)
        
        return jsonify({
            'success': True,
            'hours': hours,
            'events': list(reversed(events)),  # 倒序排列，最新的在前
            'total': len(events)
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/major-events/trigger-check', methods=['POST'])
def trigger_event_check():
    """手动触发事件检查"""
    try:
        import sys
        sys.path.insert(0, '/home/user/webapp/major-events-system')
        from major_events_monitor import MajorEventsMonitor
        
        monitor = MajorEventsMonitor()
        triggered_events = monitor.monitor_cycle()
        
        return jsonify({
            'success': True,
            'triggered_events': triggered_events,
            'count': len(triggered_events)
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/anchor-system/profit-history', methods=['GET'])
def get_anchor_system_profit_history():
    """获取锚定系统盈利历史数据（按日期查询，支持分页加载）"""
    try:
        import json
        from pathlib import Path
        
        # 获取参数
        trade_mode = request.args.get('trade_mode', 'real')  # real or paper
        date_str = request.args.get('date')  # YYYY-MM-DD 格式
        
        # 数据目录
        data_dir = Path('/home/user/webapp/data/anchor_profit_stats')
        
        # 如果指定了日期，尝试从按日期文件读取
        if date_str:
            # 尝试按日期文件（新格式）
            date_file = data_dir / f'anchor_profit_{date_str}.jsonl'
            
            if date_file.exists():
                # 从按日期文件读取
                history_data = []
                with open(date_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            # 兼容旧数据：如果没有 trade_mode 字段，默认认为是 real
                            data_trade_mode = data.get('trade_mode', 'real')
                            if data_trade_mode == trade_mode:
                                history_data.append(data)
                        except:
                            continue
                
                return jsonify({
                    'success': True,
                    'trade_mode': trade_mode,
                    'date': date_str,
                    'history': history_data,
                    'count': len(history_data),
                    'source': 'date_file'
                })
            else:
                # 按日期文件不存在，尝试从主文件读取（兼容旧数据）
                main_file = data_dir / 'anchor_profit_stats.jsonl'
                if not main_file.exists():
                    return jsonify({
                        'success': False,
                        'error': f'数据文件不存在：{date_str}'
                    })
                
                # 解析日期范围
                from datetime import datetime as dt
                target_date = dt.strptime(date_str, '%Y-%m-%d')
                start_timestamp = int(target_date.replace(hour=0, minute=0, second=0).timestamp())
                end_timestamp = int(target_date.replace(hour=23, minute=59, second=59).timestamp())
                
                # 从主文件读取指定日期的数据
                history_data = []
                with open(main_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            timestamp = data.get('timestamp', 0)
                            if start_timestamp <= timestamp <= end_timestamp:
                                # 兼容旧数据：如果没有 trade_mode 字段，默认认为是 real
                                data_trade_mode = data.get('trade_mode', 'real')
                                if data_trade_mode == trade_mode:
                                    history_data.append(data)
                        except:
                            continue
                
                return jsonify({
                    'success': True,
                    'trade_mode': trade_mode,
                    'date': date_str,
                    'history': history_data,
                    'count': len(history_data),
                    'source': 'main_file_filtered'
                })
        
        # 如果没有指定日期，返回今天的数据（默认行为）
        else:
            today_str = datetime.now(BEIJING_TZ).strftime('%Y-%m-%d')
            return get_anchor_system_profit_history_by_date(trade_mode, today_str, data_dir)
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

def get_anchor_system_profit_history_by_date(trade_mode, date_str, data_dir):
    """辅助函数：按日期查询数据"""
    import json
    from pathlib import Path
    from datetime import datetime as dt
    
    # 尝试按日期文件
    date_file = data_dir / f'anchor_profit_{date_str}.jsonl'
    
    if date_file.exists():
        history_data = []
        with open(date_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    # 兼容旧数据：如果没有 trade_mode 字段，默认认为是 real
                    data_trade_mode = data.get('trade_mode', 'real')
                    if data_trade_mode == trade_mode:
                        history_data.append(data)
                except:
                    continue
        
        return jsonify({
            'success': True,
            'trade_mode': trade_mode,
            'date': date_str,
            'history': history_data,
            'count': len(history_data),
            'source': 'date_file'
        })
    else:
        # 从主文件读取
        main_file = data_dir / 'anchor_profit_stats.jsonl'
        if not main_file.exists():
            return jsonify({
                'success': False,
                'error': f'数据文件不存在：{date_str}'
            })
        
        target_date = dt.strptime(date_str, '%Y-%m-%d')
        start_timestamp = int(target_date.replace(hour=0, minute=0, second=0).timestamp())
        end_timestamp = int(target_date.replace(hour=23, minute=59, second=59).timestamp())
        
        history_data = []
        with open(main_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    timestamp = data.get('timestamp', 0)
                    if start_timestamp <= timestamp <= end_timestamp:
                        # 兼容旧数据：如果没有 trade_mode 字段，默认认为是 real
                        data_trade_mode = data.get('trade_mode', 'real')
                        if data_trade_mode == trade_mode:
                            history_data.append(data)
                except:
                    continue
        
        return jsonify({
            'success': True,
            'trade_mode': trade_mode,
            'date': date_str,
            'history': history_data,
            'count': len(history_data),
            'source': 'main_file_filtered'
        })

@app.route('/api/major-events/data/sar-slope', methods=['GET'])
def get_sar_slope_data():
    """获取SAR斜率数据（从JSONL读取）"""
    try:
        import json
        from pathlib import Path
        
        hours = int(request.args.get('hours', 1))  # 默认1小时
        jsonl_file = Path('/home/user/webapp/major-events-system/data/sar_slope_data.jsonl')
        
        if not jsonl_file.exists():
            return jsonify({'success': False, 'error': 'JSONL文件不存在'})
        
        data_list = []
        cutoff_time = int(time.time()) - (hours * 3600)
        
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get('timestamp', 0) >= cutoff_time:
                        data_list.append(data)
                except:
                    continue
        
        return jsonify({
            'success': True,
            'hours': hours,
            'data': data_list,
            'count': len(data_list)
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/major-events/data/liquidation', methods=['GET'])
def get_liquidation_data():
    """获取爆仓数据（从JSONL读取）"""
    try:
        import json
        from pathlib import Path
        
        hours = int(request.args.get('hours', 1))  # 默认1小时
        jsonl_file = Path('/home/user/webapp/major-events-system/data/liquidation_data.jsonl')
        
        if not jsonl_file.exists():
            return jsonify({'success': False, 'error': 'JSONL文件不存在'})
        
        data_list = []
        cutoff_time = int(time.time()) - (hours * 3600)
        
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    if data.get('timestamp', 0) >= cutoff_time:
                        data_list.append(data)
                except:
                    continue
        
        return jsonify({
            'success': True,
            'hours': hours,
            'data': data_list,
            'count': len(data_list)
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/api/okx-trading/batch-order', methods=['POST'])
def batch_order_from_event():
    """从重大事件页面触发的批量开仓"""
    try:
        import requests
        import hmac
        import base64
        from datetime import datetime, timezone
        
        data = request.get_json()
        direction = data.get('direction', 'short')  # long/short
        percent_per_coin = float(data.get('percentPerCoin', 5))
        api_key = data.get('apiKey', '')
        secret_key = data.get('apiSecret', '')
        passphrase = data.get('passphrase', '')
        
        if not api_key or not secret_key or not passphrase:
            return jsonify({
                'success': False,
                'error': 'API凭证不完整'
            })
        
        # 1. 获取账户余额
        base_url = 'https://www.okx.com'
        balance_path = '/api/v5/account/balance'
        balance_timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
        balance_message = balance_timestamp + 'GET' + balance_path
        balance_mac = hmac.new(bytes(secret_key, encoding='utf8'), bytes(balance_message, encoding='utf-8'), digestmod='sha256')
        balance_signature = base64.b64encode(balance_mac.digest()).decode()
        
        balance_headers = {
            'OK-ACCESS-KEY': api_key,
            'OK-ACCESS-SIGN': balance_signature,
            'OK-ACCESS-TIMESTAMP': balance_timestamp,
            'OK-ACCESS-PASSPHRASE': passphrase,
            'Content-Type': 'application/json'
        }
        
        balance_response = requests.get(base_url + balance_path, headers=balance_headers, timeout=10)
        balance_result = balance_response.json()
        
        if balance_result.get('code') != '0':
            return jsonify({
                'success': False,
                'error': f"获取余额失败: {balance_result.get('msg')}"
            })
        
        # 提取USDT可用余额
        balance = 0
        for detail in balance_result.get('data', [{}])[0].get('details', []):
            if detail.get('ccy') == 'USDT':
                balance = float(detail.get('availBal', 0))
                break
        
        if balance <= 0:
            return jsonify({
                'success': False,
                'error': f"USDT余额不足: {balance}"
            })
        
        # 2. 获取常用币列表
        favorite_file = 'data/favorite_symbols.jsonl'
        favorite_symbols = []
        try:
            with open(favorite_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    favorite_data = json.loads(lines[-1].strip())
                    favorite_symbols = favorite_data.get('symbols', [])
        except:
            favorite_symbols = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", 
                              "BNB-USDT-SWAP", "XRP-USDT-SWAP", "DOGE-USDT-SWAP"]
        
        if len(favorite_symbols) < 6:
            return jsonify({
                'success': False,
                'error': f"常用币不足6个，当前: {len(favorite_symbols)}个"
            })
        
        # 3. 获取市场行情，选择涨幅前6
        ticker_path = '/api/v5/market/tickers?instType=SWAP'
        ticker_response = requests.get(base_url + ticker_path, timeout=10)
        ticker_result = ticker_response.json()
        
        if ticker_result.get('code') != '0':
            return jsonify({
                'success': False,
                'error': f"获取行情失败: {ticker_result.get('msg')}"
            })
        
        # 筛选常用币并按涨跌幅排序
        symbols_data = []
        for ticker in ticker_result.get('data', []):
            inst_id = ticker.get('instId', '')
            if inst_id in favorite_symbols:
                change_24h = float(ticker.get('changeRate24h', 0)) * 100
                price = float(ticker.get('last', 0))
                symbols_data.append({
                    'instId': inst_id,
                    'price': price,
                    'change': change_24h
                })
        
        # 按涨跌幅排序，取前6
        symbols_data.sort(key=lambda x: x['change'], reverse=True)
        top6_symbols = symbols_data[:6]
        
        if len(top6_symbols) < 6:
            return jsonify({
                'success': False,
                'error': f"可用币种不足6个，当前: {len(top6_symbols)}个"
            })
        
        # 4. 计算每个币的开仓参数
        margin_per_coin = balance * percent_per_coin / 100  # 保证金
        contract_value_per_coin = margin_per_coin * 10  # 合约价值（10x杠杆）
        
        # 5. 批量下单
        success_count = 0
        fail_count = 0
        results = []
        
        for symbol_data in top6_symbols:
            inst_id = symbol_data['instId']
            price = symbol_data['price']
            
            try:
                # 设置杠杆
                leverage = '10'
                pos_side = direction  # long/short
                
                set_leverage_path = '/api/v5/account/set-leverage'
                leverage_body = json.dumps({
                    'instId': inst_id,
                    'lever': leverage,
                    'mgnMode': 'isolated',
                    'posSide': pos_side
                })
                
                leverage_timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                leverage_message = leverage_timestamp + 'POST' + set_leverage_path + leverage_body
                leverage_mac = hmac.new(bytes(secret_key, encoding='utf8'), bytes(leverage_message, encoding='utf-8'), digestmod='sha256')
                leverage_signature = base64.b64encode(leverage_mac.digest()).decode()
                
                leverage_headers = {
                    'OK-ACCESS-KEY': api_key,
                    'OK-ACCESS-SIGN': leverage_signature,
                    'OK-ACCESS-TIMESTAMP': leverage_timestamp,
                    'OK-ACCESS-PASSPHRASE': passphrase,
                    'Content-Type': 'application/json'
                }
                
                requests.post(base_url + set_leverage_path, headers=leverage_headers, data=leverage_body, timeout=10)
                
                # 获取合约规格
                instruments_path = f'/api/v5/public/instruments?instType=SWAP&instId={inst_id}'
                instruments_response = requests.get(base_url + instruments_path, timeout=5)
                instruments_data = instruments_response.json()
                
                ct_val = 0.1  # 默认值
                if instruments_data.get('code') == '0' and instruments_data.get('data'):
                    ct_val = float(instruments_data['data'][0].get('ctVal', 0.1))
                
                # 计算合约张数
                usdt_per_contract = ct_val * price
                contracts_count = max(1, round(contract_value_per_coin / usdt_per_contract))
                
                # 下单
                request_path = '/api/v5/trade/order'
                side = 'buy' if direction == 'long' else 'sell'
                
                order_params = {
                    'instId': inst_id,
                    'tdMode': 'isolated',
                    'side': side,
                    'posSide': pos_side,
                    'ordType': 'market',
                    'sz': str(int(contracts_count))
                }
                
                body = json.dumps(order_params)
                timestamp = datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
                message = timestamp + 'POST' + request_path + body
                mac = hmac.new(bytes(secret_key, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
                signature = base64.b64encode(mac.digest()).decode()
                
                headers = {
                    'OK-ACCESS-KEY': api_key,
                    'OK-ACCESS-SIGN': signature,
                    'OK-ACCESS-TIMESTAMP': timestamp,
                    'OK-ACCESS-PASSPHRASE': passphrase,
                    'Content-Type': 'application/json'
                }
                
                response = requests.post(base_url + request_path, headers=headers, data=body, timeout=10)
                result = response.json()
                
                print(f"[批量开仓] {inst_id} 下单响应: {result}")
                
                if result.get('code') == '0':
                    success_count += 1
                    results.append(f"✅ {inst_id}: 成功 ({contracts_count}张)")
                else:
                    fail_count += 1
                    error_msg = result.get('msg', '未知错误')
                    error_code = result.get('code', '未知代码')
                    results.append(f"❌ {inst_id}: [{error_code}] {error_msg}")
                    print(f"[批量开仓] {inst_id} 失败: code={error_code}, msg={error_msg}")
                    
            except Exception as e:
                fail_count += 1
                results.append(f"❌ {inst_id}: {str(e)}")
                print(f"[批量开仓] {inst_id} 异常: {str(e)}")
        
        return jsonify({
            'success': success_count > 0,
            'successCount': success_count,
            'failCount': fail_count,
            'results': results
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/okx-trading/hedge-order', methods=['POST'])
def hedge_order_from_event():
    """从重大事件页面触发的对冲开仓"""
    try:
        data = request.get_json()
        hedge_direction = data.get('hedgeDirection', 'short')  # short=空单配多单, long=多单配空单
        
        # TODO: 这里需要获取账户配置和持仓信息
        # 临时方案：返回提示信息，要求用户在交易页面配置账户后再使用
        
        return jsonify({
            'success': False,
            'error': '此功能需要先在交易页面配置API密钥。\n\n请前往"OKX交易系统"页面配置账户后使用。',
            'redirect': '/okx-trading'
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


# ==================== 27币涨跌幅追踪系统 API ====================

@app.route('/api/coin-change-tracker/latest', methods=['GET'])
def get_coin_change_latest():
    """获取最新的27币涨跌幅数据"""
    try:
        from datetime import datetime, timezone, timedelta
        from pathlib import Path
        
        data_dir = Path('data/coin_change_tracker')
        if not data_dir.exists():
            return jsonify({
                'success': False,
                'error': '数据目录不存在'
            })
        
        # 获取当前日期
        beijing_time = datetime.now(timezone(timedelta(hours=8)))
        date_str = beijing_time.strftime('%Y%m%d')
        
        # 读取今天的数据文件
        data_file = data_dir / f'coin_change_{date_str}.jsonl'
        
        if not data_file.exists():
            return jsonify({
                'success': False,
                'error': f'今天的数据文件不存在: {date_str}'
            })
        
        # 读取最后一条记录
        with open(data_file, 'r') as f:
            lines = f.readlines()
            if lines:
                latest = json.loads(lines[-1].strip())
                return jsonify({
                    'success': True,
                    'data': latest
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '数据文件为空'
                })
                
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/coin-change-tracker/history', methods=['GET'])
def get_coin_change_history():
    """获取27币涨跌幅历史数据"""
    try:
        from datetime import datetime, timezone, timedelta
        from pathlib import Path
        
        # 获取参数
        date_str = request.args.get('date')  # YYYYMMDD
        limit = int(request.args.get('limit', 1440))  # 默认1天的数据（1440分钟）
        
        data_dir = Path('data/coin_change_tracker')
        if not data_dir.exists():
            return jsonify({
                'success': False,
                'error': '数据目录不存在'
            })
        
        # 如果没有指定日期，使用今天
        if not date_str:
            beijing_time = datetime.now(timezone(timedelta(hours=8)))
            date_str = beijing_time.strftime('%Y%m%d')
        
        # 读取数据文件
        data_file = data_dir / f'coin_change_{date_str}.jsonl'
        
        if not data_file.exists():
            return jsonify({
                'success': False,
                'error': f'数据文件不存在: {date_str}'
            })
        
        # 读取数据
        records = []
        with open(data_file, 'r') as f:
            lines = f.readlines()
            # 取最后limit条
            for line in lines[-limit:]:
                if line.strip():
                    records.append(json.loads(line.strip()))
        
        return jsonify({
            'success': True,
            'date': date_str,
            'count': len(records),
            'data': records
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/coin-change-tracker/baseline', methods=['GET'])
def get_coin_change_baseline():
    """获取当天的基准价"""
    try:
        from datetime import datetime, timezone, timedelta
        from pathlib import Path
        
        # 获取参数
        date_str = request.args.get('date')
        
        data_dir = Path('data/coin_change_tracker')
        if not data_dir.exists():
            return jsonify({
                'success': False,
                'error': '数据目录不存在'
            })
        
        # 如果没有指定日期，使用今天
        if not date_str:
            beijing_time = datetime.now(timezone(timedelta(hours=8)))
            date_str = beijing_time.strftime('%Y%m%d')
        
        # 读取基准价文件
        baseline_file = data_dir / f'baseline_{date_str}.json'
        
        if not baseline_file.exists():
            return jsonify({
                'success': False,
                'error': f'基准价文件不存在: {date_str}'
            })
        
        with open(baseline_file, 'r') as f:
            baseline_data = json.load(f)
        
        return jsonify({
            'success': True,
            'data': baseline_data
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


@app.route('/api/coin-change-tracker/reset-baseline', methods=['POST'])
def reset_coin_change_baseline():
    """手动重置基准价（使用当前价格）"""
    try:
        from datetime import datetime, timezone, timedelta
        from pathlib import Path
        import requests
        
        # 获取当前时间
        beijing_time = datetime.now(timezone(timedelta(hours=8)))
        date_str = beijing_time.strftime('%Y%m%d')
        
        # 获取当前币价
        symbols = [
            'BTC-USDT-SWAP', 'ETH-USDT-SWAP', 'XRP-USDT-SWAP',
            'BNB-USDT-SWAP', 'SOL-USDT-SWAP', 'LTC-USDT-SWAP',
            'DOGE-USDT-SWAP', 'SUI-USDT-SWAP', 'TRX-USDT-SWAP',
            'TON-USDT-SWAP', 'ETC-USDT-SWAP', 'BCH-USDT-SWAP',
            'HBAR-USDT-SWAP', 'XLM-USDT-SWAP', 'FIL-USDT-SWAP',
            'LINK-USDT-SWAP', 'CRO-USDT-SWAP', 'DOT-USDT-SWAP',
            'AAVE-USDT-SWAP', 'UNI-USDT-SWAP', 'NEAR-USDT-SWAP',
            'APT-USDT-SWAP', 'CFX-USDT-SWAP', 'CRV-USDT-SWAP',
            'STX-USDT-SWAP', 'LDO-USDT-SWAP', 'TAO-USDT-SWAP'
        ]
        
        # 从OKX获取当前价格
        url = 'https://www.okx.com/api/v5/market/tickers?instType=SWAP'
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get('code') != '0':
            return jsonify({
                'success': False,
                'error': f"获取行情失败: {data.get('msg')}"
            })
        
        prices = {}
        for ticker in data.get('data', []):
            inst_id = ticker.get('instId')
            if inst_id in symbols:
                prices[inst_id] = float(ticker.get('last', 0))
        
        if len(prices) < 27:
            return jsonify({
                'success': False,
                'error': f"获取币价不完整，只获取到{len(prices)}个"
            })
        
        # 保存基准价
        data_dir = Path('data/coin_change_tracker')
        data_dir.mkdir(parents=True, exist_ok=True)
        baseline_file = data_dir / f'baseline_{date_str}.json'
        
        baseline_data = {
            'date': date_str,
            'timestamp': beijing_time.isoformat(),
            'prices': prices,
            'note': '手动重置'
        }
        
        with open(baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': '基准价已重置',
            'date': date_str,
            'timestamp': beijing_time.isoformat(),
            'count': len(prices)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        })


# ==================== Flask App 启动入口 ====================
if __name__ == '__main__':
    # 🔥 启动时预热逃顶信号缓存（智能采样：历史15分钟/点，最近3天全量）
    print('🔥 开始预热逃顶信号缓存...')
    import time
    from datetime import datetime, timedelta
    start_time = time.time()
    
    try:
        sys.path.insert(0, '/home/user/webapp')
        from escape_signal_jsonl_manager import EscapeSignalJSONLManager
        
        manager = EscapeSignalJSONLManager()
        today = datetime.now().strftime('%Y-%m-%d')
        three_days_ago = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        
        # 获取所有数据（从2026-01-03开始）
        all_data = manager.get_stats_range(start_date='2026-01-03', end_date=today)
        
        if not all_data:
            print('⚠️ 未获取到任何数据，跳过缓存预热')
        else:
            # 分离历史数据与最近3天数据
            historical_data = []
            recent_data = []
            three_days_ago_dt = datetime.now() - timedelta(days=3)
            
            for record in all_data:
                try:
                    stat_time = datetime.fromisoformat(record['stat_time'].replace('Z', '+00:00').replace('+00:00', ''))
                    if stat_time < three_days_ago_dt:
                        historical_data.append(record)
                    else:
                        recent_data.append(record)
                except:
                    pass
            
            # 历史数据按15分钟采样
            sampled_historical = []
            if historical_data:
                historical_data.sort(key=lambda x: x['stat_time'])
                last_sampled_time = None
                
                for record in historical_data:
                    try:
                        current_time = datetime.fromisoformat(record['stat_time'].replace('Z', '+00:00').replace('+00:00', ''))
                        
                        if last_sampled_time is None or (current_time - last_sampled_time).total_seconds() >= 900:  # 15分钟
                            sampled_historical.append(record)
                            last_sampled_time = current_time
                    except:
                        pass
            
            # 合并数据
            keypoints_data = sampled_historical + recent_data
            
            print(f'📊 数据采样统计:')
            print(f'历史数据: {len(historical_data)} → {len(sampled_historical)} (15分钟/点)')
            print(f'最近3天: {len(recent_data)} (全量)')
            print(f'总计: {len(all_data)} → {len(keypoints_data)}')
            
            # 计算统计信息
            max_signal_24h = max((r.get('signal_24h_count', 0) for r in keypoints_data), default=0)
            max_signal_2h = max((r.get('signal_2h_count', 0) for r in keypoints_data), default=0)
            
            # 缓存结果
            _escape_signal_cache['data'] = {
                'success': True,
                'keypoints': keypoints_data,
                'keypoint_count': len(keypoints_data),
                'total_records': len(all_data),
                'max_signal_24h': max_signal_24h,
                'max_signal_2h': max_signal_2h,
                'compression_rate': f"{len(keypoints_data) / len(all_data) * 100:.1f}%" if all_data else "0%",
                'data_range': f"{all_data[0]['stat_time']} ~ {all_data[-1]['stat_time']}" if all_data else "无数据"
            }
            _escape_signal_cache['timestamp'] = time.time()
            
            elapsed = time.time() - start_time
            print(f'✅ 缓存预热完成！耗时: {elapsed:.2f}秒, 数据点数量: {len(keypoints_data)}')
    
    except Exception as e:
        print(f'⚠️ 缓存预热失败: {e}')
    
    app.run(host='0.0.0.0', port=5000, debug=False)
