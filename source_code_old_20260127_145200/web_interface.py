#!/usr/bin/env python3
"""
加密货币数据可视化界面 - 仿照用户提供的格式
"""
from flask import Flask, render_template_string, request, jsonify
import sqlite3
from datetime import datetime, timedelta
import json

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>加密货币数据分析系统</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            background: #1a1d2e;
            color: #fff;
            padding: 20px;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-size: 24px;
        }
        .status-bar {
            background: #252b3f;
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            gap: 30px;
            align-items: center;
            flex-wrap: wrap;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .status-label {
            color: #8b93a7;
        }
        .status-value {
            font-weight: bold;
            font-size: 18px;
        }
        .status-value.rise {
            color: #00d4aa;
        }
        .status-value.fall {
            color: #ff4d4f;
        }
        .datetime-selector {
            background: #252b3f;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            gap: 15px;
            align-items: center;
        }
        .datetime-selector label {
            color: #8b93a7;
        }
        .datetime-selector input {
            background: #1a1d2e;
            border: 1px solid #404654;
            color: #fff;
            padding: 8px 15px;
            border-radius: 5px;
            font-size: 14px;
        }
        .datetime-selector button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
            padding: 8px 25px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
        }
        .datetime-selector button:hover {
            opacity: 0.9;
        }
        .data-table {
            background: #252b3f;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            background: #1a1d2e;
            padding: 12px 8px;
            text-align: center;
            font-size: 13px;
            color: #8b93a7;
            border-bottom: 2px solid #404654;
            white-space: nowrap;
        }
        td {
            padding: 10px 8px;
            text-align: center;
            border-bottom: 1px solid #323649;
            font-size: 13px;
            white-space: nowrap;
        }
        tr:hover {
            background: #2a3147;
        }
        .symbol-cell {
            font-weight: bold;
            font-size: 14px;
        }
        .rise-tag {
            background: #ff4d4f;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
        }
        .fall-tag {
            background: #00d4aa;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
        }
        .neutral-tag {
            background: #404654;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
        }
        .positive {
            color: #ff4d4f;
        }
        .negative {
            color: #00d4aa;
        }
        .priority-1 { color: #ff0000; font-weight: bold; }
        .priority-2 { color: #ff6600; font-weight: bold; }
        .priority-3 { color: #ff9900; }
        .priority-4 { color: #ffcc00; }
        .priority-5 { color: #99cc00; }
        .priority-6 { color: #8b93a7; }
        .chart-section {
            background: #252b3f;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .chart-title {
            font-size: 18px;
            margin-bottom: 15px;
            color: #fff;
        }
        #trendChart {
            width: 100%;
            height: 400px;
        }
        .legend {
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            justify-content: center;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .legend-color {
            width: 30px;
            height: 3px;
            border-radius: 2px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #252b3f;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-card .label {
            color: #8b93a7;
            font-size: 13px;
            margin-bottom: 8px;
        }
        .stat-card .value {
            font-size: 24px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>🚀 加密货币数据分析系统</h1>
            <div id="currentTime"></div>
        </div>

        <!-- 状态栏 -->
        <div class="status-bar">
            <div class="status-item">
                <span class="status-label">运算时间:</span>
                <span class="status-value" id="calcTime">--</span>
            </div>
            <div class="status-item">
                <span class="status-label">急涨:</span>
                <span class="status-value rise" id="rushUp">0</span>
            </div>
            <div class="status-item">
                <span class="status-label">急跌:</span>
                <span class="status-value fall" id="rushDown">0</span>
            </div>
            <div class="status-item">
                <span class="status-label">状态:</span>
                <span class="status-value" id="status">--</span>
            </div>
            <div class="status-item">
                <span class="status-label">比值:</span>
                <span class="status-value" id="ratio">0</span>
            </div>
            <div class="status-item">
                <span class="status-label">差值:</span>
                <span class="status-value" id="diff">0</span>
            </div>
            <div class="status-item">
                <span class="status-label">计次:</span>
                <span class="status-value" id="count">0</span>
            </div>
            <div class="status-item">
                <span class="status-label">24h涨幅≥10%:</span>
                <span class="status-value rise" id="rise10">0</span>
            </div>
            <div class="status-item">
                <span class="status-label">24h跌幅≤-10%:</span>
                <span class="status-value fall" id="fall10">0</span>
            </div>
        </div>

        <!-- 日期时间选择器 -->
        <div class="datetime-selector">
            <label>选择日期:</label>
            <input type="date" id="queryDate" value="">
            <label>时间:</label>
            <input type="time" id="queryTime" value="">
            <button onclick="queryData()">🔍 查询</button>
            <button onclick="loadLatest()">📊 最新数据</button>
        </div>

        <!-- 币种数据表格 -->
        <div class="data-table">
            <table>
                <thead>
                    <tr>
                        <th>序号</th>
                        <th>币名</th>
                        <th>涨跌</th>
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
                        <th>优先级</th>
                    </tr>
                </thead>
                <tbody id="dataTable">
                    <tr><td colspan="15" style="padding:30px;color:#8b93a7;">请选择日期时间查询数据</td></tr>
                </tbody>
            </table>
        </div>

        <!-- 趋势图 -->
        <div class="chart-section">
            <div class="chart-title">急涨/急跌历史趋势图</div>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background:#ff4d4f;"></div>
                    <span>急涨</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background:#00d4aa;"></div>
                    <span>急跌</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background:#ffa940; border: 2px dashed #ffa940;"></div>
                    <span>差值(急涨-急跌)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background:#1890ff;"></div>
                    <span>计次</span>
                </div>
            </div>
            <div id="trendChart"></div>
        </div>
    </div>

    <script>
        // 初始化图表
        const chart = echarts.init(document.getElementById('trendChart'));
        
        // 更新当前时间
        function updateTime() {
            const now = new Date();
            document.getElementById('currentTime').textContent = 
                now.toLocaleString('zh-CN', {year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit'});
        }
        setInterval(updateTime, 1000);
        updateTime();

        // 初始化日期时间选择器
        const now = new Date();
        document.getElementById('queryDate').valueAsDate = now;
        document.getElementById('queryTime').value = now.toTimeString().substr(0, 5);

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
                    loadChartData(date);
                })
                .catch(error => {
                    alert('查询失败: ' + error);
                });
        }

        // 加载最新数据
        function loadLatest() {
            fetch('/api/latest')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert('❌ ' + data.error);
                        return;
                    }
                    updateUI(data);
                    const date = data.snapshot_time.split(' ')[0];
                    loadChartData(date);
                })
                .catch(error => {
                    alert('加载失败: ' + error);
                });
        }

        // 更新UI
        function updateUI(data) {
            document.getElementById('calcTime').textContent = data.snapshot_time;
            document.getElementById('rushUp').textContent = data.rush_up;
            document.getElementById('rushDown').textContent = data.rush_down;
            document.getElementById('status').textContent = data.status;
            document.getElementById('ratio').textContent = data.ratio;
            document.getElementById('diff').textContent = data.diff;
            document.getElementById('count').textContent = data.count;
            document.getElementById('rise10').textContent = data.rise_10 || 0;
            document.getElementById('fall10').textContent = data.fall_10 || 0;
            
            // 更新表格
            const tbody = document.getElementById('dataTable');
            if (data.coins && data.coins.length > 0) {
                let html = '';
                data.coins.forEach((coin, idx) => {
                    const changeClass = coin.change > 0 ? 'positive' : (coin.change < 0 ? 'negative' : '');
                    const change24Class = coin.change_24h > 0 ? 'positive' : (coin.change_24h < 0 ? 'negative' : '');
                    const rushUpTag = coin.rush_up > 0 ? '<span class="rise-tag">急涨</span>' : '';
                    const rushDownTag = coin.rush_down > 0 ? '<span class="fall-tag">急跌</span>' : '';
                    const priorityClass = 'priority-' + coin.priority.replace('等级', '');
                    
                    html += '<tr>';
                    html += '<td>' + (idx + 1) + '</td>';
                    html += '<td class="symbol-cell">' + coin.symbol + '</td>';
                    html += '<td class="' + changeClass + '">' + coin.change.toFixed(2) + '%</td>';
                    html += '<td>' + coin.rush_up + '</td>';
                    html += '<td>' + coin.rush_down + '</td>';
                    html += '<td>' + coin.update_time + '</td>';
                    html += '<td>' + coin.high_price.toFixed(2) + '</td>';
                    html += '<td>' + coin.high_time + '</td>';
                    html += '<td class="negative">' + coin.decline.toFixed(2) + '</td>';
                    html += '<td class="' + change24Class + '">' + coin.change_24h.toFixed(2) + '</td>';
                    html += '<td>' + coin.rank + '</td>';
                    html += '<td>' + coin.current_price.toFixed(4) + '</td>';
                    html += '<td>' + coin.ratio1 + '</td>';
                    html += '<td>' + coin.ratio2 + '</td>';
                    html += '<td class="' + priorityClass + '">' + coin.priority + '</td>';
                    html += '</tr>';
                });
                tbody.innerHTML = html;
            } else {
                tbody.innerHTML = '<tr><td colspan="15" style="padding:30px;color:#8b93a7;">暂无数据</td></tr>';
            }
        }

        // 加载图表数据
        function loadChartData(date) {
            fetch('/api/chart?date=' + encodeURIComponent(date))
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        console.error(data.error);
                        return;
                    }
                    
                    const option = {
                        backgroundColor: 'transparent',
                        tooltip: {
                            trigger: 'axis',
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            borderColor: '#404654',
                            textStyle: { color: '#fff' }
                        },
                        grid: {
                            left: '3%',
                            right: '5%',
                            bottom: '3%',
                            containLabel: true
                        },
                        xAxis: {
                            type: 'category',
                            data: data.times,
                            axisLine: { lineStyle: { color: '#404654' } },
                            axisLabel: { color: '#8b93a7', rotate: 45 }
                        },
                        yAxis: [
                            {
                                type: 'value',
                                name: '数量',
                                nameTextStyle: { color: '#8b93a7' },
                                axisLine: { lineStyle: { color: '#404654' } },
                                axisLabel: { color: '#8b93a7' },
                                splitLine: { lineStyle: { color: '#323649' } }
                            },
                            {
                                type: 'value',
                                name: '计次',
                                nameTextStyle: { color: '#8b93a7' },
                                axisLine: { lineStyle: { color: '#404654' } },
                                axisLabel: { color: '#8b93a7' },
                                splitLine: { show: false }
                            }
                        ],
                        series: [
                            {
                                name: '急涨',
                                type: 'line',
                                data: data.rush_up,
                                smooth: true,
                                itemStyle: { color: '#ff4d4f' },
                                lineStyle: { width: 3 }
                            },
                            {
                                name: '急跌',
                                type: 'line',
                                data: data.rush_down,
                                smooth: true,
                                itemStyle: { color: '#00d4aa' },
                                lineStyle: { width: 3 }
                            },
                            {
                                name: '差值',
                                type: 'line',
                                data: data.diff,
                                smooth: true,
                                itemStyle: { color: '#ffa940' },
                                lineStyle: { width: 2, type: 'dashed' }
                            },
                            {
                                name: '计次',
                                type: 'line',
                                yAxisIndex: 1,
                                data: data.count,
                                smooth: true,
                                itemStyle: { color: '#1890ff' },
                                lineStyle: { width: 2 }
                            }
                        ]
                    };
                    
                    chart.setOption(option);
                })
                .catch(error => {
                    console.error('图表加载失败:', error);
                });
        }

        // 页面加载时获取最新数据
        window.onload = function() {
            loadLatest();
        };

        // 响应式调整
        window.addEventListener('resize', function() {
            chart.resize();
        });
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
                symbol, change, rush_up, rush_down, update_time,
                high_price, high_time, decline, change_24h, rank,
                current_price, ratio1, ratio2, priority_level
            FROM crypto_coin_data
            WHERE snapshot_time = ?
            ORDER BY index_order ASC
        """, (snapshot_time,))
        
        coins = []
        rise_10 = 0
        fall_10 = 0
        
        for row in cursor.fetchall():
            if row[8] >= 10:  # change_24h >= 10
                rise_10 += 1
            elif row[8] <= -10:  # change_24h <= -10
                fall_10 += 1
                
            coins.append({
                'symbol': row[0],
                'change': row[1],
                'rush_up': row[2],
                'rush_down': row[3],
                'update_time': row[4],
                'high_price': row[5],
                'high_time': row[6],
                'decline': row[7],
                'change_24h': row[8],
                'rank': row[9],
                'current_price': row[10],
                'ratio1': row[11],
                'ratio2': row[12],
                'priority': row[13]
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
            'rise_10': rise_10,
            'fall_10': fall_10,
            'coins': coins
        })
    
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/latest')
def api_latest():
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                snapshot_time, rush_up, rush_down, diff, count, ratio, status
            FROM crypto_snapshots
            ORDER BY snapshot_time DESC
            LIMIT 1
        """)
        
        snapshot = cursor.fetchone()
        
        if not snapshot:
            conn.close()
            return jsonify({'error': '数据库中暂无数据'})
        
        snapshot_time, rush_up, rush_down, diff, count, ratio, status = snapshot
        
        cursor.execute("""
            SELECT 
                symbol, change, rush_up, rush_down, update_time,
                high_price, high_time, decline, change_24h, rank,
                current_price, ratio1, ratio2, priority_level
            FROM crypto_coin_data
            WHERE snapshot_time = ?
            ORDER BY index_order ASC
        """, (snapshot_time,))
        
        coins = []
        rise_10 = 0
        fall_10 = 0
        
        for row in cursor.fetchall():
            if row[8] >= 10:
                rise_10 += 1
            elif row[8] <= -10:
                fall_10 += 1
                
            coins.append({
                'symbol': row[0],
                'change': row[1],
                'rush_up': row[2],
                'rush_down': row[3],
                'update_time': row[4],
                'high_price': row[5],
                'high_time': row[6],
                'decline': row[7],
                'change_24h': row[8],
                'rank': row[9],
                'current_price': row[10],
                'ratio1': row[11],
                'ratio2': row[12],
                'priority': row[13]
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
            'rise_10': rise_10,
            'fall_10': fall_10,
            'coins': coins
        })
    
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/chart')
def api_chart():
    date = request.args.get('date', '')
    if not date:
        # 获取最新日期
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT snapshot_time FROM crypto_snapshots ORDER BY snapshot_time DESC LIMIT 1")
        result = cursor.fetchone()
        conn.close()
        if result:
            date = result[0].split(' ')[0]
        else:
            return jsonify({'error': '无数据'})
    
    try:
        conn = sqlite3.connect('crypto_data.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                snapshot_time, rush_up, rush_down, diff, count
            FROM crypto_snapshots
            WHERE snapshot_time LIKE ?
            ORDER BY snapshot_time ASC
        """, (f"{date}%",))
        
        data = cursor.fetchall()
        conn.close()
        
        times = [row[0].split(' ')[1][:5] for row in data]
        rush_up = [row[1] for row in data]
        rush_down = [row[2] for row in data]
        diff = [row[3] for row in data]
        count = [row[4] for row in data]
        
        return jsonify({
            'times': times,
            'rush_up': rush_up,
            'rush_down': rush_down,
            'diff': diff,
            'count': count
        })
    
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
