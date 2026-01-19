/**
 * 操作提示服务
 * 
 * 职责：
 * 1. 计算K线的操作提示（抄底做多/顶部做空）
 * 2. 将操作提示存储到 kline_data 表的 operation_tip 字段
 * 3. 逻辑与前端 calculateOperationTip() 完全一致
 * 
 * 算法：
 * - 计算30天内最大跌幅/涨幅作为基准
 * - 对每根K线计算距离历史极值的空间比例
 * - 根据比例和币种等级判断是否满足阈值
 * - 绿色徽章=抄底做多，红色徽章=顶部做空
 */

import { D1Database } from '@cloudflare/workers-types';

export interface KlineWithTip {
  open_time: number;
  symbol: string;
  close: number;
  drop_from_48h_high?: number;
  rise_from_48h_low?: number;
  operation_tip?: string;
}

export interface CoinLevel {
  symbol: string;
  coin_level: number;
}

export class OperationTipService {
  constructor(private db: D1Database) {}

  /**
   * 为所有币种计算并更新操作提示
   * 建议在K线同步后调用
   */
  async calculateAndUpdateAllOperationTips(timeframe: string = '5m'): Promise<{
    success: boolean;
    processed: number;
    updated: number;
    errors: string[];
  }> {
    console.log('🎯 [操作提示] 开始计算所有币种的操作提示...');
    
    let processed = 0;
    let updated = 0;
    const errors: string[] = [];

    try {
      // 获取所有币种
      const coins = await this.getAllCoins();
      console.log(`📊 [操作提示] 找到 ${coins.length} 个币种`);

      for (const coin of coins) {
        try {
          const result = await this.calculateAndUpdateForSymbol(coin.symbol, timeframe);
          processed++;
          updated += result.updated;
          console.log(`✅ [操作提示] ${coin.symbol}: 更新了 ${result.updated} 个操作提示`);
        } catch (error: any) {
          const errorMsg = `${coin.symbol}: ${error.message}`;
          errors.push(errorMsg);
          console.error(`❌ [操作提示] ${errorMsg}`);
        }
      }

      console.log(`✅ [操作提示] 完成: 处理 ${processed} 个币种, 更新 ${updated} 条记录`);
      
      return {
        success: true,
        processed,
        updated,
        errors
      };

    } catch (error: any) {
      console.error('❌ [操作提示] 批量计算失败:', error);
      return {
        success: false,
        processed,
        updated,
        errors: [error.message]
      };
    }
  }

  /**
   * 为单个币种计算并更新操作提示
   */
  async calculateAndUpdateForSymbol(
    symbol: string, 
    timeframe: string = '5m',
    limit: number = 300
  ): Promise<{
    success: boolean;
    updated: number;
  }> {
    try {
      // 1. 获取币种等级
      const coinLevel = await this.getCoinLevel(symbol);

      // 2. 获取48小时高低点数据（从OKX API）
      const { high48h, low48h } = await this.fetch48hData(symbol);
      
      if (!high48h || !low48h) {
        console.warn(`⚠️ [操作提示] ${symbol} 无法获取48h数据`);
        return { success: true, updated: 0 };
      }

      // 3. 获取K线数据并计算48h相关指标
      const klines = await this.getKlineDataWithCalculations(symbol, timeframe, limit, high48h, low48h);
      
      if (klines.length === 0) {
        return { success: true, updated: 0 };
      }

      // 4. 计算30天统计（最大跌幅/涨幅）
      const { maxDrop, maxRise } = this.calculate30DayStats(klines);

      if (maxDrop === 0 && maxRise === 0) {
        // 没有足够的历史数据，无法计算操作提示
        return { success: true, updated: 0 };
      }

      const max30dDrop = Math.abs(maxDrop);
      const max30dRise = Math.abs(maxRise);

      // 4. 为每根K线计算操作提示
      const updates: Array<{ open_time: number; operation_tip: string }> = [];

      for (const kline of klines) {
        const tip = this.calculateOperationTip(
          kline,
          coinLevel,
          maxDrop,
          maxRise,
          max30dDrop,
          max30dRise
        );

        // 只更新有提示的K线（不是"-"）
        if (tip && tip !== '-') {
          updates.push({
            open_time: kline.open_time,
            operation_tip: tip
          });
        }
      }

      // 5. 批量更新数据库
      if (updates.length > 0) {
        await this.batchUpdateOperationTips(symbol, timeframe, updates);
      }

      return {
        success: true,
        updated: updates.length
      };

    } catch (error) {
      console.error(`❌ [操作提示] ${symbol} 计算失败:`, error);
      throw error;
    }
  }

