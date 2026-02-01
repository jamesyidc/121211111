/**
 * 策略匹配调度器 V2（Cloudflare Workers 兼容版本）
 * 
 * 职责：
 * 1. 提供策略匹配执行功能（不依赖 setInterval）
 * 2. 自动清理过期的生产池信号（超过3分钟）
 * 3. 提供统计信息和健康检查
 * 
 * 触发方式：
 * - Cloudflare Cron Triggers（推荐）
 * - API 手动触发
 * - 外部定时任务调用
 */

import { D1Database } from '@cloudflare/workers-types';
import { StrategyMatchingService } from './strategyMatchingService';

export class StrategyMatchingSchedulerV2 {
  private matchingService: StrategyMatchingService;
  
  // 统计信息（存储在内存中，重启后重置）
  private static stats = {
    totalRuns: 0,
    successfulRuns: 0,
    failedRuns: 0,
    totalMatched: 0,
    lastRunTime: null as Date | null,
    lastError: null as string | null,
    isRunning: false
  };

  // 最后执行时间戳（避免重复执行）
  private static lastExecutionTime: number = 0;
  private static MIN_EXECUTION_INTERVAL_MS = 25000; // 最小间隔25秒

  constructor(private db: D1Database) {
    this.matchingService = new StrategyMatchingService(db);
  }

  /**
   * 执行策略匹配（节流保护）
   * 返回 true 表示执行了，false 表示跳过
   */
  async execute(): Promise<{ executed: boolean; reason?: string; matchedCount?: number }> {
    const now = Date.now();
    const timeSinceLastExecution = now - StrategyMatchingSchedulerV2.lastExecutionTime;

    // 节流保护：避免25秒内重复执行
    if (timeSinceLastExecution < StrategyMatchingSchedulerV2.MIN_EXECUTION_INTERVAL_MS) {
      const waitSeconds = Math.ceil((StrategyMatchingSchedulerV2.MIN_EXECUTION_INTERVAL_MS - timeSinceLastExecution) / 1000);
      return {
        executed: false,
        reason: `执行间隔太短，请等待 ${waitSeconds} 秒`
      };
    }

    // 防止并发执行
    if (StrategyMatchingSchedulerV2.stats.isRunning) {
      return {
        executed: false,
        reason: '策略匹配正在执行中'
      };
    }

    try {
      StrategyMatchingSchedulerV2.stats.isRunning = true;
      StrategyMatchingSchedulerV2.lastExecutionTime = now;
      
      await this.executeMatchingInternal();
      
      return {
        executed: true,
        matchedCount: StrategyMatchingSchedulerV2.stats.totalMatched
      };
    } finally {
      StrategyMatchingSchedulerV2.stats.isRunning = false;
    }
  }

  /**
   * 执行策略匹配（内部方法）
   */
  private async executeMatchingInternal(): Promise<void> {
    StrategyMatchingSchedulerV2.stats.totalRuns++;
    StrategyMatchingSchedulerV2.stats.lastRunTime = new Date();

    try {
      console.log(`\n🔄 [匹配调度V2] 第 ${StrategyMatchingSchedulerV2.stats.totalRuns} 次扫描开始...`);

      // 1. 执行策略匹配
      const results = await this.matchingService.scanAndMatchSignals();
      
      const matchedCount = results.filter(r => r.matched).length;
      StrategyMatchingSchedulerV2.stats.totalMatched += matchedCount;
      StrategyMatchingSchedulerV2.stats.successfulRuns++;

      console.log(`✅ [匹配调度V2] 扫描完成: ${matchedCount} 个信号已匹配`);

      // 2. 清理过期信号
      await this.cleanupExpiredSignals();

      // 3. 打印统计信息
      await this.printStatistics();

    } catch (error) {
      StrategyMatchingSchedulerV2.stats.failedRuns++;
      StrategyMatchingSchedulerV2.stats.lastError = error instanceof Error ? error.message : String(error);
      console.error('❌ [匹配调度V2] 扫描失败:', error);
      throw error;
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
      console.log(`   总运行次数: ${StrategyMatchingSchedulerV2.stats.totalRuns}`);
      console.log(`   成功/失败: ${StrategyMatchingSchedulerV2.stats.successfulRuns}/${StrategyMatchingSchedulerV2.stats.failedRuns}`);
      console.log(`   累计匹配: ${StrategyMatchingSchedulerV2.stats.totalMatched} 个信号`);
      console.log(`   待匹配信号: ${matchingStats.unmatched_signals} 个`);
      console.log(`   今日已匹配: ${matchingStats.matched_today} 个`);
      console.log(`   生产池待执行: ${(productionPoolCount as any)?.count || 0} 个`);
      console.log(`   执行中持仓: ${(executingPoolCount as any)?.count || 0} 个`);
      console.log(`   最后运行: ${StrategyMatchingSchedulerV2.stats.lastRunTime?.toISOString()}`);

    } catch (error) {
      console.error('❌ [统计信息] 获取失败:', error);
    }
  }

  /**
   * 获取调度器状态
   */
  static getStatus(): any {
    return {
      isRunning: StrategyMatchingSchedulerV2.stats.isRunning,
      stats: StrategyMatchingSchedulerV2.stats,
      lastExecutionTime: StrategyMatchingSchedulerV2.lastExecutionTime 
        ? new Date(StrategyMatchingSchedulerV2.lastExecutionTime).toISOString()
        : null,
      nextAvailableTime: StrategyMatchingSchedulerV2.lastExecutionTime 
        ? new Date(StrategyMatchingSchedulerV2.lastExecutionTime + StrategyMatchingSchedulerV2.MIN_EXECUTION_INTERVAL_MS).toISOString()
        : '立即可用'
    };
  }

  /**
   * 重置统计信息
   */
  static resetStats(): void {
    StrategyMatchingSchedulerV2.stats = {
      totalRuns: 0,
      successfulRuns: 0,
      failedRuns: 0,
      totalMatched: 0,
      lastRunTime: null,
      lastError: null,
      isRunning: false
    };
    StrategyMatchingSchedulerV2.lastExecutionTime = 0;
  }
}
