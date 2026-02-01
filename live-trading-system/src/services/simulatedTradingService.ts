// 模拟交易服务
export class SimulatedTradingService {
  constructor(private db: D1Database) {}

  // ========== 账户管理 ==========
  
  // 创建模拟账户
  async createAccount(data: {
    accountName: string;
    initialBalance: number;
    leverage?: number;
    tradingFeeRate?: number;
  }) {
    const result = await this.db.prepare(`
      INSERT INTO simulated_accounts (account_name, initial_balance, current_balance, leverage, trading_fee_rate)
      VALUES (?, ?, ?, ?, ?)
    `).bind(
      data.accountName,
      data.initialBalance,
      data.initialBalance,
      data.leverage || 1.0,
      data.tradingFeeRate || 0.001
    ).run();

    return { success: true, id: result.meta.last_row_id };
  }

  // 获取所有账户
  async getAllAccounts() {
    const result = await this.db.prepare(`
      SELECT * FROM simulated_accounts ORDER BY created_at DESC
    `).all();

    return result.results;
  }

  // 获取单个账户详情
  async getAccount(accountId: number) {
    const account = await this.db.prepare(`
      SELECT * FROM simulated_accounts WHERE id = ?
    `).bind(accountId).first();

    if (!account) {
      throw new Error('账户不存在');
    }

    // 获取统计信息
    const stats = await this.db.prepare(`
      SELECT 
        COUNT(*) as total_trades,
        SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as win_trades,
        SUM(CASE WHEN profit_loss < 0 THEN 1 ELSE 0 END) as lose_trades,
        SUM(profit_loss) as total_profit_loss,
        AVG(profit_loss) as avg_profit_loss
      FROM simulated_trades
      WHERE account_id = ? AND status = 'CLOSED'
    `).bind(accountId).first();

    return {
      ...account,
      stats: {
        ...stats,
        win_rate: stats.total_trades > 0 ? (stats.win_trades / stats.total_trades * 100).toFixed(2) : 0
      }
    };
  }

  // 更新账户余额
  async updateAccountBalance(accountId: number, newBalance: number) {
    await this.db.prepare(`
      UPDATE simulated_accounts 
      SET current_balance = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `).bind(newBalance, accountId).run();

    return { success: true };
  }

  // 更新账户状态
  async updateAccountStatus(accountId: number, status: 'ACTIVE' | 'PAUSED' | 'STOPPED') {
    await this.db.prepare(`
      UPDATE simulated_accounts 
      SET status = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `).bind(status, accountId).run();

    return { success: true };
  }

  // ========== 交易执行 ==========
  
