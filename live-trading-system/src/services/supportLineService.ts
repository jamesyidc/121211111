/**
 * 支撑线低吸策略服务
 * 
 * 功能：
 * 1. 管理支撑线价格设置（仅限等级2及以上币种）
 * 2. 检查价格是否接近支撑线（±1%）
 * 3. 提供低吸机会提示
 * 4. 每日0点自动清零支撑线数据
 */

export interface SupportLine {
  id?: number;
  symbol: string;
  support_price: number;
  date: string;
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SupportLineOpportunity {
  symbol: string;
  current_price: number;
  support_price: number;
  distance_percent: number;  // 当前价格距离支撑线的百分比
  is_near_support: boolean;  // 是否接近支撑线（±1%）
  coin_level: number;
  market_strategy: string;   // 当前市场策略
  can_long: boolean;         // 是否可以做多（综合判断）
}

export class SupportLineService {
  constructor(private db: D1Database) {}

  /**
   * 获取今天的日期（北京时间）
   */
  private getTodayDate(): string {
    const now = new Date();
    now.setHours(now.getHours() + 8); // 转换为北京时间
    return now.toISOString().split('T')[0];
  }

  /**
   * 设置或更新支撑线
   */
  async setSupportLine(symbol: string, support_price: number, notes?: string): Promise<void> {
    const today = this.getTodayDate();
    
    await this.db
      .prepare(`
        INSERT INTO support_lines (symbol, support_price, date, notes)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(symbol, date) DO UPDATE SET
          support_price = excluded.support_price,
          notes = excluded.notes,
          updated_at = CURRENT_TIMESTAMP
      `)
      .bind(symbol, support_price, today, notes || '')
      .run();
  }

  /**
   * 批量设置支撑线
   */
  async batchSetSupportLines(lines: Array<{symbol: string, support_price: number, notes?: string}>): Promise<void> {
    const today = this.getTodayDate();
    
    const statements = lines.map(line => 
      this.db
        .prepare(`
          INSERT INTO support_lines (symbol, support_price, date, notes)
          VALUES (?, ?, ?, ?)
          ON CONFLICT(symbol, date) DO UPDATE SET
            support_price = excluded.support_price,
            notes = excluded.notes,
            updated_at = CURRENT_TIMESTAMP
        `)
        .bind(line.symbol, line.support_price, today, line.notes || '')
    );
    
    await this.db.batch(statements);
  }

  /**
   * 获取今天的所有支撑线
   */
  async getTodaySupportLines(): Promise<any[]> {
    const today = this.getTodayDate();
    
    const result = await this.db
      .prepare(`
        SELECT 
          sl.*,
          pr.price as current_price,
          pr.timestamp as price_updated_at
        FROM support_lines sl
        LEFT JOIN (
          SELECT symbol, price, timestamp,
                 ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY timestamp DESC) as rn
          FROM price_records
        ) pr ON sl.symbol = pr.symbol AND pr.rn = 1
        WHERE sl.date = ?
        ORDER BY sl.symbol
      `)
      .bind(today)
      .all();
    
    return result.results as any[];
  }

  /**
   * 获取单个币种的支撑线
   */
  async getSupportLine(symbol: string): Promise<SupportLine | null> {
    const today = this.getTodayDate();
    
    const result = await this.db
      .prepare(`
        SELECT * FROM support_lines
        WHERE symbol = ? AND date = ?
      `)
      .bind(symbol, today)
      .first();
    
    return result as SupportLine | null;
  }

  /**
   * 删除支撑线
   */
  async deleteSupportLine(symbol: string): Promise<void> {
    const today = this.getTodayDate();
    
    await this.db
      .prepare(`
        DELETE FROM support_lines
        WHERE symbol = ? AND date = ?
      `)
      .bind(symbol, today)
      .run();
  }

  /**
   * 清零今天的所有支撑线（每日0点自动执行）
   */
  async clearTodaySupportLines(): Promise<number> {
    const today = this.getTodayDate();
    
    const result = await this.db
      .prepare(`
        DELETE FROM support_lines
        WHERE date = ?
      `)
      .bind(today)
      .run();
    
    return result.meta?.changes || 0;
  }

