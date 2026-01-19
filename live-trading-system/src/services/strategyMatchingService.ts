/**
 * 策略匹配服务
 * 
 * 职责：
 * 1. 扫描 trading_signals 表中未执行的信号（is_executed = 0）
 * 2. 匹配 strategy_library 中的做多/做空策略
 * 3. 检查策略的启动条件（当天涨幅、RSI、排名等）
 * 4. 生成符合条件的信号到 strategy_signal_pool（生产信号池）
 * 5. 标记已匹配的 trading_signals 为已执行
 * 
 * 数据流：
 * trading_signals (操作提示) → 策略匹配 → strategy_signal_pool (生产池)
 */

import { D1Database } from '@cloudflare/workers-types';

export interface TradingSignal {
  signal_id: string;
  symbol: string;
  signal_type: string;
  signal_category: 'BUY_POINT' | 'SELL_POINT';
  direction: 'LONG' | 'SHORT';
  
  // K线数据
  kline_time: number;
  kline_open: number;
  kline_high: number;
  kline_low: number;
  kline_close: number;
  kline_volume: number;
  
  // 技术指标
  rsi_5min?: number;
  rsi_1hour?: number;
  sar?: number;
  boll_mb?: number;
  boll_ub?: number;
  boll_lb?: number;
  
  // 市场数据
  homepage_rank?: number;
  change_today?: number;
  bar_10_compare?: number;
  high_48h?: number;
  low_48h?: number;
  drop_from_48h_high?: number;
  rise_from_48h_low?: number;
  
  created_at: string;
}

export interface Strategy {
  strategy_id: string;
  strategy_code: string;
  strategy_name: string;
  strategy_type: 'LONG' | 'SHORT';
  
  // 入场信号
  entry_signal_code: string;
  entry_signal_name?: string;
  entry_price_type?: string;
  
  // 出场信号（最多5个）
  exit_signal_code_1?: string;
  exit_signal_code_2?: string;
  exit_signal_code_3?: string;
  exit_signal_code_4?: string;
  exit_signal_code_5?: string;
  
  // 仓位管理
  position_size_usdt: number;
  take_profit_enabled?: number;
  take_profit_pct?: number;
  stop_loss_enabled?: number;
  stop_loss_pct?: number;
  max_holding_period?: number;
  
  // 过滤条件
  coin_level_filter_enabled?: number;
  allowed_coin_levels?: string;
  
  daily_change_filter_enabled?: number;
  daily_change_condition_type?: string;
  daily_change_min_pct?: number;
  daily_change_max_pct?: number;
  
  rank_filter_enabled?: number;
  rank_condition_type?: string;
  rank_threshold?: number;
  
  rsi_filter_enabled?: number;
  rsi_indicator?: string;
  rsi_condition_type?: string;
  rsi_threshold?: number;
  
  // 交易时段
  trading_hours?: string;
  
  // 状态
  is_enabled?: number;
  priority?: number;
}

export interface MatchResult {
  matched: boolean;
  strategy?: Strategy;
  signal?: TradingSignal;
  reason?: string;
  pool_id?: string;
}

export class StrategyMatchingService {
  constructor(private db: D1Database) {}

  /**
   * 主函数：扫描并匹配信号
   * 建议每30秒或1分钟调用一次
   */
  async scanAndMatchSignals(): Promise<MatchResult[]> {
    console.log('🔍 [策略匹配] 开始扫描未执行的交易信号...');
    
    try {
      // 1. 获取所有未执行的买入信号
      const unmatchedSignals = await this.getUnmatchedBuySignals();
      console.log(`📊 [策略匹配] 找到 ${unmatchedSignals.length} 个未匹配的买入信号`);
      
      if (unmatchedSignals.length === 0) {
        return [];
      }
      
      // 2. 获取所有启用的策略
      const enabledStrategies = await this.getEnabledStrategies();
      console.log(`📈 [策略匹配] 活跃策略: ${enabledStrategies.length} 个`);
      
      if (enabledStrategies.length === 0) {
        console.log('⚠️ [策略匹配] 没有启用的策略');
        return [];
      }
      
      // 3. 对每个信号尝试匹配策略
      const results: MatchResult[] = [];
      
      for (const signal of unmatchedSignals) {
        const matchResult = await this.matchSignalToStrategy(signal, enabledStrategies);
        results.push(matchResult);
        
        if (matchResult.matched) {
          console.log(`✅ [策略匹配] 信号匹配成功: ${signal.symbol} - ${matchResult.strategy?.strategy_name}`);
        }
      }
      
      const successCount = results.filter(r => r.matched).length;
      console.log(`✅ [策略匹配] 完成: ${successCount}/${unmatchedSignals.length} 个信号已匹配`);
      
      return results;
      
    } catch (error) {
      console.error('❌ [策略匹配] 扫描失败:', error);
      throw error;
    }
  }

