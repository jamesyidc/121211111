#!/usr/bin/env python3
"""
Web演示界面 - 展示查询和图表功能
"""
from flask import Flask, render_template_string, request, send_file, jsonify
import sqlite3
from datetime import datetime
import os
import sys

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>加密货币数据查询系统</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Microsoft YaHei', 'Arial', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }
        h1 {
            color: #667eea;
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 40px;
            font-size: 1.1em;
        }
        .section {
            margin-bottom: 40px;
            padding: 30px;
            background: #f8f9fa;
            border-radius: 15px;
            border: 2px solid #e0e0e0;
        }
        .section h2 {
            color: #764ba2;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        .input-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: bold;
            font-size: 1.1em;
        }
        input[type="text"], input[type="datetime-local"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 10px rgba(102, 126, 234, 0.3);
        }
        .button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 40px;
            border: none;
            border-radius: 10px;
            font-size: 1.1em;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: bold;
        }
        .button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        .button:active {
            transform: translateY(0);
        }
        .result {
            margin-top: 30px;
            padding: 25px;
            background: white;
            border-radius: 10px;
            border-left: 5px solid #667eea;
        }
        .result pre {
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            border-radius: 10px;
            overflow: hidden;
        }
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: bold;
        }
        tr:hover {
            background: #f5f5f5;
        }
        .priority-1 { color: #ff0000; font-weight: bold; }
        .priority-2 { color: #ff6600; font-weight: bold; }
        .priority-3 { color: #ff9900; }
        .priority-4 { color: #ffcc00; }
        .priority-5 { color: #99cc00; }
        .priority-6 { color: #666; }
        .stat-box {
            display: inline-block;
            padding: 10px 20px;
            margin: 10px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            font-weight: bold;
        }
        .chart-container {
            margin-top: 30px;
            text-align: center;
        }
        .chart-container img {
            max-width: 100%;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .info-box {
            background: #e3f2fd;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #2196f3;
            margin-bottom: 20px;
        }
        .priority-legend {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        .priority-item {
            padding: 15px;
            border-radius: 8px;
            background: white;
            border: 2px solid #e0e0e0;
        }
        .loading {
            text-align: center;
            padding: 20px;
            color: #667eea;
            font-size: 1.2em;
        }
        .feature-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .feature-card {
            background: white;
            padding: 25px;
            border-radius: 15px;
            border: 2px solid #e0e0e0;
            transition: all 0.3s;
        }
        .feature-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            border-color: #667eea;
        }
        .feature-card h3 {
            color: #764ba2;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 加密货币数据查询系统</h1>
        <p class="subtitle">历史数据查询 | 4指标曲线图 | 优先级计算</p>

        <!-- 功能介绍 -->
        <div class="section">
            <h2>✨ 核心功能</h2>
            <div class="feature-grid">
                <div class="feature-card">
                    <h3>📊 历史数据查询</h3>
                    <p>按日期+时间查询历史数据，无需设置开始/结束时间，支持多种格式</p>
                </div>
                <div class="feature-card">
                    <h3>📈 4指标曲线图</h3>
                    <p>急涨、急跌、差值、计次四条曲线，清晰展示市场趋势</p>
                </div>
                <div class="feature-card">
                    <h3>🎯 优先级计算</h3>
                    <p>基于最高占比和最低占比自动计算6个优先级等级</p>
                </div>
            </div>
        </div>

        <!-- 查询功能 -->
        <div class="section">
            <h2>🔍 查询历史数据</h2>
            <div class="info-box">
                <strong>支持的格式：</strong> 2025-12-06 13:30 或 2025-12-06_1330
            </div>
            <div class="input-group">
                <label for="query_time">输入查询时间：</label>
                <input type="text" id="query_time" placeholder="例如: 2025-12-06 13:42" value="2025-12-06 13:42">
            </div>
            <button class="button" onclick="queryData()">🔍 查询数据</button>
            <div id="query_result" class="result" style="display:none;"></div>
        </div>

        <!-- 优先级说明 -->
        <div class="section">
            <h2>🎯 优先级等级说明</h2>
            <div class="priority-legend">
                <div class="priority-item">
                    <strong class="priority-1">等级1</strong><br>
                    最高占比 > 90%<br>
                    最低占比 > 120%
                </div>
                <div class="priority-item">
                    <strong class="priority-2">等级2</strong><br>
                    最高占比 > 80%<br>
                    最低占比 > 120%
                </div>
                <div class="priority-item">
                    <strong class="priority-3">等级3</strong><br>
                    最高占比 > 90%<br>
                    最低占比 > 110%
                </div>
                <div class="priority-item">
                    <strong class="priority-4">等级4</strong><br>
                    最高占比 > 70%<br>
                    最低占比 > 120%
                </div>
                <div class="priority-item">
                    <strong class="priority-5">等级5</strong><br>
                    最高占比 > 80%<br>
                    最低占比 > 110%
                </div>
                <div class="priority-item">
                    <strong class="priority-6">等级6</strong><br>
                    最高占比 < 80%<br>
                    最低占比 < 110%
                </div>
            </div>
        </div>

        <!-- 数据库统计 -->
        <div class="section">
            <h2>📊 数据库统计</h2>
            <button class="button" onclick="loadStats()">📈 查看统计</button>
            <div id="stats_result" class="result" style="display:none;"></div>
        </div>
    </div>

    <script>
        function queryData() {
            const time = document.getElementById('query_time').value;
            const resultDiv = document.getElementById('query_result');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div class="loading">⏳ 正在查询数据...</div>';
            
            fetch('/api/query?time=' + encodeURIComponent(time))
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        resultDiv.innerHTML = '<div style="color:red;">❌ ' + data.error + '</div>';
                    } else {
                        let html = '<h3>查询结果</h3>';
                        html += '<div class="stat-box">时间: ' + data.snapshot_time + '</div>';
                        html += '<div class="stat-box">急涨: ' + data.rush_up + '</div>';
                        html += '<div class="stat-box">急跌: ' + data.rush_down + '</div>';
                        html += '<div class="stat-box">差值: ' + data.diff + '</div>';
                        html += '<div class="stat-box">计次: ' + data.count + '</div>';
                        html += '<div class="stat-box">状态: ' + data.status + '</div>';
                        
                        if (data.coins && data.coins.length > 0) {
                            html += '<table><thead><tr><th>序号</th><th>币种</th><th>涨幅</th><th>24h涨幅</th><th>最高占比</th><th>最低占比</th><th>优先级</th></tr></thead><tbody>';
                            data.coins.slice(0, 20).forEach((coin, idx) => {
                                const priorityClass = 'priority-' + coin.priority.replace('等级', '');
                                html += '<tr>';
                                html += '<td>' + (idx + 1) + '</td>';
                                html += '<td><strong>' + coin.symbol + '</strong></td>';
                                html += '<td>' + coin.change.toFixed(2) + '%</td>';
                                html += '<td>' + coin.change_24h.toFixed(2) + '%</td>';
                                html += '<td>' + coin.ratio1 + '</td>';
                                html += '<td>' + coin.ratio2 + '</td>';
                                html += '<td class="' + priorityClass + '">' + coin.priority + '</td>';
                                html += '</tr>';
                            });
                            html += '</tbody></table>';
                            if (data.coins.length > 20) {
                                html += '<p style="margin-top:15px;color:#666;">... 还有 ' + (data.coins.length - 20) + ' 个币种</p>';
                            }
                        }
                        resultDiv.innerHTML = html;
                    }
                })
                .catch(error => {
                    resultDiv.innerHTML = '<div style="color:red;">❌ 查询失败: ' + error + '</div>';
                });
        }

        function loadStats() {
            const resultDiv = document.getElementById('stats_result');
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<div class="loading">⏳ 正在加载统计...</div>';
            
            fetch('/api/stats')
                .then(response => response.json())
                .then(data => {
                    let html = '<h3>数据库统计</h3>';
                    html += '<p><strong>总快照数:</strong> ' + data.total_snapshots + '</p>';
                    html += '<p><strong>总币种记录数:</strong> ' + data.total_coins + '</p>';
                    html += '<p><strong>最新数据时间:</strong> ' + data.latest_time + '</p>';
                    html += '<p><strong>最早数据时间:</strong> ' + data.earliest_time + '</p>';
                    
                    if (data.priority_stats) {
                        html += '<h4 style="margin-top:20px;">优先级分布（最新数据）:</h4>';
                        html += '<table><thead><tr><th>优先级</th><th>币种数量</th></tr></thead><tbody>';
                        for (let i = 1; i <= 6; i++) {
                            const level = '等级' + i;
                            const count = data.priority_stats[level] || 0;
                            const priorityClass = 'priority-' + i;
                            html += '<tr><td class="' + priorityClass + '">' + level + '</td><td>' + count + '</td></tr>';
                        }
                        html += '</tbody></table>';
                    }
                    resultDiv.innerHTML = html;
                })
                .catch(error => {
                    resultDiv.innerHTML = '<div style="color:red;">❌ 加载失败: ' + error + '</div>';
                });
        }

        // 页面加载时自动加载统计
        window.onload = function() {
            loadStats();
        };
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/query')
def api_query():
    query_time = request.args.get('time', '')
    if not query_time:
        return jsonify({'error': '请提供查询时间'})
    
    # 格式化时间
    if '_' in query_time:
        query_time = query_time.replace('_', ' ')
        parts = query_time.split()
        if len(parts) == 2 and len(parts[1]) == 4:
            query_time = f"{parts[0]} {parts[1][:2]}:{parts[1][2:]}"
    
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                snapshot_time, rush_up, rush_down, diff, count, ratio, status
            FROM crypto_snapshots
            WHERE snapshot_time LIKE ?
            ORDER BY snapshot_time DESC
            LIMIT 1
        """, (f"{query_time}%",))
        
        snapshot = cursor.fetchone()
        
        if not snapshot:
            conn.close()
            return jsonify({'error': f'未找到 {query_time} 的数据'})
        
        snapshot_time, rush_up, rush_down, diff, count, ratio, status = snapshot
        
        cursor.execute("""
            SELECT 
                symbol, change, change_24h, ratio1, ratio2, priority_level
            FROM crypto_coin_data
            WHERE snapshot_time = ?
            ORDER BY index_order ASC
        """, (snapshot_time,))
        
        coins = []
        for row in cursor.fetchall():
            coins.append({
                'symbol': row[0],
                'change': row[1],
                'change_24h': row[2],
                'ratio1': row[3],
                'ratio2': row[4],
                'priority': row[5]
            })
        
        conn.close()
        
        return jsonify({
            'snapshot_time': snapshot_time,
            'rush_up': rush_up,
            'rush_down': rush_down,
            'diff': diff,
            'count': count,
            'ratio': ratio,
            'status': status,
            'coins': coins
        })
    
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/stats')
def api_stats():
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM crypto_snapshots")
        total_snapshots = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM crypto_coin_data")
        total_coins = cursor.fetchone()[0]
        
        cursor.execute("SELECT snapshot_time FROM crypto_snapshots ORDER BY snapshot_time DESC LIMIT 1")
        latest = cursor.fetchone()
        latest_time = latest[0] if latest else 'N/A'
        
        cursor.execute("SELECT snapshot_time FROM crypto_snapshots ORDER BY snapshot_time ASC LIMIT 1")
        earliest = cursor.fetchone()
        earliest_time = earliest[0] if earliest else 'N/A'
        
        # 优先级统计（最新数据）
        if latest:
            cursor.execute("""
                SELECT priority_level, COUNT(*) 
                FROM crypto_coin_data 
                WHERE snapshot_time = ?
                GROUP BY priority_level
            """, (latest_time,))
            priority_stats = {row[0]: row[1] for row in cursor.fetchall()}
        else:
            priority_stats = {}
        
        conn.close()
        
        return jsonify({
            'total_snapshots': total_snapshots,
            'total_coins': total_coins,
            'latest_time': latest_time,
            'earliest_time': earliest_time,
            'priority_stats': priority_stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
