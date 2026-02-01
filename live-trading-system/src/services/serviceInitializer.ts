/**
 * 服务初始化器
 * 
 * 职责：
 * 1. 启动后台服务（策略匹配调度器等）
 * 2. 管理服务的生命周期
 * 3. 提供服务健康检查
 */

import { D1Database } from '@cloudflare/workers-types';
import { StrategyMatchingScheduler } from './strategyMatchingScheduler';

export class ServiceInitializer {
  private static instance: ServiceInitializer | null = null;
  private strategyMatchingScheduler: StrategyMatchingScheduler | null = null;
  private isInitialized: boolean = false;

  private constructor(private db: D1Database) {}

  /**
   * 获取单例实例
   */
  static getInstance(db: D1Database): ServiceInitializer {
    if (!ServiceInitializer.instance) {
      ServiceInitializer.instance = new ServiceInitializer(db);
    }
    return ServiceInitializer.instance;
  }

  /**
   * 初始化所有后台服务
   */
  initialize(): void {
    if (this.isInitialized) {
      console.log('⚠️ [服务初始化] 服务已初始化');
      return;
    }

    console.log('🚀 [服务初始化] 开始初始化后台服务...');

    try {
      // 1. 启动策略匹配调度器
      this.strategyMatchingScheduler = new StrategyMatchingScheduler(this.db);
      this.strategyMatchingScheduler.start();

      this.isInitialized = true;
      console.log('✅ [服务初始化] 所有后台服务已启动');

    } catch (error) {
      console.error('❌ [服务初始化] 初始化失败:', error);
      throw error;
    }
  }

  /**
   * 停止所有后台服务
   */
  shutdown(): void {
    if (!this.isInitialized) {
      console.log('⚠️ [服务初始化] 服务未初始化');
      return;
    }

    console.log('🛑 [服务初始化] 停止所有后台服务...');

    try {
      // 停止策略匹配调度器
      if (this.strategyMatchingScheduler) {
        this.strategyMatchingScheduler.stop();
        this.strategyMatchingScheduler = null;
      }

      this.isInitialized = false;
      console.log('✅ [服务初始化] 所有后台服务已停止');

    } catch (error) {
      console.error('❌ [服务初始化] 停止失败:', error);
    }
  }

  /**
   * 获取服务状态
   */
  getStatus(): any {
    return {
      isInitialized: this.isInitialized,
      services: {
        strategyMatching: this.strategyMatchingScheduler?.getStatus() || null
      }
    };
  }

  /**
   * 手动触发策略匹配
   */
  async triggerStrategyMatching(): Promise<void> {
    if (!this.strategyMatchingScheduler) {
      throw new Error('策略匹配调度器未初始化');
    }
    await this.strategyMatchingScheduler.triggerManually();
  }

  /**
   * 获取策略匹配调度器（用于API调用）
   */
  getStrategyMatchingScheduler(): StrategyMatchingScheduler | null {
    return this.strategyMatchingScheduler;
  }
}
