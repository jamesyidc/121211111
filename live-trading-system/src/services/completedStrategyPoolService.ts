/**
 * 已完成策略池服务 - 三流合一系统
 * 查询历史交易记录和统计
 */

import { D1Database } from '@cloudflare/workers-types';

export interface CompletedTrade {
  completion_id: string;
  execution_id: string;
  pool_id: string;
  strategy_id: string;
  signal_id: string;
  symbol: string;
  account_id: string;
  account_type: 'SIMULATION' | 'LIVE';
  
  entry_price: number;
  exit_price: number;
  entry_time: string;
  exit_time: string;
  
  realized_pnl: number;
  realized_pnl_pct: number;
  holding_minutes: number;
  
  exit_reason: string;
  exit_details: string;
  
  highest_price?: number;
  lowest_price?: number;
  max_drawdown_pct?: number;
  
  created_at?: string;
}

export class CompletedStrategyPoolService {
  constructor(private db: D1Database) {}

  /**
   * 查询完成的交易（支持过滤）
   */
  async getCompletedTrades(params: {
    accountType?: 'SIMULATION' | 'LIVE';
    accountId?: string;
    symbol?: string;
    strategyId?: string;
    startDate?: string;
    endDate?: string;
    limit?: number;
    offset?: number;
  }): Promise<CompletedTrade[]> {
    const conditions: string[] = ['1=1'];
    const values: any[] = [];

    if (params.accountType) {
      conditions.push('account_type = ?');
      values.push(params.accountType);
    }

    if (params.accountId) {
      conditions.push('account_id = ?');
      values.push(params.accountId);
    }

    if (params.symbol) {
      conditions.push('symbol = ?');
      values.push(params.symbol);
    }

    if (params.strategyId) {
      conditions.push('strategy_id = ?');
      values.push(params.strategyId);
    }

    if (params.startDate) {
      conditions.push('DATE(exit_time) >= ?');
      values.push(params.startDate);
    }

    if (params.endDate) {
      conditions.push('DATE(exit_time) <= ?');
      values.push(params.endDate);
    }

    const limit = params.limit || 100;
    const offset = params.offset || 0;

    const result = await this.db
      .prepare(`
        SELECT * FROM completed_strategy_pool 
        WHERE ${conditions.join(' AND ')}
        ORDER BY exit_time DESC
        LIMIT ? OFFSET ?
      `)
      .bind(...values, limit, offset)
      .all();

    return result.results as CompletedTrade[];
  }

  /**
   * 获取交易统计
   */
  async getTradeStatistics(params: {
    accountType?: 'SIMULATION' | 'LIVE';
    accountId?: string;
    startDate?: string;
    endDate?: string;
  }): Promise<any> {
    const conditions: string[] = ['1=1'];
    const values: any[] = [];

    if (params.accountType) {
      conditions.push('account_type = ?');
      values.push(params.accountType);
    }

    if (params.accountId) {
      conditions.push('account_id = ?');
      values.push(params.accountId);
    }

    if (params.startDate) {
      conditions.push('DATE(exit_time) >= ?');
      values.push(params.startDate);
    }

    if (params.endDate) {
      conditions.push('DATE(exit_time) <= ?');
      values.push(params.endDate);
    }

    const result = await this.db
      .prepare(`
        SELECT 
          COUNT(*) as total_trades,
          SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
          SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
          ROUND(SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
          ROUND(SUM(realized_pnl), 2) as total_pnl,
          ROUND(AVG(realized_pnl), 2) as avg_pnl,
          ROUND(MAX(realized_pnl), 2) as max_profit,
          ROUND(MIN(realized_pnl), 2) as max_loss,
          ROUND(AVG(realized_pnl_pct), 2) as avg_pnl_pct,
          ROUND(AVG(holding_minutes), 2) as avg_holding_minutes,
          exit_reason,
          COUNT(*) as reason_count
        FROM completed_strategy_pool
        WHERE ${conditions.join(' AND ')}
        GROUP BY exit_reason
      `)
      .bind(...values)
      .all();

    // 汇总统计
    const summary = await this.db
      .prepare(`
        SELECT 
          COUNT(*) as total_trades,
          SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
          SUM(CASE WHEN realized_pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
          ROUND(SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
          ROUND(SUM(realized_pnl), 2) as total_pnl,
          ROUND(AVG(realized_pnl), 2) as avg_pnl,
          ROUND(MAX(realized_pnl), 2) as max_profit,
          ROUND(MIN(realized_pnl), 2) as max_loss,
          ROUND(AVG(realized_pnl_pct), 2) as avg_pnl_pct,
          ROUND(AVG(holding_minutes), 2) as avg_holding_minutes
        FROM completed_strategy_pool
        WHERE ${conditions.join(' AND ')}
      `)
      .bind(...values)
      .all();

    return {
      summary: summary.results[0],
      byExitReason: result.results,
    };
  }

  /**
   * 按策略统计
   */
  async getStatisticsByStrategy(): Promise<any[]> {
    const result = await this.db
      .prepare(`
        SELECT 
          strategy_id,
          COUNT(*) as total_trades,
          SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
          ROUND(SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
          ROUND(SUM(realized_pnl), 2) as total_pnl,
          ROUND(AVG(realized_pnl_pct), 2) as avg_pnl_pct
        FROM completed_strategy_pool
        GROUP BY strategy_id
        ORDER BY total_pnl DESC
      `)
      .all();

    return result.results;
  }

  /**
   * 按币种统计
   */
  async getStatisticsBySymbol(limit: number = 20): Promise<any[]> {
    const result = await this.db
      .prepare(`
        SELECT 
          symbol,
          COUNT(*) as total_trades,
          SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
          ROUND(SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as win_rate,
          ROUND(SUM(realized_pnl), 2) as total_pnl,
          ROUND(AVG(realized_pnl_pct), 2) as avg_pnl_pct
        FROM completed_strategy_pool
        GROUP BY symbol
        ORDER BY total_trades DESC
        LIMIT ?
      `)
      .bind(limit)
      .all();

    return result.results;
  }

  /**
   * 获取每日统计
   */
  async getDailyStatistics(days: number = 30): Promise<any[]> {
    const result = await this.db
      .prepare(`
        SELECT 
          DATE(exit_time) as trade_date,
          COUNT(*) as total_trades,
          SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
          ROUND(SUM(realized_pnl), 2) as daily_pnl,
          ROUND(AVG(realized_pnl_pct), 2) as avg_pnl_pct
        FROM completed_strategy_pool
        WHERE exit_time >= datetime('now', '-' || ? || ' days')
        GROUP BY DATE(exit_time)
        ORDER BY trade_date DESC
      `)
      .bind(days)
      .all();

    return result.results;
  }

  /**
   * 清理旧的完成记录（保留90天）
   */
  async cleanupOldRecords(): Promise<number> {
    const result = await this.db
      .prepare(`
        DELETE FROM completed_strategy_pool 
        WHERE exit_time < datetime('now', '-90 days')
      `)
      .run();

    return result.meta?.changes || 0;
  }
}
