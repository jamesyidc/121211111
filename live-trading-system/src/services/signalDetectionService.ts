/**
 * 信号检测服务
 * 负责扫描K线数据，检测符合策略条件的买入/卖出信号
 * 并将信号添加到生产策略信号池
 */

import { D1Database } from '@cloudflare/workers-types';

export interface KlineData {
  symbol: string;
  open_time: string;
  close_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  quote_volume: number;
}

export interface DetectedSignal {
  symbol: string;
  signal_code: string;
  signal_name: string;
  signal_direction: 'LONG' | 'SHORT';
  signal_category: 'buy_point' | 'sell_point';
  trigger_price: number;
  trigger_time: string;
  kline_data: KlineData;
}

export class SignalDetectionService {
  constructor(private db: D1Database) {}

  /**
   * 扫描所有币种的最新K线，检测买入信号
   * 每30秒调用一次
   */
  async scanForBuySignals(): Promise<DetectedSignal[]> {
    console.log('🔍 开始扫描买入信号...');
    
    try {
      // 1. 获取所有活跃的币种
      const symbols = await this.getActiveSymbols();
      console.log(`📊 扫描 ${symbols.length} 个币种`);
      
      // 2. 获取所有启用的策略及其买点信号
      const strategies = await this.getEnabledStrategies();
      console.log(`📈 活跃策略: ${strategies.length} 个`);
      
      if (strategies.length === 0) {
        console.log('⚠️ 没有启用的策略');
        return [];
      }
      
      // 3. 对每个币种检测信号
      const detectedSignals: DetectedSignal[] = [];
      
      for (const symbol of symbols) {
        const signals = await this.detectSignalsForSymbol(symbol, strategies);
        detectedSignals.push(...signals);
      }
      
      console.log(`✅ 检测到 ${detectedSignals.length} 个买入信号`);
      return detectedSignals;
      
    } catch (error) {
      console.error('❌ 扫描买入信号失败:', error);
      throw error;
    }
  }

  /**
   * 检测单个币种的信号
   */
  private async detectSignalsForSymbol(
    symbol: string,
    strategies: any[]
  ): Promise<DetectedSignal[]> {
    
    // 获取最新K线数据
    const latestKline = await this.getLatestKline(symbol);
    if (!latestKline) {
      return [];
    }
    
    const detectedSignals: DetectedSignal[] = [];
    
    // 对每个策略检查是否满足买入条件
    for (const strategy of strategies) {
      // 检查币种级别过滤
      if (!this.passesCoinLevelFilter(strategy, symbol)) {
        continue;
      }
      
      // 检查涨跌幅过滤
      if (!this.passesDailyChangeFilter(strategy, latestKline)) {
        continue;
      }
      
      // 检查是否有对应的买点信号
      const signal = await this.checkBuySignal(
        strategy.entry_signal_code,
        symbol,
        latestKline
      );
      
      if (signal) {
        detectedSignals.push({
          symbol,
          signal_code: signal.signal_code,
          signal_name: signal.signal_name,
          signal_direction: signal.signal_direction,
          signal_category: 'buy_point',
          trigger_price: latestKline.close,
          trigger_time: latestKline.close_time,
          kline_data: latestKline
        });
        
        console.log(`🎯 检测到信号 [${symbol}]: ${signal.signal_name} @ ${latestKline.close}`);
      }
    }
    
    return detectedSignals;
  }

  /**
   * 获取所有活跃币种
   */
  private async getActiveSymbols(): Promise<string[]> {
    const result = await this.db
      .prepare(`
        SELECT DISTINCT symbol 
        FROM coin_info 
        WHERE is_active = 1
        ORDER BY symbol
      `)
      .all();
    
    return result.results.map((r: any) => r.symbol);
  }

  /**
   * 获取所有启用的策略
   */
  private async getEnabledStrategies(): Promise<any[]> {
    const result = await this.db
      .prepare(`
        SELECT 
          strategy_code,
          strategy_name,
          strategy_type,
          entry_signal_code,
          entry_signal_name,
          coin_level_filter_enabled,
          allowed_coin_levels,
          daily_change_filter_enabled,
          daily_change_condition_type,
          daily_change_min_pct,
          daily_change_max_pct,
          priority
        FROM strategy_library
        WHERE is_enabled = 1
        ORDER BY priority DESC
      `)
      .all();
    
    return result.results;
  }

  /**
   * 获取最新K线数据
   */
  private async getLatestKline(symbol: string): Promise<KlineData | null> {
    const result = await this.db
      .prepare(`
        SELECT 
          symbol,
          open_time,
          close_time,
          open,
          high,
          low,
          close,
          volume,
          quote_volume
        FROM klines
        WHERE symbol = ?
        ORDER BY open_time DESC
        LIMIT 1
      `)
      .bind(symbol)
      .first();
    
    return result as KlineData | null;
  }

