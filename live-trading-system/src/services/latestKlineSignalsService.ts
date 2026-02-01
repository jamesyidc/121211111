/**
 * 最新K线信号服务
 * 
 * 职责：
 * 1. 维护 latest_kline_signals 表（只保存最近3根K线）
 * 2. 从 ReadOnlyKlineService 获取完整的计算后指标数据
 * 3. 提供给信号生成服务使用
 * 
 * 更新频率：每3分钟（与K线同步一致）
 */

import { D1Database } from '@cloudflare/workers-types';

export interface LatestKlineSignal {
  symbol: string;
  timeframe: string;
  open_time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  // 技术指标
  rsi_5min?: number;
  rsi_1h?: number;
  sar?: number;
  sar_change?: number;
  boll_mb?: number;
  boll_ub?: number;
  boll_lb?: number;
  boll_width_change?: number;
  // 市场数据
  homepage_rank?: number;
  change_percent?: string;
  high_48h?: number;
  low_48h?: number;
  drop_from_48h_high?: number;
  rise_from_48h_low?: number;
  // 操作提示
  operation_tip?: string;
}

export class LatestKlineSignalsService {
  constructor(private db: D1Database) {}

  /**
   * 确保表存在
   */
  async ensureTableExists(): Promise<void> {
    try {
      await this.db.prepare(`
        CREATE TABLE IF NOT EXISTS latest_kline_signals (
          symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL DEFAULT '5m',
          open_time INTEGER NOT NULL,
          open REAL NOT NULL,
          high REAL NOT NULL,
          low REAL NOT NULL,
          close REAL NOT NULL,
          volume REAL NOT NULL,
          rsi_5min REAL,
          rsi_1h REAL,
          sar REAL,
          sar_change REAL,
          boll_mb REAL,
          boll_ub REAL,
          boll_lb REAL,
          boll_width_change REAL,
          homepage_rank INTEGER,
          change_percent TEXT,
          high_48h REAL,
          low_48h REAL,
          drop_from_48h_high REAL,
          rise_from_48h_low REAL,
          operation_tip TEXT,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (symbol, open_time)
        )
      `).run();
      
      console.log('✅ [最新K线信号] 表已就绪');
    } catch (error: any) {
      console.error('❌ [最新K线信号] 创建表失败:', error.message);
      throw error;
    }
  }

  /**
   * 更新指定币种的最近3根K线数据
   */
  async updateLatestKlines(
    symbol: string,
    klines: LatestKlineSignal[]
  ): Promise<{ success: boolean; inserted: number }> {
    try {
      // 删除该币种的旧数据
      await this.db.prepare(`
        DELETE FROM latest_kline_signals WHERE symbol = ?
      `).bind(symbol).run();

      // 插入新数据（最多3根）
      const latest3 = klines.slice(0, 3);
      let inserted = 0;

      for (const kline of latest3) {
        await this.db.prepare(`
          INSERT INTO latest_kline_signals (
            symbol, timeframe, open_time, open, high, low, close, volume,
            rsi_5min, rsi_1h, sar, sar_change,
            boll_mb, boll_ub, boll_lb, boll_width_change,
            homepage_rank, change_percent,
            high_48h, low_48h, drop_from_48h_high, rise_from_48h_low,
            operation_tip
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `).bind(
          kline.symbol,
          kline.timeframe || '5m',
          kline.open_time,
          kline.open,
          kline.high,
          kline.low,
          kline.close,
          kline.volume,
          kline.rsi_5min ?? null,
          kline.rsi_1h ?? null,
          kline.sar ?? null,
          kline.sar_change ?? null,
          kline.boll_mb ?? null,
          kline.boll_ub ?? null,
          kline.boll_lb ?? null,
          kline.boll_width_change ?? null,
          kline.homepage_rank ?? null,
          kline.change_percent ?? null,
          kline.high_48h ?? null,
          kline.low_48h ?? null,
          kline.drop_from_48h_high ?? null,
          kline.rise_from_48h_low ?? null,
          kline.operation_tip ?? null
        ).run();

        inserted++;
      }

      return { success: true, inserted };

    } catch (error: any) {
      console.error(`❌ [最新K线信号] ${symbol} 更新失败:`, error.message);
      return { success: false, inserted: 0 };
    }
  }

