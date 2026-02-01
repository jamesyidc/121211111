/**
 * 执行中策略池服务 - 三流合一系统
 * 30秒轮询监控持仓、止盈止损、卖点信号
 */

import { D1Database } from '@cloudflare/workers-types';

export interface ExecutingPosition {
  execution_id: string;
  pool_id: string;
  strategy_id: string;
  signal_id: string;
  symbol: string;
  account_id: string;
  account_type: 'SIMULATION' | 'LIVE';
  
  // 价格信息
  entry_price: number;
  current_price?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
  highest_price?: number;
  lowest_price?: number;
  
  // 监控配置
  monitored_sell_signals: string;    // JSON数组: ["通用卖点", "高抛"]
  take_profit_price?: number;
  stop_loss_price?: number;
  trailing_stop_price?: number;
  
  // 时间管理
  holding_minutes: number;
  max_holding_minutes?: number;
  last_check_time?: string;
  
  created_at?: string;
}

export interface ExitReason {
  type: 'SELL_SIGNAL' | 'TAKE_PROFIT' | 'STOP_LOSS' | 'TRAILING_STOP' | 'MAX_HOLDING' | 'MANUAL_CLOSE';
  details: string;
}

export class ExecutingStrategyPoolService {
  constructor(private db: D1Database) {}

