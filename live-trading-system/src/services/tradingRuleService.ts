/**
 * 交易规则服务
 * 管理每个币种的交易权限：能否开单、能开多单还是空单
 */

export interface TradingRule {
  id: number;
  symbol: string;
  trading_allowed: number;  // 1=允许交易, 0=禁止交易
  long_allowed: number;     // 1=允许做多, 0=禁止做多
  short_allowed: number;    // 1=允许做空, 0=禁止做空
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface TradingRuleUpdate {
  symbol: string;
  trading_allowed?: number;
  long_allowed?: number;
  short_allowed?: number;
  notes?: string;
}

export class TradingRuleService {
  constructor(private db: D1Database) {}

  /**
   * 获取所有交易规则
   */
  async getAllRules(): Promise<TradingRule[]> {
    const result = await this.db
      .prepare(`
        SELECT * FROM trading_rules 
        ORDER BY symbol ASC
      `)
      .all();

    return result.results as TradingRule[];
  }

  /**
   * 获取单个币种的交易规则
   */
  async getRuleBySymbol(symbol: string): Promise<TradingRule | null> {
    const result = await this.db
      .prepare(`
        SELECT * FROM trading_rules 
        WHERE symbol = ?
      `)
      .bind(symbol)
      .first();

    return result as TradingRule | null;
  }

  /**
   * 检查币种是否允许交易
   */
  async isTradingAllowed(symbol: string): Promise<boolean> {
    const rule = await this.getRuleBySymbol(symbol);
    return rule ? rule.trading_allowed === 1 : false;
  }

  /**
   * 检查币种是否允许做多
   */
  async isLongAllowed(symbol: string): Promise<boolean> {
    const rule = await this.getRuleBySymbol(symbol);
    if (!rule || rule.trading_allowed !== 1) return false;
    return rule.long_allowed === 1;
  }

  /**
   * 检查币种是否允许做空
   */
  async isShortAllowed(symbol: string): Promise<boolean> {
    const rule = await this.getRuleBySymbol(symbol);
    if (!rule || rule.trading_allowed !== 1) return false;
    return rule.short_allowed === 1;
  }

  /**
   * 更新交易规则
   */
  async updateRule(update: TradingRuleUpdate): Promise<void> {
    const { symbol, trading_allowed, long_allowed, short_allowed, notes } = update;

    // 构建动态更新SQL
    const updates: string[] = [];
    const params: any[] = [];

    if (trading_allowed !== undefined) {
      updates.push('trading_allowed = ?');
      params.push(trading_allowed);
    }

    if (long_allowed !== undefined) {
      updates.push('long_allowed = ?');
      params.push(long_allowed);
    }

    if (short_allowed !== undefined) {
      updates.push('short_allowed = ?');
      params.push(short_allowed);
    }

    if (notes !== undefined) {
      updates.push('notes = ?');
      params.push(notes);
    }

    if (updates.length === 0) {
      return; // 没有需要更新的字段
    }

    // 添加 updated_at
    updates.push('updated_at = CURRENT_TIMESTAMP');
    params.push(symbol);

    const sql = `
      UPDATE trading_rules 
      SET ${updates.join(', ')}
      WHERE symbol = ?
    `;

    await this.db.prepare(sql).bind(...params).run();
  }

  /**
   * 批量更新交易规则
   */
  async batchUpdateRules(updates: TradingRuleUpdate[]): Promise<void> {
    for (const update of updates) {
      await this.updateRule(update);
    }
  }

  /**
   * 获取交易统计（多少币种允许交易、允许做多、允许做空）
   */
  async getTradingStats(): Promise<{
    total: number;
    trading_allowed: number;
    long_allowed: number;
    short_allowed: number;
    both_allowed: number;
    trading_disabled: number;
  }> {
    const result = await this.db
      .prepare(`
        SELECT 
          COUNT(*) as total,
          SUM(CASE WHEN trading_allowed = 1 THEN 1 ELSE 0 END) as trading_allowed,
          SUM(CASE WHEN trading_allowed = 1 AND long_allowed = 1 THEN 1 ELSE 0 END) as long_allowed,
          SUM(CASE WHEN trading_allowed = 1 AND short_allowed = 1 THEN 1 ELSE 0 END) as short_allowed,
          SUM(CASE WHEN trading_allowed = 1 AND long_allowed = 1 AND short_allowed = 1 THEN 1 ELSE 0 END) as both_allowed,
          SUM(CASE WHEN trading_allowed = 0 THEN 1 ELSE 0 END) as trading_disabled
        FROM trading_rules
      `)
      .first();

    return result as any;
  }