  /**
   * 批量更新所有币种的最近3根K线
   */
  async updateAllLatestKlines(
    allKlinesData: Map<string, LatestKlineSignal[]>
  ): Promise<{ success: boolean; totalInserted: number; errors: string[] }> {
    let totalInserted = 0;
    const errors: string[] = [];

    console.log(`🔄 [最新K线信号] 开始更新 ${allKlinesData.size} 个币种...`);

    for (const [symbol, klines] of allKlinesData) {
      const result = await this.updateLatestKlines(symbol, klines);
      if (result.success) {
        totalInserted += result.inserted;
        console.log(`✅ [最新K线信号] ${symbol}: 更新了 ${result.inserted} 根K线`);
      } else {
        errors.push(`${symbol}: 更新失败`);
      }
    }

    console.log(`✅ [最新K线信号] 完成: 总共插入 ${totalInserted} 条记录`);

    return {
      success: errors.length === 0,
      totalInserted,
      errors
    };
  }

  /**
   * 从ReadOnlyKlineService获取数据并更新所有币种
   * 
   * 方案A: 合并两个数据源
   * - 数据源1: ReadOnlyKlineService（动态计算的技术指标：RSI, SAR, BOLL等）
   * - 数据源2: kline_data表（operation_tip和48h指标）
   * - 合并策略: 按open_time匹配，取两者的完整字段
   */
  async updateAllLatestSignals(
    timeframe: string = '5m'
  ): Promise<{
    success: boolean;
    processed: number;
    inserted: number;
    deleted: number;
    errors: string[];
  }> {
    // 确保表存在
    await this.ensureTableExists();

    // 动态导入ReadOnlyKlineService
    const { ReadOnlyKlineService } = await import('./ReadOnlyKlineService');
    const klineService = new ReadOnlyKlineService(this.db);

    // 获取所有币种（优先从coin_priority读取，如果为空则从coins读取）
    let coinsResult = await this.db.prepare(`
      SELECT DISTINCT symbol FROM coin_priority ORDER BY symbol
    `).all();
    
    // 如果coin_priority为空，从coins表读取
    if (!coinsResult.results || coinsResult.results.length === 0) {
      console.log('⚠️ [最新K线信号] coin_priority表为空，从coins表读取');
      coinsResult = await this.db.prepare(`
        SELECT DISTINCT symbol FROM coins ORDER BY rank_order
      `).all();
    }

    const coins = coinsResult.results as Array<{ symbol: string }>;
    console.log(`📊 [最新K线信号-合并数据源] 找到 ${coins.length} 个币种`);

    let processed = 0;
    let inserted = 0;
    let deleted = 0;
    const errors: string[] = [];

    for (const coin of coins) {
      try {
        // 步骤1: 从kline_data表获取最近3根K线的基础数据（open/high/low/close等）
        const klineDataResult = await this.db.prepare(`
          SELECT 
            open_time,
            open,
            high,
            low,
            close,
            volume,
            operation_tip, 
            high_48h, 
            low_48h, 
            drop_from_48h_high, 
            rise_from_48h_low
          FROM kline_data 
          WHERE symbol = ? AND timeframe = ?
          ORDER BY open_time DESC 
          LIMIT 3
        `).bind(coin.symbol, timeframe).all();

        const klineDataRecords = klineDataResult.results as Array<{
          open_time: number;
          open: number;
          high: number;
          low: number;
          close: number;
          volume: number;
          operation_tip: string | null;
          high_48h: number | null;
          low_48h: number | null;
          drop_from_48h_high: number | null;
          rise_from_48h_low: number | null;
        }>;

        if (klineDataRecords.length === 0) {
          continue; // 没有数据，跳过
        }

        // 步骤2: 一次性获取该币种的技术指标数据（ReadOnlyKlineService）
        const klineData = await klineService.getKlineWithIndicators(coin.symbol, timeframe, 100);
        
        if (!klineData || !klineData.data || klineData.data.length === 0) {
          continue; // 没有指标数据，跳过
        }
        
        // 创建时间戳到指标数据的映射
        const indicatorMap = new Map<number, any>();
        for (const k of klineData.data) {
          const kTime = this.parseTimeToTimestamp(k.time);
          indicatorMap.set(kTime, k);
        }
        
        // 步骤3: 合并kline_data和指标数据
        const signals: LatestKlineSignal[] = [];
        
        for (const kdRecord of klineDataRecords) {
          const indicatorData = indicatorMap.get(kdRecord.open_time);
          
          signals.push({
            symbol: coin.symbol,
            timeframe: timeframe,
            open_time: kdRecord.open_time,
            open: kdRecord.open,
            high: kdRecord.high,
            low: kdRecord.low,
            close: kdRecord.close,
            volume: kdRecord.volume,
            // 技术指标（来自ReadOnlyKlineService动态计算）
            rsi_5min: indicatorData?.rsi_5min ?? null,
            rsi_1h: indicatorData?.rsi_1h ?? null,
            sar: indicatorData?.sar ?? null,
            sar_change: indicatorData?.sarChange ?? null,
            boll_mb: indicatorData?.boll_mb ?? null,
            boll_ub: indicatorData?.boll_ub ?? null,
            boll_lb: indicatorData?.boll_lb ?? null,
            boll_width_change: indicatorData?.boll_width_change ?? null,
            // 市场数据
            homepage_rank: indicatorData?.homepage_rank ?? null,
            change_percent: indicatorData?.change ?? null,
            // 48h指标和操作提示（来自kline_data持久化数据）
            high_48h: kdRecord.high_48h,
            low_48h: kdRecord.low_48h,
            drop_from_48h_high: kdRecord.drop_from_48h_high,
            rise_from_48h_low: kdRecord.rise_from_48h_low,
            operation_tip: kdRecord.operation_tip
          });
        }

        if (signals.length === 0) {
          continue;
        }

        // 步骤4: 写入latest_kline_signals表
        const result = await this.updateLatestKlines(coin.symbol, signals);
        processed++;
        inserted += result.inserted;
        deleted += signals.length; // 每次都删除旧数据
        
        // 调试日志（仅记录有operation_tip的币种）
        const withTip = signals.filter(s => s.operation_tip).length;
        if (withTip > 0) {
          console.log(`✅ [数据合并] ${coin.symbol}: 技术指标✓ operation_tip✓ (${withTip}/${signals.length}条有提示)`);
        }
        
      } catch (error: any) {
        errors.push(`${coin.symbol}: ${error.message}`);
        console.error(`❌ [最新K线信号] ${coin.symbol} 更新失败:`, error.message);
      }
    }

    console.log(`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 [数据合并完成] 
   处理币种: ${processed}/${coins.length}
   插入记录: ${inserted} 条
   数据源: ReadOnlyKlineService (技术指标) + kline_data (operation_tip)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    `);

    return {
      success: errors.length === 0,
      processed,
      inserted,
      deleted,
      errors
    };
  }

