/**
 * 信号池管理服务
 * 负责管理三个池的数据流转：
 * 1. 生产策略信号池 (strategy_signal_pool) - 待执行信号
 * 2. 已买入策略信号池 (executing_strategy_pool) - 执行中持仓
 * 3. 已完成策略信号池 (completed_strategy_pool) - 已完成交易
 */

import { D1Database } from '@cloudflare/workers-types';
import { DetectedSignal } from './signalDetectionService';

export interface PoolConfig {
  auto_trading_enabled: boolean;  // 是否自动交易
  semi_auto_enabled: boolean;      // 是否半自动（需人工确认）
}

export class SignalPoolManager {
  constructor(private db: D1Database) {}

  /**
   * 将检测到的信号添加到生产策略信号池
   * 保留3根K线时间
   */
  async addToProductionPool(
    signal: DetectedSignal,
    strategyCode: string
  ): Promise<{ success: boolean; poolId?: string; reason?: string }> {
    
    try {
      // 1. 检查是否已存在相同的信号（去重）
      const exists = await this.checkSignalExists(signal.symbol, signal.signal_code);
      if (exists) {
        console.log(`⚠️ 信号已存在 [${signal.symbol}]: ${signal.signal_name}`);
        return { success: false, reason: '信号已存在' };
      }
      
      // 2. 检查该币种今日是否已有买入信号（冲突检测）
      const conflict = await this.checkTodayConflict(signal.symbol);
      if (conflict.hasConflict) {
        console.log(`⚠️ 今日已有信号 [${signal.symbol}]`);
        return { success: false, reason: '今日已有买入信号' };
      }
      
      // 3. 获取策略详情
      const strategy = await this.getStrategy(strategyCode);
      if (!strategy) {
        return { success: false, reason: '策略不存在' };
      }
      
      // 4. 生成池ID
      const poolId = this.generatePoolId();
      
      // 5. 计算过期时间（3根K线后）
      const expiresAt = new Date(Date.now() + 3 * 60 * 1000).toISOString();
      
      // 6. 插入到生产策略信号池
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
            created_at
          ) VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, 'PENDING', 1, ?, ?, ?, CURRENT_TIMESTAMP)
        `)
        .bind(
          poolId,
          strategyCode,
          signal.signal_code,
          signal.symbol,
          signal.signal_direction,
          signal.trigger_price,
          signal.trigger_time,
          signal.signal_name,
          strategy.priority || 'MEDIUM',
          JSON.stringify(strategy),
          expiresAt
        )
        .run();
      
      console.log(`✅ 信号已加入生产池 [${signal.symbol}]: ${poolId}`);
      
      return { success: true, poolId };
      
    } catch (error) {
      console.error('❌ 添加到生产池失败:', error);
      return { success: false, reason: error.message };
    }
  }

  /**
   * 执行买入（从生产池 → 已买入池）
   */
  async executeBuy(
    poolId: string,
    accountId: string = 'SIMULATION_001',
    accountType: 'SIMULATION' | 'LIVE' = 'SIMULATION'
  ): Promise<{ success: boolean; executionId?: string; reason?: string }> {
    
    try {
      // 1. 获取信号池记录
      const poolEntry = await this.getPoolEntry(poolId);
      if (!poolEntry) {
        return { success: false, reason: '信号池记录不存在' };
      }
      
      if (poolEntry.status !== 'PENDING') {
        return { success: false, reason: `信号状态不正确: ${poolEntry.status}` };
      }
      
      // 2. 检查信号是否过期
      if (poolEntry.expires_at && new Date(poolEntry.expires_at) < new Date()) {
        await this.markPoolEntryAs(poolId, 'REJECTED', '信号已过期');
        return { success: false, reason: '信号已过期' };
      }
      
      // 3. 获取策略参数
      const strategy = JSON.parse(poolEntry.strategy_params);
      
      // 4. 计算买入金额和数量
      const entryPrice = poolEntry.trigger_price;
      const positionSizeUsdt = strategy.position_size_usdt || 100;
      const positionAmount = positionSizeUsdt / entryPrice;
      const buyFee = positionSizeUsdt * 0.001; // 0.1% 手续费
      const totalCost = positionSizeUsdt + buyFee;
      
      // 5. 检查并冻结资金
      const { AccountBalanceService } = await import('./accountBalanceService');
      const balanceService = new AccountBalanceService(this.db);
      
      // 初始化账户（如果不存在）
      await balanceService.initializeAccount(accountId, accountType);
      
      // 冻结资金
      const freezeResult = await balanceService.freezeFunds(
        accountId,
        accountType,
        totalCost,
        poolId
      );
      
      if (!freezeResult.success) {
        await this.markPoolEntryAs(poolId, 'REJECTED', freezeResult.reason);
        return { success: false, reason: freezeResult.reason };
      }
      
      // 7. 计算止盈止损价格
      const takeProfitPrice = strategy.take_profit_enabled 
        ? entryPrice * (1 + strategy.take_profit_pct / 100)
        : null;
      const stopLossPrice = strategy.stop_loss_enabled
        ? entryPrice * (1 - strategy.stop_loss_pct / 100)
        : null;
      
      // 8. 获取卖点信号列表
      const monitoredSellSignals = this.getMonitoredSellSignals(strategy);
      
      // 9. 生成订单ID
      const buyOrderId = `BUY_${Date.now()}_${Math.random().toString(36).substr(2, 6).toUpperCase()}`;
      
      // 10. 插入到执行中策略池（包含订单信息）
      await this.db
        .prepare(`
          INSERT INTO executing_strategy_pool (
            execution_id,
            pool_id,
            strategy_id,
            strategy_name,
            symbol,
            direction,
            entry_signal_id,
            entry_signal_type,
            entry_price,
            entry_time,
            position_size,
            position_amount,
            current_price,
            highest_price,
            lowest_price,
            monitored_sell_signals,
            max_holding_minutes,
            take_profit_price,
            stop_loss_price,
            account_id,
            account_type,
            buy_order_id,
            buy_filled_amount,
            buy_unfilled_amount,
            buy_filled_value,
            buy_unfilled_value,
            buy_order_status,
            buy_fee,
            last_check_time,
            created_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        `)
        .bind(
          executionId,
          poolId,
          poolEntry.strategy_id,
          strategy.strategy_name,
          poolEntry.symbol,
          poolEntry.direction,
          poolEntry.signal_id,
          poolEntry.trigger_signal_type,
          entryPrice,
          poolEntry.trigger_time,
          positionSizeUsdt,
          positionAmount,
          entryPrice,
          entryPrice,
          entryPrice,
          monitoredSellSignals,
          strategy.max_holding_period || 0,
          takeProfitPrice,
          stopLossPrice,
          accountId,
          accountType,
          buyOrderId,
          positionAmount,      // 假设全部成交
          0,                   // 未成交数量
          positionSizeUsdt,    // 成交金额
          0,                   // 未成交金额
          'FILLED',            // 订单状态
          buyFee
        )
        .run();
      
      // 11. 确认买入，从冻结余额转为持仓
      await balanceService.confirmBuy(
        accountId,
        accountType,
        totalCost,
        positionSizeUsdt
      );
      
      // 12. 更新生产池状态为已执行
      await this.markPoolEntryAs(poolId, 'EXECUTING', null, executionId);
      
      console.log(`✅ 买入已执行 [${poolEntry.symbol}]: ${executionId}`);
      
      return { success: true, executionId };
      
    } catch (error) {
      console.error('❌ 执行买入失败:', error);
      return { success: false, reason: error.message };
    }
  }

  /**
   * 执行卖出（从已买入池 → 已完成池）
   */
  async executeSell(
    executionId: string,
    exitReason: 'SELL_SIGNAL' | 'TAKE_PROFIT' | 'STOP_LOSS' | 'MAX_HOLDING' | 'MANUAL_CLOSE',
    exitPrice: number,
    exitSignalCode?: string
  ): Promise<{ success: boolean; completionId?: string; reason?: string }> {
    
    try {
      // 1. 获取执行中的持仓
      const position = await this.getPosition(executionId);
      if (!position) {
        return { success: false, reason: '持仓不存在' };
      }
      
      // 2. 计算卖出金额和手续费
      const sellAmount = exitPrice * position.buy_filled_amount;
      const sellFee = sellAmount * 0.001; // 0.1% 手续费
      const netSellAmount = sellAmount - sellFee;
      
      // 3. 计算盈亏
      const buyAmount = position.buy_filled_value;
      const totalFee = position.buy_fee + sellFee;
      const realizedPnl = netSellAmount - buyAmount;
      const realizedPnlPct = ((exitPrice - position.entry_price) / position.entry_price) * 100;
      
      // 4. 实盘：冻结持仓（准备卖出）
      const { AccountBalanceService } = await import('./accountBalanceService');
      const balanceService = new AccountBalanceService(this.db);
      
      if (position.account_type === 'LIVE') {
        await balanceService.freezePosition(
          position.account_id,
          position.account_type,
          position.position_size
        );
      }
      
      // 5. 确认卖出，释放资金
      await balanceService.confirmSell(
        position.account_id,
        position.account_type,
        sellAmount,
        buyAmount,
        totalFee
      );
      
      // 6. 计算持仓时长
      const entryTime = new Date(position.entry_time).getTime();
      const exitTime = Date.now();
      const holdingMinutes = Math.floor((exitTime - entryTime) / (60 * 1000));
      
      // 7. 生成完成ID
      const completionId = this.generateCompletionId();
      
      // 8. 插入到已完成策略池
      await this.db
        .prepare(`
          INSERT INTO completed_strategy_pool (
            completion_id,
            execution_id,
            strategy_id,
            strategy_name,
            symbol,
            direction,
            entry_signal_id,
            entry_signal_type,
            entry_price,
            entry_time,
            position_size,
            position_amount,
            exit_signal_id,
            exit_signal_type,
            exit_price,
            exit_time,
            exit_reason,
            highest_price,
            lowest_price,
            max_unrealized_pnl_pct,
            min_unrealized_pnl_pct,
            realized_pnl,
            realized_pnl_pct,
            holding_minutes,
            check_count,
            entry_fee,
            exit_fee,
            total_fee,
            net_pnl,
            account_id,
            account_type,
            created_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        `)
        .bind(
          completionId,
          executionId,
          position.strategy_id,
          position.strategy_name,
          position.symbol,
          position.direction,
          position.entry_signal_id,
          position.entry_signal_type,
          position.entry_price,
          position.entry_time,
          position.position_size,
          position.buy_filled_amount,
          exitSignalCode || null,
          exitReason,
          exitPrice,
          exitReason,
          position.highest_price,
          position.lowest_price,
          position.unrealized_pnl_pct || 0,
          position.unrealized_pnl_pct || 0,
          realizedPnl,
          realizedPnlPct,
          holdingMinutes,
          position.check_count || 0,
          position.buy_fee,
          sellFee,
          totalFee,
          realizedPnl,
          position.account_id,
          position.account_type
        )
        .run();
      
      // 9. 从执行中池删除
      await this.db
        .prepare(`DELETE FROM executing_strategy_pool WHERE execution_id = ?`)
        .bind(executionId)
        .run();
      
      console.log(`✅ 卖出已完成 [${position.symbol}]: ${completionId}`);
      console.log(`   成本: ${buyAmount.toFixed(2)} USDT`);
      console.log(`   卖出: ${sellAmount.toFixed(2)} USDT`);
      console.log(`   手续费: ${totalFee.toFixed(2)} USDT`);
      console.log(`   盈亏: ${realizedPnl >= 0 ? '+' : ''}${realizedPnl.toFixed(2)} USDT (${realizedPnlPct.toFixed(2)}%)`);
      
      return { success: true, completionId, profit: realizedPnl };
      
    } catch (error) {
      console.error('❌ 执行卖出失败:', error);
      return { success: false, reason: error.message };
    }
  }

  /**
   * 清理过期的信号（超过3根K线）
   */
  async cleanupExpiredSignals(): Promise<number> {
    const result = await this.db
      .prepare(`
        UPDATE strategy_signal_pool
        SET status = 'REJECTED',
            rejection_reason = '信号已过期'
        WHERE status = 'PENDING'
          AND expires_at < CURRENT_TIMESTAMP
      `)
      .run();
    
    const count = result.meta?.changes || 0;
    if (count > 0) {
      console.log(`🧹 清理了 ${count} 个过期信号`);
    }
    
    return count;
  }

  /**
   * 获取池统计信息
   */
  async getPoolStatistics(): Promise<any> {
    const productionCount = await this.db
      .prepare(`SELECT COUNT(*) as count FROM strategy_signal_pool WHERE status = 'PENDING'`)
      .first();
    
    const executingCount = await this.db
      .prepare(`SELECT COUNT(*) as count FROM executing_strategy_pool`)
      .first();
    
    const completedToday = await this.db
      .prepare(`
        SELECT COUNT(*) as count 
        FROM completed_strategy_pool 
        WHERE DATE(created_at) = DATE('now')
      `)
      .first();
    
    return {
      production_pool: productionCount?.count || 0,
      executing_pool: executingCount?.count || 0,
      completed_today: completedToday?.count || 0
    };
  }

  // ========== 辅助方法 ==========

  private generatePoolId(): string {
    return `POOL_${Date.now()}_${Math.random().toString(36).substr(2, 9).toUpperCase()}`;
  }

  private generateExecutionId(): string {
    return `EXEC_${Date.now()}_${Math.random().toString(36).substr(2, 9).toUpperCase()}`;
  }

  private generateCompletionId(): string {
    return `COMP_${Date.now()}_${Math.random().toString(36).substr(2, 9).toUpperCase()}`;
  }

  private async checkSignalExists(symbol: string, signalCode: string): Promise<boolean> {
    const result = await this.db
      .prepare(`
        SELECT COUNT(*) as count
        FROM strategy_signal_pool
        WHERE symbol = ?
          AND signal_id = ?
          AND status IN ('PENDING', 'EXECUTING')
      `)
      .bind(symbol, signalCode)
      .first();
    
    return (result?.count as number) > 0;
  }

  private async checkTodayConflict(symbol: string): Promise<{ hasConflict: boolean }> {
    const today = new Date().toISOString().split('T')[0];
    
    const result = await this.db
      .prepare(`
        SELECT COUNT(*) as count
        FROM strategy_signal_pool
        WHERE symbol = ?
          AND DATE(created_at) = ?
          AND status IN ('PENDING', 'EXECUTING')
          AND action = 'OPEN'
      `)
      .bind(symbol, today)
      .first();
    
    return { hasConflict: (result?.count as number) > 0 };
  }

  private async getStrategy(strategyCode: string): Promise<any | null> {
    return await this.db
      .prepare(`SELECT * FROM strategy_library WHERE strategy_code = ?`)
      .bind(strategyCode)
      .first();
  }

  private async getPoolEntry(poolId: string): Promise<any | null> {
    return await this.db
      .prepare(`SELECT * FROM strategy_signal_pool WHERE pool_id = ?`)
      .bind(poolId)
      .first();
  }

  private async getPosition(executionId: string): Promise<any | null> {
    return await this.db
      .prepare(`SELECT * FROM executing_strategy_pool WHERE execution_id = ?`)
      .bind(executionId)
      .first();
  }

  private async markPoolEntryAs(
    poolId: string,
    status: string,
    reason?: string | null,
    executionId?: string
  ): Promise<void> {
    let query = `UPDATE strategy_signal_pool SET status = ?, updated_at = CURRENT_TIMESTAMP`;
    const params: any[] = [status];
    
    if (reason) {
      query += `, rejection_reason = ?`;
      params.push(reason);
    }
    
    if (executionId) {
      query += `, execution_time = CURRENT_TIMESTAMP`;
    }
    
    query += ` WHERE pool_id = ?`;
    params.push(poolId);
    
    await this.db.prepare(query).bind(...params).run();
  }

  private getMonitoredSellSignals(strategy: any): string {
    const signals: string[] = [];
    
    for (let i = 1; i <= 5; i++) {
      const signalCode = strategy[`exit_signal_code_${i}`];
      if (signalCode) {
        signals.push(signalCode);
      }
    }
    
    return JSON.stringify(signals);
  }
}