  /**
   * 清理历史支撑线数据（保留最近7天）
   */
  async cleanupOldSupportLines(): Promise<number> {
    const result = await this.db
      .prepare(`
        DELETE FROM support_lines
        WHERE date < date('now', '-7 days', '+8 hours')
      `)
      .run();
    
    return result.meta?.changes || 0;
  }

  /**
   * 检查低吸机会
   * 
   * 条件：
   * 1. 币种当前等级 <= 2 或 7天内达到过等级2
   * 2. 今天有设置支撑线
   * 3. 当前价格接近支撑线（±1%）
   * 4. 市场策略不是"单边主跌"
   * 5. 交易规则允许做多
   */
  async checkOpportunities(): Promise<SupportLineOpportunity[]> {
    const today = this.getTodayDate();
    
    // 获取所有符合条件的币种（当前等级<=2 或 7天内达到过等级2，有支撑线，允许做多）
    const query = `
      SELECT 
        sl.symbol,
        sl.support_price,
        sl.date,
        cp.level as coin_level,
        tr.long_allowed,
        tr.notes as market_notes,
        COALESCE(lh.level, 0) as history_level
      FROM support_lines sl
      INNER JOIN coin_priority cp ON sl.symbol = cp.symbol
      INNER JOIN trading_rules tr ON sl.symbol = tr.symbol
      LEFT JOIN (
        SELECT symbol, MAX(level) as level
        FROM coin_priority_level_history
        WHERE level <= 2 
          AND expiry_time >= datetime('now')
        GROUP BY symbol
      ) lh ON sl.symbol = lh.symbol
      WHERE sl.date = ?
        AND (cp.level <= 2 OR lh.level <= 2)
        AND tr.trading_allowed = 1
        AND tr.long_allowed = 1
      ORDER BY cp.level, sl.symbol
    `;
    
    const result = await this.db
      .prepare(query)
      .bind(today)
      .all();
    
    const opportunities: SupportLineOpportunity[] = [];
    
    for (const row of result.results as any[]) {
      // 获取当前价格
      const priceResult = await this.db
        .prepare(`
          SELECT price 
          FROM coin_round_details 
          WHERE symbol = ?
          ORDER BY round_time DESC 
          LIMIT 1
        `)
        .bind(row.symbol)
        .first();
      
      if (!priceResult) continue;
      
      const current_price = (priceResult as any).price;
      const support_price = row.support_price;
      
      // 计算距离百分比
      const distance_percent = ((current_price - support_price) / support_price) * 100;
      
      // 判断是否接近支撑线（±1%）
      const is_near_support = Math.abs(distance_percent) <= 1;
      
      // 判断市场策略（从notes中提取）
      const market_notes = row.market_notes || '';
      const market_strategy = market_notes.includes('单边主跌') ? '单边主跌' : 
                              market_notes.includes('单边主升') ? '单边主升' : 
                              '双边震荡';
      
      // 只有在非单边下跌市场中才可以做多
      const can_long = market_strategy !== '单边主跌' && row.long_allowed === 1;
      
      opportunities.push({
        symbol: row.symbol,
        current_price,
        support_price,
        distance_percent,
        is_near_support,
        coin_level: row.coin_level,
        market_strategy,
        can_long
      });
    }
    
    return opportunities;
  }

  /**
   * 获取低吸机会摘要（只返回接近支撑线的币种）
   */
  async getOpportunitySummary(): Promise<{
    total_opportunities: number;
    near_support_count: number;
    opportunities: SupportLineOpportunity[];
  }> {
    const all_opportunities = await this.checkOpportunities();
    const near_support = all_opportunities.filter(o => o.is_near_support && o.can_long);
    
    return {
      total_opportunities: all_opportunities.length,
      near_support_count: near_support.length,
      opportunities: near_support
    };
  }
}
