#!/usr/bin/env node
/**
 * 沙箱API服务器 - 用于处理系统维护命令
 * 端口: 3001
 */

const http = require('http');
const { exec } = require('child_process');
const path = require('path');

const PORT = 3001;
const SCRIPT_PATH = path.join(__dirname, 'sandbox-api.sh');

// CORS配置
function setCORSHeaders(res) {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

// 执行脚本命令
function executeScript(command) {
    return new Promise((resolve, reject) => {
        exec(`${SCRIPT_PATH} ${command}`, { timeout: 30000 }, (error, stdout, stderr) => {
            if (error) {
                reject({ success: false, message: stderr || error.message });
            } else {
                try {
                    // 尝试解析JSON输出
                    const result = JSON.parse(stdout);
                    resolve(result);
                } catch (e) {
                    resolve({ success: true, message: stdout.trim() });
                }
            }
        });
    });
}

// 创建服务器
const server = http.createServer(async (req, res) => {
    setCORSHeaders(res);

    // 处理OPTIONS预检请求
    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    const url = req.url;
    console.log(`[${new Date().toISOString()}] ${req.method} ${url}`);

    try {
        // 磁盘状态
        if (url === '/api/sandbox/disk-status' && req.method === 'GET') {
            const result = await executeScript('disk-status');
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result));
            return;
        }

        // 清理磁盘
        if (url === '/api/sandbox/clean-disk' && req.method === 'POST') {
            const result = await executeScript('clean-disk');
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result));
            return;
        }

        // 修复端口
        if (url === '/api/sandbox/fix-ports' && req.method === 'POST') {
            const result = await executeScript('fix-ports');
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result));
            return;
        }

        // 重启服务
        if (url === '/api/sandbox/restart-services' && req.method === 'POST') {
            const result = await executeScript('restart-services');
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result));
            return;
        }

        // 修复Vite代理
        if (url === '/api/sandbox/fix-vite-proxy' && req.method === 'POST') {
            const result = await executeScript('fix-vite-proxy');
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result));
            return;
        }

        // 重新构建项目
        if (url === '/api/sandbox/rebuild' && req.method === 'POST') {
            const result = await executeScript('rebuild');
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(result));
            return;
        }

        // 健康检查
        if (url === '/api/sandbox/health' && req.method === 'GET') {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ 
                status: 'ok', 
                timestamp: new Date().toISOString() 
            }));
            return;
        }

        // 404
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ 
            success: false, 
            message: 'API endpoint not found' 
        }));

    } catch (error) {
        console.error('Error:', error);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ 
            success: false, 
            message: error.message || 'Internal server error' 
        }));
    }
});

// 启动服务器
server.listen(PORT, '0.0.0.0', () => {
    console.log(`✅ 沙箱API服务器已启动`);
    console.log(`   监听端口: ${PORT}`);
    console.log(`   脚本路径: ${SCRIPT_PATH}`);
    console.log(`   启动时间: ${new Date().toISOString()}`);
    console.log(`\n可用端点:`);
    console.log(`   GET  /api/sandbox/health`);
    console.log(`   GET  /api/sandbox/disk-status`);
    console.log(`   POST /api/sandbox/clean-disk`);
    console.log(`   POST /api/sandbox/fix-ports`);
    console.log(`   POST /api/sandbox/restart-services`);
    console.log(`   POST /api/sandbox/fix-vite-proxy`);
});

// 错误处理
server.on('error', (error) => {
    console.error('❌ 服务器错误:', error);
    process.exit(1);
});

// 优雅关闭
process.on('SIGTERM', () => {
    console.log('收到SIGTERM信号，正在关闭服务器...');
    server.close(() => {
        console.log('服务器已关闭');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    console.log('\n收到SIGINT信号，正在关闭服务器...');
    server.close(() => {
        console.log('服务器已关闭');
        process.exit(0);
    });
});
