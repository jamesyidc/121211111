/**
 * 策略信号池服务 - 三流合一系统
 * 处理信号匹配、冲突检测、分配账户
 */

import { D1Database } from '@cloudflare/workers-types';
import { TradingSignal } from './tradingSignalService';
import { Strategy } from './strategyLibraryService';

export interface SignalPoolEntry {
  pool_id: string;
  strategy_id: string;
  signal_id: string;
  symbol: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXECUTED';
  
  // 冲突检测
  conflict_check_passed: number;
  existing_signal_priority?: string;
  current_signal_priority?: string;
  conflict_reason?: string;
  
  // 账户分配
  assigned_account_id?: string;
  account_type?: 'SIMULATION' | 'LIVE';
  
  // 配置快照
  entry_price?: number;
  position_size_usdt?: number;
  take_profit_pct?: number;
  stop_loss_pct?: number;
  max_holding_minutes?: number;
  
  created_at?: string;
  executed_at?: string;
}

export class StrategySignalPoolService {
  constructor(private db: D1Database) {}

  /**
   * 处理新的买点信号：匹配策略 + 冲突检测 + 账户涨跌幅检查
   */
  async processNewBuySignal(
    signal: TradingSignal,
    strategy: Strategy,
    accountId?: string,
    accountType?: 'SIMULATION' | 'LIVE'
  ): Promise<{ success: boolean; poolId?: string; reason?: string }> {
    
    // 1. 检查账户涨跌幅触发条件（如果启用）
    if (strategy.account_gain_trigger_enabled === 1) {
      const accountCheckResult = await this.checkAccountGainTrigger(
        strategy, 
        accountId, 
        accountType
      );
      
      if (!accountCheckResult.passed) {
        console.log(`⚠️ 账户涨跌幅条件不满足 [${signal.symbol}]: ${accountCheckResult.reason}`);
        await this.recordRejectedSignal(signal, strategy, { 
          reason: `账户涨跌幅: ${accountCheckResult.reason}` 
        });
        return { 
          success: false, 
          reason: `账户涨跌幅条件不满足: ${accountCheckResult.reason}` 
        };
      }
      console.log(`✅ 账户涨跌幅条件满足 [${signal.symbol}]: ${accountCheckResult.message}`);
    }
    
    // 2. 检查今天是否已有该币种的信号
    const conflictCheck = await this.checkTodayConflict(signal.symbol);
    
    // 3. 如果有冲突，比较优先级
    if (conflictCheck.hasConflict) {
      const currentPriority = strategy.priority;
      const existingPriority = conflictCheck.existingPriority!;
      
      // 当前信号优先级不高于已有信号，拒绝
      if (!this.isPriorityHigher(currentPriority, existingPriority)) {
        console.log(`⚠️ 信号冲突被拒绝 [${signal.symbol}]: 现有${existingPriority} >= 当前${currentPriority}`);
        
        await this.recordRejectedSignal(signal, strategy, conflictCheck);
        return { 
          success: false, 
          reason: `优先级冲突: 现有${existingPriority}信号，当前${currentPriority}` 
        };
      }
      
      // 当前信号优先级更高，取消已有信号
      console.log(`✅ 高优先级信号覆盖 [${signal.symbol}]: ${currentPriority} > ${existingPriority}`);
      await this.cancelExistingSignal(conflictCheck.existingPoolId!);
    }
    
    // 4. 通过所有检查，添加到信号池
    const poolId = await this.addToSignalPool(signal, strategy, conflictCheck);
    
    return { success: true, poolId };
  }

  /**
   * 检查今天是否已有该币种的买点信号
   */
  private async checkTodayConflict(symbol: string): Promise<{
    hasConflict: boolean;
    existingPoolId?: string;
    existingPriority?: string;
  }> {
    const today = new Date().toISOString().split('T')[0];
    
    const result = await this.db
      .prepare(`
        SELECT 
          sp.pool_id,
          sp.current_signal_priority,
          ts.signal_category
        FROM strategy_signal_pool sp
        JOIN trading_signals ts ON sp.signal_id = ts.signal_id
        WHERE sp.symbol = ?
          AND sp.status IN ('PENDING', 'APPROVED')
          AND DATE(sp.created_at) = ?
          AND ts.signal_category = 'BUY_POINT'
        LIMIT 1
      `)
      .bind(symbol, today)
      .all();

    if (result.results.length === 0) {
      return { hasConflict: false };
    }

    const existing = result.results[0] as any;
    return {
      hasConflict: true,
      existingPoolId: existing.pool_id,
      existingPriority: existing.current_signal_priority,
    };
  }