  // 开仓
  async openTrade(data: {
    accountId: number;
    strategyId?: number;
    symbol: string;
    positionType: 'LONG' | 'SHORT';
    entryPrice: number;
    quantity: number;
    signalSource?: string;
    notes?: string;
  }) {
    // 获取账户信息
    const account: any = await this.db.prepare(`
      SELECT * FROM simulated_accounts WHERE id = ?
    `).bind(data.accountId).first();

    if (!account) {
      throw new Error('账户不存在');
    }

    if (account.status !== 'ACTIVE') {
      throw new Error('账户未激活');
    }

    // 计算交易金额和手续费
    const tradeAmount = data.entryPrice * data.quantity;
    const leveragedAmount = tradeAmount * account.leverage;
    const fee = leveragedAmount * account.trading_fee_rate;

    // 检查余额是否足够
    const requiredBalance = tradeAmount + fee;
    if (account.current_balance < requiredBalance) {
      throw new Error(`余额不足，需要 $${requiredBalance.toFixed(2)}, 当前余额 $${account.current_balance.toFixed(2)}`);
    }

    // 扣除保证金和手续费
    const newBalance = account.current_balance - requiredBalance;
    await this.updateAccountBalance(data.accountId, newBalance);

    // 创建交易记录
    const result = await this.db.prepare(`
      INSERT INTO simulated_trades (
        account_id, strategy_id, symbol, trade_type, position_type,
        entry_price, quantity, leverage, fee, signal_source, notes
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      data.accountId,
      data.strategyId || null,
      data.symbol,
      data.positionType === 'LONG' ? 'BUY' : 'SELL',
      data.positionType,
      data.entryPrice,
      data.quantity,
      account.leverage,
      fee,
      data.signalSource || null,
      data.notes || null
    ).run();

    return { 
      success: true, 
      tradeId: result.meta.last_row_id,
      fee,
      newBalance
    };
  }

  // 平仓
  async closeTrade(tradeId: number, exitPrice: number) {
    // 获取交易信息
    const trade: any = await this.db.prepare(`
      SELECT t.*, a.trading_fee_rate, a.current_balance
      FROM simulated_trades t
      JOIN simulated_accounts a ON t.account_id = a.id
      WHERE t.id = ?
    `).bind(tradeId).first();

    if (!trade) {
      throw new Error('交易不存在');
    }

    if (trade.status !== 'OPEN') {
      throw new Error('交易已关闭');
    }

    // 计算盈亏
    const exitAmount = exitPrice * trade.quantity;
    const entryAmount = trade.entry_price * trade.quantity;
    
    let profitLoss: number;
    if (trade.position_type === 'LONG') {
      profitLoss = (exitAmount - entryAmount) * trade.leverage;
    } else {
      profitLoss = (entryAmount - exitAmount) * trade.leverage;
    }

    // 计算平仓手续费
    const exitFee = exitAmount * trade.trading_fee_rate;
    profitLoss -= exitFee;

    // 计算盈亏百分比
    const profitLossPercent = (profitLoss / entryAmount) * 100;

    // 更新交易记录
    await this.db.prepare(`
      UPDATE simulated_trades 
      SET exit_price = ?, 
          profit_loss = ?,
          profit_loss_percent = ?,
          status = 'CLOSED',
          exit_time = CURRENT_TIMESTAMP
      WHERE id = ?
    `).bind(exitPrice, profitLoss, profitLossPercent, tradeId).run();

    // 返还本金并结算盈亏
    const returnAmount = entryAmount + profitLoss - trade.fee;
    const newBalance = trade.current_balance + returnAmount;
    
    await this.updateAccountBalance(trade.account_id, newBalance);

    return {
      success: true,
      profitLoss,
      profitLossPercent,
      exitFee,
      newBalance
    };
  }

  // 获取账户的持仓
  async getOpenTrades(accountId: number) {
    const result = await this.db.prepare(`
      SELECT t.*, s.strategy_name
      FROM simulated_trades t
      LEFT JOIN trading_strategies s ON t.strategy_id = s.id
      WHERE t.account_id = ? AND t.status = 'OPEN'
      ORDER BY t.entry_time DESC
    `).bind(accountId).all();

    return result.results;
  }

  // 获取账户的交易历史
  async getTradeHistory(accountId: number, limit: number = 100) {
    const result = await this.db.prepare(`
      SELECT t.*, s.strategy_name
      FROM simulated_trades t
      LEFT JOIN trading_strategies s ON t.strategy_id = s.id
      WHERE t.account_id = ?
      ORDER BY t.entry_time DESC
      LIMIT ?
    `).bind(accountId, limit).all();

    return result.results;
  }

  // ========== 策略管理 ==========
  
  // 获取所有策略
  async getAllStrategies() {
    const result = await this.db.prepare(`
      SELECT * FROM trading_strategies ORDER BY created_at DESC
    `).all();

    return result.results;
  }

  // 获取策略详情
  async getStrategy(strategyId: number) {
    const strategy = await this.db.prepare(`
      SELECT * FROM trading_strategies WHERE id = ?
    `).bind(strategyId).first();

    return strategy;
  }

  // ========== 自动交易引擎 ==========
  
  // 根据信号自动执行交易
  async executeTradeBySignal(data: {
    accountId: number;
    strategyId: number;
    symbol: string;
    signalType: string; // SAR_BULLISH, SAR_BEARISH, RSI_OVERSOLD, RSI_OVERBOUGHT
    currentPrice: number;
    quantity?: number;
  }) {
    const account: any = await this.getAccount(data.accountId);
    
    if (account.status !== 'ACTIVE') {
      return { success: false, message: '账户未激活' };
    }

    // 检查是否已有该币种的持仓
    const existingTrade: any = await this.db.prepare(`
      SELECT * FROM simulated_trades 
      WHERE account_id = ? AND symbol = ? AND status = 'OPEN'
      LIMIT 1
    `).bind(data.accountId, data.symbol).first();

    // 看多信号（SAR翻多、RSI超卖）
    if (data.signalType === 'SAR_BULLISH' || data.signalType === 'RSI_OVERSOLD') {
      // 如果有空单，先平仓
      if (existingTrade && existingTrade.position_type === 'SHORT') {
        await this.closeTrade(existingTrade.id, data.currentPrice);
      }
      
      // 如果没有多单，开多单
      if (!existingTrade || existingTrade.position_type === 'SHORT') {
        const quantity = data.quantity || (account.current_balance * 0.1 / data.currentPrice); // 默认使用10%资金
        return await this.openTrade({
          accountId: data.accountId,
          strategyId: data.strategyId,
          symbol: data.symbol,
          positionType: 'LONG',
          entryPrice: data.currentPrice,
          quantity,
          signalSource: data.signalType,
          notes: '自动交易：看多信号'
        });
      }
    }
    
    // 看空信号（SAR翻空、RSI超买）
    if (data.signalType === 'SAR_BEARISH' || data.signalType === 'RSI_OVERBOUGHT') {
      // 如果有多单，先平仓
      if (existingTrade && existingTrade.position_type === 'LONG') {
        await this.closeTrade(existingTrade.id, data.currentPrice);
      }
      
      // 如果没有空单，开空单
      if (!existingTrade || existingTrade.position_type === 'LONG') {
        const quantity = data.quantity || (account.current_balance * 0.1 / data.currentPrice);
        return await this.openTrade({
          accountId: data.accountId,
          strategyId: data.strategyId,
          symbol: data.symbol,
          positionType: 'SHORT',
          entryPrice: data.currentPrice,
          quantity,
          signalSource: data.signalType,
          notes: '自动交易：看空信号'
        });
      }
    }

    return { success: true, message: '无需交易' };
  }

  // 批量检查信号并自动交易
  async autoTradeAllSymbols(accountId: number, strategyId: number) {
    const account: any = await this.getAccount(accountId);
    
    if (account.status !== 'ACTIVE') {
      return { success: false, message: '账户未激活' };
    }

    // 获取所有币种的最新信号
    const signals: any = await this.db.prepare(`
      SELECT symbol, signal, close 
      FROM kline_data 
      WHERE timeframe = '5m' 
      AND signal IS NOT NULL
      GROUP BY symbol
      HAVING MAX(open_time)
    `).all();

    const results = [];
    for (const signal of signals.results) {
      let signalType = '';
      
      if (signal.signal && signal.signal.includes('多头')) {
        signalType = 'SAR_BULLISH';
      } else if (signal.signal && signal.signal.includes('空头')) {
        signalType = 'SAR_BEARISH';
      }

      if (signalType) {
        const result = await this.executeTradeBySignal({
          accountId,
          strategyId,
          symbol: signal.symbol,
          signalType,
          currentPrice: signal.close
        });
        
        results.push({
          symbol: signal.symbol,
          signal: signal.signal,
          result
        });
      }
    }

    return { success: true, trades: results };
  }

  // 创建账户快照
  async createAccountSnapshot(accountId: number) {
    const account: any = await this.getAccount(accountId);
    
    await this.db.prepare(`
      INSERT INTO account_snapshots (
        account_id, balance, total_profit_loss, total_trades,
        win_trades, lose_trades, win_rate
      ) VALUES (?, ?, ?, ?, ?, ?, ?)
    `).bind(
      accountId,
      account.current_balance,
      account.stats.total_profit_loss || 0,
      account.stats.total_trades || 0,
      account.stats.win_trades || 0,
      account.stats.lose_trades || 0,
      parseFloat(account.stats.win_rate) || 0
    ).run();

    return { success: true };
  }
}
