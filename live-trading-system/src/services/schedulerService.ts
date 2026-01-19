/**
 * 定时任务调度服务
 * 用于自动同步K线数据
 */

interface SchedulerConfig {
  enabled: boolean;
  interval: number; // 毫秒
  endpoint: string;
}

export class SchedulerService {
  private config: SchedulerConfig;
  private timerId: NodeJS.Timeout | null = null;
  private isRunning: boolean = false;

  constructor(config: Partial<SchedulerConfig> = {}) {
    this.config = {
      enabled: config.enabled ?? true,
      interval: config.interval ?? 5 * 60 * 1000, // 默认5分钟
      endpoint: config.endpoint ?? 'http://localhost:3000/api/kline/sync/auto'
    };
  }

  /**
   * 启动定时任务
   */
  start(): void {
    if (!this.config.enabled) {
      console.log('📅 定时任务已禁用');
      return;
    }

    if (this.isRunning) {
      console.log('⚠️  定时任务已在运行中');
      return;
    }

    this.isRunning = true;
    console.log(`🚀 启动K线自动同步定时任务 (间隔: ${this.config.interval / 1000}秒)`);

    // 立即执行一次
    this.executeSync();

    // 设置定时器
    this.timerId = setInterval(() => {
      this.executeSync();
    }, this.config.interval);
  }

  /**
   * 停止定时任务
   */
  stop(): void {
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
      this.isRunning = false;
      console.log('🛑 定时任务已停止');
    }
  }

  /**
   * 执行同步
   */
  private async executeSync(): Promise<void> {
    const startTime = Date.now();
    console.log(`\n⏰ [${new Date().toISOString()}] 开始自动同步K线数据...`);

    try {
      const response = await fetch(this.config.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);

      if (result.success) {
        console.log(`✅ K线数据同步成功 (耗时: ${duration}秒)`);
        console.log(`   - 成功: ${result.summary?.success || 0} 个币种`);
        console.log(`   - 失败: ${result.summary?.failed || 0} 个币种`);
        console.log(`   - 总数: ${result.summary?.total || 0} 个币种`);
      } else {
        console.error(`❌ K线数据同步失败: ${result.error}`);
      }
    } catch (error: any) {
      const duration = ((Date.now() - startTime) / 1000).toFixed(2);
      console.error(`❌ K线数据同步异常 (耗时: ${duration}秒):`, error.message);
    }
  }

  /**
   * 获取运行状态
   */
  getStatus(): { isRunning: boolean; config: SchedulerConfig } {
    return {
      isRunning: this.isRunning,
      config: { ...this.config }
    };
  }
}
