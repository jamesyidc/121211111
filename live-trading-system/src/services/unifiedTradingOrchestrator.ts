/**
 * 三流合一系统协调器
 * 30秒轮询：信号收集 -> 策略匹配 -> 冲突检测 -> 执行监控 -> 平仓处理
 */

import { D1Database } from '@cloudflare/workers-types';
import { TradingSignalService, KLineData } from './tradingSignalService';
import { StrategyLibraryService } from './strategyLibraryService';
import { StrategySignalPoolService } from './strategySignalPoolService';
import { ExecutingStrategyPoolService } from './executingStrategyPoolService';
import { CompletedStrategyPoolService } from './completedStrategyPoolService';
import { TradingAccountService } from './tradingAccountService';

export class UnifiedTradingOrchestrator {
  private signalService: TradingSignalService;
  private strategyService: StrategyLibraryService;
  private poolService: StrategySignalPoolService;
  private executingService: ExecutingStrategyPoolService;
  private completedService: CompletedStrategyPoolService;
  private accountService: TradingAccountService;

  constructor(private db: D1Database) {
    this.signalService = new TradingSignalService(db);
    this.strategyService = new StrategyLibraryService(db);
    this.poolService = new StrategySignalPoolService(db);
    this.executingService = new ExecutingStrategyPoolService(db);
    this.completedService = new CompletedStrategyPoolService(db);
    this.accountService = new TradingAccountService(db);
  }