  /**
   * 比较优先级（返回true表示current更高）
   */
  private isPriorityHigher(
    current: 'LOW' | 'MEDIUM' | 'HIGH',
    existing: 'LOW' | 'MEDIUM' | 'HIGH'
  ): boolean {
    const priorityMap = { HIGH: 3, MEDIUM: 2, LOW: 1 };
    return priorityMap[current] > priorityMap[existing];
  }

  /**
   * 记录被拒绝的信号
   */
  private async recordRejectedSignal(
    signal: TradingSignal,
    strategy: Strategy,
    conflictCheck: any
  ): Promise<void> {
    const poolId = `POOL_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    await this.db
      .prepare(`
        INSERT INTO strategy_signal_pool (
          pool_id, strategy_id, signal_id, symbol, status,
          conflict_check_passed, existing_signal_priority, current_signal_priority,
          rejection_reason
        ) VALUES (?, ?, ?, ?, 'REJECTED', 0, ?, ?, ?)
      `)
      .bind(
        poolId,
        strategy.strategy_code || strategy.strategy_id, // 使用strategy_code，fallback到strategy_id
        signal.signal_id,
        signal.symbol,
        conflictCheck.existingPriority,
        strategy.priority,
        '优先级低于已有信号'
      )
      .run();
  }

  /**
   * 取消已有信号（优先级被覆盖）
   */
  private async cancelExistingSignal(poolId: string): Promise<void> {
    await this.db
      .prepare(`
        UPDATE strategy_signal_pool 
        SET status = 'REJECTED', 
            rejection_reason = '被更高优先级信号覆盖'
        WHERE pool_id = ?
      `)
      .bind(poolId)
      .run();
  }

  /**
   * 添加信号到信号池
   */
  private async addToSignalPool(
    signal: TradingSignal,
    strategy: Strategy,
    conflictCheck: any
  ): Promise<string> {
    const poolId = `POOL_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const triggerTime = new Date(signal.kline_time).toISOString();
    
    // 构建策略参数快照
    const strategyParams = JSON.stringify({
      position_size_usdt: strategy.position_size_usdt,
      take_profit_pct: strategy.take_profit_pct,
      stop_loss_pct: strategy.stop_loss_pct,
      max_holding_period: strategy.max_holding_period,
      priority: strategy.priority
    });
    
    // 临时禁用外键检查（因为strategy_id字段可能未填充）
    await this.db.prepare(`PRAGMA foreign_keys = OFF`).run();
    
    await this.db
      .prepare(`
        INSERT INTO strategy_signal_pool (
          pool_id, strategy_id, signal_id, symbol, direction, action,
          trigger_price, trigger_time, trigger_signal_type,
          status, conflict_check_passed, current_signal_priority,
          strategy_params
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `)
      .bind(
        poolId,
        strategy.strategy_code || `STR_${strategy.id}` || 'STR_UNKNOWN', // 使用strategy_code作为外键
        signal.signal_id,
        signal.symbol,
        signal.direction,             // LONG/SHORT
        'OPEN',                       // 开仓动作
        signal.kline_close,           // 触发价格
        triggerTime,                  // 触发时间
        signal.signal_type,           // 触发信号类型
        'PENDING',                    // 状态
        1,                            // 冲突检测通过
        strategy.priority || 'MEDIUM',// 当前信号优先级
        strategyParams                // 策略参数快照
      )
      .run();
    
    // 重新启用外键检查
    await this.db.prepare(`PRAGMA foreign_keys = ON`).run();

    console.log(`✅ 信号已添加到池 [${signal.symbol}]: ${poolId}`);
    return poolId;
  }

  /**
   * 获取待执行的信号
   */
  async getPendingSignals(accountType?: 'SIMULATION' | 'LIVE'): Promise<SignalPoolEntry[]> {
    let query = `
      SELECT * FROM strategy_signal_pool 
      WHERE status = 'APPROVED'
    `;
    
    const params: any[] = [];
    
    if (accountType) {
      query += ` AND (account_type = ? OR account_type IS NULL)`;
      params.push(accountType);
    }
    
    query += ` ORDER BY created_at ASC`;
    
    const result = await this.db
      .prepare(query)
      .bind(...params)
      .all();

    return result.results as SignalPoolEntry[];
  }