  /**
   * 计算30天统计（最大跌幅/涨幅）
   */
  private calculate30DayStats(klines: KlineWithTip[]): {
    maxDrop: number;
    maxRise: number;
  } {
    const validData = klines.filter(k => 
      k.drop_from_48h_high !== null && 
      k.drop_from_48h_high !== undefined &&
      k.rise_from_48h_low !== null && 
      k.rise_from_48h_low !== undefined
    );

    if (validData.length === 0) {
      return { maxDrop: 0, maxRise: 0 };
    }

    // 找出最大跌幅（最负的值）
    let maxDrop = 0;
    validData.forEach(k => {
      if (k.drop_from_48h_high! < maxDrop) {
        maxDrop = k.drop_from_48h_high!;
      }
    });

    // 找出最大涨幅（最大的正值）
    let maxRise = 0;
    validData.forEach(k => {
      if (k.rise_from_48h_low! > maxRise) {
        maxRise = k.rise_from_48h_low!;
      }
    });

    return { maxDrop, maxRise };
  }

  /**
   * 计算单个K线的操作提示
   * 逻辑与前端 calculateOperationTip() 完全一致
   */
  private calculateOperationTip(
    kline: KlineWithTip,
    coinLevel: number,
    historyMaxDrop: number,
    historyMaxRise: number,
    max30dDrop: number,
    max30dRise: number
  ): string {
    // 检查必要数据
    if (!kline.drop_from_48h_high || !kline.rise_from_48h_low || !max30dDrop || !max30dRise) {
      return '-';
    }

    // 计算距离历史最大跌幅/涨幅的空间
    const currentDrop = kline.drop_from_48h_high;
    const currentRise = kline.rise_from_48h_low;
    const dropSpaceAbs = Math.abs(historyMaxDrop - currentDrop);
    const riseSpaceAbs = Math.abs(historyMaxRise - currentRise);

    let requiredRatio = 0;

    // 情况1：距离历史最大跌幅 > 距离历史最大涨幅 → 可能做空
    if (dropSpaceAbs > riseSpaceAbs) {
      // 等级1和2不允许做空
      if (coinLevel === 1 || coinLevel === 2) {
        return '-';
      }

      // 根据30天内最大跌幅确定阈值
      if (max30dDrop < 5) {
        requiredRatio = 3;
      } else if (max30dDrop < 10) {
        requiredRatio = 4;
      } else if (max30dDrop < 15) {
        requiredRatio = 6;
      } else {
        requiredRatio = 9;
      }

      // 计算比值
      const ratio = dropSpaceAbs / riseSpaceAbs;

      if (ratio >= requiredRatio) {
        return '顶部做空';
      }
    }
    // 情况2：距离历史最大跌幅 < 距离历史最大涨幅 → 可能做多
    else if (dropSpaceAbs < riseSpaceAbs) {
      // 根据30天内最大涨幅确定阈值
      if (max30dRise < 5) {
        requiredRatio = 3;
      } else if (max30dRise < 10) {
        requiredRatio = 4;
      } else if (max30dRise < 15) {
        requiredRatio = 6;
      } else {
        requiredRatio = 9;
      }

      // 计算比值
      const ratio = riseSpaceAbs / dropSpaceAbs;

      if (ratio >= requiredRatio) {
        return '抄底做多';
      }
    }

    return '-';
  }

