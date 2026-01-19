/**
 * 交易账户服务 - 三流合一系统
 * 管理模拟和实盘账户
 */

import { D1Database } from '@cloudflare/workers-types';

export interface TradingAccount {
  account_id: string;
  account_type: 'SIMULATION' | 'LIVE';
  account_name: string;
  
  // 资金信息
  initial_balance: number;
  current_balance: number;
  available_balance: number;
  frozen_balance: number;
  
  // 交易统计
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  total_pnl_pct: number;
  
  // 风险管理
  max_concurrent_positions: number;
  current_positions: number;
  max_position_size: number;
  max_daily_loss?: number;
  
  // 状态
  is_active: number;
  created_at?: string;
  updated_at?: string;
}

export class TradingAccountService {
  constructor(private db: D1Database) {}

  /**
   * 创建新账户
   */
  async createAccount(params: {
    accountType: 'SIMULATION' | 'LIVE';
    accountName: string;
    initialBalance: number;
    maxConcurrentPositions?: number;
    maxPositionSize?: number;
    maxDailyLoss?: number;
  }): Promise<string> {
    const accountId = `${params.accountType}_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;

    await this.db
      .prepare(`
        INSERT INTO trading_accounts (
          account_id, account_type, account_name,
          initial_balance, current_balance, available_balance, frozen_balance,
          total_trades, winning_trades, losing_trades, win_rate, total_pnl, total_pnl_pct,
          max_concurrent_positions, current_positions, max_position_size,
          max_daily_loss, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, ?, 0, ?, ?, 1)
      `)
      .bind(
        accountId,
        params.accountType,
        params.accountName,
        params.initialBalance,
        params.initialBalance,
        params.initialBalance,
        params.maxConcurrentPositions || 5,
        params.maxPositionSize || 100,
        params.maxDailyLoss || null
      )
      .run();

    console.log(`✅ 账户创建成功: ${accountId}`);
    return accountId;
  }

  /**
   * 获取账户信息
   */
  async getAccount(accountId: string): Promise<TradingAccount | null> {
    const result = await this.db
      .prepare(`SELECT * FROM trading_accounts WHERE account_id = ?`)
      .bind(accountId)
      .all();

    return result.results.length > 0 ? (result.results[0] as TradingAccount) : null;
  }

  /**
   * 获取所有激活的账户
   */
  async getActiveAccounts(accountType?: 'SIMULATION' | 'LIVE'): Promise<TradingAccount[]> {
    let query = `SELECT * FROM trading_accounts WHERE is_active = 1`;
    const params: any[] = [];

    if (accountType) {
      query += ` AND account_type = ?`;
      params.push(accountType);
    }

    query += ` ORDER BY created_at DESC`;

    const result = await this.db
      .prepare(query)
      .bind(...params)
      .all();

    return result.results as TradingAccount[];
  }

  /**
   * 冻结资金（开仓时）
   */
  async freezeBalance(accountId: string, amount: number): Promise<boolean> {
    const account = await this.getAccount(accountId);
    if (!account) return false;

    if (account.available_balance < amount) {
      console.error(`❌ 资金不足: 可用${account.available_balance}, 需要${amount}`);
      return false;
    }

    const result = await this.db
      .prepare(`
        UPDATE trading_accounts
        SET available_balance = available_balance - ?,
            frozen_balance = frozen_balance + ?,
            current_positions = current_positions + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE account_id = ?
      `)
      .bind(amount, amount, accountId)
      .run();

    return result.success;
  }

  /**
   * 解冻资金并更新余额（平仓时）
   */
  async unfreezeAndUpdateBalance(
    accountId: string,
    frozenAmount: number,
    pnl: number,
    isWin: boolean
  ): Promise<boolean> {
    const result = await this.db
      .prepare(`
        UPDATE trading_accounts
        SET available_balance = available_balance + ? + ?,
            frozen_balance = frozen_balance - ?,
            current_balance = current_balance + ?,
            total_trades = total_trades + 1,
            winning_trades = winning_trades + ?,
            losing_trades = losing_trades + ?,
            win_rate = ROUND((winning_trades + ?) * 100.0 / (total_trades + 1), 2),
            total_pnl = total_pnl + ?,
            total_pnl_pct = ROUND((total_pnl + ?) / initial_balance * 100, 2),
            current_positions = current_positions - 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE account_id = ?
      `)
      .bind(
        frozenAmount,
        pnl,
        frozenAmount,
        pnl,
        isWin ? 1 : 0,
        isWin ? 0 : 1,
        isWin ? 1 : 0,
        pnl,
        pnl,
        accountId
      )
      .run();

    return result.success;
  }

  /**
   * 检查是否可以开新仓
   */
  async canOpenNewPosition(accountId: string, positionSize: number): Promise<{
    allowed: boolean;
    reason?: string;
  }> {
    const account = await this.getAccount(accountId);
    if (!account) {
      return { allowed: false, reason: '账户不存在' };
    }

    if (!account.is_active) {
      return { allowed: false, reason: '账户未激活' };
    }

    if (account.current_positions >= account.max_concurrent_positions) {
      return { allowed: false, reason: `达到最大持仓数: ${account.max_concurrent_positions}` };
    }

    if (account.available_balance < positionSize) {
      return { allowed: false, reason: `可用余额不足: ${account.available_balance}` };
    }

    if (positionSize > account.max_position_size) {
      return { allowed: false, reason: `超过单笔最大仓位: ${account.max_position_size}` };
    }

    return { allowed: true };
  }

  /**
   * 更新账户状态
   */
  async updateAccount(
    accountId: string,
    updates: Partial<TradingAccount>
  ): Promise<boolean> {
    const fields: string[] = [];
    const values: any[] = [];

    Object.entries(updates).forEach(([key, value]) => {
      if (key !== 'account_id' && key !== 'created_at') {
        fields.push(`${key} = ?`);
        values.push(value);
      }
    });

    if (fields.length === 0) return false;

    values.push(accountId);

    const result = await this.db
      .prepare(`
        UPDATE trading_accounts 
        SET ${fields.join(', ')}, updated_at = CURRENT_TIMESTAMP
        WHERE account_id = ?
      `)
      .bind(...values)
      .run();

    return result.success;
  }

  /**
   * 获取账户统计
   */
  async getAccountStatistics(): Promise<any> {
    const result = await this.db
      .prepare(`
        SELECT 
          account_type,
          COUNT(*) as total_accounts,
          SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_accounts,
          SUM(current_balance) as total_balance,
          SUM(total_pnl) as total_pnl,
          AVG(win_rate) as avg_win_rate,
          SUM(current_positions) as total_positions
        FROM trading_accounts
        GROUP BY account_type
      `)
      .all();

    return result.results;
  }

  /**
   * 重置模拟账户
   */
  async resetSimulationAccount(accountId: string): Promise<boolean> {
    const account = await this.getAccount(accountId);
    if (!account || account.account_type !== 'SIMULATION') {
      return false;
    }

    const result = await this.db
      .prepare(`
        UPDATE trading_accounts
        SET current_balance = initial_balance,
            available_balance = initial_balance,
            frozen_balance = 0,
            total_trades = 0,
            winning_trades = 0,
            losing_trades = 0,
            win_rate = 0,
            total_pnl = 0,
            total_pnl_pct = 0,
            current_positions = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE account_id = ?
      `)
      .bind(accountId)
      .run();

    return result.success;
  }
}
