/**
 * 精确时间点调度服务
 * 用于在每5分钟的固定时间点（0分10秒、5分10秒、10分10秒等）触发K线数据同步
 */

interface PreciseSchedulerConfig {
  enabled: boolean;
  intervalMinutes: number; // 间隔分钟数（默认5分钟）
  offsetSeconds: number; // 偏移秒数（默认10秒）
  endpoint: string;
}

export class PreciseSchedulerService {
  private config: PreciseSchedulerConfig;
  private timerId: NodeJS.Timeout | null = null;
  private isRunning: boolean = false;

  constructor(config: Partial<PreciseSchedulerConfig> = {}) {
    this.config = {
      enabled: config.enabled ?? true,
      intervalMinutes: config.intervalMinutes ?? 5, // 5分钟间隔
      offsetSeconds: config.offsetSeconds ?? 10, // 在第10秒执行
      endpoint: config.endpoint ?? 'http://localhost:3000/api/kline/sync/auto'
    };
  }

  /**
   * 计算下一次执行时间
   * @returns 距离下次执行的毫秒数
   */
  private calculateNextExecutionDelay(): number {
    const now = new Date();
    const currentMinutes = now.getMinutes();
    const currentSeconds = now.getSeconds();
    const currentMilliseconds = now.getMilliseconds();
    
    const { intervalMinutes, offsetSeconds } = this.config;
    
    // 计算当前是在哪个周期内
    const currentCycle = Math.floor(currentMinutes / intervalMinutes);
    
    // 计算下一个周期的开始分钟
    let nextMinute = (currentCycle + 1) * intervalMinutes;
    
    // 如果当前分钟数小于下一个执行点，且当前秒数小于offsetSeconds
    // 那么可以在本周期内执行
    const targetMinuteInCurrentCycle = currentCycle * intervalMinutes;
    if (currentMinutes === targetMinuteInCurrentCycle && currentSeconds < offsetSeconds) {
      nextMinute = targetMinuteInCurrentCycle;
    }
    
    // 如果下一个执行分钟超过60，需要到下一个小时
    const nextHour = nextMinute >= 60 ? 1 : 0;
    nextMinute = nextMinute % 60;
    
    // 创建下一次执行的时间
    const nextExecution = new Date(now);
    nextExecution.setHours(now.getHours() + nextHour);
    nextExecution.setMinutes(nextMinute);
    nextExecution.setSeconds(offsetSeconds);
    nextExecution.setMilliseconds(0);
    
    // 计算延迟毫秒数
    let delay = nextExecution.getTime() - now.getTime();
    
    // 如果计算出的延迟为负数或非常小，说明需要等到下一个周期
    if (delay <= 0) {
      nextExecution.setMinutes(nextExecution.getMinutes() + intervalMinutes);
      delay = nextExecution.getTime() - now.getTime();
    }
    
    return delay;
  }

  /**
   * 启动精确时间点调度
   */
  start(): void {
    if (!this.config.enabled) {
      console.log('📅 精确时间点调度已禁用');
      return;
    }

    if (this.isRunning) {
      console.log('⚠️  精确时间点调度已在运行中');
      return;
    }

    this.isRunning = true;
    console.log(`🚀 启动K线精确时间点同步调度器`);
    console.log(`⏱️  配置: 每${this.config.intervalMinutes}分钟在第${this.config.offsetSeconds}秒执行`);
    console.log(`📍 示例: 0:00:${this.config.offsetSeconds}, 0:${this.config.intervalMinutes}:${this.config.offsetSeconds}, 0:${this.config.intervalMinutes * 2}:${this.config.offsetSeconds}...`);
    
    this.scheduleNext();
  }

  /**
   * 安排下一次执行
   */
  private scheduleNext(): void {
    if (!this.isRunning) {
      return;
    }

    const delay = this.calculateNextExecutionDelay();
    const nextExecutionTime = new Date(Date.now() + delay);
    
    console.log(`⏳ 下次执行时间: ${nextExecutionTime.toLocaleString('zh-CN', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    })} (${(delay / 1000).toFixed(0)}秒后)`);

    this.timerId = setTimeout(async () => {
      await this.executeSync();
      this.scheduleNext(); // 执行完后安排下一次
    }, delay);
  }

  /**
   * 停止调度
   */
  stop(): void {
    if (this.timerId) {
      clearTimeout(this.timerId);
      this.timerId = null;
      this.isRunning = false;
      console.log('🛑 精确时间点调度已停止');
    }
  }

  /**
   * 执行同步
   */
  private async executeSync(): Promise<void> {
    const now = new Date();
    const startTime = Date.now();
    const timeString = now.toLocaleString('zh-CN', { 
      hour12: false,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
    
    console.log(`\n⏰ [${timeString}] 开始精确时间点K线数据同步...`);

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
   * 立即执行一次同步（不影响调度）
   */
  async executeNow(): Promise<void> {
    console.log('🔄 手动触发K线数据同步...');
    await this.executeSync();
  }

  /**
   * 获取运行状态
   */
  getStatus(): { 
    isRunning: boolean; 
    config: PreciseSchedulerConfig;
    nextExecutionTime: string | null;
  } {
    let nextExecutionTime: string | null = null;
    
    if (this.isRunning) {
      const delay = this.calculateNextExecutionDelay();
      const nextTime = new Date(Date.now() + delay);
      nextExecutionTime = nextTime.toLocaleString('zh-CN', { 
        hour12: false,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      });
    }

    return {
      isRunning: this.isRunning,
      config: { ...this.config },
      nextExecutionTime
    };
  }
}