  /**
   * 解析时间字符串为时间戳
   */
  private parseTimeToTimestamp(timeStr: string): number {
    // 格式: "2025/11/3 14:45:00"
    const parts = timeStr.split(/[\/\s:]/);
    const year = parseInt(parts[0]);
    const month = parseInt(parts[1]) - 1; // JS月份从0开始
    const day = parseInt(parts[2]);
    const hour = parseInt(parts[3]);
    const minute = parseInt(parts[4]);
    const second = parseInt(parts[5]);
    
    return new Date(year, month, day, hour, minute, second).getTime();
  }

  /**
   * 获取有operation_tip的最新K线（用于信号生成）
   */
  async getKlinesWithOperationTip(limit: number = 100): Promise<LatestKlineSignal[]> {
    try {
      const result = await this.db.prepare(`
        SELECT * FROM latest_kline_signals
        WHERE operation_tip IS NOT NULL AND operation_tip != ''
        ORDER BY open_time DESC
        LIMIT ?
      `).bind(limit).all();

      return result.results as LatestKlineSignal[];
    } catch (error: any) {
      console.error('❌ [最新K线信号] 查询失败:', error.message);
      return [];
    }
  }

  /**
   * 获取表中的统计信息
   */
  async getStatistics(): Promise<{
    total: number;
    withOperationTip: number;
    symbols: number;
  }> {
    try {
      const totalResult = await this.db.prepare(`
        SELECT COUNT(*) as count FROM latest_kline_signals
      `).first();

      const withTipResult = await this.db.prepare(`
        SELECT COUNT(*) as count FROM latest_kline_signals
        WHERE operation_tip IS NOT NULL AND operation_tip != ''
      `).first();

      const symbolsResult = await this.db.prepare(`
        SELECT COUNT(DISTINCT symbol) as count FROM latest_kline_signals
      `).first();

      return {
        total: (totalResult as any)?.count || 0,
        withOperationTip: (withTipResult as any)?.count || 0,
        symbols: (symbolsResult as any)?.count || 0
      };
    } catch (error: any) {
      console.error('❌ [最新K线信号] 获取统计失败:', error.message);
      return { total: 0, withOperationTip: 0, symbols: 0 };
    }
  }
}