  /**
   * 主循环：30秒调用一次
   */
  async runTradingCycle(klineData: KLineData[]): Promise<{
    success: boolean;
    newSignals: number;
    matchedStrategies: number;
    executedTrades: number;
    closedPositions: number;
    errors: string[];
  }> {
    const errors: string[] = [];
    let newSignals = 0;
    let matchedStrategies = 0;
    let executedTrades = 0;
    let closedPositions = 0;

    try {
      console.log('🔄 === 三流合一交易周期开始 ===');

      // ===== Phase 1: 信号收集 =====
      console.log('📊 Phase 1: 提取K线信号...');
      const signalResult = await this.signalService.extractAndStoreSignals(klineData);
      newSignals = signalResult.newSignals;
      console.log(`✅ 新信号: ${newSignals}, 重复: ${signalResult.duplicates}`);

      // ===== Phase 2: 策略匹配（仅处理买点信号）=====
      console.log('🎯 Phase 2: 策略匹配...');
      
      // 获取最近的信号（如果有新信号就用新信号，否则检查最近1小时内的信号）
      const signalsToProcess = newSignals > 0 
        ? await this.signalService.getRecentSignals(newSignals)
        : await this.signalService.getRecentSignals(100); // 检查最近100条
      
      // 过滤出1小时内的新鲜买点信号
      const oneHourAgo = Date.now() - 60 * 60 * 1000;
      const buySignals = signalsToProcess.filter(s => 
        s.signal_category === 'BUY_POINT' && s.kline_time > oneHourAgo
      );
      
      console.log(`📋 找到 ${buySignals.length} 个新鲜买点信号（1小时内）`);

      if (buySignals.length > 0) {
        // 获取当前可用账户（优先模拟账户）
        const accounts = await this.accountService.getActiveAccounts('SIMULATION');
        const defaultAccount = accounts.length > 0 ? accounts[0] : undefined;

        for (const signal of buySignals) {
          const strategies = await this.strategyService.findStrategiesByBuySignal(signal.signal_type);
          console.log(`  ${signal.signal_type} (${signal.symbol}): 找到 ${strategies.length} 个策略`);
          
          for (const strategy of strategies) {
            // 传递账户信息用于涨跌幅检查
            const result = await this.poolService.processNewBuySignal(
              signal, 
              strategy,
              defaultAccount?.account_id,
              defaultAccount?.account_type
            );
            if (result.success) {
              matchedStrategies++;
              console.log(`    ✅ 成功匹配策略: ${strategy.strategy_name}`);
            } else {
              console.log(`    ⚠️ 策略未通过: ${result.reason || '未知原因'}`);
            }
          }
        }
        console.log(`✅ 匹配策略: ${matchedStrategies}`);
      } else {
        console.log(`⚠️ 没有新鲜的买点信号需要处理`);
      }

      // ===== Phase 3: 执行待处理信号 =====
      console.log('🚀 Phase 3: 执行待处理信号...');
      const pendingSignals = await this.poolService.getPendingSignals();
      
      for (const poolEntry of pendingSignals) {
        const executed = await this.executeSignal(poolEntry);
        if (executed) {
          executedTrades++;
        }
      }
      console.log(`✅ 已执行: ${executedTrades}`);

      // ===== Phase 4: 监控执行中的持仓 =====
      console.log('👀 Phase 4: 监控执行中持仓...');
      const currentPrices = this.extractPricesFromKLine(klineData);
      const monitorResult = await this.executingService.monitorAllPositions(currentPrices);
      
      console.log(`✅ 监控持仓: ${monitorResult.checked}, 触发退出: ${monitorResult.triggered.length}`);

      // ===== Phase 5: 处理触发的退出 =====
      for (const { executionId, reason } of monitorResult.triggered) {
        const position = await this.executingService.getPosition(executionId);
        if (position && position.current_price) {
          await this.executingService.closePosition(executionId, reason, position.current_price);
          
          // 更新账户余额
          const pnl = position.current_price - position.entry_price;
          const isWin = pnl > 0;
          await this.accountService.unfreezeAndUpdateBalance(
            position.account_id,
            position.entry_price,  // 冻结金额
            pnl,
            isWin
          );
          
          closedPositions++;
        }
      }

      // ===== Phase 6: 检查卖点信号 =====
      console.log('🔔 Phase 6: 检查卖点信号...');
      const sellSignals = klineData.filter(k => 
        k.operation_tip && 
        ['通用卖点', '高抛', '底部平空'].includes(k.operation_tip)
      );

      for (const sellKline of sellSignals) {
        await this.processSellSignal(sellKline, currentPrices.get(sellKline.symbol) || sellKline.close);
      }

      console.log('✅ === 三流合一交易周期完成 ===\n');

      return {
        success: true,
        newSignals,
        matchedStrategies,
        executedTrades,
        closedPositions,
        errors,
      };

    } catch (error: any) {
      console.error('❌ 交易周期错误:', error);
      errors.push(error.message);
      return {
        success: false,
        newSignals,
        matchedStrategies,
        executedTrades,
        closedPositions,
        errors,
      };
    }
  }