  /**
   * 重置所有规则为默认（允许所有交易）
   */
  async resetAllRules(): Promise<void> {
    await this.db
      .prepare(`
        UPDATE trading_rules 
        SET trading_allowed = 1, 
            long_allowed = 1, 
            short_allowed = 1,
            notes = '重置为默认允许所有交易',
            updated_at = CURRENT_TIMESTAMP
      `)
      .run();
  }

  /**
   * 快速设置：禁止所有交易
   */
  async disableAllTrading(): Promise<void> {
    await this.db
      .prepare(`
        UPDATE trading_rules 
        SET trading_allowed = 0,
            notes = '全部禁止交易',
            updated_at = CURRENT_TIMESTAMP
      `)
      .run();
  }

  /**
   * 快速设置：仅允许做多
   */
  async setLongOnly(): Promise<void> {
    await this.db
      .prepare(`
        UPDATE trading_rules 
        SET trading_allowed = 1,
            long_allowed = 1,
            short_allowed = 0,
            notes = '仅允许做多',
            updated_at = CURRENT_TIMESTAMP
      `)
      .run();
  }

  /**
   * 快速设置：仅允许做空
   */
  async setShortOnly(): Promise<void> {
    await this.db
      .prepare(`
        UPDATE trading_rules 
        SET trading_allowed = 1,
            long_allowed = 0,
            short_allowed = 1,
            notes = '仅允许做空',
            updated_at = CURRENT_TIMESTAMP
      `)
      .run();
  }

  /**
   * 根据风险等级自动设置交易规则
   * @param riskLevel 风险等级：'高风险'、'中风险'、'低风险'
   * 
   * 规则：
   * - 高风险：只允许等级1-2的币种交易
   * - 中风险：允许等级1-4的币种交易
   * - 低风险：允许所有等级的币种交易
   */
  async applyRiskBasedRules(riskLevel: string): Promise<void> {
    let allowedLevels: number[] = [];
    let note = '';

    if (riskLevel === '高风险') {
      allowedLevels = [1, 2];
      note = '高风险模式：仅允许1-2等级币种交易';
    } else if (riskLevel === '中风险') {
      allowedLevels = [1, 2, 3, 4];
      note = '中风险模式：允许1-4等级币种交易';
    } else {
      // 低风险：允许所有等级
      await this.db
        .prepare(`
          UPDATE trading_rules 
          SET trading_allowed = 1,
              notes = '低风险模式：允许所有等级币种交易',
              updated_at = CURRENT_TIMESTAMP
        `)
        .run();
      return;
    }

    // 获取符合等级要求的币种列表
    const allowedCoins = await this.db
      .prepare(`
        SELECT symbol FROM coin_priority 
        WHERE level IN (${allowedLevels.join(',')})
      `)
      .all();

    const allowedSymbols = allowedCoins.results.map((row: any) => row.symbol);

    // 禁止所有交易
    await this.db
      .prepare(`
        UPDATE trading_rules 
        SET trading_allowed = 0,
            notes = ?,
            updated_at = CURRENT_TIMESTAMP
      `)
      .bind(note)
      .run();

    // 只启用允许的币种
    if (allowedSymbols.length > 0) {
      const placeholders = allowedSymbols.map(() => '?').join(',');
      await this.db
        .prepare(`
          UPDATE trading_rules 
          SET trading_allowed = 1,
              notes = ?,
              updated_at = CURRENT_TIMESTAMP
          WHERE symbol IN (${placeholders})
        `)
        .bind(note, ...allowedSymbols)
        .run();
    }
  }

