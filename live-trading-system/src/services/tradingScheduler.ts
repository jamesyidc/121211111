/**
 * 交易调度器
 * 负责定时执行信号检测、持仓监控等任务
 */

import { D1Database } from '@cloudflare/workers-types';
import { SignalDetectionService } from './signalDetectionService';
import { SignalPoolManager } from './signalPoolManager';
import { StrategyLibraryService } from './strategyLibraryService';

export interface SchedulerConfig {
  scan_interval_seconds: number;      // 扫描K线间隔（秒）
  monitor_interval_seconds: number;   // 监控持仓间隔（秒）
  auto_trading_enabled: boolean;      // 是否自动交易
  cleanup_enabled: boolean;           // 是否自动清理过期信号
}

export class TradingScheduler {
  private scanTimer: NodeJS.Timeout | null = null;
  private monitorTimer: NodeJS.Timeout | null = null;
  private cleanupTimer: NodeJS.Timeout | null = null;
  
  private signalDetector: SignalDetectionService;
  private poolManager: SignalPoolManager;
  private strategyService: StrategyLibraryService;
  
  private config: SchedulerConfig = {
    scan_interval_seconds: 30,      // 30秒扫描一次
    monitor_interval_seconds: 60,   // 1分钟监控一次
    auto_trading_enabled: false,    // 默认关闭自动交易
    cleanup_enabled: true           // 默认开启清理
  };
  
  constructor(private db: D1Database) {
    this.signalDetector = new SignalDetectionService(db);
    this.poolManager = new SignalPoolManager(db);
    this.strategyService = new StrategyLibraryService(db);
  }

  /**
   * 启动调度器
   */
  async start(config?: Partial<SchedulerConfig>): Promise<void> {
    if (config) {
      this.config = { ...this.config, ...config };
    }
    
    console.log('🚀 交易调度器启动...');
    console.log('⚙️ 配置:', this.config);
    
    // 启动信号扫描任务
    this.startSignalScanning();
    
    // 启动持仓监控任务
    this.startPositionMonitoring();
    
    // 启动清理任务
    if (this.config.cleanup_enabled) {
      this.startCleanupTask();
    }
    
    console.log('✅ 调度器已启动');
  }

  /**
   * 停止调度器
   */
  stop(): void {
    console.log('🛑 停止调度器...');
    
    if (this.scanTimer) {
      clearInterval(this.scanTimer);
      this.scanTimer = null;
    }
    
    if (this.monitorTimer) {
      clearInterval(this.monitorTimer);
      this.monitorTimer = null;
    }
    
    if (this.cleanupTimer) {
      clearInterval(this.cleanupTimer);
      this.cleanupTimer = null;
    }
    
    console.log('✅ 调度器已停止');
  }

  /**
   * 启动信号扫描（每30秒）
   */
  private startSignalScanning(): void {
    console.log(`📡 启动信号扫描任务 (间隔: ${this.config.scan_interval_seconds}秒)`);
    
    // 立即执行一次
    this.scanForSignals();
    
    // 定时执行
    this.scanTimer = setInterval(
      () => this.scanForSignals(),
      this.config.scan_interval_seconds * 1000
    );
  }

  /**
   * 启动持仓监控（每1分钟）
   */
  private startPositionMonitoring(): void {
    console.log(`👁️ 启动持仓监控任务 (间隔: ${this.config.monitor_interval_seconds}秒)`);
    
    // 立即执行一次
    this.monitorPositions();
    
    // 定时执行
    this.monitorTimer = setInterval(
      () => this.monitorPositions(),
      this.config.monitor_interval_seconds * 1000
    );
  }

  /**
   * 启动清理任务（每5分钟）
   */
  private startCleanupTask(): void {
    console.log('🧹 启动清理任务 (间隔: 5分钟)');
    
    this.cleanupTimer = setInterval(
      () => this.cleanup(),
      5 * 60 * 1000
    );
  }

