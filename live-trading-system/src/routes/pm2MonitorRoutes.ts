/**
 * PM2 Monitor API Routes
 * Provides API endpoints for PM2 process monitoring and management
 */

import type { D1Database } from '@cloudflare/workers-types';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * Setup PM2 routes
 */
export function setupPM2Routes(app: any) {
  
  // Get PM2 process list
  app.get('/api/pm2/list', async (c: any) => {
    try {
      const { stdout } = await execAsync('pm2 jlist');
      const processes = JSON.parse(stdout || '[]');
      
      return c.json({
        success: true,
        processes,
        timestamp: new Date().toISOString()
      });
    } catch (error: any) {
      console.error('PM2 list error:', error);
      return c.json({
        success: false,
        error: error.message,
        processes: []
      }, 500);
    }
  });

  // Get PM2 process details
  app.get('/api/pm2/describe/:name', async (c: any) => {
    try {
      const name = c.req.param('name');
      const { stdout } = await execAsync(`pm2 describe ${name} --json`);
      const details = JSON.parse(stdout || '[]');
      
      return c.json({
        success: true,
        process: details[0] || null
      });
    } catch (error: any) {
      return c.json({
        success: false,
        error: error.message
      }, 500);
    }
  });

  // Get PM2 logs
  app.get('/api/pm2/logs/:name', async (c: any) => {
    try {
      const name = c.req.param('name');
      const lines = c.req.query('lines') || 50;
      
      const { stdout } = await execAsync(`pm2 logs ${name} --nostream --lines ${lines}`);
      const logs = stdout.split('\n').filter(line => line.trim());
      
      return c.json({
        success: true,
        logs,
        processName: name
      });
    } catch (error: any) {
      return c.json({
        success: false,
        error: error.message,
        logs: []
      }, 500);
    }
  });

  // Restart process
  app.post('/api/pm2/restart/:name', async (c: any) => {
    try {
      const name = c.req.param('name');
      await execAsync(`pm2 restart ${name}`);
      
      return c.json({
        success: true,
        message: `Process ${name} restarted successfully`
      });
    } catch (error: any) {
      return c.json({
        success: false,
        error: error.message
      }, 500);
    }
  });

  // Stop process
  app.post('/api/pm2/stop/:name', async (c: any) => {
    try {
      const name = c.req.param('name');
      await execAsync(`pm2 stop ${name}`);
      
      return c.json({
        success: true,
        message: `Process ${name} stopped successfully`
      });
    } catch (error: any) {
      return c.json({
        success: false,
        error: error.message
      }, 500);
    }
  });

  // Start process
  app.post('/api/pm2/start/:name', async (c: any) => {
    try {
      const name = c.req.param('name');
      await execAsync(`pm2 start ${name}`);
      
      return c.json({
        success: true,
        message: `Process ${name} started successfully`
      });
    } catch (error: any) {
      return c.json({
        success: false,
        error: error.message
      }, 500);
    }
  });

  // Delete process
  app.post('/api/pm2/delete/:name', async (c: any) => {
    try {
      const name = c.req.param('name');
      await execAsync(`pm2 delete ${name}`);
      
      return c.json({
        success: true,
        message: `Process ${name} deleted successfully`
      });
    } catch (error: any) {
      return c.json({
        success: false,
        error: error.message
      }, 500);
    }
  });

  // Get system metrics
  app.get('/api/pm2/system', async (c: any) => {
    try {
      // Get system info
      const { stdout: memInfo } = await execAsync('free -m');
      const { stdout: cpuInfo } = await execAsync('top -bn1 | grep "Cpu(s)"');
      const { stdout: diskInfo } = await execAsync('df -h /');
      
      return c.json({
        success: true,
        system: {
          memory: memInfo,
          cpu: cpuInfo,
          disk: diskInfo,
          timestamp: new Date().toISOString()
        }
      });
    } catch (error: any) {
      return c.json({
        success: false,
        error: error.message
      }, 500);
    }
  });

  // PM2 save
  app.post('/api/pm2/save', async (c: any) => {
    try {
      await execAsync('pm2 save');
      
      return c.json({
        success: true,
        message: 'PM2 configuration saved successfully'
      });
    } catch (error: any) {
      return c.json({
        success: false,
        error: error.message
      }, 500);
    }
  });

  // PM2 resurrect
  app.post('/api/pm2/resurrect', async (c: any) => {
    try {
      await execAsync('pm2 resurrect');
      
      return c.json({
        success: true,
        message: 'PM2 processes resurrected successfully'
      });
    } catch (error: any) {
      return c.json({
        success: false,
        error: error.message
      }, 500);
    }
  });

  // Get PM2 environment info
  app.get('/api/pm2/env/:name', async (c: any) => {
    try {
      const name = c.req.param('name');
      const { stdout } = await execAsync(`pm2 env ${name}`);
      
      return c.json({
        success: true,
        environment: stdout
      });
    } catch (error: any) {
      return c.json({
        success: false,
        error: error.message
      }, 500);
    }
  });

  // PM2 monitoring metrics
  app.get('/api/pm2/metrics', async (c: any) => {
    try {
      const { stdout } = await execAsync('pm2 jlist');
      const processes = JSON.parse(stdout || '[]');
      
      const metrics = {
        total: processes.length,
        online: processes.filter((p: any) => p.pm2_env?.status === 'online').length,
        stopped: processes.filter((p: any) => p.pm2_env?.status === 'stopped').length,
        errored: processes.filter((p: any) => p.pm2_env?.status === 'errored').length,
        totalMemory: processes.reduce((sum: number, p: any) => sum + (p.monit?.memory || 0), 0),
        totalCpu: processes.reduce((sum: number, p: any) => sum + (p.monit?.cpu || 0), 0),
        totalRestarts: processes.reduce((sum: number, p: any) => sum + (p.pm2_env?.restart_time || 0), 0),
        processes: processes.map((p: any) => ({
          name: p.name,
          status: p.pm2_env?.status,
          cpu: p.monit?.cpu,
          memory: p.monit?.memory,
          uptime: p.pm2_env?.pm_uptime,
          restarts: p.pm2_env?.restart_time
        }))
      };
      
      return c.json({
        success: true,
        metrics,
        timestamp: new Date().toISOString()
      });
    } catch (error: any) {
      return c.json({
        success: false,
        error: error.message
      }, 500);
    }
  });

  console.log('✅ PM2 Monitor routes registered');
}
