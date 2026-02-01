/**
 * 风控规则服务
 * 负责风险控制规则的验证和执行
 */

export interface RiskRule {
  id: string;
  rule_name: string;
  rule_type: string;
  description: string;
  is_enabled: number;
  priority: number;
  conditions: string;  // JSON
  action: string;
  created_at: string;
  updated_at?: string;
}

export interface RiskCheckResult {
  allowed: boolean;
  blockedBy?: string[];
  warnings?: string[];
  triggeredRules?: RiskRule[];
}

export interface TradingLog {
  id: string;
  account_id: string;
  log_type: string;
  timestamp: string;
  symbol?: string;
  side?: string;
  order_type?: string;
  price?: number;
  quantity?: number;
  amount?: number;
  leverage?: number;
  status?: string;
  order_id?: string;
  position_id?: string;
  pnl?: number;
  pnl_percent?: number;
  fee?: number;
  risk_rule_triggered?: string;
  message?: string;
  raw_data?: string;
  hash: string;
}

export class RiskControlService {
  constructor(private db: any) {}

  /**
   * 生成数据哈希（用于防篡改）
   */
  private async generateHash(data: any): Promise<string> {
    const dataStr = JSON.stringify(data);
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(dataStr);
    const hashBuffer = await crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return hashHex;
  }

  /**
   * 写入交易日志（不可篡改、不可删除）
   */
  async writeLog(logData: Omit<TradingLog, 'id' | 'hash' | 'created_at'>): Promise<void> {
    try {
      const logId = `log_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const timestamp = new Date().toISOString();
      
      // 生成数据哈希
      const hash = await this.generateHash({ ...logData, id: logId, timestamp });
      
      await this.db.prepare(`
        INSERT INTO trading_logs (
          id, account_id, log_type, timestamp, symbol, side, order_type,
          price, quantity, amount, leverage, status, order_id, position_id,
          pnl, pnl_percent, fee, risk_rule_triggered, message, raw_data, hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        logId,
        logData.account_id,
        logData.log_type,
        logData.timestamp || timestamp,
        logData.symbol || null,
        logData.side || null,
        logData.order_type || null,
        logData.price || null,
        logData.quantity || null,
        logData.amount || null,
        logData.leverage || null,
        logData.status || null,
        logData.order_id || null,
        logData.position_id || null,
        logData.pnl || null,
        logData.pnl_percent || null,
        logData.fee || null,
        logData.risk_rule_triggered || null,
        logData.message || null,
        logData.raw_data || null,
        hash
      ).run();
      
      console.log(`📝 交易日志已写入: ${logId} - ${logData.log_type}`);
    } catch (error: any) {
      console.error('❌ 写入交易日志失败:', error);
      throw error;
    }
  }

  /**
   * 获取所有启用的风控规则
   */
  async getEnabledRules(): Promise<RiskRule[]> {
    try {
      const result = await this.db.prepare(`
        SELECT * FROM risk_control_rules
        WHERE is_enabled = 1
        ORDER BY priority DESC
      `).all();
      
      return result.results || [];
    } catch (error: any) {
      console.error('❌ 获取风控规则失败:', error);
      return [];
    }
  }

  /**
   * 检查做空操作是否被风控规则阻止
   */
  async checkShortAllowed(params: {
    accountId: string;
    symbol: string;
    coinLevel?: number;
    currentChange24h?: number;
    marketTrend?: string;
  }): Promise<RiskCheckResult> {
    const rules = await this.getEnabledRules();
    const blockedBy: string[] = [];
    const triggeredRules: RiskRule[] = [];
    
    for (const rule of rules) {
      try {
        const conditions = JSON.parse(rule.conditions);
        let blocked = false;
        
        switch (rule.rule_type) {
          case 'market_trend':
            // 单边主升不做空
            if (conditions.trend_type === 'single_side_up' && params.marketTrend === 'single_side_up') {
              blocked = true;
            }
            break;
            
          case 'coin_restriction':
            // 等级1-2币种不做空
            if (conditions.level_in && params.coinLevel && conditions.level_in.includes(params.coinLevel)) {
              blocked = true;
            }
            break;
            
          case 'time_based':
            // 23:59涨幅>15%不做空
            const now = new Date();
            const hours = now.getUTCHours() + 8; // 北京时间
            const minutes = now.getUTCMinutes();
            
            if (conditions.time === '23:59' && hours === 23 && minutes === 59) {
              if (params.currentChange24h && params.currentChange24h > conditions.change_threshold) {
                blocked = true;
              }
            }
            break;
        }
        
        if (blocked && rule.action === 'block_short') {
          blockedBy.push(rule.rule_name);
          triggeredRules.push(rule);
          
          // 记录风控触发
          await this.recordRiskTrigger({
            ruleId: rule.id,
            accountId: params.accountId,
            symbol: params.symbol,
            conditionsMet: conditions,
            actionTaken: rule.action,
            blockedOperation: 'short',
            message: `${rule.rule_name}: ${rule.description}`,
          });
        }
      } catch (error) {
        console.error(`解析风控规则失败 ${rule.id}:`, error);
      }
    }
    
    return {
      allowed: blockedBy.length === 0,
      blockedBy: blockedBy.length > 0 ? blockedBy : undefined,
      triggeredRules: triggeredRules.length > 0 ? triggeredRules : undefined,
    };
  }