  /**
   * 检查买点信号是否存在
   */
  private async checkBuySignal(
    signalCode: string,
    symbol: string,
    kline: KlineData
  ): Promise<any | null> {
    // 查询信号库中是否有该信号
    const signalDef = await this.db
      .prepare(`
        SELECT 
          signal_code,
          signal_name,
          signal_direction,
          signal_category
        FROM signal_library
        WHERE signal_code = ?
          AND signal_category = 'buy_point'
          AND is_enabled = 1
      `)
      .bind(signalCode)
      .first();
    
    if (!signalDef) {
      return null;
    }
    
    // 查询 trading_signals 表，看是否有该币种的最新信号记录
    const signalRecord = await this.db
      .prepare(`
        SELECT *
        FROM trading_signals
        WHERE symbol = ?
          AND signal_code = ?
          AND signal_category = 'buy_point'
        ORDER BY signal_time DESC
        LIMIT 1
      `)
      .bind(symbol, signalCode)
      .first();
    
    // 如果有信号记录且时间在3根K线以内，则认为信号有效
    if (signalRecord) {
      const signalTime = new Date(signalRecord.signal_time as string).getTime();
      const currentTime = new Date(kline.close_time).getTime();
      const threeKlinesPeriod = 3 * 60 * 1000; // 3分钟（假设1分钟K线）
      
      if (currentTime - signalTime <= threeKlinesPeriod) {
        return signalDef;
      }
    }
    
    return null;
  }

  /**
   * 检查币种级别过滤
   */
  private passesCoinLevelFilter(strategy: any, symbol: string): boolean {
    if (!strategy.coin_level_filter_enabled) {
      return true;
    }
    
    // TODO: 实现币种级别过滤逻辑
    // 需要查询 coin_info 表获取币种的 level
    return true;
  }

  /**
   * 检查涨跌幅过滤
   */
  private passesDailyChangeFilter(strategy: any, kline: KlineData): boolean {
    if (!strategy.daily_change_filter_enabled) {
      return true;
    }
    
    // TODO: 实现涨跌幅过滤逻辑
    // 需要计算当日涨跌幅百分比
    return true;
  }

  /**
   * 扫描卖出信号（针对已持仓的策略）
   * 每1分钟调用一次
   */
  async scanForSellSignals(): Promise<any[]> {
    console.log('🔍 开始扫描卖出信号...');
    
    try {
      // 获取所有执行中的持仓
      const positions = await this.getActivePositions();
      console.log(`📊 监控 ${positions.length} 个持仓`);
      
      const triggeredSells: any[] = [];
      
      for (const position of positions) {
        const sellSignal = await this.checkSellConditions(position);
        if (sellSignal) {
          triggeredSells.push(sellSignal);
        }
      }
      
      console.log(`✅ 触发 ${triggeredSells.length} 个卖出信号`);
      return triggeredSells;
      
    } catch (error) {
      console.error('❌ 扫描卖出信号失败:', error);
      throw error;
    }
  }

  /**
   * 获取所有执行中的持仓
   */
  private async getActivePositions(): Promise<any[]> {
    const result = await this.db
      .prepare(`
        SELECT * FROM executing_strategy_pool
        ORDER BY entry_time DESC
      `)
      .all();
    
    return result.results;
  }

  /**
   * 检查卖出条件
   */
  private async checkSellConditions(position: any): Promise<any | null> {
    // 获取当前价格
    const currentKline = await this.getLatestKline(position.symbol);
    if (!currentKline) {
      return null;
    }
    
    const currentPrice = currentKline.close;
    const entryPrice = position.entry_price;
    const pnlPct = ((currentPrice - entryPrice) / entryPrice) * 100;
    
    // 1. 检查止盈
    if (position.take_profit_price && currentPrice >= position.take_profit_price) {
      return {
        execution_id: position.execution_id,
        reason: 'TAKE_PROFIT',
        exit_price: currentPrice,
        pnl_pct: pnlPct
      };
    }
    
    // 2. 检查止损
    if (position.stop_loss_price && currentPrice <= position.stop_loss_price) {
      return {
        execution_id: position.execution_id,
        reason: 'STOP_LOSS',
        exit_price: currentPrice,
        pnl_pct: pnlPct
      };
    }
    
    // 3. 检查最大持仓时间
    if (position.max_holding_minutes > 0) {
      const holdingMinutes = position.holding_minutes || 0;
      if (holdingMinutes >= position.max_holding_minutes) {
        return {
          execution_id: position.execution_id,
          reason: 'MAX_HOLDING',
          exit_price: currentPrice,
          pnl_pct: pnlPct
        };
      }
    }
    
    // 4. 检查卖点信号
    const sellSignalTriggered = await this.checkSellSignalTriggered(
      position.symbol,
      position.monitored_sell_signals
    );
    
    if (sellSignalTriggered) {
      return {
        execution_id: position.execution_id,
        reason: 'SELL_SIGNAL',
        signal_code: sellSignalTriggered.signal_code,
        exit_price: currentPrice,
        pnl_pct: pnlPct
      };
    }
    
    return null;
  }

  /**
   * 检查卖点信号是否触发
   */
  private async checkSellSignalTriggered(
    symbol: string,
    monitoredSignals: string
  ): Promise<any | null> {
    
    let signalCodes: string[];
    try {
      signalCodes = JSON.parse(monitoredSignals);
    } catch {
      return null;
    }
    
    if (signalCodes.length === 0) {
      return null;
    }
    
    // 查询最新的卖点信号
    for (const signalCode of signalCodes) {
      const signal = await this.db
        .prepare(`
          SELECT *
          FROM trading_signals
          WHERE symbol = ?
            AND signal_code = ?
            AND signal_category = 'sell_point'
          ORDER BY signal_time DESC
          LIMIT 1
        `)
        .bind(symbol, signalCode)
        .first();
      
      if (signal) {
        // 检查信号是否在最近3根K线内
        const signalTime = new Date(signal.signal_time as string).getTime();
        const now = Date.now();
        const threeKlinesPeriod = 3 * 60 * 1000;
        
        if (now - signalTime <= threeKlinesPeriod) {
          return signal;
        }
      }
    }
    
    return null;
  }
}
