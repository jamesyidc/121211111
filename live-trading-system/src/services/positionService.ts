// 持仓追踪服务
export class PositionService {
  constructor(private db: D1Database) {}

  // 添加持仓
  async addPosition(data: {
    symbol: string;
    positionType: 'LONG' | 'SHORT';
    entryPrice: number;
    quantity?: number;
    stopLoss?: number;
    takeProfit?: number;
    notes?: string;
  }) {
    const result = await this.db.prepare(`
      INSERT INTO positions (symbol, position_type, entry_price, quantity, stop_loss, take_profit, notes)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    `).bind(
      data.symbol,
      data.positionType,
      data.entryPrice,
      data.quantity || 0,
      data.stopLoss || null,
      data.takeProfit || null,
      data.notes || null
    ).run();

    return { success: true, id: result.meta.last_row_id };
  }

  // 获取所有活跃持仓（带当前价格和预警次数）
  async getActivePositions() {
    const result = await this.db.prepare(`
      SELECT 
        p.*,
        COUNT(DISTINCT pa.id) as alert_count
      FROM positions p
      LEFT JOIN position_alerts pa ON p.id = pa.position_id
      WHERE p.status = 'ACTIVE' 
      GROUP BY p.id
      ORDER BY p.entry_time DESC
    `).all();

    return result.results;
  }
  
  // 获取持仓的当前价格（从最新K线数据）
  async enrichPositionsWithCurrentPrice(positions: any[]) {
    const enriched = [];
    
    for (const pos of positions) {
      // 获取该币种的最新收盘价
      const latestKline = await this.db.prepare(`
        SELECT close FROM kline_data 
        WHERE symbol = ? AND timeframe = '5m'
        ORDER BY open_time DESC 
        LIMIT 1
      `).bind(pos.symbol).first();
      
      enriched.push({
        ...pos,
        current_price: latestKline?.close || null
      });
    }
    
    return enriched;
  }

  // 获取单个持仓详情
  async getPosition(id: number) {
    const result = await this.db.prepare(`
      SELECT * FROM positions WHERE id = ?
    `).bind(id).first();

    return result;
  }

  // 更新持仓
  async updatePosition(id: number, data: {
    quantity?: number;
    stopLoss?: number;
    takeProfit?: number;
    notes?: string;
  }) {
    const updates: string[] = [];
    const values: any[] = [];

    if (data.quantity !== undefined) {
      updates.push('quantity = ?');
      values.push(data.quantity);
    }
    if (data.stopLoss !== undefined) {
      updates.push('stop_loss = ?');
      values.push(data.stopLoss);
    }
    if (data.takeProfit !== undefined) {
      updates.push('take_profit = ?');
      values.push(data.takeProfit);
    }
    if (data.notes !== undefined) {
      updates.push('notes = ?');
      values.push(data.notes);
    }

    updates.push('updated_at = CURRENT_TIMESTAMP');
    values.push(id);

    await this.db.prepare(`
      UPDATE positions 
      SET ${updates.join(', ')}
      WHERE id = ?
    `).bind(...values).run();

    return { success: true };
  }

  // 平仓
  async closePosition(id: number, closedPrice: number) {
    await this.db.prepare(`
      UPDATE positions 
      SET status = 'CLOSED', 
          closed_at = CURRENT_TIMESTAMP,
          closed_price = ?,
          updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `).bind(closedPrice, id).run();

    return { success: true };
  }

  // 删除持仓
  async deletePosition(id: number) {
    // 先删除相关的提醒记录
    await this.db.prepare(`
      DELETE FROM position_alerts WHERE position_id = ?
    `).bind(id).run();

    // 删除持仓
    await this.db.prepare(`
      DELETE FROM positions WHERE id = ?
    `).bind(id).run();

    return { success: true };
  }

  // 检查持仓预警（多单见顶/空单见底）
  async checkPositionAlerts(klineData: any[]) {
    const positions = await this.getActivePositions();
    const alerts: any[] = [];

    for (const position of positions) {
      // 找到对应币种的最新K线数据
      const latestKline = klineData.find((k: any) => 
        k.symbol === position.symbol && k.index === 0
      );

      if (!latestKline) continue;

      const sarChangePercent = latestKline.sarChangePercent || 0;
      const changePercent = parseFloat(latestKline.change) || 0;
      const rsi5min = latestKline.rsi_5min || 0;

      // 多单见顶判断
      if (position.position_type === 'LONG') {
        // 条件：SAR正值变大 + 涨跌幅为负 + RSI > 70
        if (sarChangePercent > 0 && changePercent < 0 && rsi5min > 70) {
          // 检查是否已经提醒过（同一K线时间）
          const existingAlert = await this.db.prepare(`
            SELECT id FROM position_alerts 
            WHERE position_id = ? 
            AND kline_time = ?
            AND alert_type = 'LONG_TOP'
          `).bind(position.id, latestKline.time).first();

          if (!existingAlert) {
            alerts.push({
              position,
              alertType: 'LONG_TOP',
              klineTime: latestKline.time,
              currentPrice: latestKline.close,
              sarChangePercent,
              changePercent,
              rsi5min,
              entryPrice: position.entry_price,
              profitPercent: ((latestKline.close - position.entry_price) / position.entry_price * 100).toFixed(2)
            });
          }
        }
      }

      // 空单见底判断
      if (position.position_type === 'SHORT') {
        // 条件：SAR负值变大（绝对值变大）+ 涨跌幅为正 + RSI < 30
        if (sarChangePercent < 0 && changePercent > 0 && rsi5min < 30) {
          // 检查是否已经提醒过
          const existingAlert = await this.db.prepare(`
            SELECT id FROM position_alerts 
            WHERE position_id = ? 
            AND kline_time = ?
            AND alert_type = 'SHORT_BOTTOM'
          `).bind(position.id, latestKline.time).first();

          if (!existingAlert) {
            alerts.push({
              position,
              alertType: 'SHORT_BOTTOM',
              klineTime: latestKline.time,
              currentPrice: latestKline.close,
              sarChangePercent,
              changePercent,
              rsi5min,
              entryPrice: position.entry_price,
              profitPercent: ((position.entry_price - latestKline.close) / position.entry_price * 100).toFixed(2)
            });
          }
        }
      }
    }

    return alerts;
  }

  // 保存预警记录
  async savePositionAlert(alert: any) {
    const result = await this.db.prepare(`
      INSERT INTO position_alerts (
        position_id, alert_type, kline_time, current_price, 
        sar_change_percent, change_percent, rsi_5min, telegram_sent
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).bind(
      alert.position.id,
      alert.alertType,
      alert.klineTime,
      alert.currentPrice,
      alert.sarChangePercent,
      alert.changePercent,
      alert.rsi5min,
      alert.telegramSent ? 1 : 0
    ).run();

    return { success: true, id: result.meta.last_row_id };
  }

  // 获取持仓的预警历史
  async getPositionAlertHistory(positionId: number) {
    const result = await this.db.prepare(`
      SELECT * FROM position_alerts 
      WHERE position_id = ? 
      ORDER BY alert_time DESC
      LIMIT 50
    `).bind(positionId).all();

    return result.results;
  }
}