  /**
   * 检查持仓是否超过限制
   */
  async checkPositionLimit(params: {
    accountId: string;
    currentPositionRatio: number;
    maxAllowedRatio?: number;
  }): Promise<RiskCheckResult> {
    const maxRatio = params.maxAllowedRatio || 0.6667; // 默认2/3
    
    if (params.currentPositionRatio > maxRatio) {
      return {
        allowed: false,
        blockedBy: ['最大持仓限制'],
        warnings: [`当前持仓比例 ${(params.currentPositionRatio * 100).toFixed(2)}% 超过限制 ${(maxRatio * 100).toFixed(2)}%`],
      };
    }
    
    return { allowed: true };
  }

  /**
   * 检查是否需要止损
   */
  async checkStopLoss(params: {
    accountId: string;
    symbol: string;
    currentLossPercent: number;
    stopLossThreshold?: number;
  }): Promise<RiskCheckResult> {
    const threshold = params.stopLossThreshold || 0.20; // 默认20%
    
    if (Math.abs(params.currentLossPercent) >= threshold) {
      return {
        allowed: false,
        blockedBy: ['止损规则触发'],
        warnings: [`${params.symbol} 亏损 ${(Math.abs(params.currentLossPercent) * 100).toFixed(2)}% 达到止损阈值 ${(threshold * 100).toFixed(2)}%`],
      };
    }
    
    return { allowed: true };
  }

  /**
   * 记录风控触发
   */
  private async recordRiskTrigger(params: {
    ruleId: string;
    accountId: string;
    symbol?: string;
    conditionsMet: any;
    actionTaken: string;
    blockedOperation: string;
    message: string;
  }): Promise<void> {
    try {
      const triggerId = `trigger_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const triggerTime = new Date().toISOString();
      
      await this.db.prepare(`
        INSERT INTO risk_control_triggers (
          id, rule_id, account_id, symbol, trigger_time,
          conditions_met, action_taken, blocked_operation, message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `).bind(
        triggerId,
        params.ruleId,
        params.accountId,
        params.symbol || null,
        triggerTime,
        JSON.stringify(params.conditionsMet),
        params.actionTaken,
        params.blockedOperation,
        params.message
      ).run();
      
      console.log(`🚨 风控触发已记录: ${triggerId}`);
    } catch (error: any) {
      console.error('❌ 记录风控触发失败:', error);
    }
  }

  /**
   * 获取交易日志
   */
  async getLogs(params: {
    accountId?: string;
    logType?: string;
    symbol?: string;
    startDate?: string;
    endDate?: string;
    limit?: number;
  }): Promise<TradingLog[]> {
    try {
      let query = 'SELECT * FROM trading_logs WHERE 1=1';
      const bindings: any[] = [];
      
      if (params.accountId) {
        query += ' AND account_id = ?';
        bindings.push(params.accountId);
      }
      
      if (params.logType) {
        query += ' AND log_type = ?';
        bindings.push(params.logType);
      }
      
      if (params.symbol) {
        query += ' AND symbol = ?';
        bindings.push(params.symbol);
      }
      
      if (params.startDate) {
        query += ' AND timestamp >= ?';
        bindings.push(params.startDate);
      }
      
      if (params.endDate) {
        query += ' AND timestamp <= ?';
        bindings.push(params.endDate);
      }
      
      query += ' ORDER BY timestamp DESC';
      
      if (params.limit) {
        query += ' LIMIT ?';
        bindings.push(params.limit);
      }
      
      const result = await this.db.prepare(query).bind(...bindings).all();
      return result.results || [];
    } catch (error: any) {
      console.error('❌ 获取交易日志失败:', error);
      return [];
    }
  }

  /**
   * 获取当日风控状态
   */
  async getDailyRiskStatus(accountId: string, date?: string): Promise<any> {
    try {
      const targetDate = date || new Date().toISOString().split('T')[0];
      
      const result = await this.db.prepare(`
        SELECT * FROM daily_risk_status
        WHERE account_id = ? AND date = ?
      `).bind(accountId, targetDate).first();
      
      return result;
    } catch (error: any) {
      console.error('❌ 获取当日风控状态失败:', error);
      return null;
    }
  }

  /**
   * 更新当日风控状态
   */
  async updateDailyRiskStatus(accountId: string, statusData: any): Promise<void> {
    try {
      const date = new Date().toISOString().split('T')[0];
      const statusId = `status_${date}_${accountId}`;
      const updatedAt = new Date().toISOString();
      
      await this.db.prepare(`
        INSERT INTO daily_risk_status (
          id, date, account_id, market_trend, restricted_coins,
          total_positions, total_equity, position_ratio,
          max_loss_today, max_loss_coin, rules_triggered,
          trades_blocked, trades_executed, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          market_trend = excluded.market_trend,
          restricted_coins = excluded.restricted_coins,
          total_positions = excluded.total_positions,
          total_equity = excluded.total_equity,
          position_ratio = excluded.position_ratio,
          max_loss_today = excluded.max_loss_today,
          max_loss_coin = excluded.max_loss_coin,
          rules_triggered = excluded.rules_triggered,
          trades_blocked = excluded.trades_blocked,
          trades_executed = excluded.trades_executed,
          updated_at = excluded.updated_at
      `).bind(
        statusId,
        date,
        accountId,
        statusData.market_trend || null,
        statusData.restricted_coins || null,
        statusData.total_positions || 0,
        statusData.total_equity || 0,
        statusData.position_ratio || 0,
        statusData.max_loss_today || 0,
        statusData.max_loss_coin || null,
        statusData.rules_triggered || 0,
        statusData.trades_blocked || 0,
        statusData.trades_executed || 0,
        updatedAt
      ).run();
      
      console.log(`📊 当日风控状态已更新: ${date}`);
    } catch (error: any) {
      console.error('❌ 更新当日风控状态失败:', error);
    }
  }
}
