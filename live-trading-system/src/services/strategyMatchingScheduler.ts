/**
 * 策略匹配调度器
 * 
 * 职责：
 * 1. 每30秒执行一次策略匹配扫描
 * 2. 自动清理过期的生产池信号（超过3分钟）
 * 3. 提供统计信息和健康检查
 */

import { D1Database } from '@cloudflare/workers-types';
import { StrategyMatchingService } from './strategyMatchingService';

export class StrategyMatchingScheduler {
  private isRunning: boolean = false;
  private intervalId: NodeJS.Timeout | null = null;
  private matchingService: StrategyMatchingService;
  
  // 统计信息
  private stats = {
    totalRuns: 0,
    successfulRuns: 0,
    failedRuns: 0,
    totalMatched: 0,
    lastRunTime: null as Date | null,
    lastError: null as string | null
  };

  constructor(private db: D1Database) {
    this.matchingService = new StrategyMatchingService(db);
  }

  /**
   * 启动调度器（每30秒执行一次）
   */
  start(): void {
    if (this.isRunning) {
      console.log('⚠️ [匹配调度] 调度器已在运行中');
      return;
    }

    this.isRunning = true;
    console.log('🚀 [匹配调度] 策略匹配调度器已启动（间隔：30秒）');

    // 立即执行一次
    this.executeMatching();

    // 设置定时任务
    this.intervalId = setInterval(() => {
      this.executeMatching();
    }, 30 * 1000); // 30秒
  }

  /**
   * 停止调度器
   */
  stop(): void {
    if (!this.isRunning) {
      console.log('⚠️ [匹配调度] 调度器未运行');
      return;
    }

    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    this.isRunning = false;
    console.log('🛑 [匹配调度] 策略匹配调度器已停止');
  }

  /**
   * 执行策略匹配
   */
  private async executeMatching(): Promise<void> {
    this.stats.totalRuns++;
    this.stats.lastRunTime = new Date();

    try {
      console.log(`\n🔄 [匹配调度] 第 ${this.stats.totalRuns} 次扫描开始...`);

      // 1. 执行策略匹配
      const results = await this.matchingService.scanAndMatchSignals();
      
      const matchedCount = results.filter(r => r.matched).length;
      this.stats.totalMatched += matchedCount;
      this.stats.successfulRuns++;

      console.log(`✅ [匹配调度] 扫描完成: ${matchedCount} 个信号已匹配`);

      // 2. 清理过期信号（每次扫描都执行）
      await this.cleanupExpiredSignals();

      // 3. 打印统计信息
      await this.printStatistics();

    } catch (error) {
      this.stats.failedRuns++;
      this.stats.lastError = error instanceof Error ? error.message : String(error);
      console.error('❌ [匹配调度] 扫描失败:', error);
    }
  }

  /**
   * 清理过期的生产池信号
   */
  private async cleanupExpiredSignals(): Promise<void> {
    try {
      const result = await this.db
        .prepare(`
          UPDATE strategy_signal_pool
          SET status = 'REJECTED',
              rejection_reason = '信号已过期（超过3分钟）',
              updated_at = CURRENT_TIMESTAMP
          WHERE status = 'PENDING'
            AND expires_at < CURRENT_TIMESTAMP
        `)
        .run();

      const cleanedCount = result.meta?.changes || 0;
      
      if (cleanedCount > 0) {
        console.log(`🧹 [生产池清理] 已清理 ${cleanedCount} 个过期信号`);
      }

    } catch (error) {
      console.error('❌ [生产池清理] 清理失败:', error);
    }
  }

  /**
   * 打印统计信息
   */
  private async printStatistics(): Promise<void> {
    try {
      // 获取匹配服务的统计信息
      const matchingStats = await this.matchingService.getMatchingStatistics();

      // 获取生产池统计
      const productionPoolCount = await this.db
        .prepare(`SELECT COUNT(*) as count FROM strategy_signal_pool WHERE status = 'PENDING'`)
        .first();

      const executingPoolCount = await this.db
        .prepare(`SELECT COUNT(*) as count FROM executing_strategy_pool`)
        .first();

      console.log(`\n📊 [统计信息]`);
      console.log(`   总运行次数: ${this.stats.totalRuns}`);
      console.log(`   成功/失败: ${this.stats.successfulRuns}/${this.stats.failedRuns}`);
      console.log(`   累计匹配: ${this.stats.totalMatched} 个信号`);
      console.log(`   待匹配信号: ${matchingStats.unmatched_signals} 个`);
      console.log(`   今日已匹配: ${matchingStats.matched_today} 个`);
      console.log(`   生产池待执行: ${(productionPoolCount as any)?.count || 0} 个`);
      console.log(`   执行中持仓: ${(executingPoolCount as any)?.count || 0} 个`);
      console.log(`   最后运行: ${this.stats.lastRunTime?.toISOString()}`);

    } catch (error) {
      console.error('❌ [统计信息] 获取失败:', error);
    }
  }

  /**
   * 获取调度器状态
   */
  getStatus(): any {
    return {
      isRunning: this.isRunning,
      stats: this.stats
    };
  }

  /**
   * 手动触发一次匹配（用于测试）
   */
  async triggerManually(): Promise<void> {
    console.log('🔧 [匹配调度] 手动触发策略匹配...');
    await this.executeMatching();
  }
}