  /**
   * 执行单个待处理信号
   */
  private async executeSignal(poolEntry: any): Promise<boolean> {
    try {
      // 1. 获取策略配置
      const strategy = await this.strategyService.getStrategy(poolEntry.strategy_id);
      if (!strategy) {
        console.error(`❌ 策略不存在: ${poolEntry.strategy_id}`);
        return false;
      }

      // 2. 选择账户（优先模拟账户）
      const accounts = await this.accountService.getActiveAccounts('SIMULATION');
      if (accounts.length === 0) {
        console.error('❌ 没有可用的账户');
        return false;
      }

      const account = accounts[0];  // 使用第一个可用账户

      // 3. 检查是否可以开仓
      const canOpen = await this.accountService.canOpenNewPosition(
        account.account_id,
        poolEntry.position_size_usdt
      );

      if (!canOpen.allowed) {
        console.warn(`⚠️ 无法开仓 [${poolEntry.symbol}]: ${canOpen.reason}`);
        return false;
      }

      // 4. 冻结资金
      const frozen = await this.accountService.freezeBalance(
        account.account_id,
        poolEntry.position_size_usdt
      );

      if (!frozen) {
        console.error(`❌ 冻结资金失败 [${poolEntry.symbol}]`);
        return false;
      }

      // 5. 创建执行记录
      const sellSignalTypes = JSON.parse(strategy.sell_signal_types) as string[];
      
      // 🔧 修复: K线数量转换为分钟数
      // max_holding_period 存储的是K线数量，需要乘以K线周期（默认5分钟）
      const KLINE_PERIOD_MINUTES_MAP: Record<string, number> = {
        '1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440,
        'kline': 5, 'minutes': 1  // 兼容性默认值
      };
      
      const periodUnit = strategy.max_holding_period_unit || '5m';
      const periodMinutes = KLINE_PERIOD_MINUTES_MAP[periodUnit] || 5;
      const maxHoldingMinutes = strategy.max_holding_period 
        ? strategy.max_holding_period * periodMinutes 
        : 0;
      
      console.log(`📊 最大持仓设置: ${strategy.max_holding_period}根K线 × ${periodMinutes}分钟/根 = ${maxHoldingMinutes}分钟`);
      
      const executionId = await this.executingService.createExecution({
        poolId: poolEntry.pool_id,
        strategyId: poolEntry.strategy_id,
        signalId: poolEntry.signal_id,
        symbol: poolEntry.symbol,
        accountId: account.account_id,
        accountType: account.account_type,
        entryPrice: poolEntry.entry_price,
        monitoredSellSignals: sellSignalTypes,
        takeProfitPct: strategy.take_profit_pct,
        stopLossPct: strategy.stop_loss_pct,
        trailingStopPct: strategy.trailing_stop_pct,
        maxHoldingMinutes: maxHoldingMinutes,  // ✅ 使用转换后的分钟数
      });

      // 6. 标记信号池为已执行
      await this.poolService.markAsExecuted(
        poolEntry.pool_id,
        account.account_id,
        account.account_type
      );

      console.log(`🚀 开仓成功 [${poolEntry.symbol}]: ${executionId}`);
      return true;

    } catch (error) {
      console.error(`❌ 执行信号失败 [${poolEntry.symbol}]:`, error);
      return false;
    }
  }

  /**
   * 处理卖点信号
   */
  private async processSellSignal(sellKline: KLineData, currentPrice: number): Promise<void> {
    if (!sellKline.operation_tip) return;

    const positions = await this.executingService.getAllExecutingPositions();
    const symbolPositions = positions.filter(p => p.symbol === sellKline.symbol);

    for (const position of symbolPositions) {
      const shouldClose = await this.executingService.checkSellSignal(
        position.execution_id,
        sellKline.operation_tip
      );

      if (shouldClose) {
        await this.executingService.closePosition(
          position.execution_id,
          {
            type: 'SELL_SIGNAL',
            details: `收到卖点信号: ${sellKline.operation_tip}`,
          },
          currentPrice
        );

        // 更新账户余额
        const pnl = currentPrice - position.entry_price;
        const isWin = pnl > 0;
        await this.accountService.unfreezeAndUpdateBalance(
          position.account_id,
          position.entry_price,
          pnl,
          isWin
        );

        console.log(`📤 卖点信号平仓 [${position.symbol}]: ${sellKline.operation_tip}`);
      }
    }
  }

  /**
   * 从K线数据提取当前价格
   */
  private extractPricesFromKLine(klineData: KLineData[]): Map<string, number> {
    const priceMap = new Map<string, number>();
    klineData.forEach(k => {
      priceMap.set(k.symbol, k.close);
    });
    return priceMap;
  }

  /**
   * 获取系统状态概览
   */
  async getSystemOverview(): Promise<any> {
    const [
      signalStats,
      strategyStats,
      poolStats,
      executingStats,
      accountStats,
    ] = await Promise.all([
      this.signalService.getSignalStatistics(),
      this.strategyService.getStrategyStatistics(),
      this.poolService.getPoolStatistics(),
      this.executingService.getExecutionStatistics(),
      this.accountService.getAccountStatistics(),
    ]);

    return {
      signals: signalStats,
      strategies: strategyStats,
      pool: poolStats,
      executing: executingStats,
      accounts: accountStats,
      timestamp: new Date().toISOString(),
    };
  }
}