  /**
   * 获取币种等级
   */
  private async getCoinLevel(symbol: string): Promise<number> {
    try {
      const result = await this.db
        .prepare(`SELECT level FROM coin_priority WHERE symbol = ?`)
        .bind(symbol)
        .first();

      if (result) {
        return (result as any).level || 6;
      }

      return 6; // 默认等级6
    } catch (error) {
      console.warn(`⚠️ [操作提示] 无法获取 ${symbol} 的等级，使用默认值6`);
      return 6;
    }
  }

  /**
   * 获取K线数据
   */
  private async getKlineData(
    symbol: string,
    timeframe: string,
    limit: number
  ): Promise<KlineWithTip[]> {
    const result = await this.db
      .prepare(`
        SELECT 
          open_time,
          symbol,
          close,
          drop_from_48h_high,
          rise_from_48h_low
        FROM kline_data
        WHERE symbol = ? 
          AND timeframe = ?
        ORDER BY open_time DESC
        LIMIT ?
      `)
      .bind(symbol, timeframe, limit)
      .all();

    return result.results as KlineWithTip[];
  }

  /**
   * 获取所有币种
   */
  private async getAllCoins(): Promise<Array<{ symbol: string }>> {
    const result = await this.db
      .prepare(`SELECT DISTINCT symbol FROM coin_priority ORDER BY symbol`)
      .all();

    return result.results as Array<{ symbol: string }>;
  }

  /**
   * 批量更新操作提示
   */
  private async batchUpdateOperationTips(
    symbol: string,
    timeframe: string,
    updates: Array<{ open_time: number; operation_tip: string }>
  ): Promise<void> {
    // SQLite 不支持批量 UPDATE，需要逐条执行
    // 使用事务提高性能
    for (const update of updates) {
      await this.db
        .prepare(`
          UPDATE kline_data 
          SET operation_tip = ?
          WHERE symbol = ? 
            AND timeframe = ? 
            AND open_time = ?
        `)
        .bind(
          update.operation_tip,
          symbol,
          timeframe,
          update.open_time
        )
        .run();
    }
  }

  /**
   * 从OKX API获取48小时高低点数据
   */
  private async fetch48hData(symbol: string): Promise<{ high48h: number | null; low48h: number | null }> {
    try {
      const instId = `${symbol}-USDT-SWAP`;
      const url = `https://www.okx.com/api/v5/market/candles?instId=${instId}&bar=2D&limit=1`;
      
      const response = await fetch(url);
      if (response.ok) {
        const result = await response.json();
        if (result.code === "0" && result.data && result.data.length > 0) {
          const kline = result.data[0];
          const high48h = parseFloat(kline[2]); // 索引2是最高价
          const low48h = parseFloat(kline[3]);  // 索引3是最低价
          
          return { high48h, low48h };
        }
      }
      
      return { high48h: null, low48h: null };
    } catch (error: any) {
      console.error(`❌ [操作提示] ${symbol} 获取48h数据失败:`, error.message);
      return { high48h: null, low48h: null };
    }
  }

  /**
   * 获取K线数据并计算48h相关指标
   */
  private async getKlineDataWithCalculations(
    symbol: string,
    timeframe: string,
    limit: number,
    high48h: number,
    low48h: number
  ): Promise<KlineWithTip[]> {
    const result = await this.db
      .prepare(`
        SELECT 
          open_time,
          symbol,
          close
        FROM kline_data
        WHERE symbol = ? 
          AND timeframe = ?
        ORDER BY open_time DESC
        LIMIT ?
      `)
      .bind(symbol, timeframe, limit)
      .all();

    const klines = result.results as KlineWithTip[];
    
    // 计算每根K线的48h相关指标
    for (const kline of klines) {
      if (kline.close > 0) {
        kline.drop_from_48h_high = ((kline.close - high48h) / high48h * 100);
        kline.rise_from_48h_low = ((kline.close - low48h) / low48h * 100);
      }
    }
    
    return klines;
  }
}