  /**
   * 匹配单个信号到策略
   */
  private async matchSignalToStrategy(
    signal: TradingSignal,
    strategies: Strategy[]
  ): Promise<MatchResult> {
    
    // 遍历所有策略，找到第一个匹配的（按优先级排序）
    for (const strategy of strategies) {
      
      // 1. 检查信号类型是否匹配
      if (!this.isSignalTypeMatch(signal, strategy)) {
        continue;
      }
      
      // 2. 检查策略方向是否匹配
      if (signal.direction !== strategy.strategy_type) {
        continue;
      }
      
      // 3. 检查币种级别过滤
      if (!await this.passesCoinLevelFilter(signal.symbol, strategy)) {
        continue;
      }
      
      // 4. 检查当天涨幅过滤（关键条件！）
      if (!this.passesDailyChangeFilter(signal, strategy)) {
        continue;
      }
      
      // 5. 检查排名过滤
      if (!this.passesRankFilter(signal, strategy)) {
        continue;
      }
      
      // 6. 检查RSI过滤
      if (!this.passesRsiFilter(signal, strategy)) {
        continue;
      }
      
      // 7. 检查交易时段
      if (!this.passesTimePeriodFilter(signal, strategy)) {
        continue;
      }
      
      // 8. 所有条件通过，生成到生产信号池
      const poolId = await this.addToProductionPool(signal, strategy);
      
      if (poolId) {
        // 9. 标记信号为已执行
        await this.markSignalAsExecuted(signal.signal_id, strategy.strategy_code, poolId);
        
        return {
          matched: true,
          strategy,
          signal,
          pool_id: poolId
        };
      }
    }
    
    // 没有匹配的策略
    return {
      matched: false,
      signal,
      reason: '未找到匹配的策略'
    };
  }

  /**
   * 获取未匹配的买入信号
   * 只获取最近1小时内的信号（避免处理过期数据）
   */
  private async getUnmatchedBuySignals(): Promise<TradingSignal[]> {
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    
    const result = await this.db
      .prepare(`
        SELECT 
          signal_id,
          symbol,
          signal_type,
          direction,
          signal_category,
          kline_time,
          kline_open,
          kline_high,
          kline_low,
          kline_close,
          kline_volume,
          rsi_5min,
          rsi_1hour,
          sar,
          boll_mb,
          boll_ub,
          boll_lb,
          homepage_rank,
          change_today,
          bar_10_compare,
          high_48h,
          low_48h,
          drop_from_48h_high,
          rise_from_48h_low,
          created_at
        FROM trading_signals
        WHERE signal_category = 'BUY_POINT'
          AND is_executed = 0
          AND created_at >= ?
        ORDER BY created_at ASC
        LIMIT 100
      `)
      .bind(oneHourAgo)
      .all();
    
    return result.results as TradingSignal[];
  }

  /**
   * 获取所有启用的策略（按优先级排序）
   */
  private async getEnabledStrategies(): Promise<Strategy[]> {
    const result = await this.db
      .prepare(`
        SELECT *
        FROM strategy_library
        WHERE is_enabled = 1
        ORDER BY priority DESC, created_at ASC
      `)
      .all();
    
    return result.results as Strategy[];
  }

