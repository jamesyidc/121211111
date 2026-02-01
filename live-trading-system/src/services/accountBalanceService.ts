/**
 * 账户余额管理服务
 * 负责管理模拟和实盘账户的资金流动
 */

import { D1Database } from '@cloudflare/workers-types';

export interface AccountBalance {
  balance_id: string;
  account_id: string;
  account_type: 'SIMULATION' | 'LIVE';
  total_balance: number;
  available_balance: number;
  frozen_balance: number;
  position_value: number;
  total_profit: number;
  total_profit_pct: number;
  today_profit: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  win_trades: number;
}

export interface FundOperation {
  amount: number;
  operation_type: 'BUY' | 'SELL' | 'FREEZE' | 'UNFREEZE';
  order_id?: string;
  description?: string;
}

export class AccountBalanceService {
  constructor(private db: D1Database) {}

  /**
   * 获取账户余额信息
   */
  async getBalance(
    accountId: string,
    accountType: 'SIMULATION' | 'LIVE'
  ): Promise<AccountBalance | null> {
    const result = await this.db
      .prepare(`
        SELECT * FROM trading_account_balance
        WHERE account_id = ? AND account_type = ?
      `)
      .bind(accountId, accountType)
      .first();
    
    return result as AccountBalance | null;
  }

  /**
   * 买入时冻结资金
   * @param accountId 账户ID
   * @param accountType 账户类型
   * @param amount 冻结金额（USDT）
   * @param orderId 订单ID
   */
  async freezeFunds(
    accountId: string,
    accountType: 'SIMULATION' | 'LIVE',
    amount: number,
    orderId: string
  ): Promise<{ success: boolean; reason?: string }> {
    
    const balance = await this.getBalance(accountId, accountType);
    
    if (!balance) {
      return { success: false, reason: '账户不存在' };
    }
    
    if (balance.available_balance < amount) {
      return { 
        success: false, 
        reason: `可用余额不足: ${balance.available_balance.toFixed(2)} USDT < ${amount.toFixed(2)} USDT` 
      };
    }
    
    // 扣减可用余额，增加冻结余额
    await this.db
      .prepare(`
        UPDATE trading_account_balance
        SET 
          available_balance = available_balance - ?,
          frozen_balance = frozen_balance + ?,
          last_updated = CURRENT_TIMESTAMP
        WHERE account_id = ? AND account_type = ?
      `)
      .bind(amount, amount, accountId, accountType)
      .run();
    
    console.log(`💰 [${accountType}] 冻结资金: ${amount.toFixed(2)} USDT, 订单: ${orderId}`);
    
    return { success: true };
  }

  /**
   * 买入成交后，从冻结余额转为持仓
   * @param accountId 账户ID
   * @param accountType 账户类型
   * @param frozenAmount 解冻金额
   * @param filledAmount 实际成交金额
   */
  async confirmBuy(
    accountId: string,
    accountType: 'SIMULATION' | 'LIVE',
    frozenAmount: number,
    filledAmount: number
  ): Promise<{ success: boolean }> {
    
    // 解冻资金
    await this.db
      .prepare(`
        UPDATE trading_account_balance
        SET 
          frozen_balance = frozen_balance - ?,
          position_value = position_value + ?,
          last_updated = CURRENT_TIMESTAMP
        WHERE account_id = ? AND account_type = ?
      `)
      .bind(frozenAmount, filledAmount, accountId, accountType)
      .run();
    
    // 如果有未成交部分，退回可用余额
    const unfilledAmount = frozenAmount - filledAmount;
    if (unfilledAmount > 0) {
      await this.db
        .prepare(`
          UPDATE trading_account_balance
          SET available_balance = available_balance + ?
          WHERE account_id = ? AND account_type = ?
        `)
        .bind(unfilledAmount, accountId, accountType)
        .run();
    }
    
    console.log(`✅ [${accountType}] 买入确认: 成交 ${filledAmount.toFixed(2)} USDT, 退回 ${unfilledAmount.toFixed(2)} USDT`);
    
    return { success: true };
  }

  /**
   * 卖出时冻结币（实盘）
   * @param accountId 账户ID
   * @param positionValue 持仓市值
   */
  async freezePosition(
    accountId: string,
    accountType: 'SIMULATION' | 'LIVE',
    positionValue: number
  ): Promise<{ success: boolean }> {
    
    // 实盘需要冻结持仓市值
    if (accountType === 'LIVE') {
      await this.db
        .prepare(`
          UPDATE trading_account_balance
          SET 
            position_value = position_value - ?,
            frozen_balance = frozen_balance + ?,
            last_updated = CURRENT_TIMESTAMP
          WHERE account_id = ? AND account_type = ?
        `)
        .bind(positionValue, positionValue, accountId, accountType)
        .run();
    }
    
    return { success: true };
  }

