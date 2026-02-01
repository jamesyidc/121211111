#!/usr/bin/env node

/**
 * PM2 Monitor API Server
 * Standalone Express server for PM2 monitoring
 * Port: 9000
 */

const express = require('express');
const { exec } = require('child_process');
const { promisify } = require('util');
const cors = require('cors');

const execAsync = promisify(exec);
const app = express();
const PORT = process.env.PM2_MONITOR_PORT || 9000;

// Middleware
app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'PM2 Monitor API', port: PORT });
});

// Get PM2 process list
app.get('/api/pm2/list', async (req, res) => {
  try {
    const { stdout } = await execAsync('pm2 jlist');
    const processes = JSON.parse(stdout || '[]');
    
    res.json({
      success: true,
      processes,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('PM2 list error:', error);
    res.status(500).json({
      success: false,
      error: error.message,
      processes: []
    });
  }
});

// Get PM2 process details
app.get('/api/pm2/describe/:name', async (req, res) => {
  try {
    const { name } = req.params;
    const { stdout } = await execAsync(`pm2 describe ${name} --json`);
    const details = JSON.parse(stdout || '[]');
    
    res.json({
      success: true,
      process: details[0] || null
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Get PM2 logs
app.get('/api/pm2/logs/:name', async (req, res) => {
  try {
    const { name } = req.params;
    const lines = req.query.lines || 50;
    
    const { stdout } = await execAsync(`pm2 logs ${name} --nostream --lines ${lines}`);
    const logs = stdout.split('\n').filter(line => line.trim());
    
    res.json({
      success: true,
      logs,
      processName: name
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message,
      logs: []
    });
  }
});

// Restart process
app.post('/api/pm2/restart/:name', async (req, res) => {
  try {
    const { name } = req.params;
    await execAsync(`pm2 restart ${name}`);
    
    res.json({
      success: true,
      message: `Process ${name} restarted successfully`
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Stop process
app.post('/api/pm2/stop/:name', async (req, res) => {
  try {
    const { name } = req.params;
    await execAsync(`pm2 stop ${name}`);
    
    res.json({
      success: true,
      message: `Process ${name} stopped successfully`
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Start process
app.post('/api/pm2/start/:name', async (req, res) => {
  try {
    const { name } = req.params;
    await execAsync(`pm2 start ${name}`);
    
    res.json({
      success: true,
      message: `Process ${name} started successfully`
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Delete process
app.post('/api/pm2/delete/:name', async (req, res) => {
  try {
    const { name } = req.params;
    await execAsync(`pm2 delete ${name}`);
    
    res.json({
      success: true,
      message: `Process ${name} deleted successfully`
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Get PM2 metrics
app.get('/api/pm2/metrics', async (req, res) => {
  try {
    const { stdout } = await execAsync('pm2 jlist');
    const processes = JSON.parse(stdout || '[]');
    
    const metrics = {
      total: processes.length,
      online: processes.filter(p => p.pm2_env?.status === 'online').length,
      stopped: processes.filter(p => p.pm2_env?.status === 'stopped').length,
      errored: processes.filter(p => p.pm2_env?.status === 'errored').length,
      totalMemory: processes.reduce((sum, p) => sum + (p.monit?.memory || 0), 0),
      totalCpu: processes.reduce((sum, p) => sum + (p.monit?.cpu || 0), 0),
      totalRestarts: processes.reduce((sum, p) => sum + (p.pm2_env?.restart_time || 0), 0),
      processes: processes.map(p => ({
        name: p.name,
        status: p.pm2_env?.status,
        cpu: p.monit?.cpu,
        memory: p.monit?.memory,
        uptime: p.pm2_env?.pm_uptime,
        restarts: p.pm2_env?.restart_time
      }))
    };
    
    res.json({
      success: true,
      metrics,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// PM2 save
app.post('/api/pm2/save', async (req, res) => {
  try {
    await execAsync('pm2 save');
    
    res.json({
      success: true,
      message: 'PM2 configuration saved successfully'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// PM2 resurrect
app.post('/api/pm2/resurrect', async (req, res) => {
  try {
    await execAsync('pm2 resurrect');
    
    res.json({
      success: true,
      message: 'PM2 processes resurrected successfully'
    });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`
╔══════════════════════════════════════╗
║   PM2 Monitor API Server             ║
║   Port: ${PORT}                         ║
║   Status: ✅ Running                  ║
╚══════════════════════════════════════╝

API Endpoints:
  GET  /health
  GET  /api/pm2/list
  GET  /api/pm2/describe/:name
  GET  /api/pm2/logs/:name
  GET  /api/pm2/metrics
  POST /api/pm2/restart/:name
  POST /api/pm2/stop/:name
  POST /api/pm2/start/:name
  POST /api/pm2/delete/:name
  POST /api/pm2/save
  POST /api/pm2/resurrect

Frontend: http://localhost:${PORT}/monitor
  `);
});

// Serve static frontend
app.use('/monitor', express.static(__dirname + '/public'));