  /**
   * 检查信号类型是否匹配策略的入场信号
   */
  private isSignalTypeMatch(signal: TradingSignal, strategy: Strategy): boolean {
    // 信号类型需要匹配策略的入场信号代码
    // 例如：signal_type = "抄底做多"，entry_signal_code = "SIGNAL_001"
    // 这里需要根据实际的信号命名规则调整
    
    // 简化逻辑：检查信号类型是否包含策略的入场信号名称
    if (strategy.entry_signal_code && signal.signal_type) {
      return signal.signal_type.includes(strategy.entry_signal_code) ||
             strategy.entry_signal_code.includes(signal.signal_type);
    }
    
    return false;
  }

  /**
   * 检查币种级别过滤
   */
  private async passesCoinLevelFilter(symbol: string, strategy: Strategy): Promise<boolean> {
    if (!strategy.coin_level_filter_enabled) {
      return true;
    }
    
    // 获取币种级别
    const coinInfo = await this.db
      .prepare(`SELECT coin_level FROM coin_info WHERE symbol = ?`)
      .bind(symbol)
      .first();
    
    if (!coinInfo) {
      return false;
    }
    
    const coinLevel = (coinInfo as any).coin_level;
    const allowedLevels = strategy.allowed_coin_levels?.split(',') || [];
    
    return allowedLevels.includes(coinLevel);
  }

  /**
   * 检查当天涨幅过滤（核心条件！）
   * 从 trading_signals.change_today 字段获取当天涨幅
   */
  private passesDailyChangeFilter(signal: TradingSignal, strategy: Strategy): boolean {
    if (!strategy.daily_change_filter_enabled) {
      return true;
    }
    
    const changeToday = signal.change_today;
    
    // 如果没有涨幅数据，默认不通过
    if (changeToday === null || changeToday === undefined) {
      return false;
    }
    
    const conditionType = strategy.daily_change_condition_type;
    const minPct = strategy.daily_change_min_pct || -Infinity;
    const maxPct = strategy.daily_change_max_pct || Infinity;
    
    switch (conditionType) {
      case 'RANGE':
        // 区间过滤：min <= change <= max
        return changeToday >= minPct && changeToday <= maxPct;
      
      case 'GT':
        // 大于：change > min
        return changeToday > minPct;
      
      case 'LT':
        // 小于：change < max
        return changeToday < maxPct;
      
      case 'ABS_LT':
        // 绝对值小于：|change| < max
        return Math.abs(changeToday) < maxPct;
      
      default:
        // 默认使用区间过滤
        return changeToday >= minPct && changeToday <= maxPct;
    }
  }

  /**
   * 检查排名过滤
   */
  private passesRankFilter(signal: TradingSignal, strategy: Strategy): boolean {
    if (!strategy.rank_filter_enabled) {
      return true;
    }
    
    const rank = signal.homepage_rank;
    
    if (rank === null || rank === undefined) {
      return false;
    }
    
    const threshold = strategy.rank_threshold || 0;
    const conditionType = strategy.rank_condition_type;
    
    switch (conditionType) {
      case 'TOP_N':
        return rank <= threshold;
      
      case 'GT':
        return rank > threshold;
      
      case 'LT':
        return rank < threshold;
      
      default:
        return rank <= threshold;
    }
  }

  /**
   * 检查RSI过滤
   */
  private passesRsiFilter(signal: TradingSignal, strategy: Strategy): boolean {
    if (!strategy.rsi_filter_enabled) {
      return true;
    }
    
    // 选择RSI指标
    const rsiIndicator = strategy.rsi_indicator || 'RSI_5MIN';
    const rsiValue = rsiIndicator === 'RSI_5MIN' ? signal.rsi_5min : signal.rsi_1hour;
    
    if (rsiValue === null || rsiValue === undefined) {
      return false;
    }
    
    const threshold = strategy.rsi_threshold || 50;
    const conditionType = strategy.rsi_condition_type;
    
    switch (conditionType) {
      case 'GT':
        return rsiValue > threshold;
      
      case 'LT':
        return rsiValue < threshold;
      
      case 'OVERSOLD':
        // 超卖：RSI < 30
        return rsiValue < 30;
      
      case 'OVERBOUGHT':
        // 超买：RSI > 70
        return rsiValue > 70;
      
      default:
        return true;
    }
  }