  /**
   * 扫描K线并检测信号
   */
  private async scanForSignals(): Promise<void> {
    try {
      console.log('🔍 [扫描任务] 开始扫描买入信号...');
      
      // 1. 检测买入信号
      const detectedSignals = await this.signalDetector.scanForBuySignals();
      
      if (detectedSignals.length === 0) {
        console.log('ℹ️ [扫描任务] 未检测到新信号');
        return;
      }
      
      console.log(`📊 [扫描任务] 检测到 ${detectedSignals.length} 个信号`);
      
      // 2. 将信号添加到生产池
      for (const signal of detectedSignals) {
        // 查找匹配的策略
        const strategies = await this.findMatchingStrategies(signal.signal_code);
        
        for (const strategy of strategies) {
          const result = await this.poolManager.addToProductionPool(
            signal,
            strategy.strategy_code
          );
          
          if (result.success) {
            console.log(`✅ [扫描任务] 信号已加入生产池: ${result.poolId}`);
            
            // 3. 如果开启自动交易，立即执行买入
            if (this.config.auto_trading_enabled) {
              await this.autoExecuteBuy(result.poolId!);
            }
          } else {
            console.log(`⚠️ [扫描任务] 信号被拒绝: ${result.reason}`);
          }
        }
      }
      
    } catch (error) {
      console.error('❌ [扫描任务] 执行失败:', error);
    }
  }

  /**
   * 监控持仓并触发卖出
   */
  private async monitorPositions(): Promise<void> {
    try {
      console.log('👁️ [监控任务] 开始监控持仓...');
      
      // 1. 扫描卖出信号
      const sellSignals = await this.signalDetector.scanForSellSignals();
      
      if (sellSignals.length === 0) {
        console.log('ℹ️ [监控任务] 无卖出触发');
        return;
      }
      
      console.log(`📊 [监控任务] 触发 ${sellSignals.length} 个卖出`);
      
      // 2. 执行卖出
      for (const sell of sellSignals) {
        const result = await this.poolManager.executeSell(
          sell.execution_id,
          sell.reason,
          sell.exit_price,
          sell.signal_code
        );
        
        if (result.success) {
          console.log(`✅ [监控任务] 卖出已完成: ${result.completionId}`);
        } else {
          console.log(`⚠️ [监控任务] 卖出失败: ${result.reason}`);
        }
      }
      
      // 3. 更新持仓的当前价格和盈亏
      await this.updatePositionPrices();
      
    } catch (error) {
      console.error('❌ [监控任务] 执行失败:', error);
    }
  }

  /**
   * 清理过期数据
   */
  private async cleanup(): Promise<void> {
    try {
      console.log('🧹 [清理任务] 开始清理...');
      
      // 清理过期信号
      const count = await this.poolManager.cleanupExpiredSignals();
      
      if (count > 0) {
        console.log(`✅ [清理任务] 清理了 ${count} 个过期信号`);
      }
      
    } catch (error) {
      console.error('❌ [清理任务] 执行失败:', error);
    }
  }

  /**
   * 自动执行买入
   */
  private async autoExecuteBuy(poolId: string): Promise<void> {
    console.log(`🤖 [自动交易] 执行买入: ${poolId}`);
    
    const result = await this.poolManager.executeBuy(poolId);
    
    if (result.success) {
      console.log(`✅ [自动交易] 买入成功: ${result.executionId}`);
    } else {
      console.log(`⚠️ [自动交易] 买入失败: ${result.reason}`);
    }
  }

  /**
   * 查找匹配信号的策略
   */
  private async findMatchingStrategies(signalCode: string): Promise<any[]> {
    const result = await this.db
      .prepare(`
        SELECT *
        FROM strategy_library
        WHERE entry_signal_code = ?
          AND is_enabled = 1
        ORDER BY priority DESC
      `)
      .bind(signalCode)
      .all();
    
    return result.results;
  }

  /**
   * 更新持仓的当前价格
   */
  private async updatePositionPrices(): Promise<void> {
    // TODO: 实现更新逻辑
    // 获取所有持仓 → 获取当前价格 → 更新数据库
  }

  /**
   * 获取调度器状态
   */
  getStatus(): any {
    return {
      running: !!(this.scanTimer && this.monitorTimer),
      config: this.config,
      timers: {
        scan: !!this.scanTimer,
        monitor: !!this.monitorTimer,
        cleanup: !!this.cleanupTimer
      }
    };
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<SchedulerConfig>): void {
    this.config = { ...this.config, ...config };
    console.log('⚙️ 配置已更新:', this.config);
    
    // 重启调度器以应用新配置
    this.stop();
    this.start();
  }
}