  /**
   * 卖出成交后，释放资金到可用余额
   * @param accountId 账户ID
   * @param accountType 账户类型
   * @param sellAmount 卖出金额
   * @param buyAmount 买入成本
   * @param fee 手续费
   */
  async confirmSell(
    accountId: string,
    accountType: 'SIMULATION' | 'LIVE',
    sellAmount: number,
    buyAmount: number,
    fee: number = 0
  ): Promise<{ success: boolean; profit: number }> {
    
    const netAmount = sellAmount - fee;
    const profit = netAmount - buyAmount;
    
    // 模拟交易：直接从持仓市值转为可用余额
    if (accountType === 'SIMULATION') {
      await this.db
        .prepare(`
          UPDATE trading_account_balance
          SET 
            position_value = position_value - ?,
            available_balance = available_balance + ?,
            total_profit = total_profit + ?,
            total_balance = total_balance + ?,
            last_updated = CURRENT_TIMESTAMP
          WHERE account_id = ? AND account_type = ?
        `)
        .bind(buyAmount, netAmount, profit, profit, accountId, accountType)
        .run();
    } 
    // 实盘：从冻结余额转为可用余额
    else {
      await this.db
        .prepare(`
          UPDATE trading_account_balance
          SET 
            frozen_balance = frozen_balance - ?,
            available_balance = available_balance + ?,
            total_profit = total_profit + ?,
            total_balance = total_balance + ?,
            last_updated = CURRENT_TIMESTAMP
          WHERE account_id = ? AND account_type = ?
        `)
        .bind(buyAmount, netAmount, profit, profit, accountId, accountType)
        .run();
    }
    
    console.log(`💵 [${accountType}] 卖出确认: 收入 ${netAmount.toFixed(2)} USDT, 盈亏 ${profit >= 0 ? '+' : ''}${profit.toFixed(2)} USDT`);
    
    return { success: true, profit };
  }

  /**
   * 更新持仓市值（实时价格变动）
   */
  async updatePositionValue(
    accountId: string,
    accountType: 'SIMULATION' | 'LIVE',
    newPositionValue: number
  ): Promise<void> {
    await this.db
      .prepare(`
        UPDATE trading_account_balance
        SET 
          position_value = ?,
          total_balance = available_balance + frozen_balance + ?,
          last_updated = CURRENT_TIMESTAMP
        WHERE account_id = ? AND account_type = ?
      `)
      .bind(newPositionValue, newPositionValue, accountId, accountType)
      .run();
  }

  /**
   * 初始化账户（如果不存在）
   */
  async initializeAccount(
    accountId: string,
    accountType: 'SIMULATION' | 'LIVE',
    initialBalance: number = 10000
  ): Promise<{ success: boolean }> {
    
    const exists = await this.getBalance(accountId, accountType);
    if (exists) {
      return { success: true };
    }
    
    const balanceId = `BAL_${accountType.substring(0, 3)}_${Date.now()}`;
    
    await this.db
      .prepare(`
        INSERT INTO trading_account_balance (
          balance_id,
          account_id,
          account_type,
          total_balance,
          available_balance
        ) VALUES (?, ?, ?, ?, ?)
      `)
      .bind(balanceId, accountId, accountType, initialBalance, initialBalance)
      .run();
    
    console.log(`🆕 [${accountType}] 账户已初始化: ${accountId}, 初始余额: ${initialBalance} USDT`);
    
    return { success: true };
  }

  /**
   * 获取账户统计信息
   */
  async getAccountStatistics(
    accountId: string,
    accountType: 'SIMULATION' | 'LIVE'
  ): Promise<any> {
    
    const balance = await this.getBalance(accountId, accountType);
    if (!balance) {
      return null;
    }
    
    // 获取持仓数量
    const positionCount = await this.db
      .prepare(`
        SELECT COUNT(*) as count
        FROM executing_strategy_pool
        WHERE account_id = ? AND account_type = ?
      `)
      .bind(accountId, accountType)
      .first();
    
    // 获取今日交易
    const todayTrades = await this.db
      .prepare(`
        SELECT 
          COUNT(*) as count,
          SUM(realized_pnl) as profit
        FROM completed_strategy_pool
        WHERE account_id = ? 
          AND account_type = ?
          AND DATE(created_at) = DATE('now')
      `)
      .bind(accountId, accountType)
      .first();
    
    return {
      ...balance,
      position_count: positionCount?.count || 0,
      today_trades: todayTrades?.count || 0,
      today_profit: todayTrades?.profit || 0
    };
  }
}