  /**
   * 检查交易时段过滤
   */
  private passesTimePeriodFilter(signal: TradingSignal, strategy: Strategy): boolean {
    if (!strategy.trading_hours) {
      return true;
    }
    
    try {
      // 解析交易时段（格式示例："09:00-12:00,14:00-16:00"）
      const periods = strategy.trading_hours.split(',');
      const signalTime = new Date(signal.kline_time);
      const signalHour = signalTime.getUTCHours();
      const signalMinute = signalTime.getUTCMinutes();
      const signalTotalMinutes = signalHour * 60 + signalMinute;
      
      for (const period of periods) {
        const [start, end] = period.trim().split('-');
        const [startHour, startMin] = start.split(':').map(Number);
        const [endHour, endMin] = end.split(':').map(Number);
        
        const startMinutes = startHour * 60 + startMin;
        const endMinutes = endHour * 60 + endMin;
        
        if (signalTotalMinutes >= startMinutes && signalTotalMinutes <= endMinutes) {
          return true;
        }
      }
      
      return false;
      
    } catch (error) {
      console.error('❌ 解析交易时段失败:', strategy.trading_hours, error);
      return true; // 解析失败时默认通过
    }
  }

  /**
   * 添加到生产信号池
   */
  private async addToProductionPool(
    signal: TradingSignal,
    strategy: Strategy
  ): Promise<string | null> {
    
    try {
      const poolId = this.generatePoolId();
      const expiresAt = new Date(Date.now() + 3 * 60 * 1000).toISOString(); // 3分钟后过期
      
      await this.db
        .prepare(`
          INSERT INTO strategy_signal_pool (
            pool_id,
            strategy_id,
            signal_id,
            symbol,
            direction,
            action,
            trigger_price,
            trigger_time,
            trigger_signal_type,
            status,
            conflict_check_passed,
            current_signal_priority,
            strategy_params,
            expires_at,
            created_at,
            updated_at
          ) VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, 'PENDING', 1, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        `)
        .bind(
          poolId,
          strategy.strategy_code,
          signal.signal_id,
          signal.symbol,
          signal.direction,
          signal.kline_close,
          new Date(signal.kline_time).toISOString(),
          signal.signal_type,
          strategy.priority || 1,
          JSON.stringify(strategy),
          expiresAt
        )
        .run();
      
      console.log(`✅ [生产池] 信号已加入: ${signal.symbol} - ${poolId}`);
      
      return poolId;
      
    } catch (error) {
      console.error('❌ [生产池] 添加失败:', error);
      return null;
    }
  }

  /**
   * 标记信号为已执行
   */
  private async markSignalAsExecuted(
    signalId: string,
    strategyCode: string,
    poolId: string
  ): Promise<void> {
    
    await this.db
      .prepare(`
        UPDATE trading_signals
        SET is_executed = 1,
            executed_strategy_code = ?,
            executed_pool_id = ?,
            executed_at = CURRENT_TIMESTAMP
        WHERE signal_id = ?
      `)
      .bind(strategyCode, poolId, signalId)
      .run();
    
    console.log(`✅ [信号标记] 已标记为执行: ${signalId}`);
  }

  /**
   * 生成池ID
   */
  private generatePoolId(): string {
    return `POOL_${Date.now()}_${Math.random().toString(36).substr(2, 9).toUpperCase()}`;
  }

  /**
   * 获取匹配统计信息
   */
  async getMatchingStatistics(): Promise<any> {
    const unmatchedCount = await this.db
      .prepare(`
        SELECT COUNT(*) as count 
        FROM trading_signals 
        WHERE signal_category = 'BUY_POINT' 
          AND is_executed = 0
          AND created_at >= datetime('now', '-1 hour')
      `)
      .first();
    
    const matchedToday = await this.db
      .prepare(`
        SELECT COUNT(*) as count 
        FROM trading_signals 
        WHERE signal_category = 'BUY_POINT' 
          AND is_executed = 1
          AND DATE(executed_at) = DATE('now')
      `)
      .first();
    
    return {
      unmatched_signals: (unmatchedCount as any)?.count || 0,
      matched_today: (matchedToday as any)?.count || 0
    };
  }
}