  /**
   * 标记信号为已执行
   */
  async markAsExecuted(
    poolId: string, 
    accountId: string, 
    accountType: 'SIMULATION' | 'LIVE'
  ): Promise<boolean> {
    const result = await this.db
      .prepare(`
        UPDATE strategy_signal_pool 
        SET status = 'EXECUTED',
            assigned_account_id = ?,
            account_type = ?,
            executed_at = CURRENT_TIMESTAMP
        WHERE pool_id = ?
      `)
      .bind(accountId, accountType, poolId)
      .run();

    return result.success;
  }

  /**
   * 获取信号池统计
   */
  async getPoolStatistics(): Promise<any> {
    const result = await this.db
      .prepare(`
        SELECT 
          status,
          COUNT(*) as count,
          COUNT(DISTINCT symbol) as unique_symbols
        FROM strategy_signal_pool
        WHERE DATE(created_at) = DATE('now')
        GROUP BY status
      `)
      .all();

    return result.results;
  }

  /**
   * 检查账户涨跌幅触发条件
   */
  private async checkAccountGainTrigger(
    strategy: Strategy,
    accountId?: string,
    accountType?: 'SIMULATION' | 'LIVE'
  ): Promise<{ passed: boolean; reason?: string; message?: string }> {
    
    // 获取账户信息
    let account;
    
    if (accountId) {
      // 使用指定账户
      const result = await this.db
        .prepare(`SELECT * FROM trading_account_balance WHERE account_id = ?`)
        .bind(accountId)
        .first();
      account = result;
    } else if (accountType) {
      // 使用账户类型的第一个账户
      const result = await this.db
        .prepare(`
          SELECT * FROM trading_account_balance 
          WHERE account_type = ? 
          ORDER BY created_at ASC 
          LIMIT 1
        `)
        .bind(accountType)
        .first();
      account = result;
    } else {
      // 默认使用模拟账户
      const result = await this.db
        .prepare(`
          SELECT * FROM trading_account_balance 
          WHERE account_type = 'SIMULATION' 
          ORDER BY created_at ASC 
          LIMIT 1
        `)
        .first();
      account = result;
    }
    
    if (!account) {
      return { 
        passed: false, 
        reason: '未找到可用账户' 
      };
    }
    
    // 计算账户涨跌幅百分比（相对初始余额）
    const initialBalance = (account as any).initial_balance_usdt || 10000;
    const currentBalance = (account as any).balance_usdt || 10000;
    const accountGainPct = ((currentBalance - initialBalance) / initialBalance) * 100;
    
    const operator = strategy.account_gain_operator;
    const triggerValue = strategy.account_gain_value_pct || 0;
    const triggerMax = strategy.account_gain_max_pct;
    
    // 根据运算符检查条件
    switch (operator) {
      case 'greater_than':
        if (accountGainPct > triggerValue) {
          return { 
            passed: true, 
            message: `账户涨幅${accountGainPct.toFixed(2)}% > ${triggerValue}%` 
          };
        }
        return { 
          passed: false, 
          reason: `账户涨幅${accountGainPct.toFixed(2)}% ≤ ${triggerValue}%（需要>${triggerValue}%）` 
        };
      
      case 'less_than':
        if (accountGainPct < triggerValue) {
          return { 
            passed: true, 
            message: `账户涨幅${accountGainPct.toFixed(2)}% < ${triggerValue}%` 
          };
        }
        return { 
          passed: false, 
          reason: `账户涨幅${accountGainPct.toFixed(2)}% ≥ ${triggerValue}%（需要<${triggerValue}%）` 
        };
      
      case 'between':
        if (triggerMax !== undefined && accountGainPct >= triggerValue && accountGainPct <= triggerMax) {
          return { 
            passed: true, 
            message: `账户涨幅${accountGainPct.toFixed(2)}%在[${triggerValue}%, ${triggerMax}%]范围内` 
          };
        }
        return { 
          passed: false, 
          reason: `账户涨幅${accountGainPct.toFixed(2)}%不在[${triggerValue}%, ${triggerMax || '?'}%]范围内` 
        };
      
      default:
        return { 
          passed: true, 
          message: '未设置账户涨跌幅条件' 
        };
    }
  }

  /**
   * 清理旧的已执行/拒绝信号（保留7天）
   */
  async cleanupOldSignals(): Promise<number> {
    const result = await this.db
      .prepare(`
        DELETE FROM strategy_signal_pool 
        WHERE status IN ('EXECUTED', 'REJECTED')
          AND created_at < datetime('now', '-7 days')
      `)
      .run();

    return result.meta?.changes || 0;
  }
}