  /**
   * 创建新的执行中持仓
   */
  async createExecution(params: {
    poolId: string;
    strategyId: string;
    signalId: string;
    symbol: string;
    accountId: string;
    accountType: 'SIMULATION' | 'LIVE';
    entryPrice: number;
    monitoredSellSignals: string[];
    takeProfitPct?: number;
    stopLossPct?: number;
    trailingStopPct?: number;
    maxHoldingMinutes?: number;
  }): Promise<string> {
    const executionId = `EXEC_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    // 计算止盈止损价格
    const takeProfitPrice = params.takeProfitPct 
      ? params.entryPrice * (1 + params.takeProfitPct / 100)
      : null;
    
    const stopLossPrice = params.stopLossPct
      ? params.entryPrice * (1 - params.stopLossPct / 100)
      : null;

    await this.db
      .prepare(`
        INSERT INTO executing_strategy_pool (
          execution_id, pool_id, strategy_id, signal_id, symbol,
          account_id, account_type, entry_price, current_price,
          monitored_sell_signals, take_profit_price, stop_loss_price,
          holding_minutes, max_holding_minutes, highest_price, lowest_price
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
      `)
      .bind(
        executionId,
        params.poolId,
        params.strategyId,
        params.signalId,
        params.symbol,
        params.accountId,
        params.accountType,
        params.entryPrice,
        params.entryPrice,  // 初始current_price = entry_price
        JSON.stringify(params.monitoredSellSignals),
        takeProfitPrice,
        stopLossPrice,
        params.maxHoldingMinutes || 0,
        params.entryPrice,  // 初始highest_price
        params.entryPrice   // 初始lowest_price
      )
      .run();

    console.log(`🚀 执行开始 [${params.symbol}]: ${executionId}`);
    return executionId;
  }

  /**
   * 30秒轮询监控所有持仓
   */
  async monitorAllPositions(
    currentPrices: Map<string, number>
  ): Promise<{
    checked: number;
    triggered: Array<{ executionId: string; reason: ExitReason }>;
  }> {
    const positions = await this.getAllExecutingPositions();
    const triggered: Array<{ executionId: string; reason: ExitReason }> = [];

    for (const position of positions) {
      const currentPrice = currentPrices.get(position.symbol);
      if (!currentPrice) {
        console.warn(`⚠️ 未找到 ${position.symbol} 的当前价格`);
        continue;
      }

      // 更新价格和持仓时长
      await this.updatePositionPrice(position.execution_id, currentPrice);

      // 检查各种退出条件
      const exitReason = this.checkExitConditions(position, currentPrice);
      if (exitReason) {
        triggered.push({ executionId: position.execution_id, reason: exitReason });
      }
    }

    return { checked: positions.length, triggered };
  }

  /**
   * 检查退出条件
   */
  private checkExitConditions(
    position: ExecutingPosition,
    currentPrice: number
  ): ExitReason | null {
    // 1. 检查止盈
    if (position.take_profit_price && currentPrice >= position.take_profit_price) {
      return {
        type: 'TAKE_PROFIT',
        details: `价格${currentPrice}达到止盈${position.take_profit_price}`,
      };
    }

    // 2. 检查止损
    if (position.stop_loss_price && currentPrice <= position.stop_loss_price) {
      return {
        type: 'STOP_LOSS',
        details: `价格${currentPrice}触发止损${position.stop_loss_price}`,
      };
    }

    // 3. 检查移动止损
    if (position.trailing_stop_price && currentPrice <= position.trailing_stop_price) {
      return {
        type: 'TRAILING_STOP',
        details: `价格${currentPrice}触发移动止损${position.trailing_stop_price}`,
      };
    }

    // 4. 检查最大持仓时长
    if (position.max_holding_minutes && position.max_holding_minutes > 0) {
      if (position.holding_minutes >= position.max_holding_minutes) {
        return {
          type: 'MAX_HOLDING',
          details: `持仓${position.holding_minutes}分钟达到上限${position.max_holding_minutes}`,
        };
      }
    }

    return null;
  }

  /**
   * 更新持仓价格和PnL
   */
  private async updatePositionPrice(
    executionId: string,
    currentPrice: number
  ): Promise<void> {
    await this.db
      .prepare(`
        UPDATE executing_strategy_pool
        SET current_price = ?,
            unrealized_pnl = (? - entry_price),
            unrealized_pnl_pct = ((? - entry_price) / entry_price * 100),
            highest_price = MAX(highest_price, ?),
            lowest_price = MIN(lowest_price, ?),
            holding_minutes = holding_minutes + 1,
            last_check_time = CURRENT_TIMESTAMP
        WHERE execution_id = ?
      `)
      .bind(
        currentPrice,
        currentPrice,
        currentPrice,
        currentPrice,
        currentPrice,
        executionId
      )
      .run();
  }

  /**
   * 检查是否收到卖点信号
   */
  async checkSellSignal(
    executionId: string,
    latestSignalType: string
  ): Promise<boolean> {
    const position = await this.getPosition(executionId);
    if (!position) return false;

    const monitoredSignals = JSON.parse(position.monitored_sell_signals) as string[];
    return monitoredSignals.includes(latestSignalType);
  }

  /**
   * 平仓并移到完成池
   */
  async closePosition(
    executionId: string,
    exitReason: ExitReason,
    exitPrice: number
  ): Promise<boolean> {
    const position = await this.getPosition(executionId);
    if (!position) return false;

    // 计算实际盈亏
    const realizedPnl = exitPrice - position.entry_price;
    const realizedPnlPct = (realizedPnl / position.entry_price) * 100;

    // 插入到完成池
    const completionId = `COMP_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    await this.db
      .prepare(`
        INSERT INTO completed_strategy_pool (
          completion_id, execution_id, pool_id, strategy_id, signal_id,
          symbol, account_id, account_type,
          entry_price, exit_price, entry_time, exit_time,
          realized_pnl, realized_pnl_pct, holding_minutes,
          exit_reason, exit_details,
          highest_price, lowest_price
        )
        SELECT 
          ? as completion_id,
          execution_id, pool_id, strategy_id, signal_id,
          symbol, account_id, account_type,
          entry_price, ? as exit_price,
          created_at as entry_time, CURRENT_TIMESTAMP as exit_time,
          ? as realized_pnl, ? as realized_pnl_pct, holding_minutes,
          ? as exit_reason, ? as exit_details,
          highest_price, lowest_price
        FROM executing_strategy_pool
        WHERE execution_id = ?
      `)
      .bind(
        completionId,
        exitPrice,
        realizedPnl,
        realizedPnlPct,
        exitReason.type,
        exitReason.details,
        executionId
      )
      .run();

    // 从执行池删除
    await this.db
      .prepare(`DELETE FROM executing_strategy_pool WHERE execution_id = ?`)
      .bind(executionId)
      .run();

    console.log(`✅ 平仓完成 [${position.symbol}]: ${exitReason.type}, PnL: ${realizedPnlPct.toFixed(2)}%`);
    return true;
  }

  /**
   * 获取所有执行中的持仓
   */
  async getAllExecutingPositions(accountType?: 'SIMULATION' | 'LIVE'): Promise<ExecutingPosition[]> {
    let query = `SELECT * FROM executing_strategy_pool`;
    const params: any[] = [];
    
    if (accountType) {
      query += ` WHERE account_type = ?`;
      params.push(accountType);
    }
    
    query += ` ORDER BY created_at ASC`;
    
    const result = await this.db
      .prepare(query)
      .bind(...params)
      .all();

    return result.results as ExecutingPosition[];
  }

  /**
   * 获取单个持仓
   */
  async getPosition(executionId: string): Promise<ExecutingPosition | null> {
    const result = await this.db
      .prepare(`SELECT * FROM executing_strategy_pool WHERE execution_id = ?`)
      .bind(executionId)
      .all();

    return result.results.length > 0 ? (result.results[0] as ExecutingPosition) : null;
  }

  /**
   * 按账户查询执行中的持仓
   */
  async getPositionsByAccount(
    accountId: string,
    accountType: 'SIMULATION' | 'LIVE'
  ): Promise<ExecutingPosition[]> {
    const result = await this.db
      .prepare(`
        SELECT * FROM executing_strategy_pool 
        WHERE account_id = ? AND account_type = ?
        ORDER BY created_at DESC
      `)
      .bind(accountId, accountType)
      .all();

    return result.results as ExecutingPosition[];
  }

  /**
   * 获取执行池统计
   */
  async getExecutionStatistics(): Promise<any> {
    const result = await this.db
      .prepare(`
        SELECT 
          account_type,
          COUNT(*) as total_positions,
          AVG(unrealized_pnl_pct) as avg_pnl_pct,
          AVG(holding_minutes) as avg_holding_minutes,
          SUM(CASE WHEN unrealized_pnl > 0 THEN 1 ELSE 0 END) as profitable_count
        FROM executing_strategy_pool
        GROUP BY account_type
      `)
      .all();

    return result.results;
  }
}