  /**
   * 获取当前风险等级下允许交易的币种列表
   */
  async getAllowedCoinsByRisk(riskLevel: string): Promise<string[]> {
    let allowedLevels: number[] = [];

    if (riskLevel === '高风险') {
      allowedLevels = [1, 2];
    } else if (riskLevel === '中风险') {
      allowedLevels = [1, 2, 3, 4];
    } else {
      // 低风险：所有币种
      const result = await this.db
        .prepare(`SELECT symbol FROM coins ORDER BY symbol`)
        .all();
      return result.results.map((row: any) => row.symbol);
    }

    const result = await this.db
      .prepare(`
        SELECT symbol FROM coin_priority 
        WHERE level IN (${allowedLevels.join(',')})
        ORDER BY level, symbol
      `)
      .all();

    return result.results.map((row: any) => row.symbol);
  }

  /**
   * 根据今日市场趋势应用单边策略
   * @param todaySurgeCount 今日总急涨次数
   * @param todayCrashCount 今日总急跌次数
   * 
   * 策略：
   * - 单边主升（只有急涨，没有急跌）：禁止做空
   * - 单边主跌（只有急跌，没有急涨）：禁止做多
   * - 双边震荡：允许做多做空
   */
  async applyUnilateralStrategy(todaySurgeCount: number, todayCrashCount: number): Promise<{
    strategy: string;
    long_allowed: boolean;
    short_allowed: boolean;
  }> {
    let strategy = '';
    let long_allowed = true;
    let short_allowed = true;
    let note = '';

    // 判断市场类型
    if (todaySurgeCount > 0 && todayCrashCount === 0) {
      // 单边主升：只有急涨，没有急跌
      strategy = '单边主升';
      long_allowed = true;
      short_allowed = false;
      note = '单边主升市场：禁止做空';
      
      await this.db
        .prepare(`
          UPDATE trading_rules 
          SET long_allowed = 1,
              short_allowed = 0,
              notes = ?,
              updated_at = CURRENT_TIMESTAMP
          WHERE trading_allowed = 1
        `)
        .bind(note)
        .run();
        
    } else if (todayCrashCount > 0 && todaySurgeCount === 0) {
      // 单边主跌：只有急跌，没有急涨
      strategy = '单边主跌';
      long_allowed = false;
      short_allowed = true;
      note = '单边主跌市场：禁止做多';
      
      await this.db
        .prepare(`
          UPDATE trading_rules 
          SET long_allowed = 0,
              short_allowed = 1,
              notes = ?,
              updated_at = CURRENT_TIMESTAMP
          WHERE trading_allowed = 1
        `)
        .bind(note)
        .run();
        
    } else {
      // 双边震荡：既有急涨也有急跌，或者两者都没有
      strategy = '双边震荡';
      long_allowed = true;
      short_allowed = true;
      note = '双边震荡市场：允许做多做空';
      
      await this.db
        .prepare(`
          UPDATE trading_rules 
          SET long_allowed = 1,
              short_allowed = 1,
              notes = ?,
              updated_at = CURRENT_TIMESTAMP
          WHERE trading_allowed = 1
        `)
        .bind(note)
        .run();
    }

    return {
      strategy,
      long_allowed,
      short_allowed
    };
  }

  /**
   * 获取今日市场统计（急涨急跌总数）
   */
  async getTodayMarketStats(): Promise<{
    todaySurgeCount: number;
    todayCrashCount: number;
  }> {
    // 获取今天的日期（北京时间）
    const now = new Date();
    now.setHours(now.getHours() + 8); // 转换为北京时间
    const today = now.toISOString().split('T')[0];

    const result = await this.db
      .prepare(`
        SELECT 
          SUM(total_surges) as total_surges,
          SUM(total_crashes) as total_crashes
        FROM daily_stats
        WHERE date = ?
      `)
      .bind(today)
      .first();

    return {
      todaySurgeCount: (result as any)?.total_surges || 0,
      todayCrashCount: (result as any)?.total_crashes || 0
    };
  }
}
